from django.contrib import admin
from apps.scoring.models import Experiment, ScoringMetric


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
