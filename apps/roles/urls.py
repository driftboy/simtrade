"""
URL configuration for roles app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import TradeRoleViewSet, UserCompanyRoleViewSet, CompanyViewSet

app_name = 'roles'

router = DefaultRouter()

# Register viewsets
router.register(r'roles', TradeRoleViewSet, basename='traderole')
router.register(r'my-roles', UserCompanyRoleViewSet, basename='usercompanyrole')
router.register(r'companies', CompanyViewSet, basename='company')

urlpatterns = [
    path('', include(router.urls)),
]
