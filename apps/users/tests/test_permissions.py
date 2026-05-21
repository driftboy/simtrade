"""
Tests for permission check decorators and helper functions.
"""
import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied

from apps.users.models import Role, Permission, UserRole, RolePermission
from apps.users.permissions import has_permission, require_permission

User = get_user_model()


class TestPermissionCheck:
    """Test cases for permission checking functionality."""

    def test_superuser_has_all_permissions(self, db):
        """Test that superuser has all permissions regardless of role assignment."""
        superuser = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )

        # Superuser should have any permission without explicit assignment
        assert has_permission(superuser, 'transaction', 'create', 'self') is True
        assert has_permission(superuser, 'document', 'delete', 'all') is True
        assert has_permission(superuser, 'user', 'update', 'class') is True

    def test_user_without_permission_denied(self, db):
        """Test that user without specific permission is denied."""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        role = Role.objects.create(code='student', name='Student')
        UserRole.objects.create(user=user, role=role)

        # User has no permissions assigned
        assert has_permission(user, 'transaction', 'create', 'self') is False
        assert has_permission(user, 'document', 'read', 'class') is False

    def test_user_with_permission_allowed(self, db):
        """Test that user with specific permission is allowed."""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        role = Role.objects.create(code='trader', name='Trader')
        permission = Permission.objects.create(
            resource='transaction',
            action='create',
            scope='self'
        )

        UserRole.objects.create(user=user, role=role)
        RolePermission.objects.create(role=role, permission=permission)

        # User should have the assigned permission
        assert has_permission(user, 'transaction', 'create', 'self') is True

        # But not other permissions
        assert has_permission(user, 'transaction', 'delete', 'self') is False
        assert has_permission(user, 'document', 'create', 'self') is False

    def test_permission_decorator(self, db):
        """Test the require_permission decorator."""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        @require_permission('transaction', 'create', 'self')
        def create_transaction(request_user):
            return 'Transaction created'

        # User without permission should raise PermissionDenied
        with pytest.raises(PermissionDenied):
            create_transaction(user)

        # Grant permission to user
        role = Role.objects.create(code='trader', name='Trader')
        permission = Permission.objects.create(
            resource='transaction',
            action='create',
            scope='self'
        )
        UserRole.objects.create(user=user, role=role)
        RolePermission.objects.create(role=role, permission=permission)

        # Now user should be able to call the function
        result = create_transaction(user)
        assert result == 'Transaction created'

    def test_permission_decorator_with_superuser(self, db):
        """Test that decorator allows superuser without explicit permission."""
        superuser = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )

        @require_permission('any', 'action', 'scope')
        def some_restricted_function(request_user):
            return 'Success'

        # Superuser should bypass permission check
        result = some_restricted_function(superuser)
        assert result == 'Success'

    def test_has_permission_with_invalid_code_format(self, db):
        """Test has_permission with improperly formatted permission code."""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        # Invalid permission code format (not resource.action.scope)
        assert has_permission(user, 'invalid', 'format', 'extra', 'parts') is False

    def test_decorator_preserves_function_attributes(self, db):
        """Test that decorator preserves original function attributes."""
        @require_permission('transaction', 'read', 'self')
        def my_function(user_id):
            """My function docstring."""
            return f'User {user_id}'

        # Function name and docstring should be preserved
        assert my_function.__name__ == 'my_function'
        assert 'My function docstring' in my_function.__doc__
