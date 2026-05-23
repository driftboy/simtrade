from decimal import Decimal

from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator


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


class ScoreSheet(models.Model):
    """评分表 — 一次实验 + 一个学生 + 一个角色实例"""

    class Status(models.TextChoices):
        DRAFT = 'draft', '草稿'
        AUTO_SCORED = 'auto_scored', '已自动评分'
        TEACHER_REVIEWED = 'teacher_reviewed', '教师已审核'
        FINALIZED = 'finalized', '已定稿'

    experiment = models.ForeignKey(
        Experiment,
        on_delete=models.CASCADE,
        related_name='score_sheets',
        verbose_name='实验',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='score_sheets',
        verbose_name='学生',
    )
    user_company_role = models.ForeignKey(
        'roles.UserCompanyRole',
        on_delete=models.CASCADE,
        related_name='score_sheets',
        verbose_name='角色实例',
    )
    status = models.CharField(
        '状态',
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    auto_score = models.DecimalField(
        '自动评分',
        max_digits=6,
        decimal_places=2,
        default=Decimal('0'),
    )
    teacher_adjustment = models.DecimalField(
        '教师加减分',
        max_digits=6,
        decimal_places=2,
        default=Decimal('0'),
    )
    final_score = models.DecimalField(
        '最终分数',
        max_digits=6,
        decimal_places=2,
        default=Decimal('0'),
    )
    teacher_comment = models.TextField('教师评语', blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_sheets',
        verbose_name='审核教师',
    )
    reviewed_at = models.DateTimeField('审核时间', null=True, blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'scoring_score_sheets'
        verbose_name = '评分表'
        verbose_name_plural = verbose_name
        unique_together = [('experiment', 'user_company_role')]
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user} - {self.user_company_role} - {self.final_score}'

    def save(self, *args, **kwargs):
        # final_score 始终由 auto_score + teacher_adjustment 派生，确保一致性
        self.final_score = self.auto_score + self.teacher_adjustment
        super().save(*args, **kwargs)


class MetricScore(models.Model):
    """指标得分明细"""

    score_sheet = models.ForeignKey(
        ScoreSheet,
        on_delete=models.CASCADE,
        related_name='metric_scores',
        verbose_name='评分表',
    )
    metric = models.ForeignKey(
        ScoringMetric,
        on_delete=models.CASCADE,
        verbose_name='评分指标',
    )
    raw_value = models.DecimalField(
        '原始值',
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
    )
    score = models.DecimalField(
        '标准化得分',
        max_digits=6,
        decimal_places=2,
        default=Decimal('0'),
    )
    details = models.JSONField('计算细节', default=dict)

    class Meta:
        db_table = 'scoring_metric_scores'
        verbose_name = '指标得分'
        verbose_name_plural = verbose_name
        unique_together = [('score_sheet', 'metric')]

    def __str__(self):
        return f'{self.metric.display_name}: {self.score}'


class ExperimentScoringConfig(models.Model):
    """实验级权重配置 — 覆盖默认权重"""

    experiment = models.ForeignKey(
        Experiment,
        on_delete=models.CASCADE,
        related_name='scoring_configs',
        verbose_name='实验',
    )
    metric = models.ForeignKey(
        ScoringMetric,
        on_delete=models.CASCADE,
        verbose_name='指标',
    )
    custom_weight = models.DecimalField(
        '自定义权重',
        max_digits=5,
        decimal_places=2,
        default=Decimal('10'),
    )
    max_adjustment = models.DecimalField(
        '加减分上限',
        max_digits=5,
        decimal_places=2,
        default=Decimal('20'),
        validators=[MinValueValidator(Decimal('0'))],
    )

    class Meta:
        db_table = 'scoring_experiment_configs'
        verbose_name = '实验评分配置'
        verbose_name_plural = verbose_name
        unique_together = [('experiment', 'metric')]

    def __str__(self):
        return f'{self.experiment.name} - {self.metric.display_name}: {self.custom_weight}'
