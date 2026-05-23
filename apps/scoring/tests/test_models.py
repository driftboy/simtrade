from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from apps.scoring.models import Experiment
from apps.scoring.models import ScoringMetric
from apps.roles.models import TradeRole


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
