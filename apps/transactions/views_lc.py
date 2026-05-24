from datetime import date
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from apps.transactions.models import LetterOfCredit, BankOperation
from apps.transactions.serializers import LetterOfCreditSerializer
from apps.roles.services import RoleService


class LetterOfCreditViewSet(viewsets.ModelViewSet):
    """信用证视图集"""

    serializer_class = LetterOfCreditSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """只返回当前角色公司相关的信用证"""
        user = self.request.user
        current_role = RoleService.get_current_role(user)

        if not current_role or not current_role.company:
            return LetterOfCredit.objects.none()

        company = current_role.company
        return LetterOfCredit.objects.filter(
            applicant=company
        ) | LetterOfCredit.objects.filter(
            beneficiary=company
        ) | LetterOfCredit.objects.filter(
            issuing_bank=company.name
        )

    def list(self, request, *args, **kwargs):
        """获取信用证列表，支持 status 查询参数过滤"""
        queryset = self.get_queryset()

        # Optional status filter
        status_filter = request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'code': 0,
            'message': 'success',
            'data': serializer.data
        })

    def create(self, request, *args, **kwargs):
        """创建信用证 — 只有进口商(importer)可创建"""
        current_role = RoleService.get_current_role(request.user)

        if not current_role or not current_role.company:
            return Response({
                'code': 4001,
                'message': '请先激活一个角色'
            }, status=status.HTTP_400_BAD_REQUEST)

        if current_role.role.code != 'importer':
            return Response({
                'code': 4003,
                'message': '只有进口商可以申请开立信用证'
            }, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save(
                applicant=current_role.company,
                status='draft'
            )
            return Response({
                'code': 0,
                'message': '信用证创建成功',
                'data': serializer.data
            }, status=status.HTTP_201_CREATED)

        return Response({
            'code': 3002,
            'message': '参数格式错误',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, *args, **kwargs):
        """获取信用证详情"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({
            'code': 0,
            'message': 'success',
            'data': serializer.data
        })

    @action(detail=True, methods=['post'])
    def issue(self, request, pk=None):
        """银行开证 — pending_issue -> issued"""
        lc = self.get_object()
        role_check = self._check_bank_role(request)
        if role_check:
            return role_check

        if lc.status != 'pending_issue':
            return Response({
                'code': 5005,
                'message': '信用证状态不允许开证，当前状态: {}'.format(lc.get_status_display())
            }, status=status.HTTP_400_BAD_REQUEST)

        now = timezone.now()
        lc.status = 'issued'
        lc.issue_date = now.date()
        lc.issued_at = now
        lc.save()

        BankOperation.objects.create(
            lc=lc,
            operation_type='issue',
            processed_by='issuing_bank',
            operator=request.user,
            notes='信用证已开证',
            result={'status': 'issued'}
        )

        serializer = self.get_serializer(lc)
        return Response({
            'code': 0,
            'message': '信用证已开证',
            'data': serializer.data
        })

    @action(detail=True, methods=['post'])
    def advise(self, request, pk=None):
        """银行通知 — issued 状态"""
        lc = self.get_object()
        role_check = self._check_bank_role(request)
        if role_check:
            return role_check

        if lc.status != 'issued':
            return Response({
                'code': 5005,
                'message': '信用证状态不允许通知，当前状态: {}'.format(lc.get_status_display())
            }, status=status.HTTP_400_BAD_REQUEST)

        lc.advised_at = timezone.now()
        lc.save()

        BankOperation.objects.create(
            lc=lc,
            operation_type='advise',
            processed_by='advising_bank',
            operator=request.user,
            notes='信用证已通知',
            result={'status': lc.status}
        )

        serializer = self.get_serializer(lc)
        return Response({
            'code': 0,
            'message': '信用证已通知',
            'data': serializer.data
        })

    @action(detail=True, methods=['post'])
    def submit_docs(self, request, pk=None):
        """交单 — issued -> submitted，申请方或受益人可操作"""
        lc = self.get_object()
        access_check = self._check_applicant_or_beneficiary(request, lc)
        if access_check:
            return access_check

        if lc.status != 'issued':
            return Response({
                'code': 5005,
                'message': '信用证状态不允许交单，当前状态: {}'.format(lc.get_status_display())
            }, status=status.HTTP_400_BAD_REQUEST)

        lc.status = 'submitted'
        lc.submitted_at = timezone.now()
        lc.save()

        serializer = self.get_serializer(lc)
        return Response({
            'code': 0,
            'message': '交单成功',
            'data': serializer.data
        })

    @action(detail=True, methods=['post'])
    def negotiate(self, request, pk=None):
        """银行议付 — submitted -> negotiated"""
        lc = self.get_object()
        role_check = self._check_bank_role(request)
        if role_check:
            return role_check

        if lc.status != 'submitted':
            return Response({
                'code': 5005,
                'message': '信用证状态不允许议付，当前状态: {}'.format(lc.get_status_display())
            }, status=status.HTTP_400_BAD_REQUEST)

        lc.status = 'negotiated'
        lc.negotiated_at = timezone.now()
        lc.save()

        BankOperation.objects.create(
            lc=lc,
            operation_type='negotiate',
            processed_by='negotiating_bank',
            operator=request.user,
            notes='信用证已议付',
            result={'status': 'negotiated'}
        )

        serializer = self.get_serializer(lc)
        return Response({
            'code': 0,
            'message': '信用证已议付',
            'data': serializer.data
        })

    @action(detail=True, methods=['post'])
    def pay(self, request, pk=None):
        """银行付款 — negotiated -> paid"""
        lc = self.get_object()
        role_check = self._check_bank_role(request)
        if role_check:
            return role_check

        if lc.status != 'negotiated':
            return Response({
                'code': 5005,
                'message': '信用证状态不允许付款，当前状态: {}'.format(lc.get_status_display())
            }, status=status.HTTP_400_BAD_REQUEST)

        lc.status = 'paid'
        lc.paid_at = timezone.now()
        lc.save()

        BankOperation.objects.create(
            lc=lc,
            operation_type='pay',
            processed_by='issuing_bank',
            operator=request.user,
            notes='信用证已付款',
            result={'status': 'paid'}
        )

        serializer = self.get_serializer(lc)
        return Response({
            'code': 0,
            'message': '信用证已付款',
            'data': serializer.data
        })

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """取消信用证 — draft/pending_issue -> cancelled，申请方或受益人可操作"""
        lc = self.get_object()
        access_check = self._check_applicant_or_beneficiary(request, lc)
        if access_check:
            return access_check

        if lc.status not in ('draft', 'pending_issue'):
            return Response({
                'code': 5005,
                'message': '信用证状态不允许取消，当前状态: {}'.format(lc.get_status_display())
            }, status=status.HTTP_400_BAD_REQUEST)

        lc.status = 'cancelled'
        lc.save()

        serializer = self.get_serializer(lc)
        return Response({
            'code': 0,
            'message': '信用证已取消',
            'data': serializer.data
        })

    # ------------------------------------------------------------------
    # Helper methods
    # ------------------------------------------------------------------

    def _check_bank_role(self, request):
        """Check that the current user has an active bank role.

        Returns a Response on failure, or None on success.
        """
        current_role = RoleService.get_current_role(request.user)
        if not current_role or not current_role.company:
            return Response({
                'code': 4001,
                'message': '请先激活一个角色'
            }, status=status.HTTP_400_BAD_REQUEST)

        if current_role.role.code != 'bank':
            return Response({
                'code': 4003,
                'message': '只有银行可以执行此操作'
            }, status=status.HTTP_400_BAD_REQUEST)

        return None

    def _check_applicant_or_beneficiary(self, request, lc):
        """Check that the current user's company is applicant or beneficiary.

        Returns a Response on failure, or None on success.
        """
        current_role = RoleService.get_current_role(request.user)
        if not current_role or not current_role.company:
            return Response({
                'code': 4001,
                'message': '请先激活一个角色'
            }, status=status.HTTP_400_BAD_REQUEST)

        company = current_role.company
        if company not in (lc.applicant, lc.beneficiary):
            return Response({
                'code': 4003,
                'message': '只有申请方或受益人可以执行此操作'
            }, status=status.HTTP_400_BAD_REQUEST)

        return None
