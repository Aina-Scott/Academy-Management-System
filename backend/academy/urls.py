from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from . import views

router = DefaultRouter()
router.register("users", views.UserViewSet, basename="user")
router.register("courses", views.CourseViewSet, basename="course")
router.register("enrollments", views.EnrollmentViewSet, basename="enrollment")
router.register("attendance/sessions", views.AttendanceSessionViewSet, basename="attendance-session")
router.register("attendance/records", views.AttendanceRecordViewSet, basename="attendance-record")

urlpatterns = [
    path("token/", TokenObtainPairView.as_view()),
    path("token/refresh/", TokenRefreshView.as_view()),
    path("me/", views.me),
    path("attendance/my-history/", views.AttendanceHistoryView.as_view(), name="attendance-my-history"),
    path("attendance/reports/", views.AttendanceReportView.as_view(), name="attendance-reports"),
    path("", include(router.urls)),
]
