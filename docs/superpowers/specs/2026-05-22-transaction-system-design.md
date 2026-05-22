# 交易管理系统设计文档

**版本**: 1.0
**日期**: 2026-05-22
**作者**: Claude + 用户
**阶段**: 阶段 1 - 交易核心 + 基础设施

---

## 1. 概述

### 1.1 目标

实现 SimTrade 平台的交易管理核心功能，支持多角色协同模式下的完整外贸交易流程（阶段 1 聚焦交易磋商与合同签订）。

### 1.2 范围

**本阶段包含：**
- 交易模型与状态机
- 询盘/发盘/还盘磋商流程（完整消息记录）
- 合同管理与签字流程
- 商品管理系统
- WebSocket 实时通知框架

**后续阶段包含：**
- 信用证管理
- 生产订单
- 货运/保险/报关
- 角色工作台
- 教师管理功能

### 1.3 核心设计决策

| 决策点 | 选择 | 理由 |
|--------|------|------|
| 角色模式 | 多角色协同（世格模式） | 真实模拟外贸业务场景 |
| 消息通知 | WebSocket 实时推送 | 更好的用户体验 |
| 商品系统 | 完整商品系统 | 支持商品目录管理 |
| 数据模型 | 独立模型 | 清晰的数据关系，便于扩展 |
| 磋商流程 | 完整消息记录 | 支持多轮往返，保留历史 |
| 辅助角色 | 真实学生扮演 | 完整的角色体验 |

---

## 2. 数据模型

### 2.1 核心模型（7 个）

#### Product（商品）

```python
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
```

#### Catalog（商品目录）

```python
class Catalog(models.Model):
    """公司商品目录 - 每个公司销售的商品"""

    company = models.ForeignKey(
        'users.Company',
        on_delete=models.CASCADE,
        related_name='catalogs'
    )
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
        unique_together = [['company', 'product']]
```

#### Transaction（交易）

```python
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

    buyer = models.ForeignKey(
        'users.Company',
        on_delete=models.PROTECT,
        related_name='buying_transactions'
    )
    seller = models.ForeignKey(
        'users.Company',
        on_delete=models.PROTECT,
        related_name='selling_transactions'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='transactions'
    )
    status = models.CharField(
        '状态',
        max_length=20,
        choices=Status.choices,
        default=Status.INQUIRING
    )
    quantity = models.IntegerField('数量')
    unit_price = models.DecimalField('单价', max_digits=12, decimal_places=2)
    currency = models.CharField('货币', max_length=10, default='USD')
    trade_term = models.CharField('贸易术语', max_length=10, blank=True)  # FOB, CIF, etc.
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
        return f"交易 #{self.id} - {self.product.name}"
```

#### InquiryMessage（磋商消息）

```python
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
    sender_role = models.CharField('发送者角色', max_length=50)  # buyer, seller
    message_type = models.CharField(
        '消息类型',
        max_length=20,
        choices=MessageType.choices
    )
    content = models.TextField('消息内容')
    # 发盘/还盘时的具体报价
    offered_quantity = models.IntegerField('报价数量', null=True, blank=True)
    offered_price = models.DecimalField('报价单价', max_digits=12, decimal_places=2, null=True, blank=True)
    offered_trade_term = models.CharField('报价贸易术语', max_length=10, blank=True)
    # 附件（如产品规格书）
    attachment = models.FileField('附件', upload_to='inquiry_attachments/', blank=True)
    is_read = models.BooleanField('是否已读', default=False)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'inquiry_messages'
        verbose_name = '磋商消息'
        verbose_name_plural = '磋商消息'
        ordering = ['created_at']
```

#### Contract（合同）

```python
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
    trade_term = models.CharField('贸易术语', max_length=10)  # FOB Shanghai, CIF New York
    payment_term = models.CharField('付款方式', max_length=50)  # L/C, D/P, T/T
    delivery_time = models.DateField('交货日期')
    port_of_loading = models.CharField('装运港', max_length=100)
    port_of_discharge = models.CharField('目的港', max_length=100)

    # 商品信息（快照，避免交易变更影响合同）
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
```

#### ContractSignature（合同签字）

```python
class ContractSignature(models.Model):
    """合同签字记录"""

    contract = models.ForeignKey(
        Contract,
        on_delete=models.CASCADE,
        related_name='signatures'
    )
    party = models.CharField('当事方', max_length=20)  # buyer, seller
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
```

#### TransactionLog（交易日志）

```python
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

### 2.2 状态机

#### Transaction 状态转换

```
草稿 → 询盘中 → 还盘中 → 待签约 → 已签约 → 履约中 → 已完成
  ↓                                                ↓
已取消                                            已取消
```

| 当前状态 | 允许的下一状态 | 触发条件 |
|---------|--------------|---------|
| draft | inquiring | 进口商发送询盘 |
| inquiring | negotiating | 出口商回复发盘或还盘 |
| inquiring | pending_contract | 双方达成一致 |
| negotiating | pending_contract | 进口商接受发盘 |
| pending_contract | contracted | 双方签字完成 |
| contracted | in_progress | 合同生效 |
| in_progress | completed | 履约完毕 |
| * | cancelled | 任一方取消 |

#### Contract 状态转换

```
草稿 → 待签字 → 已签字 → 已生效 → 履行完毕
  ↓
已取消
```

| 当前状态 | 允许的下一状态 | 触发条件 |
|---------|--------------|---------|
| draft | pending_sign | 一方签字 |
| pending_sign | signed | 双方签字 |
| signed | effective | 确认生效 |
| effective | fulfilled | 履约完成 |

### 2.3 数据关系图

```
Company (用户扮演的虚拟公司)
  ├─ buying_transactions (作为买方)
  └─ selling_transactions (作为卖方)

Transaction (交易)
  ├─ product → Product (商品)
  ├─ messages → InquiryMessage[] (磋商消息)
  ├─ contract → Contract (合同)
  └─ logs → TransactionLog[] (操作日志)

Contract (合同)
  └─ signatures → ContractSignature[] (签字记录)

Catalog (商品目录)
  ├─ company → Company
  └─ product → Product
```

---

## 3. WebSocket 通知架构

### 3.1 技术选型

- **Django Channels** - WebSocket 支持
- **Redis Pub/Sub** - 消息队列
- **daphne** - ASGI 服务器

### 3.2 通知类型

| 类型 | 代码 | 触发场景 | 接收者 |
|------|------|---------|--------|
| 新询盘 | `inquiry_received` | 进口商发送询盘 | 出口商 |
| 新发盘 | `offer_received` | 出口商回复发盘 | 进口商 |
| 新还盘 | `counter_offer_received` | 任一方还盘 | 对方 |
| 接受报价 | `offer_accepted` | 一方接受报价 | 对方 |
| 签字请求 | `signature_requested` | 合同待签字 | 合同双方 |
| 合同生效 | `contract_effective` | 合同生效 | 交易双方 |
| 交易取消 | `transaction_cancelled` | 交易取消 | 交易双方 |

### 3.3 通知格式

```json
{
  "type": "inquiry_received",
  "transaction_id": 123,
  "data": {
    "sender": "ABC 公司",
    "product": "电子产品 A",
    "message": "对贵司产品感兴趣，请报价"
  },
  "url": "/transactions/123/",
  "timestamp": "2026-05-22T10:30:00Z"
}
```

### 3.4 连接管理

```python
# consumers.py
class TransactionConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        if self.scope["user"].is_anonymous:
            await self.close()
        else:
            self.user_group_name = f'user_{self.user.id}'
            await self.channel_layer.group_add(
                self.user_group_name,
                self.channel_name
            )
            await self.accept()

    async def notify(self, event):
        await self.send(text_data=json.dumps(event['data']))
```

### 3.5 通知服务

```python
# services.py
class NotificationService:
    @staticmethod
    async def send_notification(user_ids, notification_type, data):
        """发送通知给指定用户列表"""
        for user_id in user_ids:
            group_name = f'user_{user_id}'
            await channel_layer.group_send(
                group_name,
                {
                    'type': 'notify',
                    'data': {
                        'type': notification_type,
                        **data
                    }
                }
            )
```

---

## 4. API 设计

### 4.1 交易管理 API

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | /api/v1/transactions/ | 获取交易列表（我参与的） | authenticated |
| POST | /api/v1/transactions/ | 创建交易/询盘 | authenticated |
| GET | /api/v1/transactions/{id}/ | 获取交易详情 | participant |
| PUT | /api/v1/transactions/{id}/ | 更新交易 | participant |
| DELETE | /api/v1/transactions/{id}/ | 取消交易 | participant |
| POST | /api/v1/transactions/{id}/cancel/ | 取消交易（专用） | participant |
| GET | /api/v1/transactions/{id}/messages/ | 获取磋商消息 | participant |
| POST | /api/v1/transactions/{id}/messages/ | 发送消息 | participant |
| PUT | /api/v1/transactions/{id}/messages/{msg_id}/read/ | 标记消息已读 | participant |

### 4.2 商品 API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/v1/products/ | 浏览所有商品基础信息 |
| GET | /api/v1/catalogs/ | 浏览所有商品目录 |
| POST | /api/v1/my-catalog/ | 添加商品到我的目录 |
| GET | /api/v1/my-catalog/ | 我的商品目录 |
| PUT | /api/v1/my-catalog/{id}/ | 修改目录商品 |
| DELETE | /api/v1/my-catalog/{id}/ | 从目录删除 |

### 4.3 合同 API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/v1/transactions/{id}/contract/ | 创建合同草稿 |
| GET | /api/v1/contracts/{id}/ | 获取合同详情 |
| PUT | /api/v1/contracts/{id}/ | 更新合同（草稿状态） |
| POST | /api/v1/contracts/{id}/sign/ | 签署合同 |
| GET | /api/v1/contracts/{id}/preview/ | 预览合同（HTML） |
| GET | /api/v1/contracts/{id}/pdf/ | 导出合同 PDF |

### 4.4 响应格式

#### 成功响应

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 123,
    "status": "inquiring",
    ...
  }
}
```

#### 错误响应

```json
{
  "code": 4001,
  "message": "交易不存在",
  "errors": {
    "transaction_id": ["该交易不存在或您无权访问"]
  }
}
```

---

## 5. 前端页面设计

### 5.1 页面清单

| 页面 | 路径 | 功能 | 模板文件 |
|------|------|------|---------|
| 商品市场 | /market/ | 浏览所有商品目录，搜索，筛选 | products/market.html |
| 我的商品 | /my-catalog/ | 管理自己的商品目录 | products/my_catalog.html |
| 交易列表 | /transactions/ | 我参与的交易列表 | transactions/list.html |
| 交易详情 | /transactions/{id}/ | 交易详情 + 磋商消息 + 合同信息 | transactions/detail.html |
| 合同预览 | /contracts/{id}/preview/ | 合同预览/打印 | transactions/contract_preview.html |

### 5.2 交易详情页面布局

```
┌─────────────────────────────────────────────────────────┐
│  交易 #123 - 询盘中                            [取消交易] │
├─────────────────────────────────────────────────────────┤
│  买方: ABC 公司    卖方: XYZ 公司    日期: 2026-05-22   │
├─────────────────────────────────────────────────────────┤
│  商品信息: 电子产品 A | 数量: 1000 PC | 目标价: $11    │
├─────────────────────────────────────────────────────────┤
│  磋商记录                                                 │
│  ┌─────────────────────────────────────────────────┐   │
│  │ [05-20 10:30] 进口商: 询价 1000 件，目标价 $10 │   │
│  │ [05-20 14:20] 出口商: 报价 $12，MOQ 500        │   │
│  │ [05-21 09:15] 进口商: 还价 $11                 │   │
│  │ ─────────────────────────────────────────────   │   │
│  │ [输入框]  [发送发盘] [接受报价]                  │   │
│  └─────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────┤
│  合同信息 (待签约)                                        │
│  ┌─────────────────────────────────────────────────┐   │
│  │ 合同号: SC2026001                               │   │
│  │ 贸易术语: FOB Shanghai                          │   │
│  │ 付款方式: L/C                                   │   │
│  │                                                  │   │
│  │ 买方: [签字] ✓  卖方: [签字] ○                  │   │
│  │                                                  │   │
│  │ [查看完整合同]                                   │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### 5.3 WebSocket 连接

```javascript
// 前端连接代码
const socket = new WebSocket(
  'ws://' + window.location.host + '/ws/notifications/'
);

socket.onmessage = function(e) {
  const data = JSON.parse(e.data);
  if (data.type === 'inquiry_received') {
    // 显示通知
    showNotification(data.message);
    // 刷新交易列表
    refreshTransactionList();
  }
};
```

---

## 6. 测试策略

### 6.1 测试覆盖

| 类型 | 覆盖内容 | 文件 |
|------|---------|------|
| 模型测试 | 7 个模型的 CRUD 和关联 | test_models.py |
| API 测试 | 所有端点的请求/响应 | test_api.py |
| 状态机测试 | Transaction/Contract 状态转换验证 | test_state_machine.py |
| 权限测试 | 参与者/非参与者访问控制 | test_permissions.py |
| WebSocket 测试 | 通知发送和接收 | test_websocket.py |
| 集成测试 | 完整流程：询盘→发盘→还盘→合同 | test_integration.py |

### 6.2 测试用例示例

```python
class TransactionStateMachineTest(TestCase):
    """交易状态机测试"""

    def test_inquiry_to_negotiating(self):
        """测试从询盘到还盘的状态转换"""
        transaction = TransactionFactory(status='inquiring')
        InquiryMessageFactory(
            transaction=transaction,
            message_type='offer'
        )
        transaction.refresh_from_db()
        assert transaction.status == 'negotiating'

    def test_complete_flow(self):
        """测试完整流程"""
        # 1. 创建询盘
        transaction = TransactionFactory(status='inquiring')
        # 2. 发盘
        InquiryMessageFactory(transaction=transaction, type='offer')
        # 3. 接受
        InquiryMessageFactory(transaction=transaction, type='accept')
        # 4. 待签约
        assert transaction.status == 'pending_contract'
```

---

## 7. 文件结构

### 7.1 新增文件

```
apps/
├── transactions/              # 交易模块
│   ├── __init__.py
│   ├── apps.py
│   ├── models.py             # 7 个模型
│   ├── serializers.py        # API 序列化器
│   ├── views.py              # API 视图
│   ├── urls.py               # 路由
│   ├── admin.py              # 管理后台
│   ├── consumers.py          # WebSocket consumer
│   ├── services.py           # 业务服务
│   ├── tests/                # 测试
│   │   ├── __init__.py
│   │   ├── test_models.py
│   │   ├── test_api.py
│   │   ├── test_state_machine.py
│   │   ├── test_permissions.py
│   │   ├── test_websocket.py
│   │   └── test_integration.py
│   └── fixtures/
│       └── transactions.json
├── products/                  # 商品模块
│   ├── __init__.py
│   ├── apps.py
│   ├── models.py             # Product, Catalog
│   ├── serializers.py
│   ├── views.py
│   ├── urls.py
│   ├── admin.py
│   └── tests/
│       ├── __init__.py
│       ├── test_models.py
│       └── test_api.py
└── notifications/             # 通知模块
    ├── __init__.py
    ├── consumers.py          # WebSocket 消费者
    ├── services.py           # 通知服务
    └── tests/
        └── test_notifications.py

templates/
├── transactions/
│   ├── list.html             # 交易列表
│   ├── detail.html           # 交易详情
│   └── contract_preview.html # 合同预览
└── products/
    ├── market.html           # 商品市场
    └── my_catalog.html       # 我的商品

simtrade/
└── routing.py                # WebSocket 路由配置
```

### 7.2 修改文件

```
simtrade/settings.py          # 添加 channels 配置
simtrade/urls.py              # 添加 API 路由
simtrade/asgi.py              # ASGI 应用配置
requirements.txt              # 添加依赖
```

---

## 8. 依赖和配置

### 8.1 新增依赖

```txt
# WebSocket 支持
channels==3.0.4
channels-redis==4.1.0
# Redis 客户端
redis==4.5.5
# ASGI 服务器
daphne==4.0.0
# 测试
channels-testing==1.2.0
```

### 8.2 Django 配置更新

```python
# settings.py

INSTALLED_APPS = [
    # ... existing apps
    'daphne',
    'channels',
    'apps.transactions',
    'apps.products',
    'apps.notifications',
]

ASGI_APPLICATION = 'simtrade.asgi.application'

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [config('REDIS_URL', default='redis://127.0.0.1:6379/1')],
        },
    },
}

# WebSocket 认证
REST_FRAMEWORK = {
    # ... existing config
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'channels.auth.AuthMiddlewareStack',  # WebSocket 认证
    ],
}
```

### 8.3 ASGI 配置

```python
# simtrade/asgi.py
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

### 8.4 WebSocket 路由

```python
# simtrade/routing.py
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/notifications/$', consumers.NotificationConsumer.as_asgi()),
]
```

---

## 9. 迁移计划

### 9.1 数据库迁移

```bash
# 1. 创建商品模块迁移
python manage.py makemigrations products
python manage.py migrate products

# 2. 创建交易模块迁移
python manage.py makemigrations transactions
python manage.py migrate transactions

# 3. 初始化商品基础数据
python manage.py loaddata products/fixtures/initial_products.json
```

### 9.2 初始数据

需要预加载的商品数据：
- 电子产品类（5 种）
- 纺织品类（5 种）
- 机械设备类（5 种）

---

## 10. 后续阶段规划

### 阶段 2：履约流程
- 信用证管理（LetterOfCredit）
- 生产订单（ProductionOrder）
- 货运/保险/报关集成
- 与单证系统联动

### 阶段 3：工作台与教师
- 角色工作台（出口商/进口商/工厂）
- 教师管理功能
- 进度监控
- 评分系统

---

## 附录

### A. 错误码

| 错误码 | 说明 |
|--------|------|
| 5001 | 交易状态不允许此操作 |
| 5002 | 不是交易参与者 |
| 5003 | 商品不在可售目录 |
| 5004 | 合同已签字，无法修改 |
| 5005 | 双方未全部签字 |

### B. 数据字典

#### Transaction Status
```python
DRAFT = 'draft'  # 草稿
INQUIRING = 'inquiring'  # 询盘中
NEGOTIATING = 'negotiating'  # 还盘中
PENDING_CONTRACT = 'pending_contract'  # 待签约
CONTRACTED = 'contracted'  # 已签约
IN_PROGRESS = 'in_progress'  # 履约中
COMPLETED = 'completed'  # 已完成
CANCELLED = 'cancelled'  # 已取消
```

#### InquiryMessage Type
```python
INQUIRY = 'inquiry'  # 询盘
OFFER = 'offer'  # 发盘
COUNTER_OFFER = 'counter_offer'  # 还盘
ACCEPT = 'accept'  # 接受
REJECT = 'reject'  # 拒绝
```

#### Contract Status
```python
DRAFT = 'draft'  # 草稿
PENDING_SIGN = 'pending_sign'  # 待签字
SIGNED = 'signed'  # 已签字
EFFECTIVE = 'effective'  # 已生效
FULFILLED = 'fulfilled'  # 履行完毕
CANCELLED = 'cancelled'  # 已取消
```
