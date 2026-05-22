import pytest
from django.test import TestCase
from apps.transactions.models import Transaction, InquiryMessage
from apps.users.models import User


class TransactionModelTest(TestCase):
    """测试交易模型"""

    def setUp(self):
        self.buyer = User.objects.create_user(username='buyer', password='testpass', email='buyer@test.com')
        self.seller = User.objects.create_user(username='seller', password='testpass', email='seller@test.com')

    def test_create_transaction(self):
        """测试创建交易"""
        transaction = Transaction.objects.create(
            buyer=self.buyer,
            seller=self.seller,
            product_id=1,  # 假设存在商品
            quantity=1000,
            unit_price=10.00,
            status='inquiring'
        )
        assert transaction.status == 'inquiring'
        assert transaction.get_status_display() == '询盘中'

    def test_transaction_status_choices(self):
        """测试交易状态选择"""
        transaction = Transaction.objects.create(
            buyer=self.buyer,
            seller=self.seller,
            product_id=1,
            quantity=1000,
            unit_price=10.00
        )
        # 测试状态转换
        transaction.status = 'negotiating'
        transaction.save()
        assert transaction.get_status_display() == '还盘中'


class InquiryMessageTest(TestCase):
    """测试磋商消息模型"""

    def setUp(self):
        self.buyer = User.objects.create_user(username='buyer2', password='testpass', email='buyer2@test.com')
        self.seller = User.objects.create_user(username='seller2', password='testpass', email='seller2@test.com')
        self.transaction = Transaction.objects.create(
            buyer=self.buyer,
            seller=self.seller,
            product_id=1,
            quantity=1000,
            unit_price=10.00
        )

    def test_create_inquiry_message(self):
        """测试创建询盘消息"""
        message = InquiryMessage.objects.create(
            transaction=self.transaction,
            sender=self.buyer,
            sender_role='buyer',
            message_type='inquiry',
            content='对贵司产品感兴趣，请报价'
        )
        assert message.message_type == 'inquiry'
        assert message.get_message_type_display() == '询盘'
