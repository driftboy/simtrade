import pytest
from decimal import Decimal
from datetime import date
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from apps.transactions.models import Transaction, Contract, Shipment, CustomsDeclaration, InspectionApplication
from apps.transactions.services import ShipmentService
from apps.users.models import User
from apps.roles.services import CompanyService
from apps.roles.models import TradeRole, UserCompanyRole
from apps.core.models import Country


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


class CustomsInspectionAPITest(TestCase):
    def setUp(self):
        from django.core.management import call_command
        call_command('init_trade_roles')

        self.exporter = User.objects.create_user(username='ci_exp', password='testpass', email='cie@test.com')
        self.carrier_user = User.objects.create_user(username='ci_car', password='testpass', email='cic@test.com')
        self.customs_user = User.objects.create_user(username='ci_cus', password='testpass', email='ciu@test.com')
        self.inspector_user = User.objects.create_user(username='ci_ins', password='testpass', email='cii@test.com')
        self.buyer_user = User.objects.create_user(username='ci_buy', password='testpass', email='cib@test.com')
        self.exporter_company = create_company_for_user(self.exporter, '_CI出口商')
        self.carrier_company = create_company_for_user(self.carrier_user, '_CI货运')
        self.customs_company = create_company_for_user(self.customs_user, '_CI海关')
        self.inspector_company = create_company_for_user(self.inspector_user, '_CI商检')
        self.buyer_company = create_company_for_user(self.buyer_user, '_CI买方')

        setup_role(self.exporter, self.exporter_company, 'exporter')
        setup_role(self.carrier_user, self.carrier_company, 'shipping')
        setup_role(self.customs_user, self.customs_company, 'customs')
        setup_role(self.inspector_user, self.inspector_company, 'inspection')

        transaction = Transaction.objects.create(
            buyer=self.buyer_company, seller=self.exporter_company,
            product_id=1, quantity=1000, unit_price=10.00,
            status='in_progress', created_by=self.exporter
        )
        contract = Contract.objects.create(
            contract_no='CI-TEST-001', transaction=transaction,
            trade_term='CIF', payment_term='L/C at sight',
            delivery_time=date(2026, 12, 31),
            port_of_loading='Shanghai', port_of_discharge='Los Angeles',
            product_name='T-Shirt', product_spec='Cotton',
            quantity=1000, unit='pcs', unit_price=10.00,
            total_amount=10000.00, currency='USD', status='effective'
        )
        shipment = ShipmentService.create_shipment(
            user=self.exporter, contract_id=contract.id,
            carrier_id=self.carrier_company.id,
            port_of_loading='Shanghai', port_of_discharge='Los Angeles'
        )
        ShipmentService.book(shipment.id, self.carrier_user, 'BK001', 'OOCL', date(2026, 10, 1), date(2026, 11, 1))
        ShipmentService.load(shipment.id, self.carrier_user)
        ShipmentService.issue_bl(shipment.id, self.carrier_user, bl_no='BL001')
        self.shipment = shipment
        self.client = APIClient()

    def test_create_customs_declaration(self):
        self.client.force_authenticate(user=self.exporter)
        url = reverse('transactions:customsdeclaration-list')
        response = self.client.post(url, {
            'shipment_id': self.shipment.id,
            'customs_office_id': self.customs_company.id,
            'hs_code': '610910',
            'goods_name': 'Cotton T-Shirt',
            'quantity': '1000',
            'unit_value': '10.00',
            'total_value': '10000.00',
            'currency': 'USD'
        }, format='json')
        assert response.status_code == 201
        assert response.json()['code'] == 0

    def test_customs_full_lifecycle(self):
        from apps.transactions.services import CustomsService
        decl = CustomsService.create_declaration(
            user=self.exporter, shipment_id=self.shipment.id,
            customs_office_id=self.customs_company.id,
            hs_code='610910', goods_name='Test',
            quantity=Decimal('1000'), unit_value=Decimal('10.00'),
            total_value=Decimal('10000.00')
        )
        self.client.force_authenticate(user=self.customs_user)
        # Review
        self.client.post(reverse('transactions:customsdeclaration-review', kwargs={'pk': decl.id}))
        # Assess
        self.client.post(reverse('transactions:customsdeclaration-assess', kwargs={'pk': decl.id}))
        # Clear
        resp = self.client.post(reverse('transactions:customsdeclaration-clear', kwargs={'pk': decl.id}))
        assert resp.status_code == 200
        decl.refresh_from_db()
        assert decl.status == 'cleared'

    def test_create_inspection_application(self):
        self.client.force_authenticate(user=self.exporter)
        url = reverse('transactions:inspectionapplication-list')
        response = self.client.post(url, {
            'shipment_id': self.shipment.id,
            'inspector_id': self.inspector_company.id,
            'inspection_type': 'legal',
            'product_name': 'Cotton T-Shirt',
            'quantity': '1000',
            'goods_value': '10000.00'
        }, format='json')
        assert response.status_code == 201
        assert response.json()['code'] == 0

    def test_inspection_full_lifecycle(self):
        from apps.transactions.services import InspectionService
        app = InspectionService.create_application(
            user=self.exporter, shipment_id=self.shipment.id,
            inspector_id=self.inspector_company.id,
            inspection_type='legal', product_name='Test',
            quantity=Decimal('1000'), goods_value=Decimal('10000.00')
        )
        self.client.force_authenticate(user=self.inspector_user)
        # Inspect
        self.client.post(reverse('transactions:inspectionapplication-inspect', kwargs={'pk': app.id}))
        # Pass
        self.client.post(reverse('transactions:inspectionapplication-pass-inspection', kwargs={'pk': app.id}))
        # Certify
        resp = self.client.post(reverse('transactions:inspectionapplication-certify', kwargs={'pk': app.id}), {
            'certificate_no': 'CIQ001',
            'origin_certificate_no': 'CO001'
        }, format='json')
        assert resp.status_code == 200
        app.refresh_from_db()
        assert app.status == 'certified'

    def test_unauthenticated_customs_rejected(self):
        url = reverse('transactions:customsdeclaration-list')
        response = self.client.get(url)
        assert response.status_code in (401, 403)

    def test_unauthenticated_inspection_rejected(self):
        url = reverse('transactions:inspectionapplication-list')
        response = self.client.get(url)
        assert response.status_code in (401, 403)
