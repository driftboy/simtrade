from django.db import models
from django.conf import settings


class Company(models.Model):
    """虚拟公司 — 学生的企业实体"""

    name = models.CharField('公司名称', max_length=200, unique=True)
    name_en = models.CharField('英文名称', max_length=200, blank=True)
    code = models.CharField('公司代码', max_length=20, unique=True)
    type = models.CharField('企业类型', max_length=50, blank=True)
    country = models.ForeignKey(
        'core.Country',
        on_delete=models.PROTECT,
        null=True,
        related_name='companies'
    )
    description = models.TextField('公司简介', blank=True)
    address = models.TextField('地址', blank=True)
    phone = models.CharField('电话', max_length=50, blank=True)
    email = models.EmailField('邮箱', blank=True)
    logo = models.URLField('Logo URL', blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_companies'
    )
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'companies'
        verbose_name = '公司'
        verbose_name_plural = '公司'
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class TradeRole(models.Model):
    """10 种贸易角色定义"""

    class RoleType(models.TextChoices):
        EXPORTER = 'exporter', '出口商'
        IMPORTER = 'importer', '进口商'
        FACTORY = 'factory', '工厂'
        BANK = 'bank', '银行'
        CUSTOMS = 'customs', '海关'
        SHIPPING = 'shipping', '货运公司'
        INSURANCE = 'insurance', '保险公司'
        INSPECTION = 'inspection', '商检机构'
        FOREX = 'forex', '外汇局'
        TAX = 'tax', '税务局'

    code = models.CharField(
        '角色代码',
        max_length=50,
        choices=RoleType.choices,
        unique=True
    )
    name = models.CharField('角色名称', max_length=100)
    description = models.TextField('职责说明')
    is_enabled = models.BooleanField('是否启用', default=True)
    is_system = models.BooleanField('系统预置', default=True)
    sort_order = models.IntegerField('排序', default=0)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'trade_roles'
        verbose_name = '贸易角色'
        verbose_name_plural = '贸易角色'
        ordering = ['sort_order', 'code']

    def __str__(self):
        return self.name


class UserCompanyRole(models.Model):
    """用户-公司-角色分配（支持多学生共享一公司）"""

    class Status(models.TextChoices):
        PENDING = 'pending', '待审核'
        APPROVED = 'approved', '已批准'
        REJECTED = 'rejected', '已拒绝'
        ACTIVE = 'active', '激活中'
        SUSPENDED = 'suspended', '已暂停'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='trade_roles'
    )
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='members'
    )
    role = models.ForeignKey(
        TradeRole,
        on_delete=models.CASCADE,
        related_name='assignees'
    )
    status = models.CharField(
        '状态',
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    is_active = models.BooleanField('当前激活', default=False)
    requested_at = models.DateTimeField('申请时间', auto_now_add=True)
    approved_at = models.DateTimeField('批准时间', null=True, blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='approved_role_assignments'
    )
    notes = models.TextField('备注', blank=True)

    class Meta:
        db_table = 'user_company_roles'
        unique_together = [['user', 'company', 'role']]
        verbose_name = '用户角色分配'
        verbose_name_plural = '用户角色分配'
        ordering = ['-requested_at']

    def __str__(self):
        return f'{self.user.username} - {self.company.name} - {self.role.name}'

    def save(self, *args, **kwargs):
        # 确保单一激活：如果设置为激活，停用该用户的其他角色
        if self.is_active:
            UserCompanyRole.objects.filter(
                user=self.user,
                is_active=True
            ).exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)
