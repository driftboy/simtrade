from rest_framework import serializers
from apps.transactions.models import Transaction, InquiryMessage, Contract, ContractSignature


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


class ContractSerializer(serializers.ModelSerializer):
    """合同序列化器"""

    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Contract
        fields = ['id', 'contract_no', 'transaction', 'status', 'status_display',
                  'trade_term', 'payment_term', 'delivery_time',
                  'port_of_loading', 'port_of_discharge',
                  'product_name', 'product_spec', 'quantity', 'unit',
                  'unit_price', 'total_amount', 'currency',
                  'packing', 'shipping_marks', 'remarks',
                  'buyer_signed_at', 'seller_signed_at',
                  'created_at', 'updated_at', 'effective_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class ContractSignatureSerializer(serializers.ModelSerializer):
    """合同签字序列化器"""

    class Meta:
        model = ContractSignature
        fields = ['id', 'contract', 'party', 'signer', 'signer_name',
                  'signature_image', 'ip_address', 'signed_at']
        read_only_fields = ['id', 'signed_at']
