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
