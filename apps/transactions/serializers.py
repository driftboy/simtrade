from rest_framework import serializers
from apps.transactions.models import (
    Transaction, InquiryMessage, Contract, ContractSignature,
    ContractAmendment, LetterOfCredit, LcAmendment, BankOperation
)


class TransactionSerializer(serializers.ModelSerializer):
    """交易序列化器"""

    status_display = serializers.CharField(source='get_status_display', read_only=True)
    buyer_username = serializers.CharField(source='buyer.username', read_only=True)
    seller_username = serializers.CharField(source='seller.username', read_only=True)

    class Meta:
        model = Transaction
        fields = ['id', 'buyer', 'buyer_username', 'seller', 'seller_username',
                  'product_id', 'status', 'status_display', 'quantity',
                  'unit_price', 'currency', 'trade_term', 'port_of_loading',
                  'port_of_discharge', 'notes', 'created_at', 'updated_at']
        read_only_fields = ['id', 'buyer', 'created_at', 'updated_at']


class InquiryMessageSerializer(serializers.ModelSerializer):
    """磋商消息序列化器"""

    sender_username = serializers.CharField(source='sender.username', read_only=True)
    message_type_display = serializers.CharField(source='get_message_type_display', read_only=True)

    class Meta:
        model = InquiryMessage
        fields = ['id', 'transaction', 'sender', 'sender_username', 'sender_role',
                  'message_type', 'message_type_display', 'content',
                  'offered_quantity', 'offered_price', 'offered_trade_term',
                  'is_read', 'created_at']
        read_only_fields = ['id', 'transaction', 'sender', 'sender_username', 'sender_role', 'created_at']


class ContractAmendmentSerializer(serializers.ModelSerializer):
    """合同修改序列化器"""
    requested_by_name = serializers.CharField(source='requested_by.username', read_only=True)

    class Meta:
        model = ContractAmendment
        fields = ['id', 'amendment_no', 'requested_by', 'requested_by_name',
                  'change_content', 'reason', 'status', 'created_at', 'processed_at']
        read_only_fields = ['id', 'created_at', 'processed_at']


class ContractSignatureSerializer(serializers.ModelSerializer):
    """合同签字序列化器"""
    signer_name = serializers.CharField(required=True)

    class Meta:
        model = ContractSignature
        fields = ['id', 'contract', 'party', 'signer', 'signer_name',
                  'ip_address', 'signed_at']
        read_only_fields = ['id', 'signed_at']


class ContractSerializer(serializers.ModelSerializer):
    """合同序列化器"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    signatures = ContractSignatureSerializer(many=True, read_only=True)
    amendments = ContractAmendmentSerializer(many=True, read_only=True)

    class Meta:
        model = Contract
        fields = ['id', 'contract_no', 'transaction', 'status', 'status_display',
                  'trade_term', 'payment_term', 'delivery_time', 'port_of_loading',
                  'port_of_discharge', 'product_name', 'product_spec', 'quantity',
                  'unit', 'unit_price', 'total_amount', 'currency', 'packing',
                  'shipping_marks', 'remarks', 'buyer_signed_at', 'seller_signed_at',
                  'created_at', 'updated_at', 'effective_at', 'signatures', 'amendments']
        read_only_fields = ['id', 'created_at', 'updated_at', 'effective_at',
                            'buyer_signed_at', 'seller_signed_at']


class ContractSignSerializer(serializers.Serializer):
    """合同签字请求序列化器"""
    signer_name = serializers.CharField(max_length=100, required=True)


class LcAmendmentSerializer(serializers.ModelSerializer):
    """信用证修改序列化器"""
    initiated_by_name = serializers.CharField(source='initiated_by.username', read_only=True)

    class Meta:
        model = LcAmendment
        fields = ['id', 'amendment_no', 'initiated_by', 'initiated_by_name',
                  'content', 'reason', 'status', 'created_at', 'processed_at']
        read_only_fields = ['id', 'created_at', 'processed_at']


class BankOperationSerializer(serializers.ModelSerializer):
    """银行业务操作序列化器"""
    operation_type_display = serializers.CharField(source='get_operation_type_display', read_only=True)

    class Meta:
        model = BankOperation
        fields = ['id', 'lc', 'operation_type', 'operation_type_display',
                  'processed_by', 'operator', 'notes', 'result', 'created_at']
        read_only_fields = ['id', 'created_at']


class LetterOfCreditSerializer(serializers.ModelSerializer):
    """信用证序列化器"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    amendments = LcAmendmentSerializer(many=True, read_only=True)
    bank_operations = BankOperationSerializer(many=True, read_only=True)

    class Meta:
        model = LetterOfCredit
        fields = ['id', 'lc_no', 'contract', 'transaction', 'status', 'status_display',
                  'issuing_bank', 'advising_bank', 'applicant', 'beneficiary',
                  'amount', 'currency', 'issue_date', 'expiry_date',
                  'latest_shipment_date', 'port_of_loading', 'port_of_discharge',
                  'documents_required', 'issued_at', 'advised_at', 'submitted_at',
                  'negotiated_at', 'paid_at', 'created_at', 'updated_at',
                  'amendments', 'bank_operations']
        read_only_fields = ['id', 'created_at', 'updated_at', 'issued_at',
                            'advised_at', 'submitted_at', 'negotiated_at', 'paid_at']
