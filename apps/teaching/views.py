from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.http import HttpResponse
from django.conf import settings
import os
from apps.teaching.models import Semester, Course, TeachingClass, StudentEnrollment, ExperimentTemplate, ExperimentGroup, Assignment, AssignmentSubmission, StudentProfile
from apps.teaching.serializers import (
    SemesterSerializer, CourseSerializer,
    TeachingClassSerializer, StudentEnrollmentSerializer,
    EnrollRequestSerializer,
    ExperimentTemplateSerializer, ExperimentGroupSerializer, AutoGroupSerializer,
    AssignmentSerializer, AssignmentSubmissionSerializer, GradeSerializer,
    StudentListSerializer, AddStudentSerializer,
    UpdateRoleSerializer, BatchUpdateRoleSerializer,
)
# 使用 importlib 直接导入 services.py 文件中的类，避免与 services 目录冲突
import importlib.util
import os
spec = importlib.util.spec_from_file_location("services_module", os.path.join(os.path.dirname(__file__), 'services.py'))
services_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(services_module)
SemesterService = services_module.SemesterService
CourseService = services_module.CourseService
TeachingClassService = services_module.TeachingClassService
from apps.teaching.permissions import IsTeacherOrAdmin
from apps.teaching.services.import_service import ImportService
from django.utils import timezone


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
        course = serializer.save(created_by=self.request.user)
        if self.request.user.user_type == 'teacher':
            course.teachers.add(self.request.user)


class TeachingClassViewSet(viewsets.ModelViewSet):
    queryset = TeachingClass.objects.select_related('course', 'course__semester')
    serializer_class = TeachingClassSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        from django.db.models import Count, Q
        qs = super().get_queryset()
        course_id = self.request.query_params.get('course_id')
        if course_id:
            qs = qs.filter(course_id=course_id)
        # 预先计算学生数量，避免 N+1 查询
        qs = qs.annotate(
            student_count_annotated=Count('enrollments', filter=Q(enrollments__status='enrolled'))
        )
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

    # ========== 班级管理 API ==========

    @action(detail=True, methods=['get', 'post'], url_path='students')
    def students(self, request, pk=None):
        """学生管理 - 获取列表或添加学生

        API: GET /api/v1/teaching/classes/{id}/students/ - 获取学生列表
        API: POST /api/v1/teaching/classes/{id}/students/ - 添加学生
        """
        teaching_class = self.get_object()

        # 权限验证
        if not teaching_class.course.teachers.filter(id=request.user.id).exists():
            return Response(
                {'code': 2001, 'message': '无权限操作'},
                status=status.HTTP_403_FORBIDDEN,
            )

        # GET 请求 - 获取学生列表
        if request.method == 'GET':
            # 获取筛选参数
            role_filter = request.query_params.get('role')
            status_filter = request.query_params.get('status')

            enrollments = teaching_class.enrollments.select_related('student__student_profile')

            if role_filter:
                enrollments = enrollments.filter(role=role_filter)
            if status_filter:
                enrollments = enrollments.filter(status=status_filter)

            # 排序
            ordering = request.query_params.get('ordering', '-enrolled_at')
            enrollments = enrollments.order_by(ordering)

            serializer = StudentListSerializer(enrollments, many=True)
            return Response({
                'code': 0,
                'message': 'success',
                'data': serializer.data,
            })

        # POST 请求 - 添加学生
        if request.method == 'POST':
            serializer = AddStudentSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(
                    {'code': 3002, 'message': '参数错误', 'errors': serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                # 检查容量
                ImportService.check_capacity(teaching_class, 1)

                data = serializer.validated_data
                if 'student_id' in data:
                    # 添加现有用户
                    profile = StudentProfile.objects.get(student_id=data['student_id'])
                    enrollment, created = StudentEnrollment.objects.get_or_create(
                        teaching_class=teaching_class,
                        student=profile.user,
                        defaults={'role': data.get('role', 'student'), 'status': 'enrolled'},
                    )
                else:
                    # 创建新用户
                    enrollment = ImportService.process_import_row(
                        {
                            '学号': data.get('student_id_new'),
                            '姓名': data.get('name'),
                            '手机号': data.get('phone'),
                            '邮箱': data.get('email'),
                            '行政班级': data.get('admin_class'),
                            '年级': data.get('grade'),
                            '初始角色': data.get('role', 'student'),
                        },
                        teaching_class,
                    )

                return Response({
                    'code': 0,
                    'message': '添加成功',
                    'data': StudentListSerializer(enrollment).data,
                })
            except StudentProfile.DoesNotExist:
                return Response(
                    {'code': 4004, 'message': '学生不存在'},
                    status=status.HTTP_404_NOT_FOUND,
                )
            except ValueError as e:
                return Response(
                    {'code': 5005, 'message': str(e)},
                    status=status.HTTP_400_BAD_REQUEST,
                )

    @action(detail=True, methods=['delete'], url_path='students/(?P<student_id>[^/.]+)')
    def remove_student(self, request, pk=None, student_id=None):
        """移除学生（软删除）

        API: DELETE /api/v1/teaching/classes/{id}/students/{student_id}/
        """
        teaching_class = self.get_object()

        # 权限验证
        if not teaching_class.course.teachers.filter(id=request.user.id).exists():
            return Response(
                {'code': 2001, 'message': '无权限操作'},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            enrollment = StudentEnrollment.objects.get(
                teaching_class=teaching_class,
                student_id=student_id,
            )
            enrollment.status = 'dropped'
            enrollment.dropped_at = timezone.now()
            enrollment.save()
            return Response({'code': 0, 'message': '移除成功'})
        except StudentEnrollment.DoesNotExist:
            return Response(
                {'code': 4004, 'message': '学生不存在'},
                status=status.HTTP_404_NOT_FOUND,
            )

    @action(detail=True, methods=['patch'], url_path='student-role')
    def update_student_role(self, request, pk=None):
        """修改学生角色

        API: PATCH /api/v1/teaching/classes/{id}/student-role/
        Body: { enrollment_id: int, role: str }
        """
        teaching_class = self.get_object()

        # 权限验证
        if not teaching_class.course.teachers.filter(id=request.user.id).exists():
            return Response(
                {'code': 2001, 'message': '无权限操作'},
                status=status.HTTP_403_FORBIDDEN,
            )

        enrollment_id = request.data.get('enrollment_id')
        if not enrollment_id:
            return Response(
                {'code': 3002, 'message': '缺少 enrollment_id'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = UpdateRoleSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'code': 3002, 'message': '参数错误', 'errors': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            enrollment = StudentEnrollment.objects.get(
                teaching_class=teaching_class,
                id=enrollment_id,
            )
            enrollment.role = serializer.validated_data['role']
            enrollment.save()
            return Response({
                'code': 0,
                'message': '修改成功',
                'data': StudentListSerializer(enrollment).data,
            })
        except StudentEnrollment.DoesNotExist:
            return Response(
                {'code': 4004, 'message': '选课记录不存在'},
                status=status.HTTP_404_NOT_FOUND,
            )

    @action(detail=True, methods=['post'], url_path='import')
    def import_students(self, request, pk=None):
        """批量导入学生

        API: POST /api/v1/teaching/classes/{id}/import/
        """
        teaching_class = self.get_object()

        # 权限验证
        if not teaching_class.course.teachers.filter(id=request.user.id).exists():
            return Response(
                {'code': 2001, 'message': '无权限操作'},
                status=status.HTTP_403_FORBIDDEN,
            )

        if 'file' not in request.FILES:
            return Response(
                {'code': 3001, 'message': '请上传文件'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = ImportService.batch_import(
            request.FILES['file'],
            teaching_class,
        )

        if result['success']:
            return Response({'code': 0, 'message': '导入成功', 'data': result})
        else:
            return Response(
                {'code': 5005, 'message': result.get('error', '导入失败'), 'data': result},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=True, methods=['patch'], url_path='students/batch')
    def batch_update_roles(self, request, pk=None):
        """批量修改学生角色

        API: PATCH /api/v1/teaching/classes/{id}/students/batch/
        """
        teaching_class = self.get_object()

        # 权限验证
        if not teaching_class.course.teachers.filter(id=request.user.id).exists():
            return Response(
                {'code': 2001, 'message': '无权限操作'},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = BatchUpdateRoleSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'code': 3002, 'message': '参数错误', 'errors': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        student_ids = serializer.validated_data['student_ids']
        role = serializer.validated_data['role']

        updated_count = StudentEnrollment.objects.filter(
            teaching_class=teaching_class,
            id__in=student_ids,
        ).update(role=role)

        return Response({
            'code': 0,
            'message': '批量修改成功',
            'data': {'updated_count': updated_count},
        })

    @action(detail=False, methods=['get'], url_path='my-classes')
    def my_classes(self, request):
        """获取当前教师的班级列表"""
        user = request.user

        if user.user_type == 'teacher':
            classes = TeachingClass.objects.filter(
                course__teachers=user,
            ).select_related('course', 'course__semester')
        elif user.user_type == 'student':
            classes = TeachingClass.objects.filter(
                enrollments__student=user,
                enrollments__status='enrolled',
            ).select_related('course', 'course__semester')
        else:
            classes = TeachingClass.objects.none()

        serializer = TeachingClassSerializer(classes, many=True)
        return Response({
            'code': 0,
            'message': 'success',
            'data': serializer.data,
        })


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


class DownloadViewSet(viewsets.ViewSet):
    """下载视图集"""
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'], url_path='import-template')
    def import_template(self, request):
        """下载导入模板

        API: GET /api/v1/teaching/downloads/import-template/
        """
        template_path = os.path.join(
            settings.BASE_DIR,
            'templates/teaching/import_template.xlsx',
        )

        if not os.path.exists(template_path):
            return Response(
                {'code': 4004, 'message': '模板文件不存在'},
                status=status.HTTP_404_NOT_FOUND,
            )

        with open(template_path, 'rb') as f:
            response = HttpResponse(
                f.read(),
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            )
            response['Content-Disposition'] = 'attachment; filename="student_import_template.xlsx"'
            return response
