import pytest
from django.test import TestCase
from django.db import IntegrityError
from apps.products.models import Product, Catalog
from apps.users.models import User


class ProductModelTest(TestCase):
    """测试商品模型"""

    def test_create_product(self):
        """测试创建商品"""
        product = Product.objects.create(
            code='ELEC001',
            name='电子产品 A',
            category='electronics',
            unit='PCS'
        )
        assert product.code == 'ELEC001'
        assert product.name == '电子产品 A'
        assert product.get_category_display() == '电子产品'

    def test_product_code_unique(self):
        """测试商品代码唯一性"""
        Product.objects.create(code='ELEC001', name='商品A', category='electronics', unit='PCS')
        with pytest.raises(IntegrityError):
            Product.objects.create(code='ELEC001', name='商品B', category='electronics', unit='PCS')


class CatalogModelTest(TestCase):
    """测试商品目录模型"""

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')

    def test_create_catalog_entry(self):
        """测试创建目录条目"""
        product = Product.objects.create(
            code='ELEC001',
            name='电子产品 A',
            category='electronics',
            unit='PCS'
        )
        # 注意：Company 模型尚未实现，Catalog 暂时只关联 product
        # 等 Company 实现后需要更新此测试
        catalog = Catalog.objects.create(
            product=product,
            sale_price=10.00
        )
        assert catalog.product == product
        assert catalog.sale_price == 10.00
