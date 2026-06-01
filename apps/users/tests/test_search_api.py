# apps/users/tests/test_search_api.py
import pytest
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from apps.teaching.models import StudentProfile

User = get_user_model()


@pytest.mark.django_db
class TestUserSearchAPI:
    @pytest.fixture
    def api_client(self):
        return APIClient()

    @pytest.fixture
    def teacher(self):
        return User.objects.create_user(username='teacher', user_type='teacher')

    @pytest.fixture
    def student_with_profile(self):
        student = User.objects.create_user(
            username='张三', email='zhangsan@example.com', user_type='student',
        )
        StudentProfile.objects.create(
            user=student, student_id='2024001', admin_class='计算机1班',
        )
        return student

    def test_search_by_student_id(self, api_client, teacher, student_with_profile):
        """测试按学号搜索"""
        api_client.force_authenticate(user=teacher)
        response = api_client.get('/api/v1/search/', {'q': '2024001'})

        assert response.status_code == 200
        data = response.json()
        assert data['code'] == 0
        assert len(data['data']) == 1
        assert data['data'][0]['student_id'] == '2024001'

    def test_search_by_username(self, api_client, teacher, student_with_profile):
        """测试按姓名搜索"""
        api_client.force_authenticate(user=teacher)
        response = api_client.get('/api/v1/search/', {'q': '张三'})

        assert response.status_code == 200
        data = response.json()
        assert len(data['data']) == 1

    def test_search_empty_query(self, api_client, teacher):
        """测试空查询"""
        api_client.force_authenticate(user=teacher)
        response = api_client.get('/api/v1/search/', {'q': ''})

        assert response.status_code == 200
        data = response.json()
        assert len(data['data']) == 0

    def test_search_no_results(self, api_client, teacher):
        """测试无结果"""
        api_client.force_authenticate(user=teacher)
        response = api_client.get('/api/v1/search/', {'q': '9999999'})

        assert response.status_code == 200
        data = response.json()
        assert len(data['data']) == 0
