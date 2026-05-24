from django.db import models
from django.conf import settings


class Notification(models.Model):
    """持久化通知"""

    class Type(models.TextChoices):
        INQUIRY = 'inquiry', '询盘'
        OFFER = 'offer', '发盘'
        COUNTER_OFFER = 'counter_offer', '还盘'
        ACCEPT = 'accept', '接受'
        REJECT = 'reject', '拒绝'
        LC_CREATED = 'lc_created', '信用证创建'
        CONTRACT_SIGNED = 'contract_signed', '合同签署'
        SYSTEM = 'system', '系统通知'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    type = models.CharField('类型', max_length=30, choices=Type.choices)
    title = models.CharField('标题', max_length=200)
    content = models.TextField('内容')
    is_read = models.BooleanField('已读', default=False)
    related_transaction_id = models.IntegerField('关联交易ID', null=True, blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'notifications'
        verbose_name = '通知'
        verbose_name_plural = '通知'
        ordering = ['-created_at']

    def __str__(self):
        return self.title
