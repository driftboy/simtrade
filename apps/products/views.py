from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from apps.products.models import Product, Catalog, HSCode
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


class MarketCategoriesView(viewsets.ViewSet):
    """市场分类 — 按 HS 章节聚合商品"""
    permission_classes = [IsAuthenticated]

    def list(self, request):
        from apps.products.management.commands.sync_hs_codes import CHAPTER_NAMES

        products = Product.objects.filter(is_active=True)
        chapter = request.query_params.get('chapter', '').strip()
        search = request.query_params.get('search', '').strip()

        if chapter:
            products = products.filter(hs_code__startswith=chapter)
        if search:
            products = products.filter(name__icontains=search) | products.filter(
                hs_code__icontains=search
            )

        # 按 HS 章节分组
        hs_codes_cache = {}
        for hsc in HSCode.objects.all():
            hs_codes_cache[hsc.code] = hsc

        def _find_hscode(code):
            """精确匹配，失败则渐进前缀匹配（8位→6位→4位）"""
            if code in hs_codes_cache:
                return hs_codes_cache[code]
            for prefix_len in (8, 6, 4):
                prefix = code[:prefix_len]
                if len(prefix) < prefix_len:
                    continue
                for hsc_code, hsc in hs_codes_cache.items():
                    if hsc_code.startswith(prefix):
                        return hsc
            return None

        chapters = {}
        for p in products:
            ch = p.hs_code[:2] if p.hs_code else ''
            if not ch:
                continue
            if ch not in chapters:
                chapters[ch] = {
                    'chapter': ch,
                    'name': CHAPTER_NAMES.get(ch, ''),
                    'products': [],
                }
            hsc = _find_hscode(p.hs_code)
            chapters[ch]['products'].append({
                'id': p.id,
                'code': p.code,
                'name': p.name,
                'name_en': p.name_en,
                'hs_code': p.hs_code,
                'unit': p.unit,
                'category': p.category,
                'description': p.description,
                'export_rate': hsc.export_rate if hsc else '',
                'rebate_rate': hsc.rebate_rate if hsc else '',
                'vat_rate': hsc.vat_rate if hsc else '',
                'mfn_rate': hsc.mfn_rate if hsc else '',
                'consumption_rate': hsc.consumption_rate if hsc else '',
            })

        # 补充无商品但有 HS 编码数据的章节
        if not chapter and not search:
            loaded_chapters = set(
                HSCode.objects.values_list('chapter', flat=True).distinct()
            )
            for ch in sorted(loaded_chapters):
                if ch not in chapters:
                    chapters[ch] = {
                        'chapter': ch,
                        'name': CHAPTER_NAMES.get(ch, ''),
                        'products': [],
                    }

        data = sorted(chapters.values(), key=lambda x: x['chapter'])
        return Response({'code': 0, 'data': data})
