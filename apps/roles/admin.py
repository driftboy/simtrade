from django.contrib import admin
from .models import Company, TradeRole, UserCompanyRole


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ['name', 'name_en', 'code', 'type', 'country', 'created_at']
    list_filter = ['type', 'country', 'created_at']
    search_fields = ['name', 'name_en', 'code', 'email']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(TradeRole)
class TradeRoleAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'is_enabled', 'is_system', 'sort_order', 'created_at']
    list_filter = ['is_enabled', 'is_system', 'created_at']
    search_fields = ['code', 'name', 'description']
    readonly_fields = ['created_at']


@admin.register(UserCompanyRole)
class UserCompanyRoleAdmin(admin.ModelAdmin):
    list_display = ['user', 'company', 'role', 'status', 'is_active', 'requested_at']
    list_filter = ['status', 'is_active', 'role', 'requested_at']
    search_fields = ['user__username', 'user__email', 'company__name', 'role__name']
    readonly_fields = ['requested_at', 'approved_at']
