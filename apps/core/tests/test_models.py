"""
Tests for Country, Port, and Currency models.
"""
import pytest
from django.db import IntegrityError
from django.core.exceptions import ValidationError

from apps.core.models import Country, Port, Currency


class TestCountryModel:
    """Test cases for Country model."""

    def test_create_country(self, db):
        """Test creating a country with all fields."""
        country = Country.objects.create(
            code='CN',
            name='中国',
            name_en='China',
            phone_code='86',
            is_active=True
        )
        assert country.code == 'CN'
        assert country.name == '中国'
        assert country.name_en == 'China'
        assert country.phone_code == '86'
        assert country.is_active is True

    def test_create_country_minimal(self, db):
        """Test creating a country with minimal required fields."""
        country = Country.objects.create(
            code='US',
            name='美国',
            name_en='United States'
        )
        assert country.code == 'US'
        assert country.name == '美国'
        assert country.name_en == 'United States'
        assert country.is_active is True  # Default value

    def test_country_code_unique(self, db):
        """Test that country code is unique."""
        Country.objects.create(
            code='CN',
            name='中国',
            name_en='China'
        )
        with pytest.raises(IntegrityError):
            Country.objects.create(
                code='CN',  # Duplicate code
                name='中华',
                name_en='China PRC'
            )

    def test_country_str_representation(self, db):
        """Test string representation of Country."""
        country = Country.objects.create(
            code='JP',
            name='日本',
            name_en='Japan'
        )
        assert str(country) == '日本'

    def test_country_ordering(self, db):
        """Test that countries are ordered by name."""
        Country.objects.create(code='CN', name='中国', name_en='China')
        Country.objects.create(code='US', name='美国', name_en='USA')
        Country.objects.create(code='JP', name='日本', name_en='Japan')

        countries = list(Country.objects.all())
        # Chinese name ordering
        assert countries[0].name == '中国'
        assert countries[1].name == '日本'
        assert countries[2].name == '美国'

    def test_country_is_active_default(self, db):
        """Test that is_active defaults to True."""
        country = Country.objects.create(
            code='KR',
            name='韩国',
            name_en='South Korea'
        )
        assert country.is_active is True

    def test_country_soft_delete(self, db):
        """Test soft delete via is_active flag."""
        country = Country.objects.create(
            code='DE',
            name='德国',
            name_en='Germany'
        )
        assert country.is_active is True

        country.is_active = False
        country.save()
        country.refresh_from_db()

        assert country.is_active is False

    def test_country_phone_code_optional(self, db):
        """Test that phone_code is optional."""
        country = Country.objects.create(
            code='FR',
            name='法国',
            name_en='France'
        )
        assert country.phone_code == ''


class TestPortModel:
    """Test cases for Port model."""

    def test_create_port(self, db):
        """Test creating a port with all fields."""
        country = Country.objects.create(
            code='CN',
            name='中国',
            name_en='China'
        )
        port = Port.objects.create(
            code='CNSHA',
            name='上海港',
            name_en='Shanghai',
            country=country,
            is_active=True
        )
        assert port.code == 'CNSHA'
        assert port.name == '上海港'
        assert port.name_en == 'Shanghai'
        assert port.country == country
        assert port.is_active is True

    def test_create_port_minimal(self, db):
        """Test creating a port with minimal required fields."""
        country = Country.objects.create(
            code='CN',
            name='中国',
            name_en='China'
        )
        port = Port.objects.create(
            code='CNSZX',
            name='深圳港',
            name_en='Shenzhen',
            country=country
        )
        assert port.code == 'CNSZX'
        assert port.name == '深圳港'
        assert port.country == country
        assert port.is_active is True  # Default value

    def test_port_code_unique(self, db):
        """Test that port code is unique."""
        country = Country.objects.create(
            code='CN',
            name='中国',
            name_en='China'
        )
        Port.objects.create(
            code='CNSHA',
            name='上海港',
            name_en='Shanghai',
            country=country
        )
        with pytest.raises(IntegrityError):
            Port.objects.create(
                code='CNSHA',  # Duplicate code
                name='上海',
                name_en='Shanghai Port',
                country=country
            )

    def test_port_str_representation(self, db):
        """Test string representation of Port."""
        country = Country.objects.create(
            code='CN',
            name='中国',
            name_en='China'
        )
        port = Port.objects.create(
            code='CNSHA',
            name='上海港',
            name_en='Shanghai',
            country=country
        )
        assert str(port) == '上海港'

    def test_port_country_relationship(self, db):
        """Test port-country relationship."""
        country = Country.objects.create(
            code='CN',
            name='中国',
            name_en='China'
        )
        port1 = Port.objects.create(
            code='CNSHA',
            name='上海港',
            name_en='Shanghai',
            country=country
        )
        port2 = Port.objects.create(
            code='CNSZX',
            name='深圳港',
            name_en='Shenzhen',
            country=country
        )

        # Check country has ports
        assert country.ports.count() == 2
        assert port1 in country.ports.all()
        assert port2 in country.ports.all()

    def test_port_ordering(self, db):
        """Test that ports are ordered by name."""
        country = Country.objects.create(
            code='CN',
            name='中国',
            name_en='China'
        )
        Port.objects.create(code='CNSZX', name='深圳港', name_en='Shenzhen', country=country)
        Port.objects.create(code='CNSHA', name='上海港', name_en='Shanghai', country=country)
        Port.objects.create(code='CNBJX', name='北京港', name_en='Beijing', country=country)

        ports = list(Port.objects.filter(country=country))
        # Chinese name ordering
        assert ports[0].name == '上海港'
        assert ports[1].name == '北京港'
        assert ports[2].name == '深圳港'

    def test_port_is_active_default(self, db):
        """Test that is_active defaults to True."""
        country = Country.objects.create(
            code='US',
            name='美国',
            name_en='USA'
        )
        port = Port.objects.create(
            code='USNYC',
            name='纽约港',
            name_en='New York',
            country=country
        )
        assert port.is_active is True

    def test_port_soft_delete(self, db):
        """Test soft delete via is_active flag."""
        country = Country.objects.create(
            code='JP',
            name='日本',
            name_en='Japan'
        )
        port = Port.objects.create(
            code='JPTYO',
            name='东京港',
            name_en='Tokyo',
            country=country
        )

        port.is_active = False
        port.save()
        port.refresh_from_db()

        assert port.is_active is False

    def test_port_cannot_exist_without_country(self, db):
        """Test that port must have a country."""
        # This should fail at database level due to NOT NULL constraint
        # and at ORM level due to required field
        country = Country.objects.create(
            code='CN',
            name='中国',
            name_en='China'
        )

        # Valid: port with country
        port = Port(
            code='CNSHA',
            name='上海港',
            name_en='Shanghai',
            country=country
        )
        port.full_clean()  # Should not raise

    def test_active_ports_manager(self, db):
        """Test getting only active ports."""
        country = Country.objects.create(
            code='CN',
            name='中国',
            name_en='China'
        )
        port1 = Port.objects.create(
            code='CNSHA',
            name='上海港',
            name_en='Shanghai',
            country=country,
            is_active=True
        )
        port2 = Port.objects.create(
            code='CNSZX',
            name='深圳港',
            name_en='Shenzhen',
            country=country,
            is_active=False
        )

        active_ports = Port.objects.filter(is_active=True)
        assert port1 in active_ports
        assert port2 not in active_ports


class CurrencyModelTest:
    """Test cases for Currency model."""

    def test_create_currency(self, db):
        """Test creating a currency with all fields."""
        currency = Currency.objects.create(
            code='CNY',
            name='人民币',
            name_en='Chinese Yuan',
            symbol='¥',
            is_active=True
        )
        assert currency.code == 'CNY'
        assert currency.name == '人民币'
        assert currency.name_en == 'Chinese Yuan'
        assert currency.symbol == '¥'
        assert currency.is_active is True

    def test_create_currency_minimal(self, db):
        """Test creating a currency with minimal required fields."""
        currency = Currency.objects.create(
            code='USD',
            name='美元',
            name_en='US Dollar'
        )
        assert currency.code == 'USD'
        assert currency.name == '美元'
        assert currency.name_en == 'US Dollar'
        assert currency.symbol == ''
        assert currency.is_active is True  # Default value

    def test_currency_code_unique(self, db):
        """Test that currency code is unique."""
        Currency.objects.create(
            code='USD',
            name='美元',
            name_en='US Dollar'
        )
        with pytest.raises(IntegrityError):
            Currency.objects.create(
                code='USD',  # Duplicate code
                name='美圆',
                name_en='United States Dollar'
            )

    def test_currency_str_representation(self, db):
        """Test string representation of Currency."""
        currency = Currency.objects.create(
            code='EUR',
            name='欧元',
            name_en='Euro',
            symbol='€'
        )
        assert str(currency) == '欧元'

    def test_currency_ordering(self, db):
        """Test that currencies are ordered by name."""
        Currency.objects.create(code='USD', name='美元', name_en='USD')
        Currency.objects.create(code='CNY', name='人民币', name_en='CNY')
        Currency.objects.create(code='EUR', name='欧元', name_en='EUR')

        currencies = list(Currency.objects.all())
        # Chinese name ordering
        assert currencies[0].name == '人民币'
        assert currencies[1].name == '欧元'
        assert currencies[2].name == '美元'

    def test_currency_is_active_default(self, db):
        """Test that is_active defaults to True."""
        currency = Currency.objects.create(
            code='JPY',
            name='日元',
            name_en='Japanese Yen'
        )
        assert currency.is_active is True

    def test_currency_soft_delete(self, db):
        """Test soft delete via is_active flag."""
        currency = Currency.objects.create(
            code='GBP',
            name='英镑',
            name_en='British Pound',
            symbol='£'
        )

        currency.is_active = False
        currency.save()
        currency.refresh_from_db()

        assert currency.is_active is False

    def test_currency_symbol_optional(self, db):
        """Test that symbol is optional."""
        currency = Currency.objects.create(
            code='AUD',
            name='澳元',
            name_en='Australian Dollar'
        )
        assert currency.symbol == ''

    def test_active_currencies_manager(self, db):
        """Test getting only active currencies."""
        curr1 = Currency.objects.create(
            code='CNY',
            name='人民币',
            name_en='CNY',
            is_active=True
        )
        curr2 = Currency.objects.create(
            code='JPY',
            name='日元',
            name_en='JPY',
            is_active=False
        )

        active_currencies = Currency.objects.filter(is_active=True)
        assert curr1 in active_currencies
        assert curr2 not in active_currencies

    def test_currency_with_special_symbol(self, db):
        """Test currencies with special unicode symbols."""
        currencies_data = [
            ('USD', '美元', 'US Dollar', '$'),
            ('EUR', '欧元', 'Euro', '€'),
            ('GBP', '英镑', 'British Pound', '£'),
            ('JPY', '日元', 'Japanese Yen', '¥'),
            ('KRW', '韩元', 'Korean Won', '₩'),
        ]

        for code, name, name_en, symbol in currencies_data:
            currency = Currency.objects.create(
                code=code,
                name=name,
                name_en=name_en,
                symbol=symbol
            )
            assert currency.symbol == symbol
            assert str(currency) == name
