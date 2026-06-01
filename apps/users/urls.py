"""
URL configuration for users app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.users.views import LoginView, LogoutView, CurrentUserView, RegisterView, UserManagementViewSet, UserSearchViewSet

app_name = 'users'

router = DefaultRouter()
router.register(r'auth/users', UserManagementViewSet, basename='user-management')
router.register(r'', UserSearchViewSet, basename='user')

urlpatterns = [
    path('', include(router.urls)),
    # Authentication endpoints
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),
    path('auth/me/', CurrentUserView.as_view(), name='current-user'),
    path('auth/register/', RegisterView.as_view(), name='register'),
]
