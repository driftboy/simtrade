from rest_framework.permissions import BasePermission


class IsTeacherOrAdmin(BasePermission):
    """教师或管理员权限"""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.user_type in ('teacher', 'admin')
