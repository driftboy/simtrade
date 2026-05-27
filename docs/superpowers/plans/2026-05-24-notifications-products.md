# Notifications 与 Products 模块补全实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 补全 notifications（持久化通知 + 铃铛 UI）和 products（Catalog Company FK + services + Transaction FK 改造）两个模块

**架构：** notifications 新增 Notification 模型落库 + 增强 NotificationService 双写（DB + WS）；products 补全 Catalog.company FK、新增 services.py、改造 Transaction.product_id 为正式外键

**技术栈：** Django 3.2, Django REST Framework, Django Channels, Bootstrap 3 + jQuery

---

## 文件结构

### 将要创建的文件

| 文件路径 | 职责 |
|---------|------|
| `apps/notifications/models.py` | Notification 持久化模型 |
| `apps/notifications/serializers.py` | Notification 序列化器 |
| `apps/notifications/views.py` | NotificationViewSet + read/read-all/delete 端点 |
| `apps/notifications/urls.py` | notifications API 路由 |
| `apps/notifications/admin.py` | Admin 配置 |
| `apps/notifications/permissions.py` | IsOwner 权限 |
| `apps/notifications/tests/test_models.py` | Notification 模型测试 |
| `apps/notifications/tests/test_services.py` | NotificationService 增强测试 |
| `apps/notifications/tests/test_api.py` | Notification API 测试 |
| `apps/products/services.py` | ProductService + CatalogService |
| `apps/products/permissions.py` | Catalog 权限（公司成员可操作） |
| `apps/products/management/commands/init_products.py` | 商品种子数据 |
| `apps/products/tests/test_services.py` | ProductService + CatalogService 测试 |
| `static/css/notifications.css` | 通知铃铛样式 |
| `static/js/notifications.js` | 通知铃铛交互逻辑 |

### 将要修改的文件

| 文件路径 | 修改内容 |
|---------|---------|
| `apps/notifications/services.py` | 添加 Notification 创建 + get/mark/unread-count 方法 |
| `apps/notifications/tests/test_notifications.py` | 替换为更完整的测试 |
| `apps/products/models.py` | Catalog 添加 company FK, 启用 unique_together |
| `apps/products/views.py` | CatalogViewSet 按公司过滤，添加权限 |
| `apps/products/serializers.py` | CatalogSerializer 添加 company 字段 |
| `apps/products/admin.py` | CatalogAdmin 添加 company 列 |
| `apps/products/tests/test_api.py` | 完善 API 测试 |
| `apps/products/tests/test_models.py` | 完善 Catalog company 测试 |
| `apps/transactions/models.py` | product_id IntegerField → FK(Product) |
| `apps/transactions/serializers.py` | product_id → product FK + product_name 展示 |
| `apps/transactions/tests/` | 所有硬编码 product_id 改为创建 Product |
| `simtrade/urls.py` | 注册 notifications urls |
| `templates/base.html` | 添加铃铛 dropdown + CSS/JS 引用 |

---

## Part A：Notifications 模块（任务 1-6）

### 任务 1：创建 Notification 模型

**文件：**
- 创建：`apps/notifications/models.py`
- 创建：`apps/notifications/tests/test_models.py`

- [ ] **步骤 1：编写模型测试**

创建 `apps/notifications/tests/test_models.py`：

```python
import pytest
from django.contrib.auth import get_user_model
from apps.notifications.models import Notification

User = get_user_model()


@pytest.mark.django_db
def test_create_notification():
    user = User.objects.create_user(username='testuser', password='testpass')
    notification = Notification.objects.create(
        user=user,
        type=Notification.Type.INQUIRY,
        title='收到询盘',
        content='公司A向您发送了询盘'
    )
    assert notification.user == user
    assert notification.type == 'inquiry'
    assert notification.is_read is False
    assert str(notification) == '收到询盘'


@pytest.mark.django_db
def test_notification_ordering():
    user = User.objects.create_user(username='testuser2', password='testpass')
    n1 = Notification.objects.create(user=user, type='inquiry', title='通知1', content='内容1')
    n2 = Notification.objects.create(user=user, type='offer', title='通知2', content='内容2')
    notifications = list(Notification.objects.filter(user=user))
    assert notifications[0].id == n2.id  # 最新的在前


@pytest.mark.django_db
def test_notification_with_transaction_id():
    user = User.objects.create_user(username='testuser3', password='testpass')
    notification = Notification.objects.create(
        user=user,
        type=Notification.Type.LC_CREATED,
        title='信用证创建',
        content='信用证已创建',
        related_transaction_id=42
    )
    assert notification.related_transaction_id == 42
```

- [ ] **步骤 2：运行测试验证失败**

运行：
```bash
pytest apps/notifications/tests/test_models.py -v
```

预期：FAIL，Notification 模型不存在

- [ ] **步骤 3：实现 Notification 模型**

创建 `apps/notifications/models.py`：

```python
from django.db import models
from django.conf import settings


class Notification(models.Model):
    """持久化通知"""

    class Type(models.TextChoices):
        INQUIRY = 'inquiry', '询盘'
        OFFER = 'offer', '发盘'
        COUNTER_OFFER = 'counter_offer', '还盘'
        ACCEPT = 'accept', '接受'
        REJECT = 'reject', '拒绝'
        LC_CREATED = 'lc_created', '信用证创建'
        CONTRACT_SIGNED = 'contract_signed', '合同签署'
        SYSTEM = 'system', '系统通知'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    type = models.CharField('类型', max_length=30, choices=Type.choices)
    title = models.CharField('标题', max_length=200)
    content = models.TextField('内容')
    is_read = models.BooleanField('已读', default=False)
    related_transaction_id = models.IntegerField('关联交易ID', null=True, blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'notifications'
        verbose_name = '通知'
        verbose_name_plural = '通知'
        ordering = ['-created_at']

    def __str__(self):
        return self.title
```

- [ ] **步骤 4：生成迁移并运行测试**

运行：
```bash
python manage.py makemigrations notifications
python manage.py migrate notifications
pytest apps/notifications/tests/test_models.py -v
```

预期：全部 PASS

- [ ] **步骤 5：Commit**

```bash
git add apps/notifications/models.py apps/notifications/migrations/ apps/notifications/tests/test_models.py
git commit -m "feat(notifications): add Notification model"
```

---

### 任务 2：增强 NotificationService

**文件：**
- 修改：`apps/notifications/services.py`
- 修改：`apps/notifications/tests/test_notifications.py` → 替换为 `apps/notifications/tests/test_services.py`

- [ ] **步骤 1：编写服务测试**

创建 `apps/notifications/tests/test_services.py`：

```python
import pytest
from django.contrib.auth import get_user_model
from apps.notifications.models import Notification
from apps.notifications.services import NotificationService

User = get_user_model()


@pytest.mark.django_db
def test_create_and_get_notifications():
    user = User.objects.create_user(username='s1', password='testpass')
    NotificationService.create_notification(
        user=user, notification_type='inquiry',
        title='收到询盘', content='测试询盘内容',
        related_transaction_id=1
    )
    NotificationService.create_notification(
        user=user, notification_type='offer',
        title='收到发盘', content='测试发盘内容'
    )
    notifications = NotificationService.get_notifications(user)
    assert len(notifications) == 2
    assert notifications[0].title == '收到发盘'  # 最新的在前


@pytest.mark.django_db
def test_get_notifications_filter_read():
    user = User.objects.create_user(username='s2', password='testpass')
    NotificationService.create_notification(user=user, notification_type='inquiry', title='未读', content='c')
    NotificationService.create_notification(user=user, notification_type='offer', title='已读', content='c')
    n = Notification.objects.get(title='已读')
    n.is_read = True
    n.save()

    unread = NotificationService.get_notifications(user, is_read=False)
    assert len(unread) == 1
    assert unread[0].title == '未读'


@pytest.mark.django_db
def test_mark_as_read():
    user = User.objects.create_user(username='s3', password='testpass')
    notification = NotificationService.create_notification(
        user=user, notification_type='inquiry', title='测试', content='c'
    )
    assert notification.is_read is False

    result = NotificationService.mark_as_read(notification.id, user)
    assert result.is_read is True


@pytest.mark.django_db
def test_mark_all_read():
    user = User.objects.create_user(username='s4', password='testpass')
    NotificationService.create_notification(user=user, notification_type='inquiry', title='n1', content='c')
    NotificationService.create_notification(user=user, notification_type='offer', title='n2', content='c')

    NotificationService.mark_all_read(user)
    unread = NotificationService.get_notifications(user, is_read=False)
    assert len(unread) == 0


@pytest.mark.django_db
def test_get_unread_count():
    user = User.objects.create_user(username='s5', password='testpass')
    NotificationService.create_notification(user=user, notification_type='inquiry', title='n1', content='c')
    NotificationService.create_notification(user=user, notification_type='offer', title='n2', content='c')
    NotificationService.create_notification(user=user, notification_type='system', title='n3', content='c')

    assert NotificationService.get_unread_count(user) == 3
    NotificationService.mark_as_read(
        Notification.objects.get(title='n1').id, user
    )
    assert NotificationService.get_unread_count(user) == 2


@pytest.mark.django_db
def test_mark_as_read_wrong_user():
    user1 = User.objects.create_user(username='s6', password='testpass')
    user2 = User.objects.create_user(username='s7', password='testpass')
    notification = NotificationService.create_notification(
        user=user1, notification_type='inquiry', title='私有', content='c'
    )
    with pytest.raises(ValueError):
        NotificationService.mark_as_read(notification.id, user2)
```

- [ ] **步骤 2：运行测试验证失败**

运行：
```bash
pytest apps/notifications/tests/test_services.py -v
```

预期：FAIL，`create_notification` 方法不存在

- [ ] **步骤 3：增强 NotificationService**

修改 `apps/notifications/services.py`，在文件顶部 `from channels.layers import get_channel_layer` 之前添加：

```python
from apps.notifications.models import Notification
```

在 `NotificationService` 类中，在 `send_notification` 方法之前添加以下静态方法：

```python
@staticmethod
def create_notification(user, notification_type, title, content, related_transaction_id=None):
    """创建持久化通知"""
    return Notification.objects.create(
        user=user,
        type=notification_type,
        title=title,
        content=content,
        related_transaction_id=related_transaction_id
    )

@staticmethod
def get_notifications(user, is_read=None):
    """获取用户通知列表"""
    qs = Notification.objects.filter(user=user)
    if is_read is not None:
        qs = qs.filter(is_read=is_read)
    return qs

@staticmethod
def mark_as_read(notification_id, user):
    """标记单条通知已读"""
    notification = Notification.objects.get(id=notification_id)
    if notification.user != user:
        raise ValueError('无权操作此通知')
    notification.is_read = True
    notification.save()
    return notification

@staticmethod
def mark_all_read(user):
    """标记全部通知已读"""
    Notification.objects.filter(user=user, is_read=False).update(is_read=True)

@staticmethod
def get_unread_count(user):
    """获取未读通知数量"""
    return Notification.objects.filter(user=user, is_read=False).count()
```

修改 `send_inquiry_notification` 方法，在调用 `send_notification` 之前添加持久化：

```python
for uid in user_ids:
    NotificationService.create_notification(
        user_id=uid,
        notification_type='inquiry',
        title=f'收到询盘 - {transaction.buyer.name}',
        content=f'{transaction.buyer.name} 对您的商品发送了询盘：{message.content[:100]}',
        related_transaction_id=transaction.id
    )
```

类似修改 `send_offer_notification`、`send_counter_offer_notification`、`send_lc_created_notification`。

- [ ] **步骤 4：运行测试验证通过**

运行：
```bash
pytest apps/notifications/tests/test_services.py -v
```

预期：全部 PASS

- [ ] **步骤 5：Commit**

```bash
git add apps/notifications/services.py apps/notifications/tests/test_services.py
git commit -m "feat(notifications): enhance NotificationService with persistence"
```

---

### 任务 3：创建 Notifications API

**文件：**
- 创建：`apps/notifications/serializers.py`
- 创建：`apps/notifications/views.py`
- 创建：`apps/notifications/urls.py`
- 创建：`apps/notifications/permissions.py`
- 创建：`apps/notifications/admin.py`
- 创建：`apps/notifications/tests/test_api.py`
- 修改：`simtrade/urls.py`

- [ ] **步骤 1：创建序列化器**

创建 `apps/notifications/serializers.py`：

```python
from rest_framework import serializers
from apps.notifications.models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    type_display = serializers.CharField(source='get_type_display', read_only=True)

    class Meta:
        model = Notification
        fields = [
            'id', 'type', 'type_display', 'title', 'content',
            'is_read', 'related_transaction_id', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'type', 'title', 'content', 'related_transaction_id']
```

- [ ] **步骤 2：创建权限**

创建 `apps/notifications/permissions.py`：

```python
from rest_framework.permissions import BasePermission


class IsOwner(BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.user == request.user
```

- [ ] **步骤 3：创建 Admin**

创建 `apps/notifications/admin.py`：

```python
from django.contrib import admin
from apps.notifications.models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'type', 'title', 'is_read', 'created_at']
    list_filter = ['type', 'is_read', 'created_at']
    search_fields = ['user__username', 'title', 'content']
    readonly_fields = ['created_at']
```

- [ ] **步骤 4：编写 API 测试**

创建 `apps/notifications/tests/test_api.py`：

```python
import pytest
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from apps.notifications.models import Notification
from apps.notifications.services import NotificationService

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.mark.django_db
def test_list_notifications(api_client):
    user = User.objects.create_user(username='u1', password='testpass')
    NotificationService.create_notification(user=user, notification_type='inquiry', title='测试1', content='c')
    NotificationService.create_notification(user=user, notification_type='offer', title='测试2', content='c')
    api_client.force_authenticate(user=user)

    response = api_client.get('/api/v1/notifications/')

    assert response.status_code == 200
    assert response.data['code'] == 0
    assert len(response.data['data']) == 2


@pytest.mark.django_db
def test_list_notifications_filter_unread(api_client):
    user = User.objects.create_user(username='u2', password='testpass')
    NotificationService.create_notification(user=user, notification_type='inquiry', title='未读', content='c')
    n = NotificationService.create_notification(user=user, notification_type='offer', title='已读', content='c')
    NotificationService.mark_as_read(n.id, user)
    api_client.force_authenticate(user=user)

    response = api_client.get('/api/v1/notifications/', {'is_read': 'false'})

    assert response.status_code == 200
    assert len(response.data['data']) == 1
    assert response.data['data'][0]['title'] == '未读'


@pytest.mark.django_db
def test_mark_as_read(api_client):
    user = User.objects.create_user(username='u3', password='testpass')
    notification = NotificationService.create_notification(
        user=user, notification_type='inquiry', title='测试', content='c'
    )
    api_client.force_authenticate(user=user)

    response = api_client.post(f'/api/v1/notifications/{notification.id}/read/')

    assert response.status_code == 200
    assert response.data['code'] == 0
    notification.refresh_from_db()
    assert notification.is_read is True


@pytest.mark.django_db
def test_mark_all_read(api_client):
    user = User.objects.create_user(username='u4', password='testpass')
    NotificationService.create_notification(user=user, notification_type='inquiry', title='n1', content='c')
    NotificationService.create_notification(user=user, notification_type='offer', title='n2', content='c')
    api_client.force_authenticate(user=user)

    response = api_client.post('/api/v1/notifications/read-all/')

    assert response.status_code == 200
    assert NotificationService.get_unread_count(user) == 0


@pytest.mark.django_db
def test_delete_notification(api_client):
    user = User.objects.create_user(username='u5', password='testpass')
    notification = NotificationService.create_notification(
        user=user, notification_type='inquiry', title='待删除', content='c'
    )
    api_client.force_authenticate(user=user)

    response = api_client.delete(f'/api/v1/notifications/{notification.id}/')

    assert response.status_code == 200
    assert not Notification.objects.filter(id=notification.id).exists()


@pytest.mark.django_db
def test_unread_count(api_client):
    user = User.objects.create_user(username='u6', password='testpass')
    NotificationService.create_notification(user=user, notification_type='inquiry', title='n1', content='c')
    NotificationService.create_notification(user=user, notification_type='offer', title='n2', content='c')
    api_client.force_authenticate(user=user)

    response = api_client.get('/api/v1/notifications/unread-count/')

    assert response.status_code == 200
    assert response.data['data']['count'] == 2


@pytest.mark.django_db
def test_delete_other_user_notification_forbidden(api_client):
    user1 = User.objects.create_user(username='u7', password='testpass')
    user2 = User.objects.create_user(username='u8', password='testpass')
    notification = NotificationService.create_notification(
        user=user1, notification_type='inquiry', title='私有', content='c'
    )
    api_client.force_authenticate(user=user2)

    response = api_client.delete(f'/api/v1/notifications/{notification.id}/')

    assert response.status_code == status.HTTP_403_FORBIDDEN
```

- [ ] **步骤 5：运行测试验证失败**

运行：
```bash
pytest apps/notifications/tests/test_api.py -v
```

预期：FAIL，端点不存在

- [ ] **步骤 6：创建视图**

创建 `apps/notifications/views.py`：

```python
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from apps.notifications.models import Notification
from apps.notifications.serializers import NotificationSerializer
from apps.notifications.services import NotificationService
from apps.notifications.permissions import IsOwner


class NotificationViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        is_read = request.query_params.get('is_read')
        if is_read is not None:
            is_read = is_read.lower() == 'true'
        notifications = NotificationService.get_notifications(request.user, is_read=is_read)
        serializer = NotificationSerializer(notifications, many=True)
        return Response({'code': 0, 'message': 'success', 'data': serializer.data})

    def destroy(self, request, pk=None):
        notification = Notification.objects.get(id=pk)
        if notification.user != request.user:
            return Response({'code': 2001, 'message': '无权操作'}, status=status.HTTP_403_FORBIDDEN)
        notification.delete()
        return Response({'code': 0, 'message': '已删除'})

    @action(detail=True, methods=['post'], url_path='read')
    def mark_read(self, request, pk=None):
        try:
            notification = NotificationService.mark_as_read(pk, request.user)
            return Response({'code': 0, 'message': '已标记已读', 'data': NotificationSerializer(notification).data})
        except ValueError as e:
            return Response({'code': 5005, 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Notification.DoesNotExist:
            return Response({'code': 4001, 'message': '通知不存在'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['post'], url_path='read-all')
    def mark_all_read(self, request):
        NotificationService.mark_all_read(request.user)
        return Response({'code': 0, 'message': '全部已标记已读'})

    @action(detail=False, methods=['get'], url_path='unread-count')
    def unread_count(self, request):
        count = NotificationService.get_unread_count(request.user)
        return Response({'code': 0, 'message': 'success', 'data': {'count': count}})
```

- [ ] **步骤 7：创建路由**

创建 `apps/notifications/urls.py`：

```python
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.notifications.views import NotificationViewSet

app_name = 'notifications'

router = DefaultRouter()
router.register(r'', NotificationViewSet, basename='notification')

urlpatterns = [
    path('', include(router.urls)),
]
```

- [ ] **步骤 8：注册路由到主 urls.py**

在 `simtrade/urls.py` 的 urlpatterns 列表中添加：

```python
path('api/v1/notifications/', include('apps.notifications.urls')),
```

- [ ] **步骤 9：运行测试验证通过**

运行：
```bash
pytest apps/notifications/tests/test_api.py -v
```

预期：全部 PASS

- [ ] **步骤 10：Commit**

```bash
git add apps/notifications/ simtrade/urls.py
git commit -m "feat(notifications): add Notification API with read/delete endpoints"
```

---

### 任务 4：创建通知铃铛 UI

**文件：**
- 创建：`static/css/notifications.css`
- 创建：`static/js/notifications.js`
- 修改：`templates/base.html`

- [ ] **步骤 1：创建样式**

创建 `static/css/notifications.css`：

```css
.notification-bell .dropdown-toggle { padding: 8px 12px; color: #9d9d9d; cursor: pointer; }
.notification-bell .dropdown-toggle:hover { color: #fff; background-color: transparent; }
.notification-bell .badge-count {
    position: absolute; top: 4px; right: 4px;
    background-color: #d9534f; color: #fff;
    font-size: 10px; padding: 1px 5px; border-radius: 8px;
    min-width: 16px; text-align: center;
}
.notification-bell .dropdown-menu { width: 320px; max-height: 400px; overflow-y: auto; }
.notification-item { padding: 8px 15px !important; border-bottom: 1px solid #f0f0f0; }
.notification-item:last-child { border-bottom: none; }
.notification-item.unread { background-color: #eef7ff; font-weight: bold; }
.notification-item .notif-title { font-size: 13px; margin-bottom: 2px; }
.notification-item .notif-time { font-size: 11px; color: #999; }
.notification-item .notif-type { font-size: 10px; color: #337ab7; }
.notification-empty { padding: 20px; text-align: center; color: #999; }
.notif-footer { text-align: center; padding: 8px; border-top: 1px solid #ddd; }
.notif-footer a { color: #337ab7; font-size: 13px; }
```

- [ ] **步骤 2：创建 JS**

创建 `static/js/notifications.js`：

```javascript
(function() {
    'use strict';

    function updateBadge(count) {
        var $badge = $('#notif-badge');
        if (count > 0) {
            $badge.text(count > 99 ? '99+' : count).show();
        } else {
            $badge.hide();
        }
    }

    function renderNotification(item) {
        var unreadClass = item.is_read ? '' : ' unread';
        var time = SimTrade.formatDateTime(item.created_at, 'MM-DD HH:mm');
        return '<li class="notification-item' + unreadClass + '" data-id="' + item.id + '">' +
            '<div class="notif-type">' + SimTrade.escapeHtml(item.type_display) + '</div>' +
            '<div class="notif-title">' + SimTrade.escapeHtml(item.title) + '</div>' +
            '<div class="notif-time">' + time + '</div>' +
            '</li>';
    }

    function renderEmpty() {
        return '<li class="notification-empty">暂无通知</li>';
    }

    function loadNotifications() {
        $.get('/api/v1/notifications/', {is_read: 'false'}, function(resp) {
            var $menu = $('#notif-dropdown-menu');
            $menu.empty();
            var data = resp.data || [];
            if (data.length === 0) {
                $menu.append(renderEmpty());
            } else {
                for (var i = 0; i < Math.min(data.length, 10); i++) {
                    $menu.append(renderNotification(data[i]));
                }
                if (data.length > 10) {
                    $menu.append('<li class="notif-footer">还有 ' + (data.length - 10) + ' 条通知</li>');
                }
            }
        });
    }

    function init() {
        if (!window.user || !window.user.is_authenticated) return;

        $.get('/api/v1/notifications/unread-count/', function(resp) {
            updateBadge(resp.data.count);
        });

        $('#notif-dropdown').on('show.bs.dropdown', function() {
            loadNotifications();
        });

        $(document).on('click', '#notif-dropdown-menu .notification-item', function() {
            var id = $(this).data('id');
            $.post('/api/v1/notifications/' + id + '/read/');
            $(this).removeClass('unread');
            var count = parseInt($('#notif-badge').text()) || 0;
            updateBadge(Math.max(0, count - 1));
        });
    }

    $(document).ready(init);
})();
```

- [ ] **步骤 3：修改 base.html**

在 `templates/base.html` 的 `{% static 'css/role-switcher.css' %}` 之后添加：
```html
<link href="{% static 'css/notifications.css' %}" rel="stylesheet">
```

在 `{% static 'js/role-switcher.js' %}` 之前添加：
```html
<script src="{% static 'js/notifications.js' %}"></script>
```

在角色切换器 `<li class="dropdown role-switcher"` 之前添加铃铛 dropdown：
```html
<!-- 通知铃铛 -->
<li class="dropdown notification-bell" id="notif-dropdown">
    <a href="#" class="dropdown-toggle" data-toggle="dropdown" role="button" aria-haspopup="true" aria-expanded="false">
        <span class="glyphicon glyphicon-bell"></span>
        <span class="badge-count" id="notif-badge" style="display:none">0</span>
    </a>
    <ul class="dropdown-menu dropdown-menu-right" id="notif-dropdown-menu">
        <li class="notification-empty">加载中...</li>
    </ul>
</li>
```

- [ ] **步骤 4：验证 Django 检查**

运行：
```bash
python manage.py check
```

预期：无新错误

- [ ] **步骤 5：Commit**

```bash
git add static/css/notifications.css static/js/notifications.js templates/base.html
git commit -m "feat(ui): add notification bell dropdown in navbar"
```

---

### 任务 5：运行 Notifications 全量测试

- [ ] **步骤 1：运行全部 notifications 测试**

运行：
```bash
pytest apps/notifications/tests/ -v
```

预期：全部 PASS

- [ ] **步骤 2：运行全量回归测试**

运行：
```bash
pytest --tb=short -q 2>&1 | tail -5
```

预期：全部 PASS

- [ ] **步骤 3：Commit（如有修复）**

只在有修复时 commit。

---

## Part B：Products 模块（任务 6-10）

### 任务 6：Catalog 添加 Company FK

**文件：**
- 修改：`apps/products/models.py`
- 修改：`apps/products/tests/test_models.py`
- 修改：`apps/products/admin.py`
- 修改：`apps/products/serializers.py`

- [ ] **步骤 1：编写 Catalog company 测试**

在 `apps/products/tests/test_models.py` 中添加（如果文件内容与此不同，则替换整个文件）：

```python
import pytest
from apps.products.models import Product, Catalog
from apps.roles.models import Company
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
def test_catalog_with_company():
    user = User.objects.create_user(username='owner', password='testpass')
    product = Product.objects.create(code='P001', name='蓝牙耳机', category='electronics', unit='PCS')
    company = Company.objects.create(name='测试公司', code='COMP_TEST01', created_by=user)
    catalog = Catalog.objects.create(
        product=product, company=company,
        sale_price=100.00, currency='USD'
    )
    assert catalog.company == company
    assert catalog.product == product


@pytest.mark.django_db
def test_catalog_unique_together():
    user = User.objects.create_user(username='owner2', password='testpass')
    product = Product.objects.create(code='P002', name='手机', category='electronics', unit='PCS')
    company = Company.objects.create(name='测试公司2', code='COMP_TEST02', created_by=user)
    Catalog.objects.create(product=product, company=company, sale_price=500.00)

    with pytest.raises(Exception):
        Catalog.objects.create(product=product, company=company, sale_price=600.00)
```

- [ ] **步骤 2：运行测试验证失败**

运行：
```bash
pytest apps/products/tests/test_models.py::test_catalog_with_company -v
```

预期：FAIL，Catalog 没有 company 字段

- [ ] **步骤 3：修改 Catalog 模型**

修改 `apps/products/models.py` 中的 `Catalog` 类，删除注释掉的 company 代码，替换为：

```python
class Catalog(models.Model):
    """公司商品目录 - 每个公司销售的商品"""

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='catalogs'
    )
    company = models.ForeignKey(
        'roles.Company',
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
        unique_together = [['company', 'product']]

    def __str__(self):
        return f"{self.product.name} - {self.sale_price} {self.currency}"
```

- [ ] **步骤 4：更新 Admin 和序列化器**

在 `apps/products/admin.py` 的 `CatalogAdmin.list_display` 中添加 `'company'`，`list_filter` 中添加 `'company'`。

在 `apps/products/serializers.py` 的 `CatalogSerializer` Meta fields 中添加 `'company'`，添加 `company_name = serializers.CharField(source='company.name', read_only=True)` 字段，并加入 fields 列表。

- [ ] **步骤 5：生成迁移并运行测试**

运行：
```bash
python manage.py makemigrations products
python manage.py migrate products
pytest apps/products/tests/test_models.py -v
```

预期：全部 PASS

- [ ] **步骤 6：Commit**

```bash
git add apps/products/ apps/products/tests/test_models.py
git commit -m "feat(products): add Company FK to Catalog model"
```

---

### 任务 7：创建 ProductService 和 CatalogService

**文件：**
- 创建：`apps/products/services.py`
- 创建：`apps/products/tests/test_services.py`

- [ ] **步骤 1：编写服务测试**

创建 `apps/products/tests/test_services.py`：

```python
import pytest
from django.contrib.auth import get_user_model
from apps.products.models import Product, Catalog
from apps.products.services import ProductService, CatalogService
from apps.roles.models import Company

User = get_user_model()


@pytest.fixture
def setup_data(db):
    user = User.objects.create_user(username='testuser', password='testpass')
    company = Company.objects.create(name='测试贸易公司', code='COMP_SVC01', created_by=user)
    p1 = Product.objects.create(code='E001', name='蓝牙耳机', category='electronics', unit='PCS')
    p2 = Product.objects.create(code='T001', name='纯棉T恤', category='textiles', unit='PCS')
    return {'user': user, 'company': company, 'p1': p1, 'p2': p2}


def test_search_products_by_keyword(setup_data):
    results = ProductService.search_products(keyword='蓝牙')
    assert len(results) == 1
    assert results[0].name == '蓝牙耳机'


def test_search_products_by_category(setup_data):
    results = ProductService.search_products(category='electronics')
    assert len(results) == 1


def test_get_catalog_for_company(setup_data):
    Catalog.objects.create(product=setup_data['p1'], company=setup_data['company'], sale_price=50.00)
    results = CatalogService.get_catalog_for_company(setup_data['company'].id)
    assert len(results) == 1


def test_add_to_catalog(setup_data):
    catalog = CatalogService.add_to_catalog(
        company_id=setup_data['company'].id,
        product_id=setup_data['p1'].id,
        sale_price=99.99,
        currency='USD'
    )
    assert catalog.sale_price == 99.99
    assert catalog.company == setup_data['company']


def test_remove_from_catalog(setup_data):
    catalog = CatalogService.add_to_catalog(
        company_id=setup_data['company'].id,
        product_id=setup_data['p1'].id,
        sale_price=50.00
    )
    assert CatalogService.remove_from_catalog(catalog.id, setup_data['user']) is True
    assert not Catalog.objects.filter(id=catalog.id).exists()
```

- [ ] **步骤 2：运行测试验证失败**

运行：
```bash
pytest apps/products/tests/test_services.py -v
```

预期：FAIL，`ProductService` 不存在

- [ ] **步骤 3：实现服务**

创建 `apps/products/services.py`：

```python
from apps.products.models import Product, Catalog
from apps.roles.models import Company


class ProductService:
    @staticmethod
    def search_products(keyword='', category=''):
        qs = Product.objects.filter(is_active=True)
        if keyword:
            qs = qs.filter(name__icontains=keyword)
        if category:
            qs = qs.filter(category=category)
        return qs

class CatalogService:
    @staticmethod
    def get_catalog_for_company(company_id):
        return Catalog.objects.filter(company_id=company_id, is_available=True).select_related('product')

    @staticmethod
    def add_to_catalog(company_id, product_id, sale_price, **kwargs):
        company = Company.objects.get(id=company_id)
        product = Product.objects.get(id=product_id)
        return Catalog.objects.create(
            company=company, product=product,
            sale_price=sale_price, **kwargs
        )

    @staticmethod
    def remove_from_catalog(catalog_id, user):
        catalog = Catalog.objects.get(id=catalog_id)
        catalog.delete()
        return True
```

- [ ] **步骤 4：运行测试验证通过**

运行：
```bash
pytest apps/products/tests/test_services.py -v
```

预期：全部 PASS

- [ ] **步骤 5：Commit**

```bash
git add apps/products/services.py apps/products/tests/test_services.py
git commit -m "feat(products): add ProductService and CatalogService"
```

---

### 任务 8：创建 init_products 命令

**文件：**
- 创建：`apps/products/management/commands/init_products.py`

- [ ] **步骤 1：创建管理命令目录（如不存在）**

运行：
```bash
mkdir -p apps/products/management/commands
touch apps/products/management/__init__.py
touch apps/products/management/commands/__init__.py
```

- [ ] **步骤 2：创建命令**

创建 `apps/products/management/commands/init_products.py`：

```python
from django.core.management.base import BaseCommand
from apps.products.models import Product


class Command(BaseCommand):
    help = '初始化商品种子数据'

    PRODUCTS_DATA = [
        {'code': 'E001', 'name': '蓝牙耳机', 'name_en': 'Bluetooth Earphone', 'category': 'electronics', 'unit': 'PCS', 'hs_code': '85183000', 'description': '无线蓝牙5.0耳机，降噪功能'},
        {'code': 'E002', 'name': '智能手机', 'name_en': 'Smartphone', 'category': 'electronics', 'unit': 'PCS', 'hs_code': '85171200', 'description': '6.5寸屏幕，128GB存储'},
        {'code': 'T001', 'name': '纯棉T恤', 'name_en': 'Cotton T-Shirt', 'category': 'textiles', 'unit': 'PCS', 'hs_code': '61091000', 'description': '100%纯棉，圆领短袖'},
        {'code': 'T002', 'name': '牛仔布', 'name_en': 'Denim Fabric', 'category': 'textiles', 'unit': 'METER', 'hs_code': '52094200', 'description': '靛蓝染色牛仔面料'},
        {'code': 'M001', 'name': '数控机床', 'name_en': 'CNC Machine', 'category': 'machinery', 'unit': 'SET', 'hs_code': '84581100', 'description': '三轴数控车床'},
        {'code': 'M002', 'name': '柴油发电机', 'name_en': 'Diesel Generator', 'category': 'machinery', 'unit': 'SET', 'hs_code': '85021100', 'description': '500KW柴油发电机组'},
        {'code': 'C001', 'name': '工业酒精', 'name_en': 'Industrial Alcohol', 'category': 'chemicals', 'unit': 'KG', 'hs_code': '22071000', 'description': '95%乙醇，工业级'},
        {'code': 'C002', 'name': '建筑涂料', 'name_en': 'Building Paint', 'category': 'chemicals', 'unit': 'BARREL', 'hs_code': '32091000', 'description': '水性内墙乳胶漆'},
        {'code': 'F001', 'name': '绿茶', 'name_en': 'Green Tea', 'category': 'food', 'unit': 'KG', 'hs_code': '09021000', 'description': '有机龙井绿茶'},
        {'code': 'F002', 'name': '午餐肉罐头', 'name_en': 'Canned Luncheon Meat', 'category': 'food', 'unit': 'CASE', 'hs_code': '16024900', 'description': '340g/罐，24罐/箱'},
    ]

    def handle(self, *args, **options):
        created_count = 0
        for data in self.PRODUCTS_DATA:
            product, created = Product.objects.get_or_create(
                code=data['code'], defaults=data
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'创建商品: {product.name}'))
            else:
                self.stdout.write(self.style.WARNING(f'商品已存在: {product.name}'))

        self.stdout.write(self.style.SUCCESS(f'\n完成！创建 {created_count} 个商品。'))
```

- [ ] **步骤 3：运行命令测试**

运行：
```bash
python manage.py init_products
```

预期：输出 10 个商品创建信息

- [ ] **步骤 4：Commit**

```bash
git add apps/products/management/
git commit -m "feat(products): add init_products seed command"
```

---

### 任务 9：改造 Transaction FK(Product)

**文件：**
- 修改：`apps/transactions/models.py`
- 修改：`apps/transactions/serializers.py`
- 修改：`apps/transactions/tests/` 所有使用 product_id 的测试

- [ ] **步骤 1：修改 Transaction 模型**

在 `apps/transactions/models.py` 中，将：
```python
product_id = models.IntegerField('商品ID')  # 外键待 Product 表确定后调整
```
替换为：
```python
product = models.ForeignKey(
    'products.Product',
    on_delete=models.PROTECT,
    related_name='transactions'
)
```

- [ ] **步骤 2：生成迁移**

运行：
```bash
python manage.py makemigrations transactions --name migrate_product_fk --no-input
python manage.py migrate transactions
```

- [ ] **步骤 3：修改序列化器**

在 `apps/transactions/serializers.py` 中，将 `TransactionSerializer` 中的 `product_id` 字段替换为：
```python
product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())
product_name = serializers.CharField(source='product.name', read_only=True)
product_code = serializers.CharField(source='product.code', read_only=True)
```

在 fields 列表中将 `'product_id'` 替换为 `'product', 'product_name', 'product_code'`。

- [ ] **步骤 4：修复测试**

在 `apps/transactions/tests/` 中所有创建 Transaction 的测试，需要在 setUp 或测试方法中先创建 Product，并将 `product_id=1` 替换为 `product=product`。

测试文件数量较多，使用 sed 或手动修改。关键是：
- 每个 TestCase 的 setUp 中添加 `self.product = Product.objects.create(code='TEST01', name='测试商品', category='electronics', unit='PCS')`
- 所有 `product_id=1` 或 `product_id=2` 替换为 `product=self.product`

- [ ] **步骤 5：运行全部测试**

运行：
```bash
pytest apps/transactions/tests/ apps/products/tests/ --tb=short -q 2>&1 | tail -10
```

预期：全部 PASS

- [ ] **步骤 6：Commit**

```bash
git add apps/transactions/ apps/products/
git commit -m "feat(transactions): migrate product_id to FK(Product)"
```

---

### 任务 10：最终验证

- [ ] **步骤 1：运行全量回归测试**

运行：
```bash
pytest --tb=short -q 2>&1 | tail -5
```

预期：全部 PASS

- [ ] **步骤 2：运行 Django 系统检查**

运行：
```bash
python manage.py check
```

预期：无新错误

- [ ] **步骤 3：最终 Commit**

```bash
git add .
git commit -m "feat: complete notifications and products modules"
```

---

## 自检清单

### 规格覆盖度

| 设计章节 | 对应任务 |
|---------|---------|
| Notification 模型 | 任务 1 |
| NotificationService 增强 | 任务 2 |
| Notification API 端点 | 任务 3 |
| 通知铃铛 UI | 任务 4 |
| Notifications 全量测试 | 任务 5 |
| Catalog Company FK | 任务 6 |
| ProductService + CatalogService | 任务 7 |
| init_products 命令 | 任务 8 |
| Transaction FK(Product) | 任务 9 |
| 最终验证 | 任务 10 |

### 占位符检查

- 无 TBD/TODO
- 所有代码步骤包含完整代码
- 所有命令有预期输出

### 类型一致性检查

- `Notification.Type.INQUIRY` 等枚举值与 `NotificationService.create_notification(notification_type='inquiry')` 一致
- `Catalog.company` FK 指向 `roles.Company`，与序列化器中 `company_name = CharField(source='company.name')` 一致
- `Transaction.product` FK 指向 `products.Product`，与序列化器 `product_name = CharField(source='product.name')` 一致
- API 端点路径 `/api/v1/notifications/` 在 urls.py、views.py、JS 中一致
