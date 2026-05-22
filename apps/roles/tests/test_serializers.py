"""
Tests for serializers in roles app.
"""
import pytest
from rest_framework import serializers

from apps.roles.models import Company, TradeRole, UserCompanyRole
from apps.core.models import Country
from apps.users.models import User


class TestCompanySerializer:
    """Test cases for CompanySerializer."""

    def test_serialize_company_all_fields(self, db):
        """Test serializing a company with all fields."""
        country = Country.objects.create(
            code='CN',
            name='中国',
            name_en='China'
        )
        user = User.objects.create_user(username='creator', password='pass')
        company = Company.objects.create(
            name='测试外贸公司',
            name_en='Test Trading Co.',
            code='TEST001',
            type='进出口公司',
            country=country,
            address='上海市浦东新区',
            phone='021-12345678',
            email='test@example.com',
            logo='https://example.com/logo.png',
            created_by=user
        )

        from apps.roles.serializers import CompanySerializer
        serializer = CompanySerializer(company)
        data = serializer.data

        assert data['id'] == company.id
        assert data['name'] == '测试外贸公司'
        assert data['name_en'] == 'Test Trading Co.'
        assert data['code'] == 'TEST001'
        assert data['type'] == '进出口公司'
        assert data['country'] == country.code  # Country uses code as pk
        assert data['country_name'] == '中国'
        assert data['address'] == '上海市浦东新区'
        assert data['phone'] == '021-12345678'
        assert data['email'] == 'test@example.com'
        assert data['logo'] == 'https://example.com/logo.png'
        assert data['created_by'] == user.id
        assert data['created_by_name'] == 'creator'
        assert 'created_at' in data
        assert 'updated_at' in data

    def test_company_read_only_fields(self, db):
        """Test that country_name and created_by_name are read-only."""
        from apps.roles.serializers import CompanySerializer
        serializer = CompanySerializer()

        assert 'country_name' in serializer.fields
        assert 'created_by_name' in serializer.fields
        assert serializer.fields['country_name'].read_only is True
        assert serializer.fields['created_by_name'].read_only is True


class TestTradeRoleSerializer:
    """Test cases for TradeRoleSerializer."""

    def test_serialize_trade_role(self, db):
        """Test serializing a trade role."""
        role = TradeRole.objects.create(
            code='exporter',
            name='出口商',
            description='销售货物到国外',
            is_enabled=True,
            is_system=True,
            sort_order=1
        )

        from apps.roles.serializers import TradeRoleSerializer
        serializer = TradeRoleSerializer(role)
        data = serializer.data

        assert data['id'] == role.id
        assert data['code'] == 'exporter'
        assert data['name'] == '出口商'
        assert data['description'] == '销售货物到国外'
        assert data['is_enabled'] is True
        assert data['is_system'] is True
        assert data['sort_order'] == 1
        assert 'created_at' in data

    def test_serialize_trade_role_disabled(self, db):
        """Test serializing a disabled trade role."""
        role = TradeRole.objects.create(
            code='importer',
            name='进口商',
            description='从国外购买货物',
            is_enabled=False,
            sort_order=2
        )

        from apps.roles.serializers import TradeRoleSerializer
        serializer = TradeRoleSerializer(role)
        data = serializer.data

        assert data['is_enabled'] is False


class TestUserCompanyRoleSerializer:
    """Test cases for UserCompanyRoleSerializer."""

    def test_serialize_user_company_role(self, db):
        """Test serializing a user-company-role assignment."""
        country = Country.objects.create(code='CN', name='中国', name_en='China')
        user = User.objects.create_user(username='testuser', password='pass', email='testuser@example.com')
        approver = User.objects.create_user(username='approver', password='pass', email='approver@example.com')
        company = Company.objects.create(
            name='测试公司',
            code='TEST001',
            country=country
        )
        role = TradeRole.objects.create(
            code='exporter',
            name='出口商',
            description='销售货物'
        )
        assignment = UserCompanyRole.objects.create(
            user=user,
            company=company,
            role=role,
            status='approved',
            is_active=True,
            approved_by=approver,
            notes='测试备注'
        )

        from apps.roles.serializers import UserCompanyRoleSerializer
        serializer = UserCompanyRoleSerializer(assignment)
        data = serializer.data

        assert data['id'] == assignment.id
        assert data['user_id'] == user.id
        assert data['username'] == 'testuser'
        assert data['company_id'] == company.id
        assert data['company_name'] == '测试公司'
        assert data['company_code'] == 'TEST001'
        assert data['role_id'] == role.id
        assert data['role_code'] == 'exporter'
        assert data['role_name'] == '出口商'
        assert data['status'] == 'approved'
        assert data['status_display'] == '已批准'
        assert data['is_active'] is True
        assert 'requested_at' in data
        assert 'approved_at' in data
        assert data['approved_by_name'] == 'approver'
        assert data['notes'] == '测试备注'

    def test_read_only_fields(self, db):
        """Test that id, user_id, username, company_id, company_name, company_code,
        role_id, role_code, role_name, status_display, requested_at, approved_at,
        approved_by_name are read-only.
        """
        from apps.roles.serializers import UserCompanyRoleSerializer
        serializer = UserCompanyRoleSerializer()

        read_only_fields = [
            'id', 'user_id', 'username', 'company_id', 'company_name',
            'company_code', 'role_id', 'role_code', 'role_name',
            'status_display', 'requested_at', 'approved_at', 'approved_by_name'
        ]

        for field in read_only_fields:
            assert field in serializer.fields
            assert serializer.fields[field].read_only is True, f'{field} should be read-only'

    def test_status_display(self, db):
        """Test that status_display returns the correct display value."""
        from apps.roles.serializers import UserCompanyRoleSerializer

        country = Country.objects.create(code='CN', name='中国', name_en='China')
        user = User.objects.create_user(username='testuser2', password='pass', email='testuser2@example.com')
        company = Company.objects.create(
            name='测试公司2',
            code='TEST002',
            country=country
        )
        role = TradeRole.objects.create(
            code='importer',
            name='进口商',
            description='购买货物'
        )

        # Test pending status
        assignment = UserCompanyRole.objects.create(
            user=user,
            company=company,
            role=role,
            status='pending'
        )
        serializer = UserCompanyRoleSerializer(assignment)
        assert serializer.data['status_display'] == '待审核'

        # Test approved status
        assignment.status = 'approved'
        assignment.save()
        serializer = UserCompanyRoleSerializer(assignment)
        assert serializer.data['status_display'] == '已批准'

        # Test rejected status
        assignment.status = 'rejected'
        assignment.save()
        serializer = UserCompanyRoleSerializer(assignment)
        assert serializer.data['status_display'] == '已拒绝'

        # Test active status
        assignment.status = 'active'
        assignment.save()
        serializer = UserCompanyRoleSerializer(assignment)
        assert serializer.data['status_display'] == '激活中'

        # Test suspended status
        assignment.status = 'suspended'
        assignment.save()
        serializer = UserCompanyRoleSerializer(assignment)
        assert serializer.data['status_display'] == '已暂停'


class TestRoleRequestSerializer:
    """Test cases for RoleRequestSerializer."""

    def test_valid_role_request(self, db):
        """Test validating a valid role request."""
        from apps.roles.serializers import RoleRequestSerializer

        data = {
            'company_id': 1,
            'role_code': 'exporter',
            'notes': '希望担任出口商角色'
        }
        serializer = RoleRequestSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

    def test_valid_role_request_without_notes(self, db):
        """Test validating a role request without notes."""
        from apps.roles.serializers import RoleRequestSerializer

        data = {
            'company_id': 1,
            'role_code': 'exporter'
        }
        serializer = RoleRequestSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

    def test_invalid_role_request_missing_company_id(self, db):
        """Test that missing company_id fails validation."""
        from apps.roles.serializers import RoleRequestSerializer

        data = {
            'role_code': 'exporter'
        }
        serializer = RoleRequestSerializer(data=data)
        assert not serializer.is_valid()
        assert 'company_id' in serializer.errors

    def test_invalid_role_request_missing_role_code(self, db):
        """Test that missing role_code fails validation."""
        from apps.roles.serializers import RoleRequestSerializer

        data = {
            'company_id': 1
        }
        serializer = RoleRequestSerializer(data=data)
        assert not serializer.is_valid()
        assert 'role_code' in serializer.errors

    def test_invalid_company_id_zero(self, db):
        """Test that company_id=0 fails validation (min_value=1)."""
        from apps.roles.serializers import RoleRequestSerializer

        data = {
            'company_id': 0,
            'role_code': 'exporter'
        }
        serializer = RoleRequestSerializer(data=data)
        assert not serializer.is_valid()
        assert 'company_id' in serializer.errors

    def test_invalid_company_id_negative(self, db):
        """Test that negative company_id fails validation."""
        from apps.roles.serializers import RoleRequestSerializer

        data = {
            'company_id': -1,
            'role_code': 'exporter'
        }
        serializer = RoleRequestSerializer(data=data)
        assert not serializer.is_valid()
        assert 'company_id' in serializer.errors


class TestRoleApproveSerializer:
    """Test cases for RoleApproveSerializer."""

    def test_valid_role_approve(self, db):
        """Test validating a valid role approval."""
        from apps.roles.serializers import RoleApproveSerializer

        data = {
            'assignment_id': 1,
            'notes': '批准申请'
        }
        serializer = RoleApproveSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

    def test_valid_role_approve_without_notes(self, db):
        """Test validating a role approval without notes."""
        from apps.roles.serializers import RoleApproveSerializer

        data = {
            'assignment_id': 1
        }
        serializer = RoleApproveSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

    def test_invalid_role_approve_missing_assignment_id(self, db):
        """Test that missing assignment_id fails validation."""
        from apps.roles.serializers import RoleApproveSerializer

        data = {}
        serializer = RoleApproveSerializer(data=data)
        assert not serializer.is_valid()
        assert 'assignment_id' in serializer.errors

    def test_invalid_assignment_id_zero(self, db):
        """Test that assignment_id=0 fails validation."""
        from apps.roles.serializers import RoleApproveSerializer

        data = {
            'assignment_id': 0
        }
        serializer = RoleApproveSerializer(data=data)
        assert not serializer.is_valid()
        assert 'assignment_id' in serializer.errors


class TestRoleRejectSerializer:
    """Test cases for RoleRejectSerializer."""

    def test_valid_role_reject(self, db):
        """Test validating a valid role rejection."""
        from apps.roles.serializers import RoleRejectSerializer

        data = {
            'assignment_id': 1,
            'reason': '资格不符'
        }
        serializer = RoleRejectSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

    def test_invalid_role_reject_missing_assignment_id(self, db):
        """Test that missing assignment_id fails validation."""
        from apps.roles.serializers import RoleRejectSerializer

        data = {
            'reason': '资格不符'
        }
        serializer = RoleRejectSerializer(data=data)
        assert not serializer.is_valid()
        assert 'assignment_id' in serializer.errors

    def test_invalid_role_reject_missing_reason(self, db):
        """Test that missing reason fails validation."""
        from apps.roles.serializers import RoleRejectSerializer

        data = {
            'assignment_id': 1
        }
        serializer = RoleRejectSerializer(data=data)
        assert not serializer.is_valid()
        assert 'reason' in serializer.errors

    def test_invalid_assignment_id_negative(self, db):
        """Test that negative assignment_id fails validation."""
        from apps.roles.serializers import RoleRejectSerializer

        data = {
            'assignment_id': -1,
            'reason': '资格不符'
        }
        serializer = RoleRejectSerializer(data=data)
        assert not serializer.is_valid()
        assert 'assignment_id' in serializer.errors


class TestCreateCompanySerializer:
    """Test cases for CreateCompanySerializer."""

    def test_valid_company_creation_all_fields(self, db):
        """Test validating company creation with all fields."""
        from apps.roles.serializers import CreateCompanySerializer

        data = {
            'name': '新公司',
            'name_en': 'New Company',
            'country_id': 1,
            'type': '进出口公司',
            'address': '北京市朝阳区',
            'phone': '010-12345678',
            'email': 'newcompany@example.com'
        }
        serializer = CreateCompanySerializer(data=data)
        assert serializer.is_valid(), serializer.errors

    def test_valid_company_creation_minimal(self, db):
        """Test validating company creation with only required field."""
        from apps.roles.serializers import CreateCompanySerializer

        data = {
            'name': '最小化公司'
        }
        serializer = CreateCompanySerializer(data=data)
        assert serializer.is_valid(), serializer.errors

    def test_invalid_company_creation_missing_name(self, db):
        """Test that missing name fails validation."""
        from apps.roles.serializers import CreateCompanySerializer

        data = {
            'type': '进出口公司'
        }
        serializer = CreateCompanySerializer(data=data)
        assert not serializer.is_valid()
        assert 'name' in serializer.errors

    def test_invalid_company_creation_invalid_email(self, db):
        """Test that invalid email fails validation."""
        from apps.roles.serializers import CreateCompanySerializer

        data = {
            'name': '测试公司',
            'email': 'not-an-email'
        }
        serializer = CreateCompanySerializer(data=data)
        assert not serializer.is_valid()
        assert 'email' in serializer.errors

    def test_invalid_country_id_zero(self, db):
        """Test that country_id=0 fails validation."""
        from apps.roles.serializers import CreateCompanySerializer

        data = {
            'name': '测试公司',
            'country_id': 0
        }
        serializer = CreateCompanySerializer(data=data)
        assert not serializer.is_valid()
        assert 'country_id' in serializer.errors
