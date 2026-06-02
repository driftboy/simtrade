"""
User models and RBAC (Role-Based Access Control) system for SimTrade Platform.
"""
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.exceptions import PermissionDenied
from django.core.validators import MinValueValidator, MaxValueValidator


class User(AbstractUser):
    """
    Custom User model for SimTrade Platform.
    Extends Django's AbstractUser with additional fields.
    """
    class UserType(models.TextChoices):
        STUDENT = 'student', 'Student'
        TEACHER = 'teacher', 'Teacher'
        ADMIN = 'admin', 'Administrator'

    # Note: username and is_active are inherited from AbstractUser
    # Override email to make it unique as per spec
    email = models.EmailField(unique=True, max_length=255)
    user_type = models.CharField(
        max_length=20,
        choices=UserType.choices,
        default=UserType.STUDENT
    )
    phone = models.CharField(max_length=20, blank=True, null=True)
    student_id = models.CharField(max_length=50, blank=True, null=True)
    avatar = models.URLField(blank=True, null=True)
    documents_per_page = models.PositiveIntegerField(
        default=5,
        validators=[MinValueValidator(5), MaxValueValidator(50)],
        help_text='单证列表每页显示数量'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-created_at']

    def __str__(self):
        return self.username

    def has_role(self, role_code: str) -> bool:
        """
        Check if user has a specific role.

        Args:
            role_code: The code of the role to check (e.g., 'teacher', 'admin')

        Returns:
            True if user has the role, False otherwise
        """
        if self.is_superuser:
            return True
        return self.user_roles.filter(
            role__code=role_code
        ).exists()

    def has_permission(self, permission_code: str) -> bool:
        """
        Check if user has a specific permission through their roles.

        Args:
            permission_code: The code of the permission to check (e.g., 'transaction.create.self')

        Returns:
            True if user has the permission, False otherwise
        """
        if self.is_superuser:
            return True

        # Parse permission code
        parts = permission_code.split('.')
        if len(parts) != 3:
            return False

        resource, action, scope = parts

        return RolePermission.objects.filter(
            role__role_users__user=self,
            permission__resource=resource,
            permission__action=action,
            permission__scope=scope
        ).exists()


class Role(models.Model):
    """
    Role model for RBAC system.
    Roles are assigned to users and have permissions associated with them.
    """
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'roles'
        verbose_name = 'Role'
        verbose_name_plural = 'Roles'
        ordering = ['name']

    def __str__(self):
        return self.name

    def add_permission(self, resource: str, action: str, scope: str) -> bool:
        """
        Add a permission to this role.

        Args:
            resource: The resource type (e.g., 'transaction', 'document')
            action: The action (e.g., 'create', 'read', 'update', 'delete')
            scope: The scope (e.g., 'self', 'class', 'all')

        Returns:
            True if permission was added, False if already exists
        """
        permission = Permission.objects.filter(
            resource=resource,
            action=action,
            scope=scope
        ).first()
        if not permission:
            permission = Permission.objects.create(
                resource=resource,
                action=action,
                scope=scope
            )

        role_perm, created = RolePermission.objects.get_or_create(
            role=self,
            permission=permission
        )
        return created

    def remove_permission(self, resource: str, action: str, scope: str) -> bool:
        """
        Remove a permission from this role.

        Args:
            resource: The resource type
            action: The action
            scope: The scope

        Returns:
            True if permission was removed, False if didn't exist
        """
        return RolePermission.objects.filter(
            role=self,
            permission__resource=resource,
            permission__action=action,
            permission__scope=scope
        ).delete()[0] > 0


class Permission(models.Model):
    """
    Permission model for RBAC system.
    Permissions are granular actions that can be performed in the system.
    Each permission is composed of resource, action, and scope.
    """
    class Resource(models.TextChoices):
        TRANSACTION = 'transaction', 'Transaction'
        DOCUMENT = 'document', 'Document'
        COURSE = 'course', 'Course'
        USER = 'user', 'User'
        SCORE = 'score', 'Score'
        SYSTEM_CONFIG = 'system_config', 'System Config'

    class Action(models.TextChoices):
        CREATE = 'create', 'Create'
        READ = 'read', 'Read'
        UPDATE = 'update', 'Update'
        DELETE = 'delete', 'Delete'
        APPROVE = 'approve', 'Approve'

    class Scope(models.TextChoices):
        SELF = 'self', 'Self'
        CLASS = 'class', 'Class'
        ALL = 'all', 'All'

    resource = models.CharField(max_length=50, choices=Resource.choices)
    action = models.CharField(max_length=50, choices=Action.choices)
    scope = models.CharField(max_length=50, choices=Scope.choices)

    class Meta:
        db_table = 'permissions'
        verbose_name = 'Permission'
        verbose_name_plural = 'Permissions'
        unique_together = ['resource', 'action', 'scope']
        ordering = ['resource', 'action', 'scope']

    def __str__(self):
        return f'{self.get_resource_display()} - {self.get_action_display()} ({self.get_scope_display()})'

    def get_full_code(self) -> str:
        """
        Get the full permission code in format: resource.action.scope

        Returns:
            The permission code string (e.g., 'transaction.create.self')
        """
        return f'{self.resource}.{self.action}.{self.scope}'


class UserRole(models.Model):
    """
    Through model for User-Role many-to-many relationship.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='user_roles'
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name='role_users'
    )
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'user_roles'
        verbose_name = 'User Role'
        verbose_name_plural = 'User Roles'
        unique_together = ['user', 'role']
        ordering = ['-assigned_at']

    def __str__(self):
        return f'{self.user.username} - {self.role.name}'


class RolePermission(models.Model):
    """
    Through model for Role-Permission many-to-many relationship.
    """
    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name='role_permissions'
    )
    permission = models.ForeignKey(
        Permission,
        on_delete=models.CASCADE,
        related_name='permission_roles'
    )
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'role_permissions'
        verbose_name = 'Role Permission'
        verbose_name_plural = 'Role Permissions'
        unique_together = ['role', 'permission']
        ordering = ['role', 'permission']

    def __str__(self):
        return f'{self.role.name} - {self.permission.get_full_code()}'
