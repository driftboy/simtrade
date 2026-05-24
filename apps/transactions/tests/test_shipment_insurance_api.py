import pytest
from decimal import Decimal
from datetime import date
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from apps.transactions.models import Transaction, Contract, Shipment, InsurancePolicy
from apps.transactions.services import ShipmentService
from apps.users.models import User
from apps.roles.services import CompanyService
from apps.roles.models import TradeRole, UserCompanyRole
from apps.core.models import Country
from apps.products.models import Product


def get_or_create_country():
    country, _ = Country.objects.get_or_create(
        code='CN', defaults={'name': '中国', 'name_en': 'China', 'phone_code': '86'}
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


class ShipmentInsuranceAPITest(TestCase):
    def setUp(self):
        from django.core.management import call_command
        call_command('init_trade_roles')

        self.exporter = User.objects.create_user(username='si_exp', password='testpass', email='sie@test.com')
        self.carrier_user = User.objects.create_user(username='si_car', password='testpass', email='sic@test.com')
        self.insurer_user = User.objects.create_user(username='si_ins', password='testpass', email='sii@test.com')
        self.buyer_user = User.objects.create_user(username='si_buy', password='testpass', email='sib@test.com')
        self.exporter_company = create_company_for_user(self.exporter, '_SI出口商')
        self.carrier_company = create_company_for_user(self.carrier_user, '_SI货运公司')
        self.insurer_company = create_company_for_user(self.insurer_user, '_SI保险公司')
        self.buyer_company = create_company_for_user(self.buyer_user, '_SI买方')

        setup_role(self.exporter, self.exporter_company, 'exporter')
        setup_role(self.carrier_user, self.carrier_company, 'shipping')
        setup_role(self.insurer_user, self.insurer_company, 'insurance')

        self.product = Product.objects.create(code='FIX-P0001', name='Test Product', category='electronics', unit='PCS')
        self.transaction = Transaction.objects.create(
            buyer=self.buyer_company, seller=self.exporter_company,
            product=self.product, quantity=1000, unit_price=10.00,
            status='in_progress', created_by=self.exporter
        )
        self.contract = Contract.objects.create(
            contract_no='SI-TEST-001', transaction=self.transaction,
            trade_term='CIF', payment_term='L/C at sight',
            delivery_time=date(2026, 12, 31),
            port_of_loading='Shanghai', port_of_discharge='Los Angeles',
            product_name='Test', product_spec='',
            quantity=1000, unit='pcs', unit_price=10.00,
            total_amount=10000.00, currency='USD', status='effective'
        )
        self.client = APIClient()

    def test_create_shipment(self):
        self.client.force_authenticate(user=self.exporter)
        url = reverse('transactions:shipment-list')
        response = self.client.post(url, {
            'contract_id': self.contract.id,
            'carrier_id': self.carrier_company.id,
            'port_of_loading': 'Shanghai',
            'port_of_discharge': 'Los Angeles'
        }, format='json')
        assert response.status_code == 201
        assert response.json()['code'] == 0

    def test_shipment_book_flow(self):
        shipment = ShipmentService.create_shipment(
            user=self.exporter, contract_id=self.contract.id,
            carrier_id=self.carrier_company.id,
            port_of_loading='Shanghai', port_of_discharge='Los Angeles'
        )
        self.client.force_authenticate(user=self.carrier_user)
        url = reverse('transactions:shipment-book', kwargs={'pk': shipment.id})
        response = self.client.post(url, {
            'booking_no': 'BK001', 'vessel_name': 'OOCL',
            'etd': '2026-10-01', 'eta': '2026-11-01'
        }, format='json')
        assert response.status_code == 200
        shipment.refresh_from_db()
        assert shipment.status == 'booked'

    def test_shipment_full_lifecycle(self):
        shipment = ShipmentService.create_shipment(
            user=self.exporter, contract_id=self.contract.id,
            carrier_id=self.carrier_company.id,
            port_of_loading='Shanghai', port_of_discharge='Los Angeles'
        )
        self.client.force_authenticate(user=self.carrier_user)
        # Book
        self.client.post(reverse('transactions:shipment-book', kwargs={'pk': shipment.id}), {
            'booking_no': 'BK001', 'vessel_name': 'OOCL',
            'etd': '2026-10-01', 'eta': '2026-11-01'
        }, format='json')
        # Load
        self.client.post(reverse('transactions:shipment-load', kwargs={'pk': shipment.id}), {
            'container_no': 'MSKU1234567'
        }, format='json')
        # Issue BL
        self.client.post(reverse('transactions:shipment-issue-bl', kwargs={'pk': shipment.id}), {
            'bl_no': 'BL123456'
        }, format='json')
        # Arrive
        resp = self.client.post(reverse('transactions:shipment-arrive', kwargs={'pk': shipment.id}))
        assert resp.status_code == 200
        shipment.refresh_from_db()
        assert shipment.status == 'arrived'

    def test_create_insurance_policy(self):
        self.client.force_authenticate(user=self.exporter)
        url = reverse('transactions:insurancepolicy-list')
        response = self.client.post(url, {
            'contract_id': self.contract.id,
            'insurer_id': self.insurer_company.id,
            'coverage_type': 'all_risk',
            'cargo_description': '1000件棉质T恤'
        }, format='json')
        assert response.status_code == 201
        assert response.json()['code'] == 0

    def test_insurance_full_lifecycle(self):
        self.client.force_authenticate(user=self.exporter)
        # Create
        resp = self.client.post(reverse('transactions:insurancepolicy-list'), {
            'contract_id': self.contract.id,
            'insurer_id': self.insurer_company.id,
            'coverage_type': 'all_risk',
            'cargo_description': 'Test'
        }, format='json')
        policy_id = resp.json()['data']['id']
        # Underwrite
        self.client.force_authenticate(user=self.insurer_user)
        resp = self.client.post(reverse('transactions:insurancepolicy-underwrite', kwargs={'pk': policy_id}))
        assert resp.status_code == 200
        # Issue
        resp = self.client.post(reverse('transactions:insurancepolicy-issue', kwargs={'pk': policy_id}))
        assert resp.status_code == 200
        policy = InsurancePolicy.objects.get(id=policy_id)
        assert policy.status == 'issued'

    def test_unauthenticated_shipment_rejected(self):
        url = reverse('transactions:shipment-list')
        response = self.client.get(url)
        assert response.status_code in (401, 403)

    def test_unauthenticated_insurance_rejected(self):
        url = reverse('transactions:insurancepolicy-list')
        response = self.client.get(url)
        assert response.status_code in (401, 403)
