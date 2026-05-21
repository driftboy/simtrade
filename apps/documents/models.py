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
    validation_rules = models.TextField('校验规则', null=True, blank=True)
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
    transaction_id = models.IntegerField('交易ID', null=True, blank=True)
    status = models.CharField(
        '状态',
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )
    data = models.TextField('单证数据', default=dict)
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
    auto_validation_result = models.TextField(
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