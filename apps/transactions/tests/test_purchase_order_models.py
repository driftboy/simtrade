import pytest
from django.test import TestCase
from datetime import date
from decimal import Decimal
from apps.transactions.models import Transaction, PurchaseOrder
from apps.users.models import User
from apps.roles.services import CompanyService
from apps.core.models import Country
from apps.products.models import Product


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


class PurchaseOrderModelTest(TestCase):
    """测试采购订单模型"""

    def setUp(self):
        self.exporter = User.objects.create_user(
            username='po_exporter', password='testpass', email='po_exp@test.com'
        )
        self.factory_user = User.objects.create_user(
            username='po_factory', password='testpass', email='po_fac@test.com'
        )
        self.exporter_company = create_company_for_user(self.exporter, '_出口商')
        self.factory_company = create_company_for_user(self.factory_user, '_工厂')
        self.product = Product.objects.create(code='FIX-P0001', name='Test Product', category='electronics', unit='PCS')
        self.transaction = Transaction.objects.create(
            buyer=self.exporter_company,
            seller=self.factory_company,
            product=self.product,
            quantity=1000,
            unit_price=10.00,
            status='in_progress',
            created_by=self.exporter
        )

    def test_create_purchase_order(self):
        """测试创建采购订单"""
        po = PurchaseOrder.objects.create(
            transaction=self.transaction,
            buyer=self.exporter_company,
            seller=self.factory_company,
            product_name='棉质T恤',
            quantity=Decimal('500'),
            unit_price=Decimal('8.00'),
            currency='CNY',
            created_by=self.exporter
        )
        assert po.order_no is not None
        assert po.order_no.startswith('PO')
        assert po.total_amount == Decimal('4000.00')
        assert po.status == 'draft'
        assert str(po) == po.order_no

    def test_purchase_order_auto_total_amount(self):
        """测试总金额自动计算"""
        po = PurchaseOrder.objects.create(
            transaction=self.transaction,
            buyer=self.exporter_company,
            seller=self.factory_company,
            product_name='棉质T恤',
            quantity=Decimal('100'),
            unit_price=Decimal('15.50'),
            currency='CNY',
            created_by=self.exporter
        )
        assert po.total_amount == Decimal('1550.00')

    def test_purchase_order_order_no_unique(self):
        """测试订单编号唯一性"""
        po1 = PurchaseOrder.objects.create(
            transaction=self.transaction,
            buyer=self.exporter_company,
            seller=self.factory_company,
            product_name='商品A',
            quantity=Decimal('10'),
            unit_price=Decimal('1.00'),
            currency='CNY',
            created_by=self.exporter
        )
        assert po1.order_no is not None

        po2 = PurchaseOrder.objects.create(
            transaction=self.transaction,
            buyer=self.exporter_company,
            seller=self.factory_company,
            product_name='商品B',
            quantity=Decimal('20'),
            unit_price=Decimal('2.00'),
            currency='CNY',
            created_by=self.exporter
        )
        assert po2.order_no != po1.order_no

    def test_purchase_order_status_choices(self):
        """测试状态选项完整"""
        valid_statuses = [choice[0] for choice in PurchaseOrder.Status.choices]
        assert 'draft' in valid_statuses
        assert 'confirmed' in valid_statuses
        assert 'shipped' in valid_statuses
        assert 'invoiced' in valid_statuses
        assert 'completed' in valid_statuses
        assert 'cancelled' in valid_statuses
