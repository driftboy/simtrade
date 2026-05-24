from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from apps.teaching.models import Semester, Course, TeachingClass, StudentEnrollment, ExperimentTemplate, ExperimentGroup, Assignment, AssignmentSubmission
from apps.teaching.serializers import (
    SemesterSerializer, CourseSerializer,
    TeachingClassSerializer, StudentEnrollmentSerializer,
    EnrollRequestSerializer,
    ExperimentTemplateSerializer, ExperimentGroupSerializer, AutoGroupSerializer,
    AssignmentSerializer, AssignmentSubmissionSerializer, GradeSerializer,
)
from apps.teaching.services import SemesterService, CourseService, TeachingClassService
from apps.teaching.permissions import IsTeacherOrAdmin


class SemesterViewSet(viewsets.ModelViewSet):
    queryset = Semester.objects.all()
    serializer_class = SemesterSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.user.user_type == 'student':
            return qs.filter(status__in=['active', 'ended'])
        return qs

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        if not IsTeacherOrAdmin().has_permission(request, self):
            return Response(
                {'code': 2001, 'message': '无权限操作'},
                status=status.HTTP_403_FORBIDDEN,
            )
        semester = SemesterService.activate_semester(pk)
        return Response({
            'code': 0, 'message': '学期已激活',
            'data': SemesterSerializer(semester).data,
        })


class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.select_related('semester')
    serializer_class = CourseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.user_type == 'student':
            return CourseService.get_student_courses(user)
        if user.user_type == 'teacher':
            return CourseService.get_teacher_courses(user)
        return qs

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class TeachingClassViewSet(viewsets.ModelViewSet):
    queryset = TeachingClass.objects.select_related('course', 'course__semester')
    serializer_class = TeachingClassSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        course_id = self.request.query_params.get('course_id')
        if course_id:
            qs = qs.filter(course_id=course_id)
        return qs

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'])
    def enroll(self, request, pk=None):
        serializer = EnrollRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'code': 3002, 'message': '参数错误', 'errors': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            enrollment = TeachingClassService.enroll_student(
                teaching_class_id=pk,
                student=request.user,
                enrollment_code=serializer.validated_data['enrollment_code'],
            )
            return Response({
                'code': 0, 'message': '选课成功',
                'data': StudentEnrollmentSerializer(enrollment).data,
            })
        except ValueError as e:
            return Response(
                {'code': 5005, 'message': str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=True, methods=['get'])
    def enrollments(self, request, pk=None):
        if not IsTeacherOrAdmin().has_permission(request, self):
            return Response(
                {'code': 2001, 'message': '无权限操作'},
                status=status.HTTP_403_FORBIDDEN,
            )
        enrollments = TeachingClassService.get_class_students(pk)
        return Response({
            'code': 0, 'message': 'success',
            'data': StudentEnrollmentSerializer(enrollments, many=True).data,
        })

    @action(detail=True, methods=['post'])
    def drop(self, request, pk=None):
        enrollment = StudentEnrollment.objects.filter(
            teaching_class_id=pk, student=request.user, status='enrolled',
        ).first()
        if not enrollment:
            return Response(
                {'code': 4001, 'message': '未选该班级'},
                status=status.HTTP_404_NOT_FOUND,
            )
        TeachingClassService.drop_student(enrollment.id, request.user)
        return Response({'code': 0, 'message': '退课成功'})


class ExperimentTemplateViewSet(viewsets.ModelViewSet):
    queryset = ExperimentTemplate.objects.all()
    serializer_class = ExperimentTemplateSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.user_type == 'admin':
            return qs
        return qs.filter(is_public=True) | qs.filter(created_by=user)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class ExperimentGroupViewSet(viewsets.ModelViewSet):
    queryset = ExperimentGroup.objects.select_related('company')
    serializer_class = ExperimentGroupSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        experiment_id = self.request.query_params.get('experiment_id')
        if experiment_id:
            qs = qs.filter(experiment_id=experiment_id)
        return qs


class AssignmentViewSet(viewsets.ModelViewSet):
    queryset = Assignment.objects.select_related('teaching_class')
    serializer_class = AssignmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        class_id = self.request.query_params.get('class_id')
        if class_id:
            qs = qs.filter(teaching_class_id=class_id)
        return qs

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        assignment = self.get_object()
        from django.utils import timezone as tz
        submission, _ = AssignmentSubmission.objects.get_or_create(
            assignment=assignment, student=request.user,
            defaults={'status': 'not_submitted'},
        )
        submission.content = request.data.get('content', '')
        if 'attachment' in request.FILES:
            submission.attachment = request.FILES['attachment']
        submission.status = 'submitted'
        submission.submitted_at = tz.now()
        submission.save()
        return Response({
            'code': 0, 'message': '提交成功',
            'data': AssignmentSubmissionSerializer(submission).data,
        })

    @action(detail=True, methods=['get'])
    def submissions(self, request, pk=None):
        if not IsTeacherOrAdmin().has_permission(request, self):
            return Response({'code': 2001, 'message': '无权限操作'}, status=status.HTTP_403_FORBIDDEN)
        assignment = self.get_object()
        submissions = assignment.submissions.select_related('student')
        return Response({
            'code': 0, 'message': 'success',
            'data': AssignmentSubmissionSerializer(submissions, many=True).data,
        })


class SubmissionViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['post'], url_path='(?P<submission_id>[^/.]+)/grade')
    def grade(self, request, submission_id=None):
        if not IsTeacherOrAdmin().has_permission(request, self):
            return Response({'code': 2001, 'message': '无权限操作'}, status=status.HTTP_403_FORBIDDEN)
        submission = AssignmentSubmission.objects.get(id=submission_id)
        serializer = GradeSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'code': 3002, 'message': '参数错误', 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        submission.score = serializer.validated_data['score']
        submission.feedback = serializer.validated_data.get('feedback', '')
        submission.status = 'graded'
        submission.graded_by = request.user
        from django.utils import timezone as tz
        submission.graded_at = tz.now()
        submission.save()
        return Response({
            'code': 0, 'message': '评分成功',
            'data': AssignmentSubmissionSerializer(submission).data,
        })


class ReportViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'], url_path='class/(?P<class_id>[^/.]+)/my')
    def my_report(self, request, class_id=None):
        from apps.teaching.services import GradeReportService
        report = GradeReportService.get_student_report(request.user, int(class_id))
        return Response({'code': 0, 'message': 'success', 'data': report})

    @action(detail=False, methods=['get'], url_path='class/(?P<class_id>[^/.]+)')
    def class_report(self, request, class_id=None):
        if not IsTeacherOrAdmin().has_permission(request, self):
            return Response({'code': 2001, 'message': '无权限操作'}, status=status.HTTP_403_FORBIDDEN)
        from apps.teaching.services import GradeReportService
        report = GradeReportService.get_class_report(int(class_id))
        return Response({'code': 0, 'message': 'success', 'data': report})

    @action(detail=False, methods=['get'], url_path='course/(?P<course_id>[^/.]+)')
    def course_report(self, request, course_id=None):
        if not IsTeacherOrAdmin().has_permission(request, self):
            return Response({'code': 2001, 'message': '无权限操作'}, status=status.HTTP_403_FORBIDDEN)
        from apps.teaching.services import GradeReportService
        report = GradeReportService.get_course_report(int(course_id))
        return Response({'code': 0, 'message': 'success', 'data': report})
