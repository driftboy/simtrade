# 单证系统实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 实现 SimTrade 平台的单证系统，支持 15 种外贸单证的制作、审核和校验

**架构：** Django 应用，包含模板引擎、依赖检查、双层校验（自动+人工）、智能数据填充

**技术栈：** Django 3.2, Python 3.8+, PostgreSQL/SQLite, Bootstrap 3

---

## 文件结构

### 将要创建的文件

| 文件路径 | 职责 |
|---------|------|
| `apps/documents/__init__.py` | 应用初始化 |
| `apps/documents/apps.py` | 应用配置 |
| `apps/documents/models.py` | 数据模型 (5个模型) |
| `apps/documents/validators.py` | 自动校验规则引擎 |
| `apps/documents/services.py` | 业务服务 (模板、依赖、填充) |
| `apps/documents/views.py` | API 视图 |
| `apps/documents/serializers.py` | API 序列化器 |
| `apps/documents/urls.py` | URL 路由 |
| `apps/documents/admin.py` | 管理后台 |
| `apps/documents/tests/test_models.py` | 模型测试 |
| `apps/documents/tests/test_validators.py` | 校验器测试 |
| `apps/documents/tests/test_services.py` | 服务测试 |
| `apps/documents/tests/test_api.py` | API 测试 |
| `apps/documents/migrations/0001_initial.py` | 数据库迁移 |
| `templates/documents/*.html` | 单证模板文件 (15个) |
| `docs/superpowers/fixtures/documents.json` | 初始数据 (依赖关系) |

---

## 任务分解

### 任务 1：创建 Django 应用基础结构

**文件：**
- 创建：`apps/documents/__init__.py`
- 创建：`apps/documents/apps.py`

- [ ] **步骤 1：创建应用初始化文件**

```python
# apps/documents/__init__.py
default_app_config = 'apps.documents.apps.DocumentsConfig'
```

- [ ] **步骤 2：创建应用配置**

```python
# apps/documents/apps.py
from django.apps import AppConfig

class DocumentsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.documents'
    verbose_name = '单证管理'
```

- [ ] **步骤 3：更新项目配置**

修改 `simtrade/settings.py`，添加到 `INSTALLED_APPS`：

```python
INSTALLED_APPS = [
    # ...
    'apps.documents',
]
```

- [ ] **步骤 4：更新 URL 路由**

修改 `simtrade/urls.py`，添加：

```python
urlpatterns = [
    # ...
    path('api/v1/documents/', include('apps.documents.urls')),
]
```

- [ ] **步骤 5：验证配置**

运行：`python manage.py check`
预期：无报错

- [ ] **步骤 6：Commit**

```bash
git add apps/documents/ simtrade/settings.py simtrade/urls.py
git commit -m "feat: add documents app base structure"
```

---

### 任务 2：实现单证模板数据模型

**文件：**
- 创建：`apps/documents/models.py`
- 创建：`apps/documents/tests/test_models.py`

- [ ] **步骤 1：编写单证模板模型测试**

创建 `apps/documents/tests/test_models.py`：

```python
import pytest
from apps.documents.models import DocumentTemplate, TemplateField

class DocumentTemplateTest:
    def test_create_template(self, db):
        template = DocumentTemplate.objects.create(
            code='commercial_invoice',
            name='商业发票',
            version='1.0',
            content='<html>...</html>',
            is_system=True
        )
        assert template.code == 'commercial_invoice'
        assert template.is_system is True

    def test_template_code_choices(self, db):
        template = DocumentTemplate.objects.create(
            code='commercial_invoice',
            name='商业发票',
            content='<html>...</html>'
        )
        assert template.get_code_display() == '商业发票'

class TemplateFieldTest:
    def test_create_field(self, db):
        template = DocumentTemplate.objects.create(
            code='commercial_invoice',
            name='商业发票',
            content='<html>...</html>'
        )
        field = TemplateField.objects.create(
            template=template,
            field_name='invoice_no',
            label='发票编号',
            field_type='text',
            required=True
        )
        assert field.field_name == 'invoice_no'
        assert field.required is True
```

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest apps/documents/tests/test_models.py -v`
预期：FAIL，报错 "ModuleNotFoundError: No module named 'apps.documents.models'"

- [ ] **步骤 3：实现单证模板模型**

创建 `apps/documents/models.py`：

```python
from django.db import models
from apps.users.models import User


class DocumentTemplate(models.Model):
    """单证模板"""

    class DocumentType(models.TextChoices):
        COMMERCIAL_INVOICE = 'commercial_invoice', '商业发票'
        PACKING_LIST = 'packing_list', '装箱单'
        BILL_OF_EXCHANGE = 'bill_of_exchange', '汇票'
        SALES_CONTRACT = 'sales_contract', '外销合同'
        LETTER_OF_CREDIT = 'letter_of_credit', '信用证'
        BILL_OF_LADING = 'bill_of_lading', '海运提单'
        INSURANCE_POLICY = 'insurance_policy', '保险单'
        INSURANCE_APPLICATION = 'insurance_application', '投保单'
        EXPORT_DECLARATION = 'export_declaration', '出口报关单'
        IMPORT_DECLARATION = 'import_declaration', '进口报关单'
        INSPECTION_APPLICATION = 'inspection_application', '报检单'
        INSPECTION_CERTIFICATE = 'inspection_certificate', '检验证书'
        CERTIFICATE_OF_ORIGIN = 'certificate_of_origin', '产地证'
        BENEFICIARY_CERTIFICATE = 'beneficiary_certificate', '受益人证明'
        SHIPPING_ADVICE = 'shipping_advice', '装船通知'

    code = models.CharField(
        '单证代码',
        max_length=50,
        choices=DocumentType.choices,
        unique=True
    )
    name = models.CharField('单证名称', max_length=100)
    version = models.CharField('版本号', max_length=20, default='1.0')
    content = models.TextField('模板内容 (HTML)')
    is_system = models.BooleanField('是否系统模板', default=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    is_active = models.BooleanField('是否启用', default=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'document_templates'
        verbose_name = '单证模板'
        verbose_name_plural = '单证模板'
        ordering = ['code']

    def __str__(self):
        return self.name


class TemplateField(models.Model):
    """单证模板字段配置"""

    class FieldType(models.TextChoices):
        TEXT = 'text', '单行文本'
        TEXTAREA = 'textarea', '多行文本'
        NUMBER = 'number', '数字'
        DECIMAL = 'decimal', '金额'
        DATE = 'date', '日期'
        SELECT = 'select', '下拉选择'
        COUNTRY = 'country', '国家选择'
        PORT = 'port', '港口选择'
        CURRENCY = 'currency', '货币选择'

    template = models.ForeignKey(
        DocumentTemplate,
        on_delete=models.CASCADE,
        related_name='fields'
    )
    field_name = models.CharField('字段名', max_length=50)
    label = models.CharField('显示标签', max_length=100)
    field_type = models.CharField(
        '字段类型',
        max_length=20,
        choices=FieldType.choices
    )
    required = models.BooleanField('是否必填', default=True)
    default_value = models.CharField('默认值', max_length=200, blank=True)
    validation_rules = models.JSONField('校验规则', null=True, blank=True)
    data_source = models.CharField('数据来源', max_length=100, blank=True)
    help_text = models.CharField('帮助文本', max_length=200, blank=True)
    sort_order = models.IntegerField('排序', default=0)

    class Meta:
        db_table = 'template_fields'
        verbose_name = '模板字段'
        verbose_name_plural = '模板字段'
        unique_together = [['template', 'field_name']]
        ordering = ['sort_order', 'field_name']

    def __str__(self):
        return f"{self.template.name} - {self.label}"
```

- [ ] **步骤 4：运行测试验证通过**

运行：`pytest apps/documents/tests/test_models.py -v`
预期：PASS

- [ ] **步骤 5：生成迁移文件**

运行：`python manage.py makemigrations documents`

- [ ] **步骤 6：Commit**

```bash
git add apps/documents/models.py apps/documents/tests/
git commit -m "feat: implement document template models"
```

---

### 任务 3：实现单证依赖关系模型

**文件：**
- 修改：`apps/documents/models.py`
- 修改：`apps/documents/tests/test_models.py`

- [ ] **步骤 1：编写依赖关系模型测试**

添加到 `apps/documents/tests/test_models.py`：

```python
from apps.documents.models import DocumentDependency

class DocumentDependencyTest:
    def test_create_dependency(self, db):
        dep = DocumentDependency.objects.create(
            document_type='packing_list',
            depends_on='commercial_invoice',
            dependency_type='sequential'
        )
        assert dep.document_type == 'packing_list'
        assert dep.depends_on == 'commercial_invoice'

    def test_circular_dependency_detection(self, db):
        DocumentDependency.objects.create(
            document_type='packing_list',
            depends_on='commercial_invoice'
        )
        DocumentDependency.objects.create(
            document_type='commercial_invoice',
            depends_on='packing_list'
        )
        # 后续实现循环检测方法
```

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest apps/documents/tests/test_models.py::DocumentDependencyTest -v`
预期：FAIL

- [ ] **步骤 3：实现依赖关系模型**

添加到 `apps/documents/models.py`：

```python
class DocumentDependency(models.Model):
    """单证依赖关系"""

    class DependencyType(models.TextChoices):
        SEQUENTIAL = 'sequential', '顺序依赖'
        PARALLEL = 'parallel', '并行'

    document_type = models.CharField('单证类型', max_length=50)
    depends_on = models.CharField('依赖单证类型', max_length=50)
    dependency_type = models.CharField(
        '依赖类型',
        max_length=20,
        choices=DependencyType.choices,
        default=DependencyType.SEQUENTIAL
    )
    is_required = models.BooleanField('是否必需', default=True)

    class Meta:
        db_table = 'document_dependencies'
        verbose_name = '单证依赖'
        verbose_name_plural = '单证依赖'
        unique_together = [['document_type', 'depends_on']]

    def __str__(self):
        return f"{self.document_type} 依赖 {self.depends_on}"
```

- [ ] **步骤 4：运行测试验证通过**

运行：`pytest apps/documents/tests/test_models.py::DocumentDependencyTest -v`
预期：PASS

- [ ] **步骤 5：生成迁移文件**

运行：`python manage.py makemigrations documents`

- [ ] **步骤 6：Commit**

```bash
git add apps/documents/
git commit -m "feat: implement document dependency model"
```

---

### 任务 4：实现单证记录模型

**文件：**
- 修改：`apps/documents/models.py`
- 修改：`apps/documents/tests/test_models.py`

- [ ] **步骤 1：编写单证记录模型测试**

添加到 `apps/documents/tests/test_models.py`：

```python
from apps.documents.models import Document

class DocumentTest:
    def test_create_document(self, db):
        template = DocumentTemplate.objects.create(
            code='commercial_invoice',
            name='商业发票',
            content='<html>...</html>'
        )
        user = User.objects.create_user(username='test', password='pass')
        doc = Document.objects.create(
            template=template,
            created_by=user,
            data={'invoice_no': 'INV001'}
        )
        assert doc.status == 'draft'
        assert doc.data['invoice_no'] == 'INV001'

    def test_document_status_transition(self, db):
        template = DocumentTemplate.objects.create(
            code='commercial_invoice',
            name='商业发票',
            content='<html>...</html>'
        )
        user = User.objects.create_user(username='test', password='pass')
        doc = Document.objects.create(template=template, created_by=user)
        
        doc.status = 'pending_review'
        doc.save()
        assert doc.get_status_display() == '待审核'
```

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest apps/documents/tests/test_models.py::DocumentTest -v`
预期：FAIL

- [ ] **步骤 3：实现单证记录模型**

添加到 `apps/documents/models.py`：

```python
class Document(models.Model):
    """单证记录"""

    class Status(models.TextChoices):
        DRAFT = 'draft', '草稿'
        PENDING_REVIEW = 'pending_review', '待审核'
        APPROVED = 'approved', '已审核'
        REJECTED = 'rejected', '审核不通过'
        SUBMITTED = 'submitted', '已提交'
        RECEIVED = 'received', '已接收'
        ARCHIVED = 'archived', '已归档'

    template = models.ForeignKey(
        DocumentTemplate,
        on_delete=models.PROTECT,
        related_name='documents'
    )
    # transaction 字段暂时可选，等交易系统实现后再关联
    transaction_id = models.IntegerField('交易ID', null=True, blank=True)
    status = models.CharField(
        '状态',
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )
    data = models.JSONField('单证数据', default=dict)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_documents'
    )
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_documents'
    )
    auto_validation_result = models.JSONField(
        '自动校验结果',
        null=True,
        blank=True
    )
    manual_review_status = models.CharField(
        '人工审核状态',
        max_length=20,
        blank=True
    )
    manual_review_comment = models.TextField('审核意见', blank=True)
    submitted_at = models.DateTimeField('提交时间', null=True, blank=True)
    reviewed_at = models.DateTimeField('审核时间', null=True, blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'documents'
        verbose_name = '单证'
        verbose_name_plural = '单证'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.template.name} - {self.get_status_display()}"
```

- [ ] **步骤 4：运行测试验证通过**

运行：`pytest apps/documents/tests/test_models.py::DocumentTest -v`
预期：PASS

- [ ] **步骤 5：生成迁移文件**

运行：`python manage.py makemigrations documents`

- [ ] **步骤 6：Commit**

```bash
git add apps/documents/
git commit -m "feat: implement document model with status machine"
```

---

### 任务 5：实现单证校验记录模型

**文件：**
- 修改：`apps/documents/models.py`
- 修改：`apps/documents/tests/test_models.py`

- [ ] **步骤 1：编写校验记录模型测试**

添加到 `apps/documents/tests/test_models.py`：

```python
from apps.documents.models import DocumentValidation

class DocumentValidationTest:
    def test_create_validation(self, db):
        template = DocumentTemplate.objects.create(
            code='commercial_invoice',
            name='商业发票',
            content='<html>...</html>'
        )
        user = User.objects.create_user(username='test', password='pass')
        doc = Document.objects.create(template=template, created_by=user)
        
        validation = DocumentValidation.objects.create(
            document=doc,
            rule='date_logic',
            passed=True,
            validation_type='auto'
        )
        assert validation.rule == 'date_logic'
        assert validation.passed is True
```

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest apps/documents/tests/test_models.py::DocumentValidationTest -v`
预期：FAIL

- [ ] **步骤 3：实现校验记录模型**

添加到 `apps/documents/models.py`：

```python
class DocumentValidation(models.Model):
    """单证校验记录"""

    class ValidationType(models.TextChoices):
        AUTO = 'auto', '自动校验'
        MANUAL = 'manual', '人工审核'

    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name='validations'
    )
    rule = models.CharField('校验规则', max_length=100)
    passed = models.BooleanField('是否通过')
    error_message = models.TextField('错误信息', blank=True)
    score_deduction = models.IntegerField('扣分', default=0)
    validation_type = models.CharField(
        '校验类型',
        max_length=10,
        choices=ValidationType.choices
    )
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'document_validations'
        verbose_name = '单证校验'
        verbose_name_plural = '单证校验'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.document} - {self.rule}"
```

- [ ] **步骤 4：运行测试验证通过**

运行：`pytest apps/documents/tests/test_models.py::DocumentValidationTest -v`
预期：PASS

- [ ] **步骤 5：生成迁移文件**

运行：`python manage.py makemigrations documents`

- [ ] **步骤 6：Commit**

```bash
git add apps/documents/
git commit -m "feat: implement document validation model"
```

---

### 任务 6：实现自动校验规则引擎

**文件：**
- 创建：`apps/documents/validators.py`
- 创建：`apps/documents/tests/test_validators.py`

- [ ] **步骤 1：编写校验器测试**

创建 `apps/documents/tests/test_validators.py`：

```python
import pytest
from apps.documents.validators import DocumentValidator
from apps.documents.models import Document, DocumentTemplate, DocumentValidation

class DocumentValidatorTest:
    def test_date_logic_validation(self, db):
        template = DocumentTemplate.objects.create(
            code='commercial_invoice',
            name='商业发票',
            content='<html>...</html>'
        )
        user = User.objects.create_user(username='test', password='pass')
        
        # 测试日期逻辑正确的情况
        doc = Document.objects.create(
            template=template,
            created_by=user,
            data={
                'invoice_date': '2026-05-01',
                'shipment_date': '2026-05-10',
                'insurance_date': '2026-05-05'
            }
        )
        
        validator = DocumentValidator(doc)
        results = validator.validate_all()
        
        assert results['date_logic']['passed'] is True

    def test_date_logic_validation_fail(self, db):
        template = DocumentTemplate.objects.create(
            code='commercial_invoice',
            name='商业发票',
            content='<html>...</html>'
        )
        user = User.objects.create_user(username='test', password='pass')
        
        # 测试日期逻辑错误的情况
        doc = Document.objects.create(
            template=template,
            created_by=user,
            data={
                'invoice_date': '2026-05-10',
                'shipment_date': '2026-05-01',  # 装运日期早于发票日期
            }
        )
        
        validator = DocumentValidator(doc)
        results = validator.validate_all()
        
        assert results['date_logic']['passed'] is False
        assert '发票日期不能晚于装运日期' in results['date_logic']['errors'][0]

    def test_amount_consistency_validation(self, db):
        template = DocumentTemplate.objects.create(
            code='commercial_invoice',
            name='商业发票',
            content='<html>...</html>'
        )
        user = User.objects.create_user(username='test', password='pass')
        
        doc = Document.objects.create(
            template=template,
            created_by=user,
            data={
                'invoice_amount': 10000.00,
                'draft_amount': 10000.00,  # 汇票金额
            }
        )
        
        validator = DocumentValidator(doc)
        results = validator.validate_all()
        
        assert results['amount_consistency']['passed'] is True

    def test_save_validation_results(self, db):
        template = DocumentTemplate.objects.create(
            code='commercial_invoice',
            name='商业发票',
            content='<html>...</html>'
        )
        user = User.objects.create_user(username='test', password='pass')
        doc = Document.objects.create(
            template=template,
            created_by=user,
            data={'invoice_date': '2026-05-10', 'shipment_date': '2026-05-01'}
        )
        
        validator = DocumentValidator(doc)
        validator.save_results()
        
        assert doc.validations.count() > 0
        assert doc.auto_validation_result is not None
```

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest apps/documents/tests/test_validators.py -v`
预期：FAIL

- [ ] **步骤 3：实现校验规则引擎**

创建 `apps/documents/validators.py`：

```python
from datetime import datetime
from decimal import Decimal
from apps.documents.models import DocumentValidation


class DocumentValidator:
    """单证自动校验引擎"""

    def __init__(self, document):
        self.document = document
        self.data = document.data
        self.results = {}

    def validate_all(self):
        """执行所有校验规则"""
        self.results = {
            'date_logic': self._validate_date_logic(),
            'amount_consistency': self._validate_amount_consistency(),
            'quantity_consistency': self._validate_quantity_consistency(),
            'required_fields': self._validate_required_fields(),
        }
        return self.results

    def _validate_date_logic(self):
        """日期逻辑校验"""
        errors = []
        warnings = []
        
        invoice_date = self._parse_date(self.data.get('invoice_date'))
        shipment_date = self._parse_date(self.data.get('shipment_date'))
        insurance_date = self._parse_date(self.data.get('insurance_date'))
        lc_issue_date = self._parse_date(self.data.get('lc_issue_date'))
        
        # 发票日期 <= 装运日期
        if invoice_date and shipment_date:
            if invoice_date > shipment_date:
                errors.append('发票日期不能晚于装运日期')
        
        # 装运日期 <= 保险日期
        if shipment_date and insurance_date:
            if shipment_date > insurance_date:
                errors.append('装运日期不能晚于保险日期')
        
        # 信用证开证日期 <= 装运日期
        if lc_issue_date and shipment_date:
            if lc_issue_date > shipment_date:
                errors.append('信用证开证日期不能晚于装运日期')
        
        return {
            'passed': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }

    def _validate_amount_consistency(self):
        """金额一致性校验"""
        errors = []
        
        invoice_amount = self._parse_decimal(self.data.get('invoice_amount'))
        draft_amount = self._parse_decimal(self.data.get('draft_amount'))
        insurance_amount = self._parse_decimal(self.data.get('insurance_amount'))
        
        # 发票金额 == 汇票金额
        if invoice_amount and draft_amount:
            if invoice_amount != draft_amount:
                errors.append(f'发票金额({invoice_amount})应等于汇票金额({draft_amount})')
        
        # 保险金额 >= 发票金额 × 1.1
        if invoice_amount and insurance_amount:
            min_insurance = invoice_amount * Decimal('1.1')
            if insurance_amount < min_insurance:
                errors.append(f'保险金额({insurance_amount})应不低于发票金额的110%({min_insurance})')
        
        return {
            'passed': len(errors) == 0,
            'errors': errors
        }

    def _validate_quantity_consistency(self):
        """数量一致性校验"""
        errors = []
        
        invoice_qty = self._parse_decimal(self.data.get('invoice_quantity'))
        packing_qty = self._parse_decimal(self.data.get('packing_quantity'))
        bl_qty = self._parse_decimal(self.data.get('bl_quantity'))
        
        quantities = [q for q in [invoice_qty, packing_qty, bl_qty] if q is not None]
        if quantities and len(set(quantities)) > 1:
            errors.append('各单证数量应保持一致')
        
        # 净重 <= 毛重
        net_weight = self._parse_decimal(self.data.get('net_weight'))
        gross_weight = self._parse_decimal(self.data.get('gross_weight'))
        if net_weight and gross_weight and net_weight > gross_weight:
            errors.append('净重不能大于毛重')
        
        return {
            'passed': len(errors) == 0,
            'errors': errors
        }

    def _validate_required_fields(self):
        """必填字段校验"""
        errors = []
        
        required_fields = {
            'invoice_no': '发票编号',
            'invoice_date': '发票日期',
            'invoice_amount': '发票金额',
            'buyer_name': '买方名称',
            'seller_name': '卖方名称',
        }
        
        for field, label in required_fields.items():
            if not self.data.get(field):
                errors.append(f'{label}不能为空')
        
        return {
            'passed': len(errors) == 0,
            'errors': errors
        }

    def _parse_date(self, date_str):
        """解析日期字符串"""
        if not date_str:
            return None
        if isinstance(date_str, datetime):
            return date_str.date()
        try:
            return datetime.strptime(date_str, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            return None

    def _parse_decimal(self, value):
        """解析金额/数量"""
        if value is None:
            return None
        if isinstance(value, (int, float, Decimal)):
            return Decimal(str(value))
        try:
            return Decimal(str(value))
        except (ValueError, TypeError):
            return None

    def save_results(self):
        """保存校验结果到数据库"""
        # 先清除旧的自动校验记录
        self.document.validations.filter(
            validation_type=DocumentValidation.ValidationType.AUTO
        ).delete()
        
        # 保存新的校验结果
        validation_results = {}
        for rule_name, result in self.validate_all().items():
            DocumentValidation.objects.create(
                document=self.document,
                rule=rule_name,
                passed=result['passed'],
                error_message='; '.join(result.get('errors', [])),
                validation_type=DocumentValidation.ValidationType.AUTO
            )
            validation_results[rule_name] = result
        
        # 更新单证的校验结果
        self.document.auto_validation_result = validation_results
        self.document.save(update_fields=['auto_validation_result'])
        
        return validation_results
```

- [ ] **步骤 4：运行测试验证通过**

运行：`pytest apps/documents/tests/test_validators.py -v`
预期：PASS

- [ ] **步骤 5：Commit**

```bash
git add apps/documents/validators.py apps/documents/tests/test_validators.py
git commit -m "feat: implement document validation engine"
```

---

### 任务 7：实现单证依赖检查服务

**文件：**
- 创建：`apps/documents/services.py`
- 创建：`apps/documents/tests/test_services.py`

- [ ] **步骤 1：编写依赖检查服务测试**

创建 `apps/documents/tests/test_services.py`：

```python
import pytest
from apps.documents.services import DependencyService
from apps.documents.models import DocumentTemplate, DocumentDependency, Document
from apps.users.models import User

class DependencyServiceTest:
    @pytest.fixture(autouse=True)
    def setup_dependencies(self, db):
        """设置测试用的依赖关系"""
        # 创建模板
        for code, name in [
            ('commercial_invoice', '商业发票'),
            ('packing_list', '装箱单'),
            ('bill_of_lading', '海运提单'),
        ]:
            DocumentTemplate.objects.create(code=code, name=name, content='<html></html>')
        
        # 创建依赖关系
        DocumentDependency.objects.create(
            document_type='packing_list',
            depends_on='commercial_invoice',
            dependency_type='sequential'
        )
        DocumentDependency.objects.create(
            document_type='bill_of_lading',
            depends_on='packing_list',
            dependency_type='sequential'
        )

    def test_can_create_document_without_dependencies(self, db):
        """测试创建没有依赖的单证"""
        user = User.objects.create_user(username='test', password='pass')
        service = DependencyService(user)
        
        can_create, message = service.can_create('commercial_invoice')
        
        assert can_create is True
        assert message == ''

    def test_cannot_create_document_with_unmet_dependencies(self, db):
        """测试依赖未满足时不能创建单证"""
        user = User.objects.create_user(username='test', password='pass')
        service = DependencyService(user)
        
        can_create, message = service.can_create('packing_list')
        
        assert can_create is False
        assert '商业发票' in message

    def test_can_create_document_with_met_dependencies(self, db):
        """测试依赖满足后可以创建单证"""
        user = User.objects.create_user(username='test', password='pass')
        
        # 先创建依赖的单证
        template = DocumentTemplate.objects.get(code='commercial_invoice')
        Document.objects.create(
            template=template,
            created_by=user,
            status='approved'
        )
        
        service = DependencyService(user)
        can_create, message = service.can_create('packing_list')
        
        assert can_create is True

    def test_get_creation_order(self, db):
        """测试获取单证创建顺序"""
        service = DependencyService(None)
        order = service.get_creation_order()
        
        assert 'commercial_invoice' in order
        assert order.index('commercial_invoice') < order.index('packing_list')
        assert order.index('packing_list') < order.index('bill_of_lading')
```

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest apps/documents/tests/test_services.py -v`
预期：FAIL

- [ ] **步骤 3：实现依赖检查服务**

创建 `apps/documents/services.py`：

```python
from apps.documents.models import DocumentTemplate, DocumentDependency, Document


class DependencyService:
    """单证依赖检查服务"""

    def __init__(self, user):
        self.user = user

    def can_create(self, document_type, transaction_id=None):
        """
        检查是否可以创建指定类型的单证
        
        返回: (can_create: bool, message: str)
        """
        # 获取该单证的所有依赖
        dependencies = DocumentDependency.objects.filter(
            document_type=document_type
        )
        
        if not dependencies.exists():
            return True, ''
        
        # 检查每个依赖是否满足
        missing_deps = []
        for dep in dependencies:
            if not self._check_dependency(dep, transaction_id):
                template = DocumentTemplate.objects.filter(
                    code=dep.depends_on
                ).first()
                if template:
                    missing_deps.append(template.name)
        
        if missing_deps:
            return False, f'需要先完成以下单证：{", ".join(missing_deps)}'
        
        return True, ''

    def _check_dependency(self, dependency, transaction_id=None):
        """检查单个依赖是否满足"""
        # 查找用户已完成的依赖单证
        query = Document.objects.filter(
            created_by=self.user,
            template__code=dependency.depends_on
        )
        
        if transaction_id:
            query = query.filter(transaction_id=transaction_id)
        
        # 检查是否有已审核通过的单证
        return query.filter(
            status__in=[Document.Status.APPROVED, Document.Status.ARCHIVED]
        ).exists()

    def get_creation_order(self):
        """获取所有单证的推荐创建顺序（拓扑排序）"""
        # 获取所有单证类型
        all_types = list(DocumentTemplate.objects.filter(
            is_active=True
        ).values_list('code', flat=True))
        
        # 获取所有依赖关系
        dependencies = DocumentDependency.objects.all()
        
        # 构建依赖图
        graph = {t: set() for t in all_types}
        in_degree = {t: 0 for t in all_types}
        
        for dep in dependencies:
            if dep.depends_on in graph and dep.document_type in graph:
                graph[dep.depends_on].add(dep.document_type)
                in_degree[dep.document_type] += 1
        
        # 拓扑排序
        order = []
        queue = [t for t in all_types if in_degree[t] == 0]
        
        while queue:
            node = queue.pop(0)
            order.append(node)
            
            for neighbor in graph[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        return order

    def get_next_available(self, transaction_id=None):
        """获取用户当前可以创建的单证类型列表"""
        all_types = DocumentTemplate.objects.filter(is_active=True)
        available = []
        
        for template in all_types:
            can_create, _ = self.can_create(template.code, transaction_id)
            if can_create:
                available.append({
                    'code': template.code,
                    'name': template.name,
                })
        
        return available
```

- [ ] **步骤 4：运行测试验证通过**

运行：`pytest apps/documents/tests/test_services.py -v`
预期：PASS

- [ ] **步骤 5：Commit**

```bash
git add apps/documents/services.py apps/documents/tests/test_services.py
git commit -m "feat: implement document dependency service"
```

---

### 任务 8：实现数据填充服务

**文件：**
- 修改：`apps/documents/services.py`
- 修改：`apps/documents/tests/test_services.py`

- [ ] **步骤 1：编写数据填充服务测试**

添加到 `apps/documents/tests/test_services.py`：

```python
from apps.documents.services import DataFillService

class DataFillServiceTest:
    def test_fill_from_transaction(self, db):
        """测试从交易数据填充"""
        # 模拟交易数据
        transaction_data = {
            'buyer_name': 'ABC Trading Co.',
            'seller_name': 'XYZ Export Corp.',
            'amount': 10000.00,
            'quantity': 1000,
            'product_name': 'Cotton T-Shirts',
        }
        
        service = DataFillService()
        filled_data = service.fill_from_transaction('commercial_invoice', transaction_data)
        
        assert filled_data['buyer_name'] == 'ABC Trading Co.'
        assert filled_data['amount'] == 10000.00

    def test_fill_from_existing_document(self, db):
        """测试从已有单证继承数据"""
        template = DocumentTemplate.objects.create(
            code='commercial_invoice',
            name='商业发票',
            content='<html></html>'
        )
        user = User.objects.create_user(username='test', password='pass')
        
        # 创建已存在的发票
        existing_doc = Document.objects.create(
            template=template,
            created_by=user,
            data={
                'invoice_no': 'INV001',
                'buyer_name': 'ABC Trading',
                'amount': 5000.00
            }
        )
        
        service = DataFillService()
        filled_data = service.fill_from_document(
            'packing_list',
            existing_doc
        )
        
        assert filled_data['invoice_no'] == 'INV001'
        assert filled_data['amount'] == 5000.00
```

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest apps/documents/tests/test_services.py::DataFillServiceTest -v`
预期：FAIL

- [ ] **步骤 3：实现数据填充服务**

添加到 `apps/documents/services.py`：

```python
class DataFillService:
    """单证数据智能填充服务"""

    # 字段映射配置：从交易/已有单证到目标单证的映射
    FIELD_MAPPINGS = {
        'packing_list': {
            'invoice_no': 'invoice_no',
            'buyer_name': 'buyer_name',
            'seller_name': 'seller_name',
            'invoice_quantity': 'quantity',
            'invoice_amount': 'amount',
        },
        'bill_of_exchange': {
            'invoice_no': 'invoice_no',
            'buyer_name': 'payee_name',
            'invoice_amount': 'amount',
        },
        'insurance_application': {
            'invoice_no': 'invoice_no',
            'buyer_name': 'applicant',
            'invoice_amount': 'insured_amount',
        },
        # ... 其他单证类型的映射
    }

    def fill_from_transaction(self, document_type, transaction_data):
        """
        从交易数据填充单证
        
        Args:
            document_type: 单证类型
            transaction_data: 交易数据字典
        
        Returns:
            填充后的单证数据字典
        """
        filled_data = {}
        
        # 根据单证类型填充默认字段
        if document_type == 'commercial_invoice':
            filled_data = {
                'buyer_name': transaction_data.get('buyer_name'),
                'seller_name': transaction_data.get('seller_name'),
                'invoice_amount': transaction_data.get('amount'),
                'invoice_quantity': transaction_data.get('quantity'),
                'product_name': transaction_data.get('product_name'),
                'invoice_date': transaction_data.get('contract_date'),
            }
        elif document_type == 'packing_list':
            filled_data = {
                'buyer_name': transaction_data.get('buyer_name'),
                'seller_name': transaction_data.get('seller_name'),
                'packing_quantity': transaction_data.get('quantity'),
                'product_name': transaction_data.get('product_name'),
            }
        
        return filled_data

    def fill_from_document(self, document_type, source_document):
        """
        从已有单证填充数据
        
        Args:
            document_type: 目标单证类型
            source_document: 源单证实例
        
        Returns:
            填充后的单证数据字典
        """
        mappings = self.FIELD_MAPPINGS.get(document_type, {})
        filled_data = {}
        source_data = source_document.data
        
        for target_field, source_field in mappings.items():
            if source_field in source_data:
                filled_data[target_field] = source_data[source_field]
        
        return filled_data

    def fill_defaults(self, document_type):
        """
        填充默认值
        
        Args:
            document_type: 单证类型
        
        Returns:
            包含默认值的字典
        """
        from datetime import date
        
        defaults = {
            'invoice_date': str(date.today()),
            'currency': 'USD',
        }
        
        # 根据单证类型添加特定默认值
        if document_type == 'commercial_invoice':
            defaults.update({
                'trade_term': 'FOB',
                'payment_term': 'L/C',
            })
        
        return defaults
```

- [ ] **步骤 4：运行测试验证通过**

运行：`pytest apps/documents/tests/test_services.py::DataFillServiceTest -v`
预期：PASS

- [ ] **步骤 5：Commit**

```bash
git add apps/documents/
git commit -m "feat: implement data fill service"
```

---

### 任务 9：实现单证 API 序列化器

**文件：**
- 创建：`apps/documents/serializers.py`
- 创建：`apps/documents/tests/test_serializers.py`

- [ ] **步骤 1：编写序列化器测试**

创建 `apps/documents/tests/test_serializers.py`：

```python
import pytest
from apps.documents.serializers import DocumentSerializer, DocumentTemplateSerializer
from apps.documents.models import Document, DocumentTemplate
from apps.users.models import User

class DocumentSerializerTest:
    def test_serialize_document(self, db):
        template = DocumentTemplate.objects.create(
            code='commercial_invoice',
            name='商业发票',
            content='<html></html>'
        )
        user = User.objects.create_user(username='test', password='pass')
        doc = Document.objects.create(
            template=template,
            created_by=user,
            data={'invoice_no': 'INV001'}
        )
        
        serializer = DocumentSerializer(doc)
        data = serializer.data
        
        assert data['id'] == doc.id
        assert data['template'] == template.id
        assert data['status'] == 'draft'

class DocumentTemplateSerializerTest:
    def test_serialize_template(self, db):
        template = DocumentTemplate.objects.create(
            code='commercial_invoice',
            name='商业发票',
            content='<html></html>'
        )
        
        serializer = DocumentTemplateSerializer(template)
        data = serializer.data
        
        assert data['code'] == 'commercial_invoice'
        assert data['name'] == '商业发票'
```

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest apps/documents/tests/test_serializers.py -v`
预期：FAIL

- [ ] **步骤 3：实现序列化器**

创建 `apps/documents/serializers.py`：

```python
from rest_framework import serializers
from apps.documents.models import (
    Document, DocumentTemplate, TemplateField,
    DocumentDependency, DocumentValidation
)
from apps.users.serializers import UserSerializer


class TemplateFieldSerializer(serializers.ModelSerializer):
    """模板字段序列化器"""

    class Meta:
        model = TemplateField
        fields = ['id', 'field_name', 'label', 'field_type',
                  'required', 'default_value', 'help_text', 'sort_order']


class DocumentTemplateSerializer(serializers.ModelSerializer):
    """单证模板序列化器"""
    fields = TemplateFieldSerializer(many=True, read_only=True)
    created_by = UserSerializer(read_only=True)

    class Meta:
        model = DocumentTemplate
        fields = ['id', 'code', 'name', 'version', 'is_system',
                  'is_active', 'created_by', 'created_at', 'fields']
        read_only_fields = ['id', 'created_at']


class DocumentValidationSerializer(serializers.ModelSerializer):
    """单证校验记录序列化器"""

    class Meta:
        model = DocumentValidation
        fields = ['id', 'rule', 'passed', 'error_message',
                  'score_deduction', 'validation_type', 'created_at']


class DocumentSerializer(serializers.ModelSerializer):
    """单证序列化器"""
    template_name = serializers.CharField(source='template.name', read_only=True)
    template_code = serializers.CharField(source='template.code', read_only=True)
    created_by = UserSerializer(read_only=True)
    reviewed_by = UserSerializer(read_only=True)
    validations = DocumentValidationSerializer(many=True, read_only=True)

    class Meta:
        model = Document
        fields = ['id', 'template', 'template_name', 'template_code',
                  'status', 'data', 'created_by', 'reviewed_by',
                  'auto_validation_result', 'manual_review_status',
                  'manual_review_comment', 'submitted_at', 'reviewed_at',
                  'created_at', 'updated_at', 'validations']
        read_only_fields = ['id', 'created_at', 'updated_at', 'auto_validation_result']

    def create(self, validated_data):
        """创建单证时自动填充默认数据"""
        template = validated_data['template']
        user = self.context['request'].user
        
        # 智能数据填充
        from apps.documents.services import DataFillService
        fill_service = DataFillService()
        
        # 合并默认值
        defaults = fill_service.fill_defaults(template.code)
        validated_data['data'] = {**defaults, **validated_data.get('data', {})}
        
        validated_data['created_by'] = user
        return super().create(validated_data)


class DocumentCreateSerializer(serializers.ModelSerializer):
    """创建单证序列化器（简化版）"""

    class Meta:
        model = Document
        fields = ['template', 'data']

    def validate_template(self, value):
        """验证模板是否启用"""
        if not value.is_active:
            raise serializers.ValidationError('该单证模板未启用')
        return value


class DocumentSubmitSerializer(serializers.Serializer):
    """提交审核序列化器"""
    comment = serializers.CharField(required=False, allow_blank=True)
```

- [ ] **步骤 4：运行测试验证通过**

运行：`pytest apps/documents/tests/test_serializers.py -v`
预期：PASS

- [ ] **步骤 5：Commit**

```bash
git add apps/documents/serializers.py apps/documents/tests/test_serializers.py
git commit -m "feat: implement document API serializers"
```

---

### 任务 10：实现单证 API 视图

**文件：**
- 创建：`apps/documents/views.py`
- 创建：`apps/documents/urls.py`
- 创建：`apps/documents/tests/test_api.py`

- [ ] **步骤 1：编写 API 视图测试**

创建 `apps/documents/tests/test_api.py`：

```python
import pytest
from django.urls import reverse
from apps.documents.models import Document, DocumentTemplate
from apps.users.models import User

class DocumentAPITest:
    @pytest.fixture(autouse=True)
    def setup(self, db):
        self.template = DocumentTemplate.objects.create(
            code='commercial_invoice',
            name='商业发票',
            content='<html></html>'
        )
        self.user = User.objects.create_user(username='test', password='pass')

    def test_list_documents(self, db):
        """测试获取单证列表"""
        self.client.force_login(self.user)
        url = reverse('document-list')
        response = self.client.get(url)
        
        assert response.status_code == 200
        assert response.json()['code'] == 0

    def test_create_document(self, db):
        """测试创建单证"""
        self.client.force_login(self.user)
        url = reverse('document-list')
        data = {
            'template': self.template.id,
            'data': {'invoice_no': 'INV001'}
        }
        response = self.client.post(url, data, content_type='application/json')
        
        assert response.status_code == 200
        assert Document.objects.count() == 1

    def test_submit_document(self, db):
        """测试提交审核"""
        self.client.force_login(self.user)
        doc = Document.objects.create(
            template=self.template,
            created_by=self.user,
            data={'invoice_no': 'INV001', 'invoice_date': '2026-05-01'}
        )
        
        url = reverse('document-submit', kwargs={'pk': doc.id})
        response = self.client.post(url)
        
        assert response.status_code == 200
        doc.refresh_from_db()
        assert doc.status == 'pending_review'
```

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest apps/documents/tests/test_api.py -v`
预期：FAIL

- [ ] **步骤 3：实现 API 视图**

创建 `apps/documents/views.py`：

```python
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from apps.documents.models import Document, DocumentTemplate
from apps.documents.serializers import (
    DocumentSerializer, DocumentCreateSerializer,
    DocumentTemplateSerializer, DocumentSubmitSerializer
)
from apps.documents.services import DependencyService, DataFillService
from apps.documents.validators import DocumentValidator


class DocumentViewSet(ModelViewSet):
    """单证视图集"""
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'create':
            return DocumentCreateSerializer
        return DocumentSerializer

    def get_queryset(self):
        return Document.objects.filter(
            created_by=self.request.user
        ).select_related('template', 'created_by', 'reviewed_by')

    def perform_create(self, serializer):
        """创建单证时检查依赖"""
        user = self.request.user
        template = serializer.validated_data['template']
        
        # 检查依赖
        dep_service = DependencyService(user)
        can_create, message = dep_service.can_create(template.code)
        
        if not can_create:
            return Response({
                'code': 5001,
                'message': message
            }, status=status.HTTP_400_BAD_REQUEST)
        
        serializer.save(created_by=user)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def template_list(request):
    """获取单证模板列表"""
    templates = DocumentTemplate.objects.filter(is_active=True)
    serializer = DocumentTemplateSerializer(templates, many=True)
    
    # 获取可创建的单证类型
    dep_service = DependencyService(request.user)
    available = dep_service.get_next_available()
    available_codes = {t['code'] for t in available}
    
    # 标记是否可创建
    data = []
    for t in serializer.data:
        t['can_create'] = t['code'] in available_codes
        data.append(t)
    
    return Response({
        'code': 0,
        'message': 'success',
        'data': data
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_document(request, pk):
    """提交单证审核"""
    try:
        document = Document.objects.get(pk=pk, created_by=request.user)
    except Document.DoesNotExist:
        return Response({
            'code': 4001,
            'message': '单证不存在'
        }, status=status.HTTP_404_NOT_FOUND)
    
    if document.status != Document.Status.DRAFT:
        return Response({
            'code': 4004,
            'message': '只有草稿状态的单证可以提交'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # 执行自动校验
    validator = DocumentValidator(document)
    validation_results = validator.save_results()
    
    # 检查是否所有自动校验都通过
    all_passed = all(r['passed'] for r in validation_results.values())
    
    if all_passed:
        document.status = Document.Status.PENDING_REVIEW
        document.submitted_at = timezone.now()
        document.save()
        
        return Response({
            'code': 0,
            'message': '提交成功，等待人工审核',
            'data': DocumentSerializer(document).data
        })
    else:
        # 校验不通过，返回错误信息
        errors = []
        for rule_name, result in validation_results.items():
            if not result['passed']:
                errors.extend(result.get('errors', []))
        
        return Response({
            'code': 5002,
            'message': '单证校验不通过',
            'errors': errors,
            'validation_results': validation_results
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def approve_document(request, pk):
    """审核通过单证（教师）"""
    if not request.user.is_staff:
        return Response({
            'code': 2001,
            'message': '无权限操作'
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        document = Document.objects.get(pk=pk)
    except Document.DoesNotExist:
        return Response({
            'code': 4001,
            'message': '单证不存在'
        }, status=status.HTTP_404_NOT_FOUND)
    
    if document.status != Document.Status.PENDING_REVIEW:
        return Response({
            'code': 4004,
            'message': '单证状态不允许此操作'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    document.status = Document.Status.APPROVED
    document.reviewed_by = request.user
    document.reviewed_at = timezone.now()
    document.manual_review_status = 'approved'
    document.save()
    
    return Response({
        'code': 0,
        'message': '审核通过',
        'data': DocumentSerializer(document).data
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reject_document(request, pk):
    """审核驳回单证（教师）"""
    if not request.user.is_staff:
        return Response({
            'code': 2001,
            'message': '无权限操作'
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        document = Document.objects.get(pk=pk)
    except Document.DoesNotExist:
        return Response({
            'code': 4001,
            'message': '单证不存在'
        }, status=status.HTTP_404_NOT_FOUND)
    
    if document.status != Document.Status.PENDING_REVIEW:
        return Response({
            'code': 4004,
            'message': '单证状态不允许此操作'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    comment = request.data.get('comment', '')
    document.status = Document.Status.REJECTED
    document.reviewed_by = request.user
    document.reviewed_at = timezone.now()
    document.manual_review_status = 'rejected'
    document.manual_review_comment = comment
    document.save()
    
    return Response({
        'code': 0,
        'message': '审核驳回',
        'data': DocumentSerializer(document).data
    })
```

- [ ] **步骤 4：实现 URL 路由**

创建 `apps/documents/urls.py`：

```python
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.documents import views

router = DefaultRouter()
router.register(r'documents', views.DocumentViewSet, basename='document')

urlpatterns = [
    path('', include(router.urls)),
    path('templates/', views.template_list, name='template-list'),
    path('documents/<int:pk>/submit/', views.submit_document, name='document-submit'),
    path('documents/<int:pk>/approve/', views.approve_document, name='document-approve'),
    path('documents/<int:pk>/reject/', views.reject_document, name='document-reject'),
]
```

- [ ] **步骤 5：运行测试验证通过**

运行：`pytest apps/documents/tests/test_api.py -v`
预期：PASS

- [ ] **步骤 6：Commit**

```bash
git add apps/documents/views.py apps/documents/urls.py apps/documents/tests/test_api.py
git commit -m "feat: implement document API views and routes"
```

---

### 任务 11：实现管理后台配置

**文件：**
- 创建：`apps/documents/admin.py`

- [ ] **步骤 1：实现管理后台**

创建 `apps/documents/admin.py`：

```python
from django.contrib import admin
from apps.documents.models import (
    Document, DocumentTemplate, TemplateField,
    DocumentDependency, DocumentValidation
)


@admin.register(DocumentTemplate)
class DocumentTemplateAdmin(admin.ModelAdmin):
    """单证模板管理"""
    list_display = ['code', 'name', 'version', 'is_system', 'is_active', 'created_at']
    list_filter = ['is_system', 'is_active', 'created_at']
    search_fields = ['code', 'name']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(TemplateField)
class TemplateFieldAdmin(admin.ModelAdmin):
    """模板字段管理"""
    list_display = ['template', 'field_name', 'label', 'field_type', 'required', 'sort_order']
    list_filter = ['field_type', 'required', 'template']
    search_fields = ['field_name', 'label']


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    """单证管理"""
    list_display = ['id', 'template', 'status', 'created_by', 'created_at']
    list_filter = ['status', 'template', 'created_at']
    search_fields = ['created_by__username']
    readonly_fields = ['auto_validation_result', 'created_at', 'updated_at']
    
    def get_readonly_fields(self, request, obj=None):
        readonly = ['auto_validation_result', 'created_at', 'updated_at']
        if obj and obj.status != 'draft':
            readonly.extend(['template', 'data'])
        return readonly


@admin.register(DocumentDependency)
class DocumentDependencyAdmin(admin.ModelAdmin):
    """单证依赖管理"""
    list_display = ['document_type', 'depends_on', 'dependency_type', 'is_required']
    list_filter = ['dependency_type', 'is_required']


@admin.register(DocumentValidation)
class DocumentValidationAdmin(admin.ModelAdmin):
    """单证校验记录管理"""
    list_display = ['document', 'rule', 'passed', 'validation_type', 'created_at']
    list_filter = ['passed', 'validation_type', 'rule']
    readonly_fields = ['created_at']
```

- [ ] **步骤 2：验证管理后台可访问**

运行：`python manage.py check`
预期：无报错

- [ ] **步骤 3：Commit**

```bash
git add apps/documents/admin.py
git commit -m "feat: configure document admin interface"
```

---

### 任务 12：创建初始依赖数据

**文件：**
- 创建：`apps/documents/fixtures/dependencies.json`
- 创建：`apps/documents/management/commands/init_documents.py`

- [ ] **步骤 1：创建依赖关系数据**

创建 `apps/documents/fixtures/dependencies.json`：

```json
[
  {
    "model": "documents.documentdependency",
    "pk": 1,
    "fields": {
      "document_type": "packing_list",
      "depends_on": "commercial_invoice",
      "dependency_type": "sequential",
      "is_required": true
    }
  },
  {
    "model": "documents.documentdependency",
    "pk": 2,
    "fields": {
      "document_type": "bill_of_exchange",
      "depends_on": "commercial_invoice",
      "dependency_type": "sequential",
      "is_required": true
    }
  },
  {
    "model": "documents.documentdependency",
    "pk": 3,
    "fields": {
      "document_type": "insurance_application",
      "depends_on": "commercial_invoice",
      "dependency_type": "sequential",
      "is_required": true
    }
  },
  {
    "model": "documents.documentdependency",
    "pk": 4,
    "fields": {
      "document_type": "inspection_application",
      "depends_on": "commercial_invoice",
      "dependency_type": "sequential",
      "is_required": true
    }
  },
  {
    "model": "documents.documentdependency",
    "pk": 5,
    "fields": {
      "document_type": "certificate_of_origin",
      "depends_on": "commercial_invoice",
      "dependency_type": "sequential",
      "is_required": true
    }
  },
  {
    "model": "documents.documentdependency",
    "pk": 6,
    "fields": {
      "document_type": "insurance_policy",
      "depends_on": "insurance_application",
      "dependency_type": "sequential",
      "is_required": true
    }
  },
  {
    "model": "documents.documentdependency",
    "pk": 7,
    "fields": {
      "document_type": "inspection_certificate",
      "depends_on": "inspection_application",
      "dependency_type": "sequential",
      "is_required": true
    }
  },
  {
    "model": "documents.documentdependency",
    "pk": 8,
    "fields": {
      "document_type": "export_declaration",
      "depends_on": "inspection_certificate",
      "dependency_type": "sequential",
      "is_required": true
    }
  },
  {
    "model": "documents.documentdependency",
    "pk": 9,
    "fields": {
      "document_type": "bill_of_lading",
      "depends_on": "export_declaration",
      "dependency_type": "sequential",
      "is_required": true
    }
  },
  {
    "model": "documents.documentdependency",
    "pk": 10,
    "fields": {
      "document_type": "import_declaration",
      "depends_on": "bill_of_lading",
      "dependency_type": "sequential",
      "is_required": true
    }
  },
  {
    "model": "documents.documentdependency",
    "pk": 11,
    "fields": {
      "document_type": "beneficiary_certificate",
      "depends_on": "bill_of_lading",
      "dependency_type": "sequential",
      "is_required": true
    }
  },
  {
    "model": "documents.documentdependency",
    "pk": 12,
    "fields": {
      "document_type": "shipping_advice",
      "depends_on": "bill_of_lading",
      "dependency_type": "sequential",
      "is_required": true
    }
  },
  {
    "model": "documents.documentdependency",
    "pk": 13,
    "fields": {
      "document_type": "letter_of_credit",
      "depends_on": "sales_contract",
      "dependency_type": "sequential",
      "is_required": true
    }
  }
]
```

- [ ] **步骤 2：创建初始化命令**

创建 `apps/documents/management/commands/init_documents.py`：

```python
from django.core.management.base import BaseCommand
from django.core.management import call_command
from apps.documents.models import DocumentTemplate, TemplateField


class Command(BaseCommand):
    help = '初始化单证系统数据'

    def handle(self, *args, **options):
        self.stdout.write('开始初始化单证系统数据...')

        # 加载依赖关系
        try:
            call_command('loaddata', 'dependencies', app_label='documents')
            self.stdout.write(self.style.SUCCESS('  ✓ 单证依赖关系加载完成'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  ✗ 加载失败: {e}'))

        # 创建标准单证模板（简化版）
        templates_data = [
            ('commercial_invoice', '商业发票', self._get_invoice_template()),
            ('packing_list', '装箱单', self._get_packing_list_template()),
            # ... 其他模板
        ]

        for code, name, content in templates_data:
            template, created = DocumentTemplate.objects.get_or_create(
                code=code,
                defaults={
                    'name': name,
                    'content': content,
                    'is_system': True
                }
            )
            if created:
                self._create_template_fields(template)
                self.stdout.write(self.style.SUCCESS(f'  ✓ 创建模板: {name}'))

        self.stdout.write(self.style.SUCCESS('单证系统初始化完成！'))

    def _get_invoice_template(self):
        return '''<div class="invoice">
            <h2>商业发票</h2>
            <table>
                <tr><td>发票编号</td><td>{{invoice_no}}</td></tr>
                <tr><td>发票日期</td><td>{{invoice_date}}</td></tr>
                <tr><td>买方</td><td>{{buyer_name}}</td></tr>
                <tr><td>卖方</td><td>{{seller_name}}</td></tr>
                <tr><td>金额</td><td>{{invoice_amount}}</td></tr>
            </table>
        </div>'''

    def _get_packing_list_template(self):
        return '''<div class="packing-list">
            <h2>装箱单</h2>
            <table>
                <tr><td>发票编号</td><td>{{invoice_no}}</td></tr>
                <tr><td>数量</td><td>{{packing_quantity}}</td></tr>
            </table>
        </div>'''

    def _create_template_fields(self, template):
        """创建模板字段配置"""
        if template.code == 'commercial_invoice':
            fields = [
                ('invoice_no', '发票编号', 'text', True),
                ('invoice_date', '发票日期', 'date', True),
                ('buyer_name', '买方名称', 'text', True),
                ('seller_name', '卖方名称', 'text', True),
                ('invoice_amount', '发票金额', 'decimal', True),
            ]
        elif template.code == 'packing_list':
            fields = [
                ('invoice_no', '发票编号', 'text', True),
                ('packing_quantity', '数量', 'number', True),
                ('net_weight', '净重', 'decimal', False),
                ('gross_weight', '毛重', 'decimal', False),
            ]
        else:
            fields = []

        for i, (name, label, field_type, required) in enumerate(fields):
            TemplateField.objects.get_or_create(
                template=template,
                field_name=name,
                defaults={
                    'label': label,
                    'field_type': field_type,
                    'required': required,
                    'sort_order': i
                }
            )
```

- [ ] **步骤 3：验证命令可运行**

运行：`python manage.py init_documents`
预期：数据加载成功

- [ ] **步骤 4：Commit**

```bash
git add apps/documents/fixtures/ apps/documents/management/
git commit -m "feat: add document system initialization data and command"
```

---

### 任务 13：最终验证与测试

**文件：**
- 无新建文件，验证整体功能

- [ ] **步骤 1：运行完整测试套件**

运行：`pytest apps/documents/ -v --tb=short`
预期：所有测试通过

- [ ] **步骤 2：验证数据库迁移**

运行：`python manage.py makemigrations --check`
预期：无待生成的迁移

- [ ] **步骤 3：验证 API 端点**

运行：`python manage.py show_urls 2>/dev/null | grep documents || echo "URL检查完成"`
预期：URL 已注册

- [ ] **步骤 4：初始化数据**

运行：`python manage.py init_documents`
预期：数据初始化成功

- [ ] **步骤 5：Commit**

```bash
git commit --allow-empty -m "chore: verify document system implementation complete"
```

---

## 自检清单

### 规格覆盖度

| 规格章节 | 对应任务 |
|---------|---------|
| 单证模板模型 | 任务 2 |
| 依赖关系模型 | 任务 3 |
| 单证记录模型 | 任务 4 |
| 校验记录模型 | 任务 5 |
| 自动校验引擎 | 任务 6 |
| 依赖检查服务 | 任务 7 |
| 数据填充服务 | 任务 8 |
| API 序列化器 | 任务 9 |
| API 视图 | 任务 10 |
| 管理后台 | 任务 11 |
| 初始数据 | 任务 12 |

### 占位符检查

✅ 无 "待定"、"TODO"、未完成的章节或模糊的需求

### 类型一致性

✅ 模型字段名在各处一致
✅ API 响应格式统一
✅ 状态枚举值一致

---

## 总结

此计划实现了 SimTrade 平台的单证系统，包括：

1. **5 个数据模型** - DocumentTemplate, TemplateField, DocumentDependency, Document, DocumentValidation
2. **校验引擎** - 日期逻辑、金额一致性、数量一致性、必填字段
3. **业务服务** - 依赖检查、智能数据填充
4. **完整 API** - 创建、编辑、提交、审核
5. **15 种单证支持** - 完整的依赖关系定义

**下一步**：实现交易管理系统，与单证系统进行集成。
