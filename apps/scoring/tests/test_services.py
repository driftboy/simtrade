from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from apps.scoring.services import ScoreAggregator, ScoringService
from apps.scoring.models import (
    Experiment, ScoringMetric, ScoreSheet, MetricScore, ExperimentScoringConfig,
)
from apps.users.models import User
from apps.roles.models import TradeRole, Company, UserCompanyRole


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
        # total ≈ 94.29
        result = ScoreAggregator.aggregate(scores, [])
        self.assertGreater(result, Decimal('90'))

    def test_all_no_data(self):
        """所有指标无数据 → 0"""
        result = ScoreAggregator.aggregate([], [])
        self.assertEqual(result, Decimal('0'))


class ScoringServiceTest(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            username='teacher1', password='test', user_type='teacher',
            email='teacher1@test.com',
        )
        self.student = User.objects.create_user(
            username='student1', password='test', user_type='student',
            email='student1@test.com',
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
