"""
User models and RBAC (Role-Based Access Control) system for SimTrade Platform.
"""
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.exceptions import PermissionDenied


class User(AbstractUser):
    """
    Custom User model for SimTrade Platform.
    Extends Django's AbstractUser with additional fields.
    """
    class UserType(models.TextChoices):
        STUDENT = 'student', 'Student'
        TEACHER = 'teacher', 'Teacher'
        ADMIN = 'admin', 'Administrator'

    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True, max_length=255)
    user_type = models.CharField(
        max_length=20,
        choices=UserType.choices,
        default=UserType.STUDENT
    )
    phone = models.CharField(max_length=20, blank=True, null=True)
    student_id = models.CharField(max_length=50, blank=True, null=True)
    avatar = models.URLField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
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
            role__code=role_code,
            role__is_active=True
        ).exists()

    def has_permission(self, permission_code: str) -> bool:
        """
        Check if user has a specific permission through their roles.

        Args:
            permission_code: The code of the permission to check (e.g., 'trade:create')

        Returns:
            True if user has the permission, False otherwise
        """
        if self.is_superuser:
            return True

        return RolePermission.objects.filter(
            role__role_users__user=self,
            permission__code=permission_code,
            role__is_active=True
        ).exists()


class Role(models.Model):
    """
    Role model for RBAC system.
    Roles are assigned to users and have permissions associated with them.
    """
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'roles'
        verbose_name = 'Role'
        verbose_name_plural = 'Roles'
        ordering = ['name']

    def __str__(self):
        return self.name

    def add_permission(self, permission_code: str) -> bool:
        """
        Add a permission to this role.

        Args:
            permission_code: The code of the permission to add

        Returns:
            True if permission was added, False if already exists
        """
        permission = Permission.objects.filter(code=permission_code).first()
        if not permission:
            return False

        role_perm, created = RolePermission.objects.get_or_create(
            role=self,
            permission=permission
        )
        return created

    def remove_permission(self, permission_code: str) -> bool:
        """
        Remove a permission from this role.

        Args:
            permission_code: The code of the permission to remove

        Returns:
            True if permission was removed, False if didn't exist
        """
        return RolePermission.objects.filter(
            role=self,
            permission__code=permission_code
        ).delete()[0] > 0


class Permission(models.Model):
    """
    Permission model for RBAC system.
    Permissions are granular actions that can be performed in the system.
    """
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'permissions'
        verbose_name = 'Permission'
        verbose_name_plural = 'Permissions'
        ordering = ['code']

    def __str__(self):
        return self.name

    def get_full_code(self) -> str:
        """
        Get the full permission code.

        Returns:
            The permission code string
        """
        return self.code


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
    assigned_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_roles'
    )

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
        return f'{self.role.name} - {self.permission.name}'
