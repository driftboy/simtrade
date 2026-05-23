from django.contrib import admin
from apps.scoring.models import Experiment, ScoringMetric, ScoreSheet, MetricScore, ExperimentScoringConfig


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
