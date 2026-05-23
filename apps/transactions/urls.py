from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.transactions import views

app_name = 'transactions'

router = DefaultRouter()
router.register(r'transactions', views.TransactionViewSet, basename='transaction')
router.register(r'contracts', views.ContractViewSet, basename='contract')
router.register(r'purchase-orders', views.PurchaseOrderViewSet, basename='purchaseorder')
router.register(r'shipments', views.ShipmentViewSet, basename='shipment')
router.register(r'insurance-policies', views.InsurancePolicyViewSet, basename='insurancepolicy')
router.register(r'customs-declarations', views.CustomsDeclarationViewSet, basename='customsdeclaration')
router.register(r'inspection-applications', views.InspectionApplicationViewSet, basename='inspectionapplication')

urlpatterns = router.urls
