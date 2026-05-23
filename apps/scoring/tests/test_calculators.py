from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from apps.scoring.calculators import (
    MetricCalculator,
    ProfitMarginCalculator,
    CostControlCalculator,
    DocumentAccuracyCalculator,
    FirstPassRateCalculator,
    CompletionRateCalculator,
    ProcessingSpeedCalculator,
    TradeCycleTimeCalculator,
    DocumentTurnaroundCalculator,
    ResponseTimeCalculator,
    NegotiationEfficiencyCalculator,
)
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
        raw, score, _ = CostControlCalculator.calculate(
            self.ucr, self.experiment, self.metric,
            actual_cost=Decimal('10000'), benchmark_cost=Decimal('9800'),
        )
        self.assertEqual(score, Decimal('100'))

    def test_moderate_deviation(self):
        raw, score, _ = CostControlCalculator.calculate(
            self.ucr, self.experiment, self.metric,
            actual_cost=Decimal('12000'), benchmark_cost=Decimal('10000'),
        )
        self.assertEqual(score, Decimal('60'))

    def test_extreme_deviation(self):
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
        raw, score, _ = DocumentAccuracyCalculator.calculate(
            self.ucr, self.experiment, self.metric,
            total_submissions=10, error_count=0,
        )
        self.assertEqual(raw, Decimal('1.0000'))
        self.assertEqual(score, Decimal('100'))

    def test_half_accuracy(self):
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
        raw, score, _ = NegotiationEfficiencyCalculator.calculate(
            self.ucr, self.experiment, self.metric,
            rounds=1, initial_price=Decimal('100'), final_price=Decimal('98'),
        )
        self.assertGreaterEqual(score, Decimal('80'))

    def test_many_rounds_good_price(self):
        raw, score, _ = NegotiationEfficiencyCalculator.calculate(
            self.ucr, self.experiment, self.metric,
            rounds=5, initial_price=Decimal('100'), final_price=Decimal('92'),
        )
        self.assertGreaterEqual(score, Decimal('40'))
        self.assertLess(score, Decimal('80'))

    def test_one_round_bad_price(self):
        raw, score, _ = NegotiationEfficiencyCalculator.calculate(
            self.ucr, self.experiment, self.metric,
            rounds=1, initial_price=Decimal('100'), final_price=Decimal('70'),
        )
        self.assertLess(score, Decimal('60'))

    def test_no_deal(self):
        raw, score, _ = NegotiationEfficiencyCalculator.calculate(
            self.ucr, self.experiment, self.metric,
        )
        self.assertIsNone(raw)
        self.assertEqual(score, Decimal('0'))
