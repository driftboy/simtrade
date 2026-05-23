from rest_framework import serializers
from apps.teaching.models import (
    Semester, Course, TeachingClass, StudentEnrollment,
    Assignment, AssignmentSubmission, ExperimentTemplate, ExperimentGroup,
)


class SemesterSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Semester
        fields = [
            'id', 'name', 'code', 'start_date', 'end_date',
            'is_active', 'status', 'status_display',
            'created_by', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by']


class CourseSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    semester_name = serializers.CharField(source='semester.name', read_only=True)
    teacher_names = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = [
            'id', 'semester', 'semester_name', 'name', 'code',
            'teachers', 'teacher_names', 'description',
            'experiment_weight', 'assignment_weight',
            'status', 'status_display',
            'created_by', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by']

    def get_teacher_names(self, obj):
        return list(obj.teachers.values_list('username', flat=True))


class TeachingClassSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    course_name = serializers.CharField(source='course.name', read_only=True)
    student_count = serializers.SerializerMethodField()

    class Meta:
        model = TeachingClass
        fields = [
            'id', 'course', 'course_name', 'name', 'capacity',
            'enrollment_code', 'status', 'status_display',
            'student_count', 'created_by', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'enrollment_code', 'created_at', 'updated_at', 'created_by']

    def get_student_count(self, obj):
        return obj.enrollments.filter(status='enrolled').count()


class StudentEnrollmentSerializer(serializers.ModelSerializer):
    student_username = serializers.CharField(source='student.username', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)

    class Meta:
        model = StudentEnrollment
        fields = [
            'id', 'teaching_class', 'student', 'student_username',
            'role', 'role_display', 'status', 'status_display',
            'enrolled_at', 'dropped_at',
        ]
        read_only_fields = ['id', 'enrolled_at', 'dropped_at']


class EnrollRequestSerializer(serializers.Serializer):
    enrollment_code = serializers.CharField(max_length=20)


class ExperimentTemplateSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model = ExperimentTemplate
        fields = ['id', 'name', 'description', 'config', 'is_public', 'use_count', 'created_by', 'created_by_name', 'created_at', 'updated_at']
        read_only_fields = ['id', 'use_count', 'created_at', 'updated_at', 'created_by']


class ExperimentGroupSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source='company.name', read_only=True)

    class Meta:
        model = ExperimentGroup
        fields = ['id', 'experiment', 'company', 'company_name', 'group_name']
        read_only_fields = ['id']


class AutoGroupSerializer(serializers.Serializer):
    group_size = serializers.IntegerField(min_value=2, max_value=10, default=5)


class AssignmentSerializer(serializers.ModelSerializer):
    assignment_type_display = serializers.CharField(source='get_assignment_type_display', read_only=True)
    class_name = serializers.CharField(source='teaching_class.name', read_only=True)
    submission_count = serializers.SerializerMethodField()

    class Meta:
        model = Assignment
        fields = ['id', 'teaching_class', 'class_name', 'title', 'description', 'assignment_type', 'assignment_type_display', 'max_score', 'due_date', 'allow_late', 'submission_count', 'created_by', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by']

    def get_submission_count(self, obj):
        return obj.submissions.filter(status__in=['submitted', 'graded']).count()


class AssignmentSubmissionSerializer(serializers.ModelSerializer):
    student_username = serializers.CharField(source='student.username', read_only=True)
    assignment_title = serializers.CharField(source='assignment.title', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = AssignmentSubmission
        fields = ['id', 'assignment', 'assignment_title', 'student', 'student_username', 'content', 'attachment', 'score', 'feedback', 'status', 'status_display', 'submitted_at', 'graded_at', 'graded_by', 'created_at', 'updated_at']
        read_only_fields = ['id', 'student', 'submitted_at', 'graded_at', 'graded_by', 'created_at', 'updated_at']


class GradeSerializer(serializers.Serializer):
    score = serializers.DecimalField(max_digits=6, decimal_places=2, min_value=0)
    feedback = serializers.CharField(required=False, allow_blank=True, max_length=1000)
