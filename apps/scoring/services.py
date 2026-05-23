from decimal import Decimal

from django.utils import timezone

from apps.scoring.calculators import get_calculator
from apps.scoring.models import (
    Experiment,
    ExperimentScoringConfig,
    MetricScore,
    ScoreSheet,
    ScoringMetric,
)


class ScoreAggregator:
    """评分汇总器 — 加权求和"""

    @staticmethod
    def aggregate(
        scores: list[tuple[ScoringMetric, Decimal]],
        configs: list[ExperimentScoringConfig],
    ) -> Decimal:
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


class ScoringService:
    """评分总调度"""

    MAX_ADJUSTMENT_DEFAULT = Decimal('20')

    @staticmethod
    def calculate_role_score(user_company_role, experiment, calculator_kwargs=None):
        kwargs = calculator_kwargs or {}
        role = user_company_role.role

        metrics = ScoringMetric.objects.filter(
            applicable_roles=role, is_active=True,
        )

        sheet, _ = ScoreSheet.objects.update_or_create(
            experiment=experiment,
            user_company_role=user_company_role,
            defaults={
                'user': user_company_role.user,
                'status': 'auto_scored',
            },
        )

        if not metrics.exists():
            return sheet

        scores = []
        for metric in metrics:
            calculator_cls = get_calculator(metric.calculation_method)
            method_kwargs = kwargs.get(metric.calculation_method, {})
            raw_value, score, details = calculator_cls.calculate(
                user_company_role, experiment, metric, **method_kwargs,
            )

            # 只纳入有数据的指标（raw_value is not None）
            MetricScore.objects.update_or_create(
                score_sheet=sheet, metric=metric,
                defaults={
                    'raw_value': raw_value,
                    'score': score,
                    'details': details,
                },
            )
            if raw_value is not None:
                scores.append((metric, score))

        configs = list(ExperimentScoringConfig.objects.filter(experiment=experiment))
        auto_score = ScoreAggregator.aggregate(scores, configs)

        sheet.auto_score = auto_score
        sheet.final_score = auto_score + sheet.teacher_adjustment
        sheet.save()
        return sheet

    @staticmethod
    def calculate_experiment_scores(experiment_id, calculator_kwargs=None):
        from apps.roles.models import UserCompanyRole

        try:
            experiment = Experiment.objects.get(id=experiment_id)
        except Experiment.DoesNotExist:
            raise ValueError(f'实验不存在: {experiment_id}')

        ucrs = UserCompanyRole.objects.filter(
            company__id__in=experiment.score_sheets.values_list(
                'user_company_role__company_id', flat=True,
            ).distinct(),
            status__in=['active', 'approved'],
        )

        if not ucrs.exists():
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
        try:
            sheet = ScoreSheet.objects.get(id=sheet_id)
        except ScoreSheet.DoesNotExist:
            raise ValueError(f'评分表不存在: {sheet_id}')

        if sheet.status == 'draft':
            raise ValueError('评分表尚未自动评分')

        max_adj = ScoringService._get_max_adjustment(sheet.experiment_id)

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
        try:
            sheet = ScoreSheet.objects.get(id=sheet_id)
        except ScoreSheet.DoesNotExist:
            raise ValueError(f'评分表不存在: {sheet_id}')

        result = ScoringService.calculate_role_score(
            sheet.user_company_role, sheet.experiment, calculator_kwargs,
        )
        result.final_score = result.auto_score + result.teacher_adjustment
        result.save()
        return result

    @staticmethod
    def _get_max_adjustment(experiment_id):
        """获取实验的最大加减分上限（取所有配置中的最大值）"""
        configs = ExperimentScoringConfig.objects.filter(
            experiment_id=experiment_id,
        )
        if not configs.exists():
            return ScoringService.MAX_ADJUSTMENT_DEFAULT
        return max(cfg.max_adjustment for cfg in configs)
