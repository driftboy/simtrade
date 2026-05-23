from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.teaching.views import SemesterViewSet, CourseViewSet, TeachingClassViewSet

router = DefaultRouter()
router.register(r'semesters', SemesterViewSet, basename='semester')
router.register(r'courses', CourseViewSet, basename='course')
router.register(r'classes', TeachingClassViewSet, basename='teachingclass')

urlpatterns = [
    path('', include(router.urls)),
]
