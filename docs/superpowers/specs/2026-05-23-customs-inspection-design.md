# 海关报关与商检设计文档

**版本**: 1.0
**日期**: 2026-05-23
**状态**: 待审核

---

## 1. 概述

### 1.1 设计目标

实现海关和商检机构的简化业务流程：提单签发后，出口商可申请出口报关和报检，海关完成审核→征税→放行，商检机构完成检验→合格→签发证书。包含关税计算和检验费计算功能。

### 1.2 核心决策

| 决策点 | 选择 | 理由 |
|--------|------|------|
| 流程深度 | 简化版 + 关税/检验费计算 | 教学模拟，聚焦核心业务环节 |
| 实现位置 | apps/transactions | 与合同/货运/保险同属交易流程 |
| 触发时机 | 提单签发后（Shipment.status='shipped'） | 贴近真实贸易流程 |
| 关联对象 | FK → Shipment | 报关/报检的前提是提单已签发 |
| 报关范围 | 仅出口报关 | 教学场景，进口报关可后续扩展 |
| 关税计算 | 固定 HS 编码税率表 | 教学场景，无需实时查询 |
| 检验费计算 | 固定费率 | 教学场景，简化计算 |

### 1.3 贸易关系

```
提单签发（Shipment.status='shipped'）
  → 出口商申请报关 → 海关审核 → 征税 → 放行
  → 出口商报检     → 商检机构检验 → 合格 → 签发证书 + 产地证
```

---

## 2. 数据模型

### 2.1 CustomsDeclaration 模型

```python
class CustomsDeclaration(models.Model):
    """出口报关单"""

    class Status(models.TextChoices):
        DECLARED = 'declared', '已申报'
        REVIEWING = 'reviewing', '审核中'
        ASSESSED = 'assessed', '已征税'
        CLEARED = 'cleared', '已放行'
        REJECTED = 'rejected', '已退单'

    shipment = models.ForeignKey(
        'transactions.Shipment',
        on_delete=models.CASCADE,
        related_name='customs_declarations'
    )
    declarant = models.ForeignKey(
        'roles.Company',
        on_delete=models.PROTECT,
        related_name='customs_declarations'
    )
    customs_office = models.ForeignKey(
        'roles.Company',
        on_delete=models.PROTECT,
        related_name='processed_declarations'
    )
    declaration_no = models.CharField('报关单号', max_length=50, unique=True, editable=False)
    hs_code = models.CharField('HS编码', max_length=20)
    goods_name = models.CharField('品名', max_length=200)
    quantity = models.DecimalField('数量', max_digits=12, decimal_places=2)
    unit_value = models.DecimalField('单价', max_digits=12, decimal_places=2)
    total_value = models.DecimalField('总价', max_digits=14, decimal_places=2)
    currency = models.CharField('币种', max_length=10, default='USD')
    duty_rate = models.DecimalField('关税率', max_digits=5, decimal_places=4, default=0)
    duty_amount = models.DecimalField('关税金额', max_digits=14, decimal_places=2, default=0)
    vat_rate = models.DecimalField('增值税率', max_digits=5, decimal_places=4, default=0)
    vat_amount = models.DecimalField('增值税金额', max_digits=14, decimal_places=2, default=0)
    status = models.CharField(
        '状态',
        max_length=20,
        choices=Status.choices,
        default=Status.DECLARED
    )
    notes = models.TextField('备注', blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_declarations'
    )
    reviewed_at = models.DateTimeField('审核时间', null=True, blank=True)
    assessed_at = models.DateTimeField('征税时间', null=True, blank=True)
    cleared_at = models.DateTimeField('放行时间', null=True, blank=True)
    rejected_at = models.DateTimeField('退单时间', null=True, blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'customs_declarations'
        verbose_name = '出口报关单'
        verbose_name_plural = '出口报关单'
        ordering = ['-created_at']

    def __str__(self):
        return self.declaration_no

    def save(self, *args, **kwargs):
        if not self.declaration_no:
            import random
            from django.utils import timezone
            date_str = timezone.now().strftime('%Y%m%d')
            for _ in range(10):
                rand_str = f'{random.randint(100000, 999999)}'
                no = f'CD{date_str}{rand_str}'
                if not CustomsDeclaration.objects.filter(declaration_no=no).exists():
                    self.declaration_no = no
                    break
            else:
                raise RuntimeError('无法生成唯一报关单号，请重试')
        super().save(*args, **kwargs)
```

### 2.2 InspectionApplication 模型

```python
class InspectionApplication(models.Model):
    """检验申请（报检单）"""

    class Status(models.TextChoices):
        APPLIED = 'applied', '已报检'
        INSPECTING = 'inspecting', '检验中'
        PASSED = 'passed', '合格'
        CERTIFIED = 'certified', '已签发证书'
        FAILED = 'failed', '不合格'

    class InspectionType(models.TextChoices):
        LEGAL = 'legal', '法定检验'
        GENERAL = 'general', '一般鉴定'

    shipment = models.ForeignKey(
        'transactions.Shipment',
        on_delete=models.CASCADE,
        related_name='inspection_applications'
    )
    applicant = models.ForeignKey(
        'roles.Company',
        on_delete=models.PROTECT,
        related_name='inspection_applications'
    )
    inspector = models.ForeignKey(
        'roles.Company',
        on_delete=models.PROTECT,
        related_name='processed_inspections'
    )
    application_no = models.CharField('报检号', max_length=50, unique=True, editable=False)
    product_name = models.CharField('品名', max_length=200)
    product_spec = models.CharField('规格', max_length=200, blank=True)
    quantity = models.DecimalField('数量', max_digits=12, decimal_places=2)
    goods_value = models.DecimalField('货值', max_digits=14, decimal_places=2, default=0)
    inspection_type = models.CharField(
        '检验类型',
        max_length=20,
        choices=InspectionType.choices,
        default=InspectionType.LEGAL
    )
    fee = models.DecimalField('检验费', max_digits=14, decimal_places=2, default=0)
    fee_currency = models.CharField('费用币种', max_length=10, default='CNY')
    certificate_no = models.CharField('检验证书号', max_length=50, blank=True)
    origin_certificate_no = models.CharField('产地证号', max_length=50, blank=True)
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
        related_name='created_inspections'
    )
    inspecting_at = models.DateTimeField('开始检验时间', null=True, blank=True)
    passed_at = models.DateTimeField('合格时间', null=True, blank=True)
    certified_at = models.DateTimeField('签发时间', null=True, blank=True)
    failed_at = models.DateTimeField('不合格时间', null=True, blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'inspection_applications'
        verbose_name = '检验申请'
        verbose_name_plural = '检验申请'
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
                no = f'IA{date_str}{rand_str}'
                if not InspectionApplication.objects.filter(application_no=no).exists():
                    self.application_no = no
                    break
            else:
                raise RuntimeError('无法生成唯一报检号，请重试')
        super().save(*args, **kwargs)
```

### 2.3 状态流转

**CustomsDeclaration：**
```
Declared ──→ Reviewing ──→ Assessed ──→ Cleared
   │              │
   └──────→ Rejected ←──┘
```

| 当前状态 | 操作 | 目标状态 | 操作者 |
|---------|------|---------|--------|
| Declared | review | Reviewing | 海关 |
| Declared | reject | Rejected | 海关 |
| Reviewing | assess | Assessed | 海关 |
| Assessed | clear | Cleared | 海关 |

**InspectionApplication：**
```
Applied ──→ Inspecting ──→ Passed ──→ Certified
  │                           │
  └──────→ Failed ←───────────┘
```

| 当前状态 | 操作 | 目标状态 | 操作者 |
|---------|------|---------|--------|
| Applied | inspect | Inspecting | 商检机构 |
| Inspecting | pass | Passed | 商检机构 |
| Inspecting | fail | Failed | 商检机构 |
| Passed | certify | Certified | 商检机构 |

---

## 3. 关税计算

### 3.1 HS 编码税率表

固定税率，基于 HS 编码前 2 位：

| HS 编码范围 | 货物类别 | 关税率 | 增值税率 |
|------------|---------|-------|---------|
| 61-63 | 纺织品 | 10% | 13% |
| 85 | 电子产品 | 8% | 13% |
| 84 | 机械 | 12% | 13% |
| 01-24 | 食品 | 15% | 9% |
| 其他 | 默认 | 10% | 13% |

### 3.2 计算公式

```
关税 = 完税价格 × 关税率
增值税 = (完税价格 + 关税) × 增值税率
总税额 = 关税 + 增值税
完税价格 = 报关总价值
```

---

## 4. 检验费计算

### 4.1 费率表

| 检验类型 | 费率 | 说明 |
|---------|------|------|
| 法定检验 | 0.5% | 按货值计 |
| 一般鉴定 | 0.3% | 按货值计 |
| 产地证 | 固定 100 元 | 一次性费用 |

### 4.2 计算公式

```
检验费 = 货值 × 费率
```

---

## 5. 服务层

### 5.1 CustomsService

```python
class CustomsService:
    @staticmethod
    def create_declaration(user, shipment_id, customs_office_id, hs_code, **kwargs):
        """出口商申报（出口商角色，Shipment 已签发提单）"""

    @staticmethod
    def calculate_duties(hs_code, total_value):
        """关税计算（根据 HS 编码查税率表）"""

    @staticmethod
    def review(declaration_id, user):
        """海关审核"""

    @staticmethod
    def assess(declaration_id, user):
        """海关征税（自动计算关税+增值税）"""

    @staticmethod
    def clear(declaration_id, user):
        """海关放行"""

    @staticmethod
    def reject(declaration_id, user, reason=''):
        """海关退单"""
```

### 5.2 InspectionService

```python
class InspectionService:
    @staticmethod
    def create_application(user, shipment_id, inspector_id, inspection_type='legal', **kwargs):
        """出口商报检（出口商角色，Shipment 已签发提单）"""

    @staticmethod
    def calculate_fee(inspection_type, goods_value):
        """检验费计算"""

    @staticmethod
    def inspect(application_id, user):
        """商检机构开始检验"""

    @staticmethod
    def pass_inspection(application_id, user):
        """商检合格"""

    @staticmethod
    def certify(application_id, user, certificate_no, origin_certificate_no=''):
        """签发检验证书 + 产地证"""

    @staticmethod
    def fail_inspection(application_id, user, reason=''):
        """检验不合格"""
```

---

## 6. API 接口

### 6.1 报关 API

| 端点 | 方法 | 说明 | 权限 |
|------|------|------|------|
| `/api/v1/customs-declarations/` | GET/POST | 报关列表/创建 | 出口商创建 |
| `/api/v1/customs-declarations/{id}/` | GET | 报关详情 | 参与方 |
| `/api/v1/customs-declarations/{id}/review/` | POST | 审核 | 海关 |
| `/api/v1/customs-declarations/{id}/assess/` | POST | 征税 | 海关 |
| `/api/v1/customs-declarations/{id}/clear/` | POST | 放行 | 海关 |
| `/api/v1/customs-declarations/{id}/reject/` | POST | 退单 | 海关 |

### 6.2 商检 API

| 端点 | 方法 | 说明 | 权限 |
|------|------|------|------|
| `/api/v1/inspection-applications/` | GET/POST | 报检列表/创建 | 出口商创建 |
| `/api/v1/inspection-applications/{id}/` | GET | 报检详情 | 参与方 |
| `/api/v1/inspection-applications/{id}/inspect/` | POST | 开始检验 | 商检机构 |
| `/api/v1/inspection-applications/{id}/pass/` | POST | 合格 | 商检机构 |
| `/api/v1/inspection-applications/{id}/certify/` | POST | 签发证书 | 商检机构 |
| `/api/v1/inspection-applications/{id}/fail/` | POST | 不合格 | 商检机构 |

---

## 7. 与现有系统的集成

### 7.1 前置条件

- 报关/报检要求 Shipment 状态为 `shipped`（提单已签发）
- 创建时自动校验 Shipment 状态

### 7.2 与 Shipment 的关系

- CustomsDeclaration 和 InspectionApplication 通过 FK 关联 Shipment
- 一个 Shipment 可以有多条报关记录（实际一般一条，但允许重报）
- 一个 Shipment 可以有多条报检记录

### 7.3 审计日志

所有操作通过 `TransactionService.log_transaction` 记录，关联到 Shipment 对应的 Transaction。

### 7.4 角色权限

- 创建报关/报检：需要 exporter 角色，且公司为 Shipment 的 shipper
- 审核/征税/放行/退单：需要 customs 角色，且公司为报关单的 customs_office
- 检验/合格/签发/不合格：需要 inspection 角色，且公司为报检单的 inspector

---

## 8. 不在范围内

- 进口报关
- 查验抽查
- HS 编码智能匹配
- 实时税费查询
- 归类争议
- 复检流程
- 前端 UI
