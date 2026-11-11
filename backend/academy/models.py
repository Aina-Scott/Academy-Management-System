from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ADMIN, INSTRUCTOR, STUDENT = "admin", "instructor", "student"
    ROLES = [(ADMIN, "Admin"), (INSTRUCTOR, "Instructor"), (STUDENT, "Student")]
    role = models.CharField(max_length=12, choices=ROLES, default=STUDENT)

    def save(self, *args, **kwargs):
        if self.is_superuser:
            self.role = self.ADMIN
        super().save(*args, **kwargs)


class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="student_profile")
    student_number = models.CharField(max_length=32, unique=True, null=True, blank=True)
    phone = models.CharField(max_length=30, blank=True)

    def __str__(self):
        return f"Student profile: {self.user.username}"


class InstructorProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="instructor_profile")
    staff_number = models.CharField(max_length=32, unique=True, null=True, blank=True)
    phone = models.CharField(max_length=30, blank=True)

    def __str__(self):
        return f"Instructor profile: {self.user.username}"


class Course(models.Model):
    code = models.CharField(max_length=20, unique=True)
    title = models.CharField(max_length=200)
    instructor = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL,
                                   related_name="courses_taught", limit_choices_to={"role": "instructor"})
    capacity = models.PositiveIntegerField(default=30)

    def __str__(self):
        return f"{self.code} {self.title}"


class Enrollment(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name="enrollments",
                                limit_choices_to={"role": "student"})
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="enrollments")
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("student", "course")


class AttendanceSession(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="attendance_sessions")
    date = models.DateField()
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="attendance_sessions_created")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["course", "date"], name="unique_course_attendance_date"),
        ]
        ordering = ["-date", "course__code"]

    def __str__(self):
        return f"{self.course.code} attendance on {self.date}"


class AttendanceRecord(models.Model):
    PRESENT, ABSENT = "present", "absent"
    STATUS_CHOICES = [(PRESENT, "Present"), (ABSENT, "Absent")]

    session = models.ForeignKey(AttendanceSession, on_delete=models.CASCADE, related_name="records")
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name="attendance_records",
                                limit_choices_to={"role": User.STUDENT})
    status = models.CharField(max_length=8, choices=STATUS_CHOICES)
    marked_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="attendance_records_marked")
    marked_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["session", "student"], name="unique_student_attendance_session"),
            models.CheckConstraint(
                condition=models.Q(status__in=["present", "absent"]),
                name="attendance_status_present_or_absent",
            ),
        ]
        ordering = ["student__first_name", "student__username"]

    def __str__(self):
        return f"{self.student.username}: {self.status} ({self.session})"
