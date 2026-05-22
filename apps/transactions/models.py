from django.db import models
from django.conf import settings


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

    # 暂时用 User，等 Company 模型实现后改为 Company
    buyer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='buying_transactions'
    )
    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='selling_transactions'
    )
    product_id = models.IntegerField('商品ID')  # 外键待 Product 表确定后调整
    status = models.CharField(
        '状态',
        max_length=20,
        choices=Status.choices,
        default=Status.INQUIRING
    )
    quantity = models.IntegerField('数量')
    unit_price = models.DecimalField('单价', max_digits=12, decimal_places=2)
    currency = models.CharField('货币', max_length=10, default='USD')
    trade_term = models.CharField('贸易术语', max_length=10, blank=True)
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
        return f"交易 #{self.id}"


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
    sender_role = models.CharField('发送者角色', max_length=50)
    message_type = models.CharField(
        '消息类型',
        max_length=20,
        choices=MessageType.choices
    )
    content = models.TextField('消息内容')
    offered_quantity = models.IntegerField('报价数量', null=True, blank=True)
    offered_price = models.DecimalField('报价单价', max_digits=12, decimal_places=2, null=True, blank=True)
    offered_trade_term = models.CharField('报价贸易术语', max_length=10, blank=True)
    attachment = models.FileField('附件', upload_to='inquiry_attachments/', blank=True)
    is_read = models.BooleanField('是否已读', default=False)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'inquiry_messages'
        verbose_name = '磋商消息'
        verbose_name_plural = '磋商消息'
        ordering = ['created_at']

    def __str__(self):
        return f"{self.get_message_type_display()} - {self.transaction_id}"


class Contract(models.Model):
    """外销合同"""

    class Status(models.TextChoices):
        DRAFT = 'draft', '草稿'
        PENDING_CONFIRM = 'pending_confirm', '待确认'
        PENDING_SIGN = 'pending_sign', '待签字'
        ONE_SIGNED = 'one_signed', '一方签字'
        SIGNED = 'signed', '已签字'
        EFFECTIVE = 'effective', '已生效'
        AMENDING = 'amending', '修改中'
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
    trade_term = models.CharField('贸易术语', max_length=10)
    payment_term = models.CharField('付款方式', max_length=50)
    delivery_time = models.DateField('交货日期')
    port_of_loading = models.CharField('装运港', max_length=100)
    port_of_discharge = models.CharField('目的港', max_length=100)

    # 商品信息（快照）
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


class ContractSignature(models.Model):
    """合同签字记录"""

    contract = models.ForeignKey(
        Contract,
        on_delete=models.CASCADE,
        related_name='signatures'
    )
    party = models.CharField('当事方', max_length=20)
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


class ContractAmendment(models.Model):
    """合同修改记录"""

    class Status(models.TextChoices):
        PENDING = 'pending', '待处理'
        ACCEPTED = 'accepted', '已接受'
        REJECTED = 'rejected', '已拒绝'

    contract = models.ForeignKey(
        Contract,
        on_delete=models.CASCADE,
        related_name='amendments',
        verbose_name='合同'
    )
    amendment_no = models.CharField('修改编号', max_length=50)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='requested_amendments',
        verbose_name='请求人'
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
        unique_together = [['contract', 'amendment_no']]

    def __str__(self):
        return f"{self.contract.contract_no} - {self.amendment_no}"
