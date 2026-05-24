from decimal import Decimal
from datetime import date
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from apps.transactions.models import Transaction, Contract, CustomsDeclaration
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


class ForexTaxAPITest(TestCase):
    def setUp(self):
        from django.core.management import call_command
        call_command('init_trade_roles')

        self.exporter = User.objects.create_user(username='ft_exp', password='testpass', email='fte@test.com')
        self.carrier_user = User.objects.create_user(username='ft_car', password='testpass', email='ftc@test.com')
        self.customs_user = User.objects.create_user(username='ft_cus', password='testpass', email='ftu@test.com')
        self.forex_user = User.objects.create_user(username='ft_for', password='testpass', email='ftf@test.com')
        self.tax_user = User.objects.create_user(username='ft_tax', password='testpass', email='ftt@test.com')
        self.buyer_user = User.objects.create_user(username='ft_buy', password='testpass', email='ftb@test.com')
        self.exporter_company = create_company_for_user(self.exporter, '_FT出口商')
        self.carrier_company = create_company_for_user(self.carrier_user, '_FT货运')
        self.customs_company = create_company_for_user(self.customs_user, '_FT海关')
        self.forex_company = create_company_for_user(self.forex_user, '_FT外汇局')
        self.tax_company = create_company_for_user(self.tax_user, '_FT税务局')
        self.buyer_company = create_company_for_user(self.buyer_user, '_FT买方')

        setup_role(self.exporter, self.exporter_company, 'exporter')
        setup_role(self.carrier_user, self.carrier_company, 'shipping')
        setup_role(self.customs_user, self.customs_company, 'customs')
        setup_role(self.forex_user, self.forex_company, 'forex')
        setup_role(self.tax_user, self.tax_company, 'tax')

        self.product = Product.objects.create(code='FIX-P0001', name='Test Product', category='electronics', unit='PCS')
        transaction = Transaction.objects.create(
            buyer=self.buyer_company, seller=self.exporter_company,
            product=self.product, quantity=1000, unit_price=10.00,
            status='in_progress', created_by=self.exporter
        )
        contract = Contract.objects.create(
            contract_no='FT-TEST-001', transaction=transaction,
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
        decl = CustomsService.create_declaration(
            user=self.exporter, shipment_id=shipment.id,
            customs_office_id=self.customs_company.id,
            hs_code='610910', goods_name='T-Shirt',
            quantity=Decimal('1000'), unit_value=Decimal('10.00'),
            total_value=Decimal('10000.00'), currency='USD'
        )
        CustomsService.review(decl.id, self.customs_user)
        CustomsService.assess(decl.id, self.customs_user)
        CustomsService.clear(decl.id, self.customs_user)
        # 手动设置 shipment 为 arrived（因为 CustomsService 要求 shipped 状态才能创建报关单）
        from django.utils import timezone as tz
        shipment.status = 'arrived'
        shipment.arrived_at = tz.now()
        shipment.save(update_fields=['status', 'arrived_at'])
        decl.refresh_from_db()
        self.declaration = decl
        self.client = APIClient()

    def test_create_forex_settlement(self):
        self.client.force_authenticate(user=self.exporter)
        url = reverse('transactions:forexsettlement-list')
        response = self.client.post(url, {
            'declaration_id': self.declaration.id,
            'forex_bureau_id': self.forex_company.id
        }, format='json')
        assert response.status_code == 201
        assert response.json()['code'] == 0

    def test_forex_full_lifecycle(self):
        settlement = ForexService.create_settlement(
            user=self.exporter, declaration_id=self.declaration.id,
            forex_bureau_id=self.forex_company.id
        )
        self.client.force_authenticate(user=self.forex_user)
        self.client.post(reverse('transactions:forexsettlement-verify', kwargs={'pk': settlement.id}))
        resp = self.client.post(reverse('transactions:forexsettlement-settle', kwargs={'pk': settlement.id}))
        assert resp.status_code == 200
        settlement.refresh_from_db()
        assert settlement.status == 'settled'

    def test_create_tax_refund_application(self):
        # 先创建并核销外汇
        settlement = ForexService.create_settlement(
            user=self.exporter, declaration_id=self.declaration.id,
            forex_bureau_id=self.forex_company.id
        )
        ForexService.verify(settlement.id, self.forex_user)

        self.client.force_authenticate(user=self.exporter)
        url = reverse('transactions:taxrefundapplication-list')
        response = self.client.post(url, {
            'declaration_id': self.declaration.id,
            'tax_bureau_id': self.tax_company.id
        }, format='json')
        assert response.status_code == 201
        assert response.json()['code'] == 0

    def test_tax_refund_full_lifecycle(self):
        from apps.transactions.services import TaxRefundService
        settlement = ForexService.create_settlement(
            user=self.exporter, declaration_id=self.declaration.id,
            forex_bureau_id=self.forex_company.id
        )
        ForexService.verify(settlement.id, self.forex_user)
        app = TaxRefundService.create_application(
            user=self.exporter, declaration_id=self.declaration.id,
            tax_bureau_id=self.tax_company.id
        )
        self.client.force_authenticate(user=self.tax_user)
        self.client.post(reverse('transactions:taxrefundapplication-review', kwargs={'pk': app.id}))
        self.client.post(reverse('transactions:taxrefundapplication-approve', kwargs={'pk': app.id}))
        resp = self.client.post(reverse('transactions:taxrefundapplication-refund', kwargs={'pk': app.id}))
        assert resp.status_code == 200
        app.refresh_from_db()
        assert app.status == 'refunded'

    def test_unauthenticated_forex_rejected(self):
        url = reverse('transactions:forexsettlement-list')
        response = self.client.get(url)
        assert response.status_code in (401, 403)

    def test_unauthenticated_tax_refund_rejected(self):
        url = reverse('transactions:taxrefundapplication-list')
        response = self.client.get(url)
        assert response.status_code in (401, 403)
