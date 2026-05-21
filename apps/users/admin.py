"""
Admin configuration for User models and RBAC system.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Role, Permission, UserRole, RolePermission


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin interface for custom User model."""

    list_display = ['username', 'email', 'user_type', 'is_active', 'created_at']
    list_filter = ['user_type', 'is_active', 'is_staff', 'created_at']
    search_fields = ['username', 'email', 'student_id', 'phone']
    ordering = ['-created_at']

    fieldsets = BaseUserAdmin.fieldsets + (
        ('Additional Info', {
            'fields': ('user_type', 'phone', 'student_id', 'avatar')
        }),
    )

    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Additional Info', {
            'fields': ('email', 'user_type', 'phone', 'student_id')
        }),
    )


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    """Admin interface for Role model."""

    list_display = ['code', 'name', 'description', 'created_at']
    list_filter = ['created_at']
    search_fields = ['code', 'name', 'description']
    ordering = ['name']

    fieldsets = (
        ('Basic Info', {
            'fields': ('code', 'name', 'description')
        }),
    )


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    """Admin interface for Permission model."""

    list_display = ['resource', 'action', 'scope', 'get_full_code']
    list_filter = ['resource', 'action', 'scope']
    search_fields = ['resource', 'action', 'scope']
    ordering = ['resource', 'action', 'scope']

    fieldsets = (
        ('Permission Details', {
            'fields': ('resource', 'action', 'scope')
        }),
    )

    readonly_fields = ['get_full_code']


@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    """Admin interface for UserRole through model."""

    list_display = ['user', 'role', 'assigned_at']
    list_filter = ['role', 'assigned_at']
    search_fields = ['user__username', 'user__email', 'role__name', 'role__code']
    ordering = ['-assigned_at']

    fieldsets = (
        ('Assignment', {
            'fields': ('user', 'role')
        }),
    )

    readonly_fields = ['assigned_at']


@admin.register(RolePermission)
class RolePermissionAdmin(admin.ModelAdmin):
    """Admin interface for RolePermission through model."""

    list_display = ['role', 'permission', 'assigned_at']
    list_filter = ['role', 'permission__resource', 'permission__action', 'assigned_at']
    search_fields = ['role__name', 'role__code', 'permission__resource', 'permission__action']
    ordering = ['role', 'permission']

    fieldsets = (
        ('Permission Assignment', {
            'fields': ('role', 'permission')
        }),
    )

    readonly_fields = ['assigned_at']
