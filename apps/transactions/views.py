from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from apps.transactions.models import Transaction, InquiryMessage, Contract
from apps.transactions.serializers import (
    TransactionSerializer,
    InquiryMessageSerializer,
    ContractSerializer
)
from apps.transactions.services import TransactionService
from apps.roles.services import RoleService
from apps.roles.models import Company


class TransactionViewSet(viewsets.ModelViewSet):
    """交易视图集"""

    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """只返回当前用户所属公司参与的交易"""
        user = self.request.user
        current_role = RoleService.get_current_role(user)

        if not current_role or not current_role.company:
            # 没有激活角色时，返回空查询集
            return Transaction.objects.none()

        company = current_role.company
        return Transaction.objects.filter(
            buyer=company
        ) | Transaction.objects.filter(
            seller=company
        )

    def list(self, request, *args, **kwargs):
        """获取交易列表"""
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'code': 0,
            'message': 'success',
            'data': serializer.data
        })

    def create(self, request, *args, **kwargs):
        """创建交易（询盘）"""
        # 获取当前激活角色的公司作为买方
        current_role = RoleService.get_current_role(request.user)

        if not current_role or not current_role.company:
            return Response({
                'code': 4001,
                'message': '请先激活一个角色'
            }, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save(
                buyer=current_role.company,
                created_by=request.user,
                status='inquiring'
            )
            # 记录日志
            TransactionService.log_transaction(
                serializer.instance,
                request.user,
                'transaction_created',
                {'method': 'api'}
            )
            return Response({
                'code': 0,
                'message': '交易创建成功',
                'data': serializer.data
            }, status=status.HTTP_201_CREATED)
        return Response({
            'code': 3002,
            'message': '参数格式错误',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, *args, **kwargs):
        """获取交易详情"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({
            'code': 0,
            'message': 'success',
            'data': serializer.data
        })

    @action(detail=True, methods=['get'])
    def messages(self, request, pk=None):
        """获取交易消息列表"""
        transaction = self.get_object()
        messages = transaction.messages.all()
        serializer = InquiryMessageSerializer(messages, many=True)
        return Response({
            'code': 0,
            'message': 'success',
            'data': serializer.data
        })

    @action(detail=True, methods=['post'])
    def send_message(self, request, pk=None):
        """发送磋商消息"""
        transaction = self.get_object()
        serializer = InquiryMessageSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(
                transaction=transaction,
                sender=request.user,
                sender_role=self._get_user_role(transaction, request.user)
            )
            # 更新交易状态
            TransactionService.handle_message(transaction, serializer.instance)
            return Response({
                'code': 0,
                'message': '消息发送成功',
                'data': serializer.data
            })
        return Response({
            'code': 3002,
            'message': '参数格式错误',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """取消交易"""
        transaction = self.get_object()
        if transaction.status in ['completed', 'cancelled']:
            return Response({
                'code': 5005,
                'message': '交易状态不允许取消'
            }, status=status.HTTP_400_BAD_REQUEST)

        transaction.status = 'cancelled'
        transaction.save()
        TransactionService.log_transaction(
            transaction,
            request.user,
            'transaction_cancelled',
            {}
        )
        return Response({
            'code': 0,
            'message': '交易已取消'
        })

    def _get_user_role(self, transaction, user):
        """获取用户在交易中的角色（基于用户所属公司）"""
        current_role = RoleService.get_current_role(user)

        if not current_role or not current_role.company:
            return 'observer'

        company = current_role.company

        if transaction.buyer == company:
            return 'buyer'
        elif transaction.seller == company:
            return 'seller'
        return 'observer'


class ContractViewSet(viewsets.ModelViewSet):
    """合同视图集"""

    serializer_class = ContractSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Contract.objects.all()

    @action(detail=True, methods=['post'])
    def sign(self, request, pk=None):
        """签署合同"""
        contract = self.get_object()
        # TODO: 实现签字逻辑
        return Response({
            'code': 0,
            'message': '签字成功'
        })
