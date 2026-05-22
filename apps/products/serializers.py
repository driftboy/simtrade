from rest_framework import serializers
from apps.products.models import Product, Catalog


class ProductSerializer(serializers.ModelSerializer):
    """商品序列化器"""

    category_display = serializers.CharField(source='get_category_display', read_only=True)

    class Meta:
        model = Product
        fields = ['id', 'code', 'name', 'name_en', 'category', 'category_display',
                  'unit', 'description', 'hs_code', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']


class CatalogSerializer(serializers.ModelSerializer):
    """商品目录序列化器"""

    product_detail = ProductSerializer(source='product', read_only=True)

    class Meta:
        model = Catalog
        fields = ['id', 'product', 'product_detail', 'sale_price', 'currency',
                  'min_order', 'max_order', 'lead_time', 'is_available', 'created_at']
        read_only_fields = ['id', 'created_at']
