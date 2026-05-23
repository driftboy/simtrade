import pytest
from django.test import TestCase
from datetime import date
from decimal import Decimal
from apps.transactions.models import Transaction, Contract, Shipment, CustomsDeclaration
from apps.transactions.services import ShipmentService, CustomsService
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


def create_effective_contract(seller_company, buyer_company, seller_user):
    transaction = Transaction.objects.create(
        buyer=buyer_company, seller=seller_company,
        product_id=1, quantity=1000, unit_price=10.00,
        status='in_progress', created_by=seller_user
    )
    contract = Contract.objects.create(
        contract_no=f'SC{Transaction.objects.count()+1:04d}',
        transaction=transaction,
        trade_term='CIF', payment_term='L/C at sight',
        delivery_time=date(2026, 12, 31),
        port_of_loading='Shanghai', port_of_discharge='Los Angeles',
        product_name='T-Shirt', product_spec='Cotton',
        quantity=1000, unit='pcs', unit_price=10.00,
        total_amount=10000.00, currency='USD', status='effective'
    )
    return contract


class CustomsServiceTest(TestCase):
    def setUp(self):
        from django.core.management import call_command
        call_command('init_trade_roles')

        self.exporter = User.objects.create_user(username='cs_exp', password='testpass', email='cse@test.com')
        self.carrier_user = User.objects.create_user(username='cs_car', password='testpass', email='csc@test.com')
        self.customs_user = User.objects.create_user(username='cs_cus', password='testpass', email='csu@test.com')
        self.buyer_user = User.objects.create_user(username='cs_buy', password='testpass', email='csb@test.com')
        self.exporter_company = create_company_for_user(self.exporter, '_CS出口商')
        self.carrier_company = create_company_for_user(self.carrier_user, '_CS货运')
        self.customs_company = create_company_for_user(self.customs_user, '_CS海关')
        self.buyer_company = create_company_for_user(self.buyer_user, '_CS买方')

        setup_role(self.exporter, self.exporter_company, 'exporter')
        setup_role(self.carrier_user, self.carrier_company, 'shipping')
        setup_role(self.customs_user, self.customs_company, 'customs')

        contract = create_effective_contract(
            self.exporter_company, self.buyer_company, self.exporter
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

    def test_create_declaration_success(self):
        decl = CustomsService.create_declaration(
            user=self.exporter,
            shipment_id=self.shipment.id,
            customs_office_id=self.customs_company.id,
            hs_code='610910',
            goods_name='Cotton T-Shirt',
            quantity=Decimal('1000'),
            unit_value=Decimal('10.00'),
            total_value=Decimal('10000.00'),
            currency='USD'
        )
        assert decl.declarant == self.exporter_company
        assert decl.customs_office == self.customs_company
        assert decl.status == 'declared'

    def test_create_declaration_non_exporter_rejected(self):
        with pytest.raises(ValueError, match='只有出口商角色才能申报报关'):
            CustomsService.create_declaration(
                user=self.customs_user,
                shipment_id=self.shipment.id,
                customs_office_id=self.customs_company.id,
                hs_code='610910',
                goods_name='Test',
                quantity=Decimal('1000'),
                unit_value=Decimal('10.00'),
                total_value=Decimal('10000.00')
            )

    def test_create_declaration_shipment_not_shipped_rejected(self):
        contract = create_effective_contract(
            self.exporter_company, self.buyer_company, self.exporter
        )
        shipment = ShipmentService.create_shipment(
            user=self.exporter, contract_id=contract.id,
            carrier_id=self.carrier_company.id,
            port_of_loading='Shanghai', port_of_discharge='Los Angeles'
        )
        with pytest.raises(ValueError, match='提单未签发'):
            CustomsService.create_declaration(
                user=self.exporter, shipment_id=shipment.id,
                customs_office_id=self.customs_company.id,
                hs_code='610910', goods_name='Test',
                quantity=Decimal('1000'), unit_value=Decimal('10.00'),
                total_value=Decimal('10000.00')
            )

    def test_calculate_duties_textile(self):
        duties = CustomsService.calculate_duties('610910', Decimal('10000.00'))
        assert duties['duty_rate'] == Decimal('0.10')
        assert duties['duty_amount'] == Decimal('1000.00')
        assert duties['vat_rate'] == Decimal('0.13')
        assert duties['vat_amount'] == Decimal('1430.00')  # (10000 + 1000) * 13%

    def test_calculate_duties_electronics(self):
        duties = CustomsService.calculate_duties('851712', Decimal('10000.00'))
        assert duties['duty_rate'] == Decimal('0.08')
        assert duties['duty_amount'] == Decimal('800.00')

    def test_calculate_duties_food(self):
        duties = CustomsService.calculate_duties('210690', Decimal('10000.00'))
        assert duties['duty_rate'] == Decimal('0.15')
        assert duties['vat_rate'] == Decimal('0.09')

    def test_calculate_duties_default(self):
        duties = CustomsService.calculate_duties('999999', Decimal('10000.00'))
        assert duties['duty_rate'] == Decimal('0.10')
        assert duties['vat_rate'] == Decimal('0.13')

    def test_review_by_customs_success(self):
        decl = CustomsService.create_declaration(
            user=self.exporter, shipment_id=self.shipment.id,
            customs_office_id=self.customs_company.id,
            hs_code='610910', goods_name='Test',
            quantity=Decimal('1000'), unit_value=Decimal('10.00'),
            total_value=Decimal('10000.00')
        )
        result = CustomsService.review(decl.id, self.customs_user)
        assert result.status == 'reviewing'
        assert result.reviewed_at is not None

    def test_assess_by_customs_success(self):
        decl = CustomsService.create_declaration(
            user=self.exporter, shipment_id=self.shipment.id,
            customs_office_id=self.customs_company.id,
            hs_code='610910', goods_name='Test',
            quantity=Decimal('1000'), unit_value=Decimal('10.00'),
            total_value=Decimal('10000.00')
        )
        CustomsService.review(decl.id, self.customs_user)
        result = CustomsService.assess(decl.id, self.customs_user)
        assert result.status == 'assessed'
        assert result.duty_amount == Decimal('1000.00')
        assert result.vat_amount == Decimal('1430.00')
        assert result.assessed_at is not None

    def test_clear_by_customs_success(self):
        decl = CustomsService.create_declaration(
            user=self.exporter, shipment_id=self.shipment.id,
            customs_office_id=self.customs_company.id,
            hs_code='610910', goods_name='Test',
            quantity=Decimal('1000'), unit_value=Decimal('10.00'),
            total_value=Decimal('10000.00')
        )
        CustomsService.review(decl.id, self.customs_user)
        CustomsService.assess(decl.id, self.customs_user)
        result = CustomsService.clear(decl.id, self.customs_user)
        assert result.status == 'cleared'
        assert result.cleared_at is not None

    def test_reject_by_customs_success(self):
        decl = CustomsService.create_declaration(
            user=self.exporter, shipment_id=self.shipment.id,
            customs_office_id=self.customs_company.id,
            hs_code='610910', goods_name='Test',
            quantity=Decimal('1000'), unit_value=Decimal('10.00'),
            total_value=Decimal('10000.00')
        )
        result = CustomsService.reject(decl.id, self.customs_user, reason='单据不齐全')
        assert result.status == 'rejected'
        assert result.rejected_at is not None

    def test_review_by_exporter_rejected(self):
        decl = CustomsService.create_declaration(
            user=self.exporter, shipment_id=self.shipment.id,
            customs_office_id=self.customs_company.id,
            hs_code='610910', goods_name='Test',
            quantity=Decimal('1000'), unit_value=Decimal('10.00'),
            total_value=Decimal('10000.00')
        )
        with pytest.raises(ValueError, match='只有海关角色才能审核'):
            CustomsService.review(decl.id, self.exporter)
