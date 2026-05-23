from rest_framework import serializers
from apps.teaching.models import (
    Semester, Course, TeachingClass, StudentEnrollment,
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
