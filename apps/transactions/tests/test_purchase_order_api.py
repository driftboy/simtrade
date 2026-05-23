import pytest
from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from apps.transactions.models import Transaction, PurchaseOrder
from apps.transactions.services import PurchaseOrderService
from apps.users.models import User
from apps.roles.services import CompanyService
from apps.roles.models import TradeRole, UserCompanyRole
from apps.core.models import Country


def get_or_create_country():
    country, _ = Country.objects.get_or_create(
        code='CN',
        defaults={'name': '中国', 'name_en': 'China', 'phone_code': '86'}
    )
    return country


def create_company_for_user(user, name_suffix=''):
    country = get_or_create_country()
    return CompanyService.create_company(
        user=user,
        name=f'{user.username}{name_suffix}公司',
        name_en=f'{user.username}{name_suffix} Company',
        country_id=country.code
    )


def setup_role(user, company, role_code):
    role = TradeRole.objects.get(code=role_code)
    UserCompanyRole.objects.get_or_create(
        user=user, company=company, role=role,
        defaults={'status': 'active', 'is_active': True}
    )


class PurchaseOrderAPITest(TestCase):
    def setUp(self):
        self.exporter = User.objects.create_user(username='api_exp', password='testpass', email='ae@test.com')
        self.factory_user = User.objects.create_user(username='api_fac', password='testpass', email='af@test.com')
        self.importer = User.objects.create_user(username='api_imp', password='testpass', email='ai@test.com')
        self.exporter_company = create_company_for_user(self.exporter, '_API出口商')
        self.factory_company = create_company_for_user(self.factory_user, '_API工厂')
        self.importer_company = create_company_for_user(self.importer, '_API进口商')
        from django.core.management import call_command
        call_command('init_trade_roles')
        setup_role(self.exporter, self.exporter_company, 'exporter')
        setup_role(self.factory_user, self.factory_company, 'factory')
        setup_role(self.importer, self.importer_company, 'importer')
        self.transaction = Transaction.objects.create(
            buyer=self.importer_company, seller=self.exporter_company,
            product_id=1, quantity=1000, unit_price=10.00,
            status='in_progress', created_by=self.importer
        )
        self.client = APIClient()

    def test_create_purchase_order(self):
        self.client.force_authenticate(user=self.exporter)
        url = reverse('transactions:purchaseorder-list')
        data = {
            'transaction_id': self.transaction.id,
            'seller_id': self.factory_company.id,
            'product_name': '棉质T恤',
            'quantity': '500',
            'unit_price': '8.00',
            'currency': 'CNY'
        }
        response = self.client.post(url, data, format='json')
        assert response.status_code == 201
        assert response.json()['code'] == 0

    def test_list_purchase_orders(self):
        PurchaseOrderService.create_order(
            user=self.exporter, transaction_id=self.transaction.id,
            seller_id=self.factory_company.id,
            product_name='商品', quantity=Decimal('100'), unit_price=Decimal('10.00')
        )
        self.client.force_authenticate(user=self.exporter)
        url = reverse('transactions:purchaseorder-list')
        response = self.client.get(url)
        assert response.status_code == 200
        assert len(response.json()['data']) >= 1

    def test_confirm_purchase_order(self):
        po = PurchaseOrderService.create_order(
            user=self.exporter, transaction_id=self.transaction.id,
            seller_id=self.factory_company.id,
            product_name='商品', quantity=Decimal('100'), unit_price=Decimal('10.00')
        )
        self.client.force_authenticate(user=self.factory_user)
        url = reverse('transactions:purchaseorder-confirm', kwargs={'pk': po.id})
        response = self.client.post(url)
        assert response.status_code == 200
        po.refresh_from_db()
        assert po.status == 'confirmed'

    def test_ship_purchase_order(self):
        po = PurchaseOrderService.create_order(
            user=self.exporter, transaction_id=self.transaction.id,
            seller_id=self.factory_company.id,
            product_name='商品', quantity=Decimal('100'), unit_price=Decimal('10.00')
        )
        PurchaseOrderService.confirm(po.id, self.factory_user)
        self.client.force_authenticate(user=self.factory_user)
        url = reverse('transactions:purchaseorder-ship', kwargs={'pk': po.id})
        response = self.client.post(url, {'tracking_info': 'SF123456'}, format='json')
        assert response.status_code == 200
        po.refresh_from_db()
        assert po.status == 'shipped'

    def test_invoice_purchase_order(self):
        po = PurchaseOrderService.create_order(
            user=self.exporter, transaction_id=self.transaction.id,
            seller_id=self.factory_company.id,
            product_name='商品', quantity=Decimal('100'), unit_price=Decimal('10.00')
        )
        PurchaseOrderService.confirm(po.id, self.factory_user)
        PurchaseOrderService.ship(po.id, self.factory_user)
        self.client.force_authenticate(user=self.factory_user)
        url = reverse('transactions:purchaseorder-invoice', kwargs={'pk': po.id})
        response = self.client.post(url)
        assert response.status_code == 200
        po.refresh_from_db()
        assert po.status == 'invoiced'

    def test_complete_purchase_order(self):
        po = PurchaseOrderService.create_order(
            user=self.exporter, transaction_id=self.transaction.id,
            seller_id=self.factory_company.id,
            product_name='商品', quantity=Decimal('100'), unit_price=Decimal('10.00')
        )
        PurchaseOrderService.confirm(po.id, self.factory_user)
        PurchaseOrderService.ship(po.id, self.factory_user)
        PurchaseOrderService.invoice(po.id, self.factory_user)
        self.client.force_authenticate(user=self.exporter)
        url = reverse('transactions:purchaseorder-complete', kwargs={'pk': po.id})
        response = self.client.post(url)
        assert response.status_code == 200
        po.refresh_from_db()
        assert po.status == 'completed'

    def test_cancel_purchase_order(self):
        po = PurchaseOrderService.create_order(
            user=self.exporter, transaction_id=self.transaction.id,
            seller_id=self.factory_company.id,
            product_name='商品', quantity=Decimal('100'), unit_price=Decimal('10.00')
        )
        self.client.force_authenticate(user=self.exporter)
        url = reverse('transactions:purchaseorder-cancel', kwargs={'pk': po.id})
        response = self.client.post(url, {'reason': '不需要了'}, format='json')
        assert response.status_code == 200
        po.refresh_from_db()
        assert po.status == 'cancelled'

    def test_unauthenticated_rejected(self):
        url = reverse('transactions:purchaseorder-list')
        response = self.client.get(url)
        assert response.status_code in (401, 403)
