"""
URL configuration for users app.
"""
from django.urls import path
from apps.users.views import LoginView, LogoutView, CurrentUserView, RegisterView

app_name = 'users'

urlpatterns = [
    # Authentication endpoints
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),
    path('auth/me/', CurrentUserView.as_view(), name='current-user'),
    path('auth/register/', RegisterView.as_view(), name='register'),
]
