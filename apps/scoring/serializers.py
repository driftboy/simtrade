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
            'status', 'teacher_adjustment', 'teacher_comment',
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
