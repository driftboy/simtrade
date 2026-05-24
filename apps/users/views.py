"""
API views for user authentication.
"""
from django.contrib.auth import login, logout
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.exceptions import AuthenticationFailed

from django.contrib.auth import get_user_model

from apps.users.serializers import (
    LoginSerializer,
    UserSerializer,
    RoleSerializer
)

User = get_user_model()


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


class RegisterView(APIView):
    """学生注册"""
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username', '').strip()
        password = request.data.get('password', '')
        email = request.data.get('email', '').strip()
        student_id = request.data.get('student_id', '').strip()

        if not username or not password or not email:
            return Response({'code': 3002, 'message': '用户名、密码和邮箱为必填项'}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(username=username).exists():
            return Response({'code': 3001, 'message': '用户名已存在'}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.create_user(username=username, password=password, email=email, user_type='student', student_id=student_id or '')
        return Response({'code': 0, 'message': '注册成功', 'data': {'id': user.id, 'username': user.username, 'user_type': user.user_type}}, status=status.HTTP_201_CREATED)
