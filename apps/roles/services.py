"""
RoleService - 业务逻辑层服务

提供角色申请、审批、激活等功能。
"""
from django.utils import timezone
from django.db import transaction
import random

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
            ValueError: 如果已有待审核或激活的相同角色，或公司/角色不存在
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

        try:
            company = Company.objects.get(id=company_id)
        except Company.DoesNotExist:
            raise ValueError('公司不存在')

        try:
            role = TradeRole.objects.get(code=role_code)
        except TradeRole.DoesNotExist:
            raise ValueError('角色不存在')

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
            ValueError: 如果角色分配不存在或状态不是待审核
        """
        try:
            assignment = UserCompanyRole.objects.select_for_update().get(id=assignment_id)
        except UserCompanyRole.DoesNotExist:
            raise ValueError('角色分配不存在')

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
            ValueError: 如果角色分配不存在或状态不是待审核
        """
        try:
            assignment = UserCompanyRole.objects.select_for_update().get(id=assignment_id)
        except UserCompanyRole.DoesNotExist:
            raise ValueError('角色分配不存在')

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
    @transaction.atomic
    def activate_role(user, assignment_id):
        """
        激活角色（单一激活）

        Args:
            user: 用户
            assignment_id: 角色分配ID

        Returns:
            UserCompanyRole: 更新后的角色分配对象

        Raises:
            ValueError: 如果角色分配不存在、无权激活或状态不允许
        """
        try:
            assignment = UserCompanyRole.objects.get(id=assignment_id)
        except UserCompanyRole.DoesNotExist:
            raise ValueError('角色分配不存在')

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


class CompanyService:
    """公司服务类 - 处理公司相关的业务逻辑"""

    @staticmethod
    @transaction.atomic
    def create_company(user, name, name_en='', country_id=None, **kwargs):
        """
        创建公司并自动将创建者加入为出口商成员

        Args:
            user: 创建用户
            name: 公司名称
            name_en: 英文名称
            country_id: 国家代码（Country.code）
            **kwargs: 其他公司字段（type, address, phone, email等）

        Returns:
            Company: 创建的公司对象

        Raises:
            ValueError: 如果国家不存在
        """
        # 验证国家
        from apps.core.models import Country
        if country_id:
            try:
                # Country模型使用code作为主键
                country = Country.objects.get(code=country_id)
            except Country.DoesNotExist:
                raise ValueError('国家不存在')
        else:
            country = None

        # 生成唯一公司代码
        code = CompanyService._generate_company_code()

        # 创建公司
        company = Company.objects.create(
            name=name,
            name_en=name_en,
            code=code,
            country=country,
            created_by=user,
            **kwargs
        )

        # 获取出口商角色
        try:
            exporter_role = TradeRole.objects.get(code='exporter')
        except TradeRole.DoesNotExist:
            # 如果出口商角色不存在，创建它
            exporter_role = TradeRole.objects.create(
                code='exporter',
                name='出口商',
                description='负责出口贸易业务'
            )

        # 创建人自动成为该公司成员（出口商角色，状态active，is_active=True）
        UserCompanyRole.objects.create(
            user=user,
            company=company,
            role=exporter_role,
            status=UserCompanyRole.Status.ACTIVE,
            is_active=True
        )

        return company

    @staticmethod
    def get_company_details(company_id, user):
        """
        获取公司详情（含成员列表）

        Args:
            company_id: 公司ID
            user: 查询用户

        Returns:
            dict: {company: {...}, members: [...]}

        Raises:
            ValueError: 如果公司不存在
        """
        # 获取公司
        try:
            company = Company.objects.get(id=company_id)
        except Company.DoesNotExist:
            raise ValueError('公司不存在')

        # 获取成员（过滤状态：approved, active, suspended）
        valid_statuses = [
            UserCompanyRole.Status.APPROVED,
            UserCompanyRole.Status.ACTIVE,
            UserCompanyRole.Status.SUSPENDED
        ]

        members_qs = UserCompanyRole.objects.filter(
            company=company,
            status__in=valid_statuses
        ).select_related('user', 'role').order_by('-requested_at')

        # 构建成员列表
        members = []
        for member in members_qs:
            members.append({
                'user_id': member.user.id,
                'username': member.user.username,
                'role_code': member.role.code,
                'role_name': member.role.name,
                'status': member.status,
                'is_active': member.is_active
            })

        # 构建公司信息
        company_info = {
            'id': company.id,
            'name': company.name,
            'name_en': company.name_en,
            'code': company.code,
            'type': company.type,
            'country_id': company.country.code if company.country else None,  # Country uses code as PK
            'country_name': company.country.name if company.country else None,
            'address': company.address,
            'phone': company.phone,
            'email': company.email,
            'logo': company.logo,
            'created_by_id': company.created_by.id if company.created_by else None,
            'created_at': company.created_at.isoformat() if company.created_at else None,
        }

        return {
            'company': company_info,
            'members': members
        }

    @staticmethod
    def _generate_company_code():
        """
        生成唯一公司代码（私有方法）

        Returns:
            str: 格式为 COMP_XXXXXX 的6位随机数字代码

        Note:
            使用随机生成并检查唯一性的方式，确保代码不重复
        """
        max_attempts = 10
        for _ in range(max_attempts):
            # 生成6位随机数字
            random_digits = ''.join([str(random.randint(0, 9)) for _ in range(6)])
            code = f'COMP_{random_digits}'

            # 检查是否唯一
            if not Company.objects.filter(code=code).exists():
                return code

        # 如果随机生成失败（极罕见），使用时间戳确保唯一性
        import time
        timestamp_suffix = str(int(time.time()))[-6:]
        return f'COMP_{timestamp_suffix}'
