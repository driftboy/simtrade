import pytest
from django.test import TestCase
from datetime import date
from decimal import Decimal
from apps.transactions.models import Transaction, Contract, Shipment, InspectionApplication
from apps.transactions.services import ShipmentService, InspectionService
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


def create_effective_contract(seller_company, buyer_company, seller_user):
    product = Product.objects.get_or_create(code='HLP-P01', defaults={'name': 'Helper Product', 'category': 'electronics', 'unit': 'PCS'})[0]
    transaction = Transaction.objects.create(
        buyer=buyer_company, seller=seller_company,
        product=product, quantity=1000, unit_price=10.00,
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


class InspectionServiceTest(TestCase):
    def setUp(self):
        from django.core.management import call_command
        call_command('init_trade_roles')

        self.exporter = User.objects.create_user(username='is_exp2', password='testpass', email='is2e@test.com')
        self.carrier_user = User.objects.create_user(username='is_car2', password='testpass', email='is2c@test.com')
        self.inspector_user = User.objects.create_user(username='is_ins2', password='testpass', email='is2i@test.com')
        self.buyer_user = User.objects.create_user(username='is_buy2', password='testpass', email='is2b@test.com')
        self.exporter_company = create_company_for_user(self.exporter, '_IS2出口商')
        self.carrier_company = create_company_for_user(self.carrier_user, '_IS2货运')
        self.inspector_company = create_company_for_user(self.inspector_user, '_IS2商检')
        self.buyer_company = create_company_for_user(self.buyer_user, '_IS2买方')

        setup_role(self.exporter, self.exporter_company, 'exporter')
        setup_role(self.carrier_user, self.carrier_company, 'shipping')
        setup_role(self.inspector_user, self.inspector_company, 'inspection')

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

    def test_calculate_fee_legal(self):
        fee = InspectionService.calculate_fee('legal', Decimal('10000.00'))
        assert fee == Decimal('50.00')  # 10000 * 0.5%

    def test_calculate_fee_general(self):
        fee = InspectionService.calculate_fee('general', Decimal('10000.00'))
        assert fee == Decimal('30.00')  # 10000 * 0.3%

    def test_create_application_success(self):
        app = InspectionService.create_application(
            user=self.exporter,
            shipment_id=self.shipment.id,
            inspector_id=self.inspector_company.id,
            inspection_type='legal',
            product_name='Cotton T-Shirt',
            product_spec='100% Cotton',
            quantity=Decimal('1000'),
            goods_value=Decimal('10000.00')
        )
        assert app.applicant == self.exporter_company
        assert app.inspector == self.inspector_company
        assert app.status == 'applied'
        assert app.fee == Decimal('50.00')

    def test_create_application_non_exporter_rejected(self):
        with pytest.raises(ValueError, match='只有出口商角色才能报检'):
            InspectionService.create_application(
                user=self.inspector_user,
                shipment_id=self.shipment.id,
                inspector_id=self.inspector_company.id,
                inspection_type='legal',
                product_name='Test', quantity=Decimal('100'),
                goods_value=Decimal('1000.00')
            )

    def test_inspect_by_inspector_success(self):
        app = InspectionService.create_application(
            user=self.exporter, shipment_id=self.shipment.id,
            inspector_id=self.inspector_company.id,
            inspection_type='legal', product_name='Test',
            quantity=Decimal('100'), goods_value=Decimal('1000.00')
        )
        result = InspectionService.inspect(app.id, self.inspector_user)
        assert result.status == 'inspecting'
        assert result.inspecting_at is not None

    def test_pass_by_inspector_success(self):
        app = InspectionService.create_application(
            user=self.exporter, shipment_id=self.shipment.id,
            inspector_id=self.inspector_company.id,
            inspection_type='legal', product_name='Test',
            quantity=Decimal('100'), goods_value=Decimal('1000.00')
        )
        InspectionService.inspect(app.id, self.inspector_user)
        result = InspectionService.pass_inspection(app.id, self.inspector_user)
        assert result.status == 'passed'
        assert result.passed_at is not None

    def test_certify_by_inspector_success(self):
        app = InspectionService.create_application(
            user=self.exporter, shipment_id=self.shipment.id,
            inspector_id=self.inspector_company.id,
            inspection_type='legal', product_name='Test',
            quantity=Decimal('100'), goods_value=Decimal('1000.00')
        )
        InspectionService.inspect(app.id, self.inspector_user)
        InspectionService.pass_inspection(app.id, self.inspector_user)
        result = InspectionService.certify(
            app.id, self.inspector_user,
            certificate_no='CIQ20260001',
            origin_certificate_no='CO20260001'
        )
        assert result.status == 'certified'
        assert result.certificate_no == 'CIQ20260001'
        assert result.origin_certificate_no == 'CO20260001'
        assert result.certified_at is not None

    def test_fail_by_inspector_success(self):
        app = InspectionService.create_application(
            user=self.exporter, shipment_id=self.shipment.id,
            inspector_id=self.inspector_company.id,
            inspection_type='legal', product_name='Test',
            quantity=Decimal('100'), goods_value=Decimal('1000.00')
        )
        InspectionService.inspect(app.id, self.inspector_user)
        result = InspectionService.fail_inspection(app.id, self.inspector_user, reason='不合格')
        assert result.status == 'failed'
        assert result.failed_at is not None

    def test_inspect_by_exporter_rejected(self):
        app = InspectionService.create_application(
            user=self.exporter, shipment_id=self.shipment.id,
            inspector_id=self.inspector_company.id,
            inspection_type='legal', product_name='Test',
            quantity=Decimal('100'), goods_value=Decimal('1000.00')
        )
        with pytest.raises(ValueError, match='只有商检机构角色才能检验'):
            InspectionService.inspect(app.id, self.exporter)
