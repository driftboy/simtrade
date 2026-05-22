"""
Serializers for roles app.
"""
from rest_framework import serializers

from .models import Company, TradeRole, UserCompanyRole


class CompanySerializer(serializers.ModelSerializer):
    """Serializer for Company model."""

    country_name = serializers.CharField(source='country.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model = Company
        fields = [
            'id', 'name', 'name_en', 'code', 'type', 'country', 'country_name',
            'address', 'phone', 'email', 'logo', 'created_by', 'created_by_name',
            'created_at', 'updated_at'
        ]


class TradeRoleSerializer(serializers.ModelSerializer):
    """Serializer for TradeRole model."""

    class Meta:
        model = TradeRole
        fields = [
            'id', 'code', 'name', 'description', 'is_enabled', 'is_system',
            'sort_order', 'created_at'
        ]


class UserCompanyRoleSerializer(serializers.ModelSerializer):
    """Serializer for UserCompanyRole model."""

    user_id = serializers.IntegerField(source='user.id', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    company_id = serializers.IntegerField(source='company.id', read_only=True)
    company_name = serializers.CharField(source='company.name', read_only=True)
    company_code = serializers.CharField(source='company.code', read_only=True)
    role_id = serializers.IntegerField(source='role.id', read_only=True)
    role_code = serializers.CharField(source='role.code', read_only=True)
    role_name = serializers.CharField(source='role.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    requested_at = serializers.DateTimeField(read_only=True)
    approved_at = serializers.DateTimeField(read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.username', read_only=True)

    class Meta:
        model = UserCompanyRole
        fields = [
            'id', 'user_id', 'username', 'company_id', 'company_name', 'company_code',
            'role_id', 'role_code', 'role_name', 'status', 'status_display',
            'is_active', 'requested_at', 'approved_at', 'approved_by_name', 'notes'
        ]


class RoleRequestSerializer(serializers.Serializer):
    """Serializer for role request input."""

    company_id = serializers.IntegerField(min_value=1)
    role_code = serializers.CharField()
    notes = serializers.CharField(required=False, allow_blank=True)


class RoleApproveSerializer(serializers.Serializer):
    """Serializer for role approval input."""

    assignment_id = serializers.IntegerField(min_value=1)
    notes = serializers.CharField(required=False, allow_blank=True)


class RoleRejectSerializer(serializers.Serializer):
    """Serializer for role rejection input."""

    assignment_id = serializers.IntegerField(min_value=1)
    reason = serializers.CharField()


class CreateCompanySerializer(serializers.Serializer):
    """Serializer for company creation input."""

    name = serializers.CharField()
    name_en = serializers.CharField(required=False, allow_blank=True)
    country_id = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    type = serializers.CharField(required=False, allow_blank=True)
    address = serializers.CharField(required=False, allow_blank=True)
    phone = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
