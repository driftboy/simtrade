from django.urls import path
from apps.core.views import (
    ExchangeRateListView, ExchangeRateSyncView, CustomsParamsStatsView,
    CustomsParamsDetailView, HSCodeStatsView, HSCodeSyncView, HSCodeListView,
)

urlpatterns = [
    path('exchange-rates/', ExchangeRateListView.as_view(), name='exchange-rates-list'),
    path('exchange-rates/sync/', ExchangeRateSyncView.as_view(), name='exchange-rates-sync'),
    path('customs-params/stats/', CustomsParamsStatsView.as_view(), name='customs-params-stats'),
    path('customs-params/detail/', CustomsParamsDetailView.as_view(), name='customs-params-detail'),
    path('hs-codes/stats/', HSCodeStatsView.as_view(), name='hs-codes-stats'),
    path('hs-codes/sync/', HSCodeSyncView.as_view(), name='hs-codes-sync'),
    path('hs-codes/list/', HSCodeListView.as_view(), name='hs-codes-list'),
]
