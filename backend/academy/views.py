from datetime import date

from django.db import transaction
from django.db.models import Count, Q
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action, api_view
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import AttendanceRecord, AttendanceSession, Course, Enrollment, StudentProfile, User
from .serializers import (
    AttendanceRecordSerializer,
    AttendanceSessionSerializer,
    AttendanceSubmissionSerializer,
    CourseSerializer,
    EnrollmentSerializer,
    UserSerializer,
)


def parse_date_filter(value, field):
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValidationError({field: "Use a valid date in YYYY-MM-DD format."}) from exc


def attendance_queryset_for(user):
    qs = AttendanceRecord.objects.select_related(
        "student", "marked_by", "session__course",
    ).prefetch_related("student__student_profile")
    if user.role == User.STUDENT:
        return qs.filter(student=user)
    if user.role == User.INSTRUCTOR:
        return qs.filter(session__course__instructor=user)
    if user.role == User.ADMIN:
        return qs
    return qs.none()


class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "admin"


class AdminWritesOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.method in permissions.SAFE_METHODS or request.user.role == "admin")


class StaffOrStudentWrites(permissions.BasePermission):
    """Instructors can view enrollments but not change them."""
    def has_permission(self, request, view):
        u = request.user
        return u.is_authenticated and (request.method in permissions.SAFE_METHODS or u.role in ("admin", "student"))


@api_view(["GET"])
def me(request):
    return Response(UserSerializer(request.user).data)


class UserViewSet(viewsets.ModelViewSet):
    serializer_class = UserSerializer
    permission_classes = [IsAdmin]

    def get_queryset(self):
        qs = User.objects.order_by("first_name", "username")
        role = self.request.query_params.get("role")
        return qs.filter(role=role) if role else qs


class CourseViewSet(viewsets.ModelViewSet):
    serializer_class = CourseSerializer
    permission_classes = [AdminWritesOnly]

    def get_queryset(self):
        qs = Course.objects.select_related("instructor").prefetch_related("enrollments").order_by("code")
        u = self.request.user
        return qs.filter(instructor=u) if u.role == "instructor" else qs


class EnrollmentViewSet(viewsets.ModelViewSet):
    serializer_class = EnrollmentSerializer
    permission_classes = [StaffOrStudentWrites]
    http_method_names = ["get", "post", "delete", "head", "options"]

    def get_queryset(self):
        qs = Enrollment.objects.select_related("student", "course")
        u = self.request.user
        if u.role == "student":
            return qs.filter(student=u)
        if u.role == "instructor":
            return qs.filter(course__instructor=u)
        return qs

    def perform_create(self, serializer):
        u = self.request.user
        student = u if u.role == "student" else serializer.validated_data.get("student")
        course = serializer.validated_data["course"]
        if not student:
            raise ValidationError("Choose a student.")
        if Enrollment.objects.filter(student=student, course=course).exists():
            raise ValidationError("Already enrolled in this course.")
        if course.enrollments.count() >= course.capacity:
            raise ValidationError("This course is full.")
        serializer.save(student=student)


class AttendanceSessionViewSet(viewsets.ModelViewSet):
    serializer_class = AttendanceSessionSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        qs = AttendanceSession.objects.select_related("course", "created_by")
        user = self.request.user
        if user.role == User.INSTRUCTOR:
            qs = qs.filter(course__instructor=user)
        elif user.role != User.ADMIN:
            return qs.none()

        course_id = self.request.query_params.get("course")
        if course_id:
            qs = qs.filter(course_id=course_id)
        session_date = parse_date_filter(self.request.query_params.get("date"), "date")
        date_from = parse_date_filter(self.request.query_params.get("date_from"), "date_from")
        date_to = parse_date_filter(self.request.query_params.get("date_to"), "date_to")
        if session_date:
            qs = qs.filter(date=session_date)
        if date_from:
            qs = qs.filter(date__gte=date_from)
        if date_to:
            qs = qs.filter(date__lte=date_to)
        if date_from and date_to and date_from > date_to:
            raise ValidationError({"date_from": "Must be on or before date_to."})
        return qs

    def create(self, request, *args, **kwargs):
        if request.user.role not in (User.ADMIN, User.INSTRUCTOR):
            raise PermissionDenied("Only admins and instructors can open attendance sessions.")
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        course = serializer.validated_data["course"]
        if request.user.role == User.INSTRUCTOR and course.instructor_id != request.user.id:
            raise PermissionDenied("You can only take attendance for your assigned courses.")
        session, created = AttendanceSession.objects.get_or_create(
            course=course,
            date=serializer.validated_data["date"],
            defaults={"created_by": request.user},
        )
        output = self.get_serializer(session)
        headers = self.get_success_headers(output.data)
        return Response(output.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
                        headers=headers)

    @action(detail=True, methods=["get", "post"], url_path="records")
    def records(self, request, pk=None):
        if request.method == "POST" and request.user.role not in (User.ADMIN, User.INSTRUCTOR):
            raise PermissionDenied("Students cannot create or change attendance records.")
        session = self.get_object()
        if request.method == "GET":
            return Response(self.roster(session))

        serializer = AttendanceSubmissionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        submitted = serializer.validated_data["records"]
        enrolled_ids = set(
            Enrollment.objects.filter(course=session.course).values_list("student_id", flat=True)
        )
        submitted_ids = {record["student"] for record in submitted}
        if submitted_ids != enrolled_ids:
            missing = sorted(enrolled_ids - submitted_ids)
            extra = sorted(submitted_ids - enrolled_ids)
            raise ValidationError({
                "records": {
                    "missing_students": missing,
                    "not_enrolled": extra,
                    "detail": "Submit exactly one status for every currently enrolled student.",
                },
            })

        with transaction.atomic():
            for record in submitted:
                AttendanceRecord.objects.update_or_create(
                    session=session,
                    student_id=record["student"],
                    defaults={"status": record["status"], "marked_by": request.user},
                )
            session.save(update_fields=["updated_at"])
        return Response(self.roster(session))

    @staticmethod
    def roster(session):
        enrollments = Enrollment.objects.filter(course=session.course).select_related(
            "student",
        ).prefetch_related("student__student_profile").order_by(
            "student__first_name", "student__username",
        )
        records = {
            record.student_id: record
            for record in AttendanceRecord.objects.filter(session=session).select_related("marked_by")
        }
        result = []
        for enrollment in enrollments:
            student = enrollment.student
            record = records.get(student.id)
            try:
                student_number = student.student_profile.student_number
            except StudentProfile.DoesNotExist:
                student_number = None
            result.append({
                "student": student.id,
                "student_name": student.get_full_name() or student.username,
                "student_number": student_number,
                "status": record.status if record else None,
                "record_id": record.id if record else None,
                "marked_by": record.marked_by.get_full_name() or record.marked_by.username if record else None,
                "marked_at": record.marked_at if record else None,
            })
        return result


class AttendanceRecordViewSet(
    viewsets.GenericViewSet,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
):
    serializer_class = AttendanceRecordSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "patch", "head", "options"]

    def get_queryset(self):
        return attendance_queryset_for(self.request.user)

    def partial_update(self, request, *args, **kwargs):
        if request.user.role not in (User.ADMIN, User.INSTRUCTOR):
            raise PermissionDenied("Students cannot change attendance records.")
        return super().partial_update(request, *args, **kwargs)

    def perform_update(self, serializer):
        serializer.save(marked_by=self.request.user)


class AttendanceHistoryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        records = attendance_queryset_for(request.user)
        course_id = request.query_params.get("course")
        if course_id:
            records = records.filter(session__course_id=course_id)
        date_from = parse_date_filter(request.query_params.get("date_from"), "date_from")
        date_to = parse_date_filter(request.query_params.get("date_to"), "date_to")
        if date_from:
            records = records.filter(session__date__gte=date_from)
        if date_to:
            records = records.filter(session__date__lte=date_to)
        if date_from and date_to and date_from > date_to:
            raise ValidationError({"date_from": "Must be on or before date_to."})
        return Response(AttendanceRecordSerializer(records, many=True).data)


class AttendanceReportView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        records = attendance_queryset_for(request.user)
        course_id = request.query_params.get("course")
        student_id = request.query_params.get("student")
        if request.user.role == User.STUDENT:
            records = records.filter(student=request.user)
        elif student_id:
            records = records.filter(student_id=student_id)
        if course_id:
            records = records.filter(session__course_id=course_id)
        date_from = parse_date_filter(request.query_params.get("date_from"), "date_from")
        date_to = parse_date_filter(request.query_params.get("date_to"), "date_to")
        if date_from:
            records = records.filter(session__date__gte=date_from)
        if date_to:
            records = records.filter(session__date__lte=date_to)
        if date_from and date_to and date_from > date_to:
            raise ValidationError({"date_from": "Must be on or before date_to."})

        counts = records.aggregate(
            present=Count("id", filter=Q(status=AttendanceRecord.PRESENT)),
            absent=Count("id", filter=Q(status=AttendanceRecord.ABSENT)),
        )
        total = counts["present"] + counts["absent"]
        percentage = round(counts["present"] * 100 / total, 1) if total else None
        return Response({
            "total_records": total,
            "present": counts["present"],
            "absent": counts["absent"],
            "attendance_percentage": percentage,
        })
