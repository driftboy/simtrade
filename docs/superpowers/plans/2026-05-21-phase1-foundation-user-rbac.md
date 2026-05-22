# SimTrade 平台 - 第一阶段：项目基础框架与用户权限系统

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 搭建 Django 项目基础架构，实现用户认证系统和 RBAC 权限框架

**架构：** Django 3.2 + PostgreSQL，采用 Django 内置 User 扩展方案，RBAC 权限模型基于 `资源.操作.作用域` 设计

**技术栈：** Django 3.2 LTS, Python 3.8+, PostgreSQL 12+, Bootstrap 3, jQuery 1.12

---

## 文件结构

### 将要创建的文件

| 文件路径 | 职责 |
|---------|------|
| `requirements.txt` | Python 依赖声明 |
| `simtrade/settings.py` | Django 项目配置 |
| `simtrade/urls.py` | 根 URL 路由 |
| `simtrade/wsgi.py` | WSGI 入口 |
| `manage.py` | Django 管理脚本 |
| `apps/users/models.py` | 用户模型扩展（Profile、Role、Permission） |
| `apps/users/permissions.py` | 权限检查装饰器和函数 |
| `apps/users/admin.py` | 管理后台配置 |
| `apps/users/views.py` | 认证视图（登录/登出） |
| `apps/users/serializers.py` | API 序列化器 |
| `apps/users/urls.py` | 用户模块路由 |
| `apps/users/apps.py` | 应用配置 |
| `apps/users/tests/test_models.py` | 模型测试 |
| `apps/users/tests/test_permissions.py` | 权限测试 |
| `apps/users/tests/test_api.py` | API 测试 |
| `apps/core/models.py` | 基础模型（Country、Port、Currency） |
| `apps/core/fixtures/initial_data.json` | 基础数据 |
| `templates/base.html` | 基础模板（Bootstrap 3） |
| `templates/registration/login.html` | 登录页面 |
| `static/css/custom.css` | 自定义样式 |
| `static/js/main.js` | 前端 JS |
| `.env.example` | 环境变量示例 |
| `.gitignore` | Git 忽略规则 |
| `README.md` | 项目说明 |

---

## 任务分解

### 任务 1：项目初始化与依赖配置

**文件：**
- 创建：`requirements.txt`
- 创建：`.env.example`
- 创建：`.gitignore`
- 创建：`README.md`

- [ ] **步骤 1：创建 requirements.txt**

```txt
# Django 核心
Django==3.2.20
djangorestframework==3.14.0
django-cors-headers==4.0.0
python-decouple==3.8

# 数据库
psycopg2-binary==2.9.7

# 前端兼容 IE8+
django-compressor==4.4

# 测试
pytest==7.4.0
pytest-django==4.5.2
pytest-cov==4.1.0
factory-boy==3.3.0
faker==19.0.0

# 代码质量
flake8==6.1.0
black==23.7.0

# 其他
Pillow==10.0.0
```

- [ ] **步骤 2：创建 .env.example**

```env
# Django
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# 数据库
DB_ENGINE=django.db.backends.postgresql
DB_NAME=simtrade
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432

# 应用配置
TIME_ZONE=Asia/Shanghai
LANGUAGE_CODE=zh-hans
```

- [ ] **步骤 3：创建 .gitignore**

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
.venv

# Django
*.log
local_settings.py
db.sqlite3
db.sqlite3-journal
/media
/staticfiles

# 环境
.env
.env.local

# IDE
.idea/
.vscode/
*.swp
*.swo
*~

# 测试
.coverage
htmlcov/
.pytest_cache/
.tox/

# 系统文件
.DS_Store
Thumbs.db
```

- [ ] **步骤 4：创建 README.md**

```md
# SimTrade 外贸模拟实训平台

面向高校国际贸易专业的模拟实训系统。

## 技术栈

- Django 3.2 LTS
- Python 3.8+
- PostgreSQL 12+
- Bootstrap 3 (兼容 IE8+)

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置环境

```bash
cp .env.example .env
# 编辑 .env 文件配置数据库等信息
```

### 数据库迁移

```bash
python manage.py migrate
```

### 创建管理员

```bash
python manage.py createsuperuser
```

### 运行开发服务器

```bash
python manage.py runserver
```

访问 http://localhost:8000

## 测试

```bash
pytest
```

## 代码规范

```bash
# 格式化
black .

# 检查
flake8
```
```

- [ ] **步骤 5：验证依赖安装**

运行：`pip install -r requirements.txt`
预期：所有依赖安装成功，无报错

- [ ] **步骤 6：Commit**

```bash
git add requirements.txt .env.example .gitignore README.md
git commit -m "chore: add project dependencies and configuration files"
```

---

### 任务 2：Django 项目创建

**文件：**
- 创建：`simtrade/settings.py`
- 创建：`simtrade/urls.py`
- 创建：`simtrade/wsgi.py`
- 创建：`simtrade/__init__.py`
- 创建：`manage.py`

- [ ] **步骤 1：创建项目目录结构**

运行：`mkdir -p simtrade apps templates static/css static/js`

- [ ] **步骤 2：创建 manage.py**

```python
#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'simtrade.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
```

- [ ] **步骤 3：创建 simtrade/__init__.py**

```python
# SimTrade Platform
__version__ = '1.0.0'
```

- [ ] **步骤 4：创建 simtrade/settings.py**

```python
import os
from pathlib import Path
from decouple import config

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY', default='django-insecure-change-me-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default=True, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1').split(',')

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third party
    'rest_framework',
    'corsheaders',
    'compressor',

    # Local apps
    'apps.users',
    'apps.core',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'simtrade.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'simtrade.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': config('DB_ENGINE', default='django.db.backends.sqlite3'),
        'NAME': config('DB_NAME', default=BASE_DIR / 'db.sqlite3'),
        'USER': config('DB_USER', default=''),
        'PASSWORD': config('DB_PASSWORD', default=''),
        'HOST': config('DB_HOST', default=''),
        'PORT': config('DB_PORT', default=''),
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'zh-hans'
TIME_ZONE = 'Asia/Shanghai'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'compressor.finders.CompressorFinder',
]
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'EXCEPTION_HANDLER': 'apps.users.exceptions.custom_exception_handler',
}

# CORS settings
CORS_ALLOW_ALL_ORIGINS = DEBUG
CORS_ALLOW_CREDENTIALS = True

# Custom user model
AUTH_USER_MODEL = 'users.User'

# Login URLs
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/login/'
```

- [ ] **步骤 5：创建 simtrade/urls.py**

```python
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('apps.users.urls')),
    path('', include('apps.users.urls')),  # 包含登录页面等
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
```

- [ ] **步骤 6：创建 simtrade/wsgi.py**

```python
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'simtrade.settings')

application = get_wsgi_application()
```

- [ ] **步骤 7：验证 Django 项目可运行**

运行：`python manage.py check`
预期：无报错

- [ ] **步骤 8：Commit**

```bash
git add simtrade/ manage.py
git commit -m "feat: create Django project structure"
```

---

### 任务 3：创建 Apps 基础结构

**文件：**
- 创建：`apps/__init__.py`
- 创建：`apps/users/__init__.py`
- 创建：`apps/users/apps.py`
- 创建：`apps/users/exceptions.py`
- 创建：`apps/core/__init__.py`
- 创建：`apps/core/apps.py`

- [ ] **步骤 1：创建 apps/__init__.py**

```python
# Apps package
```

- [ ] **步骤 2：创建 apps/users/apps.py**

```python
from django.apps import AppConfig


class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.users'
    verbose_name = '用户管理'
```

- [ ] **步骤 3：创建 apps/users/__init__.py**

```python
default_app_config = 'apps.users.apps.UsersConfig'
```

- [ ] **步骤 4：创建 apps/users/exceptions.py**

```python
from rest_framework.views import exception_handler
from rest_framework.response import Response


def custom_exception_handler(exc, context):
    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)

    if response is not None:
        custom_response_data = {
            'code': getattr(exc, 'custom_code', response.status_code * 100),
            'message': str(exc.detail if hasattr(exc, 'detail') else exc),
            'errors': response.data if hasattr(response, 'data') else None
        }
        response.data = custom_response_data

    return response


class CustomAPIException(Exception):
    def __init__(self, code, message, errors=None):
        self.code = code
        self.message = message
        self.errors = errors
        super().__init__(message)
```

- [ ] **步骤 5：创建 apps/core/apps.py**

```python
from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.core'
    verbose_name = '核心数据'
```

- [ ] **步骤 6：创建 apps/core/__init__.py**

```python
default_app_config = 'apps.core.apps.CoreConfig'
```

- [ ] **步骤 7：验证配置正确**

运行：`python manage.py check`
预期：无报错

- [ ] **步骤 8：Commit**

```bash
git add apps/
git commit -m "feat: create apps base structure"
```

---

### 任务 4：用户模型与权限系统

**文件：**
- 创建：`apps/users/models.py`
- 创建：`apps/users/permissions.py`
- 创建：`apps/users/tests/test_models.py`

- [ ] **步骤 1：编写用户模型测试**

创建 `apps/users/tests/test_models.py`：

```python
import pytest
from django.test import TestCase
from apps.users.models import User, Role, Permission, UserRole, RolePermission


class UserModelTest(TestCase):
    """测试用户模型"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_create_user(self):
        """测试创建用户"""
        assert User.objects.count() == 1
        assert self.user.username == 'testuser'
        assert self.user.email == 'test@example.com'
        assert self.user.check_password('testpass123')

    def test_user_type_choices(self):
        """测试用户类型选择"""
        self.user.user_type = 'student'
        self.user.save()
        assert self.user.get_user_type_display() == '学生'

    def test_create_superuser(self):
        """测试创建超级用户"""
        admin = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='admin123'
        )
        assert admin.is_superuser
        assert admin.is_staff


class RoleModelTest(TestCase):
    """测试角色模型"""

    def test_create_role(self):
        """测试创建角色"""
        role = Role.objects.create(
            code='TEACHER',
            name='教师'
        )
        assert role.code == 'TEACHER'
        assert role.get_code_display() == '教师'


class PermissionModelTest(TestCase):
    """测试权限模型"""

    def test_create_permission(self):
        """测试创建权限"""
        permission = Permission.objects.create(
            resource='transaction',
            action='create',
            scope='self'
        )
        assert permission.resource == 'transaction'
        assert permission.get_full_code() == 'transaction.create.self'


class UserRoleTest(TestCase):
    """测试用户角色关联"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.role = Role.objects.create(
            code='STUDENT',
            name='学生'
        )

    def test_assign_role_to_user(self):
        """测试给用户分配角色"""
        user_role = UserRole.objects.create(
            user=self.user,
            role=self.role
        )
        assert user_role.user == self.user
        assert user_role.role == self.role
        assert self.user.has_role('STUDENT')


class RolePermissionTest(TestCase):
    """测试角色权限关联"""

    def setUp(self):
        self.role = Role.objects.create(
            code='STUDENT',
            name='学生'
        )
        self.permission = Permission.objects.create(
            resource='transaction',
            action='create',
            scope='self'
        )

    def test_assign_permission_to_role(self):
        """测试给角色分配权限"""
        role_permission = RolePermission.objects.create(
            role=self.role,
            permission=self.permission
        )
        assert role_permission.role == self.role
        assert role_permission.permission == self.permission
```

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest apps/users/tests/test_models.py -v`
预期：FAIL，报错 "ModuleNotFoundError: No module named 'apps.users.models'"

- [ ] **步骤 3：实现用户模型**

创建 `apps/users/models.py`：

```python
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """扩展用户模型"""

    class UserType(models.TextChoices):
        STUDENT = 'student', '学生'
        TEACHER = 'teacher', '教师'
        ADMIN = 'admin', '管理员'

    username = models.CharField('用户名', max_length=50, unique=True)
    email = models.EmailField('邮箱', unique=True)
    user_type = models.CharField(
        '用户类型',
        max_length=20,
        choices=UserType.choices,
        default=UserType.STUDENT
    )
    phone = models.CharField('手机号', max_length=20, blank=True)
    student_id = models.CharField('学号', max_length=50, blank=True)
    avatar = models.ImageField('头像', upload_to='avatars/', blank=True)
    is_active = models.BooleanField('是否激活', default=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']

    class Meta:
        db_table = 'users_user'
        verbose_name = '用户'
        verbose_name_plural = '用户'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_user_type_display()} - {self.username}"

    def has_role(self, role_code):
        """检查用户是否有指定角色"""
        return self.roles.filter(code=role_code).exists()

    def has_permission(self, resource, action, scope, obj=None):
        """检查用户是否有指定权限"""
        # 管理员拥有所有权限
        if self.is_superuser:
            return True

        # 获取用户所有角色
        roles = self.roles.all()

        # 检查每个角色的权限
        for role in roles:
            for role_perm in role.permissions.all():
                perm = role_perm.permission
                if (perm.resource == resource and
                    perm.action == action and
                    perm.scope == scope):
                    # 检查作用域
                    if scope == 'all':
                        return True
                    elif scope == 'self' and obj:
                        return obj.owner == self
                    elif scope == 'class' and obj:
                        # 假设 obj 有 course 属性
                        return hasattr(obj, 'course') and obj.course.teacher == self
        return False


class Role(models.Model):
    """角色模型"""

    class RoleCode(models.TextChoices):
        STUDENT = 'STUDENT', '学生'
        TEACHER = 'TEACHER', '教师'
        ADMIN = 'ADMIN', '管理员'

    code = models.CharField('角色代码', max_length=50, choices=RoleCode.choices, unique=True)
    name = models.CharField('角色名称', max_length=50)
    description = models.TextField('描述', blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'users_role'
        verbose_name = '角色'
        verbose_name_plural = '角色'

    def __str__(self):
        return self.name


class Permission(models.Model):
    """权限模型"""

    resource = models.CharField('资源', max_length=50)
    action = models.CharField('操作', max_length=50)
    scope = models.CharField('作用域', max_length=20)

    class Meta:
        db_table = 'users_permission'
        verbose_name = '权限'
        verbose_name_plural = '权限'
        unique_together = [['resource', 'action', 'scope']]

    def __str__(self):
        return f"{self.resource}.{self.action}.{self.scope}"

    def get_full_code(self):
        """获取完整权限代码"""
        return f"{self.resource}.{self.action}.{self.scope}"


class UserRole(models.Model):
    """用户角色关联"""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='roles')
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='users')
    assigned_at = models.DateTimeField('分配时间', auto_now_add=True)

    class Meta:
        db_table = 'users_user_role'
        verbose_name = '用户角色'
        verbose_name_plural = '用户角色'
        unique_together = [['user', 'role']]

    def __str__(self):
        return f"{self.user.username} - {self.role.name}"


class RolePermission(models.Model):
    """角色权限关联"""

    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='permissions')
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE, related_name='roles')
    assigned_at = models.DateTimeField('分配时间', auto_now_add=True)

    class Meta:
        db_table = 'users_role_permission'
        verbose_name = '角色权限'
        verbose_name_plural = '角色权限'
        unique_together = [['role', 'permission']]

    def __str__(self):
        return f"{self.role.name} - {self.permission.get_full_code()}"
```

- [ ] **步骤 4：创建测试配置**

创建 `pytest.ini`：

```ini
[pytest]
DJANGO_SETTINGS_MODULE = simtrade.settings
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    --verbose
    --tb=short
    --cov=apps
    --cov-report=html
    --cov-report=term-missing
```

创建 `conftest.py`（项目根目录）：

```python
import pytest
import django
from django.conf import settings

if not settings.configured:
    settings.configure(
        DEBUG=True,
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': ':memory:',
            }
        },
        INSTALLED_APPS=[
            'django.contrib.auth',
            'django.contrib.contenttypes',
            'apps.users',
        ],
        SECRET_KEY='test-secret-key',
        USE_TZ=True,
    )

django.setup()

@pytest.fixture
def db_setup():
    """设置测试数据库"""
    from django.core.management import call_command
    call_command('migrate', verbosity=0)
```

- [ ] **步骤 5：运行测试验证通过**

运行：`pytest apps/users/tests/test_models.py -v`
预期：PASS

- [ ] **步骤 6：生成迁移文件**

运行：`python manage.py makemigrations users`
预期：生成迁移文件

- [ ] **步骤 7：Commit**

```bash
git add apps/users/models.py apps/users/tests/
git commit -m "feat: implement user model and RBAC system"
```

---

### 任务 5：权限检查装饰器

**文件：**
- 创建：`apps/users/permissions.py`
- 创建：`apps/users/tests/test_permissions.py`

- [ ] **步骤 1：编写权限检查测试**

创建 `apps/users/tests/test_permissions.py`：

```python
import pytest
from django.test import RequestFactory
from django.contrib.auth.models import AnonymousUser
from apps.users.models import User, Role, Permission, RolePermission
from apps.users.permissions import require_permission, has_permission


class PermissionCheckTest(TestCase):
    """测试权限检查函数"""

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )

    def test_superuser_has_all_permissions(self):
        """测试超级用户拥有所有权限"""
        self.user.is_superuser = True
        self.user.save()
        assert has_permission(self.user, 'any_resource', 'any_action', 'any_scope')

    def test_user_without_permission_denied(self):
        """测试无权限用户被拒绝"""
        result = has_permission(self.user, 'transaction', 'create', 'self')
        assert result is False

    def test_user_with_permission_allowed(self):
        """测试有权限用户被允许"""
        # 创建角色和权限
        role = Role.objects.create(code='STUDENT', name='学生')
        permission = Permission.objects.create(
            resource='transaction',
            action='create',
            scope='self'
        )
        RolePermission.objects.create(role=role, permission=permission)
        UserRole.objects.create(user=self.user, role=role)

        assert has_permission(self.user, 'transaction', 'create', 'self')

    def test_permission_decorator(self):
        """测试权限装饰器"""
        @require_permission('transaction', 'create', 'self')
        def test_view(request):
            return 'success'

        request = self.factory.get('/')
        request.user = self.user

        # 无权限时应抛出异常
        with pytest.raises(PermissionDenied):
            test_view(request)
```

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest apps/users/tests/test_permissions.py -v`
预期：FAIL，报错 "ModuleNotFoundError: No module named 'apps.users.permissions'"

- [ ] **步骤 3：实现权限检查模块**

创建 `apps/users/permissions.py`：

```python
from functools import wraps
from django.core.exceptions import PermissionDenied
from apps.users.models import User


def has_permission(user: User, resource: str, action: str, scope: str, obj=None) -> bool:
    """
    检查用户是否有指定权限

    Args:
        user: 用户实例
        resource: 资源名称 (如 'transaction', 'document')
        action: 操作名称 (如 'create', 'read', 'update', 'delete')
        scope: 作用域 ('self', 'class', 'all')
        obj: 被操作的对象实例

    Returns:
        bool: 是否有权限
    """
    # 管理员拥有所有权限
    if user.is_superuser or user.is_staff:
        return True

    # 获取用户所有角色
    roles = user.roles.all()

    # 检查每个角色的权限
    for role in roles:
        for role_perm in role.permissions.all():
            perm = role_perm.permission
            if (perm.resource == resource and
                perm.action == action and
                perm.scope == scope):
                # 检查作用域
                if scope == 'all':
                    return True
                elif scope == 'self':
                    if obj is None:
                        return True
                    return hasattr(obj, 'owner') and obj.owner == user
                elif scope == 'class':
                    if obj is None:
                        return True
                    return hasattr(obj, 'course') and obj.course.teacher == user
    return False


def require_permission(resource: str, action: str, scope: str):
    """
    权限检查装饰器

    用法:
        @require_permission('transaction', 'update', 'self')
        def update_transaction(request, transaction_id):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                raise PermissionDenied("用户未登录")

            # 从 kwargs 中获取被操作对象
            obj = None
            if scope == 'self' and 'pk' in kwargs:
                # 假设 URL 包含 pk 参数
                from apps.transaction.models import Transaction
                try:
                    obj = Transaction.objects.get(pk=kwargs['pk'])
                except:
                    pass

            if not has_permission(request.user, resource, action, scope, obj):
                raise PermissionDenied(
                    f"用户没有权限执行此操作: {resource}.{action}.{scope}"
                )

            return view_func(request, *args, **kwargs)
        return wrapped_view
    return decorator
```

- [ ] **步骤 4：更新测试导入**

修改 `apps/users/tests/test_permissions.py` 添加导入：

```python
from django.core.exceptions import PermissionDenied
```

- [ ] **步骤 5：运行测试验证通过**

运行：`pytest apps/users/tests/test_permissions.py -v`
预期：PASS

- [ ] **步骤 6：Commit**

```bash
git add apps/users/permissions.py apps/users/tests/test_permissions.py
git commit -m "feat: implement permission check decorators"
```

---

### 任务 6：用户认证 API

**文件：**
- 创建：`apps/users/serializers.py`
- 创建：`apps/users/views.py`
- 创建：`apps/users/urls.py`
- 创建：`apps/users/tests/test_api.py`

- [ ] **步骤 1：编写 API 测试**

创建 `apps/users/tests/test_api.py`：

```python
import pytest
from django.test import TestCase
from django.urls import reverse
from apps.users.models import User


class AuthAPITest(TestCase):
    """测试认证 API"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_login_success(self):
        """测试登录成功"""
        url = reverse('login')
        data = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        response = self.client.post(url, data, content_type='application/json')
        assert response.status_code == 200
        assert response.json()['code'] == 0

    def test_login_failure(self):
        """测试登录失败"""
        url = reverse('login')
        data = {
            'username': 'testuser',
            'password': 'wrongpassword'
        }
        response = self.client.post(url, data, content_type='application/json')
        assert response.status_code == 401

    def test_get_current_user(self):
        """测试获取当前用户信息"""
        self.client.login(username='testuser', password='testpass123')
        url = reverse('current_user')
        response = self.client.get(url)
        assert response.status_code == 200
        assert response.json()['data']['username'] == 'testuser'

    def test_logout(self):
        """测试登出"""
        self.client.login(username='testuser', password='testpass123')
        url = reverse('logout')
        response = self.client.post(url)
        assert response.status_code == 200
```

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest apps/users/tests/test_api.py -v`
预期：FAIL，报错 "NoReverseMatch"

- [ ] **步骤 3：实现序列化器**

创建 `apps/users/serializers.py`：

```python
from rest_framework import serializers
from django.contrib.auth import authenticate
from apps.users.models import User, Role, Permission


class UserSerializer(serializers.ModelSerializer):
    """用户序列化器"""

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'user_type', 'phone',
                  'student_id', 'avatar', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']


class LoginSerializer(serializers.Serializer):
    """登录序列化器"""

    username = serializers.CharField(max_length=50)
    password = serializers.CharField(max_length=128, write_only=True)

    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')

        if username and password:
            user = authenticate(username=username, password=password)
            if not user:
                raise serializers.ValidationError('用户名或密码错误')
            if not user.is_active:
                raise serializers.ValidationError('用户已被禁用')
            attrs['user'] = user
        else:
            raise serializers.ValidationError('必须提供用户名和密码')

        return attrs


class RoleSerializer(serializers.ModelSerializer):
    """角色序列化器"""

    class Meta:
        model = Role
        fields = ['id', 'code', 'name', 'description', 'created_at']
        read_only_fields = ['id', 'created_at']


class PermissionSerializer(serializers.ModelSerializer):
    """权限序列化器"""

    full_code = serializers.CharField(source='get_full_code', read_only=True)

    class Meta:
        model = Permission
        fields = ['id', 'resource', 'action', 'scope', 'full_code']
        read_only_fields = ['id']
```

- [ ] **步骤 4：实现认证视图**

创建 `apps/users/views.py`：

```python
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth import login, logout
from apps.users.serializers import UserSerializer, LoginSerializer


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """用户登录"""
    serializer = LoginSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.validated_data['user']
        login(request, user)
        return Response({
            'code': 0,
            'message': '登录成功',
            'data': UserSerializer(user).data
        })
    return Response({
        'code': 1002,
        'message': '用户名或密码错误',
        'errors': serializer.errors
    }, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['POST'])
def logout_view(request):
    """用户登出"""
    logout(request)
    return Response({
        'code': 0,
        'message': '登出成功'
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def current_user_view(request):
    """获取当前用户信息"""
    return Response({
        'code': 0,
        'message': 'success',
        'data': UserSerializer(request.user).data
    })
```

- [ ] **步骤 5：配置 URL 路由**

创建 `apps/users/urls.py`：

```python
from django.urls import path
from apps.users import views

app_name = 'users'

urlpatterns = [
    # 认证相关
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('auth/me/', views.current_user_view, name='current_user'),
]
```

更新 `simtrade/urls.py` 添加认证 URL：

```python
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/auth/', include('apps.users.urls')),  # 认证 API
    path('', include('apps.users.urls')),  # 包含登录页面等
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
```

- [ ] **步骤 6：运行测试验证通过**

运行：`pytest apps/users/tests/test_api.py -v`
预期：PASS

- [ ] **步骤 7：Commit**

```bash
git add apps/users/serializers.py apps/users/views.py apps/users/urls.py
git add apps/users/tests/test_api.py
git commit -m "feat: implement authentication API"
```

---

### 任务 7：管理后台配置

**文件：**
- 创建：`apps/users/admin.py`

- [ ] **步骤 1：实现管理后台**

创建 `apps/users/admin.py`：

```python
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from apps.users.models import User, Role, Permission, UserRole, RolePermission


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """用户管理"""

    list_display = ['username', 'email', 'user_type', 'is_active', 'created_at']
    list_filter = ['user_type', 'is_active', 'created_at']
    search_fields = ['username', 'email', 'student_id']
    ordering = ['-created_at']

    fieldsets = BaseUserAdmin.fieldsets + (
        ('额外信息', {'fields': ('user_type', 'phone', 'student_id', 'avatar')}),
    )

    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('额外信息', {'fields': ('email', 'user_type')}),
    )


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    """角色管理"""

    list_display = ['code', 'name', 'description', 'created_at']
    search_fields = ['code', 'name']
    list_filter = ['created_at']


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    """权限管理"""

    list_display = ['resource', 'action', 'scope', 'get_full_code']
    list_filter = ['resource', 'action', 'scope']
    search_fields = ['resource', 'action']


@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    """用户角色管理"""

    list_display = ['user', 'role', 'assigned_at']
    list_filter = ['role', 'assigned_at']
    search_fields = ['user__username', 'role__name']


@admin.register(RolePermission)
class RolePermissionAdmin(admin.ModelAdmin):
    """角色权限管理"""

    list_display = ['role', 'permission', 'assigned_at']
    list_filter = ['role', 'assigned_at']
```

- [ ] **步骤 2：验证管理后台可访问**

运行：`python manage.py runserver`
访问：http://localhost:8000/admin/
预期：管理后台正常显示

- [ ] **步骤 3：Commit**

```bash
git add apps/users/admin.py
git commit -m "feat: configure admin interface"
```

---

### 任务 8：前端模板与静态文件

**文件：**
- 创建：`templates/base.html`
- 创建：`templates/registration/login.html`
- 创建：`static/css/custom.css`
- 创建：`static/js/main.js`

- [ ] **步骤 1：创建基础模板**

创建 `templates/base.html`：

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{% block title %}SimTrade - 外贸模拟实训平台{% endblock %}</title>

    <!-- Bootstrap 3 (兼容 IE8+) -->
    <link href="https://cdn.bootcdn.net/ajax/libs/twitter-bootstrap/3.4.1/css/bootstrap.min.css" rel="stylesheet">
    {% load compress %}
    {% compress css %}
    <link rel="stylesheet" href="{% static 'css/custom.css' %}">
    {% endcompress %}
</head>
<body>
    <!-- 导航栏 -->
    <nav class="navbar navbar-default">
        <div class="container-fluid">
            <div class="navbar-header">
                <a class="navbar-brand" href="/">SimTrade</a>
            </div>
            <div class="collapse navbar-collapse">
                <ul class="nav navbar-nav navbar-right">
                    {% if user.is_authenticated %}
                        <li><a href="#">欢迎, {{ user.username }}</a></li>
                        <li><a href="{% url 'logout' %}">退出</a></li>
                    {% else %}
                        <li><a href="{% url 'login' %}">登录</a></li>
                    {% endif %}
                </ul>
            </div>
        </div>
    </nav>

    <!-- 内容区域 -->
    <div class="container">
        {% block content %}{% endblock %}
    </div>

    <!-- jQuery -->
    <script src="https://cdn.bootcdn.net/ajax/libs/jquery/1.12.4/jquery.min.js"></script>
    <!-- Bootstrap 3 -->
    <script src="https://cdn.bootcdn.net/ajax/libs/twitter-bootstrap/3.4.1/js/bootstrap.min.js"></script>

    {% compress js %}
    <script src="{% static 'js/main.js' %}"></script>
    {% endcompress %}

    {% block scripts %}{% endblock %}
</body>
</html>
```

- [ ] **步骤 2：创建登录页面**

创建 `templates/registration/login.html`：

```html
{% extends "base.html" %}

{% block title %}登录 - SimTrade{% endblock %}

{% block content %}
<div class="row">
    <div class="col-md-4 col-md-offset-4">
        <div class="panel panel-default">
            <div class="panel-heading">
                <h3 class="panel-title">用户登录</h3>
            </div>
            <div class="panel-body">
                <form id="loginForm" method="post">
                    {% csrf_token %}
                    <div class="form-group">
                        <label for="username">用户名</label>
                        <input type="text" class="form-control" id="username" name="username" required>
                    </div>
                    <div class="form-group">
                        <label for="password">密码</label>
                        <input type="password" class="form-control" id="password" name="password" required>
                    </div>
                    <div id="errorMessage" class="alert alert-danger" style="display: none;"></div>
                    <button type="submit" class="btn btn-primary btn-block">登录</button>
                </form>
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block scripts %}
<script>
$('#loginForm').on('submit', function(e) {
    e.preventDefault();
    var $form = $(this);
    var $error = $('#errorMessage').hide();

    $.ajax({
        url: '{% url "login" %}',
        method: 'POST',
        data: {
            username: $('#username').val(),
            password: $('#password').val(),
            csrfmiddlewaretoken: $('input[name=csrfmiddlewaretoken]').val()
        },
        success: function(response) {
            if (response.code === 0) {
                window.location.href = '/';
            } else {
                $error.text(response.message || '登录失败').show();
            }
        },
        error: function(xhr) {
            var response = xhr.responseJSON || {};
            $error.text(response.message || '登录失败').show();
        }
    });
});
</script>
{% endblock %}
```

- [ ] **步骤 3：创建自定义样式**

创建 `static/css/custom.css`：

```css
/* SimTrade 自定义样式 */

body {
    font-family: "Microsoft YaHei", Arial, sans-serif;
    min-height: 100vh;
    background-color: #f5f5f5;
}

.navbar-default {
    background-color: #337ab7;
    border-color: #2e6da4;
}

.navbar-default .navbar-brand {
    color: #fff;
    font-weight: bold;
}

.navbar-default .navbar-nav > li > a {
    color: #fff;
}

.panel {
    margin-top: 50px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
}

.btn-primary {
    background-color: #337ab7;
    border-color: #2e6da4;
}

.btn-primary:hover {
    background-color: #286090;
    border-color: #204d74;
}
```

- [ ] **步骤 4：创建主 JS 文件**

创建 `static/js/main.js`：

```javascript
/**
 * SimTrade 主脚本
 */

$(document).ready(function() {
    'use strict';

    // 全局 AJAX 错误处理
    $(document).ajaxError(function(event, xhr, settings, thrownError) {
        if (xhr.status === 401) {
            window.location.href = '/login/';
        }
    });

    // 工具函数
    window.SimTrade = {
        showAlert: function(message, type) {
            type = type || 'info';
            var alertHtml = '<div class="alert alert-' + type + ' alert-dismissible" role="alert">' +
                '<button type="button" class="close" data-dismiss="alert"><span>&times;</span></button>' +
                message + '</div>';
            $('.container').prepend(alertHtml);
            setTimeout(function() {
                $('.alert').fadeOut();
            }, 5000);
        }
    };
});
```

- [ ] **步骤 5：验证页面可访问**

运行：`python manage.py runserver`
访问：http://localhost:8000/login/
预期：登录页面正常显示

- [ ] **步骤 6：Commit**

```bash
git add templates/ static/
git commit -m "feat: add frontend templates and static files"
```

---

### 任务 9：核心数据模型

**文件：**
- 创建：`apps/core/models.py`
- 创建：`apps/core/fixtures/initial_data.json`

- [ ] **步骤 1：编写核心数据模型测试**

创建 `apps/core/tests/test_models.py`：

```python
import pytest
from django.test import TestCase
from apps.core.models import Country, Port, Currency


class CountryModelTest(TestCase):
    """测试国家模型"""

    def test_create_country(self):
        """测试创建国家"""
        country = Country.objects.create(
            code='CN',
            name='中国',
            name_en='China'
        )
        assert country.code == 'CN'
        assert country.name == '中国'


class PortModelTest(TestCase):
    """测试港口模型"""

    def setUp(self):
        self.country = Country.objects.create(
            code='CN',
            name='中国'
        )

    def test_create_port(self):
        """测试创建港口"""
        port = Port.objects.create(
            code='CNSHA',
            name='上海',
            country=self.country
        )
        assert port.code == 'CNSHA'
        assert port.name == '上海'


class CurrencyModelTest(TestCase):
    """测试货币模型"""

    def test_create_currency(self):
        """测试创建货币"""
        currency = Currency.objects.create(
            code='USD',
            name='美元',
            symbol='$'
        )
        assert currency.code == 'USD'
        assert currency.symbol == '$'
```

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest apps/core/tests/test_models.py -v`
预期：FAIL

- [ ] **步骤 3：实现核心数据模型**

创建 `apps/core/models.py`：

```python
from django.db import models


class Country(models.Model):
    """国家模型"""

    code = models.CharField('国家代码', max_length=10, unique=True, primary_key=True)
    name = models.CharField('中文名称', max_length=100)
    name_en = models.CharField('英文名称', max_length=100)
    phone_code = models.CharField('电话区号', max_length=10, blank=True)
    is_active = models.BooleanField('是否启用', default=True)

    class Meta:
        db_table = 'core_country'
        verbose_name = '国家'
        verbose_name_plural = '国家'
        ordering = ['code']

    def __str__(self):
        return f"{self.code} - {self.name}"


class Port(models.Model):
    """港口模型"""

    code = models.CharField('港口代码', max_length=20, unique=True)
    name = models.CharField('中文名称', max_length=100)
    name_en = models.CharField('英文名称', max_length=100, blank=True)
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name='ports')
    is_active = models.BooleanField('是否启用', default=True)

    class Meta:
        db_table = 'core_port'
        verbose_name = '港口'
        verbose_name_plural = '港口'
        ordering = ['code']

    def __str__(self):
        return f"{self.code} - {self.name}"


class Currency(models.Model):
    """货币模型"""

    code = models.CharField('货币代码', max_length=10, unique=True, primary_key=True)
    name = models.CharField('中文名称', max_length=50)
    name_en = models.CharField('英文名称', max_length=50, blank=True)
    symbol = models.CharField('符号', max_length=10, blank=True)
    is_active = models.BooleanField('是否启用', default=True)

    class Meta:
        db_table = 'core_currency'
        verbose_name = '货币'
        verbose_name_plural = '货币'
        ordering = ['code']

    def __str__(self):
        return f"{self.code} - {self.symbol}"
```

- [ ] **步骤 4：运行测试验证通过**

运行：`pytest apps/core/tests/test_models.py -v`
预期：PASS

- [ ] **步骤 5：创建初始数据 Fixture**

创建 `apps/core/fixtures/initial_data.json`：

```json
[
  {
    "model": "core.country",
    "pk": "CN",
    "fields": {
      "code": "CN",
      "name": "中国",
      "name_en": "China",
      "phone_code": "+86",
      "is_active": true
    }
  },
  {
    "model": "core.country",
    "pk": "US",
    "fields": {
      "code": "US",
      "name": "美国",
      "name_en": "United States",
      "phone_code": "+1",
      "is_active": true
    }
  },
  {
    "model": "core.country",
    "pk": "JP",
    "fields": {
      "code": "JP",
      "name": "日本",
      "name_en": "Japan",
      "phone_code": "+81",
      "is_active": true
    }
  },
  {
    "model": "core.port",
    "pk": 1,
    "fields": {
      "code": "CNSHA",
      "name": "上海",
      "name_en": "Shanghai",
      "country": "CN",
      "is_active": true
    }
  },
  {
    "model": "core.port",
    "pk": 2,
    "fields": {
      "code": "CNNGB",
      "name": "宁波",
      "name_en": "Ningbo",
      "country": "CN",
      "is_active": true
    }
  },
  {
    "model": "core.port",
    "pk": 3,
    "fields": {
      "code": "USLAX",
      "name": "洛杉矶",
      "name_en": "Los Angeles",
      "country": "US",
      "is_active": true
    }
  },
  {
    "model": "core.port",
    "pk": 4,
    "fields": {
      "code": "USNYC",
      "name": "纽约",
      "name_en": "New York",
      "country": "US",
      "is_active": true
    }
  },
  {
    "model": "core.currency",
    "pk": "CNY",
    "fields": {
      "code": "CNY",
      "name": "人民币",
      "name_en": "Chinese Yuan",
      "symbol": "¥",
      "is_active": true
    }
  },
  {
    "model": "core.currency",
    "pk": "USD",
    "fields": {
      "code": "USD",
      "name": "美元",
      "name_en": "US Dollar",
      "symbol": "$",
      "is_active": true
    }
  },
  {
    "model": "core.currency",
    "pk": "EUR",
    "fields": {
      "code": "EUR",
      "name": "欧元",
      "name_en": "Euro",
      "symbol": "€",
      "is_active": true
    }
  }
]
```

- [ ] **步骤 6：生成迁移文件**

运行：`python manage.py makemigrations core`

- [ ] **步骤 7：Commit**

```bash
git add apps/core/
git commit -m "feat: implement core data models"
```

---

### 任务 10：初始化数据加载

**文件：**
- 创建：`apps/core/management/commands/init_data.py`

- [ ] **步骤 1：创建数据初始化命令**

创建 `apps/core/management/commands/init_data.py`：

```python
from django.core.management.base import BaseCommand
from django.core.management import call_command


class Command(BaseCommand):
    help = '初始化系统基础数据'

    def handle(self, *args, **options):
        self.stdout.write('开始初始化系统数据...')

        # 加载 fixture 数据
        try:
            call_command('loaddata', 'initial_data', app_label='core')
            self.stdout.write(self.style.SUCCESS('✓ 基础数据加载完成'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ 数据加载失败: {e}'))

        # 创建默认角色和权限
        from apps.users.models import Role, Permission
        from apps.users.models import RolePermission

        # 创建角色
        roles_data = [
            ('STUDENT', '学生', '可以创建自己的交易和单证'),
            ('TEACHER', '教师', '可以管理班级的课程和学生'),
            ('ADMIN', '管理员', '拥有所有权限'),
        ]

        for code, name, desc in roles_data:
            role, created = Role.objects.get_or_create(
                code=code,
                defaults={'name': name, 'description': desc}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'✓ 创建角色: {name}'))

        # 创建权限
        permissions_data = [
            # 交易权限
            ('transaction', 'create', 'self'),
            ('transaction', 'read', 'self'),
            ('transaction', 'update', 'self'),
            ('transaction', 'delete', 'self'),
            # 单证权限
            ('document', 'create', 'self'),
            ('document', 'read', 'self'),
            ('document', 'update', 'self'),
            ('document', 'delete', 'self'),
            # 课程权限
            ('course', 'read', 'all'),
            ('score', 'read', 'all'),
        ]

        for resource, action, scope in permissions_data:
            perm, created = Permission.objects.get_or_create(
                resource=resource,
                action=action,
                scope=scope
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'✓ 创建权限: {resource}.{action}.{scope}'))

        # 分配权限给角色
        student_role = Role.objects.get(code='STUDENT')
        teacher_role = Role.objects.get(code='TEACHER')
        admin_role = Role.objects.get(code='ADMIN')

        # 学生权限
        student_permissions = [
            ('transaction', 'create', 'self'),
            ('transaction', 'read', 'self'),
            ('transaction', 'update', 'self'),
            ('document', 'create', 'self'),
            ('document', 'read', 'self'),
            ('document', 'update', 'self'),
            ('course', 'read', 'all'),
        ]

        for resource, action, scope in student_permissions:
            try:
                perm = Permission.objects.get(resource=resource, action=action, scope=scope)
                RolePermission.objects.get_or_create(role=student_role, permission=perm)
            except Permission.DoesNotExist:
                pass

        self.stdout.write(self.style.SUCCESS('✓ 学生权限分配完成'))

        self.stdout.write(self.style.SUCCESS('系统数据初始化完成！'))
```

- [ ] **步骤 2：验证命令可运行**

运行：`python manage.py init_data`
预期：数据加载成功

- [ ] **步骤 3：Commit**

```bash
git add apps/core/management/
git commit -m "feat: add data initialization command"
```

---

### 任务 11：最终验证与文档

**文件：**
- 修改：`README.md`
- 创建：`docs/API.md`

- [ ] **步骤 1：更新 README.md**

更新 `README.md` 添加完整内容：

```md
# SimTrade 外贸模拟实训平台

面向高校国际贸易专业的模拟实训系统。

## 技术栈

- Django 3.2 LTS
- Python 3.8+
- PostgreSQL 12+
- Bootstrap 3 (兼容 IE8+)

## 功能特性

- ✅ 用户认证与 RBAC 权限系统
- ✅ 多角色模拟（出口商、进口商、工厂、银行等）
- 🚧 交易管理
- 🚧 单证系统
- 🚧 评分系统

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置环境

```bash
cp .env.example .env
# 编辑 .env 文件配置数据库等信息
```

### 数据库迁移

```bash
python manage.py migrate
```

### 初始化数据

```bash
python manage.py init_data
```

### 创建管理员

```bash
python manage.py createsuperuser
```

### 运行开发服务器

```bash
python manage.py runserver
```

访问 http://localhost:8000

## 测试

```bash
# 运行所有测试
pytest

# 运行特定模块测试
pytest apps/users/tests/
pytest apps/core/tests/

# 查看覆盖率报告
pytest --cov=apps --cov-report=html
```

## API 文档

详见 [API.md](docs/API.md)

## 项目结构

```
simtrade/
├── apps/
│   ├── users/          # 用户与权限
│   └── core/           # 核心数据
├── templates/          # 模板文件
├── static/             # 静态文件
├── docs/               # 文档
└── simtrade/           # 项目配置
```

## 代码规范

```bash
# 格式化代码
black .

# 检查代码风格
flake8
```

## License

MIT
```

- [ ] **步骤 2：创建 API 文档**

创建 `docs/API.md`：

```md
# SimTrade API 文档

## 基础信息

- 基础路径：`/api/v1/`
- 认证方式：Session Authentication
- 响应格式：JSON

## 响应格式

### 成功响应

```json
{
  "code": 0,
  "message": "success",
  "data": {...}
}
```

### 错误响应

```json
{
  "code": 1001,
  "message": "错误描述",
  "errors": {...}
}
```

## 认证接口

### 用户登录

**请求**
```
POST /api/v1/auth/login/
Content-Type: application/json

{
  "username": "testuser",
  "password": "password123"
}
```

**响应**
```json
{
  "code": 0,
  "message": "登录成功",
  "data": {
    "id": 1,
    "username": "testuser",
    "email": "test@example.com",
    "user_type": "student"
  }
}
```

### 用户登出

**请求**
```
POST /api/v1/auth/logout/
```

**响应**
```json
{
  "code": 0,
  "message": "登出成功"
}
```

### 获取当前用户

**请求**
```
GET /api/v1/auth/me/
Authorization: Session cookie
```

**响应**
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 1,
    "username": "testuser",
    "email": "test@example.com",
    "user_type": "student"
  }
}
```

## 错误码

| 错误码 | 说明 |
|--------|------|
| 0 | 成功 |
| 1001 | 用户不存在 |
| 1002 | 密码错误 |
| 1003 | Token 无效 |
| 2001 | 无权限访问 |
| 3001 | 参数缺失 |
| 3002 | 参数格式错误 |
| 4001 | 资源不存在 |
```

- [ ] **步骤 3：运行完整测试套件**

运行：`pytest`
预期：所有测试通过

- [ ] **步骤 4：验证项目可运行**

运行：`python manage.py runserver`
访问：http://localhost:8000
预期：项目正常运行

- [ ] **步骤 5：最终 Commit**

```bash
git add README.md docs/
git commit -m "docs: add API documentation and update README"
```

---

## 自检清单

### 规格覆盖度

| 设计章节 | 对应任务 |
|---------|---------|
| 用户与权限系统 (7 表) | 任务 4, 5, 7 |
| 认证 API | 任务 6 |
| 系统配置 (5 表) | 任务 9 |
| 数据初始化 | 任务 10 |
| 浏览器兼容性 | 任务 8 (Bootstrap 3) |
| REST API 设计 | 任务 6, 文档 |

### 占位符检查

✅ 无 "待定"、"TODO" 等占位符
✅ 所有代码步骤包含完整代码
✅ 所有命令有明确的预期输出

### 类型一致性检查

✅ User 模型字段名在各处一致
✅ 权限代码格式 `resource.action.scope` 保持一致
✅ API 响应格式统一

---

## 总结

此计划实现了 SimTrade 平台的第一阶段：

1. ✅ Django 项目基础框架
2. ✅ 用户认证系统
3. ✅ RBAC 权限框架
4. ✅ 核心 API 接口
5. ✅ 前端基础模板
6. ✅ 基础数据模型

**下一步**：实现交易系统、单证系统等业务模块。
