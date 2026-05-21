"""
Tests for Authentication API endpoints.
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from apps.users.models import User, Role, Permission, UserRole, RolePermission

User = get_user_model()


class TestAuthAPI:
    """Test cases for authentication API."""

    @pytest.fixture(autouse=True)
    def setup(self, db):
        """Set up test fixtures."""
        self.client = APIClient()

        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            user_type='student'
        )

        # Create test role and permissions
        self.role = Role.objects.create(
            code='student',
            name='Student'
        )
        self.permission = Permission.objects.create(
            resource='transaction',
            action='create',
            scope='self'
        )
        RolePermission.objects.create(
            role=self.role,
            permission=self.permission
        )
        UserRole.objects.create(
            user=self.user,
            role=self.role
        )

    def test_login_success(self, db):
        """Test successful login with valid credentials."""
        response = self.client.post('/api/v1/auth/login/', {
            'username': 'testuser',
            'password': 'testpass123'
        })

        assert response.status_code == status.HTTP_200_OK
        assert 'user' in response.data
        assert response.data['user']['username'] == 'testuser'
        assert response.data['user']['email'] == 'test@example.com'
        assert 'roles' in response.data

    def test_login_invalid_username(self, db):
        """Test login with invalid username."""
        response = self.client.post('/api/v1/auth/login/', {
            'username': 'nonexistent',
            'password': 'testpass123'
        })

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_invalid_password(self, db):
        """Test login with invalid password."""
        response = self.client.post('/api/v1/auth/login/', {
            'username': 'testuser',
            'password': 'wrongpassword'
        })

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_missing_fields(self, db):
        """Test login with missing required fields."""
        response = self.client.post('/api/v1/auth/login/', {
            'username': 'testuser'
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_logout_success(self, db):
        """Test successful logout."""
        # First login
        self.client.login(username='testuser', password='testpass123')

        # Then logout
        response = self.client.post('/api/v1/auth/logout/')

        assert response.status_code == status.HTTP_200_OK
        assert 'message' in response.data

    def test_current_user_authenticated(self, db):
        """Test getting current user when authenticated."""
        # Login first
        self.client.login(username='testuser', password='testpass123')

        response = self.client.get('/api/v1/auth/me/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['username'] == 'testuser'
        assert response.data['email'] == 'test@example.com'
        assert response.data['user_type'] == 'student'

    def test_current_user_unauthenticated(self, db):
        """Test getting current user when not authenticated."""
        # Ensure not logged in
        self.client.logout()

        response = self.client.get('/api/v1/auth/me/')

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_user_serializer_includes_roles(self, db):
        """Test that user serializer includes role information."""
        self.client.login(username='testuser', password='testpass123')

        response = self.client.get('/api/v1/auth/me/')

        assert response.status_code == status.HTTP_200_OK
        assert 'roles' in response.data
        assert len(response.data['roles']) > 0
        assert response.data['roles'][0]['code'] == 'student'
        assert response.data['roles'][0]['name'] == 'Student'

    def test_superuser_has_all_roles(self, db):
        """Test that superuser response indicates admin status."""
        admin = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )

        self.client.login(username='admin', password='adminpass123')

        response = self.client.get('/api/v1/auth/me/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['username'] == 'admin'
        assert response.data['is_superuser'] is True

    def test_login_inactive_user(self, db):
        """Test login with inactive user."""
        self.user.is_active = False
        self.user.save()

        response = self.client.post('/api/v1/auth/login/', {
            'username': 'testuser',
            'password': 'testpass123'
        })

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
