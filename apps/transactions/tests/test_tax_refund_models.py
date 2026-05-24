from django.test import TestCase
from datetime import date
from decimal import Decimal
from apps.transactions.models import Transaction, Contract, CustomsDeclaration, TaxRefundApplication
from apps.transactions.services import ShipmentService, CustomsService
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
    decl.refresh_from_db()
    return decl


class TaxRefundApplicationModelTest(TestCase):
    def setUp(self):
        from django.core.management import call_command
        call_command('init_trade_roles')

        self.exporter = User.objects.create_user(username='tr_mod_exp', password='testpass', email='tre@test.com')
        self.carrier_user = User.objects.create_user(username='tr_mod_car', password='testpass', email='trc@test.com')
        self.customs_user = User.objects.create_user(username='tr_mod_cus', password='testpass', email='tru@test.com')
        self.tax_user = User.objects.create_user(username='tr_mod_tax', password='testpass', email='trt@test.com')
        self.buyer_user = User.objects.create_user(username='tr_mod_buy', password='testpass', email='trb@test.com')
        self.exporter_company = create_company_for_user(self.exporter, '_TR出口商')
        self.carrier_company = create_company_for_user(self.carrier_user, '_TR货运')
        self.customs_company = create_company_for_user(self.customs_user, '_TR海关')
        self.tax_company = create_company_for_user(self.tax_user, '_TR税务局')
        self.buyer_company = create_company_for_user(self.buyer_user, '_TR买方')

        setup_role(self.exporter, self.exporter_company, 'exporter')
        setup_role(self.carrier_user, self.carrier_company, 'shipping')
        setup_role(self.customs_user, self.customs_company, 'customs')

        self.declaration = create_cleared_declaration(
            self.exporter_company, self.buyer_company, self.carrier_company,
            self.customs_company, self.exporter, self.carrier_user, self.customs_user
        )

    def test_create_tax_refund_application(self):
        app = TaxRefundApplication.objects.create(
            customs_declaration=self.declaration,
            applicant=self.exporter_company,
            tax_bureau=self.tax_company,
            hs_code='610910',
            total_value=Decimal('10000.00'),
            refund_rate=Decimal('0.13'),
            refund_amount=Decimal('1300.00'),
            created_by=self.exporter
        )
        assert app.application_no is not None
        assert app.application_no.startswith('TR')
        assert app.status == 'applied'
        assert str(app) == app.application_no

    def test_refund_status_choices(self):
        valid = [c[0] for c in TaxRefundApplication.Status.choices]
        assert 'applied' in valid
        assert 'reviewing' in valid
        assert 'approved' in valid
        assert 'refunded' in valid
        assert 'rejected' in valid
