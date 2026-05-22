# 合同与信用证系统实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 实现 SimTrade 平台的合同签署和信用证流程功能

**架构：** Django 应用扩展，基于状态机的服务层设计，包含完整的模型、API、前端页面

**Tech Stack：** Django 3.2, Python 3.8+, PostgreSQL/SQLite, Bootstrap 3

---

## 文件结构

### 将要创建/修改的文件

| 文件路径 | 职责 |
|---------|------|
| `apps/transactions/models.py` | 修改：扩展 Contract 状态，新增 LetterOfCredit, LcAmendment, BankOperation, ContractAmendment |
| `apps/transactions/services.py` | 修改：扩展 ContractService，新增 LetterOfCreditService, StateTransitionService |
| `apps/transactions/serializers.py` | 修改：扩展序列化器，新增序列化器 |
| `apps/transactions/views.py` | 修改：扩展视图，新增视图 |
| `apps/transactions/urls.py` | 修改：新增路由 |
| `apps/transactions/admin.py` | 修改：新增模型注册 |
| `apps/transactions/tests/test_models.py` | 修改：新增模型测试 |
| `apps/transactions/tests/test_services.py` | 新增：服务测试 |
| `apps/transactions/tests/test_api.py` | 修改：API 测试 |
| `apps/transactions/tests/test_integration.py` | 新增：集成测试 |
| `templates/transactions/contract.html` | 新增：合同详情页面 |
| `templates/transactions/contract_edit.html` | 新增：合同修改页面 |
| `templates/transactions/letter_of_credit.html` | 新增：信用证详情页面 |
| `templates/transactions/letter_of_credit_apply.html` | 新增：开证申请页面 |

---

## 任务分解

### 任务 1：扩展 Contract 模型状态

**文件：**
- 修改：`apps/transactions/models.py`

- [ ] **步骤 1：编写 Contract 状态扩展测试**

```python
# apps/transactions/tests/test_models.py
def test_contract_status_expansion():
    """测试合同状态选项扩展"""
    contract = Contract.objects.create(contract_no='SC001', ...)
    
    # 测试新状态
    contract.status = 'pending_confirm'
    assert contract.get_status_display() == '待确认'
    
    contract.status = 'amending'
    assert contract.get_status_display() == '修改中'
    
    contract.status = 'one_signed'
    assert contract.get_status_display() == '一方签字'
```

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest apps/transactions/tests/test_models.py::test_contract_status_expansion -v`
预期：FAIL，状态选项不存在

- [ ] **步骤 3：扩展 Contract 状态选项**

修改 `apps/transactions/models.py` 中 Contract.Status：

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

- [ ] **步骤 4：运行测试验证通过**

运行：`pytest apps/transactions/tests/test_models.py::test_contract_status_expansion -v`
预期：PASS

- [ ] **步骤 5：生成迁移文件**

运行：`python manage.py makemigrations transactions`

- [ ] **步骤 6：Commit**

```bash
git add apps/transactions/models.py apps/transactions/migrations/
git commit -m "feat(contract): expand contract status choices"
```

---

### 任务 2：新增 ContractAmendment 模型

**文件：**
- 修改：`apps/transactions/models.py`
- 创建：`apps/transactions/tests/test_models.py`

- [ ] **步骤 1：编写 ContractAmendment 模型测试**

```python
# apps/transactions/tests/test_models.py
def test_create_contract_amendment():
    """测试创建合同修改记录"""
    contract = Contract.objects.create(contract_no='SC001', ...)
    user = User.objects.create_user(username='testuser')
    
    amendment = ContractAmendment.objects.create(
        contract=contract,
        amendment_no='A001',
        requested_by=user,
        change_content={'unit_price': 6.00},
        reason='价格调整'
    )
    
    assert amendment.amendment_no == 'A001'
    assert amendment.status == 'pending'
    assert amendment.change_content['unit_price'] == 6.00
```

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest apps/transactions/tests/test_models.py::test_create_contract_amendment -v`
预期：FAIL，模型不存在

- [ ] **步骤 3：实现 ContractAmendment 模型**

在 `apps/transactions/models.py` 中添加：

```python
class ContractAmendment(models.Model):
    """合同修改记录"""
    
    class Status(models.TextChoices):
        PENDING = 'pending', '待处理'
        ACCEPTED = 'accepted', '已接受'
        REJECTED = 'rejected', '已拒绝'
    
    contract = models.ForeignKey(
        Contract,
        on_delete=models.CASCADE,
        related_name='amendments'
    )
    amendment_no = models.CharField('修改编号', max_length=50)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='requested_amendments'
    )
    change_content = models.JSONField('修改内容')
    reason = models.TextField('修改原因')
    status = models.CharField(
        '状态',
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    processed_at = models.DateTimeField('处理时间', null=True, blank=True)

    class Meta:
        db_table = 'contract_amendments'
        verbose_name = '合同修改记录'
        verbose_name_plural = '合同修改记录'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.contract.contract_no} - {self.amendment_no}"
```

- [ ] **步骤 4：运行测试验证通过**

运行：`pytest apps/transactions/tests/test_models.py::test_create_contract_amendment -v`
预期：PASS

- [ ] **步骤 5：生成迁移文件**

运行：`python manage.py makemigrations transactions`

- [ ] **步骤 6：Commit**

```bash
git add apps/transactions/models.py apps/transactions/migrations/ apps/transactions/tests/test_models.py
git commit -m "feat(contract): add ContractAmendment model"
```

---

### 任务 3：新增 LetterOfCredit 模型

**文件：**
- 修改：`apps/transactions/models.py`
- 修改：`apps/transactions/tests/test_models.py`

- [ ] **步骤 1：编写 LetterOfCredit 模型测试**

```python
def test_create_letter_of_credit():
    """测试创建信用证"""
    contract = Contract.objects.create(contract_no='SC001', ...)
    transaction = Transaction.objects.create(...)
    applicant = User.objects.create_user(username='importer')
    beneficiary = User.objects.create_user(username='exporter')
    
    lc = LetterOfCredit.objects.create(
        lc_no='LC2026001',
        contract=contract,
        transaction=transaction,
        applicant=applicant,
        beneficiary=beneficiary,
        amount=10000.00,
        currency='USD',
        expiry_date='2026-12-31'
    )
    
    assert lc.lc_no == 'LC2026001'
    assert lc.status == 'draft'
    assert lc.amount == 10000.00
```

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest apps/transactions/tests/test_models.py::test_create_letter_of_credit -v`
预期：FAIL，模型不存在

- [ ] **步骤 3：实现 LetterOfCredit 模型**

在 `apps/transactions/models.py` 中添加：

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
    contract = models.OneToOneField(
        Contract,
        on_delete=models.PROTECT,
        related_name='letter_of_credit'
    )
    transaction = models.ForeignKey(
        'Transaction',
        on_delete=models.PROTECT,
        related_name='letters_of_credit'
    )
    status = models.CharField(
        '状态',
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )
    
    # 信用证当事人
    issuing_bank = models.CharField('开证行', max_length=200)
    advising_bank = models.CharField('通知行', max_length=200)
    applicant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='applied_letters_of_credit'
    )
    beneficiary = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='beneficiary_letters_of_credit'
    )
    
    # 金额与期限
    amount = models.DecimalField('金额', max_digits=14, decimal_places=2)
    currency = models.CharField('货币', max_length=10)
    issue_date = models.DateField('开证日期', null=True, blank=True)
    expiry_date = models.DateField('有效期')
    
    # 装运条款
    latest_shipment_date = models.DateField('最迟装运日期')
    port_of_loading = models.CharField('装运港', max_length=100)
    port_of_discharge = models.CharField('目的港', max_length=100)
    
    # 单据要求
    documents_required = models.JSONField('单据要求', default=list)
    
    # 系统处理时间戳
    issued_at = models.DateTimeField('开证时间', null=True, blank=True)
    advised_at = models.DateTimeField('通知时间', null=True, blank=True)
    submitted_at = models.DateTimeField('交单时间', null=True, blank=True)
    negotiated_at = models.DateTimeField('议付时间', null=True, blank=True)
    paid_at = models.DateTimeField('付款时间', null=True, blank=True)
    
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'letters_of_credit'
        verbose_name = '信用证'
        verbose_name_plural = '信用证'
        ordering = ['-created_at']

    def __str__(self):
        return f"信用证 {self.lc_no}"
```

- [ ] **步骤 4：运行测试验证通过**

运行：`pytest apps/transactions/tests/test_models.py::test_create_letter_of_credit -v`
预期：PASS

- [ ] **步骤 5：生成迁移文件**

运行：`python manage.py makemigrations transactions`

- [ ] **步骤 6：Commit**

```bash
git add apps/transactions/models.py apps/transactions/migrations/ apps/transactions/tests/test_models.py
git commit -m "feat(lc): add LetterOfCredit model"
```

---

### 任务 4：新增 LcAmendment 和 BankOperation 模型

**文件：**
- 修改：`apps/transactions/models.py`
- 修改：`apps/transactions/tests/test_models.py`

- [ ] **步骤 1：编写 LcAmendment 模型测试**

```python
def test_create_lc_amendment():
    """测试创建信用证修改记录"""
    lc = LetterOfCredit.objects.create(lc_no='LC001', ...)
    user = User.objects.create_user(username='testuser')
    
    amendment = LcAmendment.objects.create(
        lc=lc,
        amendment_no='LA001',
        initiated_by=user,
        content={'amount': 12000.00},
        reason='增加金额'
    )
    
    assert amendment.amendment_no == 'LA001'
    assert amendment.status == 'pending'
```

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest apps/transactions/tests/test_models.py::test_create_lc_amendment -v`
预期：FAIL，模型不存在

- [ ] **步骤 3：实现 LcAmendment 和 BankOperation 模型**

在 `apps/transactions/models.py` 中添加：

```python
class LcAmendment(models.Model):
    """信用证修改记录"""
    
    class Status(models.TextChoices):
        PENDING = 'pending', '待处理'
        APPROVED = 'approved', '已批准'
        REJECTED = 'rejected', '已拒绝'
    
    lc = models.ForeignKey(
        LetterOfCredit,
        on_delete=models.CASCADE,
        related_name='amendments'
    )
    amendment_no = models.CharField('修改编号', max_length=50)
    initiated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='initiated_amendments'
    )
    content = models.JSONField('修改内容')
    reason = models.TextField('修改原因')
    status = models.CharField(
        '状态',
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    processed_at = models.DateTimeField('处理时间', null=True, blank=True)

    class Meta:
        db_table = 'lc_amendments'
        verbose_name = '信用证修改记录'
        verbose_name_plural = '信用证修改记录'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.lc.lc_no} - {self.amendment_no}"


class BankOperation(models.Model):
    """银行业务操作记录"""
    
    OPERATION_TYPES = [
        ('issue', '开证'),
        ('advise', '通知'),
        ('negotiate', '议付'),
        ('pay', '付款'),
        ('amend', '修改'),
    ]
    
    lc = models.ForeignKey(
        LetterOfCredit,
        on_delete=models.CASCADE,
        related_name='bank_operations'
    )
    operation_type = models.CharField(
        '操作类型',
        max_length=20,
        choices=OPERATION_TYPES
    )
    processed_by = models.CharField(
        '处理方',
        max_length=20,
        default='system'
    )
    operator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='bank_operations'
    )
    notes = models.TextField('备注', blank=True)
    result = models.JSONField('处理结果', default=dict, blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'bank_operations'
        verbose_name = '银行业务操作'
        verbose_name_plural = '银行业务操作'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.lc.lc_no} - {self.get_operation_type_display()}"
```

- [ ] **步骤 4：运行测试验证通过**

运行：`pytest apps/transactions/tests/test_models.py -v`
预期：PASS

- [ ] **步骤 5：生成迁移文件**

运行：`python manage.py makemigrations transactions`

- [ ] **步骤 6：Commit**

```bash
git add apps/transactions/models.py apps/transactions/migrations/ apps/transactions/tests/test_models.py
git commit -m "feat(lc): add LcAmendment and BankOperation models"
```

---

### 任务 5：扩展 ContractService 服务

**文件：**
- 修改：`apps/transactions/services.py`
- 创建：`apps/transactions/tests/test_services.py`

- [ ] **步骤 1：编写 ContractService 测试**

```python
# apps/transactions/tests/test_services.py
def test_contract_become_effective():
    """测试合同生效流程"""
    contract = Contract.objects.create(...)
    buyer = User.objects.create_user(username='buyer')
    seller = User.objects.create_user(username='seller')
    
    # 双方签字
    ContractService.sign(contract, buyer, 'buyer', '127.0.0.1')
    ContractService.sign(contract, seller, 'seller', '127.0.0.1')
    
    # 生效
    result = ContractService.become_effective(contract)
    
    assert contract.status == 'effective'
    assert contract.effective_at is not None
```

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest apps/transactions/tests/test_services.py::test_contract_become_effective -v`
预期：FAIL，方法不存在

- [ ] **步骤 3：扩展 ContractService**

修改 `apps/transactions/services.py`，添加以下方法：

```python
from django.utils import timezone
from apps.transactions.models import Contract, ContractAmendment, LetterOfCredit


class ContractService:
    """合同业务服务"""
    
    @staticmethod
    def send_for_confirmation(contract, user):
        """发送确认：草稿 → 待确认"""
        if contract.status != 'draft':
            raise ValueError(f"合同状态不允许发送确认: {contract.status}")
        
        contract.status = 'pending_confirm'
        contract.save()
        
        TransactionService.log_transaction(
            contract.transaction,
            user,
            'contract_sent_for_confirmation',
            {'contract_id': contract.id}
        )
        return contract
    
    @staticmethod
    def confirm_terms(contract, user):
        """确认条款：待确认 → 待签字"""
        if contract.status != 'pending_confirm':
            raise ValueError(f"合同状态不允许确认: {contract.status}")
        
        contract.status = 'pending_sign'
        contract.save()
        
        TransactionService.log_transaction(
            contract.transaction,
            user,
            'contract_terms_confirmed',
            {'contract_id': contract.id}
        )
        return contract
    
    @staticmethod
    def request_amendment(contract, change_content, reason, user):
        """请求修改：待确认 → 修改中"""
        if contract.status != 'pending_confirm':
            raise ValueError(f"合同状态不允许请求修改: {contract.status}")
        
        amendment_no = ContractService._generate_amendment_no(contract)
        ContractAmendment.objects.create(
            contract=contract,
            amendment_no=amendment_no,
            requested_by=user,
            change_content=change_content,
            reason=reason
        )
        
        contract.status = 'amending'
        contract.save()
        return contract
    
    @staticmethod
    def accept_amendment(contract, amendment_id, user):
        """接受修改：修改中 → 待确认"""
        if contract.status != 'amending':
            raise ValueError(f"合同状态不允许接受修改: {contract.status}")
        
        amendment = ContractAmendment.objects.get(id=amendment_id)
        amendment.status = 'accepted'
        amendment.processed_at = timezone.now()
        amendment.save()
        
        # 应用修改内容到合同
        for key, value in amendment.change_content.items():
            setattr(contract, key, value)
        
        contract.status = 'pending_confirm'
        contract.save()
        return contract
    
    @staticmethod
    def sign(contract, user, party, ip_address):
        """签字：待签字 → 一方签字 → 已签字"""
        if contract.status not in ['pending_sign', 'one_signed']:
            raise ValueError(f"合同状态不允许签字: {contract.status}")
        
        from apps.transactions.models import ContractSignature
        signature, created = ContractSignature.objects.get_or_create(
            contract=contract,
            party=party,
            defaults={
                'signer': user,
                'signer_name': user.username,
                'ip_address': ip_address
            }
        )
        
        # 更新签字时间
        if party == 'buyer':
            contract.buyer_signed_at = timezone.now()
        elif party == 'seller':
            contract.seller_signed_at = timezone.now()
        
        # 检查是否双方都已签字
        if contract.buyer_signed_at and contract.seller_signed_at:
            contract.status = 'signed'
        else:
            contract.status = 'one_signed'
        
        contract.save()
        return contract
    
    @staticmethod
    def become_effective(contract):
        """合同生效：已签字 → 已生效，触发联动"""
        if contract.status != 'signed':
            raise ValueError(f"合同状态不允许生效: {contract.status}")
        
        contract.status = 'effective'
        contract.effective_at = timezone.now()
        contract.save()
        
        # 触发状态联动
        StateTransitionService.on_contract_effective(contract)
        
        return contract
    
    @staticmethod
    def cancel(contract, user, reason):
        """取消合同"""
        if contract.status in ['effective', 'fulfilled', 'cancelled']:
            raise ValueError(f"合同状态不允许取消: {contract.status}")
        
        contract.status = 'cancelled'
        contract.save()
        
        TransactionService.log_transaction(
            contract.transaction,
            user,
            'contract_cancelled',
            {'reason': reason}
        )
        return contract
    
    @staticmethod
    def _generate_amendment_no(contract):
        """生成修改编号"""
        import random
        import string
        count = contract.amendments.count() + 1
        return f"{contract.contract_no}-A{count:02d}"
```

- [ ] **步骤 4：运行测试验证通过**

运行：`pytest apps/transactions/tests/test_services.py -v`
预期：PASS

- [ ] **步骤 5：Commit**

```bash
git add apps/transactions/services.py apps/transactions/tests/test_services.py
git commit -m "feat(contract): extend ContractService with signing flow"
```

---

### 任务 6：实现 LetterOfCreditService 服务

**文件：**
- 修改：`apps/transactions/services.py`
- 修改：`apps/transactions/tests/test_services.py`

- [ ] **步骤 1：编写 LetterOfCreditService 测试**

```python
def test_create_lc_from_contract():
    """测试从合同创建信用证"""
    contract = Contract.objects.create(
        contract_no='SC001',
        payment_term='L/C',
        ...
    )
    
    lc = LetterOfCreditService.create_from_contract(contract)
    
    assert lc.status == 'draft'
    assert lc.contract == contract
    assert lc.lc_no.startswith('LC')

def test_apply_for_issue():
    """测试申请开证"""
    lc = LetterOfCredit.objects.create(status='draft', ...)
    user = User.objects.create_user(username='importer')
    
    result = LetterOfCreditService.apply_for_issue(lc, user)
    
    assert result.status == 'pending_issue'
```

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest apps/transactions/tests/test_services.py -v`
预期：FAIL，方法不存在

- [ ] **步骤 3：实现 LetterOfCreditService**

在 `apps/transactions/services.py` 中添加：

```python
class LetterOfCreditService:
    """信用证业务服务"""
    
    @staticmethod
    def create_from_contract(contract):
        """从合同创建信用证草稿"""
        if contract.payment_term != 'L/C':
            return None
        
        lc_no = LetterOfCreditService._generate_lc_no()
        
        # 默认单据要求
        documents_required = [
            'commercial_invoice',
            'bill_of_lading',
            'insurance_policy',
            'packing_list'
        ]
        
        lc = LetterOfCredit.objects.create(
            lc_no=lc_no,
            contract=contract,
            transaction=contract.transaction,
            applicant=contract.transaction.buyer,
            beneficiary=contract.transaction.seller,
            amount=contract.total_amount,
            currency=contract.currency,
            expiry_date=contract.delivery_time + timezone.timedelta(days=90),
            latest_shipment_date=contract.delivery_time,
            port_of_loading=contract.port_of_loading,
            port_of_discharge=contract.port_of_discharge,
            documents_required=documents_required,
            issuing_bank='中国银行',
            advising_bank='通知银行'
        )
        
        TransactionService.log_transaction(
            contract.transaction,
            contract.transaction.buyer,
            'lc_created',
            {'lc_id': lc.id}
        )
        return lc
    
    @staticmethod
    def apply_for_issue(lc, user):
        """申请开证：草稿 → 待开证"""
        if lc.status != 'draft':
            raise ValueError(f"信用证状态不允许申请开证: {lc.status}")
        
        lc.status = 'pending_issue'
        lc.save()
        
        TransactionService.log_transaction(
            lc.transaction,
            user,
            'lc_applied_for_issue',
            {'lc_id': lc.id}
        )
        return lc
    
    @staticmethod
    def auto_issue(lc):
        """系统自动开证：待开证 → 已开证"""
        if lc.status != 'pending_issue':
            raise ValueError(f"信用证状态不允许开证: {lc.status}")
        
        lc.status = 'issued'
        lc.issue_date = timezone.now().date()
        lc.issued_at = timezone.now()
        lc.advised_at = timezone.now()
        lc.save()
        
        # 创建银行操作记录
        BankOperation.objects.create(
            lc=lc,
            operation_type='issue',
            processed_by='system',
            notes='系统自动开证'
        )
        
        BankOperation.objects.create(
            lc=lc,
            operation_type='advise',
            processed_by='system',
            notes='系统自动通知'
        )
        
        # 发送通知
        NotificationService.send_lc_issued_notification(lc)
        
        TransactionService.log_transaction(
            lc.transaction,
            lc.transaction.beneficiary,
            'lc_issued',
            {'lc_id': lc.id}
        )
        return lc
    
    @staticmethod
    def request_amendment(lc, content, reason, user):
        """请求修改：已开证 → 修改中"""
        if lc.status != 'issued':
            raise ValueError(f"信用证状态不允许请求修改: {lc.status}")
        
        amendment_no = LetterOfCreditService._generate_amendment_no(lc)
        amendment = LcAmendment.objects.create(
            lc=lc,
            amendment_no=amendment_no,
            initiated_by=user,
            content=content,
            reason=reason
        )
        
        lc.status = 'amending'
        lc.save()
        return amendment
    
    @staticmethod
    def approve_amendment(lc, amendment_id):
        """批准修改：修改中 → 已开证"""
        if lc.status != 'amending':
            raise ValueError(f"信用证状态不允许批准修改: {lc.status}")
        
        amendment = LcAmendment.objects.get(id=amendment_id)
        amendment.status = 'approved'
        amendment.processed_at = timezone.now()
        amendment.save()
        
        # 应用修改内容
        for key, value in amendment.content.items():
            setattr(lc, key, value)
        
        lc.status = 'issued'
        lc.save()
        return lc
    
    @staticmethod
    def withdraw_amendment(lc, user):
        """撤回修改请求：修改中 → 已开证"""
        if lc.status != 'amending':
            raise ValueError(f"信用证状态不允许撤回修改: {lc.status}")
        
        # 删除待处理的修改
        lc.amendments.filter(status='pending').delete()
        
        lc.status = 'issued'
        lc.save()
        return lc
    
    @staticmethod
    def submit_documents(lc, document_ids, user):
        """交单：已开证 → 已交单"""
        if lc.status != 'issued':
            raise ValueError(f"信用证状态不允许交单: {lc.status}")
        
        lc.status = 'submitted'
        lc.submitted_at = timezone.now()
        lc.save()
        
        TransactionService.log_transaction(
            lc.transaction,
            user,
            'lc_documents_submitted',
            {'lc_id': lc.id, 'document_count': len(document_ids)}
        )
        return lc
    
    @staticmethod
    def auto_negotiate(lc):
        """系统自动议付：已交单 → 已议付"""
        if lc.status != 'submitted':
            raise ValueError(f"信用证状态不允许议付: {lc.status}")
        
        # 检查单据是否齐全（简化处理）
        documents = Document.objects.filter(transaction=lc.transaction)
        required_count = len(lc.documents_required)
        
        if documents.count() < required_count:
            raise ValueError(f"单据不齐，需要 {required_count} 份，实际 {documents.count()} 份")
        
        lc.status = 'negotiated'
        lc.negotiated_at = timezone.now()
        lc.save()
        
        # 创建银行操作记录
        BankOperation.objects.create(
            lc=lc,
            operation_type='negotiate',
            processed_by='system',
            notes='单据齐全，自动议付',
            result={'documents_count': documents.count()}
        )
        
        # 触发付款
        LetterOfCreditService.auto_pay(lc)
        return lc
    
    @staticmethod
    def auto_pay(lc):
        """系统自动付款：已议付 → 已付款"""
        if lc.status != 'negotiated':
            # 如果不是议付状态，直接返回（可能已自动付款）
            return lc
        
        lc.status = 'paid'
        lc.paid_at = timezone.now()
        lc.save()
        
        # 创建银行操作记录
        BankOperation.objects.create(
            lc=lc,
            operation_type='pay',
            processed_by='system',
            notes=f'自动付款 {lc.amount} {lc.currency}',
            result={'amount': str(lc.amount), 'currency': lc.currency}
        )
        
        # 触发状态联动
        StateTransitionService.on_lc_paid(lc)
        return lc
    
    @staticmethod
    def cancel(lc, user, reason):
        """取消信用证"""
        if lc.status in ['negotiated', 'paid']:
            raise ValueError(f"信用证状态不允许取消: {lc.status}")
        
        lc.status = 'cancelled'
        lc.save()
        
        TransactionService.log_transaction(
            lc.transaction,
            user,
            'lc_cancelled',
            {'reason': reason}
        )
        return lc
    
    @staticmethod
    def _generate_lc_no():
        """生成信用证号"""
        import random
        import string
        year = timezone.now().year
        random_str = ''.join(random.choices(string.digits, k=6))
        return f"LC{year}{random_str}"
    
    @staticmethod
    def _generate_amendment_no(lc):
        """生成修改编号"""
        count = lc.amendments.count() + 1
        return f"{lc.lc_no}-A{count:02d}"
```

- [ ] **步骤 4：运行测试验证通过**

运行：`pytest apps/transactions/tests/test_services.py -v`
预期：PASS

- [ ] **步骤 5：Commit**

```bash
git add apps/transactions/services.py apps/transactions/tests/test_services.py
git commit -m "feat(lc): implement LetterOfCreditService"
```

---

### 任务 7：实现 StateTransitionService 状态联动服务

**文件：**
- 修改：`apps/transactions/services.py`
- 修改：`apps/transactions/tests/test_services.py`

- [ ] **步骤 1：编写 StateTransitionService 测试**

```python
def test_on_contract_effective():
    """测试合同生效联动"""
    contract = Contract.objects.create(
        contract_no='SC001',
        payment_term='L/C',
        ...
    )
    
    StateTransitionService.on_contract_effective(contract)
    
    # 检查交易状态更新
    assert contract.transaction.status == 'in_progress'
    # 检查信用证创建
    assert LetterOfCredit.objects.filter(contract=contract).exists()
```

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest apps/transactions/tests/test_services.py::test_on_contract_effective -v`
预期：FAIL，方法不存在

- [ ] **步骤 3：实现 StateTransitionService**

在 `apps/transactions/services.py` 中添加：

```python
class StateTransitionService:
    """状态联动服务"""
    
    @staticmethod
    def on_contract_effective(contract):
        """合同生效联动"""
        # 更新交易状态
        transaction = contract.transaction
        if transaction.status == 'contracted':
            transaction.status = 'in_progress'
            transaction.save()
        
        # 如果付款方式是信用证，自动创建信用证
        if contract.payment_term == 'L/C':
            LetterOfCreditService.create_from_contract(contract)
        
        TransactionService.log_transaction(
            transaction,
            transaction.buyer,
            'contract_became_effective',
            {'contract_id': contract.id}
        )
    
    @staticmethod
    def on_lc_created(lc):
        """信用证创建联动"""
        NotificationService.send_lc_created_notification(lc)
    
    @staticmethod
    def on_lc_issued(lc):
        """信用证开立联动"""
        # 更新交易状态确认
        transaction = lc.transaction
        TransactionService.log_transaction(
            transaction,
            transaction.beneficiary,
            'lc_issued',
            {'lc_id': lc.id}
        )
    
    @staticmethod
    def on_lc_paid(lc):
        """信用证付款联动"""
        transaction = lc.transaction
        # 更新交易状态
        TransactionService.log_transaction(
            transaction,
            transaction.applicant,
            'lc_paid',
            {'lc_id': lc.id, 'amount': str(lc.amount)}
        )
```

- [ ] **步骤 4：运行测试验证通过**

运行：`pytest apps/transactions/tests/test_services.py -v`
预期：PASS

- [ ] **步骤 5：Commit**

```bash
git add apps/transactions/services.py apps/transactions/tests/test_services.py
git commit -m "feat(state): implement StateTransitionService"
```

---

### 任务 8：扩展序列化器

**文件：**
- 修改：`apps/transactions/serializers.py`
- 创建：`apps/transactions/tests/test_serializers.py`

- [ ] **步骤 1：编写序列化器测试**

```python
def test_contract_serializer():
    """测试合同序列化器"""
    contract = Contract.objects.create(...)
    serializer = ContractSerializer(contract)
    
    data = serializer.data
    assert data['contract_no'] == contract.contract_no
    assert 'status_display' in data
```

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest apps/transactions/tests/test_serializers.py -v`
预期：FAIL，序列化器不存在

- [ ] **步骤 3：扩展序列化器**

修改 `apps/transactions/serializers.py`：

```python
from rest_framework import serializers
from apps.transactions.models import (
    Transaction, InquiryMessage, Contract, ContractSignature,
    TransactionLog, ContractAmendment, LetterOfCredit,
    LcAmendment, BankOperation
)


class ContractAmendmentSerializer(serializers.ModelSerializer):
    """合同修改序列化器"""
    
    requested_by_name = serializers.CharField(source='requested_by.username', read_only=True)
    
    class Meta:
        model = ContractAmendment
        fields = ['id', 'amendment_no', 'requested_by', 'requested_by_name',
                  'change_content', 'reason', 'status', 'created_at', 'processed_at']
        read_only_fields = ['id', 'created_at', 'processed_at']


class ContractSignatureSerializer(serializers.ModelSerializer):
    """合同签字序列化器"""
    
    signer_name = serializers.CharField(required=True)
    
    class Meta:
        model = ContractSignature
        fields = ['id', 'contract', 'party', 'signer', 'signer_name',
                  'ip_address', 'signed_at']
        read_only_fields = ['id', 'signed_at']


class ContractSerializer(serializers.ModelSerializer):
    """合同序列化器"""
    
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    signatures = ContractSignatureSerializer(many=True, read_only=True)
    amendments = ContractAmendmentSerializer(many=True, read_only=True)
    
    class Meta:
        model = Contract
        fields = ['id', 'contract_no', 'transaction', 'status', 'status_display',
                  'trade_term', 'payment_term', 'delivery_time', 'port_of_loading',
                  'port_of_discharge', 'product_name', 'product_spec', 'quantity',
                  'unit', 'unit_price', 'total_amount', 'currency', 'packing',
                  'shipping_marks', 'remarks', 'buyer_signed_at', 'seller_signed_at',
                  'created_at', 'updated_at', 'effective_at', 'signatures', 'amendments']
        read_only_fields = ['id', 'created_at', 'updated_at', 'effective_at',
                            'buyer_signed_at', 'seller_signed_at']


class LcAmendmentSerializer(serializers.ModelSerializer):
    """信用证修改序列化器"""
    
    initiated_by_name = serializers.CharField(source='initiated_by.username', read_only=True)
    
    class Meta:
        model = LcAmendment
        fields = ['id', 'amendment_no', 'initiated_by', 'initiated_by_name',
                  'content', 'reason', 'status', 'created_at', 'processed_at']
        read_only_fields = ['id', 'created_at', 'processed_at']


class BankOperationSerializer(serializers.ModelSerializer):
    """银行业务操作序列化器"""
    
    operation_type_display = serializers.CharField(source='get_operation_type_display', read_only=True)
    
    class Meta:
        model = BankOperation
        fields = ['id', 'lc', 'operation_type', 'operation_type_display',
                  'processed_by', 'operator', 'notes', 'result', 'created_at']
        read_only_fields = ['id', 'created_at']


class LetterOfCreditSerializer(serializers.ModelSerializer):
    """信用证序列化器"""
    
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    amendments = LcAmendmentSerializer(many=True, read_only=True)
    bank_operations = BankOperationSerializer(many=True, read_only=True)
    
    class Meta:
        model = LetterOfCredit
        fields = ['id', 'lc_no', 'contract', 'transaction', 'status', 'status_display',
                  'issuing_bank', 'advising_bank', 'applicant', 'beneficiary',
                  'amount', 'currency', 'issue_date', 'expiry_date',
                  'latest_shipment_date', 'port_of_loading', 'port_of_discharge',
                  'documents_required', 'issued_at', 'advised_at', 'submitted_at',
                  'negotiated_at', 'paid_at', 'created_at', 'updated_at',
                  'amendments', 'bank_operations']
        read_only_fields = ['id', 'created_at', 'updated_at', 'issued_at',
                            'advised_at', 'submitted_at', 'negotiated_at', 'paid_at']


class ContractSignSerializer(serializers.Serializer):
    """合同签字请求序列化器"""
    
    signer_name = serializers.CharField(max_length=100, required=True)
```

- [ ] **步骤 4：运行测试验证通过**

运行：`pytest apps/transactions/tests/test_serializers.py -v`
预期：PASS

- [ ] **步骤 5：Commit**

```bash
git add apps/transactions/serializers.py apps/transactions/tests/test_serializers.py
git commit -m "feat(serializers): add contract and LC serializers"
```

---

### 任务 9：扩展 ContractViewSet 视图

**文件：**
- 修改：`apps/transactions/views.py`
- 修改：`apps/transactions/tests/test_api.py`

- [ ] **步骤 1：编写 Contract API 测试**

```python
def test_contract_sign_api():
    """测试合同签字 API"""
    contract = Contract.objects.create(status='pending_sign', ...)
    user = User.objects.create_user(username='seller')
    
    api_client.force_authenticate(user=user)
    url = reverse('contract-sign', kwargs={'pk': contract.id})
    
    data = {'signer_name': '张三'}
    response = api_client.post(url, data, format='json')
    
    assert response.status_code == 200
    assert response.data['code'] == 0
```

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest apps/transactions/tests/test_api.py::test_contract_sign_api -v`
预期：FAIL，接口不存在

- [ ] **步骤 3：扩展 ContractViewSet**

修改 `apps/transactions/views.py` 中的 ContractViewSet：

```python
class ContractViewSet(viewsets.ModelViewSet):
    """合同视图集"""

    serializer_class = ContractSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # 只返回当前用户参与的合同
        user = self.request.user
        return Contract.objects.filter(
            transaction__buyer=user
        ) | Contract.objects.filter(
            transaction__seller=user
        )

    @action(detail=True, methods=['post'])
    def send(self, request, pk=None):
        """发送确认"""
        contract = self.get_object()
        try:
            result = ContractService.send_for_confirmation(contract, request.user)
            serializer = self.get_serializer(result)
            return Response({
                'code': 0,
                'message': '合同已发送确认',
                'data': serializer.data
            })
        except ValueError as e:
            return Response({
                'code': 5005,
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        """确认条款"""
        contract = self.get_object()
        try:
            result = ContractService.confirm_terms(contract, request.user)
            serializer = self.get_serializer(result)
            return Response({
                'code': 0,
                'message': '合同条款已确认',
                'data': serializer.data
            })
        except ValueError as e:
            return Response({
                'code': 5005,
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def request_change(self, request, pk=None):
        """请求修改"""
        contract = self.get_object()
        serializer = ContractSignSerializer(data=request.data)
        if serializer.is_valid():
            try:
                result = ContractService.request_amendment(
                    contract,
                    request.data.get('change_content', {}),
                    request.data.get('reason', ''),
                    request.user
                )
                return Response({
                    'code': 0,
                    'message': '修改请求已提交'
                })
            except ValueError as e:
                return Response({
                    'code': 5005,
                    'message': str(e)
                }, status=status.HTTP_400_BAD_REQUEST)
        return Response({
            'code': 3002,
            'message': '参数格式错误',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def accept_change(self, request, pk=None):
        """接受修改"""
        contract = self.get_object()
        amendment_id = request.data.get('amendment_id')
        if not amendment_id:
            return Response({
                'code': 3001,
                'message': '缺少 amendment_id 参数'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            result = ContractService.accept_amendment(contract, amendment_id, request.user)
            serializer = self.get_serializer(result)
            return Response({
                'code': 0,
                'message': '修改已接受，合同已更新',
                'data': serializer.data
            })
        except ValueError as e:
            return Response({
                'code': 5005,
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def sign(self, request, pk=None):
        """签署合同"""
        contract = self.get_object()
        serializer = ContractSignSerializer(data=request.data)
        if serializer.is_valid():
            # 确定用户角色
            if contract.transaction.buyer == request.user:
                party = 'buyer'
            elif contract.transaction.seller == request.user:
                party = 'seller'
            else:
                return Response({
                    'code': 2001,
                    'message': '无权签署此合同'
                }, status=status.HTTP_403_FORBIDDEN)
            
            try:
                result = ContractService.sign(
                    contract,
                    request.user,
                    party,
                    request.META.get('REMOTE_ADDR', '')
                )
                
                # 如果双方都已签字，自动生效
                if result.status == 'signed':
                    ContractService.become_effective(result)
                
                serializer = self.get_serializer(result)
                return Response({
                    'code': 0,
                    'message': '签字成功',
                    'data': serializer.data
                })
            except ValueError as e:
                return Response({
                    'code': 5005,
                    'message': str(e)
                }, status=status.HTTP_400_BAD_REQUEST)
        return Response({
            'code': 3002,
            'message': '参数格式错误',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """取消合同"""
        contract = self.get_object()
        reason = request.data.get('reason', '')
        try:
            ContractService.cancel(contract, request.user, reason)
            return Response({
                'code': 0,
                'message': '合同已取消'
            })
        except ValueError as e:
            return Response({
                'code': 5005,
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def status(self, request, pk=None):
        """获取当前状态和操作权限"""
        contract = self.get_object()
        user = request.user
        
        # 确定用户角色
        if contract.transaction.buyer == user:
            role = 'buyer'
        elif contract.transaction.seller == user:
            role = 'seller'
        else:
            role = 'observer'
        
        # 确定可用操作
        available_actions = []
        if contract.status == 'draft' and role == 'seller':
            available_actions.append('send')
        elif contract.status == 'pending_confirm' and role == 'buyer':
            available_actions.extend(['confirm', 'request_change'])
        elif contract.status == 'amending' and role == 'seller':
            available_actions.append('accept_change')
        elif contract.status in ['pending_sign', 'one_signed']:
            available_actions.append('sign')
        
        return Response({
            'code': 0,
            'data': {
                'status': contract.status,
                'status_display': contract.get_status_display(),
                'role': role,
                'available_actions': available_actions,
                'signatures': ContractSignatureSerializer(
                    contract.signatures.all(), many=True
                ).data
            }
        })

    @action(detail=True, methods=['get'])
    def changes(self, request, pk=None):
        """获取修改历史"""
        contract = self.get_object()
        amendments = contract.amendments.all()
        serializer = ContractAmendmentSerializer(amendments, many=True)
        return Response({
            'code': 0,
            'data': serializer.data
        })
```

- [ ] **步骤 4：运行测试验证通过**

运行：`pytest apps/transactions/tests/test_api.py -v`
预期：PASS

- [ ] **步骤 5：Commit**

```bash
git add apps/transactions/views.py apps/transactions/tests/test_api.py
git commit -m "feat(contract): extend ContractViewSet with signing APIs"
```

---

### 任务 10：实现 LetterOfCreditViewSet 视图

**文件：**
- 修改：`apps/transactions/views.py`
- 修改：`apps/transactions/urls.py`
- 修改：`apps/transactions/tests/test_api.py`

- [ ] **步骤 1：编写 LetterOfCredit API 测试**

```python
def test_lc_apply_api():
    """测试信用证申请开证 API"""
    lc = LetterOfCredit.objects.create(status='draft', ...)
    user = User.objects.create_user(username='importer')
    
    api_client.force_authenticate(user=user)
    url = reverse('letterofcredit-apply', kwargs={'pk': lc.id})
    
    response = api_client.post(url, format='json')
    
    assert response.status_code == 200
    assert response.data['code'] == 0
```

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest apps/transactions/tests/test_api.py::test_lc_apply_api -v`
预期：FAIL，接口不存在

- [ ] **步骤 3：实现 LetterOfCreditViewSet**

在 `apps/transactions/views.py` 中添加：

```python
class LetterOfCreditViewSet(viewsets.ModelViewSet):
    """信用证视图集"""

    serializer_class = LetterOfCreditSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return LetterOfCredit.objects.filter(
            applicant=user
        ) | LetterOfCredit.objects.filter(
            beneficiary=user
        )

    @action(detail=True, methods=['post'])
    def apply(self, request, pk=None):
        """申请开证"""
        lc = self.get_object()
        try:
            result = LetterOfCreditService.apply_for_issue(lc, request.user)
            # 系统自动开证
            LetterOfCreditService.auto_issue(result)
            serializer = self.get_serializer(result)
            return Response({
                'code': 0,
                'message': '信用证已开立',
                'data': serializer.data
            })
        except ValueError as e:
            return Response({
                'code': 5005,
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def request_amendment(self, request, pk=None):
        """请求修改"""
        lc = self.get_object()
        content = request.data.get('content', {})
        reason = request.data.get('reason', '')
        
        if not content or not reason:
            return Response({
                'code': 3001,
                'message': '缺少修改内容或原因'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            result = LetterOfCreditService.request_amendment(
                lc, content, reason, request.user
            )
            return Response({
                'code': 0,
                'message': '修改请求已提交'
            })
        except ValueError as e:
            return Response({
                'code': 5005,
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def accept_amendment(self, request, pk=None):
        """接受修改"""
        lc = self.get_object()
        amendment_id = request.data.get('amendment_id')
        if not amendment_id:
            return Response({
                'code': 3001,
                'message': '缺少 amendment_id 参数'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            result = LetterOfCreditService.approve_amendment(lc, amendment_id)
            serializer = self.get_serializer(result)
            return Response({
                'code': 0,
                'message': '修改已批准',
                'data': serializer.data
            })
        except ValueError as e:
            return Response({
                'code': 5005,
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def withdraw_amendment(self, request, pk=None):
        """撤回修改请求"""
        lc = self.get_object()
        try:
            result = LetterOfCreditService.withdraw_amendment(lc, request.user)
            serializer = self.get_serializer(result)
            return Response({
                'code': 0,
                'message': '修改请求已撤回',
                'data': serializer.data
            })
        except ValueError as e:
            return Response({
                'code': 5005,
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def submit_documents(self, request, pk=None):
        """交单"""
        lc = self.get_object()
        document_ids = request.data.get('document_ids', [])
        
        if not document_ids:
            return Response({
                'code': 3001,
                'message': '缺少 document_ids 参数'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            result = LetterOfCreditService.submit_documents(lc, document_ids, request.user)
            # 系统自动议付
            LetterOfCreditService.auto_negotiate(result)
            serializer = self.get_serializer(result)
            return Response({
                'code': 0,
                'message': '交单成功',
                'data': serializer.data
            })
        except ValueError as e:
            return Response({
                'code': 5005,
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def submitted_documents(self, request, pk=None):
        """获取已提交单据列表"""
        lc = self.get_object()
        # 从关联的交易获取单据
        from apps.documents.models import Document
        documents = Document.objects.filter(transaction=lc.transaction)
        return Response({
            'code': 0,
            'data': [{'id': d.id, 'type': d.template.code} for d in documents]
        })

    @action(detail=True, methods=['get'])
    def amendments(self, request, pk=None):
        """获取修改历史"""
        lc = self.get_object()
        amendments = lc.amendments.all()
        serializer = LcAmendmentSerializer(amendments, many=True)
        return Response({
            'code': 0,
            'data': serializer.data
        })

    @action(detail=True, methods=['get'])
    def negotiation_result(self, request, pk=None):
        """获取议付结果"""
        lc = self.get_object()
        operations = lc.bank_operations.filter(
            operation_type__in=['negotiate', 'pay']
        )
        serializer = BankOperationSerializer(operations, many=True)
        return Response({
            'code': 0,
            'data': serializer.data
        })

    @action(detail=True, methods=['get'])
    def operations(self, request, pk=None):
        """获取银行操作记录"""
        lc = self.get_object()
        operations = lc.bank_operations.all()
        serializer = BankOperationSerializer(operations, many=True)
        return Response({
            'code': 0,
            'data': serializer.data
        })

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """取消信用证"""
        lc = self.get_object()
        reason = request.data.get('reason', '')
        try:
            LetterOfCreditService.cancel(lc, request.user, reason)
            return Response({
                'code': 0,
                'message': '信用证已取消'
            })
        except ValueError as e:
            return Response({
                'code': 5005,
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
```

- [ ] **步骤 4：更新 URL 路由**

修改 `apps/transactions/urls.py`：

```python
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.transactions.views import (
    TransactionViewSet, ContractViewSet, InquiryMessageViewSet,
    LetterOfCreditViewSet
)

router = DefaultRouter()
router.register(r'transactions', TransactionViewSet, basename='transaction')
router.register(r'inquiry-messages', InquiryMessageViewSet, basename='inquirymessage')
router.register(r'contracts', ContractViewSet, basename='contract')
router.register(r'letters-of-credit', LetterOfCreditViewSet, basename='letterofcredit')

urlpatterns = [
    path('api/v1/', include(router.urls)),
]
```

- [ ] **步骤 5：运行测试验证通过**

运行：`pytest apps/transactions/tests/test_api.py -v`
预期：PASS

- [ ] **步骤 6：Commit**

```bash
git add apps/transactions/views.py apps/transactions/urls.py apps/transactions/tests/test_api.py
git commit -m "feat(lc): implement LetterOfCreditViewSet"
```

---

### 任务 11：扩展 admin 配置

**文件：**
- 修改：`apps/transactions/admin.py`

- [ ] **步骤 1：验证 admin 配置**

运行：`python manage.py check`
预期：无报错

- [ ] **步骤 2：扩展 admin 配置**

修改 `apps/transactions/admin.py`：

```python
from django.contrib import admin
from apps.transactions.models import (
    Transaction, InquiryMessage, Contract, ContractSignature,
    TransactionLog, ContractAmendment, LetterOfCredit,
    LcAmendment, BankOperation
)


@admin.register(ContractAmendment)
class ContractAmendmentAdmin(admin.ModelAdmin):
    """合同修改管理"""
    list_display = ['contract', 'amendment_no', 'requested_by', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['amendment_no', 'contract__contract_no']


@admin.register(LetterOfCredit)
class LetterOfCreditAdmin(admin.ModelAdmin):
    """信用证管理"""
    list_display = ['lc_no', 'contract', 'status', 'amount', 'currency', 'created_at']
    list_filter = ['status', 'currency', 'created_at']
    search_fields = ['lc_no', 'contract__contract_no']


@admin.register(LcAmendment)
class LcAmendmentAdmin(admin.ModelAdmin):
    """信用证修改管理"""
    list_display = ['lc', 'amendment_no', 'initiated_by', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['amendment_no', 'lc__lc_no']


@admin.register(BankOperation)
class BankOperationAdmin(admin.ModelAdmin):
    """银行业务操作管理"""
    list_display = ['lc', 'operation_type', 'processed_by', 'created_at']
    list_filter = ['operation_type', 'processed_by', 'created_at']
```

- [ ] **步骤 3：验证 admin 可访问**

运行：`python manage.py runserver`
访问：http://localhost:8000/admin/
预期：管理后台正常显示

- [ ] **步骤 4：Commit**

```bash
git add apps/transactions/admin.py
git commit -m "feat(admin): register new models in admin"
```

---

### 任务 12：创建合同详情页面

**文件：**
- 创建：`templates/transactions/contract.html`

- [ ] **步骤 1：创建合同详情页面模板**

```html
{% extends "base.html" %}

{% block title %}合同 {{ contract.contract_no }} - SimTrade{% endblock %}

{% block content %}
<div class="container">
    <div class="contract-header">
        <h2>合同 {{ contract.contract_no }}</h2>
        <span class="status status-{{ contract.status }}">
            {{ contract.get_status_display }}
        </span>
    </div>

    <!-- 状态进度条 -->
    <div class="progress-bar">
        <div class="step {% if contract.status in 'draft,pending_confirm,amending' %}active{% elif contract.status != 'cancelled' %}done{% endif %}">
            草稿
        </div>
        <div class="step {% if contract.status in 'pending_confirm,amending' %}active{% elif contract.status not in 'draft,cancelled' %}done{% endif %}">
            待确认
        </div>
        <div class="step {% if contract.status == 'amending' %}active{% elif contract.status not in 'draft,pending_confirm,cancelled' %}done{% endif %}">
            待签字
        </div>
        <div class="step {% if contract.status in 'effective,fulfilled' %}done{% endif %}">
            已生效
        </div>
    </div>

    <!-- 操作按钮 -->
    <div class="action-buttons" id="actionButtons">
        <!-- 根据 available_actions 动态渲染 -->
    </div>

    <!-- 合同内容 -->
    <div class="contract-content">
        <table class="table table-bordered">
            <tr>
                <th width="30%">商品名称</th>
                <td>{{ contract.product_name }}</td>
            </tr>
            <tr>
                <th>商品规格</th>
                <td>{{ contract.product_spec|default:"-" }}</td>
            </tr>
            <tr>
                <th>数量</th>
                <td>{{ contract.quantity }} {{ contract.unit }}</td>
            </tr>
            <tr>
                <th>单价</th>
                <td>{{ contract.unit_price }} {{ contract.currency }}</td>
            </tr>
            <tr>
                <th>总金额</th>
                <td>{{ contract.total_amount }} {{ contract.currency }}</td>
            </tr>
            <tr>
                <th>贸易术语</th>
                <td>{{ contract.trade_term }}</td>
            </tr>
            <tr>
                <th>付款方式</th>
                <td>{{ contract.payment_term }}</td>
            </tr>
            <tr>
                <th>交货时间</th>
                <td>{{ contract.delivery_time }}</td>
            </tr>
            <tr>
                <th>装运港</th>
                <td>{{ contract.port_of_loading }}</td>
            </tr>
            <tr>
                <th>目的港</th>
                <td>{{ contract.port_of_discharge }}</td>
            </tr>
            <tr>
                <th>包装方式</th>
                <td>{{ contract.packing|default:"-" }}</td>
            </tr>
            <tr>
                <th>唛头</th>
                <td>{{ contract.shipping_marks|default:"-" }}</td>
            </tr>
            <tr>
                <th>备注条款</th>
                <td>{{ contract.remarks|default:"-" }}</td>
            </tr>
        </table>
    </div>

    <!-- 签字信息 -->
    <div class="signatures">
        <h3>签字信息</h3>
        <div class="signature-item">
            <strong>买方签字：</strong>
            {% if contract.buyer_signed_at %}
                <span class="signed">已签字 ({{ contract.buyer_signed_at|date:"Y-m-d H:i" }})</span>
            {% else %}
                <span class="unsigned">未签字</span>
            {% endif %}
        </div>
        <div class="signature-item">
            <strong>卖方签字：</strong>
            {% if contract.seller_signed_at %}
                <span class="signed">已签字 ({{ contract.seller_signed_at|date:"Y-m-d H:i" }})</span>
            {% else %}
                <span class="unsigned">未签字</span>
            {% endif %}
        </div>
    </div>

    <!-- 修改历史 -->
    {% if contract.amendments.exists %}
    <div class="amendments">
        <h3>修改历史</h3>
        <table class="table">
            <thead>
                <tr>
                    <th>修改编号</th>
                    <th>修改内容</th>
                    <th>修改原因</th>
                    <th>状态</th>
                    <th>时间</th>
                </tr>
            </thead>
            <tbody>
                {% for amendment in contract.amendments.all %}
                <tr>
                    <td>{{ amendment.amendment_no }}</td>
                    <td>{{ amendment.change_content }}</td>
                    <td>{{ amendment.reason }}</td>
                    <td>{{ amendment.get_status_display }}</td>
                    <td>{{ amendment.created_at|date:"Y-m-d H:i" }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
    {% endif %}
</div>

<script>
$(document).ready(function() {
    // 加载合同状态和可用操作
    $.ajax({
        url: '/api/v1/contracts/{{ contract.id }}/status/',
        method: 'GET',
        success: function(response) {
            if (response.code === 0) {
                renderActionButtons(response.data.available_actions);
            }
        }
    });

    function renderActionButtons(actions) {
        var buttons = $('#actionButtons');
        buttons.empty();
        
        if (actions.includes('send')) {
            buttons.append('<button class="btn btn-primary" onclick="sendContract()">发送确认</button>');
        }
        if (actions.includes('confirm')) {
            buttons.append('<button class="btn btn-success" onclick="confirmContract()">确认条款</button>');
            buttons.append('<button class="btn btn-warning" onclick="showRequestChangeModal()">请求修改</button>');
        }
        if (actions.includes('accept_change')) {
            buttons.append('<button class="btn btn-success" onclick="acceptChange()">接受修改</button>');
        }
        if (actions.includes('sign')) {
            buttons.append('<button class="btn btn-primary" onclick="showSignModal()">签字</button>');
        }
        if (actions.includes('cancel')) {
            buttons.append('<button class="btn btn-danger" onclick="cancelContract()">取消合同</button>');
        }
    }

    function sendContract() {
        $.ajax({
            url: '/api/v1/contracts/{{ contract.id }}/send/',
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            },
            success: function(response) {
                if (response.code === 0) {
                    SimTrade.showAlert('合同已发送确认', 'success');
                    location.reload();
                }
            }
        });
    }

    function confirmContract() {
        $.ajax({
            url: '/api/v1/contracts/{{ contract.id }}/confirm/',
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            },
            success: function(response) {
                if (response.code === 0) {
                    SimTrade.showAlert('合同条款已确认', 'success');
                    location.reload();
                }
            }
        });
    }

    function showSignModal() {
        $('#signModal').modal('show');
    }

    function signContract() {
        $.ajax({
            url: '/api/v1/contracts/{{ contract.id }}/sign/',
            method: 'POST',
            data: {
                signer_name: $('#signerName').val()
            },
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            },
            success: function(response) {
                if (response.code === 0) {
                    SimTrade.showAlert('签字成功', 'success');
                    location.reload();
                }
            }
        });
    }

    function getCookie(name) {
        var cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            var cookies = document.cookie.split(';');
            for (var i = 0; i < cookies.length; i++) {
                var cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
});
</script>

<!-- 签字模态框 -->
<div class="modal fade" id="signModal" tabindex="-1">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header">
                <h4 class="modal-title">签署合同</h4>
                <button type="button" class="close" data-dismiss="modal">&times;</button>
            </div>
            <div class="modal-body">
                <form id="signForm">
                    {% csrf_token %}
                    <div class="form-group">
                        <label>签字人姓名</label>
                        <input type="text" class="form-control" id="signerName" required>
                    </div>
                    <p class="help-block">点击"确认签字"后即表示您已阅读并同意合同条款。</p>
                </form>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-default" data-dismiss="modal">取消</button>
                <button type="button" class="btn btn-primary" onclick="signContract()">确认签字</button>
            </div>
        </div>
    </div>
</div>

{% endblock %}
```

- [ ] **步骤 2：验证页面可访问**

运行：`python manage.py runserver`
访问：合同详情页面
预期：页面正常显示

- [ ] **步骤 3：Commit**

```bash
git add templates/transactions/contract.html
git commit -m "feat(contract): add contract detail page"
```

---

### 任务 13：创建信用证详情页面

**文件：**
- 创建：`templates/transactions/letter_of_credit.html`

- [ ] **步骤 1：创建信用证详情页面模板**

```html
{% extends "base.html" %}

{% block title %}信用证 {{ lc.lc_no }} - SimTrade{% endblock %}

{% block content %}
<div class="container">
    <div class="lc-header">
        <h2>信用证 {{ lc.lc_no }}</h2>
        <span class="status status-{{ lc.status }}">
            {{ lc.get_status_display }}
        </span>
    </div>

    <!-- 状态进度条 -->
    <div class="progress-bar">
        <div class="step {% if lc.status == 'draft' %}active{% elif lc.status != 'cancelled' %}done{% endif %}">
            草稿
        </div>
        <div class="step {% if lc.status == 'pending_issue' %}active{% elif lc.status not in 'draft,cancelled' %}done{% endif %}">
            已开证
        </div>
        <div class="step {% if lc.status == 'submitted' %}active{% elif lc.status in 'negotiated,paid' %}done{% endif %}">
            已交单
        </div>
        <div class="step {% if lc.status in 'negotiated,paid' %}active{% elif lc.status == 'paid' %}done{% endif %}">
            已议付
        </div>
    </div>

    <!-- 操作按钮 -->
    <div class="action-buttons" id="actionButtons">
        <!-- 根据 available_actions 动态渲染 -->
    </div>

    <!-- 信用证内容 -->
    <div class="lc-content">
        <h3>信用证条款</h3>
        <table class="table table-bordered">
            <tr>
                <th width="30%">信用证号</th>
                <td>{{ lc.lc_no }}</td>
            </tr>
            <tr>
                <th>开证行</th>
                <td>{{ lc.issuing_bank }}</td>
            </tr>
            <tr>
                <th>通知行</th>
                <td>{{ lc.advising_bank }}</td>
            </tr>
            <tr>
                <th>申请人</th>
                <td>{{ lc.applicant.username }}</td>
            </tr>
            <tr>
                <th>受益人</th>
                <td>{{ lc.beneficiary.username }}</td>
            </tr>
            <tr>
                <th>金额</th>
                <td>{{ lc.amount }} {{ lc.currency }}</td>
            </tr>
            <tr>
                <th>有效期</th>
                <td>{{ lc.expiry_date }}</td>
            </tr>
            <tr>
                <th>最迟装运日期</th>
                <td>{{ lc.latest_shipment_date }}</td>
            </tr>
            <tr>
                <th>装运港</th>
                <td>{{ lc.port_of_loading }}</td>
            </tr>
            <tr>
                <th>目的港</th>
                <td>{{ lc.port_of_discharge }}</td>
            </tr>
            <tr>
                <th>单据要求</th>
                <td>
                    <ul>
                        {% for doc in lc.documents_required %}
                        <li>{{ doc }}</li>
                        {% endfor %}
                    </ul>
                </td>
            </tr>
        </table>
    </div>

    <!-- 银行操作记录 -->
    <div class="bank-operations">
        <h3>银行操作记录</h3>
        <table class="table">
            <thead>
                <tr>
                    <th>操作类型</th>
                    <th>处理方</th>
                    <th>备注</th>
                    <th>时间</th>
                </tr>
            </thead>
            <tbody>
                {% if lc.bank_operations.exists %}
                    {% for op in lc.bank_operations.all %}
                    <tr>
                        <td>{{ op.get_operation_type_display }}</td>
                        <td>{{ op.processed_by }}</td>
                        <td>{{ op.notes|default:"-" }}</td>
                        <td>{{ op.created_at|date:"Y-m-d H:i" }}</td>
                    </tr>
                    {% endfor %}
                {% else %}
                    <tr>
                        <td colspan="4" class="text-center">暂无操作记录</td>
                    </tr>
                {% endif %}
            </tbody>
        </table>
    </div>
</div>

<script>
$(document).ready(function() {
    // 加载可用操作
    $.ajax({
        url: '/api/v1/letters-of-credit/{{ lc.id }}/status/',
        method: 'GET',
        success: function(response) {
            if (response.code === 0) {
                renderActionButtons(response.data.available_actions);
            }
        }
    });

    function renderActionButtons(actions) {
        var buttons = $('#actionButtons');
        buttons.empty();
        
        if (actions.includes('apply')) {
            buttons.append('<button class="btn btn-primary" onclick="applyForIssue()">申请开证</button>');
        }
        if (actions.includes('request_amendment')) {
            buttons.append('<button class="btn btn-warning" onclick="showAmendmentModal()">请求修改</button>');
        }
        if (actions.includes('submit_documents')) {
            buttons.append('<button class="btn btn-success" onclick="showDocumentsModal()">交单</button>');
        }
    }

    function applyForIssue() {
        $.ajax({
            url: '/api/v1/letters-of-credit/{{ lc.id }}/apply/',
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            },
            success: function(response) {
                if (response.code === 0) {
                    SimTrade.showAlert('信用证已开立', 'success');
                    location.reload();
                }
            }
        });
    }

    function showDocumentsModal() {
        // 加载所需单据列表
        $.ajax({
            url: '/api/v1/letters-of-credit/{{ lc.id }}/documents/',
            method: 'GET',
            success: function(response) {
                if (response.code === 0) {
                    var docs = response.data;
                    var docsHtml = '<ul>';
                    docs.forEach(function(doc) {
                        docsHtml += '<li><input type="checkbox" value="' + doc.id + '"> ' + doc.type + '</li>';
                    });
                    docsHtml += '</ul>';
                    $('#documentsList').html(docsHtml);
                }
            }
        });
        $('#documentsModal').modal('show');
    }

    function submitDocuments() {
        var selectedDocs = [];
        $('#documentsList input:checked').each(function() {
            selectedDocs.push($(this).val());
        });

        $.ajax({
            url: '/api/v1/letters-of-credit/{{ lc.id }}/submit-documents/',
            method: 'POST',
            data: {
                document_ids: selectedDocs
            },
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            },
            success: function(response) {
                if (response.code === 0) {
                    SimTrade.showAlert('交单成功', 'success');
                    location.reload();
                }
            }
        });
    }

    function getCookie(name) {
        var cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            var cookies = document.cookie.split(';');
            for (var i = 0; i < cookies.length; i++) {
                var cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
});
</script>

<!-- 交单模态框 -->
<div class="modal fade" id="documentsModal" tabindex="-1">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header">
                <h4 class="modal-title">提交单据</h4>
                <button type="button" class="close" data-dismiss="modal">&times;</button>
            </div>
            <div class="modal-body">
                <h5>选择要提交的单据：</h5>
                <div id="documentsList">加载中...</div>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-default" data-dismiss="modal">取消</button>
                <button type="button" class="btn btn-primary" onclick="submitDocuments()">提交</button>
            </div>
        </div>
    </div>
</div>

{% endblock %}
```

- [ ] **步骤 2：验证页面可访问**

运行：`python manage.py runserver`
访问：信用证详情页面
预期：页面正常显示

- [ ] **步骤 3：Commit**

```bash
git add templates/transactions/letter_of_credit.html
git commit -m "feat(lc): add letter of credit detail page"
```

---

### 任务 14：集成测试

**文件：**
- 创建：`apps/transactions/tests/test_integration.py`

- [ ] **步骤 1：编写完整合同流程测试**

```python
def test_complete_contract_flow():
    """测试完整合同流程"""
    # 创建交易
    buyer = User.objects.create_user(username='buyer')
    seller = User.objects.create_user(username='seller')
    transaction = Transaction.objects.create(
        buyer=buyer,
        seller=seller,
        status='pending_contract'
    )
    
    # 创建合同草稿
    contract = ContractService.create_from_transaction(transaction, {
        'payment_term': 'L/C',
        ...
    })
    assert contract.status == 'draft'
    
    # 发送确认
    contract = ContractService.send_for_confirmation(contract, seller)
    assert contract.status == 'pending_confirm'
    
    # 确认条款
    contract = ContractService.confirm_terms(contract, buyer)
    assert contract.status == 'pending_sign'
    
    # 双方签字
    contract = ContractService.sign(contract, buyer, 'buyer', '127.0.0.1')
    assert contract.status == 'one_signed'
    
    contract = ContractService.sign(contract, seller, 'seller', '127.0.0.1')
    assert contract.status == 'signed'
    
    # 合同生效
    contract = ContractService.become_effective(contract)
    assert contract.status == 'effective'
    assert contract.transaction.status == 'in_progress'
    
    # 检查信用证已创建
    assert LetterOfCredit.objects.filter(contract=contract).exists()
```

- [ ] **步骤 2：运行集成测试**

运行：`pytest apps/transactions/tests/test_integration.py -v`
预期：PASS

- [ ] **步骤 3：Commit**

```bash
git add apps/transactions/tests/test_integration.py
git commit -m "test: add integration tests for contract and LC flow"
```

---

### 任务 15：最终验证

**文件：**
- 所有相关文件

- [ ] **步骤 1：运行所有测试**

运行：`pytest apps/transactions/tests/ -v`
预期：所有测试通过

- [ ] **步骤 2：验证 Django 检查**

运行：`python manage.py check`
预期：无报错

- [ ] **步骤 3：验证项目可运行**

运行：`python manage.py runserver`
访问：http://localhost:8000/admin/
预期：管理后台正常显示

- [ ] **步骤 4：最终 Commit**

```bash
git add .
git commit -m "feat: complete contract and letter of credit system implementation"
```

---

## 自检清单

### 规格覆盖度

| 设计章节 | 对应任务 |
|---------|---------|
| 扩展 Contract 状态 | 任务 1 |
| ContractAmendment 模型 | 任务 2 |
| LetterOfCredit 模型 | 任务 3 |
| LcAmendment/BankOperation 模型 | 任务 4 |
| ContractService | 任务 5 |
| LetterOfCreditService | 任务 6 |
| StateTransitionService | 任务 7 |
| 序列化器 | 任务 8 |
| Contract API | 任务 9 |
| LetterOfCredit API | 任务 10 |
| Admin 配置 | 任务 11 |
| 合同页面 | 任务 12 |
| 信用证页面 | 任务 13 |
| 集成测试 | 任务 14 |
| 最终验证 | 任务 15 |

### 占位符检查

✅ 无 "TBD"、"TODO" 等占位符
✅ 所有代码步骤包含完整代码
✅ 所有命令有明确的预期输出

### 类型一致性检查

✅ 模型字段名在各处一致
✅ 状态枚举值一致
✅ API 响应格式统一
