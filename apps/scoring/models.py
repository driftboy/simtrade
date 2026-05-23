from decimal import Decimal

from django.db import models
from django.conf import settings


class Experiment(models.Model):
    """实验 — 组织一轮贸易模拟"""

    class Status(models.TextChoices):
        DRAFT = 'draft', '草稿'
        ACTIVE = 'active', '进行中'
        COMPLETED = 'completed', '已完成'

    name = models.CharField('实验名称', max_length=200)
    description = models.TextField('描述', blank=True)
    status = models.CharField(
        '状态',
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    start_date = models.DateTimeField('开始时间')
    end_date = models.DateTimeField('结束时间', null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='创建者',
    )
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'scoring_experiments'
        verbose_name = '实验'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class ScoringMetric(models.Model):
    """评分指标注册表"""

    class Dimension(models.TextChoices):
        FINANCIAL = 'financial', '财务表现'
        ACCURACY = 'accuracy', '业务准确度'
        EFFICIENCY = 'efficiency', '操作效率'
        NEGOTIATION = 'negotiation', '谈判能力'

    name = models.CharField('指标标识', max_length=50, unique=True)
    display_name = models.CharField('显示名称', max_length=100)
    dimension = models.CharField(
        '所属维度',
        max_length=20,
        choices=Dimension.choices,
    )
    applicable_roles = models.ManyToManyField(
        'roles.TradeRole',
        verbose_name='适用角色',
        blank=True,
    )
    weight = models.DecimalField(
        '默认权重',
        max_digits=5,
        decimal_places=2,
        default=Decimal('10'),
    )
    calculation_method = models.CharField('计算方法', max_length=50)
    config = models.JSONField('计算配置', default=dict)
    is_active = models.BooleanField('是否启用', default=True)

    class Meta:
        db_table = 'scoring_metrics'
        verbose_name = '评分指标'
        verbose_name_plural = verbose_name
        ordering = ['dimension', 'name']

    def __str__(self):
        return f'{self.display_name} ({self.get_dimension_display()})'
