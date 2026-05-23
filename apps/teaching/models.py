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
