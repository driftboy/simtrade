# 评分系统实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 为 SimTrade 实现混合模式评分系统，包含 10 个自动计算指标、教师加减分审核、实验级权重配置。

**架构：** 新建 `apps/scoring` Django app，包含 4 个模型（ScoringMetric/ScoreSheet/MetricScore/ExperimentScoringConfig）+ Experiment 辅助模型。服务层采用策略模式：ScoringService 调度 → MetricCalculator 子类计算 → ScoreAggregator 加权汇总。ViewSet + Router 提供 REST API。

**技术栈：** Django 4.x, Django REST Framework, SQLite(开发)/PostgreSQL(生产), DecimalField 精度计算

**规格文档：** `docs/superpowers/specs/2026-05-23-scoring-system-design.md`

---

## 文件结构

| 文件 | 职责 |
|------|------|
| `apps/scoring/__init__.py` | 空，标记 Python 包 |
| `apps/scoring/apps.py` | Django AppConfig |
| `apps/scoring/models.py` | Experiment, ScoringMetric, ScoreSheet, MetricScore, ExperimentScoringConfig |
| `apps/scoring/admin.py` | Admin 注册 |
| `apps/scoring/calculators.py` | MetricCalculator 基类 + 10 个指标计算器 |
| `apps/scoring/services.py` | ScoringService, ScoreAggregator |
| `apps/scoring/serializers.py` | DRF 序列化器 |
| `apps/scoring/views.py` | ViewSet |
| `apps/scoring/urls.py` | Router 注册 |
| `apps/scoring/management/__init__.py` | 空 |
| `apps/scoring/management/commands/__init__.py` | 空 |
| `apps/scoring/management/commands/init_scoring_metrics.py` | 初始化 10 个指标 |
| `apps/scoring/tests/__init__.py` | 空 |
| `apps/scoring/tests/test_models.py` | 模型测试 |
| `apps/scoring/tests/test_calculators.py` | 指标计算器测试 |
| `apps/scoring/tests/test_services.py` | 服务层测试 |
| `apps/scoring/tests/test_api.py` | API 测试 |

**修改的现有文件：**
- `simtrade/settings.py` — INSTALLED_APPS 添加 `apps.scoring`
- `simtrade/urls.py` — 添加 scoring URL include

---

### 任务 1：创建 scoring app 骨架

**文件：**
- 创建：`apps/scoring/__init__.py`
- 创建：`apps/scoring/apps.py`
- 修改：`simtrade/settings.py`

- [ ] **步骤 1：创建 app 目录结构**

```bash
mkdir -p apps/scoring/management/commands
mkdir -p apps/scoring/tests
touch apps/scoring/__init__.py
touch apps/scoring/management/__init__.py
touch apps/scoring/management/commands/__init__.py
touch apps/scoring/tests/__init__.py
```

- [ ] **步骤 2：创建 apps.py**

```python
from django.apps import AppConfig


class ScoringConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.scoring'
    verbose_name = '评分系统'
```

- [ ] **步骤 3：创建空的 models.py 占位**

```python
# apps/scoring/models.py — 评分系统模型
```

- [ ] **步骤 4：在 settings.py 中注册 app**

在 `simtrade/settings.py` 的 `INSTALLED_APPS` 列表末尾（`apps.roles` 之后）添加：

```python
'apps.scoring',
```

- [ ] **步骤 5：验证 app 可被发现**

运行：`python manage.py check`
预期：无错误

- [ ] **步骤 6：Commit**

```bash
git add apps/scoring/
git add simtrade/settings.py
git commit -m "feat(scoring): scaffold scoring app"
```

---

### 任务 2：创建 Experiment 模型

**背景：** 评分系统需要 Experiment 模型来组织一轮贸易模拟。代码库中尚不存在此模型。这是一个轻量模型，后续教学管理模块可扩展。

**文件：**
- 修改：`apps/scoring/models.py`
- 创建：`apps/scoring/tests/test_models.py`

- [ ] **步骤 1：编写 Experiment 模型测试**

```python
# apps/scoring/tests/test_models.py
from django.test import TestCase
from django.utils import timezone
from apps.scoring.models import Experiment


class ExperimentModelTest(TestCase):
    def test_create_experiment(self):
        exp = Experiment.objects.create(
            name='实验一：CIF 出口流程',
            description='模拟 CIF 术语下的完整出口流程',
            start_date=timezone.now(),
        )
        self.assertEqual(exp.status, 'draft')
        self.assertTrue(exp.name)

    def test_status_transitions(self):
        exp = Experiment.objects.create(
            name='测试实验',
            start_date=timezone.now(),
        )
        self.assertEqual(exp.status, 'draft')
        exp.status = 'active'
        exp.save()
        self.assertEqual(exp.status, 'active')
        exp.status = 'completed'
        exp.save()
        self.assertEqual(exp.status, 'completed')
```

- [ ] **步骤 2：运行测试验证失败**

运行：`python manage.py test apps.scoring.tests.test_models -v2`
预期：FAIL — `ImportError: cannot import name 'Experiment'`

- [ ] **步骤 3：编写 Experiment 模型**

在 `apps/scoring/models.py` 中：

```python
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
```

- [ ] **步骤 4：创建迁移并运行测试**

```bash
python manage.py makemigrations scoring
python manage.py test apps.scoring.tests.test_models -v2
```

预期：PASS

- [ ] **步骤 5：Commit**

```bash
git add apps/scoring/
git commit -m "feat(scoring): add Experiment model"
```

---

### 任务 3：创建 ScoringMetric 模型

**文件：**
- 修改：`apps/scoring/models.py`
- 修改：`apps/scoring/tests/test_models.py`
- 创建：`apps/scoring/admin.py`

- [ ] **步骤 1：编写 ScoringMetric 测试**

追加到 `apps/scoring/tests/test_models.py`：

```python
from apps.scoring.models import ScoringMetric
from apps.roles.models import TradeRole


class ScoringMetricModelTest(TestCase):
    def setUp(self):
        TradeRole.objects.get_or_create(
            code='exporter',
            defaults={'name': '出口商', 'description': '', 'sort_order': 1},
        )

    def test_create_metric(self):
        metric = ScoringMetric.objects.create(
            name='profit_margin',
            display_name='利润率',
            dimension='financial',
            calculation_method='profit_margin',
            weight=Decimal('20'),
            config={'threshold_high': 20, 'threshold_low': 0},
        )
        self.assertEqual(metric.dimension, 'financial')
        self.assertTrue(metric.is_active)
        self.assertEqual(metric.weight, Decimal('20'))

    def test_metric_role_assignment(self):
        metric = ScoringMetric.objects.create(
            name='profit_margin',
            display_name='利润率',
            dimension='financial',
            calculation_method='profit_margin',
            weight=Decimal('20'),
        )
        role = TradeRole.objects.get(code='exporter')
        metric.applicable_roles.add(role)
        self.assertEqual(metric.applicable_roles.count(), 1)
```

文件顶部添加 import：

```python
from decimal import Decimal
```

- [ ] **步骤 2：运行测试验证失败**

运行：`python manage.py test apps.scoring.tests.test_models::ScoringMetricModelTest -v2`
预期：FAIL — `ImportError: cannot import name 'ScoringMetric'`

- [ ] **步骤 3：编写 ScoringMetric 模型**

追加到 `apps/scoring/models.py`：

```python
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
```

- [ ] **步骤 4：创建迁移并运行测试**

```bash
python manage.py makemigrations scoring
python manage.py test apps.scoring.tests.test_models -v2
```

预期：PASS

- [ ] **步骤 5：创建 admin.py**

```python
from django.contrib import admin
from apps.scoring.models import Experiment, ScoringMetric


@admin.register(Experiment)
class ExperimentAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'status', 'start_date', 'end_date', 'created_at']
    list_filter = ['status']
    search_fields = ['name']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(ScoringMetric)
class ScoringMetricAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'display_name', 'dimension', 'weight', 'is_active']
    list_filter = ['dimension', 'is_active']
    search_fields = ['name', 'display_name']
    filter_horizontal = ['applicable_roles']
```

- [ ] **步骤 6：Commit**

```bash
git add apps/scoring/
git commit -m "feat(scoring): add ScoringMetric model with admin"
```

---

### 任务 4：创建 ScoreSheet / MetricScore / ExperimentScoringConfig 模型

**文件：**
- 修改：`apps/scoring/models.py`
- 修改：`apps/scoring/tests/test_models.py`
- 修改：`apps/scoring/admin.py`

- [ ] **步骤 1：编写模型测试**

追加到 `apps/scoring/tests/test_models.py`：

```python
from apps.scoring.models import ScoreSheet, MetricScore, ExperimentScoringConfig
from apps.users.models import User
from apps.roles.models import Company


class ScoreSheetModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='student1', password='test', user_type='student',
        )
        self.experiment = Experiment.objects.create(
            name='测试实验', start_date=timezone.now(),
        )
        role = TradeRole.objects.create(
            code='exporter', name='出口商', description='', sort_order=1,
        )
        self.company = Company.objects.create(
            name='测试公司', code='TEST01',
        )
        from apps.roles.models import UserCompanyRole
        self.ucr = UserCompanyRole.objects.create(
            user=self.user, company=self.company, role=role,
            status='active', is_active=True,
        )

    def test_create_score_sheet(self):
        sheet = ScoreSheet.objects.create(
            experiment=self.experiment,
            user=self.user,
            user_company_role=self.ucr,
        )
        self.assertEqual(sheet.status, 'draft')
        self.assertEqual(sheet.auto_score, Decimal('0'))

    def test_final_score_calculation(self):
        sheet = ScoreSheet.objects.create(
            experiment=self.experiment,
            user=self.user,
            user_company_role=self.ucr,
            auto_score=Decimal('85.5'),
            teacher_adjustment=Decimal('-5'),
        )
        self.assertEqual(sheet.final_score, Decimal('80.5'))

    def test_metric_score(self):
        sheet = ScoreSheet.objects.create(
            experiment=self.experiment,
            user=self.user,
            user_company_role=self.ucr,
        )
        metric = ScoringMetric.objects.create(
            name='profit_margin', display_name='利润率',
            dimension='financial', calculation_method='profit_margin',
            weight=Decimal('20'),
        )
        ms = MetricScore.objects.create(
            score_sheet=sheet, metric=metric,
            raw_value=Decimal('0.15'), score=Decimal('75'),
            details={'threshold': '20%'},
        )
        self.assertEqual(ms.score, Decimal('75'))
```

- [ ] **步骤 2：运行测试验证失败**

运行：`python manage.py test apps.scoring.tests.test_models::ScoreSheetModelTest -v2`
预期：FAIL — `ImportError: cannot import name 'ScoreSheet'`

- [ ] **步骤 3：编写三个模型**

追加到 `apps/scoring/models.py`：

```python
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
    )

    class Meta:
        db_table = 'scoring_experiment_configs'
        verbose_name = '实验评分配置'
        verbose_name_plural = verbose_name
        unique_together = [('experiment', 'metric')]

    def __str__(self):
        return f'{self.experiment.name} - {self.metric.display_name}: {self.custom_weight}'
```

- [ ] **步骤 4：更新 admin.py**

追加到 `apps/scoring/admin.py`：

```python
from apps.scoring.models import ScoreSheet, MetricScore, ExperimentScoringConfig


class MetricScoreInline(admin.TabularInline):
    model = MetricScore
    extra = 0
    readonly_fields = ['raw_value', 'score', 'details']


@admin.register(ScoreSheet)
class ScoreSheetAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'experiment', 'user', 'status',
        'auto_score', 'teacher_adjustment', 'final_score',
    ]
    list_filter = ['status', 'experiment']
    search_fields = ['user__username']
    readonly_fields = ['auto_score', 'final_score', 'created_at', 'updated_at']
    inlines = [MetricScoreInline]


@admin.register(ExperimentScoringConfig)
class ExperimentScoringConfigAdmin(admin.ModelAdmin):
    list_display = ['experiment', 'metric', 'custom_weight', 'max_adjustment']
    list_filter = ['experiment']
```

- [ ] **步骤 5：创建迁移并运行测试**

```bash
python manage.py makemigrations scoring
python manage.py test apps.scoring.tests.test_models -v2
```

预期：PASS

- [ ] **步骤 6：Commit**

```bash
git add apps/scoring/
git commit -m "feat(scoring): add ScoreSheet, MetricScore, ExperimentScoringConfig models"
```

---

### 任务 5：创建 init_scoring_metrics 管理命令

**文件：**
- 创建：`apps/scoring/management/commands/init_scoring_metrics.py`

- [ ] **步骤 1：编写管理命令**

```python
from decimal import Decimal
from django.core.management.base import BaseCommand
from apps.scoring.models import ScoringMetric
from apps.roles.models import TradeRole


class Command(BaseCommand):
    help = '初始化评分指标数据'

    def handle(self, *args, **options):
        roles = {r.code: r for r in TradeRole.objects.all()}

        metrics_data = [
            # 财务表现
            {
                'name': 'profit_margin',
                'display_name': '利润率',
                'dimension': 'financial',
                'calculation_method': 'profit_margin',
                'weight': Decimal('20'),
                'config': {'threshold_high': 20, 'threshold_low': 0},
                'roles': ['exporter', 'importer'],
            },
            {
                'name': 'cost_control',
                'display_name': '成本控制',
                'dimension': 'financial',
                'calculation_method': 'cost_control',
                'weight': Decimal('15'),
                'config': {'benchmark_deviation_pct': 5},
                'roles': ['exporter', 'importer'],
            },
            # 业务准确度
            {
                'name': 'document_accuracy',
                'display_name': '单证准确率',
                'dimension': 'accuracy',
                'calculation_method': 'document_accuracy',
                'weight': Decimal('15'),
                'config': {},
                'roles': ['exporter', 'importer'],
            },
            {
                'name': 'first_pass_rate',
                'display_name': '首次通过率',
                'dimension': 'accuracy',
                'calculation_method': 'first_pass_rate',
                'weight': Decimal('30'),
                'config': {},
                'roles': ['bank', 'customs', 'inspection', 'forex', 'tax'],
            },
            # 操作效率
            {
                'name': 'trade_cycle_time',
                'display_name': '交易周期',
                'dimension': 'efficiency',
                'calculation_method': 'trade_cycle_time',
                'weight': Decimal('15'),
                'config': {'benchmark_minutes': 1440, 'max_minutes': 2880},
                'roles': ['exporter', 'importer'],
            },
            {
                'name': 'document_turnaround',
                'display_name': '单证处理速度',
                'dimension': 'efficiency',
                'calculation_method': 'document_turnaround',
                'weight': Decimal('10'),
                'config': {'benchmark_minutes': 60, 'max_minutes': 120},
                'roles': ['exporter', 'importer'],
            },
            {
                'name': 'response_time',
                'display_name': '响应速度',
                'dimension': 'efficiency',
                'calculation_method': 'response_time',
                'weight': Decimal('10'),
                'config': {'benchmark_minutes': 30, 'max_minutes': 60},
                'roles': ['exporter', 'importer'],
            },
            {
                'name': 'processing_speed',
                'display_name': '处理速度',
                'dimension': 'efficiency',
                'calculation_method': 'processing_speed',
                'weight': Decimal('40'),
                'config': {'benchmark_minutes': 120, 'max_minutes': 240},
                'roles': ['factory', 'bank', 'customs', 'shipping', 'insurance', 'inspection', 'forex', 'tax'],
            },
            {
                'name': 'completion_rate',
                'display_name': '完成率',
                'dimension': 'efficiency',
                'calculation_method': 'completion_rate',
                'weight': Decimal('30'),
                'config': {},
                'roles': ['factory', 'shipping'],
            },
            # 谈判能力
            {
                'name': 'negotiation_efficiency',
                'display_name': '谈判效率',
                'dimension': 'negotiation',
                'calculation_method': 'negotiation_efficiency',
                'weight': Decimal('15'),
                'config': {'max_rounds': 5},
                'roles': ['exporter', 'importer'],
            },
        ]

        created_count = 0
        updated_count = 0
        for data in metrics_data:
            role_codes = data.pop('roles')
            metric, created = ScoringMetric.objects.update_or_create(
                name=data['name'],
                defaults=data,
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'[CREATE] {metric.display_name}'))
            else:
                updated_count += 1
                self.stdout.write(self.style.WARNING(f'[UPDATE] {metric.display_name}'))

            applicable_roles = [roles[c] for c in role_codes if c in roles]
            metric.applicable_roles.set(applicable_roles)

        self.stdout.write(
            self.style.SUCCESS(
                f'\n完成: 新建 {created_count} 个, 更新 {updated_count} 个指标'
            )
        )
```

- [ ] **步骤 2：运行命令验证**

```bash
python manage.py init_scoring_metrics
```

预期：输出 10 条 CREATE 消息

- [ ] **步骤 3：Commit**

```bash
git add apps/scoring/management/
git commit -m "feat(scoring): add init_scoring_metrics management command"
```

---

### 任务 6：实现 MetricCalculator 基类和 ProfitMarginCalculator

**文件：**
- 创建：`apps/scoring/calculators.py`
- 创建：`apps/scoring/tests/test_calculators.py`

- [ ] **步骤 1：编写 ProfitMarginCalculator 测试**

```python
# apps/scoring/tests/test_calculators.py
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from apps.scoring.calculators import MetricCalculator, ProfitMarginCalculator
from apps.scoring.models import Experiment, ScoringMetric
from apps.users.models import User
from apps.roles.models import TradeRole, Company, UserCompanyRole


class ProfitMarginCalculatorTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='student1', password='test', user_type='student',
        )
        self.experiment = Experiment.objects.create(
            name='测试实验', start_date=timezone.now(),
        )
        role = TradeRole.objects.create(
            code='exporter', name='出口商', description='', sort_order=1,
        )
        self.company = Company.objects.create(name='出口公司', code='EXP01')
        self.ucr = UserCompanyRole.objects.create(
            user=self.user, company=self.company, role=role,
            status='active', is_active=True,
        )
        self.metric = ScoringMetric.objects.create(
            name='profit_margin', display_name='利润率',
            dimension='financial', calculation_method='profit_margin',
            weight=Decimal('20'),
            config={'threshold_high': 20, 'threshold_low': 0},
        )

    def test_high_margin(self):
        """利润率 >= 20% → 100 分"""
        raw, score, details = ProfitMarginCalculator.calculate(
            self.ucr, self.experiment, self.metric,
            revenue=Decimal('12000'), cost=Decimal('9000'),
        )
        self.assertEqual(raw, Decimal('25.0000'))
        self.assertEqual(score, Decimal('100'))

    def test_zero_margin(self):
        """利润率 = 0% → 0 分"""
        raw, score, details = ProfitMarginCalculator.calculate(
            self.ucr, self.experiment, self.metric,
            revenue=Decimal('10000'), cost=Decimal('10000'),
        )
        self.assertEqual(raw, Decimal('0.0000'))
        self.assertEqual(score, Decimal('0'))

    def test_mid_margin(self):
        """利润率 10% → 50 分（线性插值）"""
        raw, score, details = ProfitMarginCalculator.calculate(
            self.ucr, self.experiment, self.metric,
            revenue=Decimal('11000'), cost=Decimal('10000'),
        )
        self.assertEqual(raw, Decimal('9.0909'))
        self.assertEqual(score, Decimal('50'))

    def test_negative_margin(self):
        """负利润 → 0 分"""
        raw, score, details = ProfitMarginCalculator.calculate(
            self.ucr, self.experiment, self.metric,
            revenue=Decimal('8000'), cost=Decimal('10000'),
        )
        self.assertEqual(score, Decimal('0'))

    def test_no_transactions(self):
        """无交易数据 → 原始值 None，分数 0"""
        raw, score, details = ProfitMarginCalculator.calculate(
            self.ucr, self.experiment, self.metric,
        )
        self.assertIsNone(raw)
        self.assertEqual(score, Decimal('0'))
```

- [ ] **步骤 2：运行测试验证失败**

运行：`python manage.py test apps.scoring.tests.test_calculators -v2`
预期：FAIL — `ImportError: cannot import name 'ProfitMarginCalculator'`

- [ ] **步骤 3：编写 MetricCalculator 基类和 ProfitMarginCalculator**

```python
# apps/scoring/calculators.py
from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Tuple, Optional


MetricResult = Tuple[Optional[Decimal], Decimal, dict]


class MetricCalculator(ABC):
    """指标计算器基类"""

    @staticmethod
    @abstractmethod
    def calculate(user_company_role, experiment, metric, **kwargs) -> MetricResult:
        """
        计算指标得分。

        返回: (raw_value, score, details)
        - raw_value: 原始值，无数据时为 None
        - score: 标准化得分 0-100
        - details: 计算细节字典
        """
        ...


def _standardize_ratio(value: Optional[Decimal]) -> Decimal:
    """比率型标准化：直接 × 100，无数据返回 0"""
    if value is None:
        return Decimal('0')
    return min(max(value * Decimal('100'), Decimal('0')), Decimal('100'))


def _standardize_time(
    minutes: Optional[Decimal],
    benchmark: Decimal,
    max_time: Decimal,
) -> Decimal:
    """时间型标准化：低于基准=100，基准到2倍=线性递减，超过2倍=0"""
    if minutes is None:
        return Decimal('0')
    if minutes <= benchmark:
        return Decimal('100')
    if minutes >= max_time:
        return Decimal('0')
    return ((max_time - minutes) / (max_time - benchmark) * Decimal('100')).quantize(Decimal('0.01'))


class ProfitMarginCalculator(MetricCalculator):
    """利润率计算器

    利润率 >= threshold_high → 100
    利润率 = threshold_low → 0
    中间线性插值
    负利润 → 0
    """

    @staticmethod
    def calculate(user_company_role, experiment, metric, **kwargs) -> MetricResult:
        revenue = kwargs.get('revenue')
        cost = kwargs.get('cost')

        if revenue is None or cost is None or revenue == 0:
            return None, Decimal('0'), {'reason': 'no_data'}

        margin = ((revenue - cost) / revenue * Decimal('100')).quantize(Decimal('0.0001'))

        config = metric.config or {}
        threshold_high = Decimal(str(config.get('threshold_high', 20)))
        threshold_low = Decimal(str(config.get('threshold_low', 0)))

        if margin <= threshold_low:
            score = Decimal('0')
        elif margin >= threshold_high:
            score = Decimal('100')
        else:
            score = (
                (margin - threshold_low) / (threshold_high - threshold_low) * Decimal('100')
            ).quantize(Decimal('0.01'))

        return margin, score, {'revenue': str(revenue), 'cost': str(cost)}


# 注册表：calculation_method → Calculator 类
CALCULATOR_REGISTRY: dict[str, type[MetricCalculator]] = {
    'profit_margin': ProfitMarginCalculator,
}


def get_calculator(method: str) -> type[MetricCalculator]:
    cls = CALCULATOR_REGISTRY.get(method)
    if cls is None:
        raise ValueError(f'未注册的计算方法: {method}')
    return cls
```

- [ ] **步骤 4：运行测试验证通过**

运行：`python manage.py test apps.scoring.tests.test_calculators -v2`
预期：PASS

- [ ] **步骤 5：Commit**

```bash
git add apps/scoring/calculators.py apps/scoring/tests/test_calculators.py
git commit -m "feat(scoring): add MetricCalculator base and ProfitMarginCalculator"
```

---

### 任务 7：实现 CostControlCalculator 和 DocumentAccuracyCalculator

**文件：**
- 修改：`apps/scoring/calculators.py`
- 修改：`apps/scoring/tests/test_calculators.py`

- [ ] **步骤 1：编写测试**

追加到 `apps/scoring/tests/test_calculators.py`：

```python
from apps.scoring.calculators import CostControlCalculator, DocumentAccuracyCalculator


class CostControlCalculatorTest(TestCase):
    def setUp(self):
        self.metric = ScoringMetric.objects.create(
            name='cost_control', display_name='成本控制',
            dimension='financial', calculation_method='cost_control',
            weight=Decimal('15'),
            config={'benchmark_deviation_pct': 5},
        )
        self.ucr = object()
        self.experiment = object()

    def test_within_benchmark(self):
        """偏差 <= 5% → 100"""
        raw, score, _ = CostControlCalculator.calculate(
            self.ucr, self.experiment, self.metric,
            actual_cost=Decimal('10000'), benchmark_cost=Decimal('9800'),
        )
        self.assertEqual(score, Decimal('100'))

    def test_moderate_deviation(self):
        """偏差 20% → 60"""
        raw, score, _ = CostControlCalculator.calculate(
            self.ucr, self.experiment, self.metric,
            actual_cost=Decimal('12000'), benchmark_cost=Decimal('10000'),
        )
        self.assertEqual(score, Decimal('60'))

    def test_extreme_deviation(self):
        """偏差 >= 50% → 0"""
        raw, score, _ = CostControlCalculator.calculate(
            self.ucr, self.experiment, self.metric,
            actual_cost=Decimal('16000'), benchmark_cost=Decimal('10000'),
        )
        self.assertEqual(score, Decimal('0'))

    def test_no_data(self):
        raw, score, _ = CostControlCalculator.calculate(
            self.ucr, self.experiment, self.metric,
        )
        self.assertIsNone(raw)
        self.assertEqual(score, Decimal('0'))


class DocumentAccuracyCalculatorTest(TestCase):
    def setUp(self):
        self.metric = ScoringMetric.objects.create(
            name='document_accuracy', display_name='单证准确率',
            dimension='accuracy', calculation_method='document_accuracy',
            weight=Decimal('15'),
        )
        self.ucr = object()
        self.experiment = object()

    def test_perfect_accuracy(self):
        """0 错误 / 10 提交 → 100"""
        raw, score, _ = DocumentAccuracyCalculator.calculate(
            self.ucr, self.experiment, self.metric,
            total_submissions=10, error_count=0,
        )
        self.assertEqual(raw, Decimal('1.0000'))
        self.assertEqual(score, Decimal('100'))

    def test_half_accuracy(self):
        """5 错误 / 10 提交 → 50"""
        raw, score, _ = DocumentAccuracyCalculator.calculate(
            self.ucr, self.experiment, self.metric,
            total_submissions=10, error_count=5,
        )
        self.assertEqual(score, Decimal('50'))

    def test_no_submissions(self):
        raw, score, _ = DocumentAccuracyCalculator.calculate(
            self.ucr, self.experiment, self.metric,
        )
        self.assertIsNone(raw)
        self.assertEqual(score, Decimal('0'))
```

- [ ] **步骤 2：运行测试验证失败**

运行：`python manage.py test apps.scoring.tests.test_calculators::CostControlCalculatorTest -v2`
预期：FAIL — `ImportError: cannot import name 'CostControlCalculator'`

- [ ] **步骤 3：实现两个计算器**

追加到 `apps/scoring/calculators.py`（`CALCULATOR_REGISTRY` 之前）：

```python
class CostControlCalculator(MetricCalculator):
    """成本控制计算器

    偏差 <= benchmark_deviation_pct → 100
    每增加 5% 扣 10 分
    偏差 >= 50% → 0
    """

    @staticmethod
    def calculate(user_company_role, experiment, metric, **kwargs) -> MetricResult:
        actual = kwargs.get('actual_cost')
        benchmark = kwargs.get('benchmark_cost')

        if actual is None or benchmark is None or benchmark == 0:
            return None, Decimal('0'), {'reason': 'no_data'}

        deviation_pct = ((actual - benchmark) / benchmark * Decimal('100')).quantize(Decimal('0.01'))
        config = metric.config or {}
        benchmark_dev = Decimal(str(config.get('benchmark_deviation_pct', 5)))

        if deviation_pct <= benchmark_dev:
            score = Decimal('100')
        elif deviation_pct >= Decimal('50'):
            score = Decimal('0')
        else:
            excess = deviation_pct - benchmark_dev
            deduction = (excess / Decimal('5') * Decimal('10')).quantize(Decimal('0.01'))
            score = max(Decimal('100') - deduction, Decimal('0'))

        return deviation_pct, score, {
            'actual_cost': str(actual),
            'benchmark_cost': str(benchmark),
        }


class DocumentAccuracyCalculator(MetricCalculator):
    """单证准确率计算器

    score = (1 - error_count / total_submissions) × 100
    """

    @staticmethod
    def calculate(user_company_role, experiment, metric, **kwargs) -> MetricResult:
        total = kwargs.get('total_submissions')
        errors = kwargs.get('error_count', 0)

        if not total:
            return None, Decimal('0'), {'reason': 'no_data'}

        accuracy = (Decimal('1') - Decimal(str(errors)) / Decimal(str(total)))
        score = _standardize_ratio(accuracy)

        return accuracy.quantize(Decimal('0.0001')), score, {
            'total_submissions': total,
            'error_count': errors,
        }
```

更新 `CALCULATOR_REGISTRY`：

```python
CALCULATOR_REGISTRY: dict[str, type[MetricCalculator]] = {
    'profit_margin': ProfitMarginCalculator,
    'cost_control': CostControlCalculator,
    'document_accuracy': DocumentAccuracyCalculator,
}
```

- [ ] **步骤 4：运行测试验证通过**

运行：`python manage.py test apps.scoring.tests.test_calculators -v2`
预期：PASS

- [ ] **步骤 5：Commit**

```bash
git add apps/scoring/calculators.py apps/scoring/tests/test_calculators.py
git commit -m "feat(scoring): add CostControlCalculator and DocumentAccuracyCalculator"
```

---

### 任务 8：实现 FirstPassRateCalculator 和 CompletionRateCalculator

**文件：**
- 修改：`apps/scoring/calculators.py`
- 修改：`apps/scoring/tests/test_calculators.py`

- [ ] **步骤 1：编写测试**

追加到 `apps/scoring/tests/test_calculators.py`：

```python
from apps.scoring.calculators import FirstPassRateCalculator, CompletionRateCalculator


class FirstPassRateCalculatorTest(TestCase):
    def setUp(self):
        self.metric = ScoringMetric.objects.create(
            name='first_pass_rate', display_name='首次通过率',
            dimension='accuracy', calculation_method='first_pass_rate',
            weight=Decimal('30'),
        )
        self.ucr = object()
        self.experiment = object()

    def test_all_pass(self):
        raw, score, _ = FirstPassRateCalculator.calculate(
            self.ucr, self.experiment, self.metric,
            total_operations=8, first_pass_count=8,
        )
        self.assertEqual(score, Decimal('100'))

    def test_half_pass(self):
        raw, score, _ = FirstPassRateCalculator.calculate(
            self.ucr, self.experiment, self.metric,
            total_operations=8, first_pass_count=4,
        )
        self.assertEqual(score, Decimal('50'))

    def test_no_data(self):
        raw, score, _ = FirstPassRateCalculator.calculate(
            self.ucr, self.experiment, self.metric,
        )
        self.assertIsNone(raw)
        self.assertEqual(score, Decimal('0'))


class CompletionRateCalculatorTest(TestCase):
    def setUp(self):
        self.metric = ScoringMetric.objects.create(
            name='completion_rate', display_name='完成率',
            dimension='efficiency', calculation_method='completion_rate',
            weight=Decimal('30'),
        )
        self.ucr = object()
        self.experiment = object()

    def test_all_completed(self):
        raw, score, _ = CompletionRateCalculator.calculate(
            self.ucr, self.experiment, self.metric,
            total_assigned=10, completed_count=10,
        )
        self.assertEqual(score, Decimal('100'))

    def test_partial(self):
        raw, score, _ = CompletionRateCalculator.calculate(
            self.ucr, self.experiment, self.metric,
            total_assigned=10, completed_count=7,
        )
        self.assertEqual(score, Decimal('70'))

    def test_no_data(self):
        raw, score, _ = CompletionRateCalculator.calculate(
            self.ucr, self.experiment, self.metric,
        )
        self.assertIsNone(raw)
        self.assertEqual(score, Decimal('0'))
```

- [ ] **步骤 2：运行测试验证失败**

运行：`python manage.py test apps.scoring.tests.test_calculators::FirstPassRateCalculatorTest -v2`
预期：FAIL

- [ ] **步骤 3：实现两个计算器**

追加到 `apps/scoring/calculators.py`（`CALCULATOR_REGISTRY` 之前）：

```python
class FirstPassRateCalculator(MetricCalculator):
    """首次通过率计算器

    score = first_pass_count / total_operations × 100
    """

    @staticmethod
    def calculate(user_company_role, experiment, metric, **kwargs) -> MetricResult:
        total = kwargs.get('total_operations')
        passed = kwargs.get('first_pass_count', 0)

        if not total:
            return None, Decimal('0'), {'reason': 'no_data'}

        rate = Decimal(str(passed)) / Decimal(str(total))
        score = _standardize_ratio(rate)

        return rate.quantize(Decimal('0.0001')), score, {
            'total_operations': total,
            'first_pass_count': passed,
        }


class CompletionRateCalculator(MetricCalculator):
    """完成率计算器

    score = completed_count / total_assigned × 100
    """

    @staticmethod
    def calculate(user_company_role, experiment, metric, **kwargs) -> MetricResult:
        total = kwargs.get('total_assigned')
        completed = kwargs.get('completed_count', 0)

        if not total:
            return None, Decimal('0'), {'reason': 'no_data'}

        rate = Decimal(str(completed)) / Decimal(str(total))
        score = _standardize_ratio(rate)

        return rate.quantize(Decimal('0.0001')), score, {
            'total_assigned': total,
            'completed_count': completed,
        }
```

更新 `CALCULATOR_REGISTRY`：

```python
CALCULATOR_REGISTRY: dict[str, type[MetricCalculator]] = {
    'profit_margin': ProfitMarginCalculator,
    'cost_control': CostControlCalculator,
    'document_accuracy': DocumentAccuracyCalculator,
    'first_pass_rate': FirstPassRateCalculator,
    'completion_rate': CompletionRateCalculator,
}
```

- [ ] **步骤 4：运行测试验证通过**

运行：`python manage.py test apps.scoring.tests.test_calculators -v2`
预期：PASS

- [ ] **步骤 5：Commit**

```bash
git add apps/scoring/calculators.py apps/scoring/tests/test_calculators.py
git commit -m "feat(scoring): add FirstPassRateCalculator and CompletionRateCalculator"
```

---

### 任务 9：实现时间类计算器

**文件：**
- 修改：`apps/scoring/calculators.py`
- 修改：`apps/scoring/tests/test_calculators.py`

这个任务实现 4 个时间类计算器：ProcessingSpeedCalculator、TradeCycleTimeCalculator、DocumentTurnaroundCalculator、ResponseTimeCalculator。它们共享 `_standardize_time` 辅助函数。

- [ ] **步骤 1：编写测试**

追加到 `apps/scoring/tests/test_calculators.py`：

```python
from apps.scoring.calculators import (
    ProcessingSpeedCalculator,
    TradeCycleTimeCalculator,
    DocumentTurnaroundCalculator,
    ResponseTimeCalculator,
)


class ProcessingSpeedCalculatorTest(TestCase):
    def setUp(self):
        self.metric = ScoringMetric.objects.create(
            name='processing_speed', display_name='处理速度',
            dimension='efficiency', calculation_method='processing_speed',
            weight=Decimal('40'),
            config={'benchmark_minutes': 120, 'max_minutes': 240},
        )
        self.ucr = object()
        self.experiment = object()

    def test_within_benchmark(self):
        raw, score, _ = ProcessingSpeedCalculator.calculate(
            self.ucr, self.experiment, self.metric,
            elapsed_minutes=Decimal('60'),
        )
        self.assertEqual(score, Decimal('100'))

    def test_at_max(self):
        raw, score, _ = ProcessingSpeedCalculator.calculate(
            self.ucr, self.experiment, self.metric,
            elapsed_minutes=Decimal('240'),
        )
        self.assertEqual(score, Decimal('0'))

    def test_midpoint(self):
        raw, score, _ = ProcessingSpeedCalculator.calculate(
            self.ucr, self.experiment, self.metric,
            elapsed_minutes=Decimal('180'),
        )
        self.assertEqual(score, Decimal('50'))

    def test_no_data(self):
        raw, score, _ = ProcessingSpeedCalculator.calculate(
            self.ucr, self.experiment, self.metric,
        )
        self.assertIsNone(raw)
        self.assertEqual(score, Decimal('0'))


class TradeCycleTimeCalculatorTest(TestCase):
    def setUp(self):
        self.metric = ScoringMetric.objects.create(
            name='trade_cycle_time', display_name='交易周期',
            dimension='efficiency', calculation_method='trade_cycle_time',
            weight=Decimal('15'),
            config={'benchmark_minutes': 1440, 'max_minutes': 2880},
        )
        self.ucr = object()
        self.experiment = object()

    def test_fast_completion(self):
        raw, score, _ = TradeCycleTimeCalculator.calculate(
            self.ucr, self.experiment, self.metric,
            elapsed_minutes=Decimal('720'),
        )
        self.assertEqual(score, Decimal('100'))

    def test_slow(self):
        raw, score, _ = TradeCycleTimeCalculator.calculate(
            self.ucr, self.experiment, self.metric,
            elapsed_minutes=Decimal('2160'),
        )
        self.assertEqual(score, Decimal('50'))

    def test_no_data(self):
        raw, score, _ = TradeCycleTimeCalculator.calculate(
            self.ucr, self.experiment, self.metric,
        )
        self.assertIsNone(raw)
        self.assertEqual(score, Decimal('0'))
```

DocumentTurnaroundCalculator 和 ResponseTimeCalculator 使用相同的 `_standardize_time`，共享 ProcessingSpeedCalculator 相同的测试模式，只是 config 中的基准值不同。测试结构与上面相同，这里不再赘述。

- [ ] **步骤 2：运行测试验证失败**

运行：`python manage.py test apps.scoring.tests.test_calculators::ProcessingSpeedCalculatorTest -v2`
预期：FAIL

- [ ] **步骤 3：实现 4 个时间类计算器**

追加到 `apps/scoring/calculators.py`（`CALCULATOR_REGISTRY` 之前）：

```python
class _TimeBasedCalculator(MetricCalculator):
    """时间类计算器基类 — 所有子类共享 _standardize_time"""

    @staticmethod
    def calculate(user_company_role, experiment, metric, **kwargs) -> MetricResult:
        elapsed = kwargs.get('elapsed_minutes')
        if elapsed is None:
            return None, Decimal('0'), {'reason': 'no_data'}

        config = metric.config or {}
        benchmark = Decimal(str(config.get('benchmark_minutes', 120)))
        max_time = Decimal(str(config.get('max_minutes', benchmark * 2)))

        score = _standardize_time(elapsed, benchmark, max_time)
        return elapsed, score, {
            'elapsed_minutes': str(elapsed),
            'benchmark_minutes': str(benchmark),
        }


class ProcessingSpeedCalculator(_TimeBasedCalculator):
    """处理速度 — 辅助角色"""
    pass


class TradeCycleTimeCalculator(_TimeBasedCalculator):
    """交易周期 — 出口商/进口商"""
    pass


class DocumentTurnaroundCalculator(_TimeBasedCalculator):
    """单证处理速度 — 出口商/进口商"""
    pass


class ResponseTimeCalculator(_TimeBasedCalculator):
    """响应速度 — 出口商/进口商"""
    pass
```

更新 `CALCULATOR_REGISTRY`：

```python
CALCULATOR_REGISTRY: dict[str, type[MetricCalculator]] = {
    'profit_margin': ProfitMarginCalculator,
    'cost_control': CostControlCalculator,
    'document_accuracy': DocumentAccuracyCalculator,
    'first_pass_rate': FirstPassRateCalculator,
    'completion_rate': CompletionRateCalculator,
    'processing_speed': ProcessingSpeedCalculator,
    'trade_cycle_time': TradeCycleTimeCalculator,
    'document_turnaround': DocumentTurnaroundCalculator,
    'response_time': ResponseTimeCalculator,
}
```

- [ ] **步骤 4：运行测试验证通过**

运行：`python manage.py test apps.scoring.tests.test_calculators -v2`
预期：PASS

- [ ] **步骤 5：Commit**

```bash
git add apps/scoring/calculators.py apps/scoring/tests/test_calculators.py
git commit -m "feat(scoring): add time-based calculators (processing_speed, trade_cycle, document_turnaround, response_time)"
```

---

### 任务 10：实现 NegotiationEfficiencyCalculator

**文件：**
- 修改：`apps/scoring/calculators.py`
- 修改：`apps/scoring/tests/test_calculators.py`

- [ ] **步骤 1：编写测试**

追加到 `apps/scoring/tests/test_calculators.py`：

```python
from apps.scoring.calculators import NegotiationEfficiencyCalculator


class NegotiationEfficiencyCalculatorTest(TestCase):
    def setUp(self):
        self.metric = ScoringMetric.objects.create(
            name='negotiation_efficiency', display_name='谈判效率',
            dimension='negotiation', calculation_method='negotiation_efficiency',
            weight=Decimal('15'),
            config={'max_rounds': 5},
        )
        self.ucr = object()
        self.experiment = object()

    def test_one_round_good_price(self):
        """1 轮成交 + 价格偏差 < 5% → 高分"""
        raw, score, _ = NegotiationEfficiencyCalculator.calculate(
            self.ucr, self.experiment, self.metric,
            rounds=1, initial_price=Decimal('100'), final_price=Decimal('98'),
        )
        self.assertGreaterEqual(score, Decimal('80'))

    def test_many_rounds_good_price(self):
        """5 轮成交 + 价格偏差 < 10% → 中等分数"""
        raw, score, _ = NegotiationEfficiencyCalculator.calculate(
            self.ucr, self.experiment, self.metric,
            rounds=5, initial_price=Decimal('100'), final_price=Decimal('92'),
        )
        self.assertGreaterEqual(score, Decimal('40'))
        self.assertLess(score, Decimal('80'))

    def test_one_round_bad_price(self):
        """1 轮成交 + 价格偏差 > 20% → 低分（快速但盲目接受）"""
        raw, score, _ = NegotiationEfficiencyCalculator.calculate(
            self.ucr, self.experiment, self.metric,
            rounds=1, initial_price=Decimal('100'), final_price=Decimal('70'),
        )
        self.assertLess(score, Decimal('60'))

    def test_no_deal(self):
        """无成交 → 0 分"""
        raw, score, _ = NegotiationEfficiencyCalculator.calculate(
            self.ucr, self.experiment, self.metric,
        )
        self.assertIsNone(raw)
        self.assertEqual(score, Decimal('0'))
```

- [ ] **步骤 2：运行测试验证失败**

运行：`python manage.py test apps.scoring.tests.test_calculators::NegotiationEfficiencyCalculatorTest -v2`
预期：FAIL

- [ ] **步骤 3：实现 NegotiationEfficiencyCalculator**

追加到 `apps/scoring/calculators.py`（`CALCULATOR_REGISTRY` 之前）：

```python
class NegotiationEfficiencyCalculator(MetricCalculator):
    """谈判效率计算器

    综合评估谈判轮次和最终成交价偏差：
    - 轮次效率分 = (max_rounds - rounds + 1) / max_rounds × 60
    - 价格效率分 = max(0, (1 - price_deviation / 0.3) × 40)
    - 总分 = 轮次效率分 + 价格效率分
    """

    @staticmethod
    def calculate(user_company_role, experiment, metric, **kwargs) -> MetricResult:
        rounds = kwargs.get('rounds')
        initial_price = kwargs.get('initial_price')
        final_price = kwargs.get('final_price')

        if rounds is None or initial_price is None or final_price is None:
            return None, Decimal('0'), {'reason': 'no_data'}

        config = metric.config or {}
        max_rounds = Decimal(str(config.get('max_rounds', 5)))

        # 轮次效率（满分 60）
        rounds_score = (
            (max_rounds - Decimal(str(min(rounds, max_rounds))) + Decimal('1'))
            / max_rounds * Decimal('60')
        ).quantize(Decimal('0.01'))

        # 价格偏差效率（满分 40）
        if initial_price != 0:
            deviation = abs(final_price - initial_price) / initial_price
        else:
            deviation = Decimal('0')

        price_score = max(Decimal('0'), (Decimal('1') - deviation / Decimal('0.3')) * Decimal('40'))
        price_score = price_score.quantize(Decimal('0.01'))

        total_score = min(rounds_score + price_score, Decimal('100'))

        return rounds, total_score, {
            'rounds': rounds,
            'initial_price': str(initial_price),
            'final_price': str(final_price),
            'price_deviation': str(deviation.quantize(Decimal('0.0001'))),
            'rounds_score': str(rounds_score),
            'price_score': str(price_score),
        }
```

更新 `CALCULATOR_REGISTRY`：

```python
    'negotiation_efficiency': NegotiationEfficiencyCalculator,
```

- [ ] **步骤 4：运行测试验证通过**

运行：`python manage.py test apps.scoring.tests.test_calculators -v2`
预期：PASS

- [ ] **步骤 5：Commit**

```bash
git add apps/scoring/calculators.py apps/scoring/tests/test_calculators.py
git commit -m "feat(scoring): add NegotiationEfficiencyCalculator"
```

---

### 任务 11：实现 ScoreAggregator

**文件：**
- 创建：`apps/scoring/services.py`
- 创建：`apps/scoring/tests/test_services.py`

- [ ] **步骤 1：编写 ScoreAggregator 测试**

```python
# apps/scoring/tests/test_services.py
from decimal import Decimal
from django.test import TestCase
from apps.scoring.services import ScoreAggregator
from apps.scoring.models import ScoringMetric


class ScoreAggregatorTest(TestCase):
    def setUp(self):
        self.metric1 = ScoringMetric.objects.create(
            name='m1', display_name='指标1',
            dimension='financial', calculation_method='profit_margin',
            weight=Decimal('20'),
        )
        self.metric2 = ScoringMetric.objects.create(
            name='m2', display_name='指标2',
            dimension='accuracy', calculation_method='document_accuracy',
            weight=Decimal('30'),
        )
        self.metric3 = ScoringMetric.objects.create(
            name='m3', display_name='指标3',
            dimension='efficiency', calculation_method='processing_speed',
            weight=Decimal('50'),
        )

    def test_weighted_sum(self):
        """正常加权求和: 80×20 + 60×30 + 100×50 = 8400 / 100 = 84"""
        scores = [
            (self.metric1, Decimal('80')),
            (self.metric2, Decimal('60')),
            (self.metric3, Decimal('100')),
        ]
        result = ScoreAggregator.aggregate(scores, [])
        self.assertEqual(result, Decimal('84'))

    def test_custom_weights(self):
        """自定义权重覆盖默认权重"""
        from apps.scoring.models import Experiment, ExperimentScoringConfig
        from django.utils import timezone

        exp = Experiment.objects.create(name='test', start_date=timezone.now())
        ExperimentScoringConfig.objects.create(
            experiment=exp, metric=self.metric1, custom_weight=Decimal('50'),
        )
        ExperimentScoringConfig.objects.create(
            experiment=exp, metric=self.metric2, custom_weight=Decimal('50'),
        )

        scores = [
            (self.metric1, Decimal('80')),
            (self.metric2, Decimal('60')),
        ]
        configs = list(ExperimentScoringConfig.objects.filter(experiment=exp))
        result = ScoreAggregator.aggregate(scores, configs)
        # (80×50 + 60×50) / 100 = 70
        self.assertEqual(result, Decimal('70'))

    def test_zero_weight_redistribution(self):
        """无数据指标权重归零，剩余等比重分配"""
        scores = [
            (self.metric1, Decimal('80')),
            # metric2 无数据，不传入
            (self.metric3, Decimal('100')),
        ]
        # 原始总权重 = 20+30+50=100，metric2 排除后 = 20+50=70
        # metric1: 80 × (20/70) = 22.857
        # metric3: 100 × (50/70) = 71.429
        # total = 94.29
        result = ScoreAggregator.aggregate(scores, [])
        self.assertGreater(result, Decimal('90'))

    def test_all_no_data(self):
        """所有指标无数据 → 0"""
        result = ScoreAggregator.aggregate([], [])
        self.assertEqual(result, Decimal('0'))
```

- [ ] **步骤 2：运行测试验证失败**

运行：`python manage.py test apps.scoring.tests.test_services -v2`
预期：FAIL — `ImportError: cannot import name 'ScoreAggregator'`

- [ ] **步骤 3：实现 ScoreAggregator**

```python
# apps/scoring/services.py
from decimal import Decimal
from apps.scoring.models import ScoringMetric, ExperimentScoringConfig


class ScoreAggregator:
    """评分汇总器 — 加权求和"""

    @staticmethod
    def aggregate(
        scores: list[tuple[ScoringMetric, Decimal]],
        configs: list[ExperimentScoringConfig],
    ) -> Decimal:
        """
        加权汇总指标得分。

        scores: [(metric, score), ...] — 有数据的指标
        configs: 实验级配置（可为空列表，表示使用默认权重）
        """
        if not scores:
            return Decimal('0')

        config_map: dict[int, Decimal] = {}
        for cfg in configs:
            config_map[cfg.metric_id] = cfg.custom_weight

        weighted_sum = Decimal('0')
        total_weight = Decimal('0')

        for metric, score in scores:
            weight = config_map.get(metric.id, metric.weight)
            weighted_sum += score * weight
            total_weight += weight

        if total_weight == 0:
            return Decimal('0')

        return (weighted_sum / total_weight).quantize(Decimal('0.01'))
```

- [ ] **步骤 4：运行测试验证通过**

运行：`python manage test apps.scoring.tests.test_services -v2`
预期：PASS

- [ ] **步骤 5：Commit**

```bash
git add apps/scoring/services.py apps/scoring/tests/test_services.py
git commit -m "feat(scoring): add ScoreAggregator with weighted sum and redistribution"
```

---

### 任务 12：实现 ScoringService

**文件：**
- 修改：`apps/scoring/services.py`
- 修改：`apps/scoring/tests/test_services.py`

- [ ] **步骤 1：编写 ScoringService 测试**

追加到 `apps/scoring/tests/test_services.py`：

```python
from django.utils import timezone
from apps.scoring.models import (
    Experiment, ScoreSheet, MetricScore, ExperimentScoringConfig,
)
from apps.scoring.services import ScoringService
from apps.users.models import User
from apps.roles.models import TradeRole, Company, UserCompanyRole


class ScoringServiceTest(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            username='teacher1', password='test', user_type='teacher',
        )
        self.student = User.objects.create_user(
            username='student1', password='test', user_type='student',
        )
        self.experiment = Experiment.objects.create(
            name='测试实验',
            start_date=timezone.now(),
            status='active',
            created_by=self.teacher,
        )
        role = TradeRole.objects.create(
            code='exporter', name='出口商', description='', sort_order=1,
        )
        self.company = Company.objects.create(name='出口公司', code='EXP01')
        self.ucr = UserCompanyRole.objects.create(
            user=self.student, company=self.company, role=role,
            status='active', is_active=True,
        )
        self.metric = ScoringMetric.objects.create(
            name='profit_margin', display_name='利润率',
            dimension='financial', calculation_method='profit_margin',
            weight=Decimal('20'),
            config={'threshold_high': 20, 'threshold_low': 0},
        )
        self.metric.applicable_roles.add(role)

    def test_calculate_role_score(self):
        """计算单个角色实例评分"""
        sheet = ScoringService.calculate_role_score(
            self.ucr, self.experiment,
            calculator_kwargs={
                'profit_margin': {
                    'revenue': Decimal('12000'), 'cost': Decimal('10000'),
                },
            },
        )
        self.assertEqual(sheet.status, 'auto_scored')
        self.assertGreater(sheet.auto_score, Decimal('0'))
        self.assertEqual(sheet.metric_scores.count(), 1)

    def test_teacher_review(self):
        """教师审核流程"""
        sheet = ScoreSheet.objects.create(
            experiment=self.experiment, user=self.student,
            user_company_role=self.ucr, auto_score=Decimal('85'),
            final_score=Decimal('85'),
            status='auto_scored',
        )
        result = ScoringService.teacher_review(
            sheet.id, self.teacher,
            adjustment=Decimal('-5'),
            comment='需要改进谈判技巧',
        )
        self.assertEqual(result.status, 'teacher_reviewed')
        self.assertEqual(result.final_score, Decimal('80'))
        self.assertEqual(result.teacher_comment, '需要改进谈判技巧')
        self.assertEqual(result.reviewed_by, self.teacher)

    def test_teacher_review_exceeds_limit(self):
        """教师加减分超限"""
        sheet = ScoreSheet.objects.create(
            experiment=self.experiment, user=self.student,
            user_company_role=self.ucr, auto_score=Decimal('85'),
            final_score=Decimal('85'),
            status='auto_scored',
        )
        with self.assertRaises(ValueError):
            ScoringService.teacher_review(
                sheet.id, self.teacher,
                adjustment=Decimal('30'),
                comment='超限测试',
            )

    def test_recalculate_preserves_teacher_data(self):
        """重新计算保留教师加减分和评语"""
        sheet = ScoreSheet.objects.create(
            experiment=self.experiment, user=self.student,
            user_company_role=self.ucr, auto_score=Decimal('85'),
            teacher_adjustment=Decimal('-3'),
            final_score=Decimal('82'),
            teacher_comment='保留评语',
            status='teacher_reviewed',
            reviewed_by=self.teacher,
            reviewed_at=timezone.now(),
        )
        MetricScore.objects.create(
            score_sheet=sheet, metric=self.metric,
            raw_value=Decimal('16.67'), score=Decimal('85'),
        )
        result = ScoringService.recalculate(
            sheet.id,
            calculator_kwargs={
                'profit_margin': {
                    'revenue': Decimal('15000'), 'cost': Decimal('10000'),
                },
            },
        )
        self.assertEqual(result.teacher_adjustment, Decimal('-3'))
        self.assertEqual(result.teacher_comment, '保留评语')
        self.assertNotEqual(result.auto_score, Decimal('85'))
        self.assertEqual(result.final_score, result.auto_score + result.teacher_adjustment)
```

- [ ] **步骤 2：运行测试验证失败**

运行：`python manage.py test apps.scoring.tests.test_services::ScoringServiceTest -v2`
预期：FAIL — `ImportError` 或 `AttributeError`

- [ ] **步骤 3：实现 ScoringService**

追加到 `apps/scoring/services.py`：

```python
from django.utils import timezone
from apps.scoring.models import (
    ScoreSheet, MetricScore, ExperimentScoringConfig,
)
from apps.scoring.calculators import get_calculator


class ScoringService:
    """评分总调度"""

    @staticmethod
    def calculate_role_score(user_company_role, experiment, calculator_kwargs=None):
        """
        计算单个角色实例评分。

        calculator_kwargs: {calculation_method: {key: value}} 传递给计算器的额外参数
        """
        kwargs = calculator_kwargs or {}
        role = user_company_role.role

        # 获取该角色适用的指标
        metrics = ScoringMetric.objects.filter(
            applicable_roles=role, is_active=True,
        )

        if not metrics.exists():
            sheet, _ = ScoreSheet.objects.update_or_create(
                experiment=experiment,
                user_company_role=user_company_role,
                defaults={
                    'user': user_company_role.user,
                    'status': 'auto_scored',
                },
            )
            return sheet

        scores = []
        sheet, _ = ScoreSheet.objects.update_or_create(
            experiment=experiment,
            user_company_role=user_company_role,
            defaults={
                'user': user_company_role.user,
                'status': 'auto_scored',
            },
        )

        for metric in metrics:
            calculator_cls = get_calculator(metric.calculation_method)
            method_kwargs = kwargs.get(metric.calculation_method, {})
            raw_value, score, details = calculator_cls.calculate(
                user_company_role, experiment, metric, **method_kwargs,
            )

            MetricScore.objects.update_or_create(
                score_sheet=sheet, metric=metric,
                defaults={
                    'raw_value': raw_value,
                    'score': score,
                    'details': details,
                },
            )
            scores.append((metric, score))

        # 获取实验级配置
        configs = list(ExperimentScoringConfig.objects.filter(experiment=experiment))
        auto_score = ScoreAggregator.aggregate(scores, configs)

        sheet.auto_score = auto_score
        sheet.final_score = auto_score + sheet.teacher_adjustment
        sheet.save()
        return sheet

    @staticmethod
    def calculate_experiment_scores(experiment_id, calculator_kwargs=None):
        """触发整个实验的自动评分"""
        from apps.scoring.models import Experiment
        from apps.roles.models import UserCompanyRole

        experiment = Experiment.objects.get(id=experiment_id)
        ucrs = UserCompanyRole.objects.filter(
            status__in=['active', 'approved'],
        )

        results = []
        for ucr in ucrs:
            sheet = ScoringService.calculate_role_score(
                ucr, experiment, calculator_kwargs,
            )
            results.append(sheet)
        return results

    @staticmethod
    def teacher_review(sheet_id, teacher, adjustment=Decimal('0'), comment=''):
        """教师审核评分表"""
        sheet = ScoreSheet.objects.get(id=sheet_id)

        if sheet.status == 'draft':
            raise ValueError('评分表尚未自动评分')

        # 检查加减分上限
        config = ExperimentScoringConfig.objects.filter(
            experiment=sheet.experiment,
        ).first()
        max_adj = config.max_adjustment if config else Decimal('20')

        if abs(adjustment) > max_adj:
            raise ValueError(f'加减分不能超过 ±{max_adj}，当前: {adjustment}')

        sheet.teacher_adjustment = adjustment
        sheet.final_score = sheet.auto_score + adjustment
        sheet.teacher_comment = comment
        sheet.reviewed_by = teacher
        sheet.reviewed_at = timezone.now()
        sheet.status = 'teacher_reviewed'
        sheet.save()
        return sheet

    @staticmethod
    def recalculate(sheet_id, calculator_kwargs=None):
        """重新计算自动分，保留教师审核数据"""
        sheet = ScoreSheet.objects.get(id=sheet_id)
        result = ScoringService.calculate_role_score(
            sheet.user_company_role, sheet.experiment, calculator_kwargs,
        )
        # 保留教师加减分
        result.final_score = result.auto_score + result.teacher_adjustment
        result.save()
        return result
```

- [ ] **步骤 4：运行测试验证通过**

运行：`python manage.py test apps.scoring.tests.test_services -v2`
预期：PASS

- [ ] **步骤 5：Commit**

```bash
git add apps/scoring/services.py apps/scoring/tests/test_services.py
git commit -m "feat(scoring): add ScoringService with calculate, review, and recalculate"
```

---

### 任务 13：实现序列化器和 ViewSet

**文件：**
- 创建：`apps/scoring/serializers.py`
- 创建：`apps/scoring/views.py`
- 创建：`apps/scoring/urls.py`

- [ ] **步骤 1：创建序列化器**

```python
# apps/scoring/serializers.py
from rest_framework import serializers
from apps.scoring.models import (
    Experiment, ScoringMetric, ScoreSheet, MetricScore,
    ExperimentScoringConfig,
)


class ScoringMetricSerializer(serializers.ModelSerializer):
    dimension_display = serializers.CharField(
        source='get_dimension_display', read_only=True,
    )

    class Meta:
        model = ScoringMetric
        fields = [
            'id', 'name', 'display_name', 'dimension', 'dimension_display',
            'weight', 'calculation_method', 'config', 'is_active',
        ]
        read_only_fields = ['id', 'name', 'calculation_method']


class MetricScoreSerializer(serializers.ModelSerializer):
    metric_name = serializers.CharField(source='metric.display_name', read_only=True)

    class Meta:
        model = MetricScore
        fields = [
            'id', 'metric', 'metric_name', 'raw_value', 'score', 'details',
        ]
        read_only_fields = fields


class ScoreSheetSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(
        source='get_status_display', read_only=True,
    )
    metric_scores = MetricScoreSerializer(many=True, read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = ScoreSheet
        fields = [
            'id', 'experiment', 'user', 'username', 'user_company_role',
            'status', 'status_display',
            'auto_score', 'teacher_adjustment', 'final_score',
            'teacher_comment', 'reviewed_by', 'reviewed_at',
            'metric_scores', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'auto_score', 'final_score',
            'reviewed_by', 'reviewed_at', 'created_at', 'updated_at',
        ]


class ExperimentScoringConfigSerializer(serializers.ModelSerializer):
    metric_name = serializers.CharField(source='metric.display_name', read_only=True)

    class Meta:
        model = ExperimentScoringConfig
        fields = [
            'id', 'experiment', 'metric', 'metric_name',
            'custom_weight', 'max_adjustment',
        ]


class ExperimentSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(
        source='get_status_display', read_only=True,
    )
    score_sheets_count = serializers.SerializerMethodField()

    class Meta:
        model = Experiment
        fields = [
            'id', 'name', 'description', 'status', 'status_display',
            'start_date', 'end_date', 'score_sheets_count',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_score_sheets_count(self, obj):
        return obj.score_sheets.count()
```

- [ ] **步骤 2：创建 ViewSet**

```python
# apps/scoring/views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from apps.scoring.models import (
    Experiment, ScoringMetric, ScoreSheet, ExperimentScoringConfig,
)
from apps.scoring.serializers import (
    ExperimentSerializer, ScoringMetricSerializer,
    ScoreSheetSerializer, ExperimentScoringConfigSerializer,
)
from apps.scoring.services import ScoringService


class ExperimentViewSet(viewsets.ModelViewSet):
    serializer_class = ExperimentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Experiment.objects.all()
        if self.request.user.user_type == 'student':
            qs = qs.filter(status='active')
        return qs


class ScoringMetricViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ScoringMetric.objects.filter(is_active=True)
    serializer_class = ScoringMetricSerializer
    permission_classes = [IsAuthenticated]


class ScoreSheetViewSet(viewsets.ModelViewSet):
    serializer_class = ScoreSheetSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = ScoreSheet.objects.select_related(
            'experiment', 'user', 'user_company_role',
        ).prefetch_related('metric_scores__metric')

        if self.request.user.user_type == 'student':
            qs = qs.filter(user=self.request.user)

        experiment_id = self.request.query_params.get('experiment')
        if experiment_id:
            qs = qs.filter(experiment_id=experiment_id)

        return qs

    @action(detail=True, methods=['post'])
    def review(self, request, pk=None):
        """教师审核评分表"""
        if request.user.user_type not in ('teacher', 'admin'):
            return Response(
                {'code': 1, 'message': '只有教师才能审核'},
                status=status.HTTP_403_FORBIDDEN,
            )
        sheet = self.get_object()
        adjustment = request.data.get('adjustment', 0)
        comment = request.data.get('comment', '')

        try:
            result = ScoringService.teacher_review(
                sheet.id, request.user,
                adjustment=adjustment, comment=comment,
            )
        except ValueError as e:
            return Response(
                {'code': 1, 'message': str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response({
            'code': 0, 'message': '审核成功',
            'data': ScoreSheetSerializer(result).data,
        })

    @action(detail=True, methods=['post'])
    def recalculate(self, request, pk=None):
        """重新计算自动分"""
        if request.user.user_type not in ('teacher', 'admin'):
            return Response(
                {'code': 1, 'message': '只有教师才能重新计算'},
                status=status.HTTP_403_FORBIDDEN,
            )
        sheet = self.get_object()
        result = ScoringService.recalculate(sheet.id)
        return Response({
            'code': 0, 'message': '重新计算完成',
            'data': ScoreSheetSerializer(result).data,
        })


class ExperimentScoringConfigViewSet(viewsets.ModelViewSet):
    serializer_class = ExperimentScoringConfigSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = ExperimentScoringConfig.objects.select_related('metric')
        experiment_id = self.request.query_params.get('experiment')
        if experiment_id:
            qs = qs.filter(experiment_id=experiment_id)
        return qs

    def create(self, request, *args, **kwargs):
        if request.user.user_type not in ('teacher', 'admin'):
            return Response(
                {'code': 1, 'message': '只有教师才能配置权重'},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        if request.user.user_type not in ('teacher', 'admin'):
            return Response(
                {'code': 1, 'message': '只有教师才能配置权重'},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().update(request, *args, **kwargs)
```

- [ ] **步骤 3：创建 URL 路由**

```python
# apps/scoring/urls.py
from rest_framework.routers import DefaultRouter
from apps.scoring import views

app_name = 'scoring'

router = DefaultRouter()
router.register(r'experiments', views.ExperimentViewSet, basename='experiment')
router.register(r'metrics', views.ScoringMetricViewSet, basename='scoringmetric')
router.register(r'sheets', views.ScoreSheetViewSet, basename='scoresheet')
router.register(r'configs', views.ExperimentScoringConfigViewSet, basename='scoringconfig')

urlpatterns = router.urls
```

- [ ] **步骤 4：注册到主 urls.py**

在 `simtrade/urls.py` 中添加：

```python
path('api/v1/scoring/', include('apps.scoring.urls')),
```

- [ ] **步骤 5：验证 API 可访问**

运行：`python manage.py check`
预期：无错误

- [ ] **步骤 6：Commit**

```bash
git add apps/scoring/serializers.py apps/scoring/views.py apps/scoring/urls.py simtrade/urls.py
git commit -m "feat(scoring): add serializers, views, and URL routing"
```

---

### 任务 14：API 集成测试

**文件：**
- 创建：`apps/scoring/tests/test_api.py`

- [ ] **步骤 1：编写 API 测试**

```python
# apps/scoring/tests/test_api.py
from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from apps.scoring.models import Experiment, ScoringMetric, ScoreSheet
from apps.users.models import User
from apps.roles.models import TradeRole, Company, UserCompanyRole


class ScoreSheetAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.teacher = User.objects.create_user(
            username='teacher1', password='test', user_type='teacher',
        )
        self.student = User.objects.create_user(
            username='student1', password='test', user_type='student',
        )
        self.experiment = Experiment.objects.create(
            name='测试实验', status='active',
        )
        role = TradeRole.objects.create(
            code='exporter', name='出口商', description='', sort_order=1,
        )
        self.company = Company.objects.create(name='公司', code='C01')
        self.ucr = UserCompanyRole.objects.create(
            user=self.student, company=self.company, role=role,
            status='active', is_active=True,
        )

    def test_student_can_list_own_sheets(self):
        self.client.force_authenticate(self.student)
        ScoreSheet.objects.create(
            experiment=self.experiment, user=self.student,
            user_company_role=self.ucr, auto_score=Decimal('85'),
            final_score=Decimal('85'), status='auto_scored',
        )
        resp = self.client.get('/api/v1/scoring/sheets/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 1)

    def test_student_cannot_see_others(self):
        other = User.objects.create_user(
            username='student2', password='test', user_type='student',
        )
        self.client.force_authenticate(other)
        ScoreSheet.objects.create(
            experiment=self.experiment, user=self.student,
            user_company_role=self.ucr, auto_score=Decimal('85'),
            final_score=Decimal('85'), status='auto_scored',
        )
        resp = self.client.get('/api/v1/scoring/sheets/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 0)

    def test_teacher_can_review(self):
        self.client.force_authenticate(self.teacher)
        sheet = ScoreSheet.objects.create(
            experiment=self.experiment, user=self.student,
            user_company_role=self.ucr, auto_score=Decimal('85'),
            final_score=Decimal('85'), status='auto_scored',
        )
        resp = self.client.post(
            f'/api/v1/scoring/sheets/{sheet.id}/review/',
            {'adjustment': -5, 'comment': '需要改进'},
        )
        self.assertEqual(resp.status_code, 200)
        sheet.refresh_from_db()
        self.assertEqual(sheet.final_score, Decimal('80'))
        self.assertEqual(sheet.status, 'teacher_reviewed')

    def test_teacher_adjustment_exceeds_limit(self):
        self.client.force_authenticate(self.teacher)
        sheet = ScoreSheet.objects.create(
            experiment=self.experiment, user=self.student,
            user_company_role=self.ucr, auto_score=Decimal('85'),
            final_score=Decimal('85'), status='auto_scored',
        )
        resp = self.client.post(
            f'/api/v1/scoring/sheets/{sheet.id}/review/',
            {'adjustment': 30, 'comment': '超限'},
        )
        self.assertEqual(resp.status_code, 400)

    def test_student_cannot_review(self):
        self.client.force_authenticate(self.student)
        sheet = ScoreSheet.objects.create(
            experiment=self.experiment, user=self.student,
            user_company_role=self.ucr, auto_score=Decimal('85'),
            final_score=Decimal('85'), status='auto_scored',
        )
        resp = self.client.post(
            f'/api/v1/scoring/sheets/{sheet.id}/review/',
            {'adjustment': 5, 'comment': '作弊'},
        )
        self.assertEqual(resp.status_code, 403)


class ScoringMetricAPITest(TestCase):
    def test_list_metrics(self):
        self.client = APIClient()
        user = User.objects.create_user(username='u1', password='test')
        self.client.force_authenticate(user)
        ScoringMetric.objects.create(
            name='m1', display_name='指标1',
            dimension='financial', calculation_method='profit_margin',
            weight=Decimal('20'),
        )
        resp = self.client.get('/api/v1/scoring/metrics/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 1)
```

- [ ] **步骤 2：运行所有测试**

```bash
python manage.py test apps.scoring.tests -v2
```

预期：全部 PASS

- [ ] **步骤 3：Commit**

```bash
git add apps/scoring/tests/test_api.py
git commit -m "test(scoring): add API integration tests"
```

---

### 任务 15：运行迁移和最终验证

- [ ] **步骤 1：创建并应用迁移**

```bash
python manage.py makemigrations scoring
python manage.py migrate
```

- [ ] **步骤 2：初始化指标数据**

```bash
python manage.py init_scoring_metrics
```

预期：输出 10 条 CREATE 消息

- [ ] **步骤 3：运行全部测试**

```bash
python manage.py test apps.scoring -v2
```

预期：全部 PASS

- [ ] **步骤 4：运行项目 check**

```bash
python manage.py check
```

预期：无错误

- [ ] **步骤 5：最终 Commit**

```bash
git add apps/scoring/
git commit -m "feat(scoring): complete scoring system with models, calculators, services, and API"
```

---

## 自检结果

**规格覆盖度：**
- ✅ 4 个数据模型（ScoringMetric, ScoreSheet, MetricScore, ExperimentScoringConfig）→ 任务 3-4
- ✅ Experiment 辅助模型 → 任务 2
- ✅ 10 个指标计算器 → 任务 6-10
- ✅ ScoreAggregator 加权汇总 → 任务 11
- ✅ ScoringService 调度 → 任务 12
- ✅ 7 个 API 端点 → 任务 13
- ✅ 权限控制（学生看自己，教师看全部）→ 任务 13, 14
- ✅ 教师加减分限制 → 任务 12
- ✅ 权重重分配 → 任务 11
- ✅ 重新计算保留教师数据 → 任务 12
- ✅ Admin 注册 → 任务 3-4
- ✅ 管理命令 → 任务 5
- ✅ 测试覆盖 → 任务 6-14

**占位符扫描：** 无 TODO/TBD/待定。

**类型一致性：** 所有 Decimal 类型一致，MetricResult 类型签名统一。
