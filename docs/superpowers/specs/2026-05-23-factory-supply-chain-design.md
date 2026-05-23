# 工厂-出口商供应链设计文档

**版本**: 1.0
**日期**: 2026-05-23
**状态**: 待审核

---

## 1. 概述

### 1.1 设计目标

实现工厂角色的简化业务流程：出口商向工厂下达采购订单，工厂确认后发货并开具增值税发票，出口商确认收货完成闭环。

### 1.2 核心决策

| 决策点 | 选择 | 理由 |
|--------|------|------|
| 流程深度 | 简化版 | 教学模拟场景，无需生产排期、库存管理 |
| 模型策略 | 独立 PurchaseOrder 模型 | 与出口交易解耦，职责清晰 |
| 实现位置 | apps/transactions | 采购是交易流程的一部分 |
| 发票生成 | 通过 documents app 生成 | 复用现有文档系统 |
| 权限校验 | 基于 RoleService | 复用已实现的角色上下文 |

### 1.3 贸易关系

```
进口商 → 出口商 → 工厂
                  ↑
          采购订单（本设计）
```

---

## 2. 数据模型

### 2.1 PurchaseOrder 模型

```python
class PurchaseOrder(models.Model):
    """采购订单 — 出口商向工厂的采购"""

    class Status(models.TextChoices):
        DRAFT = 'draft', '草稿'
        CONFIRMED = 'confirmed', '已确认'
        SHIPPED = 'shipped', '已发货'
        INVOICED = 'invoiced', '已开票'
        COMPLETED = 'completed', '已完成'
        CANCELLED = 'cancelled', '已取消'

    transaction = models.ForeignKey(
        'transactions.Transaction',
        on_delete=models.CASCADE,
        related_name='purchase_orders'
    )
    buyer = models.ForeignKey(
        'roles.Company',
        on_delete=models.PROTECT,
        related_name='buying_purchase_orders'
    )
    seller = models.ForeignKey(
        'roles.Company',
        on_delete=models.PROTECT,
        related_name='selling_purchase_orders'
    )
    order_no = models.CharField('订单编号', max_length=50, unique=True, editable=False)
    product_name = models.CharField('商品名称', max_length=200)
    product_code = models.CharField('商品编码', max_length=50, blank=True)
    quantity = models.DecimalField('数量', max_digits=12, decimal_places=2)
    unit = models.CharField('计量单位', max_length=20, default='件')
    unit_price = models.DecimalField('单价', max_digits=12, decimal_places=2)
    currency = models.CharField('币种', max_length=10, default='CNY')
    total_amount = models.DecimalField('总金额', max_digits=14, decimal_places=2, editable=False)
    delivery_date = models.DateField('交货日期', null=True, blank=True)
    delivery_address = models.TextField('交货地址', blank=True)
    status = models.CharField(
        '状态',
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )
    notes = models.TextField('备注', blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_purchase_orders'
    )
    confirmed_at = models.DateTimeField('确认时间', null=True, blank=True)
    shipped_at = models.DateTimeField('发货时间', null=True, blank=True)
    invoiced_at = models.DateTimeField('开票时间', null=True, blank=True)
    completed_at = models.DateTimeField('完成时间', null=True, blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'purchase_orders'
        verbose_name = '采购订单'
        verbose_name_plural = '采购订单'
        ordering = ['-created_at']

    def __str__(self):
        return self.order_no

    def save(self, *args, **kwargs):
        if not self.order_no:
            self.order_no = self._generate_order_no()
        self.total_amount = self.quantity * self.unit_price
        super().save(*args, **kwargs)

    @staticmethod
    def _generate_order_no():
        """生成订单编号：PO + YYYYMMDD + 6位随机数"""
        import random
        from django.utils import timezone
        date_str = timezone.now().strftime('%Y%m%d')
        while True:
            rand_str = f'{random.randint(100000, 999999)}'
            order_no = f'PO{date_str}{rand_str}'
            if not PurchaseOrder.objects.filter(order_no=order_no).exists():
                return order_no
```

### 2.2 状态流转

```
Draft ──→ Confirmed ──→ Shipped ──→ Invoiced ──→ Completed
  │           │
  └──────→ Cancelled ←──┘
```

**状态转换规则：**

| 当前状态 | 允许的操作 | 目标状态 | 操作者 |
|---------|-----------|---------|--------|
| Draft | confirm | Confirmed | 工厂 |
| Draft | cancel | Cancelled | 出口商 |
| Confirmed | ship | Shipped | 工厂 |
| Confirmed | cancel | Cancelled | 出口商/工厂 |
| Shipped | invoice | Invoiced | 工厂 |
| Invoiced | complete | Completed | 出口商 |

---

## 3. 服务层

### 3.1 PurchaseOrderService

```python
class PurchaseOrderService:
    """采购订单服务"""

    @staticmethod
    def create_order(user, transaction_id, seller_id, **kwargs):
        """出口商创建采购订单

        Args:
            user: 创建人（出口商角色）
            transaction_id: 关联的出口交易 ID
            seller_id: 工厂公司 ID
            **kwargs: product_name, quantity, unit_price 等

        Returns:
            PurchaseOrder

        Raises:
            ValueError: 角色无权限或交易状态不允许
        """

    @staticmethod
    def confirm(order_id, user):
        """工厂确认订单

        Args:
            order_id: 采购订单 ID
            user: 操作人（工厂角色）

        Raises:
            ValueError: 非工厂公司成员或订单状态不允许
        """

    @staticmethod
    def ship(order_id, user, tracking_info=''):
        """工厂发货

        Args:
            order_id: 采购订单 ID
            user: 操作人（工厂角色）
            tracking_info: 物流信息

        Raises:
            ValueError: 非工厂公司成员或订单状态不允许
        """

    @staticmethod
    def invoice(order_id, user):
        """工厂开具增值税发票

        自动生成增值税发票文档。

        Args:
            order_id: 采购订单 ID
            user: 操作人（工厂角色）

        Returns:
            Document（生成的发票文档）

        Raises:
            ValueError: 非工厂公司成员或订单状态不允许
        """

    @staticmethod
    def complete(order_id, user):
        """出口商确认收货

        Args:
            order_id: 采购订单 ID
            user: 操作人（出口商角色）

        Raises:
            ValueError: 非出口商公司成员或订单状态不允许
        """

    @staticmethod
    def cancel(order_id, user, reason=''):
        """取消订单

        Draft 状态仅出口商可取消。
        Confirmed 状态出口商和工厂均可取消。

        Args:
            order_id: 采购订单 ID
            user: 操作人
            reason: 取消原因
        """
```

### 3.2 序列化器

```python
class PurchaseOrderSerializer(serializers.ModelSerializer):
    """采购订单序列化器"""
    buyer_name = serializers.CharField(source='buyer.name', read_only=True)
    seller_name = serializers.CharField(source='seller.name', read_only=True)
    transaction_no = serializers.CharField(source='transaction.transaction_no', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = PurchaseOrder
        fields = [
            'id', 'order_no', 'transaction', 'transaction_no',
            'buyer', 'buyer_name', 'seller', 'seller_name',
            'product_name', 'product_code', 'quantity', 'unit',
            'unit_price', 'currency', 'total_amount',
            'delivery_date', 'delivery_address',
            'status', 'status_display', 'notes',
            'created_by', 'confirmed_at', 'shipped_at',
            'invoiced_at', 'completed_at',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'order_no', 'created_by',
            'confirmed_at', 'shipped_at', 'invoiced_at', 'completed_at',
            'created_at', 'updated_at'
        ]


class CreatePurchaseOrderSerializer(serializers.Serializer):
    """创建采购订单请求"""
    transaction_id = serializers.IntegerField(min_value=1)
    seller_id = serializers.IntegerField(min_value=1)
    product_name = serializers.CharField(max_length=200)
    product_code = serializers.CharField(required=False, allow_blank=True, max_length=50)
    quantity = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0.01)
    unit = serializers.CharField(max_length=20, default='件')
    unit_price = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0.01)
    currency = serializers.CharField(max_length=10, default='CNY')
    delivery_date = serializers.DateField(required=False, allow_null=True)
    delivery_address = serializers.CharField(required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)
```

---

## 4. API 接口

### 4.1 端点列表

| 端点 | 方法 | 说明 | 权限 |
|------|------|------|------|
| `/api/v1/purchase-orders/` | GET | 采购订单列表 | 登录（按公司过滤） |
| `/api/v1/purchase-orders/` | POST | 创建采购订单 | 出口商角色 |
| `/api/v1/purchase-orders/{id}/` | GET | 订单详情 | 买卖方成员 |
| `/api/v1/purchase-orders/{id}/confirm/` | POST | 确认订单 | 工厂角色 |
| `/api/v1/purchase-orders/{id}/ship/` | POST | 发货 | 工厂角色 |
| `/api/v1/purchase-orders/{id}/invoice/` | POST | 开票 | 工厂角色 |
| `/api/v1/purchase-orders/{id}/complete/` | POST | 确认收货 | 出口商角色 |
| `/api/v1/purchase-orders/{id}/cancel/` | POST | 取消 | 买卖方 |

### 4.2 响应格式

遵循项目统一的响应格式：

```json
{
    "code": 0,
    "message": "success",
    "data": { ... }
}
```

---

## 5. 与现有系统的集成

### 5.1 关联出口交易

- 每个采购订单必须关联一个 `Transaction`（出口交易）
- 只有交易中的出口商公司（seller）才能创建采购订单
- 订单的 `buyer` 自动设为出口商公司，`seller` 由请求指定（工厂公司）

### 5.2 发票文档生成

- `invoice()` 操作时，通过 `apps/documents` 自动生成增值税发票文档
- 使用现有的 `DocumentTemplate` 中类型为 `vat_invoice` 的模板
- 如果模板不存在，创建基本发票记录

### 5.3 审计日志

- 所有状态变更通过 `TransactionLog` 记录
- 日志关联到对应的 `Transaction`

### 5.4 角色权限

- 通过 `RoleService.get_current_role()` 获取当前激活角色
- `create_order` / `complete`：需要出口商角色（`role.code == 'exporter'`），且公司为采购订单的 buyer
- `confirm` / `ship` / `invoice`：需要工厂角色（`role.code == 'factory'`），且公司为采购订单的 seller
- `cancel`：Draft 时出口商可取消；Confirmed 时买卖方均可取消

---

## 6. 测试策略

### 6.1 模型测试

- 创建采购订单
- 订单编号唯一性
- 状态流转合法性
- 字段验证

### 6.2 服务层测试

- 出口商创建订单
- 工厂确认订单
- 工厂发货
- 工厂开票（含发票文档生成）
- 出口商确认收货
- 取消订单（各状态）
- 权限校验（非出口商/工厂角色操作应拒绝）

### 6.3 API 测试

- CRUD 操作
- 状态转换端点
- 权限过滤
- 响应格式一致性

---

## 7. Admin 配置

```python
@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = [
        'order_no', 'buyer', 'seller', 'product_name',
        'total_amount', 'status', 'created_at'
    ]
    list_filter = ['status', 'currency', 'created_at']
    search_fields = ['order_no', 'product_name', 'buyer__name', 'seller__name']
    readonly_fields = ['created_at', 'updated_at', 'confirmed_at', 'shipped_at', 'invoiced_at', 'completed_at']
```

---

## 8. 不在范围内

以下功能属于后续子项目（B/C/D）：

- 货运公司订舱和提单
- 保险承保和保单
- 海关报关和征税
- 商检和检验证书
- 外汇核销
- 税务退税
- 前端角色切换 UI
