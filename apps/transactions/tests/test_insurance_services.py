import pytest
from django.test import TestCase
from datetime import date
from decimal import Decimal
from apps.transactions.models import Transaction, Contract, InsurancePolicy
from apps.transactions.services import InsuranceService
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
        product_name='Test Product', product_spec='Spec',
        quantity=1000, unit='pcs', unit_price=10.00,
        total_amount=10000.00, currency='USD', status='effective'
    )
    return contract


class InsuranceServiceTest(TestCase):
    def setUp(self):
        from django.core.management import call_command
        call_command('init_trade_roles')

        self.exporter = User.objects.create_user(username='is_exp', password='testpass', email='ise@test.com')
        self.insurer_user = User.objects.create_user(username='is_ins', password='testpass', email='isi@test.com')
        self.buyer_user = User.objects.create_user(username='is_buy', password='testpass', email='isb@test.com')
        self.exporter_company = create_company_for_user(self.exporter, '_IS出口商')
        self.insurer_company = create_company_for_user(self.insurer_user, '_IS保险公司')
        self.buyer_company = create_company_for_user(self.buyer_user, '_IS买方')

        setup_role(self.exporter, self.exporter_company, 'exporter')
        setup_role(self.insurer_user, self.insurer_company, 'insurance')
        self.contract = create_effective_contract(
            self.exporter_company, self.buyer_company, self.exporter
        )

    def test_calculate_premium_all_risk(self):
        """一切险：0.8%"""
        premium = InsuranceService.calculate_premium(Decimal('11000.00'), 'all_risk')
        assert premium == Decimal('88.00')

    def test_calculate_premium_fpa(self):
        """平安险：0.3%"""
        premium = InsuranceService.calculate_premium(Decimal('11000.00'), 'fpa')
        assert premium == Decimal('33.00')

    def test_calculate_premium_wa(self):
        """水渍险：0.5%"""
        premium = InsuranceService.calculate_premium(Decimal('11000.00'), 'wa')
        assert premium == Decimal('55.00')

    def test_create_policy_success(self):
        policy = InsuranceService.create_policy(
            user=self.exporter,
            contract_id=self.contract.id,
            insurer_id=self.insurer_company.id,
            coverage_type='all_risk',
            cargo_description='1000件棉质T恤'
        )
        assert policy.insured == self.exporter_company
        assert policy.insurer == self.insurer_company
        assert policy.status == 'applied'
        assert policy.premium == Decimal('88.00')  # 11000 * 0.8%
        assert policy.insured_amount == Decimal('11000.00')  # 10000 * 110%

    def test_create_policy_non_exporter_rejected(self):
        with pytest.raises(ValueError, match='只有出口商角色才能投保'):
            InsuranceService.create_policy(
                user=self.insurer_user,
                contract_id=self.contract.id,
                insurer_id=self.insurer_company.id,
                coverage_type='all_risk',
                cargo_description='Test'
            )

    def test_underwrite_by_insurer_success(self):
        policy = InsuranceService.create_policy(
            user=self.exporter, contract_id=self.contract.id,
            insurer_id=self.insurer_company.id,
            coverage_type='all_risk', cargo_description='Test'
        )
        result = InsuranceService.underwrite(policy.id, self.insurer_user)
        assert result.status == 'underwritten'
        assert result.underwritten_at is not None

    def test_underwrite_by_exporter_rejected(self):
        policy = InsuranceService.create_policy(
            user=self.exporter, contract_id=self.contract.id,
            insurer_id=self.insurer_company.id,
            coverage_type='all_risk', cargo_description='Test'
        )
        with pytest.raises(ValueError, match='只有保险公司角色才能承保'):
            InsuranceService.underwrite(policy.id, self.exporter)

    def test_issue_by_insurer_success(self):
        policy = InsuranceService.create_policy(
            user=self.exporter, contract_id=self.contract.id,
            insurer_id=self.insurer_company.id,
            coverage_type='all_risk', cargo_description='Test'
        )
        InsuranceService.underwrite(policy.id, self.insurer_user)
        result = InsuranceService.issue(policy.id, self.insurer_user)
        assert result.status == 'issued'
        assert result.issued_at is not None

    def test_cancel_by_exporter(self):
        policy = InsuranceService.create_policy(
            user=self.exporter, contract_id=self.contract.id,
            insurer_id=self.insurer_company.id,
            coverage_type='all_risk', cargo_description='Test'
        )
        result = InsuranceService.cancel(policy.id, self.exporter, reason='不需要了')
        assert result.status == 'cancelled'

    def test_cancel_issued_rejected(self):
        policy = InsuranceService.create_policy(
            user=self.exporter, contract_id=self.contract.id,
            insurer_id=self.insurer_company.id,
            coverage_type='all_risk', cargo_description='Test'
        )
        InsuranceService.underwrite(policy.id, self.insurer_user)
        InsuranceService.issue(policy.id, self.insurer_user)
        with pytest.raises(ValueError, match='已签发的保单不能取消'):
            InsuranceService.cancel(policy.id, self.exporter)
