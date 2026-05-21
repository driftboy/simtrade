# SimTrade 单证系统设计文档

**版本**: 1.0
**日期**: 2026-05-21
**作者**: Claude + 用户
**状态**: 已批准

---

## 1. 概述

### 1.1 目标

实现 SimTrade 平台的单证系统，支持 15 种外贸单证的制作、审核和校验，这是平台的核心特色功能。

### 1.2 设计原则

- **混合模板系统** - 标准模板保证可用性，自定义模板支持灵活性
- **严格制作顺序** - 遵循实际外贸业务流程
- **双层校验机制** - 自动校验 + 人工审核
- **智能数据填充** - 自动提取但允许修改

---

## 2. 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                         单证系统架构                              │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐   │
│  │   学生端     │      │   教师端     │      │   系统端     │   │
│  │ · 浏览单证   │      │ · 审核队列   │      │ · 自动校验   │   │
│  │ · 创建单证   │      │ · 审核操作   │      │ · 状态流转   │   │
│  │ · 填写数据   │      │ · 申诉处理   │      │ · 依赖检查   │   │
│  └──────┬───────┘      └──────┬───────┘      └──────┬───────┘   │
│         └─────────────────────┴─────────────────────┘           │
│                    ┌──────────▼──────────┐                     │
│                    │    单证核心服务     │                     │
│                    │ · 模板引擎         │                     │
│                    │ · 数据填充引擎     │                     │
│                    │ · 校验引擎         │                     │
│                    │ · 依赖引擎         │                     │
│                    └──────────┬──────────┘                     │
└──────────────────────────────┼─────────────────────────────────┘
         ┌─────────────────────┼─────────────────────┐
    ┌────▼────┐          ┌────▼────┐          ┌────▼────┐
    │ 模板层  │          │  业务层  │          │  数据层  │
    │ ·标准   │          │ ·单证   │          │Document │
    │  模板   │          │  状态机 │          │Template │
    │ ·自定义 │          │ ·工作流 │          │Dependency│
    └─────────┘          └─────────┘          └─────────┘
```

---

## 3. 数据模型

### 3.1 单证模板 (DocumentTemplate)

```python
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

    code = models.CharField('单证代码', max_length=50, choices=DocumentType.choices, unique=True)
    name = models.CharField('单证名称', max_length=100)
    version = models.CharField('版本号', max_length=20, default='1.0')
    content = models.TextField('模板内容 (HTML)')
    is_system = models.BooleanField('是否系统模板', default=True)
    created_by = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True)
    is_active = models.BooleanField('是否启用', default=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'document_templates'
        verbose_name = '单证模板'
        verbose_name_plural = '单证模板'
```

### 3.2 模板字段配置 (TemplateField)

```python
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

    template = models.ForeignKey(DocumentTemplate, on_delete=models.CASCADE, related_name='fields')
    field_name = models.CharField('字段名', max_length=50)
    label = models.CharField('显示标签', max_length=100)
    field_type = models.CharField('字段类型', max_length=20, choices=FieldType.choices)
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
```

### 3.3 单证依赖关系 (DocumentDependency)

```python
class DocumentDependency(models.Model):
    """单证依赖关系"""

    class DependencyType(models.TextChoices):
        SEQUENTIAL = 'sequential', '顺序依赖'
        PARALLEL = 'parallel', '并行'

    document_type = models.CharField('单证类型', max_length=50)
    depends_on = models.CharField('依赖单证类型', max_length=50)
    dependency_type = models.CharField('依赖类型', max_length=20, choices=DependencyType.choices)
    is_required = models.BooleanField('是否必需', default=True)

    class Meta:
        db_table = 'document_dependencies'
        verbose_name = '单证依赖'
        verbose_name_plural = '单证依赖'
```

### 3.4 单证记录 (Document)

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

    transaction = models.ForeignKey('transaction.Transaction', on_delete=models.CASCADE,
                                     null=True, blank=True, related_name='documents')
    template = models.ForeignKey(DocumentTemplate, on_delete=models.PROTECT)
    status = models.CharField('状态', max_length=20, choices=Status.choices, default=Status.DRAFT)
    data = models.JSONField('单证数据', default=dict)
    created_by = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True,
                                  related_name='created_documents')
    reviewed_by = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='reviewed_documents')
    auto_validation_result = models.JSONField('自动校验结果', null=True, blank=True)
    manual_review_status = models.CharField('人工审核状态', max_length=20, blank=True)
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
```

### 3.5 单证校验记录 (DocumentValidation)

```python
class DocumentValidation(models.Model):
    """单证校验记录"""

    class ValidationType(models.TextChoices):
        AUTO = 'auto', '自动校验'
        MANUAL = 'manual', '人工审核'

    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='validations')
    rule = models.CharField('校验规则', max_length=100)
    passed = models.BooleanField('是否通过')
    error_message = models.TextField('错误信息', blank=True)
    score_deduction = models.IntegerField('扣分', default=0)
    validation_type = models.CharField('校验类型', max_length=10, choices=ValidationType.choices)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'document_validations'
        verbose_name = '单证校验'
        verbose_name_plural = '单证校验'
```

---

## 4. 单证类型与依赖

| 序号 | 单证代码 | 单证名称 | 依赖单证 | 优先级 |
|------|----------|----------|----------|--------|
| 1 | commercial_invoice | 商业发票 | 无 | 1 |
| 2 | packing_list | 装箱单 | commercial_invoice | 2 |
| 3 | bill_of_exchange | 汇票 | commercial_invoice | 2 |
| 4 | insurance_application | 投保单 | commercial_invoice | 3 |
| 5 | insurance_policy | 保险单 | insurance_application | 4 |
| 6 | inspection_application | 报检单 | commercial_invoice | 3 |
| 7 | inspection_certificate | 检验证书 | inspection_application | 4 |
| 8 | export_declaration | 出口报关单 | inspection_certificate | 5 |
| 9 | bill_of_lading | 海运提单 | export_declaration | 6 |
| 10 | sales_contract | 外销合同 | 无 | 0 |
| 11 | letter_of_credit | 信用证 | sales_contract | 1 |
| 12 | import_declaration | 进口报关单 | bill_of_lading | 7 |
| 13 | certificate_of_origin | 产地证 | commercial_invoice | 3 |
| 14 | beneficiary_certificate | 受益人证明 | bill_of_lading | 7 |
| 15 | shipping_advice | 装船通知 | bill_of_lading | 7 |

---

## 5. 核心校验规则

### 5.1 自动校验规则（硬编码）

```python
# 日期逻辑校验
rules.register('date_logic', [
    '发票日期 <= 装运日期',
    '装运日期 <= 保险日期',
    '信用证开证日期 <= 装运日期',
    '保险日期 >= 发票日期',
])

# 金额一致性校验
rules.register('amount_consistency', [
    '发票金额 == 汇票金额',
    '保险金额 >= 发票金额 * 1.1',
    '各单证显示金额应一致',
])

# 数量一致性校验
rules.register('quantity_consistency', [
    '发票数量 == 装箱单数量',
    '发票数量 == 提单数量',
    '净重 <= 毛重',
])

# 单证齐全性校验
rules.register('document_completeness', [
    '信用证要求的所有单证必须提交',
    '必填字段不能为空',
])
```

### 5.2 自定义校验规则（数据库配置）

教师可通过管理后台配置：
- 某字段的必填/可选状态
- 特定格式的校验规则
- 各类错误的扣分标准

---

## 6. 业务流程

### 6.1 单证制作流程

```
[学生选择单证类型]
        │
        ▼
[检查依赖单证是否完成] ──→ 未完成 → 提示需要先制作的单证
        │ 已完成
        ▼
[创建单证实例]
        │
        ▼
[智能数据填充] ◄── 从交易/合同/已有单证提取数据
        │
        ▼
[学生编辑/填写]
        │
        ▼
[保存草稿]
        │
        ▼
[提交审核]
        │
        ▼
[自动校验] ──→ 失败 → 返回修改，显示错误
        │ 通过
        ▼
[进入人工审核队列]
```

### 6.2 单证状态机

```
草稿(DRAFT) → 待审核(PENDING_REVIEW) → 已审核(APPROVED) → 已提交(SUBMITTED) → 已接收(RECEIVED) → 已归档(ARCHIVED)
                │                        ↑
                └──→ 审核不通过(REJECTED) ┘
```

---

## 7. API 设计

### 7.1 单证模板 API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/v1/documents/templates/ | 获取模板列表 |
| GET | /api/v1/documents/templates/{code}/ | 获取模板详情 |
| POST | /api/v1/documents/templates/ | 创建自定义模板 (教师) |

### 7.2 单证操作 API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/v1/documents/ | 获取单证列表 |
| POST | /api/v1/documents/ | 创建单证 |
| GET | /api/v1/documents/{id}/ | 获取单证详情 |
| PUT | /api/v1/documents/{id}/ | 更新单证 |
| DELETE | /api/v1/documents/{id}/ | 删除单证 |
| POST | /api/v1/documents/{id}/submit/ | 提交审核 |
| POST | /api/v1/documents/{id}/approve/ | 审核通过 (教师) |
| POST | /api/v1/documents/{id}/reject/ | 审核驳回 (教师) |

### 7.3 辅助 API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/v1/documents/{id}/preview/ | 预览单证 |
| GET | /api/v1/documents/{id}/dependencies/ | 获取依赖关系 |
| POST | /api/v1/documents/validate/ | 批量校验 |

---

## 8. 权限设计

| 角色 | 权限 |
|------|------|
| 学生 | 创建、编辑、删除自己的草稿单证；提交审核；查看审核结果 |
| 教师 | 审核单证；查看所有单证；创建自定义模板 |
| 管理员 | 所有权限 |

---

## 9. 与现有系统集成

- **用户权限** - 复用现有的 RBAC 系统
- **基础数据** - 使用 Country/Port/Currency 模型
- **预留接口** - 为后续的交易系统预留关联字段
