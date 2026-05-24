import pytest
from django.test import TestCase
from datetime import date
from decimal import Decimal
from apps.transactions.models import (
    Transaction, Contract, Shipment, CustomsDeclaration, ForexSettlement
)
from apps.transactions.services import ShipmentService, CustomsService, ForexService
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


def create_cleared_declaration(seller_company, buyer_company, carrier_company,
                                customs_company, seller_user, carrier_user, customs_user):
    """Create a cleared customs declaration with an arrived shipment.

    The order of operations matters:
    1. Shipment must be 'shipped' before customs declaration can be created
    2. Customs flow runs to completion (declared -> reviewing -> assessed -> cleared)
    3. After customs is cleared, shipment is manually set to 'arrived' for forex eligibility
       (arrive() requires 'shipped' status which is already past)
    """
    from django.utils import timezone

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
    # Shipment is now 'shipped' - create declaration while status is still 'shipped'
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
    # Customs is cleared. Now set shipment to 'arrived' for forex eligibility.
    # We cannot call arrive() because it requires status=='shipped' which is already past.
    shipment.status = 'arrived'
    shipment.arrived_at = timezone.now()
    shipment.save(update_fields=['status', 'arrived_at'])
    decl.refresh_from_db()
    return decl


class ForexServiceTest(TestCase):
    def setUp(self):
        from django.core.management import call_command
        call_command('init_trade_roles')

        self.exporter = User.objects.create_user(username='fs_exp', password='testpass', email='fse@test.com')
        self.carrier_user = User.objects.create_user(username='fs_car', password='testpass', email='fsc@test.com')
        self.customs_user = User.objects.create_user(username='fs_cus', password='testpass', email='fsu@test.com')
        self.forex_user = User.objects.create_user(username='fs_for', password='testpass', email='fsf@test.com')
        self.buyer_user = User.objects.create_user(username='fs_buy', password='testpass', email='fsb@test.com')
        self.exporter_company = create_company_for_user(self.exporter, '_FS出口商')
        self.carrier_company = create_company_for_user(self.carrier_user, '_FS货运')
        self.customs_company = create_company_for_user(self.customs_user, '_FS海关')
        self.forex_company = create_company_for_user(self.forex_user, '_FS外汇局')
        self.buyer_company = create_company_for_user(self.buyer_user, '_FS买方')

        setup_role(self.exporter, self.exporter_company, 'exporter')
        setup_role(self.carrier_user, self.carrier_company, 'shipping')
        setup_role(self.customs_user, self.customs_company, 'customs')
        setup_role(self.forex_user, self.forex_company, 'forex')

        self.declaration = create_cleared_declaration(
            self.exporter_company, self.buyer_company, self.carrier_company,
            self.customs_company, self.exporter, self.carrier_user, self.customs_user
        )

    def test_get_exchange_rate_usd(self):
        rate = ForexService.get_exchange_rate('USD')
        assert Decimal('7.15') <= rate <= Decimal('7.25')

    def test_get_exchange_rate_cny(self):
        rate = ForexService.get_exchange_rate('CNY')
        assert rate == Decimal('1.0000')

    def test_get_exchange_rate_eur(self):
        rate = ForexService.get_exchange_rate('EUR')
        assert Decimal('7.74') <= rate <= Decimal('7.86')

    def test_create_settlement_success(self):
        settlement = ForexService.create_settlement(
            user=self.exporter,
            declaration_id=self.declaration.id,
            forex_bureau_id=self.forex_company.id
        )
        assert settlement.applicant == self.exporter_company
        assert settlement.forex_bureau == self.forex_company
        assert settlement.status == 'applied'
        assert settlement.foreign_currency == 'USD'
        assert settlement.foreign_amount == Decimal('10000.00')
        assert Decimal('7.15') <= settlement.reference_rate <= Decimal('7.25')

    def test_create_settlement_non_exporter_rejected(self):
        with pytest.raises(ValueError, match='只有出口商角色才能申请外汇核销'):
            ForexService.create_settlement(
                user=self.forex_user,
                declaration_id=self.declaration.id,
                forex_bureau_id=self.forex_company.id
            )

    def test_create_settlement_not_cleared_rejected(self):
        self.product = Product.objects.create(code='FIX-P0001', name='Test Product', category='electronics', unit='PCS')
        contract = Contract.objects.create(
            contract_no='FS-NC-001',
            transaction=Transaction.objects.create(
                buyer=self.buyer_company, seller=self.exporter_company,
                product=self.product, quantity=1000, unit_price=10.00,
                status='in_progress', created_by=self.exporter
            ),
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
        # Do NOT call arrive() here - CustomsService.create_declaration requires shipped status.
        # The declaration stays in 'declared' status, which triggers the 'not cleared' error.
        decl = CustomsService.create_declaration(
            user=self.exporter, shipment_id=shipment.id,
            customs_office_id=self.customs_company.id,
            hs_code='610910', goods_name='Test',
            quantity=Decimal('1000'), unit_value=Decimal('10.00'),
            total_value=Decimal('10000.00')
        )
        with pytest.raises(ValueError, match='报关单未放行'):
            ForexService.create_settlement(
                user=self.exporter, declaration_id=decl.id,
                forex_bureau_id=self.forex_company.id
            )

    def test_verify_by_forex_success(self):
        settlement = ForexService.create_settlement(
            user=self.exporter, declaration_id=self.declaration.id,
            forex_bureau_id=self.forex_company.id
        )
        result = ForexService.verify(settlement.id, self.forex_user)
        assert result.status == 'verified'
        assert result.verified_at is not None

    def test_settle_by_forex_success(self):
        settlement = ForexService.create_settlement(
            user=self.exporter, declaration_id=self.declaration.id,
            forex_bureau_id=self.forex_company.id
        )
        ForexService.verify(settlement.id, self.forex_user)
        result = ForexService.settle(settlement.id, self.forex_user)
        assert result.status == 'settled'
        assert result.settlement_rate > 0
        assert result.settlement_cny_amount > 0
        assert result.settled_at is not None

    def test_reject_by_forex_success(self):
        settlement = ForexService.create_settlement(
            user=self.exporter, declaration_id=self.declaration.id,
            forex_bureau_id=self.forex_company.id
        )
        result = ForexService.reject(settlement.id, self.forex_user, reason='单据不齐全')
        assert result.status == 'rejected'
        assert result.rejected_at is not None

    def test_verify_by_exporter_rejected(self):
        settlement = ForexService.create_settlement(
            user=self.exporter, declaration_id=self.declaration.id,
            forex_bureau_id=self.forex_company.id
        )
        with pytest.raises(ValueError, match='只有外汇局角色才能核销'):
            ForexService.verify(settlement.id, self.exporter)
