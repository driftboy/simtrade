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
