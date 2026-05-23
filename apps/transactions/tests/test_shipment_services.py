import pytest
from django.test import TestCase
from datetime import date
from decimal import Decimal
from apps.transactions.models import Transaction, Contract, Shipment
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


def create_effective_contract(seller_company, buyer_company, seller_user, trade_term='CIF'):
    transaction = Transaction.objects.create(
        buyer=buyer_company, seller=seller_company,
        product_id=1, quantity=1000, unit_price=10.00,
        status='in_progress', created_by=seller_user
    )
    contract = Contract.objects.create(
        contract_no=f'SC{Transaction.objects.count()+1:04d}',
        transaction=transaction,
        trade_term=trade_term, payment_term='L/C at sight',
        delivery_time=date(2026, 12, 31),
        port_of_loading='Shanghai', port_of_discharge='Los Angeles',
        product_name='Test Product', product_spec='Spec',
        quantity=1000, unit='pcs', unit_price=10.00,
        total_amount=10000.00, currency='USD', status='effective'
    )
    return contract


class ShipmentServiceTest(TestCase):
    def setUp(self):
        from django.core.management import call_command
        call_command('init_trade_roles')

        self.exporter = User.objects.create_user(username='ss_exp', password='testpass', email='sse@test.com')
        self.carrier_user = User.objects.create_user(username='ss_car', password='testpass', email='ssc@test.com')
        self.buyer_user = User.objects.create_user(username='ss_buy', password='testpass', email='ssb@test.com')
        self.exporter_company = create_company_for_user(self.exporter, '_SS出口商')
        self.carrier_company = create_company_for_user(self.carrier_user, '_SS货运公司')
        self.buyer_company = create_company_for_user(self.buyer_user, '_SS买方')

        setup_role(self.exporter, self.exporter_company, 'exporter')
        setup_role(self.carrier_user, self.carrier_company, 'shipping')
        self.contract = create_effective_contract(
            self.exporter_company, self.buyer_company, self.exporter
        )

    def test_create_shipment_success(self):
        shipment = ShipmentService.create_shipment(
            user=self.exporter,
            contract_id=self.contract.id,
            carrier_id=self.carrier_company.id,
            port_of_loading='Shanghai',
            port_of_discharge='Los Angeles'
        )
        assert shipment.shipper == self.exporter_company
        assert shipment.carrier == self.carrier_company
        assert shipment.status == 'draft'

    def test_create_shipment_non_exporter_rejected(self):
        with pytest.raises(ValueError, match='只有出口商角色才能创建货运订单'):
            ShipmentService.create_shipment(
                user=self.carrier_user,
                contract_id=self.contract.id,
                carrier_id=self.carrier_company.id,
                port_of_loading='Shanghai',
                port_of_discharge='Los Angeles'
            )

    def test_calculate_freight_cif(self):
        amount = ShipmentService.calculate_freight(self.contract.id)
        assert amount == Decimal('300.00')  # 10000 * 3%

    def test_calculate_freight_fob(self):
        fob_contract = create_effective_contract(
            self.exporter_company, self.buyer_company, self.exporter, trade_term='FOB'
        )
        amount = ShipmentService.calculate_freight(fob_contract.id)
        assert amount == Decimal('0.00')

    def test_book_by_carrier_success(self):
        shipment = ShipmentService.create_shipment(
            user=self.exporter, contract_id=self.contract.id,
            carrier_id=self.carrier_company.id,
            port_of_loading='Shanghai', port_of_discharge='Los Angeles'
        )
        result = ShipmentService.book(
            shipment.id, self.carrier_user,
            booking_no='BK20260001', vessel_name='OOCL PIRAEUS',
            etd=date(2026, 10, 1), eta=date(2026, 11, 1)
        )
        assert result.status == 'booked'
        assert result.booking_no == 'BK20260001'
        assert result.booked_at is not None

    def test_book_by_exporter_rejected(self):
        shipment = ShipmentService.create_shipment(
            user=self.exporter, contract_id=self.contract.id,
            carrier_id=self.carrier_company.id,
            port_of_loading='Shanghai', port_of_discharge='Los Angeles'
        )
        with pytest.raises(ValueError, match='只有货运公司角色才能订舱'):
            ShipmentService.book(
                shipment.id, self.exporter,
                booking_no='BK001', vessel_name='Vessel',
                etd=date(2026, 10, 1), eta=date(2026, 11, 1)
            )

    def test_load_by_carrier_success(self):
        shipment = ShipmentService.create_shipment(
            user=self.exporter, contract_id=self.contract.id,
            carrier_id=self.carrier_company.id,
            port_of_loading='Shanghai', port_of_discharge='Los Angeles'
        )
        ShipmentService.book(
            shipment.id, self.carrier_user,
            booking_no='BK001', vessel_name='Vessel',
            etd=date(2026, 10, 1), eta=date(2026, 11, 1)
        )
        result = ShipmentService.load(shipment.id, self.carrier_user, container_no='MSKU1234567')
        assert result.status == 'loaded'
        assert result.container_no == 'MSKU1234567'

    def test_issue_bl_by_carrier_success(self):
        shipment = ShipmentService.create_shipment(
            user=self.exporter, contract_id=self.contract.id,
            carrier_id=self.carrier_company.id,
            port_of_loading='Shanghai', port_of_discharge='Los Angeles'
        )
        ShipmentService.book(shipment.id, self.carrier_user, booking_no='BK001', vessel_name='V', etd=date(2026, 10, 1), eta=date(2026, 11, 1))
        ShipmentService.load(shipment.id, self.carrier_user)
        result = ShipmentService.issue_bl(shipment.id, self.carrier_user, bl_no='B/L NO.123456')
        assert result.status == 'shipped'
        assert result.bl_no == 'B/L NO.123456'

    def test_arrive_by_carrier_success(self):
        shipment = ShipmentService.create_shipment(
            user=self.exporter, contract_id=self.contract.id,
            carrier_id=self.carrier_company.id,
            port_of_loading='Shanghai', port_of_discharge='Los Angeles'
        )
        ShipmentService.book(shipment.id, self.carrier_user, booking_no='BK001', vessel_name='V', etd=date(2026, 10, 1), eta=date(2026, 11, 1))
        ShipmentService.load(shipment.id, self.carrier_user)
        ShipmentService.issue_bl(shipment.id, self.carrier_user, bl_no='BL001')
        result = ShipmentService.arrive(shipment.id, self.carrier_user)
        assert result.status == 'arrived'
        assert result.arrived_at is not None

    def test_cancel_draft_by_exporter(self):
        shipment = ShipmentService.create_shipment(
            user=self.exporter, contract_id=self.contract.id,
            carrier_id=self.carrier_company.id,
            port_of_loading='Shanghai', port_of_discharge='Los Angeles'
        )
        result = ShipmentService.cancel(shipment.id, self.exporter, reason='不需要了')
        assert result.status == 'cancelled'

    def test_cancel_loaded_rejected(self):
        shipment = ShipmentService.create_shipment(
            user=self.exporter, contract_id=self.contract.id,
            carrier_id=self.carrier_company.id,
            port_of_loading='Shanghai', port_of_discharge='Los Angeles'
        )
        ShipmentService.book(shipment.id, self.carrier_user, booking_no='BK001', vessel_name='V', etd=date(2026, 10, 1), eta=date(2026, 11, 1))
        ShipmentService.load(shipment.id, self.carrier_user)
        with pytest.raises(ValueError, match='订单状态不允许取消'):
            ShipmentService.cancel(shipment.id, self.exporter)
