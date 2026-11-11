from rest_framework import serializers
from .models import (
    AttendanceRecord,
    AttendanceSession,
    Course,
    Enrollment,
    InstructorProfile,
    StudentProfile,
    User,
)


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)
    student_number = serializers.CharField(source="student_profile.student_number", required=False, allow_blank=True, allow_null=True)
    student_phone = serializers.CharField(source="student_profile.phone", required=False, allow_blank=True)
    staff_number = serializers.CharField(source="instructor_profile.staff_number", required=False, allow_blank=True, allow_null=True)
    instructor_phone = serializers.CharField(source="instructor_profile.phone", required=False, allow_blank=True)

    class Meta:
        model = User
        fields = [
            "id", "username", "first_name", "last_name", "email", "role", "password",
            "student_number", "student_phone", "staff_number", "instructor_phone",
        ]

    def validate_role(self, role):
        if self.instance and role != self.instance.role:
            raise serializers.ValidationError("Change a user's role by creating a new account.")
        return role

    def validate(self, attrs):
        if self.instance is None and not attrs.get("password"):
            raise serializers.ValidationError({"password": "This field is required."})
        return attrs

    def validate_student_number(self, value):
        if not value:
            return None
        profiles = StudentProfile.objects.filter(student_number=value)
        if self.instance:
            profiles = profiles.exclude(user=self.instance)
        if profiles.exists():
            raise serializers.ValidationError("This student number is already in use.")
        return value

    def validate_staff_number(self, value):
        if not value:
            return None
        profiles = InstructorProfile.objects.filter(staff_number=value)
        if self.instance:
            profiles = profiles.exclude(user=self.instance)
        if profiles.exists():
            raise serializers.ValidationError("This staff number is already in use.")
        return value

    def create(self, data):
        student_profile = data.pop("student_profile", {})
        instructor_profile = data.pop("instructor_profile", {})
        user = User.objects.create_user(**data)
        if user.role == User.STUDENT:
            StudentProfile.objects.create(user=user, **student_profile)
        elif user.role == User.INSTRUCTOR:
            InstructorProfile.objects.create(user=user, **instructor_profile)
        return user

    def update(self, instance, data):
        student_profile = data.pop("student_profile", None)
        instructor_profile = data.pop("instructor_profile", None)
        password = data.pop("password", None)

        for field, value in data.items():
            setattr(instance, field, value)
        if password:
            instance.set_password(password)
        instance.save()

        if student_profile is not None and instance.role == User.STUDENT:
            StudentProfile.objects.update_or_create(user=instance, defaults=student_profile)
        if instructor_profile is not None and instance.role == User.INSTRUCTOR:
            InstructorProfile.objects.update_or_create(user=instance, defaults=instructor_profile)
        return instance


class CourseSerializer(serializers.ModelSerializer):
    instructor_name = serializers.SerializerMethodField()
    enrolled = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = ["id", "code", "title", "instructor", "instructor_name", "capacity", "enrolled"]

    def get_instructor_name(self, c):
        return (c.instructor.first_name or c.instructor.username) if c.instructor else None

    def get_enrolled(self, c):
        return c.enrollments.count()

    def validate_capacity(self, capacity):
        if capacity < 1:
            raise serializers.ValidationError("Capacity must be at least one.")
        if self.instance and capacity < self.instance.enrollments.count():
            raise serializers.ValidationError("Capacity cannot be lower than current enrollment.")
        return capacity


class EnrollmentSerializer(serializers.ModelSerializer):
    student = serializers.PrimaryKeyRelatedField(queryset=User.objects.filter(role="student"), required=False)
    student_name = serializers.SerializerMethodField()
    course_code = serializers.CharField(source="course.code", read_only=True)
    course_title = serializers.CharField(source="course.title", read_only=True)

    class Meta:
        model = Enrollment
        fields = ["id", "student", "student_name", "course", "course_code", "course_title"]
        validators = []

    def get_student_name(self, e):
        return e.student.first_name or e.student.username


class AttendanceSessionSerializer(serializers.ModelSerializer):
    course_code = serializers.CharField(source="course.code", read_only=True)
    course_title = serializers.CharField(source="course.title", read_only=True)

    class Meta:
        model = AttendanceSession
        fields = ["id", "course", "course_code", "course_title", "date", "created_by", "created_at", "updated_at"]
        read_only_fields = ["created_by", "created_at", "updated_at"]
        validators = []


class AttendanceRecordSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()
    student_number = serializers.SerializerMethodField()
    marked_by_name = serializers.SerializerMethodField()
    course = serializers.IntegerField(source="session.course_id", read_only=True)
    course_code = serializers.CharField(source="session.course.code", read_only=True)
    course_title = serializers.CharField(source="session.course.title", read_only=True)
    date = serializers.DateField(source="session.date", read_only=True)

    class Meta:
        model = AttendanceRecord
        fields = [
            "id", "session", "student", "student_name", "student_number", "status",
            "marked_by", "marked_by_name", "marked_at", "course", "course_code", "course_title", "date",
        ]
        read_only_fields = [
            "session", "student", "marked_by", "marked_at", "course", "course_code", "course_title", "date",
        ]

    def get_student_name(self, record):
        return record.student.get_full_name() or record.student.username

    def get_student_number(self, record):
        try:
            return record.student.student_profile.student_number
        except StudentProfile.DoesNotExist:
            return None

    def get_marked_by_name(self, record):
        return record.marked_by.get_full_name() or record.marked_by.username


class AttendanceEntrySerializer(serializers.Serializer):
    student = serializers.IntegerField(min_value=1)
    status = serializers.ChoiceField(choices=AttendanceRecord.STATUS_CHOICES)


class AttendanceSubmissionSerializer(serializers.Serializer):
    records = AttendanceEntrySerializer(many=True)

    def validate_records(self, records):
        student_ids = [record["student"] for record in records]
        if len(student_ids) != len(set(student_ids)):
            raise serializers.ValidationError("Each student may appear only once.")
        return records
