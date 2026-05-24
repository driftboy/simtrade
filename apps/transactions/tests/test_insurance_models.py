import pytest
from django.test import TestCase
from datetime import date
from decimal import Decimal
from apps.transactions.models import Transaction, Contract, Shipment, InsurancePolicy
from apps.users.models import User
from apps.roles.services import CompanyService
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


class InsurancePolicyModelTest(TestCase):
    def setUp(self):
        self.exporter = User.objects.create_user(username='in_mod_exp', password='testpass', email='ime@test.com')
        self.insurer_user = User.objects.create_user(username='in_mod_ins', password='testpass', email='imi@test.com')
        self.buyer_user = User.objects.create_user(username='in_mod_buy', password='testpass', email='imb@test.com')
        self.exporter_company = create_company_for_user(self.exporter, '_保险出口商')
        self.insurer_company = create_company_for_user(self.insurer_user, '_保险公司')
        self.buyer_company = create_company_for_user(self.buyer_user, '_保险买方')
        self.product = Product.objects.create(code='FIX-P0001', name='Test Product', category='electronics', unit='PCS')
        self.transaction = Transaction.objects.create(
            buyer=self.buyer_company, seller=self.exporter_company,
            product=self.product, quantity=1000, unit_price=10.00,
            status='in_progress', created_by=self.exporter
        )
        self.contract = Contract.objects.create(
            contract_no='IN-TEST-001', transaction=self.transaction,
            trade_term='CIF', payment_term='L/C at sight',
            delivery_time=date(2026, 12, 31),
            port_of_loading='Shanghai', port_of_discharge='Los Angeles',
            product_name='Test Product', product_spec='Spec',
            quantity=1000, unit='pcs', unit_price=10.00,
            total_amount=10000.00, currency='USD', status='effective'
        )

    def test_create_insurance_policy(self):
        policy = InsurancePolicy.objects.create(
            contract=self.contract,
            insured=self.exporter_company,
            insurer=self.insurer_company,
            cargo_description='1000件棉质T恤',
            insured_amount=Decimal('11000.00'),
            premium=Decimal('88.00'),
            premium_currency='CNY',
            coverage_type='all_risk',
            created_by=self.exporter
        )
        assert policy.policy_no is not None
        assert policy.policy_no.startswith('IN')
        assert policy.status == 'applied'
        assert str(policy) == policy.policy_no

    def test_policy_coverage_types(self):
        valid = [c[0] for c in InsurancePolicy.CoverageType.choices]
        assert 'fpa' in valid
        assert 'wa' in valid
        assert 'all_risk' in valid

    def test_policy_status_choices(self):
        valid = [c[0] for c in InsurancePolicy.Status.choices]
        assert 'applied' in valid
        assert 'underwritten' in valid
        assert 'issued' in valid
        assert 'cancelled' in valid
