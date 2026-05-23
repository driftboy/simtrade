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
        """利润率 >= 20% -> 100 分"""
        raw, score, details = ProfitMarginCalculator.calculate(
            self.ucr, self.experiment, self.metric,
            revenue=Decimal('12000'), cost=Decimal('9000'),
        )
        self.assertEqual(raw, Decimal('25.0000'))
        self.assertEqual(score, Decimal('100'))

    def test_zero_margin(self):
        """利润率 = 0% -> 0 分"""
        raw, score, details = ProfitMarginCalculator.calculate(
            self.ucr, self.experiment, self.metric,
            revenue=Decimal('10000'), cost=Decimal('10000'),
        )
        self.assertEqual(raw, Decimal('0.0000'))
        self.assertEqual(score, Decimal('0'))

    def test_mid_margin(self):
        """利润率 9.09% -> 线性插值得分（~45.45）"""
        raw, score, details = ProfitMarginCalculator.calculate(
            self.ucr, self.experiment, self.metric,
            revenue=Decimal('11000'), cost=Decimal('10000'),
        )
        self.assertEqual(raw, Decimal('9.0909'))
        self.assertEqual(score, Decimal('45.45'))

    def test_negative_margin(self):
        """负利润 -> 0 分"""
        raw, score, details = ProfitMarginCalculator.calculate(
            self.ucr, self.experiment, self.metric,
            revenue=Decimal('8000'), cost=Decimal('10000'),
        )
        self.assertEqual(score, Decimal('0'))

    def test_no_transactions(self):
        """无交易数据 -> 原始值 None，分数 0"""
        raw, score, details = ProfitMarginCalculator.calculate(
            self.ucr, self.experiment, self.metric,
        )
        self.assertIsNone(raw)
        self.assertEqual(score, Decimal('0'))
