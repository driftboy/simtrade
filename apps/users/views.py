"""
API views for user authentication.
"""
from django.contrib.auth import login, logout
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.exceptions import AuthenticationFailed

from apps.users.serializers import (
    LoginSerializer,
    UserSerializer,
    RoleSerializer
)


class LoginView(APIView):
    """
    API view for user login.

    POST /api/v1/auth/login/
    Accepts username and password, returns user data with roles.
    """

    permission_classes = [AllowAny]
    throttle_rate = '10/min'

    def post(self, request):
        """
        Handle user login.

        Request body:
            username: str - User's username
            password: str - User's password

        Returns:
            200: User authenticated successfully
                {
                    "user": UserSerializer data,
                    "roles": RoleSerializer data
                }
            400: Missing required fields
            401: Invalid credentials or inactive account
        """
        serializer = LoginSerializer(
            data=request.data,
            context={'request': request}
        )

        if serializer.is_valid():
            user = serializer.validated_data['user']

            # Set session for authentication
            login(request, user)

            return Response({
                'code': 0,
                'message': '登录成功',
                'data': {
                    'user': UserSerializer(user).data,
                    'roles': RoleSerializer(
                        [ur.role for ur in user.user_roles.all()],
                        many=True
                    ).data
                }
            }, status=status.HTTP_200_OK)

        # Check if the error is due to missing fields (400) or invalid credentials (401)
        errors = serializer.errors
        if 'non_field_errors' in errors:
            # Authentication failed
            return Response(errors, status=status.HTTP_401_UNAUTHORIZED)
        else:
            # Missing or invalid fields
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    """
    API view for user logout.

    POST /api/v1/auth/logout/
    Logs out the current user.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Handle user logout.

        Returns:
            200: User logged out successfully
                {
                    "message": "Successfully logged out"
                }
        """
        logout(request)
        return Response({
            'code': 0,
            'message': '登出成功'
        }, status=status.HTTP_200_OK)


class CurrentUserView(APIView):
    """
    API view for retrieving current authenticated user.

    GET /api/v1/auth/me/
    Returns the currently authenticated user's data.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Get current user information.

        Returns:
            200: User data retrieved successfully
                UserSerializer data
            401: User not authenticated
        """
        serializer = UserSerializer(request.user)
        return Response({
            'code': 0,
            'message': 'success',
            'data': serializer.data
        }, status=status.HTTP_200_OK)
