"""
Tests for User preferences functionality.
"""
from django.test import TestCase
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

User = get_user_model()


class UserPreferencesTestCase(TestCase):
    """测试用户偏好设置功能"""

    def setUp(self):
        """创建测试数据"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass'
        )
        self.client.force_authenticate(user=self.user)

    def test_default_documents_per_page(self):
        """测试默认每页条数为 5"""
        self.assertEqual(self.user.documents_per_page, 5)

    def test_update_valid_preference(self):
        """测试更新有效偏好值"""
        response = self.client.put(
            '/api/v1/auth/me/',
            data={'documents_per_page': 10},
            format='json'
        )
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.documents_per_page, 10)

    def test_update_invalid_preference(self):
        """测试更新无效偏好值"""
        response = self.client.put(
            '/api/v1/auth/me/',
            data={'documents_per_page': 15},
            format='json'
        )
        self.assertEqual(response.status_code, 400)

    def test_preference_range_validation(self):
        """测试偏好值范围验证"""
        # 最小值测试
        response = self.client.put(
            '/api/v1/auth/me/',
            data={'documents_per_page': 3},
            format='json'
        )
        self.assertEqual(response.status_code, 400)

        # 最大值测试
        response = self.client.put(
            '/api/v1/auth/me/',
            data={'documents_per_page': 100},
            format='json'
        )
        self.assertEqual(response.status_code, 400)
