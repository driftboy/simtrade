"""
API views for user authentication.
"""
from django.contrib.auth import login, logout
from django.db import models as db_models
from rest_framework import status, viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.decorators import action
from rest_framework.exceptions import AuthenticationFailed

from django.contrib.auth import get_user_model

from apps.users.serializers import (
    LoginSerializer,
    UserSerializer,
    RoleSerializer,
    UserSearchSerializer
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


class UserManagementViewSet(viewsets.ModelViewSet):
    """Admin user management ViewSet."""
    permission_classes = [IsAdminUser]
    serializer_class = UserSerializer
    queryset = User.objects.all().order_by('-id')

    def get_queryset(self):
        qs = super().get_queryset()
        user_type = self.request.query_params.get('user_type')
        if user_type:
            qs = qs.filter(user_type=user_type)
        search = self.request.query_params.get('search')
        if search:
            qs = qs.filter(username__icontains=search) | qs.filter(email__icontains=search)
        return qs

    def list(self, request):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({'code': 0, 'message': 'success', 'data': serializer.data})

    def retrieve(self, request, pk=None):
        user = self.get_object()
        serializer = self.get_serializer(user)
        return Response({'code': 0, 'message': 'success', 'data': serializer.data})

    def partial_update(self, request, pk=None):
        user = self.get_object()
        user_type = request.data.get('user_type')
        if user_type and user_type in ('student', 'teacher', 'admin'):
            user.user_type = user_type
            user.save(update_fields=['user_type'])
        serializer = self.get_serializer(user)
        return Response({'code': 0, 'message': '更新成功', 'data': serializer.data})

    @action(detail=True, methods=['post'], url_path='reset-password')
    def reset_password(self, request, pk=None):
        user = self.get_object()
        new_password = request.data.get('new_password', '123456')
        user.set_password(new_password)
        user.save()
        return Response({'code': 0, 'message': f'密码已重置为: {new_password}', 'data': {'new_password': new_password}})


class UserSearchViewSet(viewsets.ViewSet):
    """用户搜索视图集"""
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def search(self, request):
        """按学号或姓名搜索用户"""
        query = request.query_params.get('q', '').strip()
        if not query:
            return Response({'code': 0, 'message': 'success', 'data': []})

        from apps.teaching.models import StudentProfile

        # 按学号或姓名搜索学生
        users = User.objects.filter(
            user_type='student',
        ).filter(
            db_models.Q(username__icontains=query) |
            db_models.Q(student_profile__student_id__icontains=query)
        ).select_related('student_profile').distinct()[:10]

        serializer = UserSearchSerializer(users, many=True)
        return Response({
            'code': 0,
            'message': 'success',
            'data': serializer.data,
        })
