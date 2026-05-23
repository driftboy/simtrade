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

    # 迁移过渡期：允许 NULL，之后改为非空
    buyer = models.ForeignKey(
        'roles.Company',
        on_delete=models.PROTECT,
        related_name='buying_transactions',
        null=True
    )
    seller = models.ForeignKey(
        'roles.Company',
        on_delete=models.PROTECT,
        related_name='selling_transactions',
        null=True
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
        Transaction,
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
        'roles.Company',
        on_delete=models.PROTECT,
        related_name='applied_letters_of_credit'
    )
    beneficiary = models.ForeignKey(
        'roles.Company',
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


class LcAmendment(models.Model):
    """信用证修改记录"""

    class Status(models.TextChoices):
        PENDING = 'pending', '待处理'
        APPROVED = 'approved', '已批准'
        REJECTED = 'rejected', '已拒绝'

    lc = models.ForeignKey(
        LetterOfCredit,
        on_delete=models.CASCADE,
        related_name='amendments',
        verbose_name='信用证'
    )
    amendment_no = models.CharField('修改编号', max_length=50)
    initiated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='initiated_amendments',
        verbose_name='发起人'
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
        unique_together = [['lc', 'amendment_no']]

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
        related_name='bank_operations',
        verbose_name='信用证'
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
        related_name='bank_operations',
        verbose_name='操作员'
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
        Transaction,
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
        if self.status == 'draft' or not self.pk:
            self.total_amount = self.quantity * self.unit_price
        super().save(*args, **kwargs)

    @staticmethod
    def _generate_order_no():
        from django.utils import timezone
        import random
        date_str = timezone.now().strftime('%Y%m%d')
        for _ in range(10):
            rand_str = f'{random.randint(100000, 999999)}'
            order_no = f'PO{date_str}{rand_str}'
            if not PurchaseOrder.objects.filter(order_no=order_no).exists():
                return order_no
        raise RuntimeError('无法生成唯一订单编号，请重试')


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
        Contract,
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
    status = models.CharField('状态', max_length=20, choices=Status.choices, default=Status.DRAFT)
    notes = models.TextField('备注', blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='created_shipments'
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
            import random
            from django.utils import timezone
            date_str = timezone.now().strftime('%Y%m%d')
            for _ in range(10):
                rand_str = f'{random.randint(100000, 999999)}'
                no = f'SH{date_str}{rand_str}'
                if not Shipment.objects.filter(shipment_no=no).exists():
                    self.shipment_no = no
                    break
            else:
                raise RuntimeError('无法生成唯一货运编号，请重试')
        super().save(*args, **kwargs)


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
        Contract,
        on_delete=models.CASCADE,
        related_name='insurance_policy'
    )
    shipment = models.ForeignKey(
        Shipment,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='insurance_policies'
    )
    insured = models.ForeignKey(
        'roles.Company', on_delete=models.PROTECT,
        related_name='insured_policies'
    )
    insurer = models.ForeignKey(
        'roles.Company', on_delete=models.PROTECT,
        related_name='issued_policies'
    )
    policy_no = models.CharField('保单号', max_length=50, unique=True, editable=False)
    cargo_description = models.TextField('货物描述')
    insured_amount = models.DecimalField('投保金额', max_digits=14, decimal_places=2)
    premium = models.DecimalField('保费', max_digits=14, decimal_places=2, default=0)
    premium_currency = models.CharField('保费币种', max_length=10, default='CNY')
    coverage_type = models.CharField(
        '险种', max_length=20,
        choices=CoverageType.choices, default=CoverageType.ALL_RISK
    )
    status = models.CharField('状态', max_length=20, choices=Status.choices, default=Status.APPLIED)
    notes = models.TextField('备注', blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='created_insurance_policies'
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
            import random
            from django.utils import timezone
            date_str = timezone.now().strftime('%Y%m%d')
            for _ in range(10):
                rand_str = f'{random.randint(100000, 999999)}'
                no = f'IN{date_str}{rand_str}'
                if not InsurancePolicy.objects.filter(policy_no=no).exists():
                    self.policy_no = no
                    break
            else:
                raise RuntimeError('无法生成唯一保单号，请重试')
        super().save(*args, **kwargs)


class CustomsDeclaration(models.Model):
    """出口报关单"""

    class Status(models.TextChoices):
        DECLARED = 'declared', '已申报'
        REVIEWING = 'reviewing', '审核中'
        ASSESSED = 'assessed', '已征税'
        CLEARED = 'cleared', '已放行'
        REJECTED = 'rejected', '已退单'

    shipment = models.ForeignKey(
        Shipment,
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
    status = models.CharField('状态', max_length=20, choices=Status.choices, default=Status.DECLARED)
    notes = models.TextField('备注', blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='created_declarations'
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
        Shipment,
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
        '检验类型', max_length=20,
        choices=InspectionType.choices, default=InspectionType.LEGAL
    )
    fee = models.DecimalField('检验费', max_digits=14, decimal_places=2, default=0)
    fee_currency = models.CharField('费用币种', max_length=10, default='CNY')
    certificate_no = models.CharField('检验证书号', max_length=50, blank=True)
    origin_certificate_no = models.CharField('产地证号', max_length=50, blank=True)
    status = models.CharField('状态', max_length=20, choices=Status.choices, default=Status.APPLIED)
    notes = models.TextField('备注', blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='created_inspections'
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
