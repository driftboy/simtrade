"""
Permission check decorators and helper functions for SimTrade Platform.

This module provides utility functions and decorators for checking user permissions
in a declarative way, following the RBAC (Role-Based Access Control) pattern.
"""
from functools import wraps

from django.core.exceptions import PermissionDenied


def has_permission(user, resource, action, scope, obj=None):
    """
    Check if a user has a specific permission.

    This is a standalone helper function that checks permissions through the user's
    roles. Superusers always have all permissions.

    Args:
        user: The User instance to check permissions for
        resource: The resource type (e.g., 'transaction', 'document')
        action: The action being performed (e.g., 'create', 'read', 'update', 'delete')
        scope: The scope of the permission (e.g., 'self', 'class', 'all')
        obj: Optional - The object being accessed (for future use with object-level checks)

    Returns:
        True if user has the permission, False otherwise

    Examples:
        >>> has_permission(user, 'transaction', 'create', 'self')
        True
        >>> has_permission(user, 'document', 'delete', 'all')
        False
    """
    if user.is_superuser:
        return True

    if not user.is_authenticated:
        return False

    # Use the User model's has_permission method which does the actual check
    permission_code = f'{resource}.{action}.{scope}'
    return user.has_permission(permission_code)


def require_permission(resource, action, scope):
    """
    Decorator that requires a specific permission to execute a function.

    This decorator checks if the first argument (user/request) has the required
    permission before executing the decorated function. Raises PermissionDenied
    if the user lacks the permission.

    Args:
        resource: The resource type (e.g., 'transaction', 'document')
        action: The action being performed (e.g., 'create', 'read', 'update', 'delete')
        scope: The scope of the permission (e.g., 'self', 'class', 'all')

    Raises:
        PermissionDenied: If the user doesn't have the required permission

    Examples:
        >>> @require_permission('transaction', 'create', 'self')
        ... def create_transaction(user, data):
        ...     # Only users with transaction.create.self permission can execute this
        ...     return Transaction.objects.create(**data)

        >>> @require_permission('document', 'delete', 'all')
        ... def delete_document(request, document_id):
        ...     # Only users with document.delete.all permission can execute this
        ...     return Document.objects.get(id=document_id).delete()
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Extract user from first argument
            # Supports both direct user passing and Django request object
            if args:
                first_arg = args[0]
                # Check if it's a request object with user attribute
                if hasattr(first_arg, 'user'):
                    user = first_arg.user
                else:
                    # Assume first argument is the user
                    user = first_arg
            else:
                raise PermissionDenied("No user context available")

            if not has_permission(user, resource, action, scope):
                raise PermissionDenied(
                    f"You do not have permission to {action} {resource} ({scope})"
                )

            return func(*args, **kwargs)
        return wrapper
    return decorator
