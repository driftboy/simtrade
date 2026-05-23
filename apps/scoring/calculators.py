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
    if minutes >= max_time:
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


# 注册表：calculation_method -> Calculator 类
CALCULATOR_REGISTRY: dict[str, type[MetricCalculator]] = {
    'profit_margin': ProfitMarginCalculator,
}


def get_calculator(method: str) -> type[MetricCalculator]:
    cls = CALCULATOR_REGISTRY.get(method)
    if cls is None:
        raise ValueError(f'未注册的计算方法: {method}')
    return cls
