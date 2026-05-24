import pytest
from datetime import date, timedelta
from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from apps.transactions.models import Transaction, Contract, LetterOfCredit, BankOperation
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
    """Assign a role to user+company and activate it."""
    role = TradeRole.objects.get(code=role_code)
    ucr, _ = UserCompanyRole.objects.get_or_create(
        user=user, company=company, role=role,
        defaults={'status': 'active', 'is_active': True}
    )
    return ucr


def activate_role(user, company, role_code):
    """Deactivate all roles for user, then activate the specified one."""
    UserCompanyRole.objects.filter(user=user).update(is_active=False)
    role = TradeRole.objects.get(code=role_code)
    ucr, _ = UserCompanyRole.objects.get_or_create(
        user=user, company=company, role=role,
        defaults={'status': 'active', 'is_active': True}
    )
    ucr.is_active = True
    ucr.status = 'active'
    ucr.save()
    return ucr


class LetterOfCreditAPITest(TestCase):
    """Test LetterOfCredit API endpoints."""

    def setUp(self):
        from django.core.management import call_command
        call_command('init_trade_roles')

        # Create users
        self.importer_user = User.objects.create_user(
            username='lc_imp', password='testpass', email='lci@test.com')
        self.exporter_user = User.objects.create_user(
            username='lc_exp', password='testpass', email='lce@test.com')
        self.bank_user = User.objects.create_user(
            username='lc_bank', password='testpass', email='lcb@test.com')

        # Create companies
        self.importer_company = create_company_for_user(self.importer_user, '_LC进口商')
        self.exporter_company = create_company_for_user(self.exporter_user, '_LC出口商')
        self.bank_company = create_company_for_user(self.bank_user, '_LC银行')

        # Assign roles
        activate_role(self.importer_user, self.importer_company, 'importer')
        activate_role(self.exporter_user, self.exporter_company, 'exporter')
        activate_role(self.bank_user, self.bank_company, 'bank')

        # Create product
        self.product = Product.objects.create(
            code='LC-P001', name='LC Test Product', category='electronics', unit='PCS')

        # Create transaction
        self.transaction = Transaction.objects.create(
            buyer=self.importer_company,
            seller=self.exporter_company,
            product=self.product,
            quantity=1000,
            unit_price=Decimal('10.00'),
            currency='USD',
            status='in_progress',
            created_by=self.importer_user
        )

        # Create contract
        self.contract = Contract.objects.create(
            contract_no='LC-TEST-001',
            transaction=self.transaction,
            trade_term='CIF',
            payment_term='L/C at sight',
            delivery_time=date(2026, 12, 31),
            port_of_loading='Shanghai',
            port_of_discharge='Los Angeles',
            product_name='Test Product',
            product_spec='',
            quantity=1000,
            unit='pcs',
            unit_price=Decimal('10.00'),
            total_amount=Decimal('10000.00'),
            currency='USD',
            status='effective'
        )

        self.client = APIClient()

    def _create_lc(self, status='draft'):
        """Helper to create an LC directly in the DB."""
        return LetterOfCredit.objects.create(
            lc_no='LC20260101000001',
            contract=self.contract,
            transaction=self.transaction,
            status=status,
            issuing_bank=f'{self.bank_company.name}',
            advising_bank='Advising Bank',
            applicant=self.importer_company,
            beneficiary=self.exporter_company,
            amount=Decimal('10000.00'),
            currency='USD',
            expiry_date=date(2026, 12, 31),
            latest_shipment_date=date(2026, 11, 30),
            port_of_loading='Shanghai',
            port_of_discharge='Los Angeles',
            documents_required=['Commercial Invoice', 'Bill of Lading']
        )

    # ------------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------------

    def test_create_lc_as_importer(self):
        """Importer can create an LC; status should be draft."""
        self.client.force_authenticate(user=self.importer_user)
        url = reverse('transactions:letterofcredit-list')
        data = {
            'lc_no': 'LC20260101000001',
            'contract': self.contract.id,
            'transaction': self.transaction.id,
            'issuing_bank': f'{self.bank_company.name}',
            'advising_bank': 'Advising Bank',
            'applicant': self.importer_company.id,
            'beneficiary': self.exporter_company.id,
            'amount': '10000.00',
            'currency': 'USD',
            'expiry_date': '2026-12-31',
            'latest_shipment_date': '2026-11-30',
            'port_of_loading': 'Shanghai',
            'port_of_discharge': 'Los Angeles',
            'documents_required': ['Commercial Invoice', 'Bill of Lading']
        }
        response = self.client.post(url, data, format='json')
        assert response.status_code == 201
        body = response.json()
        assert body['code'] == 0
        assert body['data']['status'] == 'draft'
        assert body['data']['applicant'] == self.importer_company.id

    def test_list_lc(self):
        """User can list LCs for their company."""
        self._create_lc()
        self.client.force_authenticate(user=self.importer_user)
        url = reverse('transactions:letterofcredit-list')
        response = self.client.get(url)
        assert response.status_code == 200
        body = response.json()
        assert body['code'] == 0
        assert len(body['data']) >= 1

    def test_issue_lc_as_bank(self):
        """Bank can issue an LC: pending_issue -> issued."""
        lc = self._create_lc(status='pending_issue')

        self.client.force_authenticate(user=self.bank_user)
        url = reverse('transactions:letterofcredit-issue', kwargs={'pk': lc.id})
        response = self.client.post(url, format='json')
        assert response.status_code == 200
        body = response.json()
        assert body['code'] == 0

        lc.refresh_from_db()
        assert lc.status == 'issued'
        # BankOperation should be created
        assert BankOperation.objects.filter(lc=lc, operation_type='issue').exists()

    def test_submit_docs_as_exporter(self):
        """Exporter (beneficiary) can submit docs: issued -> submitted."""
        lc = self._create_lc(status='issued')

        self.client.force_authenticate(user=self.exporter_user)
        url = reverse('transactions:letterofcredit-submit-docs', kwargs={'pk': lc.id})
        response = self.client.post(url, format='json')
        assert response.status_code == 200
        body = response.json()
        assert body['code'] == 0

        lc.refresh_from_db()
        assert lc.status == 'submitted'

    def test_negotiate_and_pay(self):
        """Bank can negotiate (submitted -> negotiated) then pay (negotiated -> paid)."""
        lc = self._create_lc(status='submitted')

        # Negotiate
        self.client.force_authenticate(user=self.bank_user)
        url = reverse('transactions:letterofcredit-negotiate', kwargs={'pk': lc.id})
        response = self.client.post(url, format='json')
        assert response.status_code == 200
        lc.refresh_from_db()
        assert lc.status == 'negotiated'
        assert BankOperation.objects.filter(lc=lc, operation_type='negotiate').exists()

        # Pay
        url = reverse('transactions:letterofcredit-pay', kwargs={'pk': lc.id})
        response = self.client.post(url, format='json')
        assert response.status_code == 200
        lc.refresh_from_db()
        assert lc.status == 'paid'
        assert BankOperation.objects.filter(lc=lc, operation_type='pay').exists()

    def test_cancel_lc(self):
        """Applicant can cancel a draft LC: draft -> cancelled."""
        lc = self._create_lc(status='draft')

        self.client.force_authenticate(user=self.importer_user)
        url = reverse('transactions:letterofcredit-cancel', kwargs={'pk': lc.id})
        response = self.client.post(url, format='json')
        assert response.status_code == 200
        body = response.json()
        assert body['code'] == 0

        lc.refresh_from_db()
        assert lc.status == 'cancelled'

    def test_unauthorized_issue(self):
        """Non-bank user cannot issue an LC."""
        lc = self._create_lc(status='pending_issue')

        # Try as importer (not bank)
        self.client.force_authenticate(user=self.importer_user)
        url = reverse('transactions:letterofcredit-issue', kwargs={'pk': lc.id})
        response = self.client.post(url, format='json')
        assert response.status_code == 400 or response.status_code == 403
        body = response.json()
        assert body['code'] in (4003, 5005)

        # LC status should not have changed
        lc.refresh_from_db()
        assert lc.status == 'pending_issue'
