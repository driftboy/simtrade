# Notifications 与 Products 模块补全设计文档

**版本**: 1.0
**日期**: 2026-05-24
**状态**: 待审核

---

## 1. 概述

### 1.1 设计目标

补全 notifications 和 products 两个模块的缺失功能，使其达到与其他模块（roles、scoring、teaching）同等的完整性。

### 1.2 核心决策

| 决策点 | 选择 | 理由 |
|--------|------|------|
| 通知持久化 | 新增 Notification 模型 | 用户离线不丢失通知，支持已读/未读管理 |
| 通知 UI | 导航栏铃铛 dropdown | 复用角色切换器模式，风格一致 |
| Catalog 归属 | 添加 Company FK | 支持每个公司独立商品目录 |
| Transaction 关联 | product_id → FK(Product) | 数据完整性，可级联查询商品详情 |
| 实现顺序 | notifications 先，products 后 | notifications 独立性强、风险低 |

---

## 2. Notifications 模块

### 2.1 Notification 模型

```python
class Notification(models.Model):
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
```

### 2.2 NotificationService 增强

修改现有 `services.py` 中的通知方法，在 WebSocket 推送的同时写入数据库：

- `send_inquiry_notification` → 创建 Notification 记录 + WS 推送
- `send_offer_notification` → 同上
- `send_counter_offer_notification` → 同上
- `send_lc_created_notification` → 同上
- 新增 `get_notifications(user, is_read=None)` — 查询用户通知列表
- 新增 `mark_as_read(notification_id, user)` — 标记单条已读
- 新增 `mark_all_read(user)` — 全部标记已读
- 新增 `get_unread_count(user)` — 获取未读数量

### 2.3 API 端点

| 端点 | 方法 | 说明 | 权限 |
|------|------|------|------|
| `/api/v1/notifications/` | GET | 获取通知列表（支持 `?is_read=true/false`） | 登录用户 |
| `/api/v1/notifications/{id}/` | DELETE | 删除通知 | 本人 |
| `/api/v1/notifications/{id}/read/` | POST | 标记已读 | 本人 |
| `/api/v1/notifications/read-all/` | POST | 全部标记已读 | 登录用户 |
| `/api/v1/notifications/unread-count/` | GET | 获取未读数 | 登录用户 |

### 2.4 通知铃铛 UI

在 `base.html` 导航栏角色切换器左侧添加通知铃铛：

- 图标：Bootstrap glyphicon-bell
- 未读数：红色 badge 角标
- Dropdown 展开最近 10 条通知
- 点击通知项跳转到关联交易
- "全部已读"按钮

### 2.5 文件变更

| 文件 | 变更 |
|------|------|
| `apps/notifications/models.py` | 新建，Notification 模型 |
| `apps/notifications/services.py` | 修改，增加持久化逻辑 |
| `apps/notifications/serializers.py` | 新建 |
| `apps/notifications/views.py` | 新建，NotificationViewSet |
| `apps/notifications/urls.py` | 新建 |
| `apps/notifications/admin.py` | 新建 |
| `apps/notifications/permissions.py` | 新建 |
| `apps/notifications/tests/test_models.py` | 新建 |
| `apps/notifications/tests/test_services.py` | 修改，增强测试 |
| `apps/notifications/tests/test_api.py` | 新建 |
| `static/css/notifications.css` | 新建，铃铛样式 |
| `static/js/notifications.js` | 新建，铃铛交互逻辑 |
| `templates/base.html` | 修改，添加铃铛 dropdown |

---

## 3. Products 模块

### 3.1 Catalog 添加 Company FK

```python
class Catalog(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='catalogs')
    company = models.ForeignKey(
        'roles.Company',
        on_delete=models.CASCADE,
        related_name='catalogs'
    )
    sale_price = models.DecimalField('销售价格', max_digits=12, decimal_places=2)
    currency = models.CharField('货币', max_length=10, default='USD')
    min_order = models.IntegerField('最小起订量', default=1)
    max_order = models.IntegerField('最大供应量', null=True, blank=True)
    lead_time = models.IntegerField('交货期(天)', default=7)
    is_available = models.BooleanField('是否可售', default=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'catalogs'
        unique_together = [['product', 'company']]
```

### 3.2 Transaction FK(Product)

将 `product_id = models.IntegerField('商品ID')` 改为：

```python
product = models.ForeignKey(
    'products.Product',
    on_delete=models.PROTECT,
    related_name='transactions'
)
```

同步修改序列化器中的字段名 `product_id` → `product`，添加 `product_name` 只读字段。

### 3.3 services.py

```python
class ProductService:
    @staticmethod
    def search_products(keyword='', category=''):
        """搜索商品"""
        # 返回 QuerySet

    @staticmethod
    def get_catalog_for_company(company_id):
        """获取公司商品目录"""
        # 返回 QuerySet

    @staticmethod
    def add_to_catalog(company_id, product_id, sale_price, **kwargs):
        """添加商品到公司目录"""
        # 返回 Catalog 实例

    @staticmethod
    def remove_from_catalog(catalog_id, user):
        """从公司目录移除商品"""
        # 返回 bool
```

### 3.4 数据初始化命令

`init_products` 管理命令，预置 10+ 种常见外贸商品：

- 电子产品：蓝牙耳机、智能手机
- 纺织品：纯棉T恤、牛仔布
- 机械设备：数控机床、发电机
- 化工产品：工业酒精、涂料
- 食品：茶叶、罐头

### 3.5 文件变更

| 文件 | 变更 |
|------|------|
| `apps/products/models.py` | 修改，Catalog 添加 company FK |
| `apps/products/services.py` | 新建 |
| `apps/products/views.py` | 修改，完善 ViewSet |
| `apps/products/serializers.py` | 修改，丰富字段 |
| `apps/products/permissions.py` | 新建 |
| `apps/products/management/commands/init_products.py` | 新建 |
| `apps/products/tests/test_services.py` | 新建 |
| `apps/products/tests/test_api.py` | 修改，完善测试 |
| `apps/transactions/models.py` | 修改，product_id → FK(Product) |
| `apps/transactions/serializers.py` | 修改，适配 product FK |
| `apps/transactions/tests/` | 修改，所有硬编码 product_id 改为创建 Product |

---

## 4. 实现顺序

1. **Notifications 模块**（独立，低风险）
   - 模型 → 服务层 → API → 测试 → UI
2. **Products 模块**（涉及 Transaction 改造）
   - Catalog 改造 → services → init_products → Transaction FK 迁移 → 测试修复

---

## 5. 测试策略

- notifications：模型测试 + 服务测试 + API 测试（目标 30+ 用例）
- products：模型测试 + 服务测试 + API 测试 + Transaction 迁移验证（目标 25+ 用例）
- 全量回归：最终运行 `pytest` 确认无破坏
