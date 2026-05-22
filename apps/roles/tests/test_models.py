"""
Tests for Company model.
"""
import pytest
from django.db import IntegrityError

from apps.roles.models import Company
from apps.core.models import Country


class TestCompanyModel:
    """Test cases for Company model."""

    def test_create_company(self, db):
        """Test creating a company with all fields."""
        country = Country.objects.create(
            code='CN',
            name='中国',
            name_en='China'
        )
        company = Company.objects.create(
            name='测试外贸公司',
            name_en='Test Trading Co.',
            code='TEST001',
            type='进出口公司',
            country=country,
            address='上海市浦东新区',
            phone='021-12345678',
            email='test@example.com'
        )

        assert company.name == '测试外贸公司'
        assert company.name_en == 'Test Trading Co.'
        assert company.code == 'TEST001'
        assert company.type == '进出口公司'
        assert company.country == country
        assert company.address == '上海市浦东新区'
        assert company.phone == '021-12345678'
        assert company.email == 'test@example.com'
        assert str(company) == '测试外贸公司'

    def test_create_company_minimal(self, db):
        """Test creating a company with minimal required fields."""
        country = Country.objects.create(
            code='US',
            name='美国',
            name_en='USA'
        )
        company = Company.objects.create(
            name='Minimal Co.',
            code='MIN001',
            country=country
        )

        assert company.name == 'Minimal Co.'
        assert company.code == 'MIN001'
        assert company.name_en == ''
        assert company.type == ''
        assert company.address == ''
        assert company.phone == ''
        assert company.email == ''

    def test_company_name_unique(self, db):
        """Test that company name is unique."""
        country = Country.objects.create(
            code='CN',
            name='中国',
            name_en='China'
        )
        Company.objects.create(
            name='重复公司名',
            code='UNIQUE001',
            country=country
        )

        with pytest.raises(IntegrityError):
            Company.objects.create(
                name='重复公司名',  # Duplicate name
                code='UNIQUE002',
                country=country
            )

    def test_company_code_unique(self, db):
        """Test that company code is unique."""
        country = Country.objects.create(
            code='CN',
            name='中国',
            name_en='China'
        )
        Company.objects.create(
            name='公司1',
            code='UNIQUE001',
            country=country
        )

        with pytest.raises(IntegrityError):
            Company.objects.create(
                name='公司2',
                code='UNIQUE001',  # Duplicate code
                country=country
            )

    def test_company_country_relationship(self, db):
        """Test company-country relationship."""
        country = Country.objects.create(
            code='CN',
            name='中国',
            name_en='China'
        )
        company1 = Company.objects.create(
            name='公司1',
            code='CO001',
            country=country
        )
        company2 = Company.objects.create(
            name='公司2',
            code='CO002',
            country=country
        )

        # Check country has companies
        assert country.companies.count() == 2
        assert company1 in country.companies.all()
        assert company2 in country.companies.all()

    def test_company_country_protect_on_delete(self, db):
        """Test that country cannot be deleted if companies reference it."""
        country = Country.objects.create(
            code='CN',
            name='中国',
            name_en='China'
        )
        Company.objects.create(
            name='测试公司',
            code='TEST001',
            country=country
        )

        # PROTECT constraint should prevent deletion
        with pytest.raises(IntegrityError):
            country.delete()

    def test_company_optional_fields(self, db):
        """Test that optional fields can be blank."""
        country = Country.objects.create(
            code='JP',
            name='日本',
            name_en='Japan'
        )
        company = Company.objects.create(
            name='可选字段测试公司',
            code='OPT001',
            country=country
        )

        # Optional fields should be empty by default
        assert company.name_en == ''
        assert company.type == ''
        assert company.address == ''
        assert company.phone == ''
        assert company.email == ''

    def test_company_ordering(self, db):
        """Test that companies are ordered by created_at descending."""
        import time
        country = Country.objects.create(
            code='CN',
            name='中国',
            name_en='China'
        )
        company1 = Company.objects.create(
            name='公司1',
            code='CO001',
            country=country
        )
        time.sleep(0.01)  # Ensure different created_at timestamps
        company2 = Company.objects.create(
            name='公司2',
            code='CO002',
            country=country
        )

        companies = list(Company.objects.all())
        # Most recent first (descending created_at)
        assert companies[0] == company2
        assert companies[1] == company1

    def test_company_str_representation(self, db):
        """Test string representation of Company."""
        country = Country.objects.create(
            code='CN',
            name='中国',
            name_en='China'
        )
        company = Company.objects.create(
            name='字符串表示测试公司',
            code='STR001',
            country=country
        )
        assert str(company) == '字符串表示测试公司'

    def test_company_email_optional(self, db):
        """Test that email field is optional."""
        country = Country.objects.create(
            code='DE',
            name='德国',
            name_en='Germany'
        )
        company = Company.objects.create(
            name='无邮箱公司',
            code='NOEMAIL',
            country=country
        )
        assert company.email == ''

    def test_company_with_email(self, db):
        """Test creating a company with email."""
        country = Country.objects.create(
            code='FR',
            name='法国',
            name_en='France'
        )
        company = Company.objects.create(
            name='有邮箱公司',
            code='HASMAIL',
            email='contact@company.com',
            country=country
        )
        assert company.email == 'contact@company.com'
