"""
Tests for Document pagination functionality.
"""
from django.test import TestCase
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

from apps.documents.models import Document, DocumentTemplate

User = get_user_model()


class DocumentPaginationTestCase(TestCase):
    """测试单证分页功能"""

    def setUp(self):
        """创建测试数据"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass',
            user_type='student'
        )
        self.template = DocumentTemplate.objects.create(
            code='test_invoice',
            name='测试发票',
            content='<html></html>'
        )

        # 创建 15 条单证记录
        for i in range(15):
            Document.objects.create(
                template=self.template,
                created_by=self.user,
                status='draft'
            )

        self.client.force_authenticate(user=self.user)

    def test_default_page_size(self):
        """测试默认每页 5 条"""
        response = self.client.get('/api/v1/documents/documents/')
        self.assertEqual(response.status_code, 200)
        # 检查分页信息
        data = response.json()
        self.assertEqual(data['count'], 15)
        self.assertEqual(len(data['results']), 5)

    def test_custom_page_size(self):
        """测试自定义每页条数"""
        response = self.client.get(
            '/api/v1/documents/documents/?page_size=10'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['results']), 10)
        self.assertEqual(data['count'], 15)

    def test_page_navigation(self):
        """测试翻页功能"""
        # 第一页
        response = self.client.get('/api/v1/documents/documents/?page=1')
        self.assertEqual(len(response.json()['results']), 5)

        # 第二页
        response = self.client.get('/api/v1/documents/documents/?page=2')
        self.assertEqual(len(response.json()['results']), 5)

        # 第三页（剩余 5 条）
        response = self.client.get('/api/v1/documents/documents/?page=3')
        self.assertEqual(len(response.json()['results']), 5)

    def test_next_previous_urls(self):
        """测试 next 和 previous URL"""
        response = self.client.get('/api/v1/documents/documents/')
        data = response.json()
        self.assertIsNone(data['previous'])
        self.assertIsNotNone(data['next'])

    def test_max_page_size_limit(self):
        """测试最大每页条数限制"""
        # 创建更多数据（超过 max_page_size=50）
        for i in range(50):
            Document.objects.create(
                template=self.template,
                created_by=self.user,
                status='draft'
            )

        # 现在有 65 条数据，请求 100 条应被限制为 50
        response = self.client.get(
            '/api/v1/documents/documents/?page_size=100'
        )
        data = response.json()
        self.assertEqual(data['count'], 65)
        # DRF 会限制为 max_page_size
        self.assertEqual(len(data['results']), 50)
