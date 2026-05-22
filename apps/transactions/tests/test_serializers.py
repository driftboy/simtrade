import pytest
from django.test import TestCase
from datetime import date
from apps.transactions.models import (
    Transaction, Contract, ContractSignature, ContractAmendment,
    LetterOfCredit, LcAmendment, BankOperation
)
from apps.transactions.serializers import (
    ContractSerializer, ContractSignatureSerializer, ContractAmendmentSerializer,
    ContractSignSerializer, LetterOfCreditSerializer,
    LcAmendmentSerializer, BankOperationSerializer
)
from apps.users.models import User


class ContractSerializerTest(TestCase):
    """测试合同序列化器"""

    def setUp(self):
        """每个测试方法前执行"""
        self.buyer = User.objects.create_user(username='buyer', password='testpass', email='buyer@test.com')
        self.seller = User.objects.create_user(username='seller', password='testpass', email='seller@test.com')
        self.transaction = Transaction.objects.create(
            buyer=self.buyer,
            seller=self.seller,
            product_id=1,
            quantity=1000,
            unit_price=10.00,
            status='pending_contract'
        )
        self.contract = Contract.objects.create(
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

    def test_contract_serializer_fields(self):
        """测试合同序列化器字段"""
        serializer = ContractSerializer(self.contract)
        data = serializer.data

        assert data['contract_no'] == 'CT202601001'
        assert data['status'] == 'draft'
        assert data['status_display'] == '草稿'
        assert data['trade_term'] == 'FOB'
        assert data['payment_term'] == 'T/T 30% in advance'
        assert data['total_amount'] == '10000.00'

    def test_contract_serializer_with_signatures(self):
        """测试包含签字记录的序列化"""
        ContractSignature.objects.create(
            contract=self.contract,
            party='buyer',
            signer=self.buyer,
            signer_name='张三'
        )
        ContractSignature.objects.create(
            contract=self.contract,
            party='seller',
            signer=self.seller,
            signer_name='李四'
        )

        serializer = ContractSerializer(self.contract)
        data = serializer.data

        assert 'signatures' in data
        assert len(data['signatures']) == 2
        assert data['signatures'][0]['signer_name'] == '张三'
        assert data['signatures'][1]['signer_name'] == '李四'

    def test_contract_serializer_with_amendments(self):
        """测试包含修改记录的序列化"""
        ContractAmendment.objects.create(
            contract=self.contract,
            amendment_no='A001',
            requested_by=self.seller,
            change_content={'unit_price': 12.00},
            reason='价格调整'
        )

        serializer = ContractSerializer(self.contract)
        data = serializer.data

        assert 'amendments' in data
        assert len(data['amendments']) == 1
        assert data['amendments'][0]['amendment_no'] == 'A001'
        assert data['amendments'][0]['change_content']['unit_price'] == 12.00


class ContractSignatureSerializerTest(TestCase):
    """测试合同签字序列化器"""

    def setUp(self):
        """每个测试方法前执行"""
        self.buyer = User.objects.create_user(username='sig_buyer', password='testpass', email='sbuyer@test.com')
        self.seller = User.objects.create_user(username='sig_seller', password='testpass', email='sseller@test.com')
        self.transaction = Transaction.objects.create(
            buyer=self.buyer,
            seller=self.seller,
            product_id=1,
            quantity=1000,
            unit_price=10.00
        )
        self.contract = Contract.objects.create(
            contract_no='CT202601002',
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

    def test_contract_signature_serializer_fields(self):
        """测试签字序列化器字段"""
        signature = ContractSignature.objects.create(
            contract=self.contract,
            party='buyer',
            signer=self.buyer,
            signer_name='张三'
        )

        serializer = ContractSignatureSerializer(signature)
        data = serializer.data

        assert data['party'] == 'buyer'
        assert data['signer_name'] == '张三'
        assert 'signed_at' in data

    def test_contract_signature_serializer_signer_name_required(self):
        """测试签字人姓名必填"""
        serializer = ContractSignatureSerializer(data={
            'contract': self.contract.id,
            'party': 'buyer',
            'signer': self.buyer.id
        })

        assert not serializer.is_valid()
        assert 'signer_name' in serializer.errors

    def test_contract_signature_serializer_valid_data(self):
        """测试有效数据序列化"""
        data = {
            'contract': self.contract.id,
            'party': 'seller',
            'signer': self.seller.id,
            'signer_name': '李四'
        }

        serializer = ContractSignatureSerializer(data=data)
        assert serializer.is_valid()
        assert serializer.errors == {}


class ContractAmendmentSerializerTest(TestCase):
    """测试合同修改序列化器"""

    def setUp(self):
        """每个测试方法前执行"""
        self.buyer = User.objects.create_user(username='amend_buyer', password='testpass', email='abuyer@test.com')
        self.seller = User.objects.create_user(username='amend_seller', password='testpass', email='aseller@test.com')
        self.transaction = Transaction.objects.create(
            buyer=self.buyer,
            seller=self.seller,
            product_id=1,
            quantity=1000,
            unit_price=10.00
        )
        self.contract = Contract.objects.create(
            contract_no='CT202601003',
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

    def test_contract_amendment_serializer_fields(self):
        """测试修改记录序列化器字段"""
        amendment = ContractAmendment.objects.create(
            contract=self.contract,
            amendment_no='A001',
            requested_by=self.seller,
            change_content={'unit_price': 12.00},
            reason='价格调整'
        )

        serializer = ContractAmendmentSerializer(amendment)
        data = serializer.data

        assert data['amendment_no'] == 'A001'
        assert data['requested_by_name'] == 'amend_seller'
        assert data['change_content']['unit_price'] == 12.00
        assert data['reason'] == '价格调整'
        assert data['status'] == 'pending'
        assert 'created_at' in data

    def test_contract_amendment_serializer_requested_by_name(self):
        """测试请求人名字段"""
        amendment = ContractAmendment.objects.create(
            contract=self.contract,
            amendment_no='A002',
            requested_by=self.buyer,
            change_content={'quantity': 1500},
            reason='数量增加'
        )

        serializer = ContractAmendmentSerializer(amendment)
        data = serializer.data

        assert data['requested_by_name'] == 'amend_buyer'


class ContractSignSerializerTest(TestCase):
    """测试合同签字请求序列化器"""

    def test_contract_sign_serializer_valid(self):
        """测试有效签字请求数据"""
        data = {'signer_name': '张三'}
        serializer = ContractSignSerializer(data=data)

        assert serializer.is_valid()
        assert serializer.validated_data['signer_name'] == '张三'

    def test_contract_sign_serializer_missing_name(self):
        """测试缺少签字人姓名"""
        serializer = ContractSignSerializer(data={})

        assert not serializer.is_valid()
        assert 'signer_name' in serializer.errors

    def test_contract_sign_serializer_max_length(self):
        """测试签字人姓名最大长度"""
        data = {'signer_name': 'x' * 101}
        serializer = ContractSignSerializer(data=data)

        assert not serializer.is_valid()
        assert 'signer_name' in serializer.errors


class LetterOfCreditSerializerTest(TestCase):
    """测试信用证序列化器"""

    def setUp(self):
        """每个测试方法前执行"""
        self.buyer = User.objects.create_user(username='lc_buyer', password='testpass', email='lc_buyer@test.com')
        self.seller = User.objects.create_user(username='lc_seller', password='testpass', email='lc_seller@test.com')
        self.transaction = Transaction.objects.create(
            buyer=self.buyer,
            seller=self.seller,
            product_id=1,
            quantity=1000,
            unit_price=10.00
        )
        self.contract = Contract.objects.create(
            contract_no='CT202601004',
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
            applicant=self.buyer,
            beneficiary=self.seller,
            amount=10000.00,
            currency='USD',
            expiry_date=date(2026, 12, 31),
            latest_shipment_date=date(2026, 11, 30),
            port_of_loading='Shanghai',
            port_of_discharge='Los Angeles',
            issuing_bank='中国银行',
            advising_bank='Bank of America'
        )

    def test_letter_of_credit_serializer_fields(self):
        """测试信用证序列化器字段"""
        serializer = LetterOfCreditSerializer(self.lc)
        data = serializer.data

        assert data['lc_no'] == 'LC2026001'
        assert data['status'] == 'draft'
        assert data['status_display'] == '草稿'
        assert data['amount'] == '10000.00'
        assert data['issuing_bank'] == '中国银行'
        assert data['advising_bank'] == 'Bank of America'

    def test_letter_of_credit_serializer_with_amendments(self):
        """测试包含修改记录的序列化"""
        LcAmendment.objects.create(
            lc=self.lc,
            amendment_no='LA001',
            initiated_by=self.buyer,
            content={'amount': 12000.00},
            reason='增加金额'
        )

        serializer = LetterOfCreditSerializer(self.lc)
        data = serializer.data

        assert 'amendments' in data
        assert len(data['amendments']) == 1
        assert data['amendments'][0]['amendment_no'] == 'LA001'

    def test_letter_of_credit_serializer_with_bank_operations(self):
        """测试包含银行业务操作的序列化"""
        BankOperation.objects.create(
            lc=self.lc,
            operation_type='issue',
            processed_by='system',
            notes='自动开证'
        )

        serializer = LetterOfCreditSerializer(self.lc)
        data = serializer.data

        assert 'bank_operations' in data
        assert len(data['bank_operations']) == 1
        assert data['bank_operations'][0]['operation_type'] == 'issue'
        assert data['bank_operations'][0]['operation_type_display'] == '开证'


class LcAmendmentSerializerTest(TestCase):
    """测试信用证修改序列化器"""

    def setUp(self):
        """每个测试方法前执行"""
        self.buyer = User.objects.create_user(username='lca_buyer', password='testpass', email='lca_buyer@test.com')
        self.seller = User.objects.create_user(username='lca_seller', password='testpass', email='lca_seller@test.com')
        self.transaction = Transaction.objects.create(
            buyer=self.buyer,
            seller=self.seller,
            product_id=1,
            quantity=1000,
            unit_price=10.00
        )
        self.contract = Contract.objects.create(
            contract_no='CT202601005',
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
            lc_no='LC2026002',
            contract=self.contract,
            transaction=self.transaction,
            applicant=self.buyer,
            beneficiary=self.seller,
            amount=10000.00,
            currency='USD',
            expiry_date=date(2026, 12, 31),
            latest_shipment_date=date(2026, 11, 30),
            port_of_loading='Shanghai',
            port_of_discharge='Los Angeles',
            issuing_bank='中国银行',
            advising_bank='Bank of America'
        )

    def test_lc_amendment_serializer_fields(self):
        """测试信用证修改序列化器字段"""
        amendment = LcAmendment.objects.create(
            lc=self.lc,
            amendment_no='LA001',
            initiated_by=self.buyer,
            content={'amount': 12000.00},
            reason='增加金额'
        )

        serializer = LcAmendmentSerializer(amendment)
        data = serializer.data

        assert data['amendment_no'] == 'LA001'
        assert data['initiated_by_name'] == 'lca_buyer'
        assert data['content']['amount'] == 12000.00
        assert data['reason'] == '增加金额'
        assert data['status'] == 'pending'

    def test_lc_amendment_serializer_initiated_by_name(self):
        """测试发起人名字段"""
        amendment = LcAmendment.objects.create(
            lc=self.lc,
            amendment_no='LA002',
            initiated_by=self.seller,
            content={'expiry_date': '2027-01-31'},
            reason='有效期延期'
        )

        serializer = LcAmendmentSerializer(amendment)
        data = serializer.data

        assert data['initiated_by_name'] == 'lca_seller'


class BankOperationSerializerTest(TestCase):
    """测试银行业务操作序列化器"""

    def setUp(self):
        """每个测试方法前执行"""
        self.buyer = User.objects.create_user(username='bo_buyer', password='testpass', email='bo_buyer@test.com')
        self.seller = User.objects.create_user(username='bo_seller', password='testpass', email='bo_seller@test.com')
        self.transaction = Transaction.objects.create(
            buyer=self.buyer,
            seller=self.seller,
            product_id=1,
            quantity=1000,
            unit_price=10.00
        )
        self.contract = Contract.objects.create(
            contract_no='CT202601006',
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
            lc_no='LC2026003',
            contract=self.contract,
            transaction=self.transaction,
            applicant=self.buyer,
            beneficiary=self.seller,
            amount=10000.00,
            currency='USD',
            expiry_date=date(2026, 12, 31),
            latest_shipment_date=date(2026, 11, 30),
            port_of_loading='Shanghai',
            port_of_discharge='Los Angeles',
            issuing_bank='中国银行',
            advising_bank='Bank of America'
        )

    def test_bank_operation_serializer_fields(self):
        """测试银行业务操作序列化器字段"""
        operation = BankOperation.objects.create(
            lc=self.lc,
            operation_type='issue',
            processed_by='system',
            notes='自动开证'
        )

        serializer = BankOperationSerializer(operation)
        data = serializer.data

        assert data['operation_type'] == 'issue'
        assert data['operation_type_display'] == '开证'
        assert data['processed_by'] == 'system'
        assert data['notes'] == '自动开证'

    def test_bank_operation_serializer_all_operation_types(self):
        """测试所有操作类型"""
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
            serializer = BankOperationSerializer(operation)
            data = serializer.data

            assert data['operation_type'] == op_type
            assert data['operation_type_display'] == display_name

    def test_bank_operation_serializer_with_operator(self):
        """测试包含操作员的序列化"""
        operation = BankOperation.objects.create(
            lc=self.lc,
            operation_type='advise',
            processed_by='bank',
            operator=self.buyer,
            notes='银行人工通知'
        )

        serializer = BankOperationSerializer(operation)
        data = serializer.data

        assert data['operation_type'] == 'advise'
        assert data['processed_by'] == 'bank'
        assert data['notes'] == '银行人工通知'
