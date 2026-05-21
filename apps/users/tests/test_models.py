"""
Tests for User, Role, Permission models and their relationships.
"""
import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from apps.users.models import User, Role, Permission, UserRole, RolePermission

User = get_user_model()


class TestUserModel:
    """Test cases for User model."""

    def test_create_user(self, db):
        """Test creating a basic user."""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        assert user.username == 'testuser'
        assert user.email == 'test@example.com'
        assert user.check_password('testpass123')
        assert user.user_type == 'student'  # Default user type
        assert user.is_active is True

    def test_create_user_with_all_fields(self, db):
        """Test creating a user with all optional fields."""
        user = User.objects.create_user(
            username='fulluser',
            email='full@example.com',
            password='testpass123',
            user_type='teacher',
            phone='13800138000',
            student_id='S2023001'
        )
        assert user.username == 'fulluser'
        assert user.user_type == 'teacher'
        assert user.phone == '13800138000'
        assert user.student_id == 'S2023001'

    def test_create_superuser(self, db):
        """Test creating a superuser."""
        user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )
        assert user.is_superuser is True
        assert user.is_staff is True
        assert user.is_active is True

    def test_user_str_representation(self, db):
        """Test string representation of User."""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        assert str(user) == 'testuser'

    def test_user_type_choices(self, db):
        """Test that user_type only accepts valid choices."""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        user.user_type = 'student'
        user.full_clean()  # Should not raise

        user.user_type = 'teacher'
        user.full_clean()  # Should not raise

        user.user_type = 'admin'
        user.full_clean()  # Should not raise


class TestRoleModel:
    """Test cases for Role model."""

    def test_create_role(self, db):
        """Test creating a role."""
        role = Role.objects.create(
            name='Teacher',
            code='teacher',
            description='Teacher role with trading permissions'
        )
        assert role.name == 'Teacher'
        assert role.code == 'teacher'
        assert role.description == 'Teacher role with trading permissions'
        assert str(role) == 'Teacher'

    def test_role_code_unique(self, db):
        """Test that role code is unique."""
        Role.objects.create(
            name='Teacher',
            code='teacher'
        )
        with pytest.raises(IntegrityError):
            Role.objects.create(
                name='Instructor',
                code='teacher'  # Duplicate code
            )

    def test_role_str_representation(self, db):
        """Test string representation of Role."""
        role = Role.objects.create(
            name='Administrator',
            code='admin'
        )
        assert str(role) == 'Administrator'


class TestPermissionModel:
    """Test cases for Permission model."""

    def test_create_permission(self, db):
        """Test creating a permission."""
        permission = Permission.objects.create(
            name='Create Trade',
            code='trade:create',
            description='Allow creating new trades'
        )
        assert permission.name == 'Create Trade'
        assert permission.code == 'trade:create'
        assert permission.description == 'Allow creating new trades'

    def test_get_full_code(self, db):
        """Test get_full_code method."""
        permission = Permission.objects.create(
            name='Create Trade',
            code='trade:create'
        )
        assert permission.get_full_code() == 'trade:create'

    def test_permission_code_unique(self, db):
        """Test that permission code is unique."""
        Permission.objects.create(
            name='Create Trade',
            code='trade:create'
        )
        with pytest.raises(IntegrityError):
            Permission.objects.create(
                name='New Trade',
                code='trade:create'  # Duplicate code
            )

    def test_permission_str_representation(self, db):
        """Test string representation of Permission."""
        permission = Permission.objects.create(
            name='Delete Trade',
            code='trade:delete'
        )
        assert str(permission) == 'Delete Trade'


class TestUserRole:
    """Test cases for UserRole relationship."""

    def test_assign_role_to_user(self, db):
        """Test assigning a role to a user."""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        role = Role.objects.create(
            name='Teacher',
            code='teacher'
        )
        user_role = UserRole.objects.create(
            user=user,
            role=role
        )
        assert user_role.user == user
        assert user_role.role == role

    def test_has_role_method(self, db):
        """Test has_role method on User model."""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        teacher_role = Role.objects.create(
            name='Teacher',
            code='teacher'
        )
        admin_role = Role.objects.create(
            name='Admin',
            code='admin'
        )

        # User has no roles initially
        assert user.has_role('teacher') is False
        assert user.has_role('admin') is False

        # Assign teacher role
        UserRole.objects.create(
            user=user,
            role=teacher_role
        )
        assert user.has_role('teacher') is True
        assert user.has_role('admin') is False

        # Assign admin role as well
        UserRole.objects.create(
            user=user,
            role=admin_role
        )
        assert user.has_role('teacher') is True
        assert user.has_role('admin') is True

    def test_multiple_users_same_role(self, db):
        """Test multiple users can have the same role."""
        role = Role.objects.create(
            name='Student',
            code='student'
        )
        user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='testpass123'
        )
        user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='testpass123'
        )

        UserRole.objects.create(user=user1, role=role)
        UserRole.objects.create(user=user2, role=role)

        assert user1.has_role('student') is True
        assert user2.has_role('student') is True

    def test_user_roles_unique_constraint(self, db):
        """Test that user-role combination is unique."""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        role = Role.objects.create(
            name='Teacher',
            code='teacher'
        )
        UserRole.objects.create(user=user, role=role)

        with pytest.raises(IntegrityError):
            UserRole.objects.create(user=user, role=role)


class TestRolePermission:
    """Test cases for RolePermission relationship."""

    def test_assign_permission_to_role(self, db):
        """Test assigning a permission to a role."""
        role = Role.objects.create(
            name='Teacher',
            code='teacher'
        )
        permission = Permission.objects.create(
            name='Create Trade',
            code='trade:create'
        )
        role_permission = RolePermission.objects.create(
            role=role,
            permission=permission
        )
        assert role_permission.role == role
        assert role_permission.permission == permission

    def test_role_has_multiple_permissions(self, db):
        """Test that a role can have multiple permissions."""
        role = Role.objects.create(
            name='Trader',
            code='trader'
        )
        perm1 = Permission.objects.create(
            name='Create Trade',
            code='trade:create'
        )
        perm2 = Permission.objects.create(
            name='Delete Trade',
            code='trade:delete'
        )
        perm3 = Permission.objects.create(
            name='View Trades',
            code='trade:view'
        )

        RolePermission.objects.create(role=role, permission=perm1)
        RolePermission.objects.create(role=role, permission=perm2)
        RolePermission.objects.create(role=role, permission=perm3)

        # Get all permissions for the role
        permission_codes = [
            rp.permission.code
            for rp in RolePermission.objects.filter(role=role)
        ]
        assert 'trade:create' in permission_codes
        assert 'trade:delete' in permission_codes
        assert 'trade:view' in permission_codes

    def test_permission_for_multiple_roles(self, db):
        """Test that a permission can be assigned to multiple roles."""
        role1 = Role.objects.create(
            name='Teacher',
            code='teacher'
        )
        role2 = Role.objects.create(
            name='Admin',
            code='admin'
        )
        permission = Permission.objects.create(
            name='View Users',
            code='users:view'
        )

        RolePermission.objects.create(role=role1, permission=permission)
        RolePermission.objects.create(role=role2, permission=permission)

        role1_perms = RolePermission.objects.filter(role=role1)
        role2_perms = RolePermission.objects.filter(role=role2)

        assert role1_perms.count() == 1
        assert role2_perms.count() == 1
        assert role1_perms.first().permission.code == 'users:view'
        assert role2_perms.first().permission.code == 'users:view'

    def test_role_permission_unique_constraint(self, db):
        """Test that role-permission combination is unique."""
        role = Role.objects.create(
            name='Teacher',
            code='teacher'
        )
        permission = Permission.objects.create(
            name='Create Trade',
            code='trade:create'
        )
        RolePermission.objects.create(role=role, permission=permission)

        with pytest.raises(IntegrityError):
            RolePermission.objects.create(role=role, permission=permission)


class TestUserPermission:
    """Test cases for User permission checking through roles."""

    def test_has_permission_method(self, db):
        """Test has_permission method on User model."""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        role = Role.objects.create(
            name='Trader',
            code='trader'
        )
        permission = Permission.objects.create(
            name='Create Trade',
            code='trade:create'
        )

        # User has no permissions initially
        assert user.has_permission('trade:create') is False

        # Assign role with permission
        UserRole.objects.create(user=user, role=role)
        RolePermission.objects.create(role=role, permission=permission)

        # Now user should have permission
        assert user.has_permission('trade:create') is True

    def test_has_permission_multiple_roles(self, db):
        """Test has_permission with user having multiple roles."""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        role1 = Role.objects.create(
            name='Trader',
            code='trader'
        )
        role2 = Role.objects.create(
            name='Viewer',
            code='viewer'
        )
        perm1 = Permission.objects.create(
            name='Create Trade',
            code='trade:create'
        )
        perm2 = Permission.objects.create(
            name='Delete Trade',
            code='trade:delete'
        )

        UserRole.objects.create(user=user, role=role1)
        UserRole.objects.create(user=user, role=role2)
        RolePermission.objects.create(role=role1, permission=perm1)
        RolePermission.objects.create(role=role2, permission=perm2)

        assert user.has_permission('trade:create') is True
        assert user.has_permission('trade:delete') is True
        assert user.has_permission('trade:view') is False

    def test_has_permission_superuser(self, db):
        """Test that superuser has all permissions."""
        user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )

        # Superuser should have any permission without explicit assignment
        assert user.has_permission('any:permission') is True
        assert user.has_permission('trade:create') is True
