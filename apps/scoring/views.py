from decimal import Decimal

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
        if request.user.user_type not in ('teacher', 'admin'):
            return Response(
                {'code': 1, 'message': '只有教师才能审核'},
                status=status.HTTP_403_FORBIDDEN,
            )
        sheet = self.get_object()
        adjustment = Decimal(str(request.data.get('adjustment', 0)))
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
