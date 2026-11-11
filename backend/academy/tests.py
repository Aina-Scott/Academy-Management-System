from django.urls import reverse
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from .models import (
    AttendanceRecord,
    AttendanceSession,
    Course,
    Enrollment,
    InstructorProfile,
    StudentProfile,
    User,
)


@override_settings(
    SECURE_SSL_REDIRECT=False,
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
)
class AcademyApiTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="academy-admin", password="admin-password", role=User.ADMIN,
        )
        self.instructor = User.objects.create_user(
            username="teacher", password="teacher-password", role=User.INSTRUCTOR,
        )
        self.other_instructor = User.objects.create_user(
            username="other-teacher", password="teacher-password", role=User.INSTRUCTOR,
        )
        self.student = User.objects.create_user(
            username="learner", password="student-password", role=User.STUDENT,
        )
        self.other_student = User.objects.create_user(
            username="other-learner", password="student-password", role=User.STUDENT,
        )
        StudentProfile.objects.create(user=self.student, student_number="S-001", phone="555-0101")
        StudentProfile.objects.create(user=self.other_student, student_number="S-002")
        InstructorProfile.objects.create(user=self.instructor, staff_number="T-001", phone="555-0201")
        InstructorProfile.objects.create(user=self.other_instructor, staff_number="T-002")
        self.course = Course.objects.create(
            code="BIO-1", title="Biology", instructor=self.instructor, capacity=2,
        )
        self.other_course = Course.objects.create(
            code="MAT-1", title="Mathematics", instructor=self.other_instructor,
        )

    def authenticate_as(self, user):
        self.client.force_authenticate(user=user)

    def test_admin_can_create_update_and_delete_users_with_profiles(self):
        self.authenticate_as(self.admin)
        response = self.client.post(reverse("user-list"), {
            "username": "new-learner",
            "first_name": "New",
            "last_name": "Learner",
            "email": "new@example.com",
            "role": User.STUDENT,
            "password": "initial-password",
            "student_number": "S-003",
            "student_phone": "555-0301",
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        created = User.objects.get(username="new-learner")
        self.assertTrue(created.check_password("initial-password"))
        self.assertEqual(created.student_profile.student_number, "S-003")
        self.assertEqual(response.data["student_phone"], "555-0301")

        response = self.client.post(reverse("user-list"), {
            "username": "duplicate-number",
            "role": User.STUDENT,
            "password": "another-password",
            "student_number": "S-001",
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("student_number", response.data)

        response = self.client.post(reverse("user-list"), {
            "username": "new-teacher",
            "role": User.INSTRUCTOR,
            "password": "teacher-password",
            "staff_number": "T-003",
            "instructor_phone": "555-0303",
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        teacher = User.objects.get(username="new-teacher")
        self.assertEqual(teacher.instructor_profile.staff_number, "T-003")
        self.assertEqual(response.data["instructor_phone"], "555-0303")

        response = self.client.patch(reverse("user-detail", args=[created.pk]), {
            "last_name": "Updated",
            "student_number": "",
            "student_phone": "555-0302",
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        created.refresh_from_db()
        self.assertEqual(created.last_name, "Updated")
        self.assertIsNone(created.student_profile.student_number)
        self.assertEqual(created.student_profile.phone, "555-0302")
        self.assertTrue(created.check_password("initial-password"))

        response = self.client.patch(reverse("user-detail", args=[created.pk]), {
            "password": "replacement-password",
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        created.refresh_from_db()
        self.assertTrue(created.check_password("replacement-password"))
        self.assertFalse(created.check_password("initial-password"))

        response = self.client.delete(reverse("user-detail", args=[created.pk]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(User.objects.filter(pk=created.pk).exists())

    def test_user_creation_requires_a_password_and_role_cannot_be_changed(self):
        self.authenticate_as(self.admin)
        response = self.client.post(reverse("user-list"), {
            "username": "no-password", "role": User.STUDENT,
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)

        response = self.client.patch(
            reverse("user-detail", args=[self.student.pk]), {"role": User.INSTRUCTOR},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.student.role, User.STUDENT)

    def test_admin_can_create_update_and_delete_courses(self):
        self.authenticate_as(self.admin)
        response = self.client.post(reverse("course-list"), {
            "code": "ART-1",
            "title": "Art",
            "instructor": self.instructor.pk,
            "capacity": 4,
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        course_id = response.data["id"]
        response = self.client.patch(reverse("course-detail", args=[course_id]), {
            "title": "Art History", "capacity": 5,
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["title"], "Art History")
        self.assertEqual(response.data["capacity"], 5)

        response = self.client.patch(reverse("course-detail", args=[course_id]), {"capacity": 0})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        course = Course.objects.get(pk=course_id)
        Enrollment.objects.create(student=self.student, course=course)
        Enrollment.objects.create(student=self.other_student, course=course)
        response = self.client.patch(reverse("course-detail", args=[course_id]), {"capacity": 1})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("current enrollment", str(response.data))
        response = self.client.delete(reverse("course-detail", args=[course_id]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_student_access_is_limited_to_own_enrollments_and_courses(self):
        own_enrollment = Enrollment.objects.create(student=self.student, course=self.course)
        other_enrollment = Enrollment.objects.create(student=self.other_student, course=self.course)
        self.authenticate_as(self.student)

        response = self.client.get(reverse("enrollment-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([row["id"] for row in response.data], [own_enrollment.pk])
        self.assertEqual(response.data[0]["course_title"], "Biology")

        response = self.client.delete(reverse("enrollment-detail", args=[other_enrollment.pk]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        response = self.client.post(reverse("enrollment-list"), {
            "course": self.other_course.pk, "student": self.other_student.pk,
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["student"], self.student.pk)

        response = self.client.post(reverse("user-list"), {
            "username": "unauthorized", "role": User.STUDENT, "password": "password",
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        response = self.client.patch(reverse("course-detail", args=[self.course.pk]), {"title": "Changed"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_instructor_only_sees_assigned_courses_and_enrollments(self):
        Enrollment.objects.create(student=self.student, course=self.course)
        Enrollment.objects.create(student=self.other_student, course=self.other_course)
        self.authenticate_as(self.instructor)

        response = self.client.get(reverse("course-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([row["id"] for row in response.data], [self.course.pk])

        response = self.client.get(reverse("enrollment-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([row["course"] for row in response.data], [self.course.pk])
        response = self.client.post(reverse("enrollment-list"), {
            "course": self.course.pk, "student": self.other_student.pk,
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        response = self.client.post(reverse("course-list"), {
            "code": "NEW-1", "title": "Unauthorized",
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_duplicate_enrollment_and_course_capacity_are_enforced(self):
        self.authenticate_as(self.student)
        response = self.client.post(reverse("enrollment-list"), {"course": self.course.pk})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        response = self.client.post(reverse("enrollment-list"), {"course": self.course.pk})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Already enrolled", str(response.data))

        self.authenticate_as(self.other_student)
        Enrollment.objects.create(student=self.student, course=self.other_course)
        self.other_course.capacity = 1
        self.other_course.save()
        response = self.client.post(reverse("enrollment-list"), {"course": self.other_course.pk})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("course is full", str(response.data))

    def test_unauthenticated_requests_are_rejected(self):
        response = self.client.get(reverse("course-list"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_jwt_login_and_me_return_the_authenticated_profile(self):
        response = self.client.post("/api/token/", {
            "username": "learner",
            "password": "student-password",
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
        response = self.client.get("/api/me/")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["username"], "learner")
        self.assertEqual(response.data["student_number"], "S-001")
        self.assertEqual(response.data["student_phone"], "555-0101")
        self.assertNotIn("password", response.data)

    def test_attendance_session_is_unique_per_course_and_date(self):
        self.authenticate_as(self.instructor)
        payload = {"course": self.course.pk, "date": "2026-11-10"}
        response = self.client.post("/api/attendance/sessions/", payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        session_id = response.data["id"]

        response = self.client.post("/api/attendance/sessions/", payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["id"], session_id)
        self.assertEqual(AttendanceSession.objects.count(), 1)

        response = self.client.post("/api/attendance/sessions/", {
            "course": self.other_course.pk, "date": "2026-11-10",
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(AttendanceSession.objects.count(), 1)

        self.authenticate_as(self.student)
        response = self.client.post("/api/attendance/sessions/", payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_attendance_submission_is_complete_scoped_and_audited(self):
        Enrollment.objects.create(student=self.student, course=self.course)
        session = AttendanceSession.objects.create(
            course=self.course, date="2026-11-10", created_by=self.instructor,
        )
        self.authenticate_as(self.instructor)

        response = self.client.get(f"/api/attendance/sessions/{session.pk}/records/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([row["student"] for row in response.data], [self.student.pk])
        self.assertIsNone(response.data[0]["status"])

        incomplete = {"records": []}
        response = self.client.post(f"/api/attendance/sessions/{session.pk}/records/", incomplete, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(AttendanceRecord.objects.count(), 0)

        invalid_status = {"records": [{"student": self.student.pk, "status": "late"}]}
        response = self.client.post(f"/api/attendance/sessions/{session.pk}/records/", invalid_status, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(AttendanceRecord.objects.count(), 0)

        duplicate_student = {"records": [
            {"student": self.student.pk, "status": "present"},
            {"student": self.student.pk, "status": "absent"},
        ]}
        response = self.client.post(
            f"/api/attendance/sessions/{session.pk}/records/", duplicate_student, format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(AttendanceRecord.objects.count(), 0)

        unenrolled = {"records": [
            {"student": self.student.pk, "status": "present"},
            {"student": self.other_student.pk, "status": "absent"},
        ]}
        response = self.client.post(f"/api/attendance/sessions/{session.pk}/records/", unenrolled, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(AttendanceRecord.objects.count(), 0)

        submitted = {"records": [{"student": self.student.pk, "status": "present"}]}
        response = self.client.post(f"/api/attendance/sessions/{session.pk}/records/", submitted, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(AttendanceRecord.objects.count(), 1)
        record = AttendanceRecord.objects.get()
        self.assertEqual(record.marked_by, self.instructor)
        self.assertEqual(response.data[0]["status"], AttendanceRecord.PRESENT)

        self.authenticate_as(self.admin)
        response = self.client.patch(
            f"/api/attendance/records/{record.pk}/", {"status": AttendanceRecord.ABSENT},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        record.refresh_from_db()
        self.assertEqual(record.status, AttendanceRecord.ABSENT)
        self.assertEqual(record.marked_by, self.admin)

        self.authenticate_as(self.student)
        response = self.client.post(
            f"/api/attendance/sessions/{session.pk}/records/",
            {"records": [{"student": self.student.pk, "status": "present"}]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        response = self.client.patch(
            f"/api/attendance/records/{record.pk}/", {"status": AttendanceRecord.PRESENT},
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_attendance_history_and_percentage_are_role_scoped_and_filtered(self):
        session = AttendanceSession.objects.create(
            course=self.course, date="2026-11-10", created_by=self.instructor,
        )
        other_session = AttendanceSession.objects.create(
            course=self.other_course, date="2026-11-09", created_by=self.other_instructor,
        )
        own_present = AttendanceRecord.objects.create(
            session=session, student=self.student, status=AttendanceRecord.PRESENT, marked_by=self.instructor,
        )
        own_absent = AttendanceRecord.objects.create(
            session=session, student=self.other_student, status=AttendanceRecord.ABSENT, marked_by=self.instructor,
        )
        other_course_record = AttendanceRecord.objects.create(
            session=other_session, student=self.student, status=AttendanceRecord.ABSENT,
            marked_by=self.other_instructor,
        )

        self.authenticate_as(self.student)
        response = self.client.get("/api/attendance/my-history/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual({row["id"] for row in response.data}, {own_present.pk, other_course_record.pk})
        response = self.client.get("/api/attendance/reports/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {
            "total_records": 2, "present": 1, "absent": 1, "attendance_percentage": 50.0,
        })
        response = self.client.get("/api/attendance/my-history/?date_from=2026-11-10")
        self.assertEqual([row["id"] for row in response.data], [own_present.pk])

        self.authenticate_as(self.instructor)
        response = self.client.get("/api/attendance/my-history/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual({row["id"] for row in response.data}, {own_present.pk, own_absent.pk})
        response = self.client.get("/api/attendance/reports/?course=999999")
        self.assertEqual(response.data["total_records"], 0)

        self.authenticate_as(self.admin)
        response = self.client.get("/api/attendance/sessions/?date=2026-11-10")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([row["id"] for row in response.data], [session.pk])
