from django.contrib import admin
from apps.transactions.models import (
    Transaction, InquiryMessage, Contract,
    ContractSignature, TransactionLog
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
