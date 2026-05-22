# 交易系统核心流程设计文档：合同与信用证

**版本**: 1.0
**日期**: 2026-05-22
**作者**: Claude
**状态**: 已审核

---

## 1. 概述

本文档定义 SimTrade 交易系统中合同与信用证的核心功能设计，包括状态机、服务层、API 接口和前端页面。

### 1.1 设计目标

- 实现完整的合同签署流程（草稿→确认→签字→生效）
- 实现完整的信用证流程（开证→交单→议付→付款）
- 支持合同和信用证的修改流程
- 实现状态联动规则
- 提供完整的 API 接口和前端页面

### 1.2 设计决策

| 决策点 | 选择 | 理由 |
|--------|------|------|
| 信用证使用范围 | 可选 | 符合实际外贸场景，合同约定付款方式 |
| 银行角色处理 | 混合模式 | 开证学生操作，审核/议付系统自动 |
| 合同签字方式 | 电子签字 | 简化流程，点击按钮即可完成 |
| 状态联动实现 | 服务层方法 | 业务逻辑清晰，易于调试 |

---

## 2. 数据模型设计

### 2.1 扩展 Contract 模型

现有 Contract 模型已完整，需扩展状态选项：

```python
class Contract(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'draft', '草稿'
        PENDING_CONFIRM = 'pending_confirm', '待确认'
        AMENDING = 'amending', '修改中'
        PENDING_SIGN = 'pending_sign', '待签字'
        ONE_SIGNED = 'one_signed', '一方签字'
        SIGNED = 'signed', '已签字'
        EFFECTIVE = 'effective', '已生效'
        FULFILLED = 'fulfilled', '履行完毕'
        CANCELLED = 'cancelled', '已取消'
```

### 2.2 ContractAmendment 模型（新增）

```python
class ContractAmendment(models.Model):
    """合同修改记录"""
    contract = models.ForeignKey(Contract, on_delete=models.CASCADE, related_name='amendments')
    amendment_no = models.CharField('修改编号', max_length=50)
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    change_content = models.JSONField('修改内容')
    reason = models.TextField('修改原因')
    status = models.CharField('状态', max_length=20, choices=[('pending', '待处理'), ('accepted', '已接受'), ('rejected', '已拒绝')])
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    processed_at = models.DateTimeField('处理时间', null=True, blank=True)
```

### 2.3 LetterOfCredit 模型（新增）

```python
class LetterOfCredit(models.Model):
    """信用证"""
    class Status(models.TextChoices):
        DRAFT = 'draft', '草稿'
        PENDING_ISSUE = 'pending_issue', '待开证'
        ISSUED = 'issued', '已开证'
        AMENDING = 'amending', '修改中'
        SUBMITTED = 'submitted', '已交单'
        NEGOTIATED = 'negotiated', '已议付'
        PAID = 'paid', '已付款'
        CANCELLED = 'cancelled', '已取消'

    lc_no = models.CharField('信用证号', max_length=50, unique=True)
    contract = models.OneToOneField(Contract, on_delete=models.PROTECT, related_name='letter_of_credit')
    transaction = models.ForeignKey('Transaction', on_delete=models.PROTECT, related_name='letters_of_credit')
    status = models.CharField('状态', max_length=20, choices=Status.choices, default=Status.DRAFT)

    # 信用证当事人
    issuing_bank = models.CharField('开证行', max_length=200)
    advising_bank = models.CharField('通知行', max_length=200)
    applicant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='applied_letters_of_credit')
    beneficiary = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='beneficiary_letters_of_credit')

    # 金额与期限
    amount = models.DecimalField('金额', max_digits=14, decimal_places=2)
    currency = models.CharField('货币', max_length=10)
    issue_date = models.DateField('开证日期', null=True, blank=True)
    expiry_date = models.DateField('有效期')

    # 装运条款
    latest_shipment_date = models.DateField('最迟装运日期')
    port_of_loading = models.CharField('装运港', max_length=100)
    port_of_discharge = models.CharField('目的港', max_length=100)

    # 单据要求（JSON 格式）
    documents_required = models.JSONField('单据要求', default=list)

    # 系统处理时间戳
    issued_at = models.DateTimeField('开证时间', null=True, blank=True)
    advised_at = models.DateTimeField('通知时间', null=True, blank=True)
    submitted_at = models.DateTimeField('交单时间', null=True, blank=True)
    negotiated_at = models.DateTimeField('议付时间', null=True, blank=True)
    paid_at = models.DateTimeField('付款时间', null=True, blank=True)

    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
```

### 2.4 LcAmendment 模型（新增）

```python
class LcAmendment(models.Model):
    """信用证修改记录"""
    lc = models.ForeignKey(LetterOfCredit, on_delete=models.CASCADE, related_name='amendments')
    amendment_no = models.CharField('修改编号', max_length=50)
    initiated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    content = models.JSONField('修改内容')
    reason = models.TextField('修改原因')
    status = models.CharField('状态', max_length=20, choices=[('pending', '待处理'), ('approved', '已批准'), ('rejected', '已拒绝')])
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    processed_at = models.DateTimeField('处理时间', null=True, blank=True)
```

### 2.5 BankOperation 模型（新增）

```python
class BankOperation(models.Model):
    """银行业务操作记录"""
    OPERATION_TYPES = [
        ('issue', '开证'),
        ('advise', '通知'),
        ('negotiate', '议付'),
        ('pay', '付款'),
        ('amend', '修改'),
    ]

    lc = models.ForeignKey(LetterOfCredit, on_delete=models.CASCADE, related_name='bank_operations')
    operation_type = models.CharField('操作类型', max_length=20, choices=OPERATION_TYPES)
    processed_by = models.CharField('处理方', max_length=20, default='system')  # system/user
    operator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.TextField('备注', blank=True)
    result = models.JSONField('处理结果', default=dict, blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
```

---

## 3. 状态机设计

### 3.1 Contract 状态流转

```
草稿
  ↓ 出口商发送确认
待确认
  ↓ 进口商确认条款
待签字
  ↓ 一方签字
一方签字
  ↓ 另一方签字
已签字 → 已生效（立即生效）
  ↓ 履约完成
履行完毕

待确认 → 修改中（进口商请求修改）
修改中 → 待确认（出口商接受修改）

任何状态 → 已取消（双方同意或超时）
```

### 3.2 LetterOfCredit 状态流转

```
草稿（合同生效时自动创建）
  ↓ 进口商申请开证
待开证
  ↓ 系统自动开证
已开证
  ↓ 出口商请求修改（可选）
修改中 → 已开证（修改完成）
  ↓ 出口商交单
已交单
  ↓ 系统自动审单议付
已议付
  ↓ 系统自动付款
已付款

草稿/待开证 → 已取消
```

### 3.3 状态联动规则

| 触发条件 | 联动动作 |
|---------|---------|
| 合同双方签字完成 | Contract: 已签字 → 已生效 |
| 合同生效 | Transaction: 已签约 → 履约中 |
| 合同生效 + 付款方式=信用证 | 创建 LetterOfCredit: 草稿 |
| 进口商申请开证 | LetterOfCredit: 草稿 → 待开证 |
| 信用证待开证 | 系统自动开证：待开证 → 已开证 |
| 信用证已交单 | 系统自动审单议付：已交单 → 已议付 |
| 信用证已议付 | 系统自动付款：已议付 → 已付款 |
| 信用证已付款 | Transaction: 可收款 |

---

## 4. 服务层设计

### 4.1 ContractService（扩展）

```python
class ContractService:
    @staticmethod
    def create_from_transaction(transaction, contract_data):
        """从交易创建合同草稿"""

    @staticmethod
    def send_for_confirmation(contract, user):
        """发送确认：草稿 → 待确认"""

    @staticmethod
    def confirm_terms(contract, user):
        """确认条款：待确认 → 待签字"""

    @staticmethod
    def request_amendment(contract, amendment_data, user):
        """请求修改：待确认 → 修改中"""

    @staticmethod
    def accept_amendment(contract, amendment_id, user):
        """接受修改：修改中 → 待确认"""

    @staticmethod
    def sign(contract, user, party, ip_address):
        """签字：待签字 → 一方签字 → 已签字"""

    @staticmethod
    def become_effective(contract):
        """合同生效：已签字 → 已生效，触发联动"""

    @staticmethod
    def cancel(contract, user, reason):
        """取消合同"""
```

### 4.2 LetterOfCreditService（新增）

```python
class LetterOfCreditService:
    @staticmethod
    def create_from_contract(contract):
        """从合同创建信用证草稿"""

    @staticmethod
    def apply_for_issue(lc, user):
        """申请开证：草稿 → 待开证"""

    @staticmethod
    def auto_issue(lc):
        """系统自动开证：待开证 → 已开证"""

    @staticmethod
    def request_amendment(lc, content, user):
        """请求修改：已开证 → 修改中"""

    @staticmethod
    def approve_amendment(lc, amendment_id):
        """批准修改：修改中 → 已开证"""

    @staticmethod
    def withdraw_amendment(lc, user):
        """撤回修改请求：修改中 → 已开证"""

    @staticmethod
    def submit_documents(lc, document_ids, user):
        """交单：已开证 → 已交单"""

    @staticmethod
    def auto_negotiate(lc):
        """系统自动议付：已交单 → 已议付"""

    @staticmethod
    def auto_pay(lc):
        """系统自动付款：已议付 → 已付款"""

    @staticmethod
    def cancel(lc, user, reason):
        """取消信用证"""
```

### 4.3 StateTransitionService（新增）

```python
class StateTransitionService:
    @staticmethod
    def on_contract_effective(contract):
        """合同生效联动"""

    @staticmethod
    def on_contract_fulfilled(contract):
        """合同履行完毕联动"""

    @staticmethod
    def on_lc_created(lc):
        """信用证创建联动"""

    @staticmethod
    def on_lc_issued(lc):
        """信用证开立联动"""

    @staticmethod
    def on_lc_paid(lc):
        """信用证付款联动"""
```

---

## 5. API 接口设计

### 5.1 Contract API

| 端点 | 方法 | 说明 | 权限 |
|------|------|------|------|
| `/api/v1/contracts/` | POST | 创建合同草稿 | 出口商 |
| `/api/v1/contracts/{id}/` | GET | 获取合同详情 | 交易双方 |
| `/api/v1/contracts/{id}/send/` | POST | 发送确认 | 出口商 |
| `/api/v1/contracts/{id}/confirm/` | POST | 确认条款 | 进口商 |
| `/api/v1/contracts/{id}/request-change/` | POST | 请求修改 | 进口商 |
| `/api/v1/contracts/{id}/accept-change/` | POST | 接受修改 | 出口商 |
| `/api/v1/contracts/{id}/reject-change/` | POST | 拒绝修改 | 出口商 |
| `/api/v1/contracts/{id}/sign/` | POST | 签字 | 交易双方 |
| `/api/v1/contracts/{id}/cancel/` | POST | 取消合同 | 交易双方 |
| `/api/v1/contracts/{id}/status/` | GET | 获取当前状态和操作权限 | 交易双方 |
| `/api/v1/contracts/{id}/changes/` | GET | 获取修改历史 | 交易双方 |
| `/api/v1/contracts/{id}/versions/` | GET | 获取合同版本列表 | 交易双方 |

### 5.2 LetterOfCredit API

| 端点 | 方法 | 说明 | 权限 |
|------|------|------|------|
| `/api/v1/letters-of-credit/` | GET | 获取信用证列表 | 交易双方 |
| `/api/v1/letters-of-credit/{id}/` | GET | 获取信用证详情 | 交易双方 |
| `/api/v1/letters-of-credit/{id}/apply/` | POST | 申请开证 | 进口商 |
| `/api/v1/letters-of-credit/{id}/request-amendment/` | POST | 请求修改 | 出口商 |
| `/api/v1/letters-of-credit/{id}/accept-amendment/` | POST | 接受修改 | 进口商 |
| `/api/v1/letters-of-credit/{id}/withdraw-amendment/` | POST | 撤回修改请求 | 出口商 |
| `/api/v1/letters-of-credit/{id}/submit-documents/` | POST | 交单 | 出口商 |
| `/api/v1/letters-of-credit/{id}/submitted-documents/` | GET | 获取已提交单据列表 | 出口商 |
| `/api/v1/letters-of-credit/{id}/documents/` | GET | 获取所需单据列表 | 出口商 |
| `/api/v1/letters-of-credit/{id}/amendments/` | GET | 获取修改历史 | 交易双方 |
| `/api/v1/letters-of-credit/{id}/negotiation-result/` | GET | 获取议付结果 | 交易双方 |
| `/api/v1/letters-of-credit/{id}/operations/` | GET | 获取银行操作记录 | 交易双方 |

### 5.3 请求/响应格式

**创建合同请求：**
```json
{
  "transaction_id": 123,
  "trade_term": "FOB",
  "payment_term": "L/C",
  "delivery_time": "2026-08-30",
  "port_of_loading": "上海",
  "port_of_discharge": "洛杉矶",
  "product_name": "棉质T恤",
  "product_spec": "100%棉，M码",
  "quantity": 1000,
  "unit": "PCS",
  "unit_price": 5.50,
  "total_amount": 5500.00,
  "currency": "USD",
  "packing": "每箱20件，纸箱包装",
  "shipping_marks": "SKU123",
  "remarks": "质量要求符合行业标准"
}
```

**签字请求：**
```json
{
  "signer_name": "张三"
}
```

**请求修改：**
```json
{
  "change_content": {
    "delivery_time": "2026-09-15",
    "unit_price": 5.80,
    "reason": "原材料价格上涨"
  },
  "reason": "需要调整交货期和价格"
}
```

---

## 6. 前端页面设计

### 6.1 合同页面

- **合同列表页面**: `/transactions/{id}/contract/`
  - 合同概览
  - 状态进度条
  - 操作按钮

- **合同详情页面**: `/contracts/{id}/detail/`
  - 完整合同条款
  - 签字区域
  - 修改历史

- **合同修改页面**: `/contracts/{id}/edit/`
  - 修改建议展示
  - 修改前后对比
  - 接受/拒绝操作

### 6.2 信用证页面

- **信用证列表页面**: `/transactions/{id}/letter-of-credit/`
  - 信用证概览
  - 状态进度条
  - 操作入口

- **信用证详情页面**: `/letters-of-credit/{id}/detail/`
  - 完整信用证条款
  - 银行操作记录
  - 操作按钮

- **开证申请页面**: `/letters-of-credit/{id}/apply/`
  - 开证信息确认
  - 提交申请

- **交单页面**: `/letters-of-credit/{id}/submit-documents/`
  - 所需单据列表
  - 单据选择
  - 提交交单

---

## 7. 测试策略

### 7.1 单元测试

- ContractService 各方法测试
- LetterOfCreditService 各方法测试
- StateTransitionService 联动测试

### 7.2 集成测试

- 完整合同流程测试
- 完整信用证流程测试
- 异常流程测试

### 7.3 API 测试

- 接口权限测试
- 参数验证测试
- 状态流转测试

---

## 8. 实施计划

详见 `docs/superpowers/plans/2026-05-22-contract-lc-system.md`
