"""
Core data models for SimTrade Platform.

This module contains the fundamental reference data models:
- Country: Country information with phone codes
- Port: Port/terminal information linked to countries
- Currency: Currency information with symbols
"""
from django.db import models


class ExchangeRate(models.Model):
    """汇率记录，来源于商务部"""

    currency = models.ForeignKey(
        'Currency',
        on_delete=models.CASCADE,
        related_name='exchange_rates',
        null=True,
        blank=True,
    )
    country_name = models.CharField('代表国家', max_length=100, blank=True)
    currency_name = models.CharField('货币名称', max_length=50)
    rate_to_usd = models.DecimalField('兑美元汇率', max_digits=14, decimal_places=4, help_text='X 单位外币 = 1 美元')
    rate_to_cny = models.DecimalField('兑人民币汇率', max_digits=14, decimal_places=4, null=True, blank=True, help_text='1 外币 = X 人民币')
    rate_date = models.DateField('汇率日期', db_index=True)
    source = models.CharField('数据来源', max_length=50, default='mofcom')
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'exchange_rates'
        verbose_name = '汇率'
        verbose_name_plural = '汇率'
        ordering = ['-rate_date']
        unique_together = [['currency_name', 'rate_date']]

    def __str__(self):
        return f'{self.country_name} {self.currency_name} {self.rate_to_usd} ({self.rate_date})'


class Country(models.Model):
    """
    Country model for storing country reference data.

    Attributes:
        code: ISO 3166-1 alpha-2 country code (e.g., 'CN', 'US', 'JP')
        name: Country name in Chinese
        name_en: Country name in English
        phone_code: International phone dialing code (e.g., '86', '1', '81')
        is_active: Soft delete flag - True if country is active
    """

    code = models.CharField(
        max_length=2,
        primary_key=True,
        help_text='ISO 3166-1 alpha-2 country code'
    )
    name = models.CharField(
        max_length=100,
        help_text='Country name in Chinese'
    )
    name_en = models.CharField(
        max_length=100,
        help_text='Country name in English'
    )
    phone_code = models.CharField(
        max_length=10,
        blank=True,
        default='',
        help_text='International phone dialing code'
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text='Whether this country is active'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'countries'
        verbose_name = 'Country'
        verbose_name_plural = 'Countries'
        ordering = ['name']

    def __str__(self):
        return self.name


class Port(models.Model):
    """
    Port model for storing port/terminal reference data.

    Attributes:
        code: UN/LOCODE (United Nations Code for Trade and Transport Locations)
        name: Port name in Chinese
        name_en: Port name in English
        country: Foreign key to Country model
        is_active: Soft delete flag - True if port is active
    """

    code = models.CharField(
        max_length=5,
        unique=True,
        db_index=True,
        help_text='UN/LOCODE port code'
    )
    name = models.CharField(
        max_length=100,
        help_text='Port name in Chinese'
    )
    name_en = models.CharField(
        max_length=100,
        help_text='Port name in English'
    )
    country = models.ForeignKey(
        Country,
        on_delete=models.PROTECT,
        related_name='ports',
        help_text='Country where this port is located'
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text='Whether this port is active'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ports'
        verbose_name = 'Port'
        verbose_name_plural = 'Ports'
        ordering = ['name']

    def __str__(self):
        return self.name


class Currency(models.Model):
    """
    Currency model for storing currency reference data.

    Attributes:
        code: ISO 4217 currency code (e.g., 'CNY', 'USD', 'EUR')
        name: Currency name in Chinese
        name_en: Currency name in English
        symbol: Currency symbol (e.g., '¥', '$', '€')
        is_active: Soft delete flag - True if currency is active
    """

    code = models.CharField(
        max_length=3,
        primary_key=True,
        help_text='ISO 4217 currency code'
    )
    name = models.CharField(
        max_length=50,
        help_text='Currency name in Chinese'
    )
    name_en = models.CharField(
        max_length=50,
        help_text='Currency name in English'
    )
    symbol = models.CharField(
        max_length=10,
        blank=True,
        default='',
        help_text='Currency symbol'
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text='Whether this currency is active'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'currencies'
        verbose_name = 'Currency'
        verbose_name_plural = 'Currencies'
        ordering = ['name']

    def __str__(self):
        return self.name


class TradeMode(models.Model):
    """监管方式代码表"""
    code = models.CharField('代码', max_length=4, primary_key=True)
    name = models.CharField('简称', max_length=50)
    full_name = models.CharField('全称', max_length=200, blank=True)
    is_active = models.BooleanField('是否启用', default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'trade_modes'
        verbose_name = '监管方式'
        verbose_name_plural = '监管方式'
        ordering = ['code']

    def __str__(self):
        return f'{self.code} {self.name}'


class TransportMode(models.Model):
    """运输方式代码表"""
    code = models.CharField('代码', max_length=2, primary_key=True)
    name = models.CharField('名称', max_length=50)
    is_active = models.BooleanField('是否启用', default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'transport_modes'
        verbose_name = '运输方式'
        verbose_name_plural = '运输方式'
        ordering = ['code']

    def __str__(self):
        return f'{self.code} {self.name}'


class PackageType(models.Model):
    """包装种类代码表"""
    code = models.CharField('代码', max_length=4, primary_key=True)
    name = models.CharField('名称', max_length=50)
    is_active = models.BooleanField('是否启用', default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'package_types'
        verbose_name = '包装种类'
        verbose_name_plural = '包装种类'
        ordering = ['code']

    def __str__(self):
        return f'{self.code} {self.name}'


class UnitOfMeasure(models.Model):
    """计量单位代码表"""
    code = models.CharField('代码', max_length=3, primary_key=True)
    name = models.CharField('名称', max_length=30)
    conv_ratio = models.DecimalField('换算比率', max_digits=10, decimal_places=4, default=1)
    conv_code = models.CharField('换算目标代码', max_length=3, blank=True)
    is_active = models.BooleanField('是否启用', default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'units_of_measure'
        verbose_name = '计量单位'
        verbose_name_plural = '计量单位'
        ordering = ['code']

    def __str__(self):
        return f'{self.code} {self.name}'


class CustomsDistrict(models.Model):
    """关区代码表"""
    code = models.CharField('代码', max_length=4, primary_key=True)
    name = models.CharField('名称', max_length=50)
    is_active = models.BooleanField('是否启用', default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'customs_districts'
        verbose_name = '关区'
        verbose_name_plural = '关区'
        ordering = ['code']

    def __str__(self):
        return f'{self.code} {self.name}'


class LevyMode(models.Model):
    """征减免税方式代码表"""
    code = models.CharField('代码', max_length=3, primary_key=True)
    name = models.CharField('名称', max_length=50)
    is_active = models.BooleanField('是否启用', default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'levy_modes'
        verbose_name = '征减免税方式'
        verbose_name_plural = '征减免税方式'
        ordering = ['code']

    def __str__(self):
        return f'{self.code} {self.name}'


class CustomsDoc(models.Model):
    """监管证件代码表"""
    code = models.CharField('代码', max_length=5, primary_key=True)
    name = models.CharField('名称', max_length=100)
    is_active = models.BooleanField('是否启用', default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'customs_docs'
        verbose_name = '监管证件'
        verbose_name_plural = '监管证件'
        ordering = ['code']

    def __str__(self):
        return f'{self.code} {self.name}'


class DomesticRegion(models.Model):
    """国内地区代码表"""
    code = models.CharField('代码', max_length=5, primary_key=True)
    name = models.CharField('名称', max_length=50)
    is_active = models.BooleanField('是否启用', default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'domestic_regions'
        verbose_name = '国内地区'
        verbose_name_plural = '国内地区'
        ordering = ['code']

    def __str__(self):
        return f'{self.code} {self.name}'
