import pytest
from django.test import TestCase
from datetime import date
from decimal import Decimal
from apps.transactions.models import (
    Transaction, Contract, CustomsDeclaration, ForexSettlement, TaxRefundApplication
)
from apps.transactions.services import ShipmentService, CustomsService, ForexService, TaxRefundService
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


def create_cleared_and_forex_verified(seller_company, buyer_company, carrier_company,
                                       customs_company, forex_company, seller_user, carrier_user, customs_user, forex_user):
    """创建已放行报关单并完成外汇核销"""
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
        product_name='Cotton T-Shirt', product_spec='100% Cotton',
        quantity=1000, unit='pcs', unit_price=10.00,
        total_amount=10000.00, currency='USD', status='effective'
    )
    shipment = ShipmentService.create_shipment(
        user=seller_user, contract_id=contract.id,
        carrier_id=carrier_company.id,
        port_of_loading='Shanghai', port_of_discharge='Los Angeles'
    )
    ShipmentService.book(shipment.id, carrier_user, 'BK001', 'OOCL', date(2026, 10, 1), date(2026, 11, 1))
    ShipmentService.load(shipment.id, carrier_user)
    ShipmentService.issue_bl(shipment.id, carrier_user, bl_no='BL001')
    # 创建报关单（需要 shipment 为 shipped 状态）
    decl = CustomsService.create_declaration(
        user=seller_user, shipment_id=shipment.id,
        customs_office_id=customs_company.id,
        hs_code='610910', goods_name='Cotton T-Shirt',
        quantity=Decimal('1000'), unit_value=Decimal('10.00'),
        total_value=Decimal('10000.00'), currency='USD'
    )
    CustomsService.review(decl.id, customs_user)
    CustomsService.assess(decl.id, customs_user)
    CustomsService.clear(decl.id, customs_user)
    # 报关放行后手动设置 shipment 为 arrived
    from django.utils import timezone as tz
    shipment.status = 'arrived'
    shipment.arrived_at = tz.now()
    shipment.save(update_fields=['status', 'arrived_at'])
    decl.refresh_from_db()
    # 创建并核销外汇
    settlement = ForexService.create_settlement(
        user=seller_user, declaration_id=decl.id,
        forex_bureau_id=forex_company.id
    )
    ForexService.verify(settlement.id, forex_user)
    return decl


class TaxRefundServiceTest(TestCase):
    def setUp(self):
        from django.core.management import call_command
        call_command('init_trade_roles')

        self.exporter = User.objects.create_user(username='ts_exp', password='testpass', email='tse@test.com')
        self.carrier_user = User.objects.create_user(username='ts_car', password='testpass', email='tsc@test.com')
        self.customs_user = User.objects.create_user(username='ts_cus', password='testpass', email='tsu@test.com')
        self.forex_user = User.objects.create_user(username='ts_for', password='testpass', email='tsf@test.com')
        self.tax_user = User.objects.create_user(username='ts_tax', password='testpass', email='tst@test.com')
        self.buyer_user = User.objects.create_user(username='ts_buy', password='testpass', email='tsb@test.com')
        self.exporter_company = create_company_for_user(self.exporter, '_TS出口商')
        self.carrier_company = create_company_for_user(self.carrier_user, '_TS货运')
        self.customs_company = create_company_for_user(self.customs_user, '_TS海关')
        self.forex_company = create_company_for_user(self.forex_user, '_TS外汇局')
        self.tax_company = create_company_for_user(self.tax_user, '_TS税务局')
        self.buyer_company = create_company_for_user(self.buyer_user, '_TS买方')

        setup_role(self.exporter, self.exporter_company, 'exporter')
        setup_role(self.carrier_user, self.carrier_company, 'shipping')
        setup_role(self.customs_user, self.customs_company, 'customs')
        setup_role(self.forex_user, self.forex_company, 'forex')
        setup_role(self.tax_user, self.tax_company, 'tax')

        self.declaration = create_cleared_and_forex_verified(
            self.exporter_company, self.buyer_company, self.carrier_company,
            self.customs_company, self.forex_company,
            self.exporter, self.carrier_user, self.customs_user, self.forex_user
        )

    def test_calculate_refund_rate_textile(self):
        rate = TaxRefundService.calculate_refund_rate('610910')
        assert rate == Decimal('0.13')

    def test_calculate_refund_rate_electronics(self):
        rate = TaxRefundService.calculate_refund_rate('851712')
        assert rate == Decimal('0.13')

    def test_calculate_refund_rate_food(self):
        rate = TaxRefundService.calculate_refund_rate('210690')
        assert rate == Decimal('0.09')

    def test_calculate_refund_rate_default(self):
        rate = TaxRefundService.calculate_refund_rate('999999')
        assert rate == Decimal('0.11')

    def test_create_application_success(self):
        app = TaxRefundService.create_application(
            user=self.exporter,
            declaration_id=self.declaration.id,
            tax_bureau_id=self.tax_company.id
        )
        assert app.applicant == self.exporter_company
        assert app.tax_bureau == self.tax_company
        assert app.status == 'applied'
        assert app.refund_rate == Decimal('0.13')
        assert app.refund_amount == Decimal('1300.00')

    def test_create_application_without_forex_verified_rejected(self):
        # 需要一个报关单没有外汇核销
        self.product = Product.objects.create(code='FIX-P0001', name='Test Product', category='electronics', unit='PCS')
        transaction = Transaction.objects.create(
            buyer=self.buyer_company, seller=self.exporter_company,
            product=self.product, quantity=1000, unit_price=10.00,
            status='in_progress', created_by=self.exporter
        )
        contract = Contract.objects.create(
            contract_no='TS-NF-001', transaction=transaction,
            trade_term='CIF', payment_term='L/C at sight',
            delivery_time=date(2026, 12, 31),
            port_of_loading='Shanghai', port_of_discharge='Los Angeles',
            product_name='Test', product_spec='Test',
            quantity=1000, unit='pcs', unit_price=10.00,
            total_amount=10000.00, currency='USD', status='effective'
        )
        shipment = ShipmentService.create_shipment(
            user=self.exporter, contract_id=contract.id,
            carrier_id=self.carrier_company.id,
            port_of_loading='Shanghai', port_of_discharge='Los Angeles'
        )
        ShipmentService.book(shipment.id, self.carrier_user, 'BK002', 'OOCL', date(2026, 10, 1), date(2026, 11, 1))
        ShipmentService.load(shipment.id, self.carrier_user)
        ShipmentService.issue_bl(shipment.id, self.carrier_user, bl_no='BL002')
        decl = CustomsService.create_declaration(
            user=self.exporter, shipment_id=shipment.id,
            customs_office_id=self.customs_company.id,
            hs_code='610910', goods_name='Test',
            quantity=Decimal('1000'), unit_value=Decimal('10.00'),
            total_value=Decimal('10000.00')
        )
        CustomsService.review(decl.id, self.customs_user)
        CustomsService.assess(decl.id, self.customs_user)
        CustomsService.clear(decl.id, self.customs_user)
        # 报关放行后手动设置 shipment 为 arrived，但不做外汇核销
        from django.utils import timezone as tz
        shipment.status = 'arrived'
        shipment.arrived_at = tz.now()
        shipment.save(update_fields=['status', 'arrived_at'])
        # 不做外汇核销，直接申请退税
        with pytest.raises(ValueError, match='外汇尚未核销或结汇'):
            TaxRefundService.create_application(
                user=self.exporter,
                declaration_id=decl.id,
                tax_bureau_id=self.tax_company.id
            )

    def test_review_by_tax_success(self):
        app = TaxRefundService.create_application(
            user=self.exporter,
            declaration_id=self.declaration.id,
            tax_bureau_id=self.tax_company.id
        )
        result = TaxRefundService.review(app.id, self.tax_user)
        assert result.status == 'reviewing'
        assert result.reviewing_at is not None

    def test_approve_by_tax_success(self):
        app = TaxRefundService.create_application(
            user=self.exporter,
            declaration_id=self.declaration.id,
            tax_bureau_id=self.tax_company.id
        )
        TaxRefundService.review(app.id, self.tax_user)
        result = TaxRefundService.approve(app.id, self.tax_user)
        assert result.status == 'approved'
        assert result.approved_at is not None

    def test_refund_by_tax_success(self):
        app = TaxRefundService.create_application(
            user=self.exporter,
            declaration_id=self.declaration.id,
            tax_bureau_id=self.tax_company.id
        )
        TaxRefundService.review(app.id, self.tax_user)
        TaxRefundService.approve(app.id, self.tax_user)
        result = TaxRefundService.refund(app.id, self.tax_user)
        assert result.status == 'refunded'
        assert result.refunded_at is not None

    def test_reject_by_tax_success(self):
        app = TaxRefundService.create_application(
            user=self.exporter,
            declaration_id=self.declaration.id,
            tax_bureau_id=self.tax_company.id
        )
        result = TaxRefundService.reject(app.id, self.tax_user, reason='单据不齐全')
        assert result.status == 'rejected'
        assert result.rejected_at is not None

    def test_review_by_exporter_rejected(self):
        app = TaxRefundService.create_application(
            user=self.exporter,
            declaration_id=self.declaration.id,
            tax_bureau_id=self.tax_company.id
        )
        with pytest.raises(ValueError, match='只有税务局角色才能审核'):
            TaxRefundService.review(app.id, self.exporter)
