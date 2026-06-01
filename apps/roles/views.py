"""
API views for roles app.
"""
from rest_framework import status
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from rest_framework.exceptions import ValidationError, NotFound, PermissionDenied

from .models import Company, TradeRole, UserCompanyRole
from .serializers import (
    CompanySerializer,
    TradeRoleSerializer,
    UserCompanyRoleSerializer,
    RoleRequestSerializer,
    RoleApproveSerializer,
    RoleRejectSerializer,
    CreateCompanySerializer
)
from .services import RoleService, CompanyService


class TradeRoleViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for TradeRole - read-only access to available roles.

    list: Get list of all available trade roles
    retrieve: Get details of a specific trade role
    """
    queryset = TradeRole.objects.all()
    serializer_class = TradeRoleSerializer
    permission_classes = [AllowAny]

    def list(self, request, *args, **kwargs):
        """
        List all available trade roles.

        Returns:
            200: List of roles retrieved successfully
                {
                    "code": 0,
                    "message": "success",
                    "data": [...]
                }
        """
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'code': 0,
            'message': 'success',
            'data': serializer.data
        }, status=status.HTTP_200_OK)


class UserCompanyRoleViewSet(viewsets.ViewSet):
    """
    ViewSet for UserCompanyRole - manage user role assignments.

    Provides endpoints for:
    - List user's roles
    - Request a new role
    - Approve role requests (teacher/staff only)
    - Reject role requests (teacher/staff only)
    - List pending requests (teacher/staff only)
    """
    permission_classes = [IsAuthenticated]

    def list(self, request):
        """
        List current user's role assignments.

        Returns:
            200: List of user's roles
                {
                    "code": 0,
                    "message": "success",
                    "data": [...]
                }
        """
        queryset = UserCompanyRole.objects.filter(
            user=request.user
        ).select_related('company', 'role')
        serializer = UserCompanyRoleSerializer(queryset, many=True)
        return Response({
            'code': 0,
            'message': 'success',
            'data': serializer.data
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='request')
    def request_role(self, request):
        """
        Request a new role assignment.

        Request body:
            company_id: int - Company ID
            role_code: str - Role code
            notes: str (optional) - Application notes

        Returns:
            200: Role request created successfully
            400: Invalid parameters or business logic error
            403: Permission denied
        """
        serializer = RoleRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'code': 3002,
                'message': '参数格式错误',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            assignment = RoleService.request_role(
                user=request.user,
                company_id=serializer.validated_data['company_id'],
                role_code=serializer.validated_data['role_code'],
                notes=serializer.validated_data.get('notes', '')
            )
            return Response({
                'code': 0,
                'message': '申请已提交，等待审核',
                'data': UserCompanyRoleSerializer(assignment).data
            }, status=status.HTTP_200_OK)

        except ValueError as e:
            error_msg = str(e)
            if '公司不存在' in error_msg or '角色不存在' in error_msg:
                return Response({
                    'code': 4001,
                    'message': error_msg
                }, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({
                    'code': 5005,
                    'message': error_msg
                }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='approve')
    def approve(self, request):
        """
        Approve a role request (teacher/staff only).

        Request body:
            assignment_id: int - Role assignment ID
            notes: str (optional) - Approval notes

        Returns:
            200: Role approved successfully
            400: Invalid parameters or business logic error
            403: Permission denied
        """
        if not (request.user.is_staff or request.user.user_type == 'teacher'):
            return Response({
                'code': 2001,
                'message': '无权限操作'
            }, status=status.HTTP_403_FORBIDDEN)

        serializer = RoleApproveSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'code': 3002,
                'message': '参数格式错误',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            assignment = RoleService.approve_role(
                assignment_id=serializer.validated_data['assignment_id'],
                approver=request.user,
                notes=serializer.validated_data.get('notes', '')
            )
            return Response({
                'code': 0,
                'message': '角色已批准并激活',
                'data': UserCompanyRoleSerializer(assignment).data
            }, status=status.HTTP_200_OK)

        except ValueError as e:
            return Response({
                'code': 5005,
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='reject')
    def reject(self, request):
        """
        Reject a role request (teacher/staff only).

        Request body:
            assignment_id: int - Role assignment ID
            reason: str - Rejection reason

        Returns:
            200: Role rejected successfully
            400: Invalid parameters or business logic error
            403: Permission denied
        """
        if not (request.user.is_staff or request.user.user_type == 'teacher'):
            return Response({
                'code': 2001,
                'message': '无权限操作'
            }, status=status.HTTP_403_FORBIDDEN)

        serializer = RoleRejectSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'code': 3002,
                'message': '参数格式错误',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            assignment = RoleService.reject_role(
                assignment_id=serializer.validated_data['assignment_id'],
                approver=request.user,
                reason=serializer.validated_data['reason']
            )
            return Response({
                'code': 0,
                'message': '角色申请已拒绝',
                'data': UserCompanyRoleSerializer(assignment).data
            }, status=status.HTTP_200_OK)

        except ValueError as e:
            return Response({
                'code': 5005,
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'], url_path='pending')
    def pending(self, request):
        """
        List all pending role requests (teacher/staff only).

        Returns:
            200: List of pending requests
            403: Permission denied
        """
        if not (request.user.is_staff or request.user.user_type == 'teacher'):
            return Response({
                'code': 2001,
                'message': '无权限操作'
            }, status=status.HTTP_403_FORBIDDEN)

        queryset = RoleService.get_pending_requests()
        serializer = UserCompanyRoleSerializer(queryset, many=True)
        return Response({
            'code': 0,
            'message': 'success',
            'data': serializer.data
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='activate')
    def activate(self, request, pk=None):
        """
        Activate a role assignment (single activation).

        Args:
            pk: UserCompanyRole ID

        Returns:
            200: Role activated successfully
            400: Invalid state or not owner
        """
        try:
            assignment = RoleService.activate_role(
                user=request.user,
                assignment_id=pk
            )
            return Response({
                'code': 0,
                'message': '角色已切换',
                'data': UserCompanyRoleSerializer(assignment).data
            }, status=status.HTTP_200_OK)

        except ValueError as e:
            return Response({
                'code': 5005,
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'], url_path='current')
    def current(self, request):
        """
        Get current active role context.

        Returns:
            200: Current role data or null
        """
        assignment = RoleService.get_current_role(request.user)
        if not assignment:
            return Response({
                'code': 0,
                'message': 'success',
                'data': None
            }, status=status.HTTP_200_OK)

        serializer = UserCompanyRoleSerializer(assignment)
        return Response({
            'code': 0,
            'message': 'success',
            'data': serializer.data
        }, status=status.HTTP_200_OK)


class CompanyViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Company - manage companies.

    Provides endpoints for:
    - Create a new company
    - Get company members
    - Join a company

    Note: list() action allows anonymous access for browsing,
    but create/update/delete require authentication.
    """
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    permission_classes = []  # Override per-action

    def get_permissions(self):
        """Set permissions based on action."""
        if self.action in ['list', 'retrieve']:
            # Allow anonymous users to browse companies
            return []
        return [IsAuthenticated()]

    def create(self, request):
        """
        Create a new company.

        Request body:
            name: str - Company name (required)
            name_en: str - English name (optional)
            country_id: int - Country ID (optional)
            type: str - Company type (optional)
            address: str - Address (optional)
            phone: str - Phone (optional)
            email: str - Email (optional)

        Returns:
            201: Company created successfully
                {
                    "code": 0,
                    "message": "公司创建成功",
                    "data": {...}
                }
            400: Invalid parameters or duplicate name
        """
        serializer = CreateCompanySerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'code': 3002,
                'message': '参数格式错误',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            company = CompanyService.create_company(
                user=request.user,
                **serializer.validated_data
            )
            return Response({
                'code': 0,
                'message': '公司创建成功',
                'data': CompanySerializer(company).data
            }, status=status.HTTP_201_CREATED)

        except ValueError as e:
            return Response({
                'code': 5005,
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            # Handle duplicate name constraint
            if 'unique' in str(e).lower() or 'exists' in str(e).lower():
                return Response({
                    'code': 5005,
                    'message': '公司名称已存在'
                }, status=status.HTTP_400_BAD_REQUEST)
            raise

    @action(detail=True, methods=['get'], url_path='members')
    def members(self, request, pk=None):
        """
        Get company members.

        Args:
            pk: Company ID

        Returns:
            200: Company members retrieved successfully
                {
                    "code": 0,
                    "message": "success",
                    "data": {
                        "company": {...},
                        "members": [...]
                    }
                }
            404: Company not found
        """
        try:
            result = CompanyService.get_company_details(
                company_id=pk,
                user=request.user
            )
            return Response({
                'code': 0,
                'message': 'success',
                'data': result
            }, status=status.HTTP_200_OK)

        except ValueError as e:
            return Response({
                'code': 4001,
                'message': str(e)
            }, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['post'], url_path='join')
    def join(self, request, pk=None):
        """
        Request to join a company.

        Args:
            pk: Company ID

        Request body:
            role_code: str - Role code to apply for
            notes: str (optional) - Application notes

        Returns:
            200: Join request submitted successfully
                {
                    "code": 0,
                    "message": "申请已提交，等待审核",
                    "data": {...}
                }
            400: Invalid parameters
            404: Company not found
        """
        # Verify company exists
        try:
            company = Company.objects.get(id=pk)
        except Company.DoesNotExist:
            return Response({
                'code': 4001,
                'message': '公司不存在'
            }, status=status.HTTP_404_NOT_FOUND)

        # Get role_code and notes from request
        role_code = request.data.get('role_code')
        notes = request.data.get('notes', '')

        if not role_code:
            return Response({
                'code': 3002,
                'message': '参数格式错误',
                'errors': {'role_code': ['此字段是必填项。']}
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            assignment = RoleService.request_role(
                user=request.user,
                company_id=pk,
                role_code=role_code,
                notes=notes
            )
            return Response({
                'code': 0,
                'message': '申请已提交，等待审核',
                'data': UserCompanyRoleSerializer(assignment).data
            }, status=status.HTTP_200_OK)

        except ValueError as e:
            error_msg = str(e)
            if '角色不存在' in error_msg:
                return Response({
                    'code': 4001,
                    'message': error_msg
                }, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({
                    'code': 5005,
                    'message': error_msg
                }, status=status.HTTP_400_BAD_REQUEST)
