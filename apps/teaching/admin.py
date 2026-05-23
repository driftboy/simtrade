from django.contrib import admin
from apps.teaching.models import Semester, Course, TeachingClass, StudentEnrollment, Assignment, AssignmentSubmission, ExperimentTemplate, ExperimentGroup


class CourseTeacherInline(admin.TabularInline):
    model = Course.teachers.through
    extra = 1


@admin.register(Semester)
class SemesterAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'start_date', 'end_date', 'is_active', 'status']
    list_filter = ['is_active', 'status']
    search_fields = ['name', 'code']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'semester', 'status', 'experiment_weight', 'assignment_weight']
    list_filter = ['status', 'semester']
    search_fields = ['name', 'code']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [CourseTeacherInline]


@admin.register(TeachingClass)
class TeachingClassAdmin(admin.ModelAdmin):
    list_display = ['name', 'course', 'capacity', 'enrollment_code', 'status']
    list_filter = ['status', 'course']
    search_fields = ['name', 'enrollment_code']
    readonly_fields = ['enrollment_code', 'created_at', 'updated_at']


@admin.register(StudentEnrollment)
class StudentEnrollmentAdmin(admin.ModelAdmin):
    list_display = ['student', 'teaching_class', 'role', 'status', 'enrolled_at']
    list_filter = ['status', 'role']
    search_fields = ['student__username', 'teaching_class__name']
    readonly_fields = ['enrolled_at']


@admin.register(ExperimentTemplate)
class ExperimentTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_public', 'use_count', 'created_by']
    list_filter = ['is_public']
    search_fields = ['name']
    readonly_fields = ['use_count', 'created_at', 'updated_at']


@admin.register(ExperimentGroup)
class ExperimentGroupAdmin(admin.ModelAdmin):
    list_display = ['group_name', 'experiment', 'company']
    search_fields = ['group_name']


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ['title', 'teaching_class', 'assignment_type', 'max_score', 'due_date']
    list_filter = ['assignment_type', 'teaching_class']
    search_fields = ['title']


@admin.register(AssignmentSubmission)
class AssignmentSubmissionAdmin(admin.ModelAdmin):
    list_display = ['assignment', 'student', 'status', 'score', 'submitted_at']
    list_filter = ['status']
    search_fields = ['student__username', 'assignment__title']
    readonly_fields = ['submitted_at', 'graded_at']
