import pytest
from django.test import TestCase
from decimal import Decimal
from apps.transactions.models import Transaction, PurchaseOrder
from apps.transactions.services import PurchaseOrderService
from apps.users.models import User
from apps.roles.services import CompanyService
from apps.roles.models import TradeRole, UserCompanyRole
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


def setup_role(user, company, role_code):
    role = TradeRole.objects.get(code=role_code)
    ucr, created = UserCompanyRole.objects.get_or_create(
        user=user, company=company, role=role,
        defaults={'status': 'active', 'is_active': True}
    )
    if not created:
        # Already exists (e.g. CompanyService auto-creates exporter role);
        # ensure it is active.
        ucr.status = 'active'
        ucr.is_active = True
        ucr.save()


class PurchaseOrderServiceCreateTest(TestCase):
    def setUp(self):
        self.exporter = User.objects.create_user(username='svc_exporter', password='testpass', email='se@test.com')
        self.factory_user = User.objects.create_user(username='svc_factory', password='testpass', email='sf@test.com')
        self.importer = User.objects.create_user(username='svc_importer', password='testpass', email='si@test.com')
        self.exporter_company = create_company_for_user(self.exporter, '_出口商')
        self.factory_company = create_company_for_user(self.factory_user, '_工厂')
        self.importer_company = create_company_for_user(self.importer, '_进口商')
        from django.core.management import call_command
        call_command('init_trade_roles')
        setup_role(self.exporter, self.exporter_company, 'exporter')
        setup_role(self.factory_user, self.factory_company, 'factory')
        setup_role(self.importer, self.importer_company, 'importer')
        self.transaction = Transaction.objects.create(
            buyer=self.importer_company, seller=self.exporter_company,
            product_id=1, quantity=1000, unit_price=10.00,
            status='in_progress', created_by=self.importer
        )

    def test_create_order_success(self):
        po = PurchaseOrderService.create_order(
            user=self.exporter, transaction_id=self.transaction.id,
            seller_id=self.factory_company.id,
            product_name='棉质T恤', quantity=Decimal('500'), unit_price=Decimal('8.00'), currency='CNY'
        )
        assert po.buyer == self.exporter_company
        assert po.seller == self.factory_company
        assert po.transaction == self.transaction
        assert po.status == 'draft'
        assert po.total_amount == Decimal('4000.00')

    def test_create_order_non_exporter_rejected(self):
        with pytest.raises(ValueError, match='只有出口商角色才能创建采购订单'):
            PurchaseOrderService.create_order(
                user=self.importer, transaction_id=self.transaction.id,
                seller_id=self.factory_company.id,
                product_name='商品', quantity=Decimal('100'), unit_price=Decimal('10.00')
            )

    def test_create_order_wrong_company_rejected(self):
        other_txn = Transaction.objects.create(
            buyer=self.importer_company, seller=self.factory_company,
            product_id=2, quantity=100, unit_price=5.00, created_by=self.importer
        )
        with pytest.raises(ValueError, match='只能为自己的出口交易创建采购订单'):
            PurchaseOrderService.create_order(
                user=self.exporter, transaction_id=other_txn.id,
                seller_id=self.factory_company.id,
                product_name='商品', quantity=Decimal('100'), unit_price=Decimal('10.00')
            )


class PurchaseOrderServiceConfirmTest(TestCase):
    def setUp(self):
        self.exporter = User.objects.create_user(username='cf_exp', password='testpass', email='ce@test.com')
        self.factory_user = User.objects.create_user(username='cf_fac', password='testpass', email='cf@test.com')
        self.exporter_company = create_company_for_user(self.exporter, '_确认出口商')
        self.factory_company = create_company_for_user(self.factory_user, '_确认工厂')
        from django.core.management import call_command
        call_command('init_trade_roles')
        setup_role(self.exporter, self.exporter_company, 'exporter')
        setup_role(self.factory_user, self.factory_company, 'factory')
        imp = User.objects.create_user('cf_imp', 'p', 'ci@t.com')
        self.transaction = Transaction.objects.create(
            buyer=create_company_for_user(imp, '_确认进口商'), seller=self.exporter_company,
            product_id=1, quantity=1000, unit_price=10.00,
            status='in_progress', created_by=self.exporter
        )
        self.po = PurchaseOrderService.create_order(
            user=self.exporter, transaction_id=self.transaction.id,
            seller_id=self.factory_company.id,
            product_name='商品', quantity=Decimal('100'), unit_price=Decimal('10.00')
        )

    def test_confirm_by_factory_success(self):
        result = PurchaseOrderService.confirm(self.po.id, self.factory_user)
        assert result.status == 'confirmed'
        assert result.confirmed_at is not None

    def test_confirm_by_exporter_rejected(self):
        with pytest.raises(ValueError, match='只有工厂角色才能确认订单'):
            PurchaseOrderService.confirm(self.po.id, self.exporter)

    def test_confirm_wrong_status_rejected(self):
        self.po.status = 'confirmed'
        self.po.save()
        with pytest.raises(ValueError, match='订单状态不允许确认'):
            PurchaseOrderService.confirm(self.po.id, self.factory_user)


class PurchaseOrderServiceShipTest(TestCase):
    def setUp(self):
        self.exporter = User.objects.create_user(username='sh_exp', password='testpass', email='she@test.com')
        self.factory_user = User.objects.create_user(username='sh_fac', password='testpass', email='shf@test.com')
        self.exporter_company = create_company_for_user(self.exporter, '_发货出口商')
        self.factory_company = create_company_for_user(self.factory_user, '_发货工厂')
        from django.core.management import call_command
        call_command('init_trade_roles')
        setup_role(self.exporter, self.exporter_company, 'exporter')
        setup_role(self.factory_user, self.factory_company, 'factory')
        imp = User.objects.create_user('sh_imp', 'p', 'shi@t.com')
        self.transaction = Transaction.objects.create(
            buyer=create_company_for_user(imp, '_发货进口商'), seller=self.exporter_company,
            product_id=1, quantity=1000, unit_price=10.00,
            status='in_progress', created_by=self.exporter
        )
        self.po = PurchaseOrderService.create_order(
            user=self.exporter, transaction_id=self.transaction.id,
            seller_id=self.factory_company.id,
            product_name='商品', quantity=Decimal('100'), unit_price=Decimal('10.00')
        )
        PurchaseOrderService.confirm(self.po.id, self.factory_user)

    def test_ship_by_factory_success(self):
        result = PurchaseOrderService.ship(self.po.id, self.factory_user, tracking_info='SF123456')
        assert result.status == 'shipped'
        assert result.shipped_at is not None

    def test_ship_by_exporter_rejected(self):
        with pytest.raises(ValueError, match='只有工厂角色才能发货'):
            PurchaseOrderService.ship(self.po.id, self.exporter)


class PurchaseOrderServiceInvoiceTest(TestCase):
    def setUp(self):
        self.exporter = User.objects.create_user(username='inv_exp', password='testpass', email='ie@test.com')
        self.factory_user = User.objects.create_user(username='inv_fac', password='testpass', email='if@test.com')
        self.exporter_company = create_company_for_user(self.exporter, '_开票出口商')
        self.factory_company = create_company_for_user(self.factory_user, '_开票工厂')
        from django.core.management import call_command
        call_command('init_trade_roles')
        setup_role(self.exporter, self.exporter_company, 'exporter')
        setup_role(self.factory_user, self.factory_company, 'factory')
        imp = User.objects.create_user('inv_imp', 'p', 'ii@t.com')
        self.transaction = Transaction.objects.create(
            buyer=create_company_for_user(imp, '_开票进口商'), seller=self.exporter_company,
            product_id=1, quantity=1000, unit_price=10.00,
            status='in_progress', created_by=self.exporter
        )
        self.po = PurchaseOrderService.create_order(
            user=self.exporter, transaction_id=self.transaction.id,
            seller_id=self.factory_company.id,
            product_name='商品', quantity=Decimal('100'), unit_price=Decimal('10.00')
        )
        PurchaseOrderService.confirm(self.po.id, self.factory_user)
        PurchaseOrderService.ship(self.po.id, self.factory_user)

    def test_invoice_by_factory_success(self):
        result = PurchaseOrderService.invoice(self.po.id, self.factory_user)
        assert result.status == 'invoiced'
        assert result.invoiced_at is not None


class PurchaseOrderServiceCompleteTest(TestCase):
    def setUp(self):
        self.exporter = User.objects.create_user(username='cp_exp', password='testpass', email='cpe@test.com')
        self.factory_user = User.objects.create_user(username='cp_fac', password='testpass', email='cpf@test.com')
        self.exporter_company = create_company_for_user(self.exporter, '_完成出口商')
        self.factory_company = create_company_for_user(self.factory_user, '_完成工厂')
        from django.core.management import call_command
        call_command('init_trade_roles')
        setup_role(self.exporter, self.exporter_company, 'exporter')
        setup_role(self.factory_user, self.factory_company, 'factory')
        imp = User.objects.create_user('cp_imp', 'p', 'cpi@t.com')
        self.transaction = Transaction.objects.create(
            buyer=create_company_for_user(imp, '_完成进口商'), seller=self.exporter_company,
            product_id=1, quantity=1000, unit_price=10.00,
            status='in_progress', created_by=self.exporter
        )
        self.po = PurchaseOrderService.create_order(
            user=self.exporter, transaction_id=self.transaction.id,
            seller_id=self.factory_company.id,
            product_name='商品', quantity=Decimal('100'), unit_price=Decimal('10.00')
        )
        PurchaseOrderService.confirm(self.po.id, self.factory_user)
        PurchaseOrderService.ship(self.po.id, self.factory_user)
        PurchaseOrderService.invoice(self.po.id, self.factory_user)

    def test_complete_by_exporter_success(self):
        result = PurchaseOrderService.complete(self.po.id, self.exporter)
        assert result.status == 'completed'
        assert result.completed_at is not None

    def test_complete_by_factory_rejected(self):
        with pytest.raises(ValueError, match='只有出口商角色才能确认收货'):
            PurchaseOrderService.complete(self.po.id, self.factory_user)


class PurchaseOrderServiceCancelTest(TestCase):
    def setUp(self):
        self.exporter = User.objects.create_user(username='cx_exp', password='testpass', email='cae@test.com')
        self.factory_user = User.objects.create_user(username='cx_fac', password='testpass', email='caf@test.com')
        self.exporter_company = create_company_for_user(self.exporter, '_取消出口商')
        self.factory_company = create_company_for_user(self.factory_user, '_取消工厂')
        from django.core.management import call_command
        call_command('init_trade_roles')
        setup_role(self.exporter, self.exporter_company, 'exporter')
        setup_role(self.factory_user, self.factory_company, 'factory')
        self.importer = User.objects.create_user('cx_imp', 'p', 'cai@t.com')
        self.importer_company = create_company_for_user(self.importer, '_取消进口商')
        self.transaction = Transaction.objects.create(
            buyer=self.importer_company, seller=self.exporter_company,
            product_id=1, quantity=1000, unit_price=10.00,
            status='in_progress', created_by=self.exporter
        )

    def test_cancel_draft_by_exporter(self):
        po = PurchaseOrderService.create_order(
            user=self.exporter, transaction_id=self.transaction.id,
            seller_id=self.factory_company.id,
            product_name='商品', quantity=Decimal('100'), unit_price=Decimal('10.00')
        )
        result = PurchaseOrderService.cancel(po.id, self.exporter, reason='不需要了')
        assert result.status == 'cancelled'

    def test_cancel_confirmed_by_factory(self):
        po = PurchaseOrderService.create_order(
            user=self.exporter, transaction_id=self.transaction.id,
            seller_id=self.factory_company.id,
            product_name='商品', quantity=Decimal('100'), unit_price=Decimal('10.00')
        )
        PurchaseOrderService.confirm(po.id, self.factory_user)
        result = PurchaseOrderService.cancel(po.id, self.factory_user, reason='产能不足')
        assert result.status == 'cancelled'

    def test_cancel_shipped_rejected(self):
        po = PurchaseOrderService.create_order(
            user=self.exporter, transaction_id=self.transaction.id,
            seller_id=self.factory_company.id,
            product_name='商品', quantity=Decimal('100'), unit_price=Decimal('10.00')
        )
        PurchaseOrderService.confirm(po.id, self.factory_user)
        PurchaseOrderService.ship(po.id, self.factory_user)
        with pytest.raises(ValueError, match='订单状态不允许取消'):
            PurchaseOrderService.cancel(po.id, self.exporter)

    def test_cancel_by_importer_rejected(self):
        """进口商不能取消订单"""
        po = PurchaseOrderService.create_order(
            user=self.exporter, transaction_id=self.transaction.id,
            seller_id=self.factory_company.id,
            product_name='商品', quantity=Decimal('100'), unit_price=Decimal('10.00')
        )
        setup_role(self.importer, self.importer_company, 'importer')
        with pytest.raises(ValueError, match='草稿订单只能由出口商取消'):
            PurchaseOrderService.cancel(po.id, self.importer)

    def test_cancel_invoiced_rejected(self):
        """已开票的订单不能取消"""
        po = PurchaseOrderService.create_order(
            user=self.exporter, transaction_id=self.transaction.id,
            seller_id=self.factory_company.id,
            product_name='商品', quantity=Decimal('100'), unit_price=Decimal('10.00')
        )
        PurchaseOrderService.confirm(po.id, self.factory_user)
        PurchaseOrderService.ship(po.id, self.factory_user)
        PurchaseOrderService.invoice(po.id, self.factory_user)
        with pytest.raises(ValueError, match='订单状态不允许取消'):
            PurchaseOrderService.cancel(po.id, self.exporter)
