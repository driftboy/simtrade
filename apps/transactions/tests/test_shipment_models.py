import pytest
from django.test import TestCase
from datetime import date
from decimal import Decimal
from apps.transactions.models import Transaction, Contract, Shipment
from apps.users.models import User
from apps.roles.services import CompanyService
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


class ShipmentModelTest(TestCase):
    def setUp(self):
        self.exporter = User.objects.create_user(username='sh_mod_exp', password='testpass', email='sme@test.com')
        self.carrier_user = User.objects.create_user(username='sh_mod_car', password='testpass', email='smc@test.com')
        self.buyer_user = User.objects.create_user(username='sh_mod_buy', password='testpass', email='smb@test.com')
        self.exporter_company = create_company_for_user(self.exporter, '_货运出口商')
        self.carrier_company = create_company_for_user(self.carrier_user, '_货运公司')
        self.buyer_company = create_company_for_user(self.buyer_user, '_货运买方')
        self.transaction = Transaction.objects.create(
            buyer=self.buyer_company,
            seller=self.exporter_company,
            product_id=1, quantity=1000, unit_price=10.00,
            status='in_progress', created_by=self.exporter
        )
        self.contract = Contract.objects.create(
            contract_no='SM-TEST-001',
            transaction=self.transaction,
            trade_term='CIF', payment_term='L/C at sight',
            delivery_time=date(2026, 12, 31),
            port_of_loading='Shanghai', port_of_discharge='Los Angeles',
            product_name='Test Product', product_spec='Spec',
            quantity=1000, unit='pcs', unit_price=10.00,
            total_amount=10000.00, currency='USD',
            status='effective'
        )

    def test_create_shipment(self):
        shipment = Shipment.objects.create(
            contract=self.contract,
            shipper=self.exporter_company,
            carrier=self.carrier_company,
            port_of_loading='Shanghai',
            port_of_discharge='Los Angeles',
            freight_amount=Decimal('300.00'),
            freight_currency='USD',
            created_by=self.exporter
        )
        assert shipment.shipment_no is not None
        assert shipment.shipment_no.startswith('SH')
        assert shipment.status == 'draft'
        assert str(shipment) == shipment.shipment_no

    def test_shipment_no_unique(self):
        s1 = Shipment.objects.create(
            contract=self.contract,
            shipper=self.exporter_company,
            carrier=self.carrier_company,
            port_of_loading='Shanghai',
            port_of_discharge='Los Angeles',
            created_by=self.exporter
        )
        # 需要另一个合同因为 OneToOne
        txn2 = Transaction.objects.create(
            buyer=self.buyer_company, seller=self.exporter_company,
            product_id=2, quantity=100, unit_price=5.00,
            created_by=self.exporter
        )
        c2 = Contract.objects.create(
            contract_no='SM-TEST-002', transaction=txn2,
            trade_term='FOB', payment_term='T/T',
            delivery_time=date(2026, 12, 31),
            port_of_loading='Shanghai', port_of_discharge='Tokyo',
            product_name='P2', product_spec='',
            quantity=100, unit='pcs', unit_price=5.00,
            total_amount=500.00, currency='USD', status='effective'
        )
        s2 = Shipment.objects.create(
            contract=c2,
            shipper=self.exporter_company,
            carrier=self.carrier_company,
            port_of_loading='Shanghai',
            port_of_discharge='Tokyo',
            created_by=self.exporter
        )
        assert s1.shipment_no != s2.shipment_no

    def test_shipment_status_choices(self):
        valid = [c[0] for c in Shipment.Status.choices]
        assert 'draft' in valid
        assert 'booked' in valid
        assert 'loaded' in valid
        assert 'shipped' in valid
        assert 'arrived' in valid
        assert 'cancelled' in valid
