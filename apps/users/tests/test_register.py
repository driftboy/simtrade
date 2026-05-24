import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()


@pytest.mark.django_db
class TestRegisterAPI(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_register_success(self):
        response = self.client.post('/api/v1/auth/register/', {
            'username': 'newstudent', 'password': 'testpass123', 'email': 'new@test.com'
        }, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['code'], 0)
        user = User.objects.get(username='newstudent')
        self.assertEqual(user.user_type, 'student')

    def test_register_with_student_id(self):
        response = self.client.post('/api/v1/auth/register/', {
            'username': 'student2', 'password': 'testpass123', 'email': 's2@test.com', 'student_id': '2026001'
        }, format='json')
        self.assertEqual(response.status_code, 201)

    def test_register_duplicate_username(self):
        User.objects.create_user(username='dup', password='pass', email='d@test.com')
        response = self.client.post('/api/v1/auth/register/', {
            'username': 'dup', 'password': 'testpass123', 'email': 'd2@test.com'
        }, format='json')
        self.assertEqual(response.status_code, 400)

    def test_register_missing_fields(self):
        response = self.client.post('/api/v1/auth/register/', {'username': 'noemail'}, format='json')
        self.assertEqual(response.status_code, 400)
