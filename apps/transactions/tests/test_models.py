import pytest
from django.test import TestCase
from django.core.exceptions import ValidationError
from datetime import date, datetime
from apps.transactions.models import (
    Transaction, InquiryMessage, Contract, ContractSignature, TransactionLog,
    ContractAmendment, LetterOfCredit, LcAmendment, BankOperation
)
from apps.users.models import User
from apps.roles.services import CompanyService
from apps.core.models import Country


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


class TransactionModelTest(TestCase):
    """测试交易模型"""

    def setUp(self):
        self.buyer = User.objects.create_user(username='buyer', password='testpass', email='buyer@test.com')
        self.seller = User.objects.create_user(username='seller', password='testpass', email='seller@test.com')
        self.buyer_company = create_company_for_user(self.buyer, '_买方')
        self.seller_company = create_company_for_user(self.seller, '_卖方')

    def test_create_transaction(self):
        """测试创建交易"""
        transaction = Transaction.objects.create(
            buyer=self.buyer_company,
            seller=self.seller_company,
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
            buyer=self.buyer_company,
            seller=self.seller_company,
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
        self.buyer_company = create_company_for_user(self.buyer, '_买方2')
        self.seller_company = create_company_for_user(self.seller, '_卖方2')
        self.transaction = Transaction.objects.create(
            buyer=self.buyer_company,
            seller=self.seller_company,
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


class ContractModelTest(TestCase):
    """测试合同模型"""

    def setUp(self):
        self.buyer = User.objects.create_user(username='contract_buyer', password='testpass', email='cbuyer@test.com')
        self.seller = User.objects.create_user(username='contract_seller', password='testpass', email='cseller@test.com')
        self.buyer_company = create_company_for_user(self.buyer, '_合同买方')
        self.seller_company = create_company_for_user(self.seller, '_合同卖方')
        self.transaction = Transaction.objects.create(
            buyer=self.buyer_company,
            seller=self.seller_company,
            product_id=1,
            quantity=1000,
            unit_price=10.00,
            status='pending_contract'
        )

    def test_create_contract(self):
        """测试创建合同"""
        contract = Contract.objects.create(
            contract_no='CT202601001',
            transaction=self.transaction,
            trade_term='FOB',
            payment_term='T/T 30% in advance',
            delivery_time=date(2026, 6, 30),
            port_of_loading='Shanghai',
            port_of_discharge='Los Angeles',
            product_name='Cotton T-Shirt',
            product_spec='100% Cotton, Size M',
            quantity=1000,
            unit='pcs',
            unit_price=10.00,
            total_amount=10000.00,
            currency='USD'
        )
        assert contract.contract_no == 'CT202601001'
        assert contract.status == 'draft'
        assert contract.get_status_display() == '草稿'
        assert str(contract) == '合同 CT202601001'

    def test_contract_status_choices(self):
        """测试合同状态枚举"""
        contract = Contract.objects.create(
            contract_no='CT202601002',
            transaction=self.transaction,
            trade_term='CIF',
            payment_term='L/C at sight',
            delivery_time=date(2026, 7, 15),
            port_of_loading='Ningbo',
            port_of_discharge='Hamburg',
            product_name='Silk Scarf',
            quantity=500,
            unit='pcs',
            unit_price=25.00,
            total_amount=12500.00,
            currency='USD'
        )
        # 测试所有状态
        for status_code, display_name in Contract.Status.choices:
            contract.status = status_code
            contract.save()
            assert contract.get_status_display() == display_name

    def test_contract_field_validation(self):
        """测试合同字段验证"""
        contract = Contract.objects.create(
            contract_no='CT202601003',
            transaction=self.transaction,
            trade_term='FOB',
            payment_term='T/T',
            delivery_time=date(2026, 8, 1),
            port_of_loading='Shenzhen',
            port_of_discharge='Rotterdam',
            product_name='Wool Sweater',
            product_spec='Merino wool',
            quantity=2000,
            unit='pcs',
            unit_price=50.00,
            total_amount=100000.00,
            currency='EUR',
            packing='Carton package',
            shipping_marks='ABC/123',
            remarks='Partial shipment allowed'
        )
        assert contract.packing == 'Carton package'
        assert contract.shipping_marks == 'ABC/123'
        assert contract.remarks == 'Partial shipment allowed'

    def test_contract_unique_contract_no(self):
        """测试合同号唯一性"""
        Contract.objects.create(
            contract_no='CT202601004',
            transaction=self.transaction,
            trade_term='FOB',
            payment_term='T/T',
            delivery_time=date(2026, 9, 1),
            port_of_loading='Qingdao',
            port_of_discharge='New York',
            product_name='Linen Shirt',
            quantity=1500,
            unit='pcs',
            unit_price=30.00,
            total_amount=45000.00,
            currency='USD'
        )
        # 尝试创建相同合同号应失败
        with pytest.raises(Exception):  # IntegrityError
            Contract.objects.create(
                contract_no='CT202601004',
                transaction=self.transaction,
                trade_term='CIF',
                payment_term='L/C',
                delivery_time=date(2026, 10, 1),
                port_of_loading='Guangzhou',
                port_of_discharge='London',
                product_name='Denim Jeans',
                quantity=1000,
                unit='pcs',
                unit_price=40.00,
                total_amount=40000.00,
                currency='USD'
            )

    def test_contract_transaction_one_to_one(self):
        """测试交易与合同一对一关系"""
        contract = Contract.objects.create(
            contract_no='CT202601005',
            transaction=self.transaction,
            trade_term='EXW',
            payment_term='D/P',
            delivery_time=date(2026, 11, 1),
            port_of_loading='Xiamen',
            port_of_discharge='Tokyo',
            product_name='Polyester Jacket',
            quantity=800,
            unit='pcs',
            unit_price=60.00,
            total_amount=48000.00,
            currency='JPY'
        )
        assert self.transaction.contract == contract


class ContractSignatureModelTest(TestCase):
    """测试合同签字记录模型"""

    def setUp(self):
        self.buyer = User.objects.create_user(username='sig_buyer', password='testpass', email='sbuyer@test.com')
        self.seller = User.objects.create_user(username='sig_seller', password='testpass', email='sseller@test.com')
        self.buyer_company = create_company_for_user(self.buyer, '_签字买方')
        self.seller_company = create_company_for_user(self.seller, '_签字卖方')
        self.transaction = Transaction.objects.create(
            buyer=self.buyer_company,
            seller=self.seller_company,
            product_id=1,
            quantity=1000,
            unit_price=10.00,
            status='pending_contract'
        )
        self.contract = Contract.objects.create(
            contract_no='CT202601010',
            transaction=self.transaction,
            trade_term='FOB',
            payment_term='T/T',
            delivery_time=date(2026, 6, 30),
            port_of_loading='Shanghai',
            port_of_discharge='Los Angeles',
            product_name='Cotton T-Shirt',
            quantity=1000,
            unit='pcs',
            unit_price=10.00,
            total_amount=10000.00,
            currency='USD'
        )

    def test_create_contract_signature(self):
        """测试创建签字记录"""
        signature = ContractSignature.objects.create(
            contract=self.contract,
            party='buyer',
            signer=self.buyer,
            signer_name='张三',
            ip_address='192.168.1.100'
        )
        assert signature.party == 'buyer'
        assert signature.signer == self.buyer
        assert signature.signer_name == '张三'
        assert signature.ip_address == '192.168.1.100'

    def test_signature_unique_together_constraint(self):
        """测试合同和当事方的唯一约束"""
        # 创建买方签字
        ContractSignature.objects.create(
            contract=self.contract,
            party='buyer',
            signer=self.buyer,
            signer_name='张三'
        )
        # 尝试为同一合同和当事方创建第二条记录应失败
        with pytest.raises(Exception):  # IntegrityError
            ContractSignature.objects.create(
                contract=self.contract,
                party='buyer',
                signer=self.buyer,
                signer_name='李四'
            )

    def test_multiple_parties_can_sign(self):
        """测试不同当事方可以签字"""
        buyer_sig = ContractSignature.objects.create(
            contract=self.contract,
            party='buyer',
            signer=self.buyer,
            signer_name='张三'
        )
        seller_sig = ContractSignature.objects.create(
            contract=self.contract,
            party='seller',
            signer=self.seller,
            signer_name='王五'
        )
        assert buyer_sig.party == 'buyer'
        assert seller_sig.party == 'seller'
        assert ContractSignature.objects.filter(contract=self.contract).count() == 2


class TransactionLogModelTest(TestCase):
    """测试交易操作日志模型"""

    def setUp(self):
        self.buyer = User.objects.create_user(username='log_buyer', password='testpass', email='lbuyer@test.com')
        self.seller = User.objects.create_user(username='log_seller', password='testpass', email='lseller@test.com')
        self.buyer_company = create_company_for_user(self.buyer, '_日志买方')
        self.seller_company = create_company_for_user(self.seller, '_日志卖方')
        self.transaction = Transaction.objects.create(
            buyer=self.buyer_company,
            seller=self.seller_company,
            product_id=1,
            quantity=1000,
            unit_price=10.00,
            status='inquiring'
        )

    def test_create_transaction_log(self):
        """测试创建交易日志"""
        log = TransactionLog.objects.create(
            transaction=self.transaction,
            user=self.buyer,
            action='status_change',
            details={'old_status': 'inquiring', 'new_status': 'negotiating'},
            ip_address='192.168.1.100'
        )
        assert log.action == 'status_change'
        assert log.user == self.buyer
        assert log.details['old_status'] == 'inquiring'
        assert log.details['new_status'] == 'negotiating'
        assert log.ip_address == '192.168.1.100'

    def test_transaction_log_jsonfield_details(self):
        """测试 JSONField 详情存储"""
        # 测试嵌套 JSON
        log = TransactionLog.objects.create(
            transaction=self.transaction,
            user=self.seller,
            action='offer_submitted',
            details={
                'quantity': 1500,
                'price': '9.50',
                'trade_term': 'FOB',
                'metadata': {
                    'source': 'web',
                    'device': 'desktop'
                }
            }
        )
        assert log.details['quantity'] == 1500
        assert log.details['price'] == '9.50'
        assert log.details['metadata']['source'] == 'web'

    def test_transaction_log_without_user(self):
        """测试无用户日志（系统操作）"""
        log = TransactionLog.objects.create(
            transaction=self.transaction,
            action='auto_reminder',
            details={'type': 'payment_reminder', 'days': 3}
        )
        assert log.user is None
        assert log.action == 'auto_reminder'

    def test_transaction_log_ordering(self):
        """测试日志按创建时间倒序排列"""
        log1 = TransactionLog.objects.create(
            transaction=self.transaction,
            user=self.buyer,
            action='action1',
            details={}
        )
        log2 = TransactionLog.objects.create(
            transaction=self.transaction,
            user=self.seller,
            action='action2',
            details={}
        )
        # 强制更新 log1 的创建时间，确保时间差
        from django.utils import timezone
        log1.created_at = timezone.now() - timezone.timedelta(seconds=1)
        log1.save()
        logs = list(TransactionLog.objects.filter(transaction=self.transaction))
        assert logs[0] == log2
        assert logs[1] == log1

    def test_transaction_log_relationships(self):
        """测试日志与交易的关系"""
        log = TransactionLog.objects.create(
            transaction=self.transaction,
            user=self.buyer,
            action='test_action',
            details={'test': 'data'}
        )
        assert log.transaction == self.transaction
        assert self.transaction.logs.filter(action='test_action').exists()


class ContractStatusExpansionTest(TestCase):
    """测试合同状态选项扩展"""

    def setUp(self):
        self.buyer = User.objects.create_user(username='status_buyer', password='testpass', email='sbuyer2@test.com')
        self.seller = User.objects.create_user(username='status_seller', password='testpass', email='sseller2@test.com')
        self.buyer_company = create_company_for_user(self.buyer, '_状态买方')
        self.seller_company = create_company_for_user(self.seller, '_状态卖方')
        self.transaction = Transaction.objects.create(
            buyer=self.buyer_company,
            seller=self.seller_company,
            product_id=1,
            quantity=1000,
            unit_price=10.00,
            status='pending_contract'
        )

    def test_contract_status_expansion(self):
        """测试合同状态选项扩展"""
        contract = Contract.objects.create(
            contract_no='SC001',
            transaction=self.transaction,
            trade_term='FOB',
            payment_term='L/C',
            delivery_time=date(2026, 12, 31),
            port_of_loading='Shanghai',
            port_of_discharge='Los Angeles',
            product_name='Test Product',
            quantity=1000,
            unit='pcs',
            unit_price=10.00,
            total_amount=10000.00,
            currency='USD'
        )

        # 测试新状态
        contract.status = 'pending_confirm'
        assert contract.get_status_display() == '待确认'

        contract.status = 'amending'
        assert contract.get_status_display() == '修改中'

        contract.status = 'one_signed'
        assert contract.get_status_display() == '一方签字'


class ContractAmendmentModelTest(TestCase):
    """测试合同修改记录模型"""

    def setUp(self):
        self.buyer = User.objects.create_user(username='amend_buyer', password='testpass', email='abuyer@test.com')
        self.seller = User.objects.create_user(username='amend_seller', password='testpass', email='aseller@test.com')
        self.buyer_company = create_company_for_user(self.buyer, '_修改买方')
        self.seller_company = create_company_for_user(self.seller, '_修改卖方')
        self.transaction = Transaction.objects.create(
            buyer=self.buyer_company,
            seller=self.seller_company,
            product_id=1,
            quantity=1000,
            unit_price=10.00,
            status='pending_contract'
        )
        self.contract = Contract.objects.create(
            contract_no='SC001',
            transaction=self.transaction,
            trade_term='FOB',
            payment_term='L/C',
            delivery_time=date(2026, 12, 31),
            port_of_loading='Shanghai',
            port_of_discharge='Los Angeles',
            product_name='Test Product',
            quantity=1000,
            unit='pcs',
            unit_price=10.00,
            total_amount=10000.00,
            currency='USD'
        )

    def test_create_contract_amendment(self):
        """测试创建合同修改记录"""
        amendment = ContractAmendment.objects.create(
            contract=self.contract,
            amendment_no='A001',
            requested_by=self.seller,
            change_content={'unit_price': 6.00},
            reason='价格调整'
        )

        assert amendment.amendment_no == 'A001'
        assert amendment.status == 'pending'
        assert amendment.get_status_display() == '待处理'
        assert amendment.change_content['unit_price'] == 6.00
        assert str(amendment) == 'SC001 - A001'
        assert self.contract.amendments.count() == 1

    def test_amendment_status_choices(self):
        """测试修改状态枚举"""
        amendment = ContractAmendment.objects.create(
            contract=self.contract,
            amendment_no='A002',
            requested_by=self.buyer,
            change_content={'quantity': 1500},
            reason='数量增加'
        )

        # 测试 pending 状态
        amendment.status = 'pending'
        assert amendment.get_status_display() == '待处理'

        # 测试 accepted 状态
        amendment.status = 'accepted'
        amendment.save()
        assert amendment.get_status_display() == '已接受'

        # 测试 rejected 状态
        amendment.status = 'rejected'
        amendment.save()
        assert amendment.get_status_display() == '已拒绝'

    def test_amendment_jsonfield_change_content(self):
        """测试 JSONField 修改内容存储"""
        amendment = ContractAmendment.objects.create(
            contract=self.contract,
            amendment_no='A003',
            requested_by=self.seller,
            change_content={
                'unit_price': 12.00,
                'quantity': 1200,
                'total_amount': 14400.00
            },
            reason='综合调整'
        )

        assert amendment.change_content['unit_price'] == 12.00
        assert amendment.change_content['quantity'] == 1200
        assert amendment.change_content['total_amount'] == 14400.00

    def test_amendment_without_requested_by(self):
        """测试无请求用户的修改记录"""
        amendment = ContractAmendment.objects.create(
            contract=self.contract,
            amendment_no='A004',
            requested_by=None,
            change_content={'port_of_discharge': 'Long Beach'},
            reason='目的港变更'
        )

        assert amendment.requested_by is None
        assert amendment.amendment_no == 'A004'

    def test_amendment_processed_at(self):
        """测试处理时间字段"""
        import django.utils.timezone as timezone
        amendment = ContractAmendment.objects.create(
            contract=self.contract,
            amendment_no='A005',
            requested_by=self.buyer,
            change_content={'delivery_time': '2027-01-31'},
            reason='交货期延期'
        )

        # 初始状态 processed_at 为空
        assert amendment.processed_at is None

        # 处理后设置时间
        amendment.status = 'accepted'
        amendment.processed_at = timezone.now()
        amendment.save()

        assert amendment.processed_at is not None

    def test_amendment_ordering(self):
        """测试修改记录按创建时间倒序排列"""
        import django.utils.timezone as timezone
        earlier_time = timezone.now() - timezone.timedelta(seconds=1)

        amendment1 = ContractAmendment.objects.create(
            contract=self.contract,
            amendment_no='A006',
            requested_by=self.seller,
            change_content={'field': 'value1'},
            reason='原因1'
        )
        # 强制设置更早的创建时间
        amendment1.created_at = earlier_time
        amendment1.save()

        amendment2 = ContractAmendment.objects.create(
            contract=self.contract,
            amendment_no='A007',
            requested_by=self.buyer,
            change_content={'field': 'value2'},
            reason='原因2'
        )

        amendments = list(self.contract.amendments.all())
        assert amendments[0] == amendment2
        assert amendments[1] == amendment1

    def test_amendment_relationships(self):
        """测试修改记录与合同的关系"""
        amendment = ContractAmendment.objects.create(
            contract=self.contract,
            amendment_no='A008',
            requested_by=self.seller,
            change_content={'test': 'data'},
            reason='测试'
        )

        assert amendment.contract == self.contract
        assert self.contract.amendments.filter(amendment_no='A008').exists()

    def test_amendment_unique_together_constraint(self):
        """测试合同和修改编号的唯一约束"""
        # 创建第一个修改记录
        ContractAmendment.objects.create(
            contract=self.contract,
            amendment_no='A099',
            requested_by=self.seller,
            change_content={'field': 'value1'},
            reason='原因1'
        )
        # 尝试为同一合同创建相同修改编号应失败
        with pytest.raises(Exception):  # IntegrityError
            ContractAmendment.objects.create(
                contract=self.contract,
                amendment_no='A099',
                requested_by=self.buyer,
                change_content={'field': 'value2'},
                reason='原因2'
            )

    def test_amendment_different_contracts_same_amendment_no(self):
        """测试不同合同可以有相同的修改编号"""
        # 创建另一个合同
        transaction2 = Transaction.objects.create(
            buyer=self.buyer_company,
            seller=self.seller_company,
            product_id=2,
            quantity=500,
            unit_price=20.00,
            status='pending_contract'
        )
        contract2 = Contract.objects.create(
            contract_no='SC002',
            transaction=transaction2,
            trade_term='CIF',
            payment_term='L/C',
            delivery_time=date(2026, 12, 31),
            port_of_loading='Shenzhen',
            port_of_discharge='Rotterdam',
            product_name='Another Product',
            quantity=500,
            unit='pcs',
            unit_price=20.00,
            total_amount=10000.00,
            currency='USD'
        )

        # 两个合同可以有相同的修改编号
        amendment1 = ContractAmendment.objects.create(
            contract=self.contract,
            amendment_no='A100',
            requested_by=self.seller,
            change_content={'field': 'value1'},
            reason='原因1'
        )
        amendment2 = ContractAmendment.objects.create(
            contract=contract2,
            amendment_no='A100',
            requested_by=self.buyer,
            change_content={'field': 'value2'},
            reason='原因2'
        )

        assert amendment1.amendment_no == amendment2.amendment_no
        assert amendment1.contract != amendment2.contract


class LetterOfCreditModelTest(TestCase):
    """测试信用证模型"""

    def setUp(self):
        self.buyer = User.objects.create_user(username='lc_buyer', password='testpass', email='lc_buyer@test.com')
        self.seller = User.objects.create_user(username='lc_seller', password='testpass', email='lc_seller@test.com')
        self.buyer_company = create_company_for_user(self.buyer, '_LC买方')
        self.seller_company = create_company_for_user(self.seller, '_LC卖方')
        self.transaction = Transaction.objects.create(
            buyer=self.buyer_company,
            seller=self.seller_company,
            product_id=1,
            quantity=1000,
            unit_price=10.00,
            status='pending_contract'
        )
        self.contract = Contract.objects.create(
            contract_no='SC001',
            transaction=self.transaction,
            trade_term='FOB',
            payment_term='L/C',
            delivery_time=date(2026, 12, 31),
            port_of_loading='Shanghai',
            port_of_discharge='Los Angeles',
            product_name='Test Product',
            quantity=1000,
            unit='pcs',
            unit_price=10.00,
            total_amount=10000.00,
            currency='USD'
        )

    def test_create_letter_of_credit(self):
        """测试创建信用证"""
        lc = LetterOfCredit.objects.create(
            lc_no='LC2026001',
            contract=self.contract,
            transaction=self.transaction,
            applicant=self.buyer_company,
            beneficiary=self.seller_company,
            amount=10000.00,
            currency='USD',
            expiry_date=date(2026, 12, 31),
            latest_shipment_date=date(2026, 11, 30),
            port_of_loading='Shanghai',
            port_of_discharge='Los Angeles',
            issuing_bank='中国银行',
            advising_bank='Bank of America'
        )

        assert lc.lc_no == 'LC2026001'
        assert lc.status == 'draft'
        assert lc.get_status_display() == '草稿'
        assert lc.amount == 10000.00
        assert str(lc) == '信用证 LC2026001'

    def test_letter_of_credit_status_choices(self):
        """测试信用证状态枚举"""
        lc = LetterOfCredit.objects.create(
            lc_no='LC2026002',
            contract=self.contract,
            transaction=self.transaction,
            applicant=self.buyer_company,
            beneficiary=self.seller_company,
            amount=10000.00,
            currency='USD',
            expiry_date=date(2026, 12, 31),
            latest_shipment_date=date(2026, 11, 30),
            port_of_loading='Shanghai',
            port_of_discharge='Los Angeles',
            issuing_bank='中国银行',
            advising_bank='Bank of America'
        )

        # 测试所有状态
        for status_code, display_name in LetterOfCredit.Status.choices:
            lc.status = status_code
            lc.save()
            assert lc.get_status_display() == display_name

    def test_letter_of_credit_unique_lc_no(self):
        """测试信用证号唯一性"""
        LetterOfCredit.objects.create(
            lc_no='LC2026003',
            contract=self.contract,
            transaction=self.transaction,
            applicant=self.buyer_company,
            beneficiary=self.seller_company,
            amount=10000.00,
            currency='USD',
            expiry_date=date(2026, 12, 31),
            latest_shipment_date=date(2026, 11, 30),
            port_of_loading='Shanghai',
            port_of_discharge='Los Angeles',
            issuing_bank='中国银行',
            advising_bank='Bank of America'
        )

        # 尝试创建相同信用证号应失败
        with pytest.raises(Exception):  # IntegrityError
            LetterOfCredit.objects.create(
                lc_no='LC2026003',
                contract=self.contract,
                transaction=self.transaction,
                applicant=self.buyer_company,
                beneficiary=self.seller_company,
                amount=10000.00,
                currency='USD',
                expiry_date=date(2026, 12, 31),
                latest_shipment_date=date(2026, 11, 30),
                port_of_loading='Shanghai',
                port_of_discharge='Los Angeles',
                issuing_bank='中国银行',
                advising_bank='Bank of America'
            )

    def test_letter_of_credit_contract_one_to_one(self):
        """测试合同与信用证一对一关系"""
        lc = LetterOfCredit.objects.create(
            lc_no='LC2026004',
            contract=self.contract,
            transaction=self.transaction,
            applicant=self.buyer_company,
            beneficiary=self.seller_company,
            amount=10000.00,
            currency='USD',
            expiry_date=date(2026, 12, 31),
            latest_shipment_date=date(2026, 11, 30),
            port_of_loading='Shanghai',
            port_of_discharge='Los Angeles',
            issuing_bank='中国银行',
            advising_bank='Bank of America'
        )

        assert self.contract.letter_of_credit == lc

    def test_letter_of_credit_documents_required_jsonfield(self):
        """测试单据要求 JSONField"""
        documents = [
            {'type': 'commercial_invoice', 'description': '商业发票', 'copies': 3},
            {'type': 'bill_of_lading', 'description': '提单', 'copies': 2},
            {'type': 'insurance_policy', 'description': '保险单', 'copies': 1}
        ]

        lc = LetterOfCredit.objects.create(
            lc_no='LC2026005',
            contract=self.contract,
            transaction=self.transaction,
            applicant=self.buyer_company,
            beneficiary=self.seller_company,
            amount=10000.00,
            currency='USD',
            expiry_date=date(2026, 12, 31),
            latest_shipment_date=date(2026, 11, 30),
            port_of_loading='Shanghai',
            port_of_discharge='Los Angeles',
            issuing_bank='中国银行',
            advising_bank='Bank of America',
            documents_required=documents
        )

        assert lc.documents_required == documents
        assert len(lc.documents_required) == 3
        assert lc.documents_required[0]['type'] == 'commercial_invoice'

    def test_letter_of_credit_timestamps(self):
        """测试信用证时间戳"""
        import django.utils.timezone as timezone

        lc = LetterOfCredit.objects.create(
            lc_no='LC2026006',
            contract=self.contract,
            transaction=self.transaction,
            applicant=self.buyer_company,
            beneficiary=self.seller_company,
            amount=10000.00,
            currency='USD',
            expiry_date=date(2026, 12, 31),
            latest_shipment_date=date(2026, 11, 30),
            port_of_loading='Shanghai',
            port_of_discharge='Los Angeles',
            issuing_bank='中国银行',
            advising_bank='Bank of America'
        )

        # 初始状态时间戳为空
        assert lc.issued_at is None
        assert lc.advised_at is None
        assert lc.submitted_at is None
        assert lc.negotiated_at is None
        assert lc.paid_at is None

        # 设置开证时间
        lc.status = 'issued'
        lc.issued_at = timezone.now()
        lc.issue_date = date(2026, 10, 1)
        lc.save()

        assert lc.issued_at is not None
        assert lc.issue_date == date(2026, 10, 1)

    def test_letter_of_credit_banks(self):
        """测试开证行和通知行"""
        lc = LetterOfCredit.objects.create(
            lc_no='LC2026007',
            contract=self.contract,
            transaction=self.transaction,
            applicant=self.buyer_company,
            beneficiary=self.seller_company,
            amount=10000.00,
            currency='USD',
            expiry_date=date(2026, 12, 31),
            latest_shipment_date=date(2026, 11, 30),
            port_of_loading='Shanghai',
            port_of_discharge='Los Angeles',
            issuing_bank='中国银行',
            advising_bank='Bank of America'
        )

        assert lc.issuing_bank == '中国银行'
        assert lc.advising_bank == 'Bank of America'

    def test_letter_of_credit_applicant_beneficiary(self):
        """测试申请人和受益人"""
        lc = LetterOfCredit.objects.create(
            lc_no='LC2026008',
            contract=self.contract,
            transaction=self.transaction,
            applicant=self.buyer_company,
            beneficiary=self.seller_company,
            amount=10000.00,
            currency='USD',
            expiry_date=date(2026, 12, 31),
            latest_shipment_date=date(2026, 11, 30),
            port_of_loading='Shanghai',
            port_of_discharge='Los Angeles',
            issuing_bank='中国银行',
            advising_bank='Bank of America'
        )

        assert lc.applicant == self.buyer_company
        assert lc.beneficiary == self.seller_company

    def test_letter_of_credit_ordering(self):
        """测试信用证按创建时间倒序排列"""
        import django.utils.timezone as timezone
        earlier_time = timezone.now() - timezone.timedelta(seconds=1)

        # 创建第二个合同用于第二个信用证
        transaction2 = Transaction.objects.create(
            buyer=self.buyer_company,
            seller=self.seller_company,
            product_id=2,
            quantity=2000,
            unit_price=15.00,
            status='pending_contract'
        )
        contract2 = Contract.objects.create(
            contract_no='SC002',
            transaction=transaction2,
            trade_term='CIF',
            payment_term='L/C',
            delivery_time=date(2026, 12, 31),
            port_of_loading='Shenzhen',
            port_of_discharge='Rotterdam',
            product_name='Test Product 2',
            quantity=2000,
            unit='pcs',
            unit_price=15.00,
            total_amount=30000.00,
            currency='USD'
        )

        lc1 = LetterOfCredit.objects.create(
            lc_no='LC2026009',
            contract=self.contract,
            transaction=self.transaction,
            applicant=self.buyer_company,
            beneficiary=self.seller_company,
            amount=10000.00,
            currency='USD',
            expiry_date=date(2026, 12, 31),
            latest_shipment_date=date(2026, 11, 30),
            port_of_loading='Shanghai',
            port_of_discharge='Los Angeles',
            issuing_bank='中国银行',
            advising_bank='Bank of America'
        )
        # 强制设置更早的创建时间
        lc1.created_at = earlier_time
        lc1.save()

        lc2 = LetterOfCredit.objects.create(
            lc_no='LC2026010',
            contract=contract2,
            transaction=transaction2,
            applicant=self.buyer_company,
            beneficiary=self.seller_company,
            amount=30000.00,
            currency='USD',
            expiry_date=date(2026, 12, 31),
            latest_shipment_date=date(2026, 11, 30),
            port_of_loading='Shenzhen',
            port_of_discharge='Rotterdam',
            issuing_bank='中国银行',
            advising_bank='Bank of America'
        )

        lcs = list(LetterOfCredit.objects.all())
        assert lcs[0] == lc2
        assert lcs[1] == lc1


class LcAmendmentModelTest(TestCase):
    """测试信用证修改记录模型"""

    def setUp(self):
        self.buyer = User.objects.create_user(username='lca_buyer', password='testpass', email='lca_buyer@test.com')
        self.seller = User.objects.create_user(username='lca_seller', password='testpass', email='lca_seller@test.com')
        self.buyer_company = create_company_for_user(self.buyer, '_LCA买方')
        self.seller_company = create_company_for_user(self.seller, '_LCA卖方')
        self.transaction = Transaction.objects.create(
            buyer=self.buyer_company,
            seller=self.seller_company,
            product_id=1,
            quantity=1000,
            unit_price=10.00,
            status='pending_contract'
        )
        self.contract = Contract.objects.create(
            contract_no='SC001',
            transaction=self.transaction,
            trade_term='FOB',
            payment_term='L/C',
            delivery_time=date(2026, 12, 31),
            port_of_loading='Shanghai',
            port_of_discharge='Los Angeles',
            product_name='Test Product',
            quantity=1000,
            unit='pcs',
            unit_price=10.00,
            total_amount=10000.00,
            currency='USD'
        )
        self.lc = LetterOfCredit.objects.create(
            lc_no='LC2026001',
            contract=self.contract,
            transaction=self.transaction,
            applicant=self.buyer_company,
            beneficiary=self.seller_company,
            amount=10000.00,
            currency='USD',
            expiry_date=date(2026, 12, 31),
            latest_shipment_date=date(2026, 11, 30),
            port_of_loading='Shanghai',
            port_of_discharge='Los Angeles',
            issuing_bank='中国银行',
            advising_bank='Bank of America'
        )

    def test_create_lc_amendment(self):
        """测试创建信用证修改记录"""
        amendment = LcAmendment.objects.create(
            lc=self.lc,
            amendment_no='LA001',
            initiated_by=self.buyer,
            content={'amount': 12000.00},
            reason='增加金额'
        )

        assert amendment.amendment_no == 'LA001'
        assert amendment.status == 'pending'
        assert amendment.get_status_display() == '待处理'
        assert amendment.content['amount'] == 12000.00
        assert str(amendment) == 'LC2026001 - LA001'
        assert self.lc.amendments.count() == 1

    def test_lc_amendment_status_choices(self):
        """测试修改状态枚举"""
        amendment = LcAmendment.objects.create(
            lc=self.lc,
            amendment_no='LA002',
            initiated_by=self.seller,
            content={'expiry_date': '2027-01-31'},
            reason='有效期延期'
        )

        # 测试 pending 状态
        amendment.status = 'pending'
        assert amendment.get_status_display() == '待处理'

        # 测试 approved 状态
        amendment.status = 'approved'
        amendment.save()
        assert amendment.get_status_display() == '已批准'

        # 测试 rejected 状态
        amendment.status = 'rejected'
        amendment.save()
        assert amendment.get_status_display() == '已拒绝'

    def test_lc_amendment_jsonfield_content(self):
        """测试 JSONField 修改内容存储"""
        amendment = LcAmendment.objects.create(
            lc=self.lc,
            amendment_no='LA003',
            initiated_by=self.buyer,
            content={
                'amount': 15000.00,
                'port_of_discharge': 'Long Beach',
                'documents_required': ['invoice', 'packing_list']
            },
            reason='多项修改'
        )

        assert amendment.content['amount'] == 15000.00
        assert amendment.content['port_of_discharge'] == 'Long Beach'
        assert len(amendment.content['documents_required']) == 2

    def test_lc_amendment_without_initiated_by(self):
        """测试无发起用户的修改记录"""
        amendment = LcAmendment.objects.create(
            lc=self.lc,
            amendment_no='LA004',
            initiated_by=None,
            content={'issuing_bank': '工商银行'},
            reason='开证行变更'
        )

        assert amendment.initiated_by is None
        assert amendment.amendment_no == 'LA004'

    def test_lc_amendment_processed_at(self):
        """测试处理时间字段"""
        import django.utils.timezone as timezone
        amendment = LcAmendment.objects.create(
            lc=self.lc,
            amendment_no='LA005',
            initiated_by=self.seller,
            content={'amount': 11000.00},
            reason='金额微调'
        )

        # 初始状态 processed_at 为空
        assert amendment.processed_at is None

        # 处理后设置时间
        amendment.status = 'approved'
        amendment.processed_at = timezone.now()
        amendment.save()

        assert amendment.processed_at is not None

    def test_lc_amendment_ordering(self):
        """测试修改记录按创建时间倒序排列"""
        import django.utils.timezone as timezone
        earlier_time = timezone.now() - timezone.timedelta(seconds=1)

        amendment1 = LcAmendment.objects.create(
            lc=self.lc,
            amendment_no='LA006',
            initiated_by=self.buyer,
            content={'field': 'value1'},
            reason='原因1'
        )
        # 强制设置更早的创建时间
        amendment1.created_at = earlier_time
        amendment1.save()

        amendment2 = LcAmendment.objects.create(
            lc=self.lc,
            amendment_no='LA007',
            initiated_by=self.seller,
            content={'field': 'value2'},
            reason='原因2'
        )

        amendments = list(self.lc.amendments.all())
        assert amendments[0] == amendment2
        assert amendments[1] == amendment1

    def test_lc_amendment_relationships(self):
        """测试修改记录与信用证的关系"""
        amendment = LcAmendment.objects.create(
            lc=self.lc,
            amendment_no='LA008',
            initiated_by=self.seller,
            content={'test': 'data'},
            reason='测试'
        )

        assert amendment.lc == self.lc
        assert self.lc.amendments.filter(amendment_no='LA008').exists()

    def test_lc_amendment_reason_field(self):
        """测试修改原因字段"""
        long_reason = '需要增加金额以适应价格上涨，同时调整目的港以满足新的物流需求'
        amendment = LcAmendment.objects.create(
            lc=self.lc,
            amendment_no='LA009',
            initiated_by=self.buyer,
            content={'amount': 12000.00},
            reason=long_reason
        )

        assert amendment.reason == long_reason

    def test_lc_amendment_unique_together_constraint(self):
        """测试信用证和修改编号的唯一约束"""
        # 创建第一个修改记录
        LcAmendment.objects.create(
            lc=self.lc,
            amendment_no='LA099',
            initiated_by=self.buyer,
            content={'amount': 12000.00},
            reason='增加金额'
        )
        # 尝试为同一信用证创建相同修改编号应失败
        with pytest.raises(Exception):  # IntegrityError
            LcAmendment.objects.create(
                lc=self.lc,
                amendment_no='LA099',
                initiated_by=self.seller,
                content={'amount': 13000.00},
                reason='再次增加金额'
            )

    def test_lc_amendment_different_lcs_same_amendment_no(self):
        """测试不同信用证可以有相同的修改编号"""
        # 创建第二个交易和合同
        transaction2 = Transaction.objects.create(
            buyer=self.buyer_company,
            seller=self.seller_company,
            product_id=2,
            quantity=500,
            unit_price=20.00,
            status='pending_contract'
        )
        contract2 = Contract.objects.create(
            contract_no='SC002',
            transaction=transaction2,
            trade_term='CIF',
            payment_term='L/C',
            delivery_time=date(2026, 12, 31),
            port_of_loading='Shenzhen',
            port_of_discharge='Rotterdam',
            product_name='Test Product 2',
            quantity=500,
            unit='pcs',
            unit_price=20.00,
            total_amount=10000.00,
            currency='USD'
        )
        lc2 = LetterOfCredit.objects.create(
            lc_no='LC2026002',
            contract=contract2,
            transaction=transaction2,
            applicant=self.buyer_company,
            beneficiary=self.seller_company,
            amount=10000.00,
            currency='USD',
            expiry_date=date(2026, 12, 31),
            latest_shipment_date=date(2026, 11, 30),
            port_of_loading='Shenzhen',
            port_of_discharge='Rotterdam',
            issuing_bank='中国银行',
            advising_bank='Bank of America'
        )

        # 两个信用证可以有相同的修改编号
        amendment1 = LcAmendment.objects.create(
            lc=self.lc,
            amendment_no='LA100',
            initiated_by=self.buyer,
            content={'amount': 12000.00},
            reason='增加金额'
        )
        amendment2 = LcAmendment.objects.create(
            lc=lc2,
            amendment_no='LA100',
            initiated_by=self.seller,
            content={'amount': 11000.00},
            reason='减少金额'
        )

        assert amendment1.amendment_no == amendment2.amendment_no
        assert amendment1.lc != amendment2.lc


class BankOperationModelTest(TestCase):
    """测试银行业务操作记录模型"""

    def setUp(self):
        self.buyer = User.objects.create_user(username='bo_buyer', password='testpass', email='bo_buyer@test.com')
        self.seller = User.objects.create_user(username='bo_seller', password='testpass', email='bo_seller@test.com')
        self.buyer_company = create_company_for_user(self.buyer, '_BO买方')
        self.seller_company = create_company_for_user(self.seller, '_BO卖方')
        self.transaction = Transaction.objects.create(
            buyer=self.buyer_company,
            seller=self.seller_company,
            product_id=1,
            quantity=1000,
            unit_price=10.00,
            status='pending_contract'
        )
        self.contract = Contract.objects.create(
            contract_no='SC001',
            transaction=self.transaction,
            trade_term='FOB',
            payment_term='L/C',
            delivery_time=date(2026, 12, 31),
            port_of_loading='Shanghai',
            port_of_discharge='Los Angeles',
            product_name='Test Product',
            quantity=1000,
            unit='pcs',
            unit_price=10.00,
            total_amount=10000.00,
            currency='USD'
        )
        self.lc = LetterOfCredit.objects.create(
            lc_no='LC2026001',
            contract=self.contract,
            transaction=self.transaction,
            applicant=self.buyer_company,
            beneficiary=self.seller_company,
            amount=10000.00,
            currency='USD',
            expiry_date=date(2026, 12, 31),
            latest_shipment_date=date(2026, 11, 30),
            port_of_loading='Shanghai',
            port_of_discharge='Los Angeles',
            issuing_bank='中国银行',
            advising_bank='Bank of America'
        )

    def test_create_bank_operation(self):
        """测试创建银行业务操作记录"""
        operation = BankOperation.objects.create(
            lc=self.lc,
            operation_type='issue',
            processed_by='system',
            notes='自动开证'
        )

        assert operation.operation_type == 'issue'
        assert operation.get_operation_type_display() == '开证'
        assert operation.processed_by == 'system'
        assert operation.notes == '自动开证'
        assert str(operation) == 'LC2026001 - 开证'

    def test_bank_operation_type_choices(self):
        """测试操作类型枚举"""
        operation_types = [
            ('issue', '开证'),
            ('advise', '通知'),
            ('negotiate', '议付'),
            ('pay', '付款'),
            ('amend', '修改'),
        ]

        for op_type, display_name in operation_types:
            operation = BankOperation.objects.create(
                lc=self.lc,
                operation_type=op_type,
                processed_by='system'
            )
            assert operation.get_operation_type_display() == display_name

    def test_bank_operation_with_operator(self):
        """测试带操作员的业务记录"""
        operation = BankOperation.objects.create(
            lc=self.lc,
            operation_type='advise',
            processed_by='bank',
            operator=self.buyer,
            notes='银行人工通知'
        )

        assert operation.operation_type == 'advise'
        assert operation.operator == self.buyer
        assert operation.notes == '银行人工通知'

    def test_bank_operation_jsonfield_result(self):
        """测试 JSONField 处理结果存储"""
        result_data = {
            'status': 'success',
            'reference_no': 'BANK2026001',
            'timestamp': '2026-05-22T10:30:00Z',
            'fees': {'amount': 100.00, 'currency': 'USD'}
        }

        operation = BankOperation.objects.create(
            lc=self.lc,
            operation_type='issue',
            processed_by='system',
            result=result_data
        )

        assert operation.result['status'] == 'success'
        assert operation.result['reference_no'] == 'BANK2026001'
        assert operation.result['fees']['amount'] == 100.00

    def test_bank_operation_without_operator(self):
        """测试无操作员的业务记录（系统操作）"""
        operation = BankOperation.objects.create(
            lc=self.lc,
            operation_type='issue',
            processed_by='system'
        )

        assert operation.operator is None
        assert operation.processed_by == 'system'

    def test_bank_operation_empty_notes(self):
        """测试空备注"""
        operation = BankOperation.objects.create(
            lc=self.lc,
            operation_type='negotiate',
            processed_by='bank',
            notes=''
        )

        assert operation.notes == ''

    def test_bank_operation_ordering(self):
        """测试业务记录按创建时间倒序排列"""
        import django.utils.timezone as timezone
        earlier_time = timezone.now() - timezone.timedelta(seconds=1)

        operation1 = BankOperation.objects.create(
            lc=self.lc,
            operation_type='issue',
            processed_by='system',
            notes='第一次操作'
        )
        # 强制设置更早的创建时间
        operation1.created_at = earlier_time
        operation1.save()

        operation2 = BankOperation.objects.create(
            lc=self.lc,
            operation_type='advise',
            processed_by='bank',
            notes='第二次操作'
        )

        operations = list(self.lc.bank_operations.all())
        assert operations[0] == operation2
        assert operations[1] == operation1

    def test_bank_operation_relationships(self):
        """测试业务记录与信用证的关系"""
        operation = BankOperation.objects.create(
            lc=self.lc,
            operation_type='pay',
            processed_by='system',
            notes='自动付款'
        )

        assert operation.lc == self.lc
        assert self.lc.bank_operations.filter(operation_type='pay').exists()

    def test_bank_operation_default_result(self):
        """测试默认空结果字典"""
        operation = BankOperation.objects.create(
            lc=self.lc,
            operation_type='amend',
            processed_by='system'
        )

        assert operation.result == {}
        assert isinstance(operation.result, dict)

    def test_bank_operation_processed_by_default(self):
        """测试 processed_by 默认值"""
        operation = BankOperation.objects.create(
            lc=self.lc,
            operation_type='issue'
        )

        assert operation.processed_by == 'system'
