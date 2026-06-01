from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
import random
import string


class Semester(models.Model):
    """学期"""

    class Status(models.TextChoices):
        UPCOMING = 'upcoming', '未开始'
        ACTIVE = 'active', '进行中'
        ENDED = 'ended', '已结束'

    name = models.CharField('学期名称', max_length=100)
    code = models.CharField('学期代码', max_length=20, unique=True)
    start_date = models.DateField('开始日期')
    end_date = models.DateField('结束日期')
    is_active = models.BooleanField('当前学期', default=False)
    status = models.CharField(
        '状态', max_length=20,
        choices=Status.choices, default=Status.UPCOMING,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True,
        related_name='created_semesters',
    )
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'semesters'
        verbose_name = '学期'
        verbose_name_plural = '学期'
        ordering = ['-start_date']

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        if self.start_date and self.end_date and self.start_date >= self.end_date:
            raise ValidationError('结束日期必须晚于开始日期')
        if self.is_active:
            active_count = Semester.objects.filter(
                is_active=True,
            ).exclude(pk=self.pk).count()
            if active_count > 0:
                raise ValidationError('只能有一个激活的学期')


class Course(models.Model):
    """课程"""

    class Status(models.TextChoices):
        UPCOMING = 'upcoming', '未开始'
        ACTIVE = 'active', '进行中'
        ENDED = 'ended', '已结束'

    semester = models.ForeignKey(
        Semester, on_delete=models.PROTECT, related_name='courses',
    )
    name = models.CharField('课程名称', max_length=200)
    code = models.CharField('课程代码', max_length=20)
    teachers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='teaching_courses',
        verbose_name='授课教师', blank=True,
    )
    description = models.TextField('课程简介', blank=True)
    experiment_weight = models.DecimalField(
        '实验成绩权重', max_digits=5, decimal_places=2, default=0.60,
    )
    assignment_weight = models.DecimalField(
        '作业成绩权重', max_digits=5, decimal_places=2, default=0.40,
    )
    status = models.CharField(
        '状态', max_length=20,
        choices=Status.choices, default=Status.UPCOMING,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True,
        related_name='created_courses',
    )
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'courses'
        verbose_name = '课程'
        verbose_name_plural = '课程'
        ordering = ['-created_at']
        unique_together = [['semester', 'code']]

    def __str__(self):
        return f'{self.semester.name} - {self.name}'

    def clean(self):
        super().clean()
        if self.experiment_weight + self.assignment_weight != 1:
            raise ValidationError('实验权重与作业权重之和必须为 1')


class TeachingClass(models.Model):
    """教学班级"""

    class Status(models.TextChoices):
        UPCOMING = 'upcoming', '未开始'
        ACTIVE = 'active', '进行中'
        ENDED = 'ended', '已结束'

    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name='classes',
    )
    name = models.CharField('班级名称', max_length=100)
    capacity = models.IntegerField('最大人数', default=40)
    enrollment_code = models.CharField('选课码', max_length=20, unique=True)
    status = models.CharField(
        '状态', max_length=20,
        choices=Status.choices, default=Status.UPCOMING,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True,
        related_name='created_classes',
    )
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'teaching_classes'
        verbose_name = '教学班级'
        verbose_name_plural = '教学班级'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['course', '-created_at']),
            models.Index(fields=['created_by']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f'{self.course.semester.name} - {self.course.name} - {self.name}'

    def save(self, *args, **kwargs):
        if not self.enrollment_code:
            self.enrollment_code = self._generate_enrollment_code()
        super().save(*args, **kwargs)

    @staticmethod
    def _generate_enrollment_code():
        while True:
            code = ''.join(
                random.choices(string.ascii_uppercase + string.digits, k=8)
            )
            if not TeachingClass.objects.filter(enrollment_code=code).exists():
                return code


class StudentEnrollment(models.Model):
    """学生选课记录"""

    class Role(models.TextChoices):
        STUDENT = 'student', '学生'
        ASSISTANT = 'assistant', '助教'
        MONITOR = 'monitor', '班长'

    class Status(models.TextChoices):
        ENROLLED = 'enrolled', '已选课'
        DROPPED = 'dropped', '已退课'

    teaching_class = models.ForeignKey(
        TeachingClass, on_delete=models.CASCADE, related_name='enrollments',
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE, related_name='enrollments',
    )
    role = models.CharField(
        '角色', max_length=20,
        choices=Role.choices, default=Role.STUDENT,
    )
    status = models.CharField(
        '状态', max_length=20,
        choices=Status.choices, default=Status.ENROLLED,
    )
    enrolled_at = models.DateTimeField('选课时间', auto_now_add=True)
    dropped_at = models.DateTimeField('退课时间', null=True, blank=True)

    class Meta:
        db_table = 'student_enrollments'
        verbose_name = '学生选课'
        verbose_name_plural = '学生选课'
        ordering = ['-enrolled_at']
        unique_together = [['teaching_class', 'student']]

    def __str__(self):
        return f'{self.student.username} - {self.teaching_class.name}'


class ExperimentTemplate(models.Model):
    """实验模板"""

    name = models.CharField('模板名称', max_length=200)
    description = models.TextField('模板描述', blank=True)
    config = models.JSONField('预设配置', default=dict)
    is_public = models.BooleanField('是否公开', default=False)
    use_count = models.IntegerField('使用次数', default=0)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True,
        related_name='created_experiment_templates',
    )
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'experiment_templates'
        verbose_name = '实验模板'
        verbose_name_plural = '实验模板'
        ordering = ['-use_count', '-created_at']

    def __str__(self):
        return self.name


class ExperimentGroup(models.Model):
    """实验分组"""

    experiment = models.ForeignKey(
        'scoring.Experiment',
        on_delete=models.CASCADE, related_name='groups',
    )
    company = models.OneToOneField(
        'roles.Company',
        on_delete=models.CASCADE, related_name='experiment_group',
    )
    group_name = models.CharField('组名', max_length=100)

    class Meta:
        db_table = 'experiment_groups'
        verbose_name = '实验分组'
        verbose_name_plural = '实验分组'
        ordering = ['group_name']

    def __str__(self):
        return f'{self.experiment.name} - {self.group_name}'


class Assignment(models.Model):
    """作业/任务"""
    class AssignmentType(models.TextChoices):
        HOMEWORK = 'homework', '作业'
        QUIZ = 'quiz', '测验'
        REPORT = 'report', '报告'

    teaching_class = models.ForeignKey(
        TeachingClass, on_delete=models.CASCADE, related_name='assignments',
    )
    title = models.CharField('标题', max_length=200)
    description = models.TextField('要求说明', blank=True)
    assignment_type = models.CharField(
        '类型', max_length=20,
        choices=AssignmentType.choices, default=AssignmentType.HOMEWORK,
    )
    max_score = models.DecimalField('满分', max_digits=6, decimal_places=2, default=100)
    due_date = models.DateTimeField('截止时间')
    allow_late = models.BooleanField('允许迟交', default=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True,
        related_name='created_assignments',
    )
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'assignments'
        verbose_name = '作业'
        verbose_name_plural = '作业'
        ordering = ['-due_date']

    def __str__(self):
        return f'{self.teaching_class.name} - {self.title}'


class AssignmentSubmission(models.Model):
    """学生作业提交"""
    class Status(models.TextChoices):
        NOT_SUBMITTED = 'not_submitted', '未提交'
        SUBMITTED = 'submitted', '已提交'
        GRADED = 'graded', '已评分'
        LATE = 'late', '迟交'

    assignment = models.ForeignKey(
        Assignment, on_delete=models.CASCADE, related_name='submissions',
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE, related_name='assignment_submissions',
    )
    content = models.TextField('文字提交', blank=True)
    attachment = models.FileField('附件', upload_to='assignment_submissions/', blank=True)
    score = models.DecimalField('得分', max_digits=6, decimal_places=2, null=True, blank=True)
    feedback = models.TextField('教师反馈', blank=True)
    status = models.CharField(
        '状态', max_length=20,
        choices=Status.choices, default=Status.NOT_SUBMITTED,
    )
    submitted_at = models.DateTimeField('提交时间', null=True, blank=True)
    graded_at = models.DateTimeField('评分时间', null=True, blank=True)
    graded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name='graded_submissions',
    )
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'assignment_submissions'
        verbose_name = '作业提交'
        verbose_name_plural = '作业提交'
        ordering = ['-submitted_at']
        unique_together = [['assignment', 'student']]

    def __str__(self):
        return f'{self.student.username} - {self.assignment.title}'


class StudentProfile(models.Model):
    """学生扩展信息"""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='student_profile',
    )
    student_id = models.CharField('学号', max_length=50, unique=True)
    admin_class = models.CharField('行政班级', max_length=100, blank=True)
    grade = models.CharField('年级', max_length=20, blank=True)
    phone = models.CharField('手机号', max_length=20, blank=True)
    enrollment_year = models.IntegerField('入学年份', null=True, blank=True)

    class Meta:
        db_table = 'student_profiles'
        verbose_name = '学生档案'
        verbose_name_plural = '学生档案'

    def __str__(self):
        return f'{self.student_id} - {self.user.username}'
