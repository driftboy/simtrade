from django.contrib import admin
from apps.transactions.models import (
    Transaction, InquiryMessage, Contract,
    ContractSignature, TransactionLog, ContractAmendment,
    LetterOfCredit, LcAmendment, BankOperation,
    PurchaseOrder, Shipment, InsurancePolicy
)


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    """交易管理"""

    list_display = ['id', 'buyer', 'seller', 'status', 'quantity', 'unit_price', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['buyer__username', 'seller__username']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(InquiryMessage)
class InquiryMessageAdmin(admin.ModelAdmin):
    """磋商消息管理"""

    list_display = ['transaction', 'sender', 'message_type', 'is_read', 'created_at']
    list_filter = ['message_type', 'is_read', 'created_at']
    search_fields = ['content']


@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    """合同管理"""

    list_display = ['contract_no', 'transaction', 'status', 'total_amount', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['contract_no', 'product_name']


@admin.register(ContractSignature)
class ContractSignatureAdmin(admin.ModelAdmin):
    """合同签字管理"""

    list_display = ['contract', 'party', 'signer_name', 'signed_at']
    list_filter = ['party', 'signed_at']


@admin.register(TransactionLog)
class TransactionLogAdmin(admin.ModelAdmin):
    """交易日志管理"""

    list_display = ['transaction', 'user', 'action', 'created_at']
    list_filter = ['action', 'created_at']
    readonly_fields = ['transaction', 'user', 'action', 'details', 'created_at']


@admin.register(ContractAmendment)
class ContractAmendmentAdmin(admin.ModelAdmin):
    """合同修改记录管理"""

    list_display = ['contract', 'amendment_no', 'requested_by', 'status', 'created_at', 'processed_at']
    list_filter = ['status', 'created_at']
    search_fields = ['contract__contract_no', 'amendment_no', 'reason']
    readonly_fields = ['created_at']


@admin.register(LetterOfCredit)
class LetterOfCreditAdmin(admin.ModelAdmin):
    """信用证管理"""

    list_display = ['lc_no', 'contract', 'status', 'amount', 'currency', 'issue_date', 'expiry_date']
    list_filter = ['status', 'currency', 'issue_date', 'created_at']
    search_fields = ['lc_no', 'issuing_bank', 'advising_bank']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(LcAmendment)
class LcAmendmentAdmin(admin.ModelAdmin):
    """信用证修改记录管理"""

    list_display = ['lc', 'amendment_no', 'initiated_by', 'status', 'created_at', 'processed_at']
    list_filter = ['status', 'created_at']
    search_fields = ['lc__lc_no', 'amendment_no', 'reason']
    readonly_fields = ['created_at']


@admin.register(BankOperation)
class BankOperationAdmin(admin.ModelAdmin):
    """银行业务操作记录管理"""

    list_display = ['lc', 'operation_type', 'processed_by', 'created_at']
    list_filter = ['operation_type', 'processed_by', 'created_at']
    search_fields = ['lc__lc_no', 'notes']
    readonly_fields = ['created_at']


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = [
        'order_no', 'buyer', 'seller', 'product_name',
        'total_amount', 'status', 'created_at'
    ]
    list_filter = ['status', 'currency', 'created_at']
    search_fields = ['order_no', 'product_name', 'buyer__name', 'seller__name']
    readonly_fields = [
        'created_at', 'updated_at', 'confirmed_at',
        'shipped_at', 'invoiced_at', 'completed_at'
    ]


@admin.register(Shipment)
class ShipmentAdmin(admin.ModelAdmin):
    list_display = [
        'shipment_no', 'shipper', 'carrier', 'vessel_name',
        'port_of_loading', 'port_of_discharge',
        'freight_amount', 'status', 'created_at'
    ]
    list_filter = ['status', 'freight_currency', 'created_at']
    search_fields = ['shipment_no', 'booking_no', 'bl_no', 'vessel_name']
    readonly_fields = [
        'created_at', 'updated_at', 'booked_at',
        'loaded_at', 'shipped_at', 'arrived_at'
    ]


@admin.register(InsurancePolicy)
class InsurancePolicyAdmin(admin.ModelAdmin):
    list_display = [
        'policy_no', 'insured', 'insurer',
        'insured_amount', 'premium', 'coverage_type',
        'status', 'created_at'
    ]
    list_filter = ['status', 'coverage_type', 'created_at']
    search_fields = ['policy_no', 'cargo_description']
    readonly_fields = [
        'created_at', 'updated_at',
        'underwritten_at', 'issued_at'
    ]
