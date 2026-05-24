from django.db import models


class Product(models.Model):
    """商品基础信息 - 系统级商品库"""

    class Category(models.TextChoices):
        ELECTRONICS = 'electronics', '电子产品'
        TEXTILES = 'textiles', '纺织品'
        MACHINERY = 'machinery', '机械设备'
        CHEMICALS = 'chemicals', '化工产品'
        FOOD = 'food', '食品'

    code = models.CharField('商品代码', max_length=50, unique=True)
    name = models.CharField('商品名称', max_length=200)
    name_en = models.CharField('英文名称', max_length=200, blank=True)
    category = models.CharField('分类', max_length=50, choices=Category.choices)
    unit = models.CharField('单位', max_length=20)  # PCS, KG, METER, etc.
    description = models.TextField('描述', blank=True)
    hs_code = models.CharField('HS 编码', max_length=20, blank=True)
    is_active = models.BooleanField('是否启用', default=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'products'
        verbose_name = '商品'
        verbose_name_plural = '商品'
        ordering = ['code']

    def __str__(self):
        return f"{self.code} - {self.name}"


class Catalog(models.Model):
    """公司商品目录 - 每个公司销售的商品"""

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='catalogs'
    )
    company = models.ForeignKey(
        'roles.Company',
        on_delete=models.CASCADE,
        related_name='catalogs'
    )
    sale_price = models.DecimalField('销售价格', max_digits=12, decimal_places=2)
    currency = models.CharField('货币', max_length=10, default='USD')
    min_order = models.IntegerField('最小起订量', default=1)
    max_order = models.IntegerField('最大供应量', null=True, blank=True)
    lead_time = models.IntegerField('交货期（天）', null=True, blank=True)
    is_available = models.BooleanField('是否可售', default=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'catalogs'
        verbose_name = '商品目录'
        verbose_name_plural = '商品目录'
        unique_together = [['company', 'product']]

    def __str__(self):
        return f"{self.product.name} - {self.sale_price} {self.currency}"
