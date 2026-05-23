# 外汇结算与出口退税设计文档

**版本**: 1.0
**日期**: 2026-05-23
**状态**: 待审核

---

## 1. 概述

### 1.1 设计目标

实现外汇局和税务局的简化业务流程：报关放行且货到港后，出口商可申请收汇核销和出口退税，外汇局完成核销→结汇，税务局完成审核→批准→退税。包含模拟汇率波动和 HS 编码退税率计算功能。

### 1.2 核心决策

| 决策点 | 选择 | 理由 |
|--------|------|------|
| 流程深度 | 简化版 + 模拟汇率波动 + HS 编码退税率 | 教学模拟，聚焦核心业务环节 |
| 实现位置 | apps/transactions | 与合同/货运/报关同属交易流程 |
| 触发时机 | 报关放行 + 货到港（Shipment.status='arrived' 且 CustomsDeclaration.status='cleared'） | 贴近真实贸易流程 |
| 关联对象 | FK → CustomsDeclaration | 外汇/退税依赖报关数据，关系精确 |
| 汇率机制 | 固定基准 ± 随机波动 | 简单模拟，增加教学趣味性 |
| 退税率 | 固定 HS 编码退税率表 | 教学场景，无需实时查询 |
| 退税依赖 | 需要 ForexSettlement 已核销或已结汇 | 贴近真实贸易流程 |

### 1.3 贸易关系

```
报关放行（CustomsDeclaration.status='cleared'）+ 货到港（Shipment.status='arrived'）
  → 出口商申请收汇核销 → 外汇局核销 → 外汇局结汇（汇率换算）
  → 出口商申请出口退税（依赖外汇已核销/结汇）→ 税务局审核 → 批准 → 退税
```

---

## 2. 数据模型

### 2.1 ForexSettlement 模型

```python
class ForexSettlement(models.Model):
    """外汇结算"""

    class Status(models.TextChoices):
        APPLIED = 'applied', '已申请'
        VERIFIED = 'verified', '已核销'
        SETTLED = 'settled', '已结汇'
        REJECTED = 'rejected', '已拒绝'

    customs_declaration = models.ForeignKey(
        'transactions.CustomsDeclaration',
        on_delete=models.CASCADE,
        related_name='forex_settlements'
    )
    applicant = models.ForeignKey(
        'roles.Company',
        on_delete=models.PROTECT,
        related_name='forex_settlements'
    )
    forex_bureau = models.ForeignKey(
        'roles.Company',
        on_delete=models.PROTECT,
        related_name='processed_forex_settlements'
    )
    settlement_no = models.CharField('结算单号', max_length=50, unique=True, editable=False)
    foreign_currency = models.CharField('外币币种', max_length=10, default='USD')
    foreign_amount = models.DecimalField('外币金额', max_digits=14, decimal_places=2)
    reference_rate = models.DecimalField('参考汇率', max_digits=10, decimal_places=4)
    reference_cny_amount = models.DecimalField('参考人民币金额', max_digits=14, decimal_places=2)
    settlement_rate = models.DecimalField('结汇汇率', max_digits=10, decimal_places=4, default=0)
    settlement_cny_amount = models.DecimalField('结汇人民币金额', max_digits=14, decimal_places=2, default=0)
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
        related_name='created_forex_settlements'
    )
    verified_at = models.DateTimeField('核销时间', null=True, blank=True)
    settled_at = models.DateTimeField('结汇时间', null=True, blank=True)
    rejected_at = models.DateTimeField('拒绝时间', null=True, blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'forex_settlements'
        verbose_name = '外汇结算'
        verbose_name_plural = '外汇结算'
        ordering = ['-created_at']

    def __str__(self):
        return self.settlement_no

    def save(self, *args, **kwargs):
        if not self.settlement_no:
            import random
            from django.utils import timezone
            date_str = timezone.now().strftime('%Y%m%d')
            for _ in range(10):
                rand_str = f'{random.randint(100000, 999999)}'
                no = f'FX{date_str}{rand_str}'
                if not ForexSettlement.objects.filter(settlement_no=no).exists():
                    self.settlement_no = no
                    break
            else:
                raise RuntimeError('无法生成唯一结算单号，请重试')
        super().save(*args, **kwargs)
```

### 2.2 TaxRefundApplication 模型

```python
class TaxRefundApplication(models.Model):
    """出口退税申请"""

    class Status(models.TextChoices):
        APPLIED = 'applied', '已申请'
        REVIEWING = 'reviewing', '审核中'
        APPROVED = 'approved', '已批准'
        REFUNDED = 'refunded', '已退税'
        REJECTED = 'rejected', '已拒绝'

    customs_declaration = models.ForeignKey(
        'transactions.CustomsDeclaration',
        on_delete=models.CASCADE,
        related_name='tax_refund_applications'
    )
    applicant = models.ForeignKey(
        'roles.Company',
        on_delete=models.PROTECT,
        related_name='tax_refund_applications'
    )
    tax_bureau = models.ForeignKey(
        'roles.Company',
        on_delete=models.PROTECT,
        related_name='processed_tax_refunds'
    )
    application_no = models.CharField('退税申请号', max_length=50, unique=True, editable=False)
    hs_code = models.CharField('HS编码', max_length=20)
    total_value = models.DecimalField('报关总价值', max_digits=14, decimal_places=2)
    refund_rate = models.DecimalField('退税率', max_digits=5, decimal_places=4, default=0)
    refund_amount = models.DecimalField('退税金额', max_digits=14, decimal_places=2, default=0)
    refund_currency = models.CharField('退税币种', max_length=10, default='CNY')
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
        related_name='created_tax_refunds'
    )
    reviewing_at = models.DateTimeField('审核时间', null=True, blank=True)
    approved_at = models.DateTimeField('批准时间', null=True, blank=True)
    refunded_at = models.DateTimeField('退税时间', null=True, blank=True)
    rejected_at = models.DateTimeField('拒绝时间', null=True, blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'tax_refund_applications'
        verbose_name = '出口退税申请'
        verbose_name_plural = '出口退税申请'
        ordering = ['-created_at']

    def __str__(self):
        return self.application_no

    def save(self, *args, **kwargs):
        if not self.application_no:
            import random
            from django.utils import timezone
            date_str = timezone.now().strftime('%Y%m%d')
            for _ in range(10):
                rand_str = f'{random.randint(100000, 999999)}'
                no = f'TR{date_str}{rand_str}'
                if not TaxRefundApplication.objects.filter(application_no=no).exists():
                    self.application_no = no
                    break
            else:
                raise RuntimeError('无法生成唯一退税申请号，请重试')
        super().save(*args, **kwargs)
```

### 2.3 状态流转

**ForexSettlement：**
```
Applied ──→ Verified ──→ Settled
   │
   └──→ Rejected
```

| 当前状态 | 操作 | 目标状态 | 操作者 |
|---------|------|---------|--------|
| Applied | verify | Verified | 外汇局 |
| Verified | settle | Settled | 外汇局 |
| Applied | reject | Rejected | 外汇局 |

**TaxRefundApplication：**
```
Applied ──→ Reviewing ──→ Approved ──→ Refunded
   │              │
   └──────→ Rejected ←──┘
```

| 当前状态 | 操作 | 目标状态 | 操作者 |
|---------|------|---------|--------|
| Applied | review | Reviewing | 税务局 |
| Reviewing | approve | Approved | 税务局 |
| Approved | refund | Refunded | 税务局 |
| Applied | reject | Rejected | 税务局 |
| Reviewing | reject | Rejected | 税务局 |

---

## 3. 汇率模拟

### 3.1 汇率配置

| 币种 | 基准汇率 | 波动范围 | 实际范围 |
|------|---------|---------|---------|
| USD | 7.2000 | ±0.0500 | 7.15 ~ 7.25 |
| EUR | 7.8000 | ±0.0600 | 7.74 ~ 7.86 |
| GBP | 9.1000 | ±0.0700 | 9.03 ~ 9.17 |
| CNY | 1.0000 | 0 | 固定 1.0 |

### 3.2 计算公式

```python
exchange_rate = base_rate + random(-range, +range)
cny_amount = foreign_amount * exchange_rate
```

每次调用 `get_exchange_rate(currency)` 返回略微不同的汇率，模拟市场波动。

---

## 4. 退税率计算

### 4.1 HS 编码退税率表

| HS 编码范围 | 货物类别 | 退税率 |
|------------|---------|--------|
| 61-63 | 纺织品 | 13% |
| 85 | 电子产品 | 13% |
| 84 | 机械 | 13% |
| 01-24 | 食品 | 9% |
| 其他 | 默认 | 11% |

### 4.2 计算公式

```
退税额 = 报关总价值 × 退税率
```

---

## 5. 服务层

### 5.1 ForexService

```python
class ForexService:
    @staticmethod
    def get_exchange_rate(currency):
        """获取模拟汇率（每次调用略有不同）"""

    @staticmethod
    def create_settlement(user, declaration_id, forex_bureau_id):
        """出口商申请收汇核销（出口商角色，报关已放行 + 货已到港，记录参考汇率和预期 CNY 金额）"""

    @staticmethod
    def verify(settlement_id, user):
        """外汇局核销"""

    @staticmethod
    def settle(settlement_id, user):
        """外汇局结汇（用新汇率计算实际 CNY 金额）"""

    @staticmethod
    def reject(settlement_id, user, reason=''):
        """外汇局拒绝"""
```

### 5.2 TaxRefundService

```python
class TaxRefundService:
    @staticmethod
    def calculate_refund_rate(hs_code):
        """根据 HS 编码查退税率"""

    @staticmethod
    def create_application(user, declaration_id, tax_bureau_id):
        """出口商申请退税（出口商角色，报关已放行 + 货已到港 + 外汇已核销/结汇，自动计算退税额）"""

    @staticmethod
    def review(application_id, user):
        """税务局审核"""

    @staticmethod
    def approve(application_id, user):
        """税务局批准"""

    @staticmethod
    def refund(application_id, user):
        """税务局退税"""

    @staticmethod
    def reject(application_id, user, reason=''):
        """税务局拒绝"""
```

---

## 6. API 接口

### 6.1 外汇结算 API

| 端点 | 方法 | 说明 | 权限 |
|------|------|------|------|
| `/api/v1/forex-settlements/` | GET/POST | 结算列表/创建 | 出口商创建 |
| `/api/v1/forex-settlements/{id}/` | GET | 结算详情 | 参与方 |
| `/api/v1/forex-settlements/{id}/verify/` | POST | 核销 | 外汇局 |
| `/api/v1/forex-settlements/{id}/settle/` | POST | 结汇 | 外汇局 |
| `/api/v1/forex-settlements/{id}/reject/` | POST | 拒绝 | 外汇局 |

### 6.2 出口退税 API

| 端点 | 方法 | 说明 | 权限 |
|------|------|------|------|
| `/api/v1/tax-refund-applications/` | GET/POST | 退税列表/创建 | 出口商创建 |
| `/api/v1/tax-refund-applications/{id}/` | GET | 退税详情 | 参与方 |
| `/api/v1/tax-refund-applications/{id}/review/` | POST | 审核 | 税务局 |
| `/api/v1/tax-refund-applications/{id}/approve/` | POST | 批准 | 税务局 |
| `/api/v1/tax-refund-applications/{id}/refund/` | POST | 退税 | 税务局 |
| `/api/v1/tax-refund-applications/{id}/reject/` | POST | 拒绝 | 税务局 |

---

## 7. 与现有系统的集成

### 7.1 前置条件

- ForexSettlement 要求 CustomsDeclaration.status='cleared' 且 Shipment.status='arrived'
- TaxRefundApplication 要求同上报关条件，且同报关单的 ForexSettlement.status 为 'verified' 或 'settled'

### 7.2 与 CustomsDeclaration 的关系

- ForexSettlement 和 TaxRefundApplication 通过 FK 关联 CustomsDeclaration
- 一笔报关单可对应一笔外汇结算和多笔退税申请（允许重申）

### 7.3 审计日志

所有操作通过 TransactionService.log_transaction 记录，关联到 CustomsDeclaration → Shipment → Contract → Transaction。

### 7.4 角色权限

- 创建外汇结算/退税申请：需要 exporter 角色，且公司为报关单的 declarant
- 核销/结汇/拒绝（外汇）：需要 forex 角色，且公司为结算单的 forex_bureau
- 审核/批准/退税/拒绝（税务）：需要 tax 角色，且公司为退税申请的 tax_bureau

---

## 8. 不在范围内

- 真实汇率 API 对接
- 外汇衍生品（远期、期权等）
- 多币种交叉结算
- 退税账户管理
- 增值税发票管理
- 前端 UI
