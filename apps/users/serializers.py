"""
Serializers for User authentication and RBAC models.
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model, authenticate

from apps.users.models import Role, Permission, UserRole, RolePermission

User = get_user_model()


class PermissionSerializer(serializers.ModelSerializer):
    """Serializer for Permission model."""

    full_code = serializers.SerializerMethodField()

    class Meta:
        model = Permission
        fields = ['id', 'resource', 'action', 'scope', 'full_code']
        read_only_fields = fields

    def get_full_code(self, obj):
        """Get the full permission code in format: resource.action.scope"""
        return obj.get_full_code()


class RoleSerializer(serializers.ModelSerializer):
    """Serializer for Role model."""

    permissions = serializers.SerializerMethodField()

    class Meta:
        model = Role
        fields = ['id', 'code', 'name', 'description', 'permissions']
        read_only_fields = ['id']

    def get_permissions(self, obj):
        """Get permissions for this role."""
        return PermissionSerializer(
            [rp.permission for rp in obj.role_permissions.all()],
            many=True
        ).data


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model."""

    roles = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'user_type', 'phone',
            'student_id', 'avatar', 'is_active', 'is_superuser',
            'roles', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'is_active', 'is_superuser', 'roles',
            'created_at', 'updated_at'
        ]

    def get_roles(self, obj):
        """Get roles for this user."""
        return RoleSerializer(
            [ur.role for ur in obj.user_roles.all()],
            many=True
        ).data


class LoginSerializer(serializers.Serializer):
    """Serializer for user login."""

    username = serializers.CharField(
        max_length=150,
        write_only=True,
        required=True,
        help_text="Username for authentication"
    )
    password = serializers.CharField(
        max_length=128,
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        help_text="Password for authentication"
    )

    def validate(self, attrs):
        """
        Validate username and password credentials.

        Args:
            attrs: Dictionary containing username and password

        Returns:
            Dictionary with authenticated user

        Raises:
            ValidationError: If authentication fails
        """
        username = attrs.get('username')
        password = attrs.get('password')

        if username and password:
            user = authenticate(
                request=self.context.get('request'),
                username=username,
                password=password
            )

            if not user:
                msg = 'Unable to log in with provided credentials.'
                raise serializers.ValidationError(msg, code='authorization')

            if not user.is_active:
                msg = 'User account is disabled.'
                raise serializers.ValidationError(msg, code='authorization')

            attrs['user'] = user
        else:
            msg = 'Must include "username" and "password".'
            raise serializers.ValidationError(msg, code='required')

        return attrs


class LoginResponseSerializer(serializers.Serializer):
    """Serializer for login response."""

    user = UserSerializer(read_only=True)
    roles = RoleSerializer(many=True, read_only=True)

    class Meta:
        fields = ['user', 'roles']
