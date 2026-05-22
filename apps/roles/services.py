"""
RoleService - 业务逻辑层服务

提供角色申请、审批、激活等功能。
"""
from django.utils import timezone
from django.db import transaction

from apps.roles.models import Company, TradeRole, UserCompanyRole


class RoleService:
    """角色服务类 - 处理角色相关的业务逻辑"""

    @staticmethod
    def request_role(user, company_id, role_code, notes=''):
        """
        学生申请角色

        Args:
            user: 申请用户
            company_id: 公司ID
            role_code: 角色代码
            notes: 申请备注

        Returns:
            UserCompanyRole: 创建的角色分配对象

        Raises:
            ValueError: 如果已有待审核或激活的相同角色
        """
        # 检查是否已有相同的角色分配（任何状态）
        # 由于模型有 unique_together 约束，需要先检查避免数据库错误
        existing = UserCompanyRole.objects.filter(
            user=user,
            company_id=company_id,
            role__code=role_code
        ).exists()

        if existing:
            raise ValueError('已有该角色分配')

        company = Company.objects.get(id=company_id)
        role = TradeRole.objects.get(code=role_code)

        return UserCompanyRole.objects.create(
            user=user,
            company=company,
            role=role,
            status=UserCompanyRole.Status.PENDING,
            is_active=False,
            notes=notes
        )

    @staticmethod
    @transaction.atomic
    def approve_role(assignment_id, approver, notes=''):
        """
        教师批准角色申请（同时激活）

        Args:
            assignment_id: 角色分配ID
            approver: 审批人
            notes: 审批备注

        Returns:
            UserCompanyRole: 更新后的角色分配对象

        Raises:
            ValueError: 如果状态不是待审核
        """
        assignment = UserCompanyRole.objects.select_for_update().get(id=assignment_id)

        if assignment.status != UserCompanyRole.Status.PENDING:
            raise ValueError('只能批准待审核的申请')

        # 设置状态为激活并激活该角色
        assignment.status = UserCompanyRole.Status.ACTIVE
        assignment.is_active = True
        assignment.approved_at = timezone.now()
        assignment.approved_by = approver

        # 合并备注
        if notes:
            if assignment.notes:
                assignment.notes = f'{assignment.notes}\n\n审批备注: {notes}'
            else:
                assignment.notes = f'审批备注: {notes}'

        assignment.save()
        return assignment

    @staticmethod
    @transaction.atomic
    def reject_role(assignment_id, approver, reason):
        """
        教师拒绝角色申请

        Args:
            assignment_id: 角色分配ID
            approver: 审批人
            reason: 拒绝原因

        Returns:
            UserCompanyRole: 更新后的角色分配对象

        Raises:
            ValueError: 如果状态不是待审核
        """
        assignment = UserCompanyRole.objects.select_for_update().get(id=assignment_id)

        if assignment.status != UserCompanyRole.Status.PENDING:
            raise ValueError('只能拒绝待审核的申请')

        assignment.status = UserCompanyRole.Status.REJECTED
        assignment.approved_by = approver

        # 记录拒绝原因
        if assignment.notes:
            assignment.notes = f'{assignment.notes}\n\n拒绝原因: {reason}'
        else:
            assignment.notes = f'拒绝原因: {reason}'

        assignment.save()
        return assignment

    @staticmethod
    def activate_role(user, assignment_id):
        """
        激活角色（单一激活）

        Args:
            user: 用户
            assignment_id: 角色分配ID

        Returns:
            UserCompanyRole: 更新后的角色分配对象

        Raises:
            ValueError: 如果无权激活或状态不允许
        """
        assignment = UserCompanyRole.objects.get(id=assignment_id)

        # 检查是否有权激活
        if assignment.user != user:
            raise ValueError('无权激活此角色')

        # 检查状态是否允许激活
        if assignment.status not in [
            UserCompanyRole.Status.ACTIVE,
            UserCompanyRole.Status.APPROVED
        ]:
            raise ValueError('只能激活已批准或激活中的角色')

        assignment.is_active = True
        assignment.save()  # save 方法会自动停用其他角色

        return assignment

    @staticmethod
    def get_current_role(user):
        """
        获取用户当前激活的角色

        Args:
            user: 用户

        Returns:
            UserCompanyRole: 当前激活的角色分配，如果没有则返回 None
        """
        try:
            return UserCompanyRole.objects.get(
                user=user,
                is_active=True
            )
        except UserCompanyRole.DoesNotExist:
            return None

    @staticmethod
    def get_pending_requests(user=None):
        """
        获取待审核申请

        Args:
            user: 可选，如果提供则只返回该用户的申请

        Returns:
            QuerySet: 待审核的角色分配查询集
        """
        queryset = UserCompanyRole.objects.filter(
            status=UserCompanyRole.Status.PENDING
        ).select_related('user', 'company', 'role')

        if user:
            queryset = queryset.filter(user=user)

        return queryset

    @staticmethod
    def switch_context(user):
        """
        获取用户当前角色上下文

        Args:
            user: 用户

        Returns:
            dict: 包含 company, role, permissions 的上下文字典，如果没有激活角色则返回 None
        """
        assignment = RoleService.get_current_role(user)

        if not assignment:
            return None

        return {
            'company': assignment.company,
            'role': assignment.role,
            'permissions': {
                'role_code': assignment.role.code,
                'company_id': assignment.company.id,
                'is_active': assignment.is_active,
                'status': assignment.status,
            }
        }
