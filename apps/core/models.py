"""
Core data models for SimTrade Platform.

This module contains the fundamental reference data models:
- Country: Country information with phone codes
- Port: Port/terminal information linked to countries
- Currency: Currency information with symbols
"""
from django.db import models


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
