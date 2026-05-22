import pytest
from django.test import TestCase
from datetime import date, datetime
from django.utils import timezone
from apps.transactions.models import (
    Transaction, Contract, ContractSignature, TransactionLog, ContractAmendment
)
from apps.transactions.services import ContractService
from apps.users.models import User


class ContractServiceTest(TestCase):
    """测试合同业务服务"""

    def setUp(self):
        """设置测试数据"""
        self.buyer = User.objects.create_user(
            username='contract_buyer',
            password='testpass',
            email='cbuyer@test.com'
        )
        self.seller = User.objects.create_user(
            username='contract_seller',
            password='testpass',
            email='cseller@test.com'
        )
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
            trade_term='FOB',
            payment_term='L/C at sight',
            delivery_time=date(2026, 12, 31),
            port_of_loading='Shanghai',
            port_of_discharge='Los Angeles',
            product_name='Cotton T-Shirt',
            product_spec='100% Cotton, Size M',
            quantity=1000,
            unit='pcs',
            unit_price=10.00,
            total_amount=10000.00,
            currency='USD',
            status='draft'
        )

    def test_send_for_confirmation_draft_to_pending_confirm(self):
        """测试发送确认：草稿 -> 待确认"""
        # 初始状态为草稿
        assert self.contract.status == 'draft'

        # 发送确认
        result = ContractService.send_for_confirmation(self.contract, self.buyer)

        # 状态更新为待确认
        assert result.status == 'pending_confirm'
        assert self.contract.status == 'pending_confirm'

        # 检查日志记录
        log = TransactionLog.objects.filter(
            transaction=self.transaction,
            action='contract_sent_for_confirmation'
        ).first()
        assert log is not None
        assert log.user == self.buyer
        assert log.details['contract_id'] == self.contract.id

    def test_send_for_confirmation_invalid_status(self):
        """测试发送确认时状态不正确"""
        # 设置非草稿状态
        self.contract.status = 'pending_confirm'
        self.contract.save()

        # 应该抛出 ValueError
        with pytest.raises(ValueError, match='合同状态不允许发送确认'):
            ContractService.send_for_confirmation(self.contract, self.buyer)

    def test_confirm_terms_pending_to_pending_sign(self):
        """测试确认条款：待确认 -> 待签字"""
        # 设置为待确认状态
        self.contract.status = 'pending_confirm'
        self.contract.save()

        # 确认条款
        result = ContractService.confirm_terms(self.contract, self.seller)

        # 状态更新为待签字
        assert result.status == 'pending_sign'
        assert self.contract.status == 'pending_sign'

        # 检查日志记录
        log = TransactionLog.objects.filter(
            transaction=self.transaction,
            action='contract_terms_confirmed'
        ).first()
        assert log is not None
        assert log.user == self.seller

    def test_confirm_terms_invalid_status(self):
        """测试确认条款时状态不正确"""
        # 设置为草稿状态
        self.contract.status = 'draft'
        self.contract.save()

        # 应该抛出 ValueError
        with pytest.raises(ValueError, match='合同状态不允许确认'):
            ContractService.confirm_terms(self.contract, self.seller)

    def test_request_amendment_pending_to_amending(self):
        """测试请求修改：待确认 -> 修改中"""
        # 设置为待确认状态
        self.contract.status = 'pending_confirm'
        self.contract.save()

        # 请求修改
        change_content = {'unit_price': 12.00}
        reason = '原材料价格上涨'
        result = ContractService.request_amendment(
            self.contract,
            change_content,
            reason,
            self.seller
        )

        # 状态更新为修改中
        assert result.status == 'amending'
        assert self.contract.status == 'amending'

        # 检查修改记录
        amendment = ContractAmendment.objects.filter(contract=self.contract).first()
        assert amendment is not None
        assert amendment.requested_by == self.seller
        assert amendment.change_content == change_content
        assert amendment.reason == reason
        assert amendment.amendment_no == f'{self.contract.contract_no}-A01'

    def test_request_amendment_invalid_status(self):
        """测试请求修改时状态不正确"""
        # 设置为草稿状态
        self.contract.status = 'draft'
        self.contract.save()

        # 应该抛出 ValueError
        with pytest.raises(ValueError, match='合同状态不允许请求修改'):
            ContractService.request_amendment(
                self.contract,
                {'unit_price': 12.00},
                'test',
                self.seller
            )

    def test_request_amendment_generates_unique_numbers(self):
        """测试修改编号唯一性"""
        # 设置为待确认状态
        self.contract.status = 'pending_confirm'
        self.contract.save()

        # 第一次修改
        ContractService.request_amendment(
            self.contract,
            {'unit_price': 11.00},
            '第一次修改',
            self.seller
        )

        # 重置状态
        self.contract.status = 'pending_confirm'
        self.contract.save()

        # 第二次修改
        ContractService.request_amendment(
            self.contract,
            {'unit_price': 13.00},
            '第二次修改',
            self.buyer
        )

        # 检查编号
        amendments = ContractAmendment.objects.filter(
            contract=self.contract
        ).order_by('created_at')

        assert amendments[0].amendment_no == f'{self.contract.contract_no}-A01'
        assert amendments[1].amendment_no == f'{self.contract.contract_no}-A02'

    def test_accept_amendment_amending_to_pending_confirm(self):
        """测试接受修改：修改中 -> 待确认"""
        # 设置为修改中状态
        self.contract.status = 'amending'
        self.contract.save()

        # 创建修改记录
        amendment = ContractAmendment.objects.create(
            contract=self.contract,
            amendment_no=f'{self.contract.contract_no}-A01',
            requested_by=self.seller,
            change_content={'unit_price': 12.00, 'total_amount': 12000.00},
            reason='价格调整'
        )

        # 保存原始价格
        original_price = self.contract.unit_price

        # 接受修改
        result = ContractService.accept_amendment(
            self.contract,
            amendment.id,
            self.buyer
        )

        # 状态更新为待确认
        assert result.status == 'pending_confirm'
        assert self.contract.status == 'pending_confirm'

        # 检查修改记录状态
        amendment.refresh_from_db()
        assert amendment.status == 'accepted'
        assert amendment.processed_at is not None

        # 检查合同字段已更新
        self.contract.refresh_from_db()
        assert self.contract.unit_price == 12.00
        assert self.contract.total_amount == 12000.00

    def test_accept_amendment_invalid_status(self):
        """测试接受修改时状态不正确"""
        # 设置为草稿状态
        self.contract.status = 'draft'
        self.contract.save()

        # 创建修改记录
        amendment = ContractAmendment.objects.create(
            contract=self.contract,
            amendment_no='A01',
            requested_by=self.seller,
            change_content={'unit_price': 12.00},
            reason='test'
        )

        # 应该抛出 ValueError
        with pytest.raises(ValueError, match='合同状态不允许接受修改'):
            ContractService.accept_amendment(self.contract, amendment.id, self.buyer)

    def test_sign_buyer_pending_to_one_signed(self):
        """测试买方签字：待签字 -> 一方签字"""
        # 设置为待签字状态
        self.contract.status = 'pending_sign'
        self.contract.save()

        # 买方签字
        result = ContractService.sign(
            self.contract,
            self.buyer,
            'buyer',
            '192.168.1.100'
        )

        # 状态更新为一方签字
        assert result.status == 'one_signed'

        # 检查签字时间
        assert self.contract.buyer_signed_at is not None
        assert self.contract.seller_signed_at is None

        # 检查签字记录
        signature = ContractSignature.objects.filter(
            contract=self.contract,
            party='buyer'
        ).first()
        assert signature is not None
        assert signature.signer == self.buyer
        assert signature.ip_address == '192.168.1.100'

    def test_sign_both_pending_to_signed(self):
        """测试双方签字：待签字 -> 已签字"""
        # 设置为待签字状态
        self.contract.status = 'pending_sign'
        self.contract.save()

        # 买方签字
        ContractService.sign(self.contract, self.buyer, 'buyer', '192.168.1.100')

        # 卖方签字
        result = ContractService.sign(self.contract, self.seller, 'seller', '192.168.1.101')

        # 状态更新为已签字
        assert result.status == 'signed'
        assert self.contract.status == 'signed'

        # 检查双方签字时间
        assert self.contract.buyer_signed_at is not None
        assert self.contract.seller_signed_at is not None

    def test_sign_one_signed_to_signed(self):
        """测试第二方签字：一方签字 -> 已签字"""
        # 设置为一方签字状态，买方已签字
        self.contract.status = 'one_signed'
        self.contract.buyer_signed_at = timezone.now()
        self.contract.save()

        # 卖方签字
        result = ContractService.sign(self.contract, self.seller, 'seller', '192.168.1.101')

        # 状态更新为已签字
        assert result.status == 'signed'

    def test_sign_invalid_status(self):
        """测试签字时状态不正确"""
        # 设置为草稿状态
        self.contract.status = 'draft'
        self.contract.save()

        # 应该抛出 ValueError
        with pytest.raises(ValueError, match='合同状态不允许签字'):
            ContractService.sign(self.contract, self.buyer, 'buyer', '192.168.1.100')

    def test_sign_twice_same_party(self):
        """测试同一方重复签字"""
        # 设置为待签字状态
        self.contract.status = 'pending_sign'
        self.contract.save()

        # 第一次签字
        ContractService.sign(self.contract, self.buyer, 'buyer', '192.168.1.100')

        # 第二次签字（同一方）
        # get_or_create 应该获取已有记录而不是创建新记录
        result = ContractService.sign(self.contract, self.buyer, 'buyer', '192.168.1.101')

        # 检查只有一条签字记录
        signatures = ContractSignature.objects.filter(
            contract=self.contract,
            party='buyer'
        )
        assert signatures.count() == 1

    def test_become_effective_signed_to_effective(self):
        """测试合同生效：已签字 -> 已生效"""
        # 设置为已签字状态
        self.contract.status = 'signed'
        self.contract.save()

        # 合同生效
        result = ContractService.become_effective(self.contract)

        # 状态更新为已生效
        assert result.status == 'effective'
        assert self.contract.status == 'effective'

        # 检查生效时间
        assert self.contract.effective_at is not None

    def test_become_effective_invalid_status(self):
        """测试生效时状态不正确"""
        # 设置为草稿状态
        self.contract.status = 'draft'
        self.contract.save()

        # 应该抛出 ValueError
        with pytest.raises(ValueError, match='合同状态不允许生效'):
            ContractService.become_effective(self.contract)

    def test_cancel_draft(self):
        """测试取消草稿合同"""
        # 取消合同
        result = ContractService.cancel(self.contract, self.buyer, '不需要了')

        # 状态更新为已取消
        assert result.status == 'cancelled'
        assert self.contract.status == 'cancelled'

        # 检查日志
        log = TransactionLog.objects.filter(
            transaction=self.transaction,
            action='contract_cancelled'
        ).first()
        assert log is not None
        assert log.user == self.buyer
        assert log.details['reason'] == '不需要了'

    def test_cancel_invalid_status_effective(self):
        """测试取消已生效合同（不允许）"""
        # 设置为已生效状态
        self.contract.status = 'effective'
        self.contract.save()

        # 应该抛出 ValueError
        with pytest.raises(ValueError, match='合同状态不允许取消'):
            ContractService.cancel(self.contract, self.buyer, '取消')

    def test_cancel_invalid_status_fulfilled(self):
        """测试取消已履行完毕合同（不允许）"""
        # 设置为履行完毕状态
        self.contract.status = 'fulfilled'
        self.contract.save()

        # 应该抛出 ValueError
        with pytest.raises(ValueError, match='合同状态不允许取消'):
            ContractService.cancel(self.contract, self.seller, '取消')

    def test_cancel_invalid_status_cancelled(self):
        """测试取消已取消合同（不允许）"""
        # 设置为已取消状态
        self.contract.status = 'cancelled'
        self.contract.save()

        # 应该抛出 ValueError
        with pytest.raises(ValueError, match='合同状态不允许取消'):
            ContractService.cancel(self.contract, self.buyer, '再次取消')

    def test_generate_amendment_no_format(self):
        """测试修改编号格式"""
        # 设置为待确认状态
        self.contract.status = 'pending_confirm'
        self.contract.save()

        # 请求修改
        ContractService.request_amendment(
            self.contract,
            {'unit_price': 11.00},
            'test',
            self.seller
        )

        # 检查编号格式
        amendment = ContractAmendment.objects.filter(contract=self.contract).first()
        assert amendment.amendment_no == f'{self.contract.contract_no}-A01'

    def test_full_contract_workflow(self):
        """测试完整合同流程"""
        # 1. 草稿 -> 待确认
        self.contract = ContractService.send_for_confirmation(self.contract, self.buyer)
        assert self.contract.status == 'pending_confirm'

        # 2. 待确认 -> 待签字
        self.contract = ContractService.confirm_terms(self.contract, self.seller)
        assert self.contract.status == 'pending_sign'

        # 3. 买方签字
        self.contract = ContractService.sign(self.contract, self.buyer, 'buyer', '127.0.0.1')
        assert self.contract.status == 'one_signed'

        # 4. 卖方签字
        self.contract = ContractService.sign(self.contract, self.seller, 'seller', '127.0.0.1')
        assert self.contract.status == 'signed'

        # 5. 合同生效
        self.contract = ContractService.become_effective(self.contract)
        assert self.contract.status == 'effective'
        assert self.contract.effective_at is not None

    def test_amendment_workflow(self):
        """测试修改流程"""
        # 1. 草稿 -> 待确认
        self.contract = ContractService.send_for_confirmation(self.contract, self.buyer)
        assert self.contract.status == 'pending_confirm'

        # 2. 请求修改
        self.contract = ContractService.request_amendment(
            self.contract,
            {'unit_price': 12.00, 'total_amount': 12000.00},
            '价格调整',
            self.seller
        )
        assert self.contract.status == 'amending'

        # 3. 接受修改
        amendment = ContractAmendment.objects.filter(contract=self.contract).first()
        self.contract = ContractService.accept_amendment(
            self.contract,
            amendment.id,
            self.buyer
        )
        assert self.contract.status == 'pending_confirm'

        # 4. 检查修改已应用
        self.contract.refresh_from_db()
        assert self.contract.unit_price == 12.00
        assert self.contract.total_amount == 12000.00
