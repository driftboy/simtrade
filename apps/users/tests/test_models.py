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
        assert user.is_active is True  # Inherited from AbstractUser

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
            code='teacher',
            name='Teacher',
            description='Teacher role with trading permissions'
        )
        assert role.code == 'teacher'
        assert role.name == 'Teacher'
        assert role.description == 'Teacher role with trading permissions'
        assert str(role) == 'Teacher'

    def test_role_code_unique(self, db):
        """Test that role code is unique."""
        Role.objects.create(
            code='teacher',
            name='Teacher'
        )
        with pytest.raises(IntegrityError):
            Role.objects.create(
                code='teacher',  # Duplicate code
                name='Instructor'
            )

    def test_role_str_representation(self, db):
        """Test string representation of Role."""
        role = Role.objects.create(
            code='admin',
            name='Administrator'
        )
        assert str(role) == 'Administrator'

    def test_role_ordering(self, db):
        """Test that roles are ordered by name."""
        Role.objects.create(code='teacher', name='Teacher')
        Role.objects.create(code='admin', name='Administrator')
        Role.objects.create(code='student', name='Student')

        roles = list(Role.objects.all())
        assert roles[0].name == 'Administrator'
        assert roles[1].name == 'Student'
        assert roles[2].name == 'Teacher'


class TestPermissionModel:
    """Test cases for Permission model."""

    def test_create_permission(self, db):
        """Test creating a permission."""
        permission = Permission.objects.create(
            resource='transaction',
            action='create',
            scope='self'
        )
        assert permission.resource == 'transaction'
        assert permission.action == 'create'
        assert permission.scope == 'self'

    def test_get_full_code(self, db):
        """Test get_full_code method."""
        permission = Permission.objects.create(
            resource='transaction',
            action='create',
            scope='self'
        )
        assert permission.get_full_code() == 'transaction.create.self'

    def test_permission_unique_constraint(self, db):
        """Test that resource+action+scope combination is unique."""
        Permission.objects.create(
            resource='transaction',
            action='create',
            scope='self'
        )
        with pytest.raises(IntegrityError):
            Permission.objects.create(
                resource='transaction',
                action='create',
                scope='self'  # Duplicate combination
            )

    def test_permission_different_scope_allowed(self, db):
        """Test that same resource+action with different scope is allowed."""
        Permission.objects.create(
            resource='transaction',
            action='create',
            scope='self'
        )
        # This should not raise - different scope
        Permission.objects.create(
            resource='transaction',
            action='create',
            scope='class'
        )

    def test_permission_str_representation(self, db):
        """Test string representation of Permission."""
        permission = Permission.objects.create(
            resource='transaction',
            action='delete',
            scope='all'
        )
        assert 'Transaction' in str(permission)
        assert 'Delete' in str(permission)
        assert 'All' in str(permission)

    def test_permission_choices(self, db):
        """Test that permission resource, action, scope accept valid choices."""
        # Valid resource
        perm = Permission(resource='transaction', action='create', scope='self')
        perm.full_clean()  # Should not raise

        # Valid action
        perm = Permission(resource='document', action='approve', scope='class')
        perm.full_clean()  # Should not raise

        # Valid scope
        perm = Permission(resource='user', action='read', scope='all')
        perm.full_clean()  # Should not raise

    def test_permission_ordering(self, db):
        """Test that permissions are ordered by resource, action, scope."""
        Permission.objects.create(resource='transaction', action='update', scope='self')
        Permission.objects.create(resource='document', action='create', scope='all')
        Permission.objects.create(resource='transaction', action='create', scope='self')

        permissions = list(Permission.objects.all())
        # document comes before transaction alphabetically
        assert permissions[0].resource == 'document'
        assert permissions[1].resource == 'transaction'
        assert permissions[1].action == 'create'
        assert permissions[2].action == 'update'


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
            code='teacher',
            name='Teacher'
        )
        user_role = UserRole.objects.create(
            user=user,
            role=role
        )
        assert user_role.user == user
        assert user_role.role == role
        assert user_role.assigned_at is not None

    def test_has_role_method(self, db):
        """Test has_role method on User model."""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        teacher_role = Role.objects.create(
            code='teacher',
            name='Teacher'
        )
        admin_role = Role.objects.create(
            code='admin',
            name='Admin'
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

    def test_has_role_superuser(self, db):
        """Test that superuser has all roles."""
        user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )

        # Superuser should have any role without explicit assignment
        assert user.has_role('teacher') is True
        assert user.has_role('admin') is True
        assert user.has_role('student') is True

    def test_multiple_users_same_role(self, db):
        """Test multiple users can have the same role."""
        role = Role.objects.create(
            code='student',
            name='Student'
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
            code='teacher',
            name='Teacher'
        )
        UserRole.objects.create(user=user, role=role)

        with pytest.raises(IntegrityError):
            UserRole.objects.create(user=user, role=role)


class TestRolePermission:
    """Test cases for RolePermission relationship."""

    def test_assign_permission_to_role(self, db):
        """Test assigning a permission to a role."""
        role = Role.objects.create(
            code='teacher',
            name='Teacher'
        )
        permission = Permission.objects.create(
            resource='transaction',
            action='create',
            scope='class'
        )
        role_permission = RolePermission.objects.create(
            role=role,
            permission=permission
        )
        assert role_permission.role == role
        assert role_permission.permission == permission
        assert role_permission.assigned_at is not None

    def test_role_has_multiple_permissions(self, db):
        """Test that a role can have multiple permissions."""
        role = Role.objects.create(
            code='trader',
            name='Trader'
        )
        perm1 = Permission.objects.create(resource='transaction', action='create', scope='self')
        perm2 = Permission.objects.create(resource='transaction', action='delete', scope='self')
        perm3 = Permission.objects.create(resource='transaction', action='read', scope='self')

        RolePermission.objects.create(role=role, permission=perm1)
        RolePermission.objects.create(role=role, permission=perm2)
        RolePermission.objects.create(role=role, permission=perm3)

        # Get all permissions for the role
        permissions = RolePermission.objects.filter(role=role)
        assert permissions.count() == 3

    def test_permission_for_multiple_roles(self, db):
        """Test that a permission can be assigned to multiple roles."""
        role1 = Role.objects.create(code='teacher', name='Teacher')
        role2 = Role.objects.create(code='admin', name='Admin')
        permission = Permission.objects.create(
            resource='user',
            action='read',
            scope='class'
        )

        RolePermission.objects.create(role=role1, permission=permission)
        RolePermission.objects.create(role=role2, permission=permission)

        role1_perms = RolePermission.objects.filter(role=role1)
        role2_perms = RolePermission.objects.filter(role=role2)

        assert role1_perms.count() == 1
        assert role2_perms.count() == 1
        assert role1_perms.first().permission.resource == 'user'
        assert role2_perms.first().permission.resource == 'user'

    def test_role_permission_unique_constraint(self, db):
        """Test that role-permission combination is unique."""
        role = Role.objects.create(code='teacher', name='Teacher')
        permission = Permission.objects.create(
            resource='transaction',
            action='create',
            scope='self'
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
            code='trader',
            name='Trader'
        )
        permission = Permission.objects.create(
            resource='transaction',
            action='create',
            scope='self'
        )

        # User has no permissions initially
        assert user.has_permission(permission.get_full_code()) is False

        # Assign role with permission
        UserRole.objects.create(user=user, role=role)
        RolePermission.objects.create(role=role, permission=permission)

        # Now user should have permission
        assert user.has_permission(permission.get_full_code()) is True

    def test_has_permission_multiple_roles(self, db):
        """Test has_permission with user having multiple roles."""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        role1 = Role.objects.create(code='trader', name='Trader')
        role2 = Role.objects.create(code='viewer', name='Viewer')
        perm1 = Permission.objects.create(resource='transaction', action='create', scope='self')
        perm2 = Permission.objects.create(resource='transaction', action='delete', scope='self')

        UserRole.objects.create(user=user, role=role1)
        UserRole.objects.create(user=user, role=role2)
        RolePermission.objects.create(role=role1, permission=perm1)
        RolePermission.objects.create(role=role2, permission=perm2)

        assert user.has_permission(perm1.get_full_code()) is True
        assert user.has_permission(perm2.get_full_code()) is True
        assert user.has_permission('transaction.read.self') is False

    def test_has_permission_superuser(self, db):
        """Test that superuser has all permissions."""
        user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )

        # Superuser should have any permission without explicit assignment
        assert user.has_permission('any.permission') is True
        assert user.has_permission('transaction.create.self') is True


class TestRoleMethods:
    """Test cases for Role model methods."""

    def test_add_permission(self, db):
        """Test add_permission method on Role."""
        role = Role.objects.create(code='teacher', name='Teacher')

        # Add permission
        result = role.add_permission('transaction', 'create', 'class')
        assert result is True  # Permission was added

        # Check permission exists
        perm = Permission.objects.get(resource='transaction', action='create', scope='class')
        assert RolePermission.objects.filter(role=role, permission=perm).exists()

    def test_add_permission_duplicate(self, db):
        """Test adding duplicate permission returns False."""
        role = Role.objects.create(code='teacher', name='Teacher')

        # Add permission first time
        result1 = role.add_permission('transaction', 'create', 'class')
        assert result1 is True

        # Try to add same permission again
        result2 = role.add_permission('transaction', 'create', 'class')
        assert result2 is False  # Already exists

    def test_remove_permission(self, db):
        """Test remove_permission method on Role."""
        role = Role.objects.create(code='teacher', name='Teacher')

        # Add permission
        role.add_permission('transaction', 'create', 'class')
        perm = Permission.objects.get(resource='transaction', action='create', scope='class')
        assert RolePermission.objects.filter(role=role, permission=perm).exists()

        # Remove permission
        result = role.remove_permission('transaction', 'create', 'class')
        assert result is True
        assert not RolePermission.objects.filter(role=role, permission=perm).exists()

    def test_remove_nonexistent_permission(self, db):
        """Test removing non-existent permission returns False."""
        role = Role.objects.create(code='teacher', name='Teacher')

        # Try to remove permission that doesn't exist
        result = role.remove_permission('transaction', 'delete', 'all')
        assert result is False
