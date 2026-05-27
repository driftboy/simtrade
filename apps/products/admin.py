from django.contrib import admin
from apps.products.models import HSCode, Product, Catalog


@admin.register(HSCode)
class HSCodeAdmin(admin.ModelAdmin):
    """HS编码管理"""

    list_display = ['code', 'name', 'unit', 'vat_rate', 'rebate_rate', 'mfn_rate', 'export_rate', 'consumption_rate', 'chapter', 'is_expired']
    list_filter = ['chapter', 'is_expired']
    search_fields = ['code', 'name']
    ordering = ['code']
    readonly_fields = ['updated_at']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """商品管理"""

    list_display = ['code', 'name', 'category', 'unit', 'is_active', 'created_at']
    list_filter = ['category', 'is_active', 'created_at']
    search_fields = ['code', 'name', 'name_en', 'hs_code']
    ordering = ['code']


@admin.register(Catalog)
class CatalogAdmin(admin.ModelAdmin):
    """商品目录管理"""

    list_display = ['product', 'company', 'sale_price', 'currency', 'min_order', 'is_available']
    list_filter = ['company', 'is_available', 'created_at']
    search_fields = ['product__code', 'product__name']
