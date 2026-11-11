from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    AttendanceRecord,
    AttendanceSession,
    Course,
    Enrollment,
    InstructorProfile,
    StudentProfile,
    User,
)

admin.site.register(User, UserAdmin)
admin.site.register(Course)
admin.site.register(Enrollment)
admin.site.register(StudentProfile)
admin.site.register(InstructorProfile)
admin.site.register(AttendanceSession)
admin.site.register(AttendanceRecord)


# admin-ire
# admin123