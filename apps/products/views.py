from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from apps.products.models import Product, Catalog
from apps.products.serializers import ProductSerializer, CatalogSerializer


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    """商品只读视图集"""

    queryset = Product.objects.filter(is_active=True)
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]

    def list(self, request, *args, **kwargs):
        """获取商品列表"""
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'code': 0,
            'message': 'success',
            'data': serializer.data
        })

    def retrieve(self, request, *args, **kwargs):
        """获取商品详情"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({
            'code': 0,
            'message': 'success',
            'data': serializer.data
        })


class CatalogViewSet(viewsets.ModelViewSet):
    """商品目录视图集"""

    serializer_class = CatalogSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # TODO: 过滤当前用户的公司的目录
        return Catalog.objects.filter(is_available=True)

    def list(self, request, *args, **kwargs):
        """获取目录列表"""
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'code': 0,
            'message': 'success',
            'data': serializer.data
        })

    def create(self, request, *args, **kwargs):
        """添加商品到目录"""
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'code': 0,
                'message': '添加成功',
                'data': serializer.data
            }, status=status.HTTP_201_CREATED)
        return Response({
            'code': 3002,
            'message': '参数格式错误',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
