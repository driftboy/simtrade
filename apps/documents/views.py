"""
API views for Document management.
"""
import json
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from apps.documents.models import Document, DocumentTemplate
from apps.documents.pagination import DocumentPagination
from apps.documents.serializers import (
    DocumentSerializer, DocumentCreateSerializer,
    DocumentTemplateSerializer, DocumentSubmitSerializer
)
from apps.documents.services import DependencyService, DataFillService
from apps.documents.validators import DocumentValidator
from apps.teaching.models import StudentEnrollment


class DocumentViewSet(ModelViewSet):
    """单证视图集"""
    permission_classes = [IsAuthenticated]
    pagination_class = DocumentPagination

    def get_serializer_class(self):
        if self.action == 'create':
            return DocumentCreateSerializer
        return DocumentSerializer

    def get_queryset(self):
        user = self.request.user
        transaction_id = self.request.query_params.get('transaction_id')
        teaching_class_id = self.request.query_params.get('teaching_class_id')

        if user.user_type == 'admin':
            queryset = Document.objects.all()
        elif user.user_type == 'teacher':
            queryset = Document.objects.filter(
                teaching_class__course__teachers=user
            )
        else:
            queryset = Document.objects.filter(created_by=user)

        if transaction_id:
            queryset = queryset.filter(transaction_id=transaction_id)
        if teaching_class_id:
            queryset = queryset.filter(teaching_class_id=teaching_class_id)

        return queryset.select_related(
            'template', 'created_by', 'reviewed_by', 'teaching_class'
        )

    def retrieve(self, request, *args, **kwargs):
        """获取单证详情"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({
            'code': 0,
            'message': 'success',
            'data': serializer.data
        })

    def create(self, request, *args, **kwargs):
        """创建单证"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        template = serializer.validated_data['template']

        # 检查依赖
        dep_service = DependencyService(user)
        can_create, message = dep_service.can_create(template.code)

        if not can_create:
            return Response({
                'code': 5001,
                'message': message
            }, status=status.HTTP_400_BAD_REQUEST)

        # 智能数据填充
        fill_service = DataFillService()
        defaults = fill_service.fill_defaults(template.code)

        # 合并用户数据和默认值
        user_data = serializer.validated_data.get('data', '{}')
        if isinstance(user_data, str):
            user_data = json.loads(user_data) if user_data else {}
        merged_data = {**defaults, **user_data}

        # 自动填入 teaching_class（学生）
        teaching_class = None
        if user.user_type == 'student':
            enrollment = StudentEnrollment.objects.filter(
                student=user,
                status='enrolled',
            ).select_related('teaching_class').first()
            if enrollment:
                teaching_class = enrollment.teaching_class

        # 保存单证
        document = Document.objects.create(
            template=template,
            created_by=user,
            teaching_class=teaching_class,
            data=json.dumps(merged_data, ensure_ascii=False)
        )

        serializer = DocumentSerializer(document)
        return Response({
            'code': 0,
            'message': '创建成功',
            'data': serializer.data
        }, status=status.HTTP_200_OK)

    def update(self, request, *args, **kwargs):
        """更新单证"""
        instance = self.get_object()

        # 处理 data 字段 - 可能是 dict 或字符串
        update_data = request.data.copy() if hasattr(request.data, 'copy') else request.data
        data = update_data.get('data')
        if isinstance(data, dict):
            update_data['data'] = json.dumps(data, ensure_ascii=False)

        serializer = self.get_serializer(instance, data=update_data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({
            'code': 0,
            'message': '更新成功',
            'data': serializer.data
        })

    def destroy(self, request, *args, **kwargs):
        """删除单证"""
        instance = self.get_object()
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def template_list(request):
    """获取单证模板列表"""
    templates = DocumentTemplate.objects.filter(is_active=True)
    serializer = DocumentTemplateSerializer(templates, many=True)

    # 获取可创建的单证类型
    dep_service = DependencyService(request.user)
    available = dep_service.get_next_available()
    available_codes = {t['code'] for t in available}

    # 标记是否可创建
    data = []
    for t in serializer.data:
        t['can_create'] = t['code'] in available_codes
        data.append(t)

    return Response({
        'code': 0,
        'message': 'success',
        'data': data
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_document(request, pk):
    """提交单证审核"""
    try:
        document = Document.objects.get(pk=pk, created_by=request.user)
    except Document.DoesNotExist:
        return Response({
            'code': 4001,
            'message': '单证不存在'
        }, status=status.HTTP_404_NOT_FOUND)

    if document.status != Document.Status.DRAFT:
        return Response({
            'code': 4004,
            'message': '只有草稿状态的单证可以提交'
        }, status=status.HTTP_400_BAD_REQUEST)

    # 执行自动校验
    validator = DocumentValidator(document)
    validation_results = validator.save_results()

    # 检查是否所有自动校验都通过
    all_passed = validation_results.get('all_passed', True)

    if all_passed:
        document.status = Document.Status.PENDING_REVIEW
        document.submitted_at = timezone.now()
        document.save()

        return Response({
            'code': 0,
            'message': '提交成功，等待人工审核',
            'data': DocumentSerializer(document).data
        })
    else:
        # 校验不通过，返回错误信息
        errors = []
        details = validation_results.get('details', {})
        for rule_name, result in details.items():
            if not result.get('passed', True):
                errors.extend(result.get('errors', []))

        return Response({
            'code': 5002,
            'message': '单证校验不通过',
            'errors': errors,
            'validation_results': validation_results
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def approve_document(request, pk):
    """审核通过单证（教师）"""
    if not request.user.is_staff:
        return Response({
            'code': 2001,
            'message': '无权限操作'
        }, status=status.HTTP_403_FORBIDDEN)

    try:
        document = Document.objects.get(pk=pk)
    except Document.DoesNotExist:
        return Response({
            'code': 4001,
            'message': '单证不存在'
        }, status=status.HTTP_404_NOT_FOUND)

    if document.status != Document.Status.PENDING_REVIEW:
        return Response({
            'code': 4004,
            'message': '单证状态不允许此操作'
        }, status=status.HTTP_400_BAD_REQUEST)

    document.status = Document.Status.APPROVED
    document.reviewed_by = request.user
    document.reviewed_at = timezone.now()
    document.manual_review_status = 'approved'
    document.save()

    return Response({
        'code': 0,
        'message': '审核通过',
        'data': DocumentSerializer(document).data
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reject_document(request, pk):
    """审核驳回单证（教师）"""
    if not request.user.is_staff:
        return Response({
            'code': 2001,
            'message': '无权限操作'
        }, status=status.HTTP_403_FORBIDDEN)

    try:
        document = Document.objects.get(pk=pk)
    except Document.DoesNotExist:
        return Response({
            'code': 4001,
            'message': '单证不存在'
        }, status=status.HTTP_404_NOT_FOUND)

    if document.status != Document.Status.PENDING_REVIEW:
        return Response({
            'code': 4004,
            'message': '单证状态不允许此操作'
        }, status=status.HTTP_400_BAD_REQUEST)

    # 获取审核意见 - DRF 已解析 request.data
    comment = request.data.get('comment', '') if hasattr(request, 'data') else ''

    document.status = Document.Status.REJECTED
    document.reviewed_by = request.user
    document.reviewed_at = timezone.now()
    document.manual_review_status = 'rejected'
    document.manual_review_comment = comment
    document.save()

    return Response({
        'code': 0,
        'message': '审核驳回',
        'data': DocumentSerializer(document).data
    })
