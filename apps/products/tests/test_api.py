import pytest
from rest_framework.test import APITestCase, APIClient
from django.urls import reverse
from apps.products.models import Product
from apps.users.models import User


class ProductAPITest(APITestCase):
    """测试商品 API"""

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.product = Product.objects.create(
            code='ELEC001',
            name='电子产品 A',
            category='electronics',
            unit='PCS'
        )

    def test_list_products(self):
        """测试获取商品列表"""
        url = reverse('products:product-list')
        response = self.client.get(url)
        assert response.status_code == 200
        assert response.json()['code'] == 0
        assert len(response.json()['data']) >= 1

    def test_retrieve_product(self):
        """测试获取商品详情"""
        url = reverse('products:product-detail', kwargs={'pk': self.product.pk})
        response = self.client.get(url)
        assert response.status_code == 200
        assert response.json()['data']['code'] == 'ELEC001'
