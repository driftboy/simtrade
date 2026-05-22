import pytest
from django.test import TestCase
from django.core.exceptions import ValidationError
from datetime import date, datetime
from apps.transactions.models import Transaction, InquiryMessage, Contract, ContractSignature, TransactionLog, ContractAmendment
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


class ContractModelTest(TestCase):
    """测试合同模型"""

    def setUp(self):
        self.buyer = User.objects.create_user(username='contract_buyer', password='testpass', email='cbuyer@test.com')
        self.seller = User.objects.create_user(username='contract_seller', password='testpass', email='cseller@test.com')
        self.transaction = Transaction.objects.create(
            buyer=self.buyer,
            seller=self.seller,
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
        self.transaction = Transaction.objects.create(
            buyer=self.buyer,
            seller=self.seller,
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
        self.transaction = Transaction.objects.create(
            buyer=self.buyer,
            seller=self.seller,
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
        self.transaction = Transaction.objects.create(
            buyer=self.buyer,
            seller=self.seller,
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
        self.transaction = Transaction.objects.create(
            buyer=self.buyer,
            seller=self.seller,
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
            buyer=self.buyer,
            seller=self.seller,
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
