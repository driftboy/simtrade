from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.teaching.views import (
    SemesterViewSet, CourseViewSet, TeachingClassViewSet,
    ExperimentTemplateViewSet, ExperimentGroupViewSet,
    AssignmentViewSet, SubmissionViewSet, ReportViewSet,
)

router = DefaultRouter()
router.register(r'semesters', SemesterViewSet, basename='semester')
router.register(r'courses', CourseViewSet, basename='course')
router.register(r'classes', TeachingClassViewSet, basename='teachingclass')
router.register(r'experiment-templates', ExperimentTemplateViewSet, basename='experimenttemplate')
router.register(r'experiment-groups', ExperimentGroupViewSet, basename='experimentgroup')
router.register(r'assignments', AssignmentViewSet, basename='assignment')
router.register(r'submissions', SubmissionViewSet, basename='submission')
router.register(r'reports', ReportViewSet, basename='report')

urlpatterns = [
    path('', include(router.urls)),
]
