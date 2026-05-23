from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from apps.teaching.models import Semester, Course, TeachingClass, StudentEnrollment
from apps.teaching.serializers import (
    SemesterSerializer, CourseSerializer,
    TeachingClassSerializer, StudentEnrollmentSerializer,
    EnrollRequestSerializer,
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
