# 货运与保险设计文档

**版本**: 1.0
**日期**: 2026-05-23
**状态**: 待审核

---

## 1. 概述

### 1.1 设计目标

实现货运公司和保险公司的简化业务流程：合同生效后，出口商可申请订舱和投保，货运公司完成订舱→装船→签发提单，保险公司完成审核承保→签发保单。包含运费计算和保费精算功能。

### 1.2 核心决策

| 决策点 | 选择 | 理由 |
|--------|------|------|
| 流程深度 | 简化版 + 运费/保费计算 | 教学模拟，聚焦核心业务环节 |
| 实现位置 | apps/transactions | 与合同/信用证同属交易流程 |
| 触发时机 | 合同生效后 | 合同生效才能安排出运 |
| Shipment 关系 | OneToOne(Contract) | 一个合同对应一次出运 |
| Insurance 关系 | OneToOne(Contract) | 一个合同对应一份保单 |
| 运费/保费计算 | 固定费率表 | 教学场景，无需实时报价 |

### 1.3 贸易关系

```
合同生效 → 出口商申请订舱 → 货运公司确认 → 装船 → 签发提单
         → 出口商投保     → 保险公司承保 → 签发保单
```

---

## 2. 数据模型

### 2.1 Shipment 模型

```python
class Shipment(models.Model):
    """货运订单"""

    class Status(models.TextChoices):
        DRAFT = 'draft', '草稿'
        BOOKED = 'booked', '已订舱'
        LOADED = 'loaded', '已装船'
        SHIPPED = 'shipped', '已签发提单'
        ARRIVED = 'arrived', '已到港'
        CANCELLED = 'cancelled', '已取消'

    contract = models.OneToOneField(
        'transactions.Contract',
        on_delete=models.CASCADE,
        related_name='shipment'
    )
    shipper = models.ForeignKey(
        'roles.Company',
        on_delete=models.PROTECT,
        related_name='outgoing_shipments'
    )
    carrier = models.ForeignKey(
        'roles.Company',
        on_delete=models.PROTECT,
        related_name='incoming_shipments'
    )
    shipment_no = models.CharField('货运编号', max_length=50, unique=True, editable=False)
    booking_no = models.CharField('订舱号', max_length=50, blank=True)
    bl_no = models.CharField('提单号', max_length=50, blank=True)
    vessel_name = models.CharField('船名/航班号', max_length=100, blank=True)
    port_of_loading = models.CharField('装运港', max_length=100)
    port_of_discharge = models.CharField('目的港', max_length=100)
    etd = models.DateField('预计出发日期', null=True, blank=True)
    eta = models.DateField('预计到达日期', null=True, blank=True)
    container_no = models.CharField('集装箱号', max_length=50, blank=True)
    freight_amount = models.DecimalField('运费金额', max_digits=14, decimal_places=2, default=0)
    freight_currency = models.CharField('运费币种', max_length=10, default='USD')
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
        related_name='created_shipments'
    )
    booked_at = models.DateTimeField('订舱时间', null=True, blank=True)
    loaded_at = models.DateTimeField('装船时间', null=True, blank=True)
    shipped_at = models.DateTimeField('签发提单时间', null=True, blank=True)
    arrived_at = models.DateTimeField('到港时间', null=True, blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'shipments'
        verbose_name = '货运订单'
        verbose_name_plural = '货运订单'
        ordering = ['-created_at']

    def __str__(self):
        return self.shipment_no

    def save(self, *args, **kwargs):
        if not self.shipment_no:
            self.shipment_no = self._generate_shipment_no()
        super().save(*args, **kwargs)

    @staticmethod
    def _generate_shipment_no():
        import random
        from django.utils import timezone
        date_str = timezone.now().strftime('%Y%m%d')
        for _ in range(10):
            rand_str = f'{random.randint(100000, 999999)}'
            shipment_no = f'SH{date_str}{rand_str}'
            if not Shipment.objects.filter(shipment_no=shipment_no).exists():
                return shipment_no
        raise RuntimeError('无法生成唯一货运编号，请重试')
```

### 2.2 InsurancePolicy 模型

```python
class InsurancePolicy(models.Model):
    """保险单"""

    class Status(models.TextChoices):
        APPLIED = 'applied', '已投保'
        UNDERWRITTEN = 'underwritten', '已承保'
        ISSUED = 'issued', '已签发'
        CANCELLED = 'cancelled', '已取消'

    class CoverageType(models.TextChoices):
        FPA = 'fpa', '平安险'
        WA = 'wa', '水渍险'
        ALL_RISK = 'all_risk', '一切险'

    contract = models.OneToOneField(
        'transactions.Contract',
        on_delete=models.CASCADE,
        related_name='insurance_policy'
    )
    shipment = models.ForeignKey(
        'transactions.Shipment',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='insurance_policies'
    )
    insured = models.ForeignKey(
        'roles.Company',
        on_delete=models.PROTECT,
        related_name='insured_policies'
    )
    insurer = models.ForeignKey(
        'roles.Company',
        on_delete=models.PROTECT,
        related_name='issued_policies'
    )
    policy_no = models.CharField('保单号', max_length=50, unique=True, editable=False)
    cargo_description = models.TextField('货物描述')
    insured_amount = models.DecimalField('投保金额', max_digits=14, decimal_places=2)
    premium = models.DecimalField('保费', max_digits=14, decimal_places=2, default=0)
    premium_currency = models.CharField('保费币种', max_length=10, default='CNY')
    coverage_type = models.CharField(
        '险种',
        max_length=20,
        choices=CoverageType.choices,
        default=CoverageType.ALL_RISK
    )
    status = models.CharField(
        '状态',
        max_length=20,
        choices=Status.choices,
        default=Status.APPLIED
    )
    notes = models.TextField('备注', blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_insurance_policies'
    )
    underwritten_at = models.DateTimeField('承保时间', null=True, blank=True)
    issued_at = models.DateTimeField('签发时间', null=True, blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'insurance_policies'
        verbose_name = '保险单'
        verbose_name_plural = '保险单'
        ordering = ['-created_at']

    def __str__(self):
        return self.policy_no

    def save(self, *args, **kwargs):
        if not self.policy_no:
            self.policy_no = self._generate_policy_no()
        super().save(*args, **kwargs)

    @staticmethod
    def _generate_policy_no():
        import random
        from django.utils import timezone
        date_str = timezone.now().strftime('%Y%m%d')
        for _ in range(10):
            rand_str = f'{random.randint(100000, 999999)}'
            policy_no = f'IN{date_str}{rand_str}'
            if not InsurancePolicy.objects.filter(policy_no=policy_no).exists():
                return policy_no
        raise RuntimeError('无法生成唯一保单号，请重试')
```

### 2.3 状态流转

**Shipment：**
```
Draft ──→ Booked ──→ Loaded ──→ Shipped ──→ Arrived
  │           │
  └──────→ Cancelled ←──┘
```

| 当前状态 | 操作 | 目标状态 | 操作者 |
|---------|------|---------|--------|
| Draft | book | Booked | 货运公司 |
| Draft | cancel | Cancelled | 出口商 |
| Booked | load | Loaded | 货运公司 |
| Booked | cancel | Cancelled | 出口商/货运公司 |
| Loaded | issue_bl | Shipped | 货运公司 |
| Shipped | arrive | Arrived | 货运公司 |

**InsurancePolicy：**
```
Applied ──→ Underwritten ──→ Issued
  │
  └──→ Cancelled
```

| 当前状态 | 操作 | 目标状态 | 操作者 |
|---------|------|---------|--------|
| Applied | underwrite | Underwritten | 保险公司 |
| Applied | cancel | Cancelled | 出口商 |
| Underwritten | issue | Issued | 保险公司 |

---

## 3. 运费计算

### 3.1 费率表

固定费率，基于贸易术语：

| 贸易术语 | 运费率（占合同金额） | 说明 |
|---------|-------------------|------|
| FOB | 0% | 买方承担运费 |
| CFR | 3% | 卖方承担运费 |
| CIF | 3% | 卖方承担运费+保险 |
| EXW | 0% | 买方自提 |

### 3.2 计算公式

```
运费 = 合同总金额 × 运费率
```

当贸易术语为 FOB 或 EXW 时，运费为 0（由买方安排）。

---

## 4. 保费精算

### 4.1 费率表

| 险种 | 费率 | 说明 |
|------|------|------|
| 平安险 (FPA) | 0.3% | 基本保障，仅承保全损 |
| 水渍险 (WA) | 0.5% | 承保全损+部分损失 |
| 一切险 (All Risk) | 0.8% | 全面保障 |

### 4.2 计算公式

```
保费 = 投保金额 × 费率
投保金额默认 = 合同总金额 × 110%（CIF 惯例加成）
```

---

## 5. 服务层

### 5.1 ShipmentService

```python
class ShipmentService:
    @staticmethod
    def create_shipment(user, contract_id, carrier_id, **kwargs):
        """出口商创建货运订单（出口商角色）"""

    @staticmethod
    def calculate_freight(contract_id):
        """计算运费（根据贸易术语和合同金额）"""

    @staticmethod
    def book(shipment_id, user, booking_no, vessel_name, etd, eta):
        """货运公司确认订舱"""

    @staticmethod
    def load(shipment_id, user, container_no=''):
        """货运公司确认装船"""

    @staticmethod
    def issue_bl(shipment_id, user, bl_no):
        """货运公司签发提单"""

    @staticmethod
    def arrive(shipment_id, user):
        """货运公司确认到港"""

    @staticmethod
    def cancel(shipment_id, user, reason=''):
        """取消货运订单"""
```

### 5.2 InsuranceService

```python
class InsuranceService:
    @staticmethod
    def create_policy(user, contract_id, insurer_id, coverage_type='all_risk', **kwargs):
        """出口商投保（出口商角色，自动计算保费）"""

    @staticmethod
    def calculate_premium(insured_amount, coverage_type):
        """保费精算"""

    @staticmethod
    def underwrite(policy_id, user):
        """保险公司审核承保"""

    @staticmethod
    def issue(policy_id, user):
        """保险公司签发保单"""

    @staticmethod
    def cancel(policy_id, user, reason=''):
        """取消保单"""
```

---

## 6. API 接口

### 6.1 货运 API

| 端点 | 方法 | 说明 | 权限 |
|------|------|------|------|
| `/api/v1/shipments/` | GET/POST | 货运列表/创建 | 出口商创建 |
| `/api/v1/shipments/{id}/` | GET | 货运详情 | 参与方 |
| `/api/v1/shipments/{id}/book/` | POST | 确认订舱 | 货运公司 |
| `/api/v1/shipments/{id}/load/` | POST | 确认装船 | 货运公司 |
| `/api/v1/shipments/{id}/issue-bl/` | POST | 签发提单 | 货运公司 |
| `/api/v1/shipments/{id}/arrive/` | POST | 确认到港 | 货运公司 |
| `/api/v1/shipments/{id}/cancel/` | POST | 取消 | 出口商/货运公司 |

### 6.2 保险 API

| 端点 | 方法 | 说明 | 权限 |
|------|------|------|------|
| `/api/v1/insurance-policies/` | GET/POST | 保单列表/创建 | 出口商创建 |
| `/api/v1/insurance-policies/{id}/` | GET | 保单详情 | 参与方 |
| `/api/v1/insurance-policies/{id}/underwrite/` | POST | 审核承保 | 保险公司 |
| `/api/v1/insurance-policies/{id}/issue/` | POST | 签发保单 | 保险公司 |
| `/api/v1/insurance-policies/{id}/cancel/` | POST | 取消 | 出口商/保险公司 |

---

## 7. 与现有系统的集成

### 7.1 合同生效联动

在 `StateTransitionService.on_contract_effective()` 中：
- 除了现有的 LC 自动创建逻辑外，不需要自动创建货运/保单
- 出口商手动申请订舱和投保

### 7.2 与 PurchaseOrder 的关系

- PurchaseOrder 和 Shipment/InsurancePolicy 是平行的，都关联到 Contract
- PurchaseOrder 处理工厂供应链（出口商→工厂）
- Shipment 处理国际物流（出口商→进口商）
- 两者独立运作，没有直接依赖

### 7.3 审计日志

所有操作通过 `TransactionService.log_transaction` 记录，关联到合同对应的 Transaction。

### 7.4 角色权限

- 创建货运/保单：需要 exporter 角色，且公司为合同的 seller
- 订舱/装船/签发提单/到港：需要 shipping 角色，且公司为货运订单的 carrier
- 承保/签发保单：需要 insurance 角色，且公司为保单的 insurer
- 取消：根据状态校验角色（同 PurchaseOrder 模式）

---

## 8. 不在范围内

- 物流实时跟踪
- 船期查询
- 集装箱管理
- 理赔流程
- 多式联运
- 前端 UI
