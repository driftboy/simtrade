from django.contrib import admin
from apps.core.models import (
    Country, Port, Currency, ExchangeRate,
    TradeMode, TransportMode, PackageType, UnitOfMeasure,
    CustomsDistrict, LevyMode, CustomsDoc, DomesticRegion,
)


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'name_en', 'phone_code', 'is_active']
    list_filter = ['is_active']
    search_fields = ['code', 'name', 'name_en']


@admin.register(Port)
class PortAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'name_en', 'country', 'is_active']
    list_filter = ['is_active', 'country']
    search_fields = ['code', 'name', 'name_en']


@admin.register(Currency)
class CurrencyAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'name_en', 'symbol', 'is_active']
    list_filter = ['is_active']
    search_fields = ['code', 'name', 'name_en']


@admin.register(ExchangeRate)
class ExchangeRateAdmin(admin.ModelAdmin):
    list_display = ['currency_name', 'country_name', 'rate_to_usd', 'rate_to_cny', 'rate_date', 'source']
    list_filter = ['source', 'rate_date']
    search_fields = ['currency_name', 'country_name']
    readonly_fields = ['created_at']


@admin.register(TradeMode)
class TradeModeAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'full_name', 'is_active']
    list_filter = ['is_active']
    search_fields = ['code', 'name']


@admin.register(TransportMode)
class TransportModeAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'is_active']
    list_filter = ['is_active']
    search_fields = ['code', 'name']


@admin.register(PackageType)
class PackageTypeAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'is_active']
    list_filter = ['is_active']
    search_fields = ['code', 'name']


@admin.register(UnitOfMeasure)
class UnitOfMeasureAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'conv_ratio', 'conv_code', 'is_active']
    list_filter = ['is_active']
    search_fields = ['code', 'name']


@admin.register(CustomsDistrict)
class CustomsDistrictAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'is_active']
    list_filter = ['is_active']
    search_fields = ['code', 'name']


@admin.register(LevyMode)
class LevyModeAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'is_active']
    list_filter = ['is_active']
    search_fields = ['code', 'name']


@admin.register(CustomsDoc)
class CustomsDocAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'is_active']
    list_filter = ['is_active']
    search_fields = ['code', 'name']


@admin.register(DomesticRegion)
class DomesticRegionAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'is_active']
    list_filter = ['is_active']
    search_fields = ['code', 'name']
