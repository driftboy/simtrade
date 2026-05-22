import pytest
from django.test import TestCase
from apps.transactions.models import Transaction, InquiryMessage, Contract
from apps.users.models import User
from apps.transactions.services import TransactionService


class TransactionIntegrationTest(TestCase):
    """交易集成测试"""

    def setUp(self):
        self.buyer = User.objects.create_user(username='buyer', password='testpass', email='buyer@example.com')
        self.seller = User.objects.create_user(username='seller', password='testpass', email='seller@example.com')

    def test_complete_negotiation_flow(self):
        """测试完整磋商流程：询盘 -> 发盘 -> 还盘 -> 接受 -> 待签约"""
        # 1. 创建交易（询盘）
        transaction = Transaction.objects.create(
            buyer=self.buyer,
            seller=self.seller,
            product_id=1,
            quantity=1000,
            unit_price=10.00,
            status='inquiring'
        )
        assert transaction.status == 'inquiring'

        # 2. 卖家发盘
        offer = InquiryMessage.objects.create(
            transaction=transaction,
            sender=self.seller,
            sender_role='seller',
            message_type='offer',
            content='报价 $12',
            offered_price=12.00
        )
        TransactionService.handle_message(transaction, offer)
        transaction.refresh_from_db()
        assert transaction.status == 'negotiating'

        # 3. 买家还盘
        counter = InquiryMessage.objects.create(
            transaction=transaction,
            sender=self.buyer,
            sender_role='buyer',
            message_type='counter_offer',
            content='还价 $11',
            offered_price=11.00
        )
        TransactionService.handle_message(transaction, counter)
        transaction.refresh_from_db()
        assert transaction.status == 'negotiating'

        # 4. 买家接受
        accept = InquiryMessage.objects.create(
            transaction=transaction,
            sender=self.buyer,
            sender_role='buyer',
            message_type='accept',
            content='接受报价'
        )
        TransactionService.handle_message(transaction, accept)
        transaction.refresh_from_db()
        assert transaction.status == 'pending_contract'

        # 5. 创建合同
        contract = TransactionService.create_contract(
            transaction,
            {
                'trade_term': 'FOB Shanghai',
                'payment_term': 'L/C',
                'delivery_time': '2026-06-30',
                'port_of_loading': 'Shanghai',
                'port_of_discharge': 'New York',
                'product_name': '测试商品',
                'quantity': 1000,
                'unit': 'PCS',
                'unit_price': 11.00,
                'total_amount': 11000.00,
                'currency': 'USD'
            }
        )
        assert contract.contract_no.startswith('SC')
        assert contract.status == 'draft'
