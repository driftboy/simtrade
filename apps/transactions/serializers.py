from rest_framework import serializers
from apps.transactions.models import (
    Transaction, InquiryMessage, Contract, ContractSignature,
    ContractAmendment, LetterOfCredit, LcAmendment, BankOperation,
    PurchaseOrder, Shipment, InsurancePolicy,
    CustomsDeclaration, InspectionApplication,
    ForexSettlement, TaxRefundApplication
)


class TransactionSerializer(serializers.ModelSerializer):
    """交易序列化器"""

    status_display = serializers.CharField(source='get_status_display', read_only=True)
    buyer_name = serializers.CharField(source='buyer.name', read_only=True)
    buyer_company_name = serializers.CharField(source='buyer.name', read_only=True)
    buyer_company_code = serializers.CharField(source='buyer.code', read_only=True)
    seller_name = serializers.CharField(source='seller.name', read_only=True)
    seller_company_name = serializers.CharField(source='seller.name', read_only=True)
    seller_company_code = serializers.CharField(source='seller.code', read_only=True)

    class Meta:
        model = Transaction
        fields = ['id', 'buyer', 'buyer_name', 'buyer_company_name', 'buyer_company_code',
                  'seller', 'seller_name', 'seller_company_name', 'seller_company_code',
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
    applicant_company_name = serializers.CharField(source='applicant.name', read_only=True)
    beneficiary_company_name = serializers.CharField(source='beneficiary.name', read_only=True)
    amendments = LcAmendmentSerializer(many=True, read_only=True)
    bank_operations = BankOperationSerializer(many=True, read_only=True)

    class Meta:
        model = LetterOfCredit
        fields = ['id', 'lc_no', 'contract', 'transaction', 'status', 'status_display',
                  'issuing_bank', 'advising_bank', 'applicant', 'applicant_company_name',
                  'beneficiary', 'beneficiary_company_name',
                  'amount', 'currency', 'issue_date', 'expiry_date',
                  'latest_shipment_date', 'port_of_loading', 'port_of_discharge',
                  'documents_required', 'issued_at', 'advised_at', 'submitted_at',
                  'negotiated_at', 'paid_at', 'created_at', 'updated_at',
                  'amendments', 'bank_operations']
        read_only_fields = ['id', 'created_at', 'updated_at', 'issued_at',
                            'advised_at', 'submitted_at', 'negotiated_at', 'paid_at']


class PurchaseOrderSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    buyer_name = serializers.CharField(source='buyer.name', read_only=True)
    seller_name = serializers.CharField(source='seller.name', read_only=True)
    transaction_id = serializers.IntegerField(source='transaction.id', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True, default='')

    class Meta:
        model = PurchaseOrder
        fields = [
            'id', 'order_no', 'transaction', 'transaction_id',
            'buyer', 'buyer_name', 'seller', 'seller_name',
            'product_name', 'product_code', 'quantity', 'unit',
            'unit_price', 'currency', 'total_amount',
            'delivery_date', 'delivery_address',
            'status', 'status_display', 'notes',
            'created_by', 'created_by_name',
            'confirmed_at', 'shipped_at', 'invoiced_at', 'completed_at',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'order_no', 'created_by', 'total_amount',
            'confirmed_at', 'shipped_at', 'invoiced_at', 'completed_at',
            'created_at', 'updated_at'
        ]


class CreatePurchaseOrderSerializer(serializers.Serializer):
    transaction_id = serializers.IntegerField(min_value=1)
    seller_id = serializers.IntegerField(min_value=1)
    product_name = serializers.CharField(max_length=200)
    product_code = serializers.CharField(required=False, allow_blank=True, max_length=50)
    quantity = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0.01)
    unit = serializers.CharField(max_length=20, default='件')
    unit_price = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0.01)
    currency = serializers.CharField(max_length=10, default='CNY')
    delivery_date = serializers.DateField(required=False, allow_null=True)
    delivery_address = serializers.CharField(required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)


class ShipmentSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    shipper_name = serializers.CharField(source='shipper.name', read_only=True)
    carrier_name = serializers.CharField(source='carrier.name', read_only=True)
    contract_no = serializers.CharField(source='contract.contract_no', read_only=True)

    class Meta:
        model = Shipment
        fields = [
            'id', 'shipment_no', 'contract', 'contract_no',
            'shipper', 'shipper_name', 'carrier', 'carrier_name',
            'booking_no', 'bl_no', 'vessel_name',
            'port_of_loading', 'port_of_discharge',
            'etd', 'eta', 'container_no',
            'freight_amount', 'freight_currency',
            'status', 'status_display', 'notes',
            'created_by', 'booked_at', 'loaded_at', 'shipped_at', 'arrived_at',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'shipment_no', 'created_by',
            'booked_at', 'loaded_at', 'shipped_at', 'arrived_at',
            'created_at', 'updated_at'
        ]


class CreateShipmentSerializer(serializers.Serializer):
    contract_id = serializers.IntegerField(min_value=1)
    carrier_id = serializers.IntegerField(min_value=1)
    port_of_loading = serializers.CharField(max_length=100)
    port_of_discharge = serializers.CharField(max_length=100)
    notes = serializers.CharField(required=False, allow_blank=True)


class InsurancePolicySerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    coverage_type_display = serializers.CharField(source='get_coverage_type_display', read_only=True)
    insured_name = serializers.CharField(source='insured.name', read_only=True)
    insurer_name = serializers.CharField(source='insurer.name', read_only=True)
    contract_no = serializers.CharField(source='contract.contract_no', read_only=True)

    class Meta:
        model = InsurancePolicy
        fields = [
            'id', 'policy_no', 'contract', 'contract_no', 'shipment',
            'insured', 'insured_name', 'insurer', 'insurer_name',
            'cargo_description', 'insured_amount',
            'premium', 'premium_currency', 'coverage_type', 'coverage_type_display',
            'status', 'status_display', 'notes',
            'created_by', 'underwritten_at', 'issued_at',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'policy_no', 'created_by', 'insured_amount', 'premium',
            'underwritten_at', 'issued_at',
            'created_at', 'updated_at'
        ]


class CreateInsurancePolicySerializer(serializers.Serializer):
    contract_id = serializers.IntegerField(min_value=1)
    insurer_id = serializers.IntegerField(min_value=1)
    coverage_type = serializers.ChoiceField(
        choices=['fpa', 'wa', 'all_risk'], default='all_risk'
    )
    cargo_description = serializers.CharField()
    notes = serializers.CharField(required=False, allow_blank=True)


class CustomsDeclarationSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    declarant_name = serializers.CharField(source='declarant.name', read_only=True)
    customs_office_name = serializers.CharField(source='customs_office.name', read_only=True)
    shipment_no = serializers.CharField(source='shipment.shipment_no', read_only=True)

    class Meta:
        model = CustomsDeclaration
        fields = [
            'id', 'declaration_no', 'shipment', 'shipment_no',
            'declarant', 'declarant_name', 'customs_office', 'customs_office_name',
            'hs_code', 'goods_name', 'quantity', 'unit_value', 'total_value', 'currency',
            'duty_rate', 'duty_amount', 'vat_rate', 'vat_amount',
            'status', 'status_display', 'notes',
            'created_by', 'reviewed_at', 'assessed_at', 'cleared_at', 'rejected_at',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'declaration_no', 'created_by',
            'duty_rate', 'duty_amount', 'vat_rate', 'vat_amount',
            'reviewed_at', 'assessed_at', 'cleared_at', 'rejected_at',
            'created_at', 'updated_at'
        ]


class CreateCustomsDeclarationSerializer(serializers.Serializer):
    shipment_id = serializers.IntegerField(min_value=1)
    customs_office_id = serializers.IntegerField(min_value=1)
    hs_code = serializers.CharField(max_length=20)
    goods_name = serializers.CharField(max_length=200)
    quantity = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0.01)
    unit_value = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0.01)
    total_value = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=0.01)
    currency = serializers.CharField(max_length=10, default='USD')
    notes = serializers.CharField(required=False, allow_blank=True)


class InspectionApplicationSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    inspection_type_display = serializers.CharField(source='get_inspection_type_display', read_only=True)
    applicant_name = serializers.CharField(source='applicant.name', read_only=True)
    inspector_name = serializers.CharField(source='inspector.name', read_only=True)
    shipment_no = serializers.CharField(source='shipment.shipment_no', read_only=True)

    class Meta:
        model = InspectionApplication
        fields = [
            'id', 'application_no', 'shipment', 'shipment_no',
            'applicant', 'applicant_name', 'inspector', 'inspector_name',
            'product_name', 'product_spec', 'quantity', 'goods_value',
            'inspection_type', 'inspection_type_display',
            'fee', 'fee_currency',
            'certificate_no', 'origin_certificate_no',
            'status', 'status_display', 'notes',
            'created_by', 'inspecting_at', 'passed_at', 'certified_at', 'failed_at',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'application_no', 'created_by', 'fee',
            'certificate_no', 'origin_certificate_no',
            'inspecting_at', 'passed_at', 'certified_at', 'failed_at',
            'created_at', 'updated_at'
        ]


class CreateInspectionApplicationSerializer(serializers.Serializer):
    shipment_id = serializers.IntegerField(min_value=1)
    inspector_id = serializers.IntegerField(min_value=1)
    inspection_type = serializers.ChoiceField(
        choices=['legal', 'general'], default='legal'
    )
    product_name = serializers.CharField(max_length=200)
    product_spec = serializers.CharField(max_length=200, required=False, allow_blank=True)
    quantity = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0.01)
    goods_value = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=0.01)
    notes = serializers.CharField(required=False, allow_blank=True)


class ForexSettlementSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    applicant_name = serializers.CharField(source='applicant.name', read_only=True)
    forex_bureau_name = serializers.CharField(source='forex_bureau.name', read_only=True)
    declaration_no = serializers.CharField(source='customs_declaration.declaration_no', read_only=True)

    class Meta:
        model = ForexSettlement
        fields = [
            'id', 'settlement_no', 'customs_declaration', 'declaration_no',
            'applicant', 'applicant_name', 'forex_bureau', 'forex_bureau_name',
            'foreign_currency', 'foreign_amount',
            'reference_rate', 'reference_cny_amount',
            'settlement_rate', 'settlement_cny_amount',
            'status', 'status_display', 'notes',
            'created_by', 'verified_at', 'settled_at', 'rejected_at',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'settlement_no', 'created_by',
            'reference_rate', 'reference_cny_amount',
            'settlement_rate', 'settlement_cny_amount',
            'verified_at', 'settled_at', 'rejected_at',
            'created_at', 'updated_at'
        ]


class CreateForexSettlementSerializer(serializers.Serializer):
    declaration_id = serializers.IntegerField(min_value=1)
    forex_bureau_id = serializers.IntegerField(min_value=1)
    notes = serializers.CharField(required=False, allow_blank=True)


class TaxRefundApplicationSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    applicant_name = serializers.CharField(source='applicant.name', read_only=True)
    tax_bureau_name = serializers.CharField(source='tax_bureau.name', read_only=True)
    declaration_no = serializers.CharField(source='customs_declaration.declaration_no', read_only=True)

    class Meta:
        model = TaxRefundApplication
        fields = [
            'id', 'application_no', 'customs_declaration', 'declaration_no',
            'applicant', 'applicant_name', 'tax_bureau', 'tax_bureau_name',
            'hs_code', 'total_value',
            'refund_rate', 'refund_amount', 'refund_currency',
            'status', 'status_display', 'notes',
            'created_by', 'reviewing_at', 'approved_at', 'refunded_at', 'rejected_at',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'application_no', 'created_by',
            'hs_code', 'total_value', 'refund_rate', 'refund_amount', 'refund_currency',
            'reviewing_at', 'approved_at', 'refunded_at', 'rejected_at',
            'created_at', 'updated_at'
        ]


class CreateTaxRefundApplicationSerializer(serializers.Serializer):
    declaration_id = serializers.IntegerField(min_value=1)
    tax_bureau_id = serializers.IntegerField(min_value=1)
    notes = serializers.CharField(required=False, allow_blank=True)
