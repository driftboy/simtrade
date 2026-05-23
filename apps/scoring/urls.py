from rest_framework.routers import DefaultRouter
from apps.scoring import views

app_name = 'scoring'

router = DefaultRouter()
router.register(r'experiments', views.ExperimentViewSet, basename='experiment')
router.register(r'metrics', views.ScoringMetricViewSet, basename='scoringmetric')
router.register(r'sheets', views.ScoreSheetViewSet, basename='scoresheet')
router.register(r'configs', views.ExperimentScoringConfigViewSet, basename='scoringconfig')

urlpatterns = router.urls
