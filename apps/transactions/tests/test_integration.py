import pytest
from django.test import TestCase
from datetime import date, datetime
from apps.transactions.models import (
    Transaction, InquiryMessage, Contract, ContractSignature,
    ContractAmendment, LetterOfCredit, LcAmendment, BankOperation
)
from apps.users.models import User
from apps.transactions.services import TransactionService, ContractService, LetterOfCreditService


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


class ContractIntegrationTest(TestCase):
    """合同集成测试"""

    def setUp(self):
        self.buyer = User.objects.create_user(username='buyer', password='testpass', email='buyer@example.com')
        self.seller = User.objects.create_user(username='seller', password='testpass', email='seller@example.com')
        self.transaction = Transaction.objects.create(
            buyer=self.buyer,
            seller=self.seller,
            product_id=1,
            quantity=1000,
            unit_price=10.00,
            status='pending_contract'
        )
        self.contract = Contract.objects.create(
            contract_no='SC2026001',
            transaction=self.transaction,
            trade_term='FOB Shanghai',
            payment_term='L/C',
            delivery_time=date(2026, 6, 30),
            port_of_loading='Shanghai',
            port_of_discharge='New York',
            product_name='测试商品',
            quantity=1000,
            unit='PCS',
            unit_price=11.00,
            total_amount=11000.00,
            currency='USD'
        )

    def test_contract_confirmation_flow(self):
        """测试合同确认流程：草稿 -> 待确认 -> 待签字"""
        # 1. 发送确认
        ContractService.send_for_confirmation(self.contract, self.buyer)
        self.contract.refresh_from_db()
        assert self.contract.status == 'pending_confirm'

        # 2. 确认条款
        ContractService.confirm_terms(self.contract, self.seller)
        self.contract.refresh_from_db()
        assert self.contract.status == 'pending_sign'

    def test_contract_signing_flow(self):
        """测试合同签字流程：待签字 -> 一方签字 -> 已签字"""
        self.contract.status = 'pending_sign'
        self.contract.save()

        # 1. 买方签字
        ContractService.sign(self.contract, self.buyer, 'buyer', '127.0.0.1')
        self.contract.refresh_from_db()
        assert self.contract.status == 'one_signed'
        assert self.contract.buyer_signed_at is not None
        assert ContractSignature.objects.filter(contract=self.contract, party='buyer').exists()

        # 2. 卖方签字
        ContractService.sign(self.contract, self.seller, 'seller', '127.0.0.1')
        self.contract.refresh_from_db()
        assert self.contract.status == 'signed'
        assert self.contract.seller_signed_at is not None
        assert ContractSignature.objects.filter(contract=self.contract, party='seller').exists()

    def test_contract_amendment_flow(self):
        """测试合同修改流程：待确认 -> 修改中 -> 接受 -> 待确认"""
        self.contract.status = 'pending_confirm'
        self.contract.save()

        # 1. 请求修改（返回的是 contract，不是 amendment）
        ContractService.request_amendment(
            self.contract,
            {'unit_price': 12.00},
            '价格调整',
            self.buyer
        )
        self.contract.refresh_from_db()
        assert self.contract.status == 'amending'

        # 获取修改记录
        amendment = ContractAmendment.objects.filter(contract=self.contract).first()
        assert amendment is not None

        # 2. 接受修改
        ContractService.accept_amendment(self.contract, amendment.id, self.seller)
        self.contract.refresh_from_db()
        assert self.contract.status == 'pending_confirm'

        amendment.refresh_from_db()
        assert amendment.status == 'accepted'


class LetterOfCreditIntegrationTest(TestCase):
    """信用证集成测试"""

    def setUp(self):
        self.buyer = User.objects.create_user(username='buyer', password='testpass', email='buyer@example.com')
        self.seller = User.objects.create_user(username='seller', password='testpass', email='seller@example.com')
        self.transaction = Transaction.objects.create(
            buyer=self.buyer,
            seller=self.seller,
            product_id=1,
            quantity=1000,
            unit_price=10.00,
            status='contracted'
        )
        self.contract = Contract.objects.create(
            contract_no='SC2026001',
            transaction=self.transaction,
            trade_term='FOB Shanghai',
            payment_term='L/C',
            delivery_time=date(2026, 6, 30),
            port_of_loading='Shanghai',
            port_of_discharge='New York',
            product_name='测试商品',
            quantity=1000,
            unit='PCS',
            unit_price=11.00,
            total_amount=11000.00,
            currency='USD',
            status='effective'
        )
        self.letter_of_credit = LetterOfCredit.objects.create(
            lc_no='LC2026001',
            contract=self.contract,
            transaction=self.transaction,
            status='draft',
            issuing_bank='中国银行',
            advising_bank='花旗银行',
            applicant=self.buyer,
            beneficiary=self.seller,
            amount=11000.00,
            currency='USD',
            expiry_date=date(2026, 7, 31),
            latest_shipment_date=date(2026, 7, 15),
            port_of_loading='Shanghai',
            port_of_discharge='New York',
            documents_required=['商业发票', '提单', '装箱单']
        )

    def test_lc_issuance_flow(self):
        """测试信用证开证流程：草稿 -> 待开证 -> 已开证"""
        # 1. 申请开证
        LetterOfCreditService.apply_for_issue(self.letter_of_credit, self.buyer)
        self.letter_of_credit.refresh_from_db()
        assert self.letter_of_credit.status == 'pending_issue'

        # 2. 银行开证（系统模拟）
        LetterOfCreditService.auto_issue(self.letter_of_credit)
        self.letter_of_credit.refresh_from_db()
        assert self.letter_of_credit.status == 'issued'
        assert self.letter_of_credit.issued_at is not None
        assert BankOperation.objects.filter(lc=self.letter_of_credit, operation_type='issue').exists()

    def test_lc_amendment_flow(self):
        """测试信用证修改流程：已开证 -> 修改中 -> 批准 -> 已开证"""
        self.letter_of_credit.status = 'issued'
        self.letter_of_credit.save()

        # 1. 请求修改
        amendment = LetterOfCreditService.request_amendment(
            self.letter_of_credit,
            {'amount': 12000.00},
            '金额调整',
            self.buyer
        )
        self.letter_of_credit.refresh_from_db()
        assert self.letter_of_credit.status == 'amending'
        assert amendment.status == 'pending'

        # 2. 批准修改
        LetterOfCreditService.approve_amendment(self.letter_of_credit, amendment.id)
        self.letter_of_credit.refresh_from_db()
        assert self.letter_of_credit.status == 'issued'

        amendment.refresh_from_db()
        assert amendment.status == 'approved'

    def test_lc_document_submission_flow(self):
        """测试信用证交单流程：已开证 -> 已交单"""
        self.letter_of_credit.status = 'issued'
        self.letter_of_credit.save()

        # 提交单据
        LetterOfCreditService.submit_documents(
            self.letter_of_credit,
            [1, 2, 3],
            self.seller
        )
        self.letter_of_credit.refresh_from_db()
        assert self.letter_of_credit.status == 'submitted'
        assert self.letter_of_credit.submitted_at is not None

    def test_lc_complete_flow(self):
        """测试信用证完整流程：开证 -> 交单 -> 议付 -> 付款"""
        # 1. 开证
        LetterOfCreditService.apply_for_issue(self.letter_of_credit, self.buyer)
        LetterOfCreditService.auto_issue(self.letter_of_credit)

        # 2. 交单
        LetterOfCreditService.submit_documents(self.letter_of_credit, [1, 2, 3], self.seller)

        # 3. 议付
        LetterOfCreditService.auto_negotiate(self.letter_of_credit)
        self.letter_of_credit.refresh_from_db()
        assert self.letter_of_credit.status == 'paid'
        assert self.letter_of_credit.negotiated_at is not None
        assert self.letter_of_credit.paid_at is not None


class CompleteWorkflowTest(TestCase):
    """完整业务流程测试"""

    def setUp(self):
        self.buyer = User.objects.create_user(username='buyer', password='testpass', email='buyer@example.com')
        self.seller = User.objects.create_user(username='seller', password='testpass', email='seller@example.com')

    def test_complete_trade_workflow(self):
        """测试完整贸易流程：询盘 -> 合同 -> 信用证 -> 结算"""
        # 1. 创建交易
        transaction = Transaction.objects.create(
            buyer=self.buyer,
            seller=self.seller,
            product_id=1,
            quantity=1000,
            unit_price=10.00,
            status='pending_contract'
        )

        # 2. 创建合同
        contract = Contract.objects.create(
            contract_no='SC2026002',
            transaction=transaction,
            trade_term='FOB Shanghai',
            payment_term='L/C',
            delivery_time=date(2026, 6, 30),
            port_of_loading='Shanghai',
            port_of_discharge='New York',
            product_name='测试商品',
            quantity=1000,
            unit='PCS',
            unit_price=11.00,
            total_amount=11000.00,
            currency='USD'
        )

        # 3. 合同确认和签字
        ContractService.send_for_confirmation(contract, self.buyer)
        ContractService.confirm_terms(contract, self.seller)
        ContractService.sign(contract, self.buyer, 'buyer', '127.0.0.1')
        ContractService.sign(contract, self.seller, 'seller', '127.0.0.1')

        assert contract.status == 'signed'
        # Note: transaction status remains pending_contract in this scenario
        # In real flow it would be updated by StateTransitionService

        # 4. 创建信用证
        lc = LetterOfCredit.objects.create(
            lc_no='LC2026002',
            contract=contract,
            transaction=transaction,
            status='draft',
            issuing_bank='中国银行',
            advising_bank='花旗银行',
            applicant=self.buyer,
            beneficiary=self.seller,
            amount=11000.00,
            currency='USD',
            expiry_date=date(2026, 7, 31),
            latest_shipment_date=date(2026, 7, 15),
            port_of_loading='Shanghai',
            port_of_discharge='New York',
            documents_required=['商业发票', '提单', '装箱单']
        )

        # 5. 信用证开证
        LetterOfCreditService.apply_for_issue(lc, self.buyer)
        LetterOfCreditService.auto_issue(lc)

        # 6. 卖方交单
        LetterOfCreditService.submit_documents(lc, [1, 2, 3], self.seller)

        # 7. 银行议付（会自动触发付款）
        LetterOfCreditService.auto_negotiate(lc)

        # 验证最终状态
        lc.refresh_from_db()
        assert lc.status == 'paid'

        # 验证银行操作记录
        operations = BankOperation.objects.filter(lc=lc)
        assert operations.filter(operation_type='issue').exists()
        assert operations.filter(operation_type='advise').exists()
        assert operations.filter(operation_type='negotiate').exists()
        assert operations.filter(operation_type='pay').exists()
