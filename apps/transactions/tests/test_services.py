import pytest
from django.test import TestCase
from datetime import date, datetime
from django.utils import timezone
from apps.transactions.models import (
    Transaction, Contract, ContractSignature, TransactionLog, ContractAmendment
)
from apps.transactions.models import LetterOfCredit, LcAmendment, BankOperation
from apps.transactions.services import ContractService, LetterOfCreditService, StateTransitionService
from apps.users.models import User
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
        self.buyer_company = create_company_for_user(self.buyer, '_服务买方')
        self.seller_company = create_company_for_user(self.seller, '_服务卖方')
        self.product = Product.objects.create(code='FIX-P0001', name='Test Product', category='electronics', unit='PCS')
        self.transaction = Transaction.objects.create(
            buyer=self.buyer_company,
            seller=self.seller_company,
            product=self.product,
            quantity=1000,
            unit_price=10.00,
            status='pending_contract',
            created_by=self.buyer  # 设置创建者为买家用户
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


class LetterOfCreditServiceTest(TestCase):
    """测试信用证业务服务"""

    def setUp(self):
        """设置测试数据"""
        self.buyer = User.objects.create_user(
            username='lc_buyer',
            password='testpass',
            email='lc_buyer@test.com'
        )
        self.seller = User.objects.create_user(
            username='lc_seller',
            password='testpass',
            email='lc_seller@test.com'
        )
        self.buyer_company = create_company_for_user(self.buyer, '_服务LC买方')
        self.seller_company = create_company_for_user(self.seller, '_服务LC卖方')
        self.product = Product.objects.create(code='FIX-P0002', name='Test Product', category='electronics', unit='PCS')
        self.transaction = Transaction.objects.create(
            buyer=self.buyer_company,
            seller=self.seller_company,
            product=self.product,
            quantity=1000,
            unit_price=10.00,
            status='pending_contract',
            created_by=self.buyer  # 设置创建者为买家用户
        )
        self.contract = Contract.objects.create(
            contract_no='SC2026001',
            transaction=self.transaction,
            trade_term='FOB',
            payment_term='L/C',
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
            status='effective'
        )

    def test_create_lc_from_contract(self):
        """测试从合同创建信用证"""
        lc = LetterOfCreditService.create_from_contract(self.contract)

        assert lc.status == 'draft'
        assert lc.contract == self.contract
        assert lc.lc_no.startswith('LC2026')
        assert lc.amount == 10000.00
        assert lc.currency == 'USD'
        assert lc.applicant == self.buyer_company
        assert lc.beneficiary == self.seller_company
        assert lc.port_of_loading == 'Shanghai'
        assert lc.port_of_discharge == 'Los Angeles'

    def test_create_lc_from_non_lc_contract(self):
        """测试非L/C合同创建信用证返回None"""
        self.contract.payment_term = 'T/T'
        self.contract.save()

        lc = LetterOfCreditService.create_from_contract(self.contract)

        assert lc is None

    def test_create_lc_creates_transaction_log(self):
        """测试创建信用证生成交易日志"""
        lc = LetterOfCreditService.create_from_contract(self.contract)

        log = TransactionLog.objects.filter(
            transaction=self.transaction,
            action='lc_created'
        ).first()
        assert log is not None
        assert log.details['lc_id'] == lc.id

    def test_apply_for_issue(self):
        """测试申请开证：草稿 -> 待开证"""
        lc = LetterOfCreditService.create_from_contract(self.contract)

        result = LetterOfCreditService.apply_for_issue(lc, self.buyer)

        assert result.status == 'pending_issue'
        lc.refresh_from_db()
        assert lc.status == 'pending_issue'

    def test_apply_for_issue_creates_log(self):
        """测试申请开证创建日志"""
        lc = LetterOfCreditService.create_from_contract(self.contract)

        LetterOfCreditService.apply_for_issue(lc, self.buyer)

        log = TransactionLog.objects.filter(
            transaction=self.transaction,
            action='lc_applied_for_issue'
        ).first()
        assert log is not None
        assert log.user == self.buyer

    def test_apply_for_issue_invalid_status(self):
        """测试申请开证时状态不正确"""
        lc = LetterOfCreditService.create_from_contract(self.contract)
        lc.status = 'issued'
        lc.save()

        with pytest.raises(ValueError, match='信用证状态不允许申请开证'):
            LetterOfCreditService.apply_for_issue(lc, self.buyer)

    def test_auto_issue(self):
        """测试系统自动开证：待开证 -> 已开证"""
        lc = LetterOfCreditService.create_from_contract(self.contract)
        lc.status = 'pending_issue'
        lc.save()

        result = LetterOfCreditService.auto_issue(lc)

        assert result.status == 'issued'
        lc.refresh_from_db()
        assert lc.status == 'issued'
        assert lc.issue_date is not None
        assert lc.issued_at is not None
        assert lc.advised_at is not None

    def test_auto_issue_creates_bank_operations(self):
        """测试自动开证创建银行操作记录"""
        lc = LetterOfCreditService.create_from_contract(self.contract)
        lc.status = 'pending_issue'
        lc.save()

        LetterOfCreditService.auto_issue(lc)

        # 检查开证操作
        issue_op = BankOperation.objects.filter(
            lc=lc,
            operation_type='issue'
        ).first()
        assert issue_op is not None
        assert issue_op.notes == '系统自动开证'

        # 检查通知操作
        advise_op = BankOperation.objects.filter(
            lc=lc,
            operation_type='advise'
        ).first()
        assert advise_op is not None
        assert advise_op.notes == '系统自动通知'

    def test_auto_issue_creates_log(self):
        """测试自动开证创建日志"""
        lc = LetterOfCreditService.create_from_contract(self.contract)
        lc.status = 'pending_issue'
        lc.save()

        LetterOfCreditService.auto_issue(lc)

        log = TransactionLog.objects.filter(
            transaction=self.transaction,
            action='lc_issued'
        ).first()
        assert log is not None
        assert log.user == self.buyer  # transaction.created_by 是买家

    def test_auto_issue_invalid_status(self):
        """测试自动开证时状态不正确"""
        lc = LetterOfCreditService.create_from_contract(self.contract)
        lc.status = 'draft'
        lc.save()

        with pytest.raises(ValueError, match='信用证状态不允许开证'):
            LetterOfCreditService.auto_issue(lc)

    def test_request_amendment(self):
        """测试请求修改：已开证 -> 修改中"""
        lc = LetterOfCreditService.create_from_contract(self.contract)
        lc.status = 'issued'
        lc.save()

        content = {'amount': 12000.00}
        reason = '数量增加'
        amendment = LetterOfCreditService.request_amendment(lc, content, reason, self.buyer)

        # 检查 LC 状态变为修改中
        lc.refresh_from_db()
        assert lc.status == 'amending'
        # 检查返回的是 amendment 对象
        assert amendment.amendment_no.startswith('LC2026')
        assert amendment.amendment_no.endswith('-A01')

    def test_request_amendment_creates_amendment_record(self):
        """测试请求修改创建修改记录"""
        lc = LetterOfCreditService.create_from_contract(self.contract)
        lc.status = 'issued'
        lc.save()

        content = {'amount': 12000.00}
        reason = '数量增加'
        amendment = LetterOfCreditService.request_amendment(lc, content, reason, self.buyer)

        assert amendment.initiated_by == self.buyer
        assert amendment.content == content
        assert amendment.reason == reason
        assert amendment.status == 'pending'

    def test_request_amendment_invalid_status(self):
        """测试请求修改时状态不正确"""
        lc = LetterOfCreditService.create_from_contract(self.contract)
        lc.status = 'draft'
        lc.save()

        with pytest.raises(ValueError, match='信用证状态不允许请求修改'):
            LetterOfCreditService.request_amendment(
                lc,
                {'amount': 12000.00},
                'test',
                self.buyer
            )

    def test_approve_amendment(self):
        """测试批准修改：修改中 -> 已开证"""
        lc = LetterOfCreditService.create_from_contract(self.contract)
        lc.status = 'issued'
        lc.save()

        # 请求修改
        amendment = LetterOfCreditService.request_amendment(
            lc,
            {'amount': 12000.00},
            '数量增加',
            self.buyer
        )

        # 批准修改
        result = LetterOfCreditService.approve_amendment(lc, amendment.id)

        assert result.status == 'issued'
        lc.refresh_from_db()
        assert lc.status == 'issued'
        assert lc.amount == 12000.00

    def test_approve_amendment_updates_amendment_status(self):
        """测试批准修改更新修改记录状态"""
        lc = LetterOfCreditService.create_from_contract(self.contract)
        lc.status = 'issued'
        lc.save()

        amendment = LetterOfCreditService.request_amendment(
            lc,
            {'amount': 12000.00},
            '数量增加',
            self.buyer
        )

        LetterOfCreditService.approve_amendment(lc, amendment.id)

        amendment.refresh_from_db()
        assert amendment.status == 'approved'
        assert amendment.processed_at is not None

    def test_approve_amendment_invalid_status(self):
        """测试批准修改时状态不正确"""
        lc = LetterOfCreditService.create_from_contract(self.contract)
        lc.status = 'draft'
        lc.save()

        with pytest.raises(ValueError, match='信用证状态不允许批准修改'):
            LetterOfCreditService.approve_amendment(lc, 1)

    def test_withdraw_amendment(self):
        """测试撤回修改请求：修改中 -> 已开证"""
        lc = LetterOfCreditService.create_from_contract(self.contract)
        lc.status = 'issued'
        lc.save()

        # 请求修改
        LetterOfCreditService.request_amendment(
            lc,
            {'amount': 12000.00},
            '数量增加',
            self.buyer
        )

        # 撤回修改
        result = LetterOfCreditService.withdraw_amendment(lc, self.buyer)

        assert result.status == 'issued'
        lc.refresh_from_db()
        assert lc.status == 'issued'

    def test_withdraw_amendment_deletes_pending_amendments(self):
        """测试撤回修改删除待处理的修改记录"""
        lc = LetterOfCreditService.create_from_contract(self.contract)
        lc.status = 'issued'
        lc.save()

        amendment = LetterOfCreditService.request_amendment(
            lc,
            {'amount': 12000.00},
            '数量增加',
            self.buyer
        )

        LetterOfCreditService.withdraw_amendment(lc, self.buyer)

        # 检查修改记录已被删除
        exists = LcAmendment.objects.filter(id=amendment.id).exists()
        assert exists is False

    def test_withdraw_amendment_invalid_status(self):
        """测试撤回修改时状态不正确"""
        lc = LetterOfCreditService.create_from_contract(self.contract)
        lc.status = 'draft'
        lc.save()

        with pytest.raises(ValueError, match='信用证状态不允许撤回修改'):
            LetterOfCreditService.withdraw_amendment(lc, self.buyer)

    def test_submit_documents(self):
        """测试交单：已开证 -> 已交单"""
        lc = LetterOfCreditService.create_from_contract(self.contract)
        lc.status = 'issued'
        lc.save()

        document_ids = [1, 2, 3]
        result = LetterOfCreditService.submit_documents(lc, document_ids, self.seller)

        assert result.status == 'submitted'
        lc.refresh_from_db()
        assert lc.status == 'submitted'
        assert lc.submitted_at is not None

    def test_submit_documents_creates_log(self):
        """测试交单创建日志"""
        lc = LetterOfCreditService.create_from_contract(self.contract)
        lc.status = 'issued'
        lc.save()

        document_ids = [1, 2, 3]
        LetterOfCreditService.submit_documents(lc, document_ids, self.seller)

        log = TransactionLog.objects.filter(
            transaction=self.transaction,
            action='lc_documents_submitted'
        ).first()
        assert log is not None
        assert log.details['document_count'] == 3

    def test_submit_documents_invalid_status(self):
        """测试交单时状态不正确"""
        lc = LetterOfCreditService.create_from_contract(self.contract)
        lc.status = 'draft'
        lc.save()

        with pytest.raises(ValueError, match='信用证状态不允许交单'):
            LetterOfCreditService.submit_documents(lc, [1, 2], self.seller)

    def test_auto_negotiate(self):
        """测试系统自动议付：已交单 -> 已议付（自动付款）"""
        lc = LetterOfCreditService.create_from_contract(self.contract)
        lc.status = 'submitted'
        lc.save()

        result = LetterOfCreditService.auto_negotiate(lc)

        # auto_negotiate 会触发 auto_pay，所以最终状态是 paid
        assert result.status == 'paid'
        lc.refresh_from_db()
        assert lc.status == 'paid'
        assert lc.negotiated_at is not None
        assert lc.paid_at is not None

    def test_auto_negotiate_creates_bank_operation(self):
        """测试自动议付创建银行操作记录"""
        lc = LetterOfCreditService.create_from_contract(self.contract)
        lc.status = 'submitted'
        lc.save()

        LetterOfCreditService.auto_negotiate(lc)

        op = BankOperation.objects.filter(
            lc=lc,
            operation_type='negotiate'
        ).first()
        assert op is not None
        assert op.notes == '单据齐全，自动议付'

    def test_auto_negotiate_triggers_auto_pay(self):
        """测试自动议付触发自动付款"""
        lc = LetterOfCreditService.create_from_contract(self.contract)
        lc.status = 'submitted'
        lc.save()

        LetterOfCreditService.auto_negotiate(lc)

        lc.refresh_from_db()
        assert lc.status == 'paid'
        assert lc.paid_at is not None

    def test_auto_negotiate_wrong_status_no_op(self):
        """测试自动议付状态不正确时不操作"""
        lc = LetterOfCreditService.create_from_contract(self.contract)
        lc.status = 'draft'
        lc.save()

        result = LetterOfCreditService.auto_negotiate(lc)

        assert result.status == 'draft'

    def test_auto_pay(self):
        """测试系统自动付款：已议付 -> 已付款"""
        lc = LetterOfCreditService.create_from_contract(self.contract)
        lc.status = 'negotiated'
        lc.save()

        result = LetterOfCreditService.auto_pay(lc)

        assert result.status == 'paid'
        lc.refresh_from_db()
        assert lc.status == 'paid'
        assert lc.paid_at is not None

    def test_auto_pay_creates_bank_operation(self):
        """测试自动付款创建银行操作记录"""
        lc = LetterOfCreditService.create_from_contract(self.contract)
        lc.status = 'negotiated'
        lc.save()

        LetterOfCreditService.auto_pay(lc)

        op = BankOperation.objects.filter(
            lc=lc,
            operation_type='pay'
        ).first()
        assert op is not None
        assert '自动付款' in op.notes
        # Decimal 转字符串后可能去掉尾部零
        assert op.result['amount'] in ['10000.00', '10000.0']
        assert op.result['currency'] == 'USD'

    def test_auto_pay_wrong_status_no_op(self):
        """测试自动付款状态不正确时不操作"""
        lc = LetterOfCreditService.create_from_contract(self.contract)
        lc.status = 'draft'
        lc.save()

        result = LetterOfCreditService.auto_pay(lc)

        assert result.status == 'draft'

    def test_cancel(self):
        """测试取消信用证"""
        lc = LetterOfCreditService.create_from_contract(self.contract)

        result = LetterOfCreditService.cancel(lc, self.buyer, '不需要了')

        assert result.status == 'cancelled'
        lc.refresh_from_db()
        assert lc.status == 'cancelled'

    def test_cancel_creates_log(self):
        """测试取消创建日志"""
        lc = LetterOfCreditService.create_from_contract(self.contract)

        LetterOfCreditService.cancel(lc, self.buyer, '不需要了')

        log = TransactionLog.objects.filter(
            transaction=self.transaction,
            action='lc_cancelled'
        ).first()
        assert log is not None
        assert log.details['reason'] == '不需要了'

    def test_cancel_invalid_status_negotiated(self):
        """测试取消已议付信用证（不允许）"""
        lc = LetterOfCreditService.create_from_contract(self.contract)
        lc.status = 'negotiated'
        lc.save()

        with pytest.raises(ValueError, match='信用证状态不允许取消'):
            LetterOfCreditService.cancel(lc, self.buyer, '取消')

    def test_cancel_invalid_status_paid(self):
        """测试取消已付款信用证（不允许）"""
        lc = LetterOfCreditService.create_from_contract(self.contract)
        lc.status = 'paid'
        lc.save()

        with pytest.raises(ValueError, match='信用证状态不允许取消'):
            LetterOfCreditService.cancel(lc, self.seller, '取消')

    def test_generate_lc_no_format(self):
        """测试信用证号格式"""
        lc = LetterOfCreditService.create_from_contract(self.contract)

        assert lc.lc_no.startswith('LC2026')
        assert len(lc.lc_no) == 12  # LC + 4位年份 + 6位随机数字

    def test_generate_amendment_no_format(self):
        """测试修改编号格式"""
        lc = LetterOfCreditService.create_from_contract(self.contract)
        lc.status = 'issued'
        lc.save()

        amendment = LetterOfCreditService.request_amendment(
            lc,
            {'amount': 12000.00},
            'test',
            self.buyer
        )

        assert amendment.amendment_no == f'{lc.lc_no}-A01'

    def test_generate_amendment_no_sequence(self):
        """测试修改编号序列"""
        lc = LetterOfCreditService.create_from_contract(self.contract)
        lc.status = 'issued'
        lc.save()

        # 第一次修改
        LetterOfCreditService.request_amendment(
            lc,
            {'amount': 11000.00},
            '第一次',
            self.buyer
        )
        # 重置状态
        lc.status = 'issued'
        lc.save()

        # 第二次修改
        LetterOfCreditService.request_amendment(
            lc,
            {'amount': 12000.00},
            '第二次',
            self.buyer
        )

        amendments = LcAmendment.objects.filter(lc=lc).order_by('created_at')
        assert amendments[0].amendment_no == f'{lc.lc_no}-A01'
        assert amendments[1].amendment_no == f'{lc.lc_no}-A02'

    def test_full_lc_workflow(self):
        """测试完整信用证流程"""
        # 1. 从合同创建信用证
        lc = LetterOfCreditService.create_from_contract(self.contract)
        assert lc.status == 'draft'

        # 2. 申请开证
        lc = LetterOfCreditService.apply_for_issue(lc, self.buyer)
        assert lc.status == 'pending_issue'

        # 3. 自动开证
        lc = LetterOfCreditService.auto_issue(lc)
        assert lc.status == 'issued'

        # 4. 交单
        lc = LetterOfCreditService.submit_documents(lc, [1, 2, 3], self.seller)
        assert lc.status == 'submitted'

        # 5. 自动议付（触发自动付款）
        lc = LetterOfCreditService.auto_negotiate(lc)
        assert lc.status == 'paid'

    def test_amendment_workflow(self):
        """测试修改流程"""
        # 1. 创建并开立信用证
        lc = LetterOfCreditService.create_from_contract(self.contract)
        lc = LetterOfCreditService.apply_for_issue(lc, self.buyer)
        lc = LetterOfCreditService.auto_issue(lc)
        assert lc.status == 'issued'

        # 2. 请求修改
        amendment = LetterOfCreditService.request_amendment(
            lc,
            {'amount': 12000.00},
            '数量增加',
            self.buyer
        )
        assert lc.status == 'amending'

        # 3. 批准修改
        lc = LetterOfCreditService.approve_amendment(lc, amendment.id)
        assert lc.status == 'issued'
        assert lc.amount == 12000.00


class StateTransitionServiceTest(TestCase):
    """测试状态联动服务"""

    def setUp(self):
        """设置测试数据"""
        self.buyer = User.objects.create_user(
            username='state_buyer',
            password='testpass',
            email='state_buyer@test.com'
        )
        self.seller = User.objects.create_user(
            username='state_seller',
            password='testpass',
            email='state_seller@test.com'
        )
        self.buyer_company = create_company_for_user(self.buyer, '_服务状态买方')
        self.seller_company = create_company_for_user(self.seller, '_服务状态卖方')
        self.product = Product.objects.create(code='FIX-P0003', name='Test Product', category='electronics', unit='PCS')
        self.transaction = Transaction.objects.create(
            buyer=self.buyer_company,
            seller=self.seller_company,
            product=self.product,
            quantity=1000,
            unit_price=10.00,
            status='contracted',
            created_by=self.buyer  # 设置创建者为买家用户
        )
        self.contract = Contract.objects.create(
            contract_no='SC2026001',
            transaction=self.transaction,
            trade_term='FOB',
            payment_term='L/C',
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
            status='signed'
        )

    def test_on_contract_effective_updates_transaction_status(self):
        """测试合同生效联动：更新交易状态"""
        # 确保交易状态为 contracted
        self.transaction.status = 'contracted'
        self.transaction.save()

        # 触发合同生效联动
        StateTransitionService.on_contract_effective(self.contract)

        # 检查交易状态更新为 in_progress
        self.transaction.refresh_from_db()
        assert self.transaction.status == 'in_progress'

    def test_on_contract_effective_creates_lc_for_lc_payment(self):
        """测试合同生效联动：L/C支付方式自动创建信用证"""
        # 确保支付方式是 L/C
        self.contract.payment_term = 'L/C at sight'
        self.contract.save()

        # 触发合同生效联动
        StateTransitionService.on_contract_effective(self.contract)

        # 检查信用证已创建
        lc = LetterOfCredit.objects.filter(contract=self.contract).first()
        assert lc is not None
        assert lc.status == 'draft'
        assert lc.amount == 10000.00

    def test_on_contract_effective_no_lc_for_non_lc_payment(self):
        """测试合同生效联动：非L/C支付方式不创建信用证"""
        # 设置为非 L/C 支付方式
        self.contract.payment_term = 'T/T'
        self.contract.save()

        # 触发合同生效联动
        StateTransitionService.on_contract_effective(self.contract)

        # 检查没有创建信用证
        lc_exists = LetterOfCredit.objects.filter(contract=self.contract).exists()
        assert lc_exists is False

    def test_on_contract_effective_creates_transaction_log(self):
        """测试合同生效联动：创建交易日志"""
        # 触发合同生效联动
        StateTransitionService.on_contract_effective(self.contract)

        # 检查日志记录
        log = TransactionLog.objects.filter(
            transaction=self.transaction,
            action='contract_became_effective'
        ).first()
        assert log is not None
        assert log.user == self.buyer
        assert log.details['contract_id'] == self.contract.id

    def test_on_contract_effective_lc_payment_variations(self):
        """测试合同生效联动：支持多种L/C支付格式"""
        lc_payment_terms = ['L/C', 'L/C at sight', 'L/C 30 days', '100% L/C']

        for payment_term in lc_payment_terms:
            # 清理之前的信用证
            LetterOfCredit.objects.filter(contract=self.contract).delete()

            # 设置支付方式
            self.contract.payment_term = payment_term
            self.contract.save()

            # 触发联动
            StateTransitionService.on_contract_effective(self.contract)

            # 检查信用证已创建
            lc_exists = LetterOfCredit.objects.filter(contract=self.contract).exists()
            assert lc_exists is True, f'支付方式 {payment_term} 应该创建信用证'

    def test_on_lc_created_sends_notification(self):
        """测试信用证创建联动：发送通知"""
        # 创建信用证
        lc = LetterOfCreditService.create_from_contract(self.contract)

        # 触发信用证创建联动（验证方法可调用）
        StateTransitionService.on_lc_created(lc)

        # 如果实现了通知服务，这里会验证通知发送
        # 目前只是确保方法不会抛出错误

    def test_on_lc_issued_creates_log(self):
        """测试信用证开立联动：创建交易日志"""
        # 创建并开立信用证
        lc = LetterOfCreditService.create_from_contract(self.contract)
        lc.status = 'issued'
        lc.save()

        # 触发信用证开立联动
        StateTransitionService.on_lc_issued(lc)

        # 检查日志记录
        log = TransactionLog.objects.filter(
            transaction=self.transaction,
            action='lc_issued'
        ).first()
        assert log is not None
        assert log.user == self.buyer  # transaction.created_by 是买家
        assert log.details['lc_id'] == lc.id

    def test_on_lc_paid_creates_log(self):
        """测试信用证付款联动：创建交易日志"""
        # 创建并付款信用证
        lc = LetterOfCreditService.create_from_contract(self.contract)
        lc.status = 'paid'
        lc.save()

        # 触发信用证付款联动
        StateTransitionService.on_lc_paid(lc)

        # 检查日志记录
        log = TransactionLog.objects.filter(
            transaction=self.transaction,
            action='lc_paid'
        ).first()
        assert log is not None
        assert log.user == self.buyer  # 申请人
        assert log.details['lc_id'] == lc.id
        # Decimal 转字符串后可能去掉尾部零
        assert log.details['amount'] in ['10000.00', '10000.0']

    def test_on_contract_effective_transaction_already_in_progress(self):
        """测试合同生效联动：交易状态已为in_progress时不重复更新"""
        # 设置交易状态为 in_progress
        self.transaction.status = 'in_progress'
        self.transaction.save()

        # 触发联动
        StateTransitionService.on_contract_effective(self.contract)

        # 状态应保持 in_progress
        self.transaction.refresh_from_db()
        assert self.transaction.status == 'in_progress'
