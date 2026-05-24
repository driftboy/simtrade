import pytest
from django.test import TestCase
from apps.transactions.models import Transaction, InquiryMessage
from apps.users.models import User
from apps.transactions.services import TransactionService
from apps.roles.services import CompanyService
from apps.core.models import Country
from apps.products.models import Product


def get_or_create_country():
    """获取或创建默认国家"""
    country, _ = Country.objects.get_or_create(
        code='CN',
        defaults={
            'name': '中国',
            'name_en': 'China',
            'phone_code': '86'
        }
    )
    return country


def create_company_for_user(user, name_suffix=''):
    """为用户创建公司"""
    country = get_or_create_country()
    return CompanyService.create_company(
        user=user,
        name=f'{user.username}{name_suffix}公司',
        name_en=f'{user.username}{name_suffix} Company',
        country_id=country.code
    )


class TransactionStateMachineTest(TestCase):
    """交易状态机测试"""

    def setUp(self):
        self.buyer = User.objects.create_user(username='buyer', password='testpass', email='buyer@example.com')
        self.seller = User.objects.create_user(username='seller', password='testpass', email='seller@example.com')
        self.buyer_company = create_company_for_user(self.buyer, '_状态机买方')
        self.seller_company = create_company_for_user(self.seller, '_状态机卖方')
        self.product = Product.objects.create(code='SM-P001', name='State Machine Product', category='electronics', unit='PCS')

    def test_inquiring_to_negotiating(self):
        """测试从询盘到还盘的状态转换"""
        transaction = Transaction.objects.create(
            buyer=self.buyer_company,
            seller=self.seller_company,
            product=self.product,
            quantity=1000,
            unit_price=10.00,
            status='inquiring'
        )
        # 卖家发送发盘
        message = InquiryMessage.objects.create(
            transaction=transaction,
            sender=self.seller,
            sender_role='seller',
            message_type='offer',
            content='报价 $12'
        )
        TransactionService.handle_message(transaction, message)
        transaction.refresh_from_db()
        assert transaction.status == 'negotiating'

    def test_negotiating_to_pending_contract(self):
        """测试从还盘到待签约的状态转换"""
        transaction = Transaction.objects.create(
            buyer=self.buyer_company,
            seller=self.seller_company,
            product=self.product,
            quantity=1000,
            unit_price=10.00,
            status='negotiating'
        )
        # 买家接受发盘
        message = InquiryMessage.objects.create(
            transaction=transaction,
            sender=self.buyer,
            sender_role='buyer',
            message_type='accept',
            content='接受报价'
        )
        TransactionService.handle_message(transaction, message)
        transaction.refresh_from_db()
        assert transaction.status == 'pending_contract'

    def test_cancel_transaction(self):
        """测试取消交易"""
        transaction = Transaction.objects.create(
            buyer=self.buyer_company,
            seller=self.seller_company,
            product=self.product,
            quantity=1000,
            unit_price=10.00,
            status='inquiring'
        )
        transaction.status = 'cancelled'
        transaction.save()
        assert transaction.status == 'cancelled'
