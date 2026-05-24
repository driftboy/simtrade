import pytest
from django.test import TestCase
from datetime import date
from decimal import Decimal
from apps.transactions.models import Transaction, Contract, Shipment, CustomsDeclaration
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


class CustomsDeclarationModelTest(TestCase):
    def setUp(self):
        from django.core.management import call_command
        call_command('init_trade_roles')

        self.exporter = User.objects.create_user(username='cd_mod_exp', password='testpass', email='cde@test.com')
        self.carrier_user = User.objects.create_user(username='cd_mod_car', password='testpass', email='cdc@test.com')
        self.customs_user = User.objects.create_user(username='cd_mod_cus', password='testpass', email='cdcu@test.com')
        self.buyer_user = User.objects.create_user(username='cd_mod_buy', password='testpass', email='cdb@test.com')
        self.exporter_company = create_company_for_user(self.exporter, '_CD出口商')
        self.carrier_company = create_company_for_user(self.carrier_user, '_CD货运')
        self.customs_company = create_company_for_user(self.customs_user, '_CD海关')
        self.buyer_company = create_company_for_user(self.buyer_user, '_CD买方')

        setup_role(self.exporter, self.exporter_company, 'exporter')
        setup_role(self.carrier_user, self.carrier_company, 'shipping')

        # 创建已签发提单的货运
        self.product = Product.objects.create(code='FIX-P0001', name='Test Product', category='electronics', unit='PCS')
        transaction = Transaction.objects.create(
            buyer=self.buyer_company, seller=self.exporter_company,
            product=self.product, quantity=1000, unit_price=10.00,
            status='in_progress', created_by=self.exporter
        )
        contract = Contract.objects.create(
            contract_no='CD-TEST-001', transaction=transaction,
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

    def test_create_customs_declaration(self):
        decl = CustomsDeclaration.objects.create(
            shipment=self.shipment,
            declarant=self.exporter_company,
            customs_office=self.customs_company,
            hs_code='610910',
            goods_name='Cotton T-Shirt',
            quantity=Decimal('1000'),
            unit_value=Decimal('10.00'),
            total_value=Decimal('10000.00'),
            currency='USD',
            created_by=self.exporter
        )
        assert decl.declaration_no is not None
        assert decl.declaration_no.startswith('CD')
        assert decl.status == 'declared'
        assert str(decl) == decl.declaration_no

    def test_declaration_status_choices(self):
        valid = [c[0] for c in CustomsDeclaration.Status.choices]
        assert 'declared' in valid
        assert 'reviewing' in valid
        assert 'assessed' in valid
        assert 'cleared' in valid
        assert 'rejected' in valid
