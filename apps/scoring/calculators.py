from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Dict, Optional, Tuple, Type


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
    """比率型标准化：直接 x 100，无数据返回 0"""
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
    if minutes >= max_time or max_time <= benchmark:
        return Decimal('0')
    return ((max_time - minutes) / (max_time - benchmark) * Decimal('100')).quantize(Decimal('0.01'))


class ProfitMarginCalculator(MetricCalculator):
    """利润率计算器

    利润率 >= threshold_high -> 100
    利润率 = threshold_low -> 0
    中间线性插值
    负利润 -> 0
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


class CostControlCalculator(MetricCalculator):
    """成本控制计算器

    偏差率 = (actual - benchmark) / benchmark * 100
    偏差 <= benchmark_deviation_pct -> 100
    每增加 5% 扣 10 分
    偏差 >= 50% -> 0
    """

    @staticmethod
    def calculate(user_company_role, experiment, metric, **kwargs) -> MetricResult:
        actual_cost = kwargs.get('actual_cost')
        benchmark_cost = kwargs.get('benchmark_cost')

        if actual_cost is None or benchmark_cost is None or benchmark_cost == 0:
            return None, Decimal('0'), {'reason': 'no_data'}

        deviation_pct = abs(actual_cost - benchmark_cost) / benchmark_cost * Decimal('100')
        config = metric.config or {}
        allowed_deviation = Decimal(str(config.get('benchmark_deviation_pct', 5)))

        if deviation_pct <= allowed_deviation:
            score = Decimal('100')
        elif deviation_pct >= Decimal('50'):
            score = Decimal('0')
        else:
            penalty = (deviation_pct / Decimal('5')) * Decimal('10')
            score = max(Decimal('100') - penalty.quantize(Decimal('0.01')), Decimal('0'))

        return deviation_pct.quantize(Decimal('0.01')), score, {
            'actual_cost': str(actual_cost),
            'benchmark_cost': str(benchmark_cost),
            'deviation_pct': str(deviation_pct.quantize(Decimal('0.01'))),
        }


class DocumentAccuracyCalculator(MetricCalculator):
    """单证准确率计算器

    accuracy = 1 - errors / total
    score = _standardize_ratio(accuracy)
    """

    @staticmethod
    def calculate(user_company_role, experiment, metric, **kwargs) -> MetricResult:
        total = kwargs.get('total_submissions')
        errors = kwargs.get('error_count', 0) or 0

        if total is None or total == 0:
            return None, Decimal('0'), {'reason': 'no_data'}

        accuracy = (Decimal('1') - Decimal(str(errors)) / Decimal(str(total))).quantize(Decimal('0.0001'))
        score = _standardize_ratio(accuracy)

        return accuracy, score, {
            'total_submissions': str(total),
            'error_count': str(errors),
        }


class FirstPassRateCalculator(MetricCalculator):
    """首次通过率计算器

    rate = first_pass / total
    score = _standardize_ratio(rate)
    """

    @staticmethod
    def calculate(user_company_role, experiment, metric, **kwargs) -> MetricResult:
        total = kwargs.get('total_operations')
        first_pass = kwargs.get('first_pass_count')

        if total is None or total == 0 or first_pass is None:
            return None, Decimal('0'), {'reason': 'no_data'}

        rate = (Decimal(str(first_pass)) / Decimal(str(total))).quantize(Decimal('0.0001'))
        score = _standardize_ratio(rate)

        return rate, score, {
            'total_operations': str(total),
            'first_pass_count': str(first_pass),
        }


class CompletionRateCalculator(MetricCalculator):
    """完成率计算器

    rate = completed / total
    score = _standardize_ratio(rate)
    """

    @staticmethod
    def calculate(user_company_role, experiment, metric, **kwargs) -> MetricResult:
        total = kwargs.get('total_assigned')
        completed = kwargs.get('completed_count')

        if total is None or total == 0 or completed is None:
            return None, Decimal('0'), {'reason': 'no_data'}

        rate = (Decimal(str(completed)) / Decimal(str(total))).quantize(Decimal('0.0001'))
        score = _standardize_ratio(rate)

        return rate, score, {
            'total_assigned': str(total),
            'completed_count': str(completed),
        }


class TimeBasedCalculator(MetricCalculator):
    """时间类计算器基类"""

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


class ProcessingSpeedCalculator(TimeBasedCalculator):
    pass


class TradeCycleTimeCalculator(TimeBasedCalculator):
    pass


class DocumentTurnaroundCalculator(TimeBasedCalculator):
    pass


class ResponseTimeCalculator(TimeBasedCalculator):
    pass


class NegotiationEfficiencyCalculator(MetricCalculator):
    """谈判效率计算器

    轮次效率分（满分60）= (max_rounds - rounds + 1) / max_rounds * 60
    价格偏差效率分（满分40）= max(0, (1 - deviation/price_threshold) * 40)
    总分 = clamp(rounds_score + price_score, 0, 100)
    """

    PRICE_DEVIATION_THRESHOLD = Decimal('0.3')

    @staticmethod
    def calculate(user_company_role, experiment, metric, **kwargs) -> MetricResult:
        rounds = kwargs.get('rounds')
        initial_price = kwargs.get('initial_price')
        final_price = kwargs.get('final_price')

        if rounds is None or initial_price is None or final_price is None or initial_price == 0:
            return None, Decimal('0'), {'reason': 'no_data'}

        config = metric.config or {}
        max_rounds = Decimal(str(config.get('max_rounds', 5)))

        # 轮次效率分（满分 60）
        rounds_score = ((max_rounds - Decimal(str(rounds)) + Decimal('1')) / max_rounds * Decimal('60')).quantize(Decimal('0.01'))

        # 价格偏差效率分（满分 40）
        deviation = abs(final_price - initial_price) / initial_price
        price_score = (Decimal('1') - deviation / NegotiationEfficiencyCalculator.PRICE_DEVIATION_THRESHOLD) * Decimal('40')

        total_score = max(Decimal('0'), min(rounds_score + price_score, Decimal('100'))).quantize(Decimal('0.01'))

        return rounds, total_score, {
            'rounds': str(rounds),
            'rounds_score': str(rounds_score),
            'price_score': str(price_score.quantize(Decimal('0.01'))),
            'initial_price': str(initial_price),
            'final_price': str(final_price),
        }


# 注册表：calculation_method -> Calculator 类
CALCULATOR_REGISTRY: Dict[str, Type[MetricCalculator]] = {
    'profit_margin': ProfitMarginCalculator,
    'cost_control': CostControlCalculator,
    'document_accuracy': DocumentAccuracyCalculator,
    'first_pass_rate': FirstPassRateCalculator,
    'completion_rate': CompletionRateCalculator,
    'processing_speed': ProcessingSpeedCalculator,
    'trade_cycle_time': TradeCycleTimeCalculator,
    'document_turnaround': DocumentTurnaroundCalculator,
    'response_time': ResponseTimeCalculator,
    'negotiation_efficiency': NegotiationEfficiencyCalculator,
}


def get_calculator(method: str) -> Type[MetricCalculator]:
    cls = CALCULATOR_REGISTRY.get(method)
    if cls is None:
        raise ValueError(f'未注册的计算方法: {method}')
    return cls
