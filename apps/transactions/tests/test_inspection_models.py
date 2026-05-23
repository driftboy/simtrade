import pytest
from django.test import TestCase
from datetime import date
from decimal import Decimal
from apps.transactions.models import Transaction, Contract, Shipment, InspectionApplication
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


class InspectionApplicationModelTest(TestCase):
    def setUp(self):
        from django.core.management import call_command
        call_command('init_trade_roles')

        self.exporter = User.objects.create_user(username='ia_mod_exp', password='testpass', email='iae@test.com')
        self.carrier_user = User.objects.create_user(username='ia_mod_car', password='testpass', email='iac@test.com')
        self.inspector_user = User.objects.create_user(username='ia_mod_ins', password='testpass', email='iai@test.com')
        self.buyer_user = User.objects.create_user(username='ia_mod_buy', password='testpass', email='iab@test.com')
        self.exporter_company = create_company_for_user(self.exporter, '_IA出口商')
        self.carrier_company = create_company_for_user(self.carrier_user, '_IA货运')
        self.inspector_company = create_company_for_user(self.inspector_user, '_IA商检')
        self.buyer_company = create_company_for_user(self.buyer_user, '_IA买方')

        setup_role(self.exporter, self.exporter_company, 'exporter')
        setup_role(self.carrier_user, self.carrier_company, 'shipping')

        transaction = Transaction.objects.create(
            buyer=self.buyer_company, seller=self.exporter_company,
            product_id=1, quantity=1000, unit_price=10.00,
            status='in_progress', created_by=self.exporter
        )
        contract = Contract.objects.create(
            contract_no='IA-TEST-001', transaction=transaction,
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

    def test_create_inspection_application(self):
        app = InspectionApplication.objects.create(
            shipment=self.shipment,
            applicant=self.exporter_company,
            inspector=self.inspector_company,
            product_name='Cotton T-Shirt',
            product_spec='100% Cotton',
            quantity=Decimal('1000'),
            goods_value=Decimal('10000.00'),
            inspection_type='legal',
            fee=Decimal('50.00'),
            created_by=self.exporter
        )
        assert app.application_no is not None
        assert app.application_no.startswith('IA')
        assert app.status == 'applied'
        assert str(app) == app.application_no

    def test_inspection_status_choices(self):
        valid = [c[0] for c in InspectionApplication.Status.choices]
        assert 'applied' in valid
        assert 'inspecting' in valid
        assert 'passed' in valid
        assert 'certified' in valid
        assert 'failed' in valid

    def test_inspection_type_choices(self):
        valid = [c[0] for c in InspectionApplication.InspectionType.choices]
        assert 'legal' in valid
        assert 'general' in valid
