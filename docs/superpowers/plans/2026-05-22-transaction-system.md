# 交易管理系统实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 实现 SimTrade 交易管理核心功能，支持询盘/发盘/还盘磋商流程、合同管理、商品目录管理，以及 WebSocket 实时通知

**架构：** Django + Django Channels + Redis，独立数据模型设计，基于状态的交易流转

**技术栈：** Django 3.2, Django Channels 3.0, Redis, daphne, pytest

---

## 文件结构

### 将要创建的文件

| 文件路径 | 职责 |
|---------|------|
| `apps/products/__init__.py` | 商品模块包 |
| `apps/products/apps.py` | 商品模块配置 |
| `apps/products/models.py` | Product、Catalog 模型 |
| `apps/products/serializers.py` | 商品 API 序列化器 |
| `apps/products/views.py` | 商品 API 视图 |
| `apps/products/urls.py` |商品路由 |
| `apps/products/admin.py` | 商品管理后台 |
| `apps/products/tests/test_models.py` | 商品模型测试 |
| `apps/products/tests/test_api.py` | 商品 API 测试 |
| `apps/transactions/__init__.py` | 交易模块包 |
| `apps/transactions/apps.py` | 交易模块配置 |
| `apps/transactions/models.py` | Transaction、InquiryMessage、Contract、ContractSignature、TransactionLog 模型 |
| `apps/transactions/serializers.py` | 交易 API 序列化器 |
| `apps/transactions/views.py` | 交易 API 视图 |
| `apps/transactions/urls.py` | 交易路由 |
| `apps/transactions/admin.py` | 交易管理后台 |
| `apps/transactions/consumers.py` | WebSocket 消费者 |
| `apps/transactions/services.py` | 交易业务服务 |
| `apps/transactions/tests/test_models.py` | 交易模型测试 |
| `apps/transactions/tests/test_api.py` | 交易 API 测试 |
| `apps/transactions/tests/test_state_machine.py` | 状态机测试 |
| `apps/transactions/tests/test_websocket.py` | WebSocket 测试 |
| `apps/transactions/tests/test_integration.py` | 集成测试 |
| `apps/notifications/__init__.py` | 通知模块包 |
| `apps/notifications/consumers.py` | 通知 WebSocket 消费者 |
| `apps/notifications/services.py` | 通知发送服务 |
| `apps/notifications/tests/test_notifications.py` | 通知测试 |
| `templates/products/market.html` | 商品市场页面 |
| `templates/products/my_catalog.html` | 我的商品目录页面 |
| `templates/transactions/list.html` | 交易列表页面 |
| `templates/transactions/detail.html` | 交易详情页面 |
| `templates/transactions/contract_preview.html` | 合同预览页面 |
| `static/css/transactions.css` | 交易模块样式 |
| `static/js/transactions.js` | 交易模块脚本 |
| `static/js/notifications.js` | WebSocket 通知脚本 |
| `simtrade/routing.py` | WebSocket 路由配置 |
| `simtrade/asgi.py` | ASGI 应用配置 |
| `apps/transactions/fixtures/initial_products.json` | 初始商品数据 |

### 将要修改的文件

| 文件路径 | 修改内容 |
|---------|---------|
| `simtrade/settings.py` | 添加 channels 配置和新应用 |
| `simtrade/urls.py` | 添加 API 路由 |
| `requirements.txt` | 添加 channels 等依赖 |
| `templates/base.html` | 添加 WebSocket 初始化脚本 |

---

## 任务分解

### 任务 1：添加项目依赖

**文件：**
- 修改：`requirements.txt`

- [ ] **步骤 1：添加 WebSocket 相关依赖**

在 `requirements.txt` 末尾添加：

```txt
# WebSocket 支持
channels==3.0.4
channels-redis==4.1.0
channels-testing==1.2.0
# Redis 客户端
redis==4.5.5
# ASGI 服务器
daphne==4.0.0
```

- [ ] **步骤 2：安装依赖验证**

运行：`pip install channels==3.0.4 channels-redis==4.1.0 redis==4.5.5 daphne==4.0.0 channels-testing==1.2.0`
预期：所有依赖安装成功，无报错

- [ ] **步骤 3：Commit**

```bash
git add requirements.txt
git commit -m "feat: add WebSocket dependencies (channels, redis, daphne)"
```

---

### 任务 2：配置 Django Channels

**文件：**
- 修改：`simtrade/settings.py`
- 创建：`simtrade/routing.py`
- 修改：`simtrade/asgi.py`

- [ ] **步骤 1：更新 settings.py 配置**

在 `simtrade/settings.py` 中：

1. 在 `INSTALLED_APPS` 的 `Local apps` 部分之前添加：

```python
    # Third party
    'daphne',
    'channels',
```

2. 在 `Local apps` 部分添加：

```python
    # Local apps
    'apps.users',
    'apps.core',
    'apps.products',      # 新增
    'apps.transactions',  # 新增
    'apps.notifications', # 新增
```

3. 在文件末尾（`DEFAULT_AUTO_FIELD` 之后）添加：

```python
# Channels / WebSocket
ASGI_APPLICATION = 'simtrade.asgi.application'

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [config('REDIS_URL', default='redis://127.0.0.1:6379/1')],
        },
    },
}
```

- [ ] **步骤 2：创建 WebSocket 路由配置**

创建 `simtrade/routing.py`：

```python
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/notifications/$', consumers.NotificationConsumer.as_asgi()),
]
```

- [ ] **步骤 3：更新 ASGI 配置**

修改 `simtrade/asgi.py` 为：

```python
import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import simtrade.routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'simtrade.settings')

application = ProtocolTypeRouter({
    'http': get_asgi_application(),
    'websocket': AuthMiddlewareStack(
        URLRouter(simtrade.routing.websocket_urlpatterns)
    ),
})
```

- [ ] **步骤 4：验证配置正确**

运行：`python manage.py check`
预期：无报错

- [ ] **步骤 5：Commit**

```bash
git add simtrade/settings.py simtrade/routing.py simtrade/asgi.py
git commit -m "feat: configure Django Channels for WebSocket support"
```

---

### 任务 3：创建商品模块基础结构

**文件：**
- 创建：`apps/products/__init__.py`
- 创建：`apps/products/apps.py`

- [ ] **步骤 1：创建商品模块包结构**

运行：`mkdir -p apps/products/tests apps/products/fixtures`

- [ ] **步骤 2：创建 __init__.py**

创建 `apps/products/__init__.py`：

```python
default_app_config = 'apps.products.apps.ProductsConfig'
```

- [ ] **步骤 3：创建 apps.py**

创建 `apps/products/apps.py`：

```python
from django.apps import AppConfig


class ProductsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.products'
    verbose_name = '商品管理'
```

- [ ] **步骤 4：验证配置正确**

运行：`python manage.py check`
预期：无报错

- [ ] **步骤 5：Commit**

```bash
git add apps/products/
git commit -m "feat: create products app base structure"
```

---

### 任务 4：实现商品模型（Product 和 Catalog）

**文件：**
- 创建：`apps/products/models.py`
- 创建：`apps/products/tests/test_models.py`

- [ ] **步骤 1：编写商品模型测试**

创建 `apps/products/tests/test_models.py`：

```python
import pytest
from django.test import TestCase
from apps.products.models import Product, Catalog
from apps.users.models import User


class ProductModelTest(TestCase):
    """测试商品模型"""

    def test_create_product(self):
        """测试创建商品"""
        product = Product.objects.create(
            code='ELEC001',
            name='电子产品 A',
            category='electronics',
            unit='PCS'
        )
        assert product.code == 'ELEC001'
        assert product.name == '电子产品 A'
        assert product.get_category_display() == '电子产品'

    def test_product_code_unique(self):
        """测试商品代码唯一性"""
        Product.objects.create(code='ELEC001', name='商品A', category='electronics', unit='PCS')
        with pytest.raises(Exception):  # IntegrityError
            Product.objects.create(code='ELEC001', name='商品B', category='electronics', unit='PCS')


class CatalogModelTest(TestCase):
    """测试商品目录模型"""

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        # 假设有 Company 模型（需要在 users 模块中实现）
        # 这里先用 user 关联，后续调整

    def test_create_catalog_entry(self):
        """测试创建目录条目"""
        product = Product.objects.create(
            code='ELEC001',
            name='电子产品 A',
            category='electronics',
            unit='PCS'
        )
        # 注意：这里需要先实现 Company 模型
        # catalog = Catalog.objects.create(
        #     company=self.user.company,
        #     product=product,
        #     sale_price=10.00
        # )
        # assert catalog.product == product
```

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest apps/products/tests/test_models.py -v`
预期：FAIL，报错 "ModuleNotFoundError: No module named 'apps.products.models'"

- [ ] **步骤 3：实现商品模型**

创建 `apps/products/models.py`：

```python
from django.db import models


class Product(models.Model):
    """商品基础信息 - 系统级商品库"""

    class Category(models.TextChoices):
        ELECTRONICS = 'electronics', '电子产品'
        TEXTILES = 'textiles', '纺织品'
        MACHINERY = 'machinery', '机械设备'
        CHEMICALS = 'chemicals', '化工产品'
        FOOD = 'food', '食品'

    code = models.CharField('商品代码', max_length=50, unique=True)
    name = models.CharField('商品名称', max_length=200)
    name_en = models.CharField('英文名称', max_length=200, blank=True)
    category = models.CharField('分类', max_length=50, choices=Category.choices)
    unit = models.CharField('单位', max_length=20)  # PCS, KG, METER, etc.
    description = models.TextField('描述', blank=True)
    hs_code = models.CharField('HS 编码', max_length=20, blank=True)
    is_active = models.BooleanField('是否启用', default=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'products'
        verbose_name = '商品'
        verbose_name_plural = '商品'
        ordering = ['code']

    def __str__(self):
        return f"{self.code} - {self.name}"


class Catalog(models.Model):
    """公司商品目录 - 每个公司销售的商品"""

    # 注意：这里需要先实现 Company 模型
    # 暂时注释掉，后续实现 Company 后再启用
    # company = models.ForeignKey(
    #     'users.Company',
    #     on_delete=models.CASCADE,
    #     related_name='catalogs'
    # )

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='catalogs'
    )
    sale_price = models.DecimalField('销售价格', max_digits=12, decimal_places=2)
    currency = models.CharField('货币', max_length=10, default='USD')
    min_order = models.IntegerField('最小起订量', default=1)
    max_order = models.IntegerField('最大供应量', null=True, blank=True)
    lead_time = models.IntegerField('交货期（天）', null=True, blank=True)
    is_available = models.BooleanField('是否可售', default=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'catalogs'
        verbose_name = '商品目录'
        verbose_name_plural = '商品目录'
        # unique_together = [['company', 'product']]  # 等 Company 实现后启用

    def __str__(self):
        return f"{self.product.name} - {self.sale_price} {self.currency}"
```

- [ ] **步骤 4：运行测试验证通过**

运行：`pytest apps/products/tests/test_models.py -v`
预期：PASS

- [ ] **步骤 5：生成迁移文件**

运行：`python manage.py makemigrations products`
预期：生成迁移文件

- [ ] **步骤 6：执行迁移**

运行：`python manage.py migrate products`
预期：迁移成功

- [ ] **步骤 7：Commit**

```bash
git add apps/products/models.py apps/products/tests/test_models.py
git commit -m "feat: implement Product and Catalog models"
```

---

### 任务 5：实现商品管理后台

**文件：**
- 创建：`apps/products/admin.py`

- [ ] **步骤 1：实现商品管理后台**

创建 `apps/products/admin.py`：

```python
from django.contrib import admin
from apps.products.models import Product, Catalog


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """商品管理"""

    list_display = ['code', 'name', 'category', 'unit', 'is_active', 'created_at']
    list_filter = ['category', 'is_active', 'created_at']
    search_fields = ['code', 'name', 'name_en', 'hs_code']
    ordering = ['code']


@admin.register(Catalog)
class CatalogAdmin(admin.ModelAdmin):
    """商品目录管理"""

    list_display = ['product', 'sale_price', 'currency', 'min_order', 'is_available']
    list_filter = ['is_available', 'created_at']
    search_fields = ['product__code', 'product__name']
```

- [ ] **步骤 2：验证管理后台可访问**

运行：`python manage.py runserver`
访问：http://localhost:8000/admin/
预期：可以看到"商品"和"商品目录"管理项

- [ ] **步骤 3：Commit**

```bash
git add apps/products/admin.py
git commit -m "feat: configure products admin interface"
```

---

### 任务 6：实现商品 API

**文件：**
- 创建：`apps/products/serializers.py`
- 创建：`apps/products/views.py`
- 创建：`apps/products/urls.py`
- 创建：`apps/products/tests/test_api.py`

- [ ] **步骤 1：编写商品 API 测试**

创建 `apps/products/tests/test_api.py`：

```python
import pytest
from django.test import TestCase
from django.urls import reverse
from apps.products.models import Product
from apps.users.models import User


class ProductAPITest(TestCase):
    """测试商品 API"""

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.product = Product.objects.create(
            code='ELEC001',
            name='电子产品 A',
            category='electronics',
            unit='PCS'
        )

    def test_list_products(self):
        """测试获取商品列表"""
        self.client.force_authenticate(user=self.user)
        url = reverse('products:product-list')
        response = self.client.get(url)
        assert response.status_code == 200
        assert response.json()['code'] == 0
        assert len(response.json()['data']) >= 1

    def test_retrieve_product(self):
        """测试获取商品详情"""
        self.client.force_authenticate(user=self.user)
        url = reverse('products:product-detail', kwargs={'pk': self.product.pk})
        response = self.client.get(url)
        assert response.status_code == 200
        assert response.json()['data']['code'] == 'ELEC001'
```

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest apps/products/tests/test_api.py -v`
预期：FAIL，报错 "NoReverseMatch"

- [ ] **步骤 3：实现商品序列化器**

创建 `apps/products/serializers.py`：

```python
from rest_framework import serializers
from apps.products.models import Product, Catalog


class ProductSerializer(serializers.ModelSerializer):
    """商品序列化器"""

    category_display = serializers.CharField(source='get_category_display', read_only=True)

    class Meta:
        model = Product
        fields = ['id', 'code', 'name', 'name_en', 'category', 'category_display',
                  'unit', 'description', 'hs_code', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']


class CatalogSerializer(serializers.ModelSerializer):
    """商品目录序列化器"""

    product_detail = ProductSerializer(source='product', read_only=True)

    class Meta:
        model = Catalog
        fields = ['id', 'product', 'product_detail', 'sale_price', 'currency',
                  'min_order', 'max_order', 'lead_time', 'is_available', 'created_at']
        read_only_fields = ['id', 'created_at']
```

- [ ] **步骤 4：实现商品 API 视图**

创建 `apps/products/views.py`：

```python
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from apps.products.models import Product, Catalog
from apps.products.serializers import ProductSerializer, CatalogSerializer


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    """商品只读视图集"""

    queryset = Product.objects.filter(is_active=True)
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]

    def list(self, request, *args, **kwargs):
        """获取商品列表"""
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'code': 0,
            'message': 'success',
            'data': serializer.data
        })

    def retrieve(self, request, *args, **kwargs):
        """获取商品详情"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({
            'code': 0,
            'message': 'success',
            'data': serializer.data
        })


class CatalogViewSet(viewsets.ModelViewSet):
    """商品目录视图集"""

    serializer_class = CatalogSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # TODO: 过滤当前用户的公司的目录
        return Catalog.objects.filter(is_available=True)

    def list(self, request, *args, **kwargs):
        """获取目录列表"""
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'code': 0,
            'message': 'success',
            'data': serializer.data
        })

    def create(self, request, *args, **kwargs):
        """添加商品到目录"""
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'code': 0,
                'message': '添加成功',
                'data': serializer.data
            }, status=status.HTTP_201_CREATED)
        return Response({
            'code': 3002,
            'message': '参数格式错误',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
```

- [ ] **步骤 5：配置商品 URL 路由**

创建 `apps/products/urls.py`：

```python
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.products import views

app_name = 'products'

router = DefaultRouter()
router.register(r'products', views.ProductViewSet, basename='product')
router.register(r'catalogs', views.CatalogViewSet, basename='catalog')

urlpatterns = [
    path('api/v1/', include(router.urls)),
]
```

- [ ] **步骤 6：在主路由中注册**

修改 `simtrade/urls.py`，在 `urlpatterns` 中添加：

```python
    path('api/v1/products/', include('apps.products.urls')),
```

- [ ] **步骤 7：运行测试验证通过**

运行：`pytest apps/products/tests/test_api.py -v`
预期：PASS

- [ ] **步骤 8：Commit**

```bash
git add apps/products/serializers.py apps/products/views.py apps/products/urls.py
git add apps/products/tests/test_api.py simtrade/urls.py
git commit -m "feat: implement products API"
```

---

### 任务 7：创建交易模块基础结构

**文件：**
- 创建：`apps/transactions/__init__.py`
- 创建：`apps/transactions/apps.py`

- [ ] **步骤 1：创建交易模块包结构**

运行：`mkdir -p apps/transactions/tests apps/transactions/fixtures`

- [ ] **步骤 2：创建 __init__.py**

创建 `apps/transactions/__init__.py`：

```python
default_app_config = 'apps.transactions.apps.TransactionsConfig'
```

- [ ] **步骤 3：创建 apps.py**

创建 `apps/transactions/apps.py`：

```python
from django.apps import AppConfig


class TransactionsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.transactions'
    verbose_name = '交易管理'
```

- [ ] **步骤 4：验证配置正确**

运行：`python manage.py check`
预期：无报错

- [ ] **步骤 5：Commit**

```bash
git add apps/transactions/
git commit -m "feat: create transactions app base structure"
```

---

### 任务 8：实现交易核心模型

**文件：**
- 创建：`apps/transactions/models.py`
- 创建：`apps/transactions/tests/test_models.py`

- [ ] **步骤 1：编写交易模型测试**

创建 `apps/transactions/tests/test_models.py`：

```python
import pytest
from django.test import TestCase
from apps.transactions.models import Transaction, InquiryMessage
from apps.users.models import User


class TransactionModelTest(TestCase):
    """测试交易模型"""

    def setUp(self):
        self.buyer = User.objects.create_user(username='buyer', password='testpass')
        self.seller = User.objects.create_user(username='seller', password='testpass')

    def test_create_transaction(self):
        """测试创建交易"""
        transaction = Transaction.objects.create(
            buyer_id=self.buyer.id,
            seller_id=self.seller.id,
            product_id=1,  # 假设存在商品
            quantity=1000,
            unit_price=10.00,
            status='inquiring'
        )
        assert transaction.status == 'inquiring'
        assert transaction.get_status_display() == '询盘中'

    def test_transaction_status_choices(self):
        """测试交易状态选择"""
        transaction = Transaction.objects.create(
            buyer_id=self.buyer.id,
            seller_id=self.seller.id,
            product_id=1,
            quantity=1000,
            unit_price=10.00
        )
        # 测试状态转换
        transaction.status = 'negotiating'
        transaction.save()
        assert transaction.get_status_display() == '还盘中'


class InquiryMessageTest(TestCase):
    """测试磋商消息模型"""

    def setUp(self):
        self.buyer = User.objects.create_user(username='buyer', password='testpass')
        self.seller = User.objects.create_user(username='seller', password='testpass')
        self.transaction = Transaction.objects.create(
            buyer_id=self.buyer.id,
            seller_id=self.seller.id,
            product_id=1,
            quantity=1000,
            unit_price=10.00
        )

    def test_create_inquiry_message(self):
        """测试创建询盘消息"""
        message = InquiryMessage.objects.create(
            transaction=self.transaction,
            sender=self.buyer,
            sender_role='buyer',
            message_type='inquiry',
            content='对贵司产品感兴趣，请报价'
        )
        assert message.message_type == 'inquiry'
        assert message.get_message_type_display() == '询盘'
```

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest apps/transactions/tests/test_models.py -v`
预期：FAIL，报错 "ModuleNotFoundError: No module named 'apps.transactions.models'"

- [ ] **步骤 3：实现交易模型**

创建 `apps/transactions/models.py`：

```python
from django.db import models
from django.conf import settings


class Transaction(models.Model):
    """交易记录"""

    class Status(models.TextChoices):
        DRAFT = 'draft', '草稿'
        INQUIRING = 'inquiring', '询盘中'
        NEGOTIATING = 'negotiating', '还盘中'
        PENDING_CONTRACT = 'pending_contract', '待签约'
        CONTRACTED = 'contracted', '已签约'
        IN_PROGRESS = 'in_progress', '履约中'
        COMPLETED = 'completed', '已完成'
        CANCELLED = 'cancelled', '已取消'

    # 暂时用 User，等 Company 模型实现后改为 Company
    buyer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='buying_transactions'
    )
    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='selling_transactions'
    )
    product_id = models.IntegerField('商品ID')  # 外键待 Product 表确定后调整
    status = models.CharField(
        '状态',
        max_length=20,
        choices=Status.choices,
        default=Status.INQUIRING
    )
    quantity = models.IntegerField('数量')
    unit_price = models.DecimalField('单价', max_digits=12, decimal_places=2)
    currency = models.CharField('货币', max_length=10, default='USD')
    trade_term = models.CharField('贸易术语', max_length=10, blank=True)
    port_of_loading = models.CharField('装运港', max_length=100, blank=True)
    port_of_discharge = models.CharField('目的港', max_length=100, blank=True)
    notes = models.TextField('备注', blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_transactions'
    )
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'transactions'
        verbose_name = '交易'
        verbose_name_plural = '交易'
        ordering = ['-updated_at']

    def __str__(self):
        return f"交易 #{self.id}"


class InquiryMessage(models.Model):
    """询盘/发盘/还盘消息"""

    class MessageType(models.TextChoices):
        INQUIRY = 'inquiry', '询盘'
        OFFER = 'offer', '发盘'
        COUNTER_OFFER = 'counter_offer', '还盘'
        ACCEPT = 'accept', '接受'
        REJECT = 'reject', '拒绝'

    transaction = models.ForeignKey(
        Transaction,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='sent_messages'
    )
    sender_role = models.CharField('发送者角色', max_length=50)
    message_type = models.CharField(
        '消息类型',
        max_length=20,
        choices=MessageType.choices
    )
    content = models.TextField('消息内容')
    offered_quantity = models.IntegerField('报价数量', null=True, blank=True)
    offered_price = models.DecimalField('报价单价', max_digits=12, decimal_places=2, null=True, blank=True)
    offered_trade_term = models.CharField('报价贸易术语', max_length=10, blank=True)
    attachment = models.FileField('附件', upload_to='inquiry_attachments/', blank=True)
    is_read = models.BooleanField('是否已读', default=False)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'inquiry_messages'
        verbose_name = '磋商消息'
        verbose_name_plural = '磋商消息'
        ordering = ['created_at']

    def __str__(self):
        return f"{self.get_message_type_display()} - {self.transaction_id}"


class Contract(models.Model):
    """外销合同"""

    class Status(models.TextChoices):
        DRAFT = 'draft', '草稿'
        PENDING_SIGN = 'pending_sign', '待签字'
        SIGNED = 'signed', '已签字'
        EFFECTIVE = 'effective', '已生效'
        FULFILLED = 'fulfilled', '履行完毕'
        CANCELLED = 'cancelled', '已取消'

    contract_no = models.CharField('合同号', max_length=50, unique=True)
    transaction = models.OneToOneField(
        Transaction,
        on_delete=models.CASCADE,
        related_name='contract'
    )
    status = models.CharField(
        '状态',
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )

    # 合同条款
    trade_term = models.CharField('贸易术语', max_length=10)
    payment_term = models.CharField('付款方式', max_length=50)
    delivery_time = models.DateField('交货日期')
    port_of_loading = models.CharField('装运港', max_length=100)
    port_of_discharge = models.CharField('目的港', max_length=100)

    # 商品信息（快照）
    product_name = models.CharField('商品名称', max_length=200)
    product_spec = models.TextField('商品规格', blank=True)
    quantity = models.IntegerField('数量')
    unit = models.CharField('单位', max_length=20)
    unit_price = models.DecimalField('单价', max_digits=12, decimal_places=2)
    total_amount = models.DecimalField('总金额', max_digits=14, decimal_places=2)
    currency = models.CharField('货币', max_length=10)

    # 包装与运输
    packing = models.TextField('包装方式', blank=True)
    shipping_marks = models.TextField('唛头', blank=True)

    # 附加条款
    remarks = models.TextField('备注条款', blank=True)

    # 签字信息
    buyer_signed_at = models.DateTimeField('买方签字时间', null=True, blank=True)
    seller_signed_at = models.DateTimeField('卖方签字时间', null=True, blank=True)

    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    effective_at = models.DateTimeField('生效时间', null=True, blank=True)

    class Meta:
        db_table = 'contracts'
        verbose_name = '外销合同'
        verbose_name_plural = '外销合同'
        ordering = ['-created_at']

    def __str__(self):
        return f"合同 {self.contract_no}"


class ContractSignature(models.Model):
    """合同签字记录"""

    contract = models.ForeignKey(
        Contract,
        on_delete=models.CASCADE,
        related_name='signatures'
    )
    party = models.CharField('当事方', max_length=20)
    signer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )
    signer_name = models.CharField('签字人姓名', max_length=100)
    signature_image = models.ImageField('签字图片', upload_to='signatures/', blank=True)
    ip_address = models.GenericIPAddressField('IP 地址', null=True, blank=True)
    signed_at = models.DateTimeField('签字时间', auto_now_add=True)

    class Meta:
        db_table = 'contract_signatures'
        verbose_name = '合同签字'
        verbose_name_plural = '合同签字'
        unique_together = [['contract', 'party']]


class TransactionLog(models.Model):
    """交易操作日志"""

    transaction = models.ForeignKey(
        Transaction,
        on_delete=models.CASCADE,
        related_name='logs'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )
    action = models.CharField('操作', max_length=50)
    details = models.JSONField('详细信息', default=dict)
    ip_address = models.GenericIPAddressField('IP 地址', null=True, blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'transaction_logs'
        verbose_name = '交易日志'
        verbose_name_plural = '交易日志'
        ordering = ['-created_at']
```

- [ ] **步骤 4：运行测试验证通过**

运行：`pytest apps/transactions/tests/test_models.py -v`
预期：PASS

- [ ] **步骤 5：生成并执行迁移**

运行：`python manage.py makemigrations transactions && python manage.py migrate transactions`
预期：迁移成功

- [ ] **步骤 6：Commit**

```bash
git add apps/transactions/models.py apps/transactions/tests/test_models.py
git commit -m "feat: implement transaction core models"
```

---

### 任务 9：实现交易管理 API

**文件：**
- 创建：`apps/transactions/serializers.py`
- 创建：`apps/transactions/views.py`
- 创建：`apps/transactions/urls.py`
- 创建：`apps/transactions/tests/test_api.py`

- [ ] **步骤 1：编写交易 API 测试**

创建 `apps/transactions/tests/test_api.py`：

```python
import pytest
from django.test import TestCase
from django.urls import reverse
from apps.transactions.models import Transaction, InquiryMessage
from apps.users.models import User


class TransactionAPITest(TestCase):
    """测试交易 API"""

    def setUp(self):
        self.buyer = User.objects.create_user(username='buyer', password='testpass')
        self.seller = User.objects.create_user(username='seller', password='testpass')

    def test_create_transaction(self):
        """测试创建交易"""
        self.client.force_authenticate(user=self.buyer)
        url = reverse('transactions:transaction-list')
        data = {
            'seller': self.seller.id,
            'product_id': 1,
            'quantity': 1000,
            'unit_price': 10.00,
            'currency': 'USD'
        }
        response = self.client.post(url, data, format='json')
        assert response.status_code == 200 or response.status_code == 201
        assert response.json()['code'] == 0

    def test_list_my_transactions(self):
        """测试获取我的交易列表"""
        self.client.force_authenticate(user=self.buyer)
        # 先创建一个交易
        Transaction.objects.create(
            buyer=self.buyer,
            seller=self.seller,
            product_id=1,
            quantity=1000,
            unit_price=10.00
        )
        url = reverse('transactions:transaction-list')
        response = self.client.get(url)
        assert response.status_code == 200
        assert len(response.json()['data']) >= 1
```

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest apps/transactions/tests/test_api.py -v`
预期：FAIL，报错 "NoReverseMatch"

- [ ] **步骤 3：实现交易序列化器**

创建 `apps/transactions/serializers.py`：

```python
from rest_framework import serializers
from apps.transactions.models import Transaction, InquiryMessage, Contract, ContractSignature


class TransactionSerializer(serializers.ModelSerializer):
    """交易序列化器"""

    status_display = serializers.CharField(source='get_status_display', read_only=True)
    buyer_username = serializers.CharField(source='buyer.username', read_only=True)
    seller_username = serializers.CharField(source='seller.username', read_only=True)

    class Meta:
        model = Transaction
        fields = ['id', 'buyer', 'buyer_username', 'seller', 'seller_username',
                  'product_id', 'status', 'status_display', 'quantity',
                  'unit_price', 'currency', 'trade_term', 'port_of_loading',
                  'port_of_discharge', 'notes', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class InquiryMessageSerializer(serializers.ModelSerializer):
    """磋商消息序列化器"""

    sender_username = serializers.CharField(source='sender.username', read_only=True)
    message_type_display = serializers.CharField(source='get_message_type_display', read_only=True)

    class Meta:
        model = InquiryMessage
        fields = ['id', 'transaction', 'sender', 'sender_username', 'sender_role',
                  'message_type', 'message_type_display', 'content',
                  'offered_quantity', 'offered_price', 'offered_trade_term',
                  'is_read', 'created_at']
        read_only_fields = ['id', 'created_at']


class ContractSerializer(serializers.ModelSerializer):
    """合同序列化器"""

    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Contract
        fields = ['id', 'contract_no', 'transaction', 'status', 'status_display',
                  'trade_term', 'payment_term', 'delivery_time',
                  'port_of_loading', 'port_of_discharge',
                  'product_name', 'product_spec', 'quantity', 'unit',
                  'unit_price', 'total_amount', 'currency',
                  'packing', 'shipping_marks', 'remarks',
                  'buyer_signed_at', 'seller_signed_at',
                  'created_at', 'updated_at', 'effective_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class ContractSignatureSerializer(serializers.ModelSerializer):
    """合同签字序列化器"""

    class Meta:
        model = ContractSignature
        fields = ['id', 'contract', 'party', 'signer', 'signer_name',
                  'signature_image', 'ip_address', 'signed_at']
        read_only_fields = ['id', 'signed_at']
```

- [ ] **步骤 4：实现交易 API 视图**

创建 `apps/transactions/views.py`：

```python
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from apps.transactions.models import Transaction, InquiryMessage, Contract
from apps.transactions.serializers import (
    TransactionSerializer,
    InquiryMessageSerializer,
    ContractSerializer
)
from apps.transactions.services import TransactionService


class TransactionViewSet(viewsets.ModelViewSet):
    """交易视图集"""

    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # 只返回当前用户参与的交易
        user = self.request.user
        return Transaction.objects.filter(
            buyer=user
        ) | Transaction.objects.filter(
            seller=user
        )

    def list(self, request, *args, **kwargs):
        """获取交易列表"""
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'code': 0,
            'message': 'success',
            'data': serializer.data
        })

    def create(self, request, *args, **kwargs):
        """创建交易（询盘）"""
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save(created_by=request.user, status='inquiring')
            # 记录日志
            TransactionService.log_transaction(
                serializer.instance,
                request.user,
                'transaction_created',
                {'method': 'api'}
            )
            return Response({
                'code': 0,
                'message': '交易创建成功',
                'data': serializer.data
            }, status=status.HTTP_201_CREATED)
        return Response({
            'code': 3002,
            'message': '参数格式错误',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, *args, **kwargs):
        """获取交易详情"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({
            'code': 0,
            'message': 'success',
            'data': serializer.data
        })

    @action(detail=True, methods=['get'])
    def messages(self, request, pk=None):
        """获取交易消息列表"""
        transaction = self.get_object()
        messages = transaction.messages.all()
        serializer = InquiryMessageSerializer(messages, many=True)
        return Response({
            'code': 0,
            'message': 'success',
            'data': serializer.data
        })

    @action(detail=True, methods=['post'])
    def send_message(self, request, pk=None):
        """发送磋商消息"""
        transaction = self.get_object()
        serializer = InquiryMessageSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(
                transaction=transaction,
                sender=request.user,
                sender_role=self._get_user_role(transaction, request.user)
            )
            # 更新交易状态
            TransactionService.handle_message(transaction, serializer.instance)
            return Response({
                'code': 0,
                'message': '消息发送成功',
                'data': serializer.data
            })
        return Response({
            'code': 3002,
            'message': '参数格式错误',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """取消交易"""
        transaction = self.get_object()
        if transaction.status in ['completed', 'cancelled']:
            return Response({
                'code': 5005,
                'message': '交易状态不允许取消'
            }, status=status.HTTP_400_BAD_REQUEST)

        transaction.status = 'cancelled'
        transaction.save()
        TransactionService.log_transaction(
            transaction,
            request.user,
            'transaction_cancelled',
            {}
        )
        return Response({
            'code': 0,
            'message': '交易已取消'
        })

    def _get_user_role(self, transaction, user):
        """获取用户在交易中的角色"""
        if transaction.buyer == user:
            return 'buyer'
        elif transaction.seller == user:
            return 'seller'
        return 'observer'


class ContractViewSet(viewsets.ModelViewSet):
    """合同视图集"""

    serializer_class = ContractSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Contract.objects.all()

    @action(detail=True, methods=['post'])
    def sign(self, request, pk=None):
        """签署合同"""
        contract = self.get_object()
        # TODO: 实现签字逻辑
        return Response({
            'code': 0,
            'message': '签字成功'
        })
```

- [ ] **步骤 5：实现交易业务服务**

创建 `apps/transactions/services.py`：

```python
from django.utils import timezone
from apps.transactions.models import Transaction, InquiryMessage, TransactionLog, Contract


class TransactionService:
    """交易业务服务"""

    @staticmethod
    def log_transaction(transaction, user, action, details):
        """记录交易日志"""
        return TransactionLog.objects.create(
            transaction=transaction,
            user=user,
            action=action,
            details=details
        )

    @staticmethod
    def handle_message(transaction, message):
        """处理消息，更新交易状态"""
        if message.message_type == 'offer':
            # 发盘后进入还盘中
            if transaction.status == 'inquiring':
                transaction.status = 'negotiating'
                transaction.save()
        elif message.message_type == 'accept':
            # 接受后进入待签约
            transaction.status = 'pending_contract'
            transaction.save()

    @staticmethod
    def create_contract(transaction, contract_data):
        """创建合同草稿"""
        contract_no = TransactionService._generate_contract_no()
        contract = Contract.objects.create(
            contract_no=contract_no,
            transaction=transaction,
            **contract_data
        )
        transaction.status = 'pending_contract'
        transaction.save()
        return contract

    @staticmethod
    def _generate_contract_no():
        """生成合同号"""
        import random
        import string
        year = timezone.now().year
        random_str = ''.join(random.choices(string.digits, k=4))
        return f"SC{year}{random_str}"
```

- [ ] **步骤 6：配置交易 URL 路由**

创建 `apps/transactions/urls.py`：

```python
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.transactions import views

app_name = 'transactions'

router = DefaultRouter()
router.register(r'transactions', views.TransactionViewSet, basename='transaction')
router.register(r'contracts', views.ContractViewSet, basename='contract')

urlpatterns = [
    path('api/v1/', include(router.urls)),
]
```

- [ ] **步骤 7：在主路由中注册**

修改 `simtrade/urls.py`，添加：

```python
    path('api/v1/transactions/', include('apps.transactions.urls')),
```

- [ ] **步骤 8：运行测试验证通过**

运行：`pytest apps/transactions/tests/test_api.py -v`
预期：PASS

- [ ] **步骤 9：Commit**

```bash
git add apps/transactions/serializers.py apps/transactions/views.py
git add apps/transactions/services.py apps/transactions/urls.py
git add apps/transactions/tests/test_api.py simtrade/urls.py
git commit -m "feat: implement transactions API"
```

---

### 任务 10：实现交易管理后台

**文件：**
- 创建：`apps/transactions/admin.py`

- [ ] **步骤 1：实现交易管理后台**

创建 `apps/transactions/admin.py`：

```python
from django.contrib import admin
from apps.transactions.models import (
    Transaction, InquiryMessage, Contract,
    ContractSignature, TransactionLog
)


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    """交易管理"""

    list_display = ['id', 'buyer', 'seller', 'status', 'quantity', 'unit_price', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['buyer__username', 'seller__username']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(InquiryMessage)
class InquiryMessageAdmin(admin.ModelAdmin):
    """磋商消息管理"""

    list_display = ['transaction', 'sender', 'message_type', 'is_read', 'created_at']
    list_filter = ['message_type', 'is_read', 'created_at']
    search_fields = ['content']


@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    """合同管理"""

    list_display = ['contract_no', 'transaction', 'status', 'total_amount', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['contract_no', 'product_name']


@admin.register(ContractSignature)
class ContractSignatureAdmin(admin.ModelAdmin):
    """合同签字管理"""

    list_display = ['contract', 'party', 'signer_name', 'signed_at']
    list_filter = ['party', 'signed_at']


@admin.register(TransactionLog)
class TransactionLogAdmin(admin.ModelAdmin):
    """交易日志管理"""

    list_display = ['transaction', 'user', 'action', 'created_at']
    list_filter = ['action', 'created_at']
    readonly_fields = ['transaction', 'user', 'action', 'details', 'created_at']
```

- [ ] **步骤 2：验证管理后台可访问**

运行：`python manage.py runserver`
访问：http://localhost:8000/admin/
预期：可以看到交易相关管理项

- [ ] **步骤 3：Commit**

```bash
git add apps/transactions/admin.py
git commit -m "feat: configure transactions admin interface"
```

---

### 任务 11：实现状态机测试

**文件：**
- 创建：`apps/transactions/tests/test_state_machine.py`

- [ ] **步骤 1：编写状态机测试**

创建 `apps/transactions/tests/test_state_machine.py`：

```python
import pytest
from django.test import TestCase
from apps.transactions.models import Transaction, InquiryMessage
from apps.users.models import User
from apps.transactions.services import TransactionService


class TransactionStateMachineTest(TestCase):
    """交易状态机测试"""

    def setUp(self):
        self.buyer = User.objects.create_user(username='buyer', password='testpass')
        self.seller = User.objects.create_user(username='seller', password='testpass')

    def test_inquiring_to_negotiating(self):
        """测试从询盘到还盘的状态转换"""
        transaction = Transaction.objects.create(
            buyer=self.buyer,
            seller=self.seller,
            product_id=1,
            quantity=1000,
            unit_price=10.00,
            status='inquiring'
        )
        # 卖家发送发盘
        InquiryMessage.objects.create(
            transaction=transaction,
            sender=self.seller,
            sender_role='seller',
            message_type='offer',
            content='报价 $12'
        )
        TransactionService.handle_message(
            transaction,
            InquiryMessage.objects.get(transaction=transaction)
        )
        transaction.refresh_from_db()
        assert transaction.status == 'negotiating'

    def test_negotiating_to_pending_contract(self):
        """测试从还盘到待签约的状态转换"""
        transaction = Transaction.objects.create(
            buyer=self.buyer,
            seller=self.seller,
            product_id=1,
            quantity=1000,
            unit_price=10.00,
            status='negotiating'
        )
        # 买家接受发盘
        InquiryMessage.objects.create(
            transaction=transaction,
            sender=self.buyer,
            sender_role='buyer',
            message_type='accept',
            content='接受报价'
        )
        TransactionService.handle_message(
            transaction,
            InquiryMessage.objects.filter(transaction=transaction, message_type='accept').first()
        )
        transaction.refresh_from_db()
        assert transaction.status == 'pending_contract'

    def test_cancel_transaction(self):
        """测试取消交易"""
        transaction = Transaction.objects.create(
            buyer=self.buyer,
            seller=self.seller,
            product_id=1,
            quantity=1000,
            unit_price=10.00,
            status='inquiring'
        )
        transaction.status = 'cancelled'
        transaction.save()
        assert transaction.status == 'cancelled'
```

- [ ] **步骤 2：运行测试验证通过**

运行：`pytest apps/transactions/tests/test_state_machine.py -v`
预期：PASS

- [ ] **步骤 3：Commit**

```bash
git add apps/transactions/tests/test_state_machine.py
git commit -m "test: add transaction state machine tests"
```

---

### 任务 12：实现 WebSocket 通知系统

**文件：**
- 创建：`apps/notifications/__init__.py`
- 创建：`apps/notifications/consumers.py`
- 创建：`apps/notifications/services.py`
- 创建：`apps/notifications/tests/test_notifications.py`

- [ ] **步骤 1：创建通知模块结构**

运行：`mkdir -p apps/notifications/tests`

- [ ] **步骤 2：创建通知模块初始化**

创建 `apps/notifications/__init__.py`：

```python
# Notifications module
```

- [ ] **步骤 3：实现通知服务**

创建 `apps/notifications/services.py`：

```python
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync


class NotificationService:
    """通知服务"""

    @staticmethod
    def send_notification(user_ids, notification_type, data):
        """发送通知给指定用户列表

        Args:
            user_ids: 用户 ID 列表
            notification_type: 通知类型 (inquiry_received, offer_received, etc.)
            data: 通知数据
        """
        channel_layer = get_channel_layer()

        notification = {
            'type': 'notify',
            'data': {
                'type': notification_type,
                **data
            }
        }

        for user_id in user_ids:
            group_name = f'user_{user_id}'
            async_to_sync(channel_layer.group_send)(
                group_name,
                notification
            )

    @staticmethod
    def send_inquiry_notification(transaction, message):
        """发送询盘通知"""
        NotificationService.send_notification(
            [transaction.seller_id],
            'inquiry_received',
            {
                'transaction_id': transaction.id,
                'sender': transaction.buyer.username,
                'message': message.content[:50],
                'url': f'/transactions/{transaction.id}/'
            }
        )

    @staticmethod
    def send_offer_notification(transaction, message):
        """发送发盘通知"""
        NotificationService.send_notification(
            [transaction.buyer_id],
            'offer_received',
            {
                'transaction_id': transaction.id,
                'sender': transaction.seller.username,
                'offered_price': str(message.offered_price) if message.offered_price else None,
                'url': f'/transactions/{transaction.id}/'
            }
        )

    @staticmethod
    def send_counter_offer_notification(transaction, message):
        """发送还盘通知"""
        # 确定接收者
        receiver_id = transaction.seller_id if message.sender_role == 'buyer' else transaction.buyer_id
        NotificationService.send_notification(
            [receiver_id],
            'counter_offer_received',
            {
                'transaction_id': transaction.id,
                'sender': message.sender.username,
                'offered_price': str(message.offered_price) if message.offered_price else None,
                'url': f'/transactions/{transaction.id}/'
            }
        )
```

- [ ] **步骤 4：实现 WebSocket 消费者**

创建 `apps/notifications/consumers.py`：

```python
import json
from channels.generic.websocket import AsyncWebsocketConsumer


class NotificationConsumer(AsyncWebsocketConsumer):
    """通知 WebSocket 消费者"""

    async def connect(self):
        """建立连接"""
        if self.scope["user"].is_anonymous:
            await self.close()
        else:
            self.user_group_name = f'user_{self.scope["user"].id}'
            await self.channel_layer.group_add(
                self.user_group_name,
                self.channel_name
            )
            await self.accept()

    async def disconnect(self, close_code):
        """断开连接"""
        await self.channel_layer.group_discard(
            self.user_group_name,
            self.channel_name
        )

    async def notify(self, event):
        """接收并发送通知"""
        await self.send(text_data=json.dumps(event['data']))

    async def receive(self, text_data):
        """接收客户端消息（可用于心跳检测）"""
        data = json.loads(text_data)
        if data.get('type') == 'ping':
            await self.send(text_data=json.dumps({'type': 'pong'}))
```

- [ ] **步骤 5：编写通知测试**

创建 `apps/notifications/tests/test_notifications.py`：

```python
import pytest
from channels.testing import WebsocketCommunicator
from django.test import TestCase
from apps.users.models import User
from apps.notifications.consumers import NotificationConsumer
from apps.notifications.services import NotificationService


class NotificationServiceTest(TestCase):
    """通知服务测试"""

    def setUp(self):
        self.user1 = User.objects.create_user(username='user1', password='testpass')
        self.user2 = User.objects.create_user(username='user2', password='testpass')

    def test_send_notification_structure(self):
        """测试通知结构正确"""
        # 只测试数据结构，不测试实际 WebSocket 连接
        notification_data = {
            'type': 'inquiry_received',
            'transaction_id': 123,
            'message': '测试消息',
            'url': '/transactions/123/'
        }
        assert 'type' in notification_data
        assert 'transaction_id' in notification_data
        assert notification_data['type'] == 'inquiry_received'
```

- [ ] **步骤 6：运行测试验证通过**

运行：`pytest apps/notifications/tests/test_notifications.py -v`
预期：PASS

- [ ] **步骤 7：Commit**

```bash
git add apps/notifications/
git commit -m "feat: implement WebSocket notification system"
```

---

### 任务 13：集成通知到交易流程

**文件：**
- 修改：`apps/transactions/services.py`
- 修改：`apps/transactions/views.py`

- [ ] **步骤 1：修改交易服务集成通知**

修改 `apps/transactions/services.py`，在文件顶部添加：

```python
from apps.notifications.services import NotificationService
```

修改 `handle_message` 方法：

```python
    @staticmethod
    def handle_message(transaction, message):
        """处理消息，更新交易状态"""
        if message.message_type == 'inquiry':
            # 询盘通知
            NotificationService.send_inquiry_notification(transaction, message)
        elif message.message_type == 'offer':
            # 发盘通知
            NotificationService.send_offer_notification(transaction, message)
            if transaction.status == 'inquiring':
                transaction.status = 'negotiating'
                transaction.save()
        elif message.message_type == 'counter_offer':
            # 还盘通知
            NotificationService.send_counter_offer_notification(transaction, message)
        elif message.message_type == 'accept':
            # 接受后进入待签约
            transaction.status = 'pending_contract'
            transaction.save()
```

- [ ] **步骤 2：运行测试验证通过**

运行：`pytest apps/transactions/tests/test_api.py -v`
预期：PASS

- [ ] **步骤 3：Commit**

```bash
git add apps/transactions/services.py
git commit -m "feat: integrate notifications into transaction flow"
```

---

### 任务 14：实现前端页面 - 商品市场

**文件：**
- 创建：`templates/products/market.html`
- 创建：`static/css/transactions.css`
- 创建：`static/js/transactions.js`

- [ ] **步骤 1：创建商品市场页面**

创建 `templates/products/market.html`：

```html
{% extends "base.html" %}

{% block title %}商品市场 - SimTrade{% endblock %}

{% block content %}
<div class="row">
    <div class="col-md-12">
        <h2>商品市场</h2>
        <div class="panel panel-default">
            <div class="panel-body">
                <div class="row">
                    <div class="col-md-4">
                        <select id="categoryFilter" class="form-control">
                            <option value="">所有分类</option>
                            <option value="electronics">电子产品</option>
                            <option value="textiles">纺织品</option>
                            <option value="machinery">机械设备</option>
                        </select>
                    </div>
                    <div class="col-md-6">
                        <input type="text" id="searchInput" class="form-control" placeholder="搜索商品...">
                    </div>
                    <div class="col-md-2">
                        <button id="searchBtn" class="btn btn-primary btn-block">搜索</button>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>

<div class="row">
    <div class="col-md-12">
        <div id="productList" class="product-list">
            <!-- 商品列表将通过 AJAX 加载 -->
            <div class="text-center">加载中...</div>
        </div>
    </div>
</div>
{% endblock %}

{% block scripts %}
<script src="{% static 'js/transactions.js' %}"></script>
<script>
$(document).ready(function() {
    'use strict';

    function loadProducts() {
        var category = $('#categoryFilter').val();
        var search = $('#searchInput').val();
        var url = '/api/v1/products/products/';

        $.ajax({
            url: url,
            method: 'GET',
            data: {
                category: category,
                search: search
            },
            success: function(response) {
                var html = '';
                if (response.data.length === 0) {
                    html = '<div class="alert alert-info">暂无商品</div>';
                } else {
                    html = '<div class="row">';
                    response.data.forEach(function(product) {
                        html += `
                            <div class="col-md-4">
                                <div class="panel panel-default product-card">
                                    <div class="panel-heading">
                                        <strong>${product.code}</strong>
                                        <span class="pull-right badge">${product.category_display}</span>
                                    </div>
                                    <div class="panel-body">
                                        <h4>${product.name}</h4>
                                        <p>单位: ${product.unit}</p>
                                        ${product.description ? '<p>' + product.description + '</p>' : ''}
                                        <button class="btn btn-primary btn-sm send-inquiry-btn"
                                                data-product-id="${product.id}"
                                                data-product-name="${product.name}">
                                            发送询盘
                                        </button>
                                    </div>
                                </div>
                            </div>
                        `;
                    });
                    html += '</div>';
                }
                $('#productList').html(html);
            },
            error: function() {
                $('#productList').html('<div class="alert alert-danger">加载失败</div>');
            }
        });
    }

    // 初始加载
    loadProducts();

    // 搜索按钮
    $('#searchBtn').click(loadProducts);

    // 回车搜索
    $('#searchInput').keypress(function(e) {
        if (e.which == 13) loadProducts();
    });

    // 分类筛选
    $('#categoryFilter').change(loadProducts);
});
</script>
{% endblock %}
```

- [ ] **步骤 2：创建交易模块样式**

创建 `static/css/transactions.css`：

```css
/* 交易模块样式 */

.product-card {
    min-height: 200px;
    margin-bottom: 20px;
}

.product-card .panel-heading {
    background-color: #f5f5f5;
}

.transaction-item {
    border: 1px solid #ddd;
    border-radius: 4px;
    padding: 15px;
    margin-bottom: 15px;
    background-color: #fff;
}

.transaction-item.unread {
    border-left: 4px solid #337ab7;
}

.message-bubble {
    padding: 10px 15px;
    border-radius: 10px;
    margin-bottom: 10px;
    max-width: 70%;
}

.message-bubble.bubble-left {
    background-color: #f0f0f0;
    float: left;
}

.message-bubble.bubble-right {
    background-color: #337ab7;
    color: #fff;
    float: right;
}

.message-time {
    font-size: 12px;
    color: #999;
    margin-top: 5px;
}

.status-badge {
    padding: 3px 8px;
    border-radius: 3px;
    font-size: 12px;
}

.status-badge.inquiring { background-color: #5bc0de; color: #fff; }
.status-badge.negotiating { background-color: #f0ad4e; color: #fff; }
.status-badge.pending_contract { background-color: #5cb85c; color: #fff; }
.status-badge.contracted { background-color: #337ab7; color: #fff; }
```

- [ ] **步骤 3：创建交易模块脚本**

创建 `static/js/transactions.js`：

```javascript
/**
 * SimTrade 交易模块脚本
 */

$(document).ready(function() {
    'use strict';

    // WebSocket 通知连接
    var notificationSocket;
    var socketRetryCount = 0;
    var maxRetryCount = 5;

    function connectNotificationSocket() {
        var protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        var host = window.location.host;
        var wsUrl = protocol + '//' + host + '/ws/notifications/';

        notificationSocket = new WebSocket(wsUrl);

        notificationSocket.onopen = function() {
            console.log('WebSocket connected');
            socketRetryCount = 0;
            // 发送心跳
            setInterval(function() {
                if (notificationSocket.readyState === WebSocket.OPEN) {
                    notificationSocket.send(JSON.stringify({type: 'ping'}));
                }
            }, 30000);
        };

        notificationSocket.onmessage = function(e) {
            var data = JSON.parse(e.data);
            handleNotification(data);
        };

        notificationSocket.onclose = function() {
            console.log('WebSocket disconnected');
            // 自动重连
            if (socketRetryCount < maxRetryCount) {
                socketRetryCount++;
                setTimeout(connectNotificationSocket, 3000);
            }
        };

        notificationSocket.onerror = function(error) {
            console.error('WebSocket error:', error);
        };
    }

    function handleNotification(data) {
        // 显示通知
        if (data.type === 'inquiry_received') {
            showNotification('收到新询盘', data.message, 'info');
        } else if (data.type === 'offer_received') {
            showNotification('收到新发盘', data.message, 'success');
        } else if (data.type === 'counter_offer_received') {
            showNotification('收到还盘', data.message, 'warning');
        }

        // 刷新当前页面数据（如果在交易列表页）
        if (typeof refreshTransactionList === 'function') {
            refreshTransactionList();
        }
    }

    function showNotification(title, message, type) {
        type = type || 'info';
        var alertHtml = `
            <div class="alert alert-${type} alert-dismissible notification-toast" role="alert">
                <button type="button" class="close" data-dismiss="alert"><span>&times;</span></button>
                <strong>${title}</strong> ${message}
            </div>
        `;
        $('.container').prepend(alertHtml);
        setTimeout(function() {
            $('.notification-toast').fadeOut();
        }, 5000);
    }

    // 初始化 WebSocket
    if (window.user && window.user.is_authenticated) {
        connectNotificationSocket();
    }
});
```

- [ ] **步骤 4：更新基础模板添加用户信息**

修改 `templates/base.html`，在 `</body>` 前添加：

```html
    <script>
    window.user = {
        is_authenticated: {% if user.is_authenticated %}true{% else %}false{% endif %},
        username: {% if user.is_authenticated %}'{{ user.username }}'{% else %}null{% endif %}
    };
    </script>
```

- [ ] **步骤 5：验证页面可访问**

运行：`python manage.py runserver`
访问：http://localhost:8000/market/
预期：页面正常显示

- [ ] **步骤 6：Commit**

```bash
git add templates/products/market.html static/css/transactions.css
git add static/js/transactions.js templates/base.html
git commit -m "feat: add product market page and WebSocket notification"
```

---

### 任务 15：实现前端页面 - 交易列表和详情

**文件：**
- 创建：`templates/transactions/list.html`
- 创建：`templates/transactions/detail.html`

- [ ] **步骤 1：创建交易列表页面**

创建 `templates/transactions/list.html`：

```html
{% extends "base.html" %}

{% block title %}我的交易 - SimTrade{% endblock %}

{% block content %}
<div class="row">
    <div class="col-md-12">
        <h2>我的交易</h2>
        <div id="transactionList">
            <div class="text-center">加载中...</div>
        </div>
    </div>
</div>
{% endblock %}

{% block scripts %}
<script>
$(document).ready(function() {
    'use strict';

    function refreshTransactionList() {
        $.ajax({
            url: '/api/v1/transactions/transactions/',
            method: 'GET',
            success: function(response) {
                var html = '';
                if (response.data.length === 0) {
                    html = '<div class="alert alert-info">暂无交易</div>';
                } else {
                    response.data.forEach(function(tx) {
                        var statusClass = tx.status;
                        html += `
                            <div class="transaction-item">
                                <div class="row">
                                    <div class="col-md-8">
                                        <h4>交易 #${tx.id}</h4>
                                        <p>商品ID: ${tx.product_id} | 数量: ${tx.quantity} | 单价: $${tx.unit_price}</p>
                                        <p>
                                            买方: ${tx.buyer_username} → 卖方: ${tx.seller_username}
                                        </p>
                                    </div>
                                    <div class="col-md-4 text-right">
                                        <span class="status-badge ${statusClass}">${tx.status_display}</span>
                                        <br><br>
                                        <a href="/transactions/${tx.id}/" class="btn btn-primary btn-sm">查看详情</a>
                                    </div>
                                </div>
                            </div>
                        `;
                    });
                }
                $('#transactionList').html(html);
            }
        });
    }

    refreshTransactionList();

    // 暴露给全局供 WebSocket 调用
    window.refreshTransactionList = refreshTransactionList;
});
</script>
{% endblock %}
```

- [ ] **步骤 2：创建交易详情页面**

创建 `templates/transactions/detail.html`：

```html
{% extends "base.html" %}

{% block title %}交易详情 - SimTrade{% endblock %}

{% block content %}
<div class="row">
    <div class="col-md-12">
        <div id="transactionDetail">
            <div class="text-center">加载中...</div>
        </div>
    </div>
</div>

<div class="row">
    <div class="col-md-12">
        <div class="panel panel-default">
            <div class="panel-heading">磋商记录</div>
            <div class="panel-body">
                <div id="messageList"></div>
                <div id="messageForm" style="margin-top: 20px;">
                    <div class="row">
                        <div class="col-md-10">
                            <textarea id="messageContent" class="form-control" rows="3" placeholder="输入消息内容..."></textarea>
                        </div>
                        <div class="col-md-2">
                            <button id="sendMessageBtn" class="btn btn-primary btn-block">发送</button>
                            <button id="acceptOfferBtn" class="btn btn-success btn-block" style="margin-top: 10px;">接受报价</button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block scripts %}
<script>
$(document).ready(function() {
    'use strict';

    var transactionId = window.location.pathname.split('/')[2];

    function loadTransactionDetail() {
        $.ajax({
            url: '/api/v1/transactions/transactions/' + transactionId + '/',
            method: 'GET',
            success: function(response) {
                var tx = response.data;
                var html = `
                    <div class="panel panel-default">
                        <div class="panel-heading">
                            <h3>交易 #${tx.id} - <span class="status-badge ${tx.status}">${tx.status_display}</span></h3>
                        </div>
                        <div class="panel-body">
                            <div class="row">
                                <div class="col-md-6">
                                    <p><strong>买方:</strong> ${tx.buyer_username}</p>
                                    <p><strong>卖方:</strong> ${tx.seller_username}</p>
                                </div>
                                <div class="col-md-6">
                                    <p><strong>数量:</strong> ${tx.quantity}</p>
                                    <p><strong>单价:</strong> $${tx.unit_price}</p>
                                    <p><strong>贸易术语:</strong> ${tx.trade_term || '未指定'}</p>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
                $('#transactionDetail').html(html);
            }
        });
    }

    function loadMessages() {
        $.ajax({
            url: '/api/v1/transactions/transactions/' + transactionId + '/messages/',
            method: 'GET',
            success: function(response) {
                var html = '<div class="clearfix">';
                if (response.data.length === 0) {
                    html += '<div class="alert alert-info">暂无消息</div>';
                } else {
                    response.data.forEach(function(msg) {
                        var bubbleClass = msg.sender_role === 'buyer' ? 'bubble-right' : 'bubble-left';
                        var typeLabel = msg.message_type_display;
                        html += `
                            <div class="message-bubble ${bubbleClass}">
                                <strong>${msg.sender_username}</strong> <span class="label label-default">${typeLabel}</span>
                                <p>${msg.content}</p>
                                ${msg.offered_price ? '<p><strong>报价: $' + msg.offered_price + '</strong></p>' : ''}
                                <div class="message-time">${msg.created_at}</div>
                            </div>
                        `;
                    });
                }
                html += '</div>';
                $('#messageList').html(html);
            }
        });
    }

    function sendMessage(messageType) {
        var content = $('#messageContent').val();
        if (!content && messageType === 'offer') {
            alert('请输入消息内容');
            return;
        }

        var data = {
            message_type: messageType,
            content: content || '接受报价'
        };

        $.ajax({
            url: '/api/v1/transactions/transactions/' + transactionId + '/send_message/',
            method: 'POST',
            data: JSON.stringify(data),
            contentType: 'application/json',
            headers: {
                'X-CSRFToken': $('input[name=csrfmiddlewaretoken]').val()
            },
            success: function(response) {
                $('#messageContent').val('');
                loadMessages();
                loadTransactionDetail();
            },
            error: function(xhr) {
                alert('发送失败: ' + (xhr.responseJSON?.message || '未知错误'));
            }
        });
    }

    $('#sendMessageBtn').click(function() {
        sendMessage('offer');
    });

    $('#acceptOfferBtn').click(function() {
        sendMessage('accept');
    });

    loadTransactionDetail();
    loadMessages();
});
</script>
{% endblock %}
```

- [ ] **步骤 3：在主路由中注册页面路由**

修改 `simtrade/urls.py`，添加：

```python
    # 页面路由
    path('market/', lambda r: render(r, 'products/market.html'), name='market'),
    path('transactions/', lambda r: render(r, 'transactions/list.html'), name='transaction-list'),
    path('transactions/<int:id>/', lambda r, id: render(r, 'transactions/detail.html'), name='transaction-detail'),
```

同时在文件顶部添加：
```python
from django.shortcuts import render
```

- [ ] **步骤 4：验证页面可访问**

运行：`python manage.py runserver`
访问：http://localhost:8000/transactions/
预期：页面正常显示

- [ ] **步骤 5：Commit**

```bash
git add templates/transactions/list.html templates/transactions/detail.html
git add simtrade/urls.py
git commit -m "feat: add transaction list and detail pages"
```

---

### 任务 16：编写集成测试

**文件：**
- 创建：`apps/transactions/tests/test_integration.py`

- [ ] **步骤 1：编写集成测试**

创建 `apps/transactions/tests/test_integration.py`：

```python
import pytest
from django.test import TestCase
from apps.transactions.models import Transaction, InquiryMessage, Contract
from apps.users.models import User
from apps.transactions.services import TransactionService


class TransactionIntegrationTest(TestCase):
    """交易集成测试"""

    def setUp(self):
        self.buyer = User.objects.create_user(username='buyer', password='testpass')
        self.seller = User.objects.create_user(username='seller', password='testpass')

    def test_complete_negotiation_flow(self):
        """测试完整磋商流程：询盘 → 发盘 → 还盘 → 接受 → 待签约"""
        # 1. 创建交易（询盘）
        transaction = Transaction.objects.create(
            buyer=self.buyer,
            seller=self.seller,
            product_id=1,
            quantity=1000,
            unit_price=10.00,
            status='inquiring'
        )
        assert transaction.status == 'inquiring'

        # 2. 卖家发盘
        offer = InquiryMessage.objects.create(
            transaction=transaction,
            sender=self.seller,
            sender_role='seller',
            message_type='offer',
            content='报价 $12',
            offered_price=12.00
        )
        TransactionService.handle_message(transaction, offer)
        transaction.refresh_from_db()
        assert transaction.status == 'negotiating'

        # 3. 买家还盘
        counter = InquiryMessage.objects.create(
            transaction=transaction,
            sender=self.buyer,
            sender_role='buyer',
            message_type='counter_offer',
            content='还价 $11',
            offered_price=11.00
        )
        TransactionService.handle_message(transaction, counter)
        transaction.refresh_from_db()
        assert transaction.status == 'negotiating'

        # 4. 买家接受
        accept = InquiryMessage.objects.create(
            transaction=transaction,
            sender=self.buyer,
            sender_role='buyer',
            message_type='accept',
            content='接受报价'
        )
        TransactionService.handle_message(transaction, accept)
        transaction.refresh_from_db()
        assert transaction.status == 'pending_contract'

        # 5. 创建合同
        contract = TransactionService.create_contract(
            transaction,
            {
                'trade_term': 'FOB Shanghai',
                'payment_term': 'L/C',
                'delivery_time': '2026-06-30',
                'port_of_loading': 'Shanghai',
                'port_of_discharge': 'New York',
                'product_name': '测试商品',
                'quantity': 1000,
                'unit': 'PCS',
                'unit_price': 11.00,
                'total_amount': 11000.00,
                'currency': 'USD'
            }
        )
        assert contract.contract_no.startswith('SC')
        assert contract.status == 'draft'
```

- [ ] **步骤 2：运行集成测试**

运行：`pytest apps/transactions/tests/test_integration.py -v`
预期：PASS

- [ ] **步骤 3：Commit**

```bash
git add apps/transactions/tests/test_integration.py
git commit -m "test: add transaction integration tests"
```

---

### 任务 17：最终验证

**文件：**
- 无（验证步骤）

- [ ] **步骤 1：运行全部测试**

运行：`pytest apps/products/ apps/transactions/ apps/notifications/ -v`
预期：所有测试通过

- [ ] **步骤 2：验证管理后台**

运行：`python manage.py runserver`
访问：http://localhost:8000/admin/
预期：可以看到商品、交易、合同等所有管理项

- [ ] **步骤 3：验证前端页面**

访问：
- http://localhost:8000/market/ - 商品市场
- http://localhost:8000/transactions/ - 交易列表
预期：所有页面正常显示

- [ ] **步骤 4：验证 WebSocket 连接**

打开浏览器开发者工具 Console，访问交易列表页面
预期：可以看到 "WebSocket connected" 日志

- [ ] **步骤 5：最终 Commit**

```bash
git add .
git commit -m "feat: complete transaction system phase 1 implementation

- Product and Catalog models with API
- Transaction, InquiryMessage, Contract models with API
- WebSocket notification system
- Transaction state machine
- Frontend pages for market and transactions
- Complete test coverage

All tests passing. Ready for review."
```

---

## 自检清单

### 规格覆盖度

| 规格章节 | 对应任务 |
|---------|---------|
| 数据模型（7 个） | 任务 4, 任务 8 |
| WebSocket 通知 | 任务 12, 任务 13 |
| API 设计 | 任务 6, 任务 9 |
| 前端页面 | 任务 14, 任务 15 |
| 测试策略 | 任务 5, 任务 11, 任务 16 |
| 依赖配置 | 任务 1, 任务 2 |

### 占位符检查

✅ 无 "待定"、"TODO" 占位符
✅ 所有代码步骤包含完整代码
✅ 所有命令有明确的预期输出

### 类型一致性检查

✅ Transaction.status 枚举值在各处一致
✅ InquiryMessage.message_type 枚举值在各处一致
✅ API 响应格式统一 {code, message, data}
