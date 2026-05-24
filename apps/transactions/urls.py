from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.transactions import views
from apps.transactions.views_lc import LetterOfCreditViewSet

app_name = 'transactions'

router = DefaultRouter()
router.register(r'transactions', views.TransactionViewSet, basename='transaction')
router.register(r'contracts', views.ContractViewSet, basename='contract')
router.register(r'purchase-orders', views.PurchaseOrderViewSet, basename='purchaseorder')
router.register(r'shipments', views.ShipmentViewSet, basename='shipment')
router.register(r'insurance-policies', views.InsurancePolicyViewSet, basename='insurancepolicy')
router.register(r'customs-declarations', views.CustomsDeclarationViewSet, basename='customsdeclaration')
router.register(r'inspection-applications', views.InspectionApplicationViewSet, basename='inspectionapplication')
router.register(r'forex-settlements', views.ForexSettlementViewSet, basename='forexsettlement')
router.register(r'tax-refund-applications', views.TaxRefundApplicationViewSet, basename='taxrefundapplication')
router.register(r'letters-of-credit', LetterOfCreditViewSet, basename='letterofcredit')

urlpatterns = router.urls
