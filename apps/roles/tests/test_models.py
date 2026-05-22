"""
Tests for Company and TradeRole models.
"""
import pytest
from django.db import IntegrityError

from apps.roles.models import Company, TradeRole
from apps.core.models import Country
from apps.users.models import User


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


class TestTradeRoleModel:
    """Test cases for TradeRole model."""

    def test_create_trade_role(self, db):
        """测试创建贸易角色"""
        role = TradeRole.objects.create(
            code='exporter',
            name='出口商',
            description='销售货物到国外',
            sort_order=1
        )

        assert role.code == 'exporter'
        assert role.name == '出口商'
        assert role.is_enabled is True
        assert role.is_system is True

    def test_trade_role_choices(self, db):
        """测试角色代码选择"""
        valid_codes = [choice[0] for choice in TradeRole.RoleType.choices]

        assert 'exporter' in valid_codes
        assert 'importer' in valid_codes
        assert 'factory' in valid_codes
        assert 'bank' in valid_codes
        assert 'customs' in valid_codes
        assert 'shipping' in valid_codes
        assert 'insurance' in valid_codes
        assert 'inspection' in valid_codes
        assert 'forex' in valid_codes
        assert 'tax' in valid_codes


class TestUserCompanyRoleModel:
    """Test cases for UserCompanyRole model."""

    def test_create_user_company_role(self, db):
        """测试创建用户-公司-角色分配"""
        country = Country.objects.create(code='CN', name='中国', name_en='China')
        user = User.objects.create_user(username='testuser', password='testpass')
        company = Company.objects.create(
            name='测试公司',
            code='TEST002',
            country=country
        )
        role = TradeRole.objects.create(
            code='exporter',
            name='出口商',
            description='销售货物'
        )

        from apps.roles.models import UserCompanyRole
        assignment = UserCompanyRole.objects.create(
            user=user,
            company=company,
            role=role
        )

        assert assignment.user == user
        assert assignment.company == company
        assert assignment.role == role
        assert assignment.status == 'pending'
        assert assignment.is_active is False

    def test_user_company_role_unique(self, db):
        """测试用户-公司-角色组合唯一性"""
        country = Country.objects.create(code='CN', name='中国', name_en='China')
        user = User.objects.create_user(username='testuser2', password='testpass')
        company = Company.objects.create(
            name='测试公司2',
            code='TEST003',
            country=country
        )
        role = TradeRole.objects.create(
            code='importer',
            name='进口商',
            description='购买货物'
        )

        from apps.roles.models import UserCompanyRole
        UserCompanyRole.objects.create(
            user=user,
            company=company,
            role=role
        )

        with pytest.raises(IntegrityError):
            UserCompanyRole.objects.create(
                user=user,
                company=company,
                role=role
            )

    def test_activate_role(self, db):
        """测试激活角色（单一激活）"""
        country = Country.objects.create(code='CN', name='中国', name_en='China')
        user = User.objects.create_user(username='testuser3', password='testpass')
        company = Company.objects.create(
            name='测试公司3',
            code='TEST004',
            country=country
        )
        role1 = TradeRole.objects.create(code='exporter', name='出口商', description='A')
        role2 = TradeRole.objects.create(code='importer', name='进口商', description='B')

        from apps.roles.models import UserCompanyRole
        assignment1 = UserCompanyRole.objects.create(
            user=user,
            company=company,
            role=role1,
            is_active=True
        )
        UserCompanyRole.objects.create(
            user=user,
            company=company,
            role=role2
        )

        # 激活第二个角色，第一个应该自动停用
        assignment2 = UserCompanyRole.objects.filter(user=user, role=role2).first()
        assignment2.is_active = True
        assignment2.save()

        assignment1.refresh_from_db()
        assert assignment1.is_active is False
        assert assignment2.is_active is True
