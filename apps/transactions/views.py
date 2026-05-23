from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from apps.transactions.models import Transaction, InquiryMessage, Contract, PurchaseOrder, Shipment, InsurancePolicy, CustomsDeclaration, InspectionApplication, ForexSettlement, TaxRefundApplication
from apps.transactions.serializers import (
    TransactionSerializer,
    InquiryMessageSerializer,
    ContractSerializer,
    PurchaseOrderSerializer,
    CreatePurchaseOrderSerializer,
    ShipmentSerializer,
    CreateShipmentSerializer,
    InsurancePolicySerializer,
    CreateInsurancePolicySerializer,
    CustomsDeclarationSerializer, CreateCustomsDeclarationSerializer,
    InspectionApplicationSerializer, CreateInspectionApplicationSerializer,
    ForexSettlementSerializer, CreateForexSettlementSerializer,
    TaxRefundApplicationSerializer, CreateTaxRefundApplicationSerializer
)
from apps.transactions.services import TransactionService, PurchaseOrderService, ShipmentService, InsuranceService, CustomsService, InspectionService, ForexService, TaxRefundService
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


class PurchaseOrderViewSet(viewsets.ModelViewSet):
    """采购订单视图集"""

    serializer_class = PurchaseOrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        current_role = RoleService.get_current_role(user)
        if not current_role or not current_role.company:
            return PurchaseOrder.objects.none()
        company = current_role.company
        return PurchaseOrder.objects.filter(
            buyer=company
        ) | PurchaseOrder.objects.filter(
            seller=company
        )

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({'code': 0, 'message': 'success', 'data': serializer.data})

    def create(self, request, *args, **kwargs):
        serializer = CreatePurchaseOrderSerializer(data=request.data)
        if serializer.is_valid():
            try:
                po = PurchaseOrderService.create_order(user=request.user, **serializer.validated_data)
                result_serializer = PurchaseOrderSerializer(po)
                return Response({
                    'code': 0, 'message': '采购订单创建成功', 'data': result_serializer.data
                }, status=status.HTTP_201_CREATED)
            except Exception as e:
                return Response({'code': 5005, 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({
            'code': 3002, 'message': '参数格式错误', 'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({'code': 0, 'message': 'success', 'data': serializer.data})

    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        po = self.get_object()
        try:
            result = PurchaseOrderService.confirm(po.id, request.user)
            return Response({'code': 0, 'message': '订单已确认', 'data': PurchaseOrderSerializer(result).data})
        except Exception as e:
            return Response({'code': 5005, 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def ship(self, request, pk=None):
        po = self.get_object()
        try:
            tracking_info = request.data.get('tracking_info', '')
            result = PurchaseOrderService.ship(po.id, request.user, tracking_info)
            return Response({'code': 0, 'message': '已发货', 'data': PurchaseOrderSerializer(result).data})
        except Exception as e:
            return Response({'code': 5005, 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def invoice(self, request, pk=None):
        po = self.get_object()
        try:
            result = PurchaseOrderService.invoice(po.id, request.user)
            return Response({'code': 0, 'message': '已开票', 'data': PurchaseOrderSerializer(result).data})
        except Exception as e:
            return Response({'code': 5005, 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        po = self.get_object()
        try:
            result = PurchaseOrderService.complete(po.id, request.user)
            return Response({'code': 0, 'message': '已确认收货', 'data': PurchaseOrderSerializer(result).data})
        except Exception as e:
            return Response({'code': 5005, 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        po = self.get_object()
        try:
            reason = request.data.get('reason', '')
            result = PurchaseOrderService.cancel(po.id, request.user, reason)
            return Response({'code': 0, 'message': '订单已取消', 'data': PurchaseOrderSerializer(result).data})
        except Exception as e:
            return Response({'code': 5005, 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ShipmentViewSet(viewsets.ModelViewSet):
    serializer_class = ShipmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        current_role = RoleService.get_current_role(user)
        if not current_role or not current_role.company:
            return Shipment.objects.none()
        company = current_role.company
        return Shipment.objects.filter(shipper=company) | Shipment.objects.filter(carrier=company)

    def list(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_queryset(), many=True)
        return Response({'code': 0, 'message': 'success', 'data': serializer.data})

    def create(self, request, *args, **kwargs):
        serializer = CreateShipmentSerializer(data=request.data)
        if serializer.is_valid():
            try:
                shipment = ShipmentService.create_shipment(user=request.user, **serializer.validated_data)
                return Response({
                    'code': 0, 'message': '货运订单创建成功',
                    'data': ShipmentSerializer(shipment).data
                }, status=status.HTTP_201_CREATED)
            except Exception as e:
                return Response({'code': 5005, 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'code': 3002, 'message': '参数格式错误', 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, *args, **kwargs):
        return Response({'code': 0, 'message': 'success', 'data': self.get_serializer(self.get_object()).data})

    @action(detail=True, methods=['post'])
    def book(self, request, pk=None):
        try:
            result = ShipmentService.book(
                self.get_object().id, request.user,
                booking_no=request.data['booking_no'],
                vessel_name=request.data['vessel_name'],
                etd=request.data.get('etd'),
                eta=request.data.get('eta')
            )
            return Response({'code': 0, 'message': '订舱成功', 'data': ShipmentSerializer(result).data})
        except Exception as e:
            return Response({'code': 5005, 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def load(self, request, pk=None):
        try:
            result = ShipmentService.load(
                self.get_object().id, request.user,
                container_no=request.data.get('container_no', '')
            )
            return Response({'code': 0, 'message': '装船确认', 'data': ShipmentSerializer(result).data})
        except Exception as e:
            return Response({'code': 5005, 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def issue_bl(self, request, pk=None):
        try:
            result = ShipmentService.issue_bl(
                self.get_object().id, request.user,
                bl_no=request.data['bl_no']
            )
            return Response({'code': 0, 'message': '提单已签发', 'data': ShipmentSerializer(result).data})
        except Exception as e:
            return Response({'code': 5005, 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def arrive(self, request, pk=None):
        try:
            result = ShipmentService.arrive(self.get_object().id, request.user)
            return Response({'code': 0, 'message': '已确认到港', 'data': ShipmentSerializer(result).data})
        except Exception as e:
            return Response({'code': 5005, 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        try:
            result = ShipmentService.cancel(
                self.get_object().id, request.user,
                reason=request.data.get('reason', '')
            )
            return Response({'code': 0, 'message': '已取消', 'data': ShipmentSerializer(result).data})
        except Exception as e:
            return Response({'code': 5005, 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class InsurancePolicyViewSet(viewsets.ModelViewSet):
    serializer_class = InsurancePolicySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        current_role = RoleService.get_current_role(user)
        if not current_role or not current_role.company:
            return InsurancePolicy.objects.none()
        company = current_role.company
        return InsurancePolicy.objects.filter(insured=company) | InsurancePolicy.objects.filter(insurer=company)

    def list(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_queryset(), many=True)
        return Response({'code': 0, 'message': 'success', 'data': serializer.data})

    def create(self, request, *args, **kwargs):
        serializer = CreateInsurancePolicySerializer(data=request.data)
        if serializer.is_valid():
            try:
                policy = InsuranceService.create_policy(user=request.user, **serializer.validated_data)
                return Response({
                    'code': 0, 'message': '投保成功',
                    'data': InsurancePolicySerializer(policy).data
                }, status=status.HTTP_201_CREATED)
            except Exception as e:
                return Response({'code': 5005, 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'code': 3002, 'message': '参数格式错误', 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, *args, **kwargs):
        return Response({'code': 0, 'message': 'success', 'data': self.get_serializer(self.get_object()).data})

    @action(detail=True, methods=['post'])
    def underwrite(self, request, pk=None):
        try:
            result = InsuranceService.underwrite(self.get_object().id, request.user)
            return Response({'code': 0, 'message': '承保成功', 'data': InsurancePolicySerializer(result).data})
        except Exception as e:
            return Response({'code': 5005, 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def issue(self, request, pk=None):
        try:
            result = InsuranceService.issue(self.get_object().id, request.user)
            return Response({'code': 0, 'message': '保单已签发', 'data': InsurancePolicySerializer(result).data})
        except Exception as e:
            return Response({'code': 5005, 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        try:
            result = InsuranceService.cancel(
                self.get_object().id, request.user,
                reason=request.data.get('reason', '')
            )
            return Response({'code': 0, 'message': '已取消', 'data': InsurancePolicySerializer(result).data})
        except Exception as e:
            return Response({'code': 5005, 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class CustomsDeclarationViewSet(viewsets.ModelViewSet):
    serializer_class = CustomsDeclarationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        current_role = RoleService.get_current_role(user)
        if not current_role or not current_role.company:
            return CustomsDeclaration.objects.none()
        company = current_role.company
        return CustomsDeclaration.objects.filter(declarant=company) | CustomsDeclaration.objects.filter(customs_office=company)

    def list(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_queryset(), many=True)
        return Response({'code': 0, 'message': 'success', 'data': serializer.data})

    def create(self, request, *args, **kwargs):
        serializer = CreateCustomsDeclarationSerializer(data=request.data)
        if serializer.is_valid():
            try:
                decl = CustomsService.create_declaration(user=request.user, **serializer.validated_data)
                return Response({
                    'code': 0, 'message': '报关申报成功',
                    'data': CustomsDeclarationSerializer(decl).data
                }, status=status.HTTP_201_CREATED)
            except Exception as e:
                return Response({'code': 5005, 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'code': 3002, 'message': '参数格式错误', 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, *args, **kwargs):
        return Response({'code': 0, 'message': 'success', 'data': self.get_serializer(self.get_object()).data})

    @action(detail=True, methods=['post'])
    def review(self, request, pk=None):
        try:
            result = CustomsService.review(self.get_object().id, request.user)
            return Response({'code': 0, 'message': '审核中', 'data': CustomsDeclarationSerializer(result).data})
        except Exception as e:
            return Response({'code': 5005, 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def assess(self, request, pk=None):
        try:
            result = CustomsService.assess(self.get_object().id, request.user)
            return Response({'code': 0, 'message': '征税完成', 'data': CustomsDeclarationSerializer(result).data})
        except Exception as e:
            return Response({'code': 5005, 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def clear(self, request, pk=None):
        try:
            result = CustomsService.clear(self.get_object().id, request.user)
            return Response({'code': 0, 'message': '已放行', 'data': CustomsDeclarationSerializer(result).data})
        except Exception as e:
            return Response({'code': 5005, 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        try:
            result = CustomsService.reject(
                self.get_object().id, request.user,
                reason=request.data.get('reason', '')
            )
            return Response({'code': 0, 'message': '已退单', 'data': CustomsDeclarationSerializer(result).data})
        except Exception as e:
            return Response({'code': 5005, 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class InspectionApplicationViewSet(viewsets.ModelViewSet):
    serializer_class = InspectionApplicationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        current_role = RoleService.get_current_role(user)
        if not current_role or not current_role.company:
            return InspectionApplication.objects.none()
        company = current_role.company
        return InspectionApplication.objects.filter(applicant=company) | InspectionApplication.objects.filter(inspector=company)

    def list(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_queryset(), many=True)
        return Response({'code': 0, 'message': 'success', 'data': serializer.data})

    def create(self, request, *args, **kwargs):
        serializer = CreateInspectionApplicationSerializer(data=request.data)
        if serializer.is_valid():
            try:
                app = InspectionService.create_application(user=request.user, **serializer.validated_data)
                return Response({
                    'code': 0, 'message': '报检成功',
                    'data': InspectionApplicationSerializer(app).data
                }, status=status.HTTP_201_CREATED)
            except Exception as e:
                return Response({'code': 5005, 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'code': 3002, 'message': '参数格式错误', 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, *args, **kwargs):
        return Response({'code': 0, 'message': 'success', 'data': self.get_serializer(self.get_object()).data})

    @action(detail=True, methods=['post'])
    def inspect(self, request, pk=None):
        try:
            result = InspectionService.inspect(self.get_object().id, request.user)
            return Response({'code': 0, 'message': '开始检验', 'data': InspectionApplicationSerializer(result).data})
        except Exception as e:
            return Response({'code': 5005, 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def pass_inspection(self, request, pk=None):
        try:
            result = InspectionService.pass_inspection(self.get_object().id, request.user)
            return Response({'code': 0, 'message': '检验合格', 'data': InspectionApplicationSerializer(result).data})
        except Exception as e:
            return Response({'code': 5005, 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def certify(self, request, pk=None):
        try:
            result = InspectionService.certify(
                self.get_object().id, request.user,
                certificate_no=request.data['certificate_no'],
                origin_certificate_no=request.data.get('origin_certificate_no', '')
            )
            return Response({'code': 0, 'message': '证书已签发', 'data': InspectionApplicationSerializer(result).data})
        except Exception as e:
            return Response({'code': 5005, 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def fail(self, request, pk=None):
        try:
            result = InspectionService.fail_inspection(
                self.get_object().id, request.user,
                reason=request.data.get('reason', '')
            )
            return Response({'code': 0, 'message': '检验不合格', 'data': InspectionApplicationSerializer(result).data})
        except Exception as e:
            return Response({'code': 5005, 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ForexSettlementViewSet(viewsets.ModelViewSet):
    serializer_class = ForexSettlementSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        current_role = RoleService.get_current_role(user)
        if not current_role or not current_role.company:
            return ForexSettlement.objects.none()
        company = current_role.company
        return ForexSettlement.objects.filter(applicant=company) | ForexSettlement.objects.filter(forex_bureau=company)

    def list(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_queryset(), many=True)
        return Response({'code': 0, 'message': 'success', 'data': serializer.data})

    def create(self, request, *args, **kwargs):
        serializer = CreateForexSettlementSerializer(data=request.data)
        if serializer.is_valid():
            try:
                settlement = ForexService.create_settlement(user=request.user, **serializer.validated_data)
                return Response({
                    'code': 0, 'message': '外汇核销申请成功',
                    'data': ForexSettlementSerializer(settlement).data
                }, status=status.HTTP_201_CREATED)
            except Exception as e:
                return Response({'code': 5005, 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'code': 3002, 'message': '参数格式错误', 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, *args, **kwargs):
        return Response({'code': 0, 'message': 'success', 'data': self.get_serializer(self.get_object()).data})

    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        try:
            result = ForexService.verify(self.get_object().id, request.user)
            return Response({'code': 0, 'message': '核销成功', 'data': ForexSettlementSerializer(result).data})
        except Exception as e:
            return Response({'code': 5005, 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def settle(self, request, pk=None):
        try:
            result = ForexService.settle(self.get_object().id, request.user)
            return Response({'code': 0, 'message': '结汇成功', 'data': ForexSettlementSerializer(result).data})
        except Exception as e:
            return Response({'code': 5005, 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        try:
            result = ForexService.reject(
                self.get_object().id, request.user,
                reason=request.data.get('reason', '')
            )
            return Response({'code': 0, 'message': '已拒绝', 'data': ForexSettlementSerializer(result).data})
        except Exception as e:
            return Response({'code': 5005, 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class TaxRefundApplicationViewSet(viewsets.ModelViewSet):
    serializer_class = TaxRefundApplicationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        current_role = RoleService.get_current_role(user)
        if not current_role or not current_role.company:
            return TaxRefundApplication.objects.none()
        company = current_role.company
        return TaxRefundApplication.objects.filter(applicant=company) | TaxRefundApplication.objects.filter(tax_bureau=company)

    def list(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_queryset(), many=True)
        return Response({'code': 0, 'message': 'success', 'data': serializer.data})

    def create(self, request, *args, **kwargs):
        serializer = CreateTaxRefundApplicationSerializer(data=request.data)
        if serializer.is_valid():
            try:
                app = TaxRefundService.create_application(user=request.user, **serializer.validated_data)
                return Response({
                    'code': 0, 'message': '退税申请成功',
                    'data': TaxRefundApplicationSerializer(app).data
                }, status=status.HTTP_201_CREATED)
            except Exception as e:
                return Response({'code': 5005, 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'code': 3002, 'message': '参数格式错误', 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, *args, **kwargs):
        return Response({'code': 0, 'message': 'success', 'data': self.get_serializer(self.get_object()).data})

    @action(detail=True, methods=['post'])
    def review(self, request, pk=None):
        try:
            result = TaxRefundService.review(self.get_object().id, request.user)
            return Response({'code': 0, 'message': '审核中', 'data': TaxRefundApplicationSerializer(result).data})
        except Exception as e:
            return Response({'code': 5005, 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        try:
            result = TaxRefundService.approve(self.get_object().id, request.user)
            return Response({'code': 0, 'message': '已批准', 'data': TaxRefundApplicationSerializer(result).data})
        except Exception as e:
            return Response({'code': 5005, 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def refund(self, request, pk=None):
        try:
            result = TaxRefundService.refund(self.get_object().id, request.user)
            return Response({'code': 0, 'message': '已退税', 'data': TaxRefundApplicationSerializer(result).data})
        except Exception as e:
            return Response({'code': 5005, 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        try:
            result = TaxRefundService.reject(
                self.get_object().id, request.user,
                reason=request.data.get('reason', '')
            )
            return Response({'code': 0, 'message': '已拒绝', 'data': TaxRefundApplicationSerializer(result).data})
        except Exception as e:
            return Response({'code': 5005, 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)
