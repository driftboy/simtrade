# 工厂-出口商供应链 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 在 apps/transactions 中实现 PurchaseOrder 模型和服务层，支持出口商向工厂下单、工厂确认/发货/开票/出口商收货的完整供应链流程

**架构：** 在现有 transactions app 中新增 PurchaseOrder 模型，通过 FK 关联 Transaction。新增 PurchaseOrderService 处理状态流转和权限校验，复用 TransactionLog 记录审计日志

**Tech Stack：** Django 3.2, DRF, pytest, Python 3.8+

---

## 文件结构

### 将要创建的文件

| 文件路径 | 职责 |
|---------|------|
| `apps/transactions/tests/test_purchase_order_models.py` | PurchaseOrder 模型测试 |
| `apps/transactions/tests/test_purchase_order_services.py` | PurchaseOrderService 服务测试 |
| `apps/transactions/tests/test_purchase_order_api.py` | PurchaseOrder API 测试 |

### 将要修改的文件

| 文件路径 | 修改内容 |
|---------|---------|
| `apps/transactions/models.py` | 新增 PurchaseOrder 模型 |
| `apps/transactions/services.py` | 新增 PurchaseOrderService |
| `apps/transactions/serializers.py` | 新增 PurchaseOrderSerializer、CreatePurchaseOrderSerializer |
| `apps/transactions/views.py` | 新增 PurchaseOrderViewSet |
| `apps/transactions/urls.py` | 注册 PurchaseOrderViewSet |
| `apps/transactions/admin.py` | 新增 PurchaseOrderAdmin |

---

## 任务分解

### 任务 1：实现 PurchaseOrder 模型

**文件：**
- 修改：`apps/transactions/models.py`
- 创建：`apps/transactions/tests/test_purchase_order_models.py`

- [ ] **步骤 1：编写 PurchaseOrder 模型测试**

创建 `apps/transactions/tests/test_purchase_order_models.py`：

```python
import pytest
from django.test import TestCase
from datetime import date
from decimal import Decimal
from apps.transactions.models import Transaction, PurchaseOrder
from apps.users.models import User
from apps.roles.services import CompanyService
from apps.core.models import Country


def get_or_create_country():
    country, _ = Country.objects.get_or_create(
        code='CN',
        defaults={'name': '中国', 'name_en': 'China', 'phone_code': '86'}
    )
    return country


def create_company_for_user(user, name_suffix=''):
    country = get_or_create_country()
    return CompanyService.create_company(
        user=user,
        name=f'{user.username}{name_suffix}公司',
        name_en=f'{user.username}{name_suffix} Company',
        country_id=country.code
    )


class PurchaseOrderModelTest(TestCase):
    """测试采购订单模型"""

    def setUp(self):
        self.exporter = User.objects.create_user(
            username='po_exporter', password='testpass', email='po_exp@test.com'
        )
        self.factory_user = User.objects.create_user(
            username='po_factory', password='testpass', email='po_fac@test.com'
        )
        self.exporter_company = create_company_for_user(self.exporter, '_出口商')
        self.factory_company = create_company_for_user(self.factory_user, '_工厂')
        self.transaction = Transaction.objects.create(
            buyer=self.exporter_company,
            seller=self.factory_company,
            product_id=1,
            quantity=1000,
            unit_price=10.00,
            status='in_progress',
            created_by=self.exporter
        )

    def test_create_purchase_order(self):
        """测试创建采购订单"""
        po = PurchaseOrder.objects.create(
            transaction=self.transaction,
            buyer=self.exporter_company,
            seller=self.factory_company,
            product_name='棉质T恤',
            quantity=Decimal('500'),
            unit_price=Decimal('8.00'),
            currency='CNY',
            created_by=self.exporter
        )
        assert po.order_no is not None
        assert po.order_no.startswith('PO')
        assert po.total_amount == Decimal('4000.00')
        assert po.status == 'draft'
        assert str(po) == po.order_no

    def test_purchase_order_auto_total_amount(self):
        """测试总金额自动计算"""
        po = PurchaseOrder.objects.create(
            transaction=self.transaction,
            buyer=self.exporter_company,
            seller=self.factory_company,
            product_name='棉质T恤',
            quantity=Decimal('100'),
            unit_price=Decimal('15.50'),
            currency='CNY',
            created_by=self.exporter
        )
        assert po.total_amount == Decimal('1550.00')

    def test_purchase_order_order_no_unique(self):
        """测试订单编号唯一性"""
        po1 = PurchaseOrder.objects.create(
            transaction=self.transaction,
            buyer=self.exporter_company,
            seller=self.factory_company,
            product_name='商品A',
            quantity=Decimal('10'),
            unit_price=Decimal('1.00'),
            currency='CNY',
            created_by=self.exporter
        )
        assert po1.order_no is not None

        po2 = PurchaseOrder.objects.create(
            transaction=self.transaction,
            buyer=self.exporter_company,
            seller=self.factory_company,
            product_name='商品B',
            quantity=Decimal('20'),
            unit_price=Decimal('2.00'),
            currency='CNY',
            created_by=self.exporter
        )
        assert po2.order_no != po1.order_no

    def test_purchase_order_status_choices(self):
        """测试状态选项完整"""
        valid_statuses = [choice[0] for choice in PurchaseOrder.Status.choices]
        assert 'draft' in valid_statuses
        assert 'confirmed' in valid_statuses
        assert 'shipped' in valid_statuses
        assert 'invoiced' in valid_statuses
        assert 'completed' in valid_statuses
        assert 'cancelled' in valid_statuses
```

- [ ] **步骤 2：运行测试验证失败**

运行：
```bash
pytest apps/transactions/tests/test_purchase_order_models.py -v
```

预期：FAIL，ImportError: cannot import name 'PurchaseOrder'

- [ ] **步骤 3：实现 PurchaseOrder 模型**

在 `apps/transactions/models.py` 末尾添加：

```python
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
        self.total_amount = self.quantity * self.unit_price
        super().save(*args, **kwargs)

    @staticmethod
    def _generate_order_no():
        import random
        from django.utils import timezone
        date_str = timezone.now().strftime('%Y%m%d')
        while True:
            rand_str = f'{random.randint(100000, 999999)}'
            order_no = f'PO{date_str}{rand_str}'
            if not PurchaseOrder.objects.filter(order_no=order_no).exists():
                return order_no
```

- [ ] **步骤 4：生成并运行迁移**

运行：
```bash
python manage.py makemigrations transactions
python manage.py migrate
pytest apps/transactions/tests/test_purchase_order_models.py -v
```

预期：全部 PASS

- [ ] **步骤 5：Commit**

```bash
git add apps/transactions/models.py apps/transactions/migrations/ apps/transactions/tests/test_purchase_order_models.py
git commit -m "feat(transactions): add PurchaseOrder model for factory supply chain"
```

---

### 任务 2：实现 PurchaseOrderService

**文件：**
- 修改：`apps/transactions/services.py`
- 创建：`apps/transactions/tests/test_purchase_order_services.py`

- [ ] **步骤 1：编写 PurchaseOrderService 测试**

创建 `apps/transactions/tests/test_purchase_order_services.py`：

```python
import pytest
from django.test import TestCase
from decimal import Decimal
from apps.transactions.models import Transaction, PurchaseOrder
from apps.transactions.services import PurchaseOrderService
from apps.users.models import User
from apps.roles.services import CompanyService, RoleService
from apps.roles.models import TradeRole, UserCompanyRole
from apps.core.models import Country


def get_or_create_country():
    country, _ = Country.objects.get_or_create(
        code='CN',
        defaults={'name': '中国', 'name_en': 'China', 'phone_code': '86'}
    )
    return country


def create_company_for_user(user, name_suffix=''):
    country = get_or_create_country()
    return CompanyService.create_company(
        user=user,
        name=f'{user.username}{name_suffix}公司',
        name_en=f'{user.username}{name_suffix} Company',
        country_id=country.code
    )


def setup_role(user, company, role_code):
    """为用户分配并激活指定角色"""
    role = TradeRole.objects.get(code=role_code)
    assignment = UserCompanyRole.objects.create(
        user=user, company=company, role=role,
        status='active', is_active=True
    )
    return assignment


class PurchaseOrderServiceCreateTest(TestCase):
    """测试创建采购订单"""

    def setUp(self):
        self.exporter = User.objects.create_user(
            username='svc_exporter', password='testpass', email='se@test.com'
        )
        self.factory_user = User.objects.create_user(
            username='svc_factory', password='testpass', email='sf@test.com'
        )
        self.importer = User.objects.create_user(
            username='svc_importer', password='testpass', email='si@test.com'
        )
        self.exporter_company = create_company_for_user(self.exporter, '_出口商')
        self.factory_company = create_company_for_user(self.factory_user, '_工厂')
        self.importer_company = create_company_for_user(self.importer, '_进口商')

        # 初始化角色
        from django.core.management import call_command
        call_command('init_trade_roles')

        # 分配角色
        setup_role(self.exporter, self.exporter_company, 'exporter')
        setup_role(self.factory_user, self.factory_company, 'factory')
        setup_role(self.importer, self.importer_company, 'importer')

        # 创建出口交易（进口商 → 出口商）
        self.transaction = Transaction.objects.create(
            buyer=self.importer_company,
            seller=self.exporter_company,
            product_id=1,
            quantity=1000,
            unit_price=10.00,
            status='in_progress',
            created_by=self.importer
        )

    def test_create_order_success(self):
        """出口商成功创建采购订单"""
        po = PurchaseOrderService.create_order(
            user=self.exporter,
            transaction_id=self.transaction.id,
            seller_id=self.factory_company.id,
            product_name='棉质T恤',
            quantity=Decimal('500'),
            unit_price=Decimal('8.00'),
            currency='CNY'
        )
        assert po.buyer == self.exporter_company
        assert po.seller == self.factory_company
        assert po.transaction == self.transaction
        assert po.status == 'draft'
        assert po.total_amount == Decimal('4000.00')
        assert po.created_by == self.exporter

    def test_create_order_non_exporter_rejected(self):
        """非出口商角色不能创建采购订单"""
        with pytest.raises(ValueError, match='只有出口商角色才能创建采购订单'):
            PurchaseOrderService.create_order(
                user=self.importer,
                transaction_id=self.transaction.id,
                seller_id=self.factory_company.id,
                product_name='商品',
                quantity=Decimal('100'),
                unit_price=Decimal('10.00')
            )

    def test_create_order_wrong_company_rejected(self):
        """出口商公司不是交易的 seller 时拒绝"""
        other_transaction = Transaction.objects.create(
            buyer=self.importer_company,
            seller=self.factory_company,
            product_id=2,
            quantity=100,
            unit_price=5.00,
            created_by=self.importer
        )
        with pytest.raises(ValueError, match='只能为自己的出口交易创建采购订单'):
            PurchaseOrderService.create_order(
                user=self.exporter,
                transaction_id=other_transaction.id,
                seller_id=self.factory_company.id,
                product_name='商品',
                quantity=Decimal('100'),
                unit_price=Decimal('10.00')
            )


class PurchaseOrderServiceConfirmTest(TestCase):
    """测试确认采购订单"""

    def setUp(self):
        self.exporter = User.objects.create_user(
            username='confirm_exp', password='testpass', email='ce@test.com'
        )
        self.factory_user = User.objects.create_user(
            username='confirm_fac', password='testpass', email='cf@test.com'
        )
        self.exporter_company = create_company_for_user(self.exporter, '_确认出口商')
        self.factory_company = create_company_for_user(self.factory_user, '_确认工厂')

        from django.core.management import call_command
        call_command('init_trade_roles')
        setup_role(self.exporter, self.exporter_company, 'exporter')
        setup_role(self.factory_user, self.factory_company, 'factory')

        self.transaction = Transaction.objects.create(
            buyer=create_company_for_user(
                User.objects.create_user('confirm_imp', 'p', 'ci@t.com'), '_确认进口商'
            ),
            seller=self.exporter_company,
            product_id=1,
            quantity=1000,
            unit_price=10.00,
            status='in_progress',
            created_by=self.exporter
        )
        self.po = PurchaseOrderService.create_order(
            user=self.exporter,
            transaction_id=self.transaction.id,
            seller_id=self.factory_company.id,
            product_name='商品',
            quantity=Decimal('100'),
            unit_price=Decimal('10.00')
        )

    def test_confirm_by_factory_success(self):
        """工厂确认订单成功"""
        result = PurchaseOrderService.confirm(self.po.id, self.factory_user)
        assert result.status == 'confirmed'
        assert result.confirmed_at is not None

    def test_confirm_by_exporter_rejected(self):
        """出口商不能确认订单"""
        with pytest.raises(ValueError, match='只有工厂角色才能确认订单'):
            PurchaseOrderService.confirm(self.po.id, self.exporter)

    def test_confirm_wrong_status_rejected(self):
        """非 draft 状态不能确认"""
        self.po.status = 'confirmed'
        self.po.save()
        with pytest.raises(ValueError, match='订单状态不允许确认'):
            PurchaseOrderService.confirm(self.po.id, self.factory_user)


class PurchaseOrderServiceShipTest(TestCase):
    """测试发货"""

    def setUp(self):
        self.exporter = User.objects.create_user(
            username='ship_exp', password='testpass', email='she@test.com'
        )
        self.factory_user = User.objects.create_user(
            username='ship_fac', password='testpass', email='shf@test.com'
        )
        self.exporter_company = create_company_for_user(self.exporter, '_发货出口商')
        self.factory_company = create_company_for_user(self.factory_user, '_发货工厂')

        from django.core.management import call_command
        call_command('init_trade_roles')
        setup_role(self.exporter, self.exporter_company, 'exporter')
        setup_role(self.factory_user, self.factory_company, 'factory')

        self.transaction = Transaction.objects.create(
            buyer=create_company_for_user(
                User.objects.create_user('ship_imp', 'p', 'shi@t.com'), '_发货进口商'
            ),
            seller=self.exporter_company,
            product_id=1,
            quantity=1000,
            unit_price=10.00,
            status='in_progress',
            created_by=self.exporter
        )
        self.po = PurchaseOrderService.create_order(
            user=self.exporter,
            transaction_id=self.transaction.id,
            seller_id=self.factory_company.id,
            product_name='商品',
            quantity=Decimal('100'),
            unit_price=Decimal('10.00')
        )
        PurchaseOrderService.confirm(self.po.id, self.factory_user)

    def test_ship_by_factory_success(self):
        """工厂发货成功"""
        result = PurchaseOrderService.ship(self.po.id, self.factory_user, tracking_info='物流单号:SF123456')
        assert result.status == 'shipped'
        assert result.shipped_at is not None

    def test_ship_by_exporter_rejected(self):
        """出口商不能发货"""
        with pytest.raises(ValueError, match='只有工厂角色才能发货'):
            PurchaseOrderService.ship(self.po.id, self.exporter)

    def test_ship_unconfirmed_order_rejected(self):
        """未确认的订单不能发货"""
        new_po = PurchaseOrderService.create_order(
            user=self.exporter,
            transaction_id=self.transaction.id,
            seller_id=self.factory_company.id,
            product_name='新商品',
            quantity=Decimal('50'),
            unit_price=Decimal('5.00')
        )
        with pytest.raises(ValueError, match='订单状态不允许发货'):
            PurchaseOrderService.ship(new_po.id, self.factory_user)


class PurchaseOrderServiceInvoiceTest(TestCase):
    """测试开票"""

    def setUp(self):
        self.exporter = User.objects.create_user(
            username='inv_exp', password='testpass', email='ie@test.com'
        )
        self.factory_user = User.objects.create_user(
            username='inv_fac', password='testpass', email='if@test.com'
        )
        self.exporter_company = create_company_for_user(self.exporter, '_开票出口商')
        self.factory_company = create_company_for_user(self.factory_user, '_开票工厂')

        from django.core.management import call_command
        call_command('init_trade_roles')
        setup_role(self.exporter, self.exporter_company, 'exporter')
        setup_role(self.factory_user, self.factory_company, 'factory')

        self.transaction = Transaction.objects.create(
            buyer=create_company_for_user(
                User.objects.create_user('inv_imp', 'p', 'ii@t.com'), '_开票进口商'
            ),
            seller=self.exporter_company,
            product_id=1,
            quantity=1000,
            unit_price=10.00,
            status='in_progress',
            created_by=self.exporter
        )
        self.po = PurchaseOrderService.create_order(
            user=self.exporter,
            transaction_id=self.transaction.id,
            seller_id=self.factory_company.id,
            product_name='商品',
            quantity=Decimal('100'),
            unit_price=Decimal('10.00')
        )
        PurchaseOrderService.confirm(self.po.id, self.factory_user)
        PurchaseOrderService.ship(self.po.id, self.factory_user)

    def test_invoice_by_factory_success(self):
        """工厂开票成功"""
        result = PurchaseOrderService.invoice(self.po.id, self.factory_user)
        assert result.status == 'invoiced'
        assert result.invoiced_at is not None


class PurchaseOrderServiceCompleteTest(TestCase):
    """测试完成"""

    def setUp(self):
        self.exporter = User.objects.create_user(
            username='comp_exp', password='testpass', email='cpe@test.com'
        )
        self.factory_user = User.objects.create_user(
            username='comp_fac', password='testpass', email='cpf@test.com'
        )
        self.exporter_company = create_company_for_user(self.exporter, '_完成出口商')
        self.factory_company = create_company_for_user(self.factory_user, '_完成工厂')

        from django.core.management import call_command
        call_command('init_trade_roles')
        setup_role(self.exporter, self.exporter_company, 'exporter')
        setup_role(self.factory_user, self.factory_company, 'factory')

        self.transaction = Transaction.objects.create(
            buyer=create_company_for_user(
                User.objects.create_user('comp_imp', 'p', 'cpi@t.com'), '_完成进口商'
            ),
            seller=self.exporter_company,
            product_id=1,
            quantity=1000,
            unit_price=10.00,
            status='in_progress',
            created_by=self.exporter
        )
        self.po = PurchaseOrderService.create_order(
            user=self.exporter,
            transaction_id=self.transaction.id,
            seller_id=self.factory_company.id,
            product_name='商品',
            quantity=Decimal('100'),
            unit_price=Decimal('10.00')
        )
        PurchaseOrderService.confirm(self.po.id, self.factory_user)
        PurchaseOrderService.ship(self.po.id, self.factory_user)
        PurchaseOrderService.invoice(self.po.id, self.factory_user)

    def test_complete_by_exporter_success(self):
        """出口商确认收货成功"""
        result = PurchaseOrderService.complete(self.po.id, self.exporter)
        assert result.status == 'completed'
        assert result.completed_at is not None

    def test_complete_by_factory_rejected(self):
        """工厂不能确认收货"""
        with pytest.raises(ValueError, match='只有出口商角色才能确认收货'):
            PurchaseOrderService.complete(self.po.id, self.factory_user)


class PurchaseOrderServiceCancelTest(TestCase):
    """测试取消订单"""

    def setUp(self):
        self.exporter = User.objects.create_user(
            username='cancel_exp', password='testpass', email='cae@test.com'
        )
        self.factory_user = User.objects.create_user(
            username='cancel_fac', password='testpass', email='caf@test.com'
        )
        self.exporter_company = create_company_for_user(self.exporter, '_取消出口商')
        self.factory_company = create_company_for_user(self.factory_user, '_取消工厂')

        from django.core.management import call_command
        call_command('init_trade_roles')
        setup_role(self.exporter, self.exporter_company, 'exporter')
        setup_role(self.factory_user, self.factory_company, 'factory')

        self.transaction = Transaction.objects.create(
            buyer=create_company_for_user(
                User.objects.create_user('cancel_imp', 'p', 'cai@t.com'), '_取消进口商'
            ),
            seller=self.exporter_company,
            product_id=1,
            quantity=1000,
            unit_price=10.00,
            status='in_progress',
            created_by=self.exporter
        )

    def test_cancel_draft_by_exporter(self):
        """出口商取消草稿订单"""
        po = PurchaseOrderService.create_order(
            user=self.exporter,
            transaction_id=self.transaction.id,
            seller_id=self.factory_company.id,
            product_name='商品',
            quantity=Decimal('100'),
            unit_price=Decimal('10.00')
        )
        result = PurchaseOrderService.cancel(po.id, self.exporter, reason='不需要了')
        assert result.status == 'cancelled'

    def test_cancel_confirmed_by_factory(self):
        """工厂取消已确认订单"""
        po = PurchaseOrderService.create_order(
            user=self.exporter,
            transaction_id=self.transaction.id,
            seller_id=self.factory_company.id,
            product_name='商品',
            quantity=Decimal('100'),
            unit_price=Decimal('10.00')
        )
        PurchaseOrderService.confirm(po.id, self.factory_user)
        result = PurchaseOrderService.cancel(po.id, self.factory_user, reason='产能不足')
        assert result.status == 'cancelled'

    def test_cancel_shipped_rejected(self):
        """已发货的订单不能取消"""
        po = PurchaseOrderService.create_order(
            user=self.exporter,
            transaction_id=self.transaction.id,
            seller_id=self.factory_company.id,
            product_name='商品',
            quantity=Decimal('100'),
            unit_price=Decimal('10.00')
        )
        PurchaseOrderService.confirm(po.id, self.factory_user)
        PurchaseOrderService.ship(po.id, self.factory_user)
        with pytest.raises(ValueError, match='已发货的订单不能取消'):
            PurchaseOrderService.cancel(po.id, self.exporter)
```

- [ ] **步骤 2：运行测试验证失败**

运行：
```bash
pytest apps/transactions/tests/test_purchase_order_services.py -v
```

预期：FAIL，ImportError: cannot import name 'PurchaseOrderService'

- [ ] **步骤 3：实现 PurchaseOrderService**

在 `apps/transactions/services.py` 末尾添加：

```python
from apps.transactions.models import PurchaseOrder


class PurchaseOrderService:
    """采购订单服务"""

    @staticmethod
    def create_order(user, transaction_id, seller_id, **kwargs):
        """出口商创建采购订单"""
        current_role = RoleService.get_current_role(user)
        if not current_role or current_role.role.code != 'exporter':
            raise ValueError('只有出口商角色才能创建采购订单')

        transaction = Transaction.objects.get(id=transaction_id)

        if transaction.seller_id != current_role.company_id:
            raise ValueError('只能为自己的出口交易创建采购订单')

        seller = Company.objects.get(id=seller_id)

        return PurchaseOrder.objects.create(
            transaction=transaction,
            buyer=current_role.company,
            seller=seller,
            created_by=user,
            **kwargs
        )

    @staticmethod
    def confirm(order_id, user):
        """工厂确认订单"""
        current_role = RoleService.get_current_role(user)
        if not current_role or current_role.role.code != 'factory':
            raise ValueError('只有工厂角色才能确认订单')

        po = PurchaseOrder.objects.get(id=order_id)
        if po.seller_id != current_role.company_id:
            raise ValueError('只能确认自己公司收到的订单')

        if po.status != 'draft':
            raise ValueError(f'订单状态不允许确认: {po.get_status_display()}')

        po.status = 'confirmed'
        po.confirmed_at = timezone.now()
        po.save()

        TransactionService.log_transaction(
            po.transaction, user, 'purchase_order_confirmed',
            {'order_no': po.order_no}
        )
        return po

    @staticmethod
    def ship(order_id, user, tracking_info=''):
        """工厂发货"""
        current_role = RoleService.get_current_role(user)
        if not current_role or current_role.role.code != 'factory':
            raise ValueError('只有工厂角色才能发货')

        po = PurchaseOrder.objects.get(id=order_id)
        if po.seller_id != current_role.company_id:
            raise ValueError('只能发货自己公司的订单')

        if po.status != 'confirmed':
            raise ValueError(f'订单状态不允许发货: {po.get_status_display()}')

        po.status = 'shipped'
        po.shipped_at = timezone.now()
        po.save()

        TransactionService.log_transaction(
            po.transaction, user, 'purchase_order_shipped',
            {'order_no': po.order_no, 'tracking_info': tracking_info}
        )
        return po

    @staticmethod
    def invoice(order_id, user):
        """工厂开具发票"""
        current_role = RoleService.get_current_role(user)
        if not current_role or current_role.role.code != 'factory':
            raise ValueError('只有工厂角色才能开票')

        po = PurchaseOrder.objects.get(id=order_id)
        if po.seller_id != current_role.company_id:
            raise ValueError('只能为自己公司的订单开票')

        if po.status != 'shipped':
            raise ValueError(f'订单状态不允许开票: {po.get_status_display()}')

        po.status = 'invoiced'
        po.invoiced_at = timezone.now()
        po.save()

        TransactionService.log_transaction(
            po.transaction, user, 'purchase_order_invoiced',
            {'order_no': po.order_no, 'amount': str(po.total_amount)}
        )
        return po

    @staticmethod
    def complete(order_id, user):
        """出口商确认收货"""
        current_role = RoleService.get_current_role(user)
        if not current_role or current_role.role.code != 'exporter':
            raise ValueError('只有出口商角色才能确认收货')

        po = PurchaseOrder.objects.get(id=order_id)
        if po.buyer_id != current_role.company_id:
            raise ValueError('只能确认自己公司采购的订单')

        if po.status != 'invoiced':
            raise ValueError(f'订单状态不允许确认收货: {po.get_status_display()}')

        po.status = 'completed'
        po.completed_at = timezone.now()
        po.save()

        TransactionService.log_transaction(
            po.transaction, user, 'purchase_order_completed',
            {'order_no': po.order_no}
        )
        return po

    @staticmethod
    def cancel(order_id, user, reason=''):
        """取消订单"""
        po = PurchaseOrder.objects.get(id=order_id)

        if po.status in ('shipped', 'invoiced', 'completed'):
            raise ValueError(f'订单状态不允许取消: {po.get_status_display()}')

        if po.status not in ('draft', 'confirmed'):
            raise ValueError(f'订单状态不允许取消: {po.get_status_display()}')

        po.status = 'cancelled'
        po.save()

        TransactionService.log_transaction(
            po.transaction, user, 'purchase_order_cancelled',
            {'order_no': po.order_no, 'reason': reason}
        )
        return po
```

同时在文件顶部 import 中添加 `Company`：

在 `apps/transactions/services.py` 顶部的 import 区域添加：
```python
from apps.roles.models import Company
```

- [ ] **步骤 4：运行测试验证通过**

运行：
```bash
pytest apps/transactions/tests/test_purchase_order_services.py -v
```

预期：全部 PASS

- [ ] **步骤 5：Commit**

```bash
git add apps/transactions/services.py apps/transactions/tests/test_purchase_order_services.py
git commit -m "feat(transactions): implement PurchaseOrderService with full lifecycle"
```

---

### 任务 3：实现序列化器

**文件：**
- 修改：`apps/transactions/serializers.py`
- 创建：`apps/transactions/tests/test_purchase_order_serializers.py`（可选，序列化器简单，在 API 测试中覆盖）

- [ ] **步骤 1：在 serializers.py 中添加序列化器**

在 `apps/transactions/serializers.py` 顶部 import 添加 `PurchaseOrder`：

```python
from apps.transactions.models import (
    Transaction, InquiryMessage, Contract, ContractSignature,
    ContractAmendment, LetterOfCredit, LcAmendment, BankOperation,
    PurchaseOrder
)
```

在文件末尾添加：

```python
class PurchaseOrderSerializer(serializers.ModelSerializer):
    """采购订单序列化器"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    buyer_name = serializers.CharField(source='buyer.name', read_only=True)
    seller_name = serializers.CharField(source='seller.name', read_only=True)
    transaction_id = serializers.IntegerField(source='transaction.id', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True, default='')

    class Meta:
        model = PurchaseOrder
        fields = [
            'id', 'order_no', 'transaction', 'transaction_id',
            'buyer', 'buyer_name', 'seller', 'seller_name',
            'product_name', 'product_code', 'quantity', 'unit',
            'unit_price', 'currency', 'total_amount',
            'delivery_date', 'delivery_address',
            'status', 'status_display', 'notes',
            'created_by', 'created_by_name',
            'confirmed_at', 'shipped_at', 'invoiced_at', 'completed_at',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'order_no', 'created_by', 'total_amount',
            'confirmed_at', 'shipped_at', 'invoiced_at', 'completed_at',
            'created_at', 'updated_at'
        ]


class CreatePurchaseOrderSerializer(serializers.Serializer):
    """创建采购订单请求"""
    transaction_id = serializers.IntegerField(min_value=1)
    seller_id = serializers.IntegerField(min_value=1)
    product_name = serializers.CharField(max_length=200)
    product_code = serializers.CharField(required=False, allow_blank=True, max_length=50)
    quantity = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0.01)
    unit = serializers.CharField(max_length=20, default='件')
    unit_price = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0.01)
    currency = serializers.CharField(max_length=10, default='CNY')
    delivery_date = serializers.DateField(required=False, allow_null=True)
    delivery_address = serializers.CharField(required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)
```

- [ ] **步骤 2：Commit**

```bash
git add apps/transactions/serializers.py
git commit -m "feat(transactions): add PurchaseOrder serializers"
```

---

### 任务 4：实现 API 视图和路由

**文件：**
- 修改：`apps/transactions/views.py`
- 修改：`apps/transactions/urls.py`
- 创建：`apps/transactions/tests/test_purchase_order_api.py`

- [ ] **步骤 1：编写 API 测试**

创建 `apps/transactions/tests/test_purchase_order_api.py`：

```python
import pytest
from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from apps.transactions.models import Transaction, PurchaseOrder
from apps.transactions.services import PurchaseOrderService
from apps.users.models import User
from apps.roles.services import CompanyService, RoleService
from apps.roles.models import TradeRole, UserCompanyRole
from apps.core.models import Country


def get_or_create_country():
    country, _ = Country.objects.get_or_create(
        code='CN',
        defaults={'name': '中国', 'name_en': 'China', 'phone_code': '86'}
    )
    return country


def create_company_for_user(user, name_suffix=''):
    country = get_or_create_country()
    return CompanyService.create_company(
        user=user,
        name=f'{user.username}{name_suffix}公司',
        name_en=f'{user.username}{name_suffix} Company',
        country_id=country.code
    )


def setup_role(user, company, role_code):
    role = TradeRole.objects.get(code=role_code)
    UserCompanyRole.objects.create(
        user=user, company=company, role=role,
        status='active', is_active=True
    )


class PurchaseOrderAPITest(TestCase):
    """测试采购订单 API"""

    def setUp(self):
        self.exporter = User.objects.create_user(
            username='api_exporter', password='testpass', email='ae@test.com'
        )
        self.factory_user = User.objects.create_user(
            username='api_factory', password='testpass', email='af@test.com'
        )
        self.importer = User.objects.create_user(
            username='api_importer', password='testpass', email='ai@test.com'
        )
        self.exporter_company = create_company_for_user(self.exporter, '_API出口商')
        self.factory_company = create_company_for_user(self.factory_user, '_API工厂')
        self.importer_company = create_company_for_user(self.importer, '_API进口商')

        from django.core.management import call_command
        call_command('init_trade_roles')

        setup_role(self.exporter, self.exporter_company, 'exporter')
        setup_role(self.factory_user, self.factory_company, 'factory')
        setup_role(self.importer, self.importer_company, 'importer')

        self.transaction = Transaction.objects.create(
            buyer=self.importer_company,
            seller=self.exporter_company,
            product_id=1,
            quantity=1000,
            unit_price=10.00,
            status='in_progress',
            created_by=self.importer
        )
        self.client = APIClient()

    def test_create_purchase_order(self):
        """测试创建采购订单"""
        self.client.force_authenticate(user=self.exporter)
        url = reverse('transactions:purchaseorder-list')
        data = {
            'transaction_id': self.transaction.id,
            'seller_id': self.factory_company.id,
            'product_name': '棉质T恤',
            'quantity': '500',
            'unit_price': '8.00',
            'currency': 'CNY'
        }
        response = self.client.post(url, data, format='json')
        assert response.status_code == 201
        assert response.json()['code'] == 0
        assert PurchaseOrder.objects.filter(buyer=self.exporter_company).exists()

    def test_list_purchase_orders(self):
        """测试获取采购订单列表"""
        PurchaseOrderService.create_order(
            user=self.exporter,
            transaction_id=self.transaction.id,
            seller_id=self.factory_company.id,
            product_name='商品',
            quantity=Decimal('100'),
            unit_price=Decimal('10.00')
        )
        self.client.force_authenticate(user=self.exporter)
        url = reverse('transactions:purchaseorder-list')
        response = self.client.get(url)
        assert response.status_code == 200
        assert len(response.json()['data']) >= 1

    def test_confirm_purchase_order(self):
        """测试工厂确认订单"""
        po = PurchaseOrderService.create_order(
            user=self.exporter,
            transaction_id=self.transaction.id,
            seller_id=self.factory_company.id,
            product_name='商品',
            quantity=Decimal('100'),
            unit_price=Decimal('10.00')
        )
        self.client.force_authenticate(user=self.factory_user)
        url = reverse('transactions:purchaseorder-confirm', kwargs={'pk': po.id})
        response = self.client.post(url)
        assert response.status_code == 200
        assert response.json()['code'] == 0

        po.refresh_from_db()
        assert po.status == 'confirmed'

    def test_ship_purchase_order(self):
        """测试工厂发货"""
        po = PurchaseOrderService.create_order(
            user=self.exporter,
            transaction_id=self.transaction.id,
            seller_id=self.factory_company.id,
            product_name='商品',
            quantity=Decimal('100'),
            unit_price=Decimal('10.00')
        )
        PurchaseOrderService.confirm(po.id, self.factory_user)
        self.client.force_authenticate(user=self.factory_user)
        url = reverse('transactions:purchaseorder-ship', kwargs={'pk': po.id})
        response = self.client.post(url, {'tracking_info': 'SF123456'}, format='json')
        assert response.status_code == 200

        po.refresh_from_db()
        assert po.status == 'shipped'

    def test_invoice_purchase_order(self):
        """测试工厂开票"""
        po = PurchaseOrderService.create_order(
            user=self.exporter,
            transaction_id=self.transaction.id,
            seller_id=self.factory_company.id,
            product_name='商品',
            quantity=Decimal('100'),
            unit_price=Decimal('10.00')
        )
        PurchaseOrderService.confirm(po.id, self.factory_user)
        PurchaseOrderService.ship(po.id, self.factory_user)
        self.client.force_authenticate(user=self.factory_user)
        url = reverse('transactions:purchaseorder-invoice', kwargs={'pk': po.id})
        response = self.client.post(url)
        assert response.status_code == 200

        po.refresh_from_db()
        assert po.status == 'invoiced'

    def test_complete_purchase_order(self):
        """测试出口商确认收货"""
        po = PurchaseOrderService.create_order(
            user=self.exporter,
            transaction_id=self.transaction.id,
            seller_id=self.factory_company.id,
            product_name='商品',
            quantity=Decimal('100'),
            unit_price=Decimal('10.00')
        )
        PurchaseOrderService.confirm(po.id, self.factory_user)
        PurchaseOrderService.ship(po.id, self.factory_user)
        PurchaseOrderService.invoice(po.id, self.factory_user)
        self.client.force_authenticate(user=self.exporter)
        url = reverse('transactions:purchaseorder-complete', kwargs={'pk': po.id})
        response = self.client.post(url)
        assert response.status_code == 200

        po.refresh_from_db()
        assert po.status == 'completed'

    def test_cancel_purchase_order(self):
        """测试取消订单"""
        po = PurchaseOrderService.create_order(
            user=self.exporter,
            transaction_id=self.transaction.id,
            seller_id=self.factory_company.id,
            product_name='商品',
            quantity=Decimal('100'),
            unit_price=Decimal('10.00')
        )
        self.client.force_authenticate(user=self.exporter)
        url = reverse('transactions:purchaseorder-cancel', kwargs={'pk': po.id})
        response = self.client.post(url, {'reason': '不需要了'}, format='json')
        assert response.status_code == 200

        po.refresh_from_db()
        assert po.status == 'cancelled'

    def test_unauthenticated_rejected(self):
        """未认证请求被拒绝"""
        url = reverse('transactions:purchaseorder-list')
        response = self.client.get(url)
        assert response.status_code in (401, 403)
```

- [ ] **步骤 2：运行测试验证失败**

运行：
```bash
pytest apps/transactions/tests/test_purchase_order_api.py -v
```

预期：FAIL，URL resolve error 或 ViewSet 不存在

- [ ] **步骤 3：实现 PurchaseOrderViewSet**

在 `apps/transactions/views.py` 顶部 import 添加：

```python
from apps.transactions.models import Transaction, InquiryMessage, Contract, PurchaseOrder
from apps.transactions.serializers import (
    TransactionSerializer, InquiryMessageSerializer, ContractSerializer,
    PurchaseOrderSerializer, CreatePurchaseOrderSerializer
)
from apps.transactions.services import TransactionService, PurchaseOrderService
```

在文件末尾添加：

```python
class PurchaseOrderViewSet(viewsets.ModelViewSet):
    """采购订单视图集"""

    serializer_class = PurchaseOrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        current_role = RoleService.get_current_role(user)
        if not current_role or not current_role.company:
            return PurchaseOrder.objects.none()
        company = current_role.company
        return PurchaseOrder.objects.filter(
            buyer=company
        ) | PurchaseOrder.objects.filter(
            seller=company
        )

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'code': 0,
            'message': 'success',
            'data': serializer.data
        })

    def create(self, request, *args, **kwargs):
        serializer = CreatePurchaseOrderSerializer(data=request.data)
        if serializer.is_valid():
            try:
                po = PurchaseOrderService.create_order(
                    user=request.user,
                    **serializer.validated_data
                )
                result_serializer = PurchaseOrderSerializer(po)
                return Response({
                    'code': 0,
                    'message': '采购订单创建成功',
                    'data': result_serializer.data
                }, status=status.HTTP_201_CREATED)
            except Exception as e:
                return Response({
                    'code': 5005,
                    'message': str(e)
                }, status=status.HTTP_400_BAD_REQUEST)
        return Response({
            'code': 3002,
            'message': '参数格式错误',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({
            'code': 0,
            'message': 'success',
            'data': serializer.data
        })

    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        po = self.get_object()
        try:
            result = PurchaseOrderService.confirm(po.id, request.user)
            serializer = PurchaseOrderSerializer(result)
            return Response({
                'code': 0,
                'message': '订单已确认',
                'data': serializer.data
            })
        except Exception as e:
            return Response({
                'code': 5005,
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def ship(self, request, pk=None):
        po = self.get_object()
        try:
            tracking_info = request.data.get('tracking_info', '')
            result = PurchaseOrderService.ship(po.id, request.user, tracking_info)
            serializer = PurchaseOrderSerializer(result)
            return Response({
                'code': 0,
                'message': '已发货',
                'data': serializer.data
            })
        except Exception as e:
            return Response({
                'code': 5005,
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def invoice(self, request, pk=None):
        po = self.get_object()
        try:
            result = PurchaseOrderService.invoice(po.id, request.user)
            serializer = PurchaseOrderSerializer(result)
            return Response({
                'code': 0,
                'message': '已开票',
                'data': serializer.data
            })
        except Exception as e:
            return Response({
                'code': 5005,
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        po = self.get_object()
        try:
            result = PurchaseOrderService.complete(po.id, request.user)
            serializer = PurchaseOrderSerializer(result)
            return Response({
                'code': 0,
                'message': '已确认收货',
                'data': serializer.data
            })
        except Exception as e:
            return Response({
                'code': 5005,
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        po = self.get_object()
        try:
            reason = request.data.get('reason', '')
            result = PurchaseOrderService.cancel(po.id, request.user, reason)
            serializer = PurchaseOrderSerializer(result)
            return Response({
                'code': 0,
                'message': '订单已取消',
                'data': serializer.data
            })
        except Exception as e:
            return Response({
                'code': 5005,
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
```

- [ ] **步骤 4：注册路由**

编辑 `apps/transactions/urls.py`：

```python
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.transactions import views

app_name = 'transactions'

router = DefaultRouter()
router.register(r'transactions', views.TransactionViewSet, basename='transaction')
router.register(r'contracts', views.ContractViewSet, basename='contract')
router.register(r'purchase-orders', views.PurchaseOrderViewSet, basename='purchaseorder')

urlpatterns = router.urls
```

- [ ] **步骤 5：运行测试验证通过**

运行：
```bash
pytest apps/transactions/tests/test_purchase_order_api.py -v
```

预期：全部 PASS

- [ ] **步骤 6：Commit**

```bash
git add apps/transactions/views.py apps/transactions/urls.py apps/transactions/tests/test_purchase_order_api.py
git commit -m "feat(transactions): add PurchaseOrderViewSet with full API endpoints"
```

---

### 任务 5：配置 Admin

**文件：**
- 修改：`apps/transactions/admin.py`

- [ ] **步骤 1：添加 PurchaseOrderAdmin**

在 `apps/transactions/admin.py` 顶部 import 添加 `PurchaseOrder`：

```python
from apps.transactions.models import (
    Transaction, InquiryMessage, Contract,
    ContractSignature, TransactionLog, ContractAmendment,
    LetterOfCredit, LcAmendment, BankOperation,
    PurchaseOrder
)
```

在文件末尾添加：

```python
@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    """采购订单管理"""

    list_display = [
        'order_no', 'buyer', 'seller', 'product_name',
        'total_amount', 'status', 'created_at'
    ]
    list_filter = ['status', 'currency', 'created_at']
    search_fields = ['order_no', 'product_name', 'buyer__name', 'seller__name']
    readonly_fields = [
        'created_at', 'updated_at', 'confirmed_at',
        'shipped_at', 'invoiced_at', 'completed_at'
    ]
```

- [ ] **步骤 2：验证 Django check**

运行：
```bash
python manage.py check
```

预期：无新增报错

- [ ] **步骤 3：Commit**

```bash
git add apps/transactions/admin.py
git commit -m "feat(transactions): add PurchaseOrderAdmin"
```

---

### 任务 6：最终验证

**文件：**
- 所有相关文件

- [ ] **步骤 1：运行全部测试**

运行：
```bash
pytest apps/transactions/tests/ apps/roles/tests/ -v
```

预期：全部 PASS（原有测试 + 新增采购订单测试）

- [ ] **步骤 2：验证 Django check**

运行：
```bash
python manage.py check
```

预期：无致命错误

---

## 自检清单

### 规格覆盖度

| 设计章节 | 对应任务 |
|---------|---------|
| PurchaseOrder 模型 | 任务 1 |
| 状态流转 | 任务 1 + 任务 2 |
| PurchaseOrderService | 任务 2 |
| 序列化器 | 任务 3 |
| API 端点 | 任务 4 |
| Admin 配置 | 任务 5 |
| 最终验证 | 任务 6 |

### 占位符检查

- 无 "TBD"、"TODO" 等占位符
- 所有代码步骤包含完整代码
- 所有命令有明确的预期输出

### 类型一致性检查

- 模型字段名在各处一致：`buyer`, `seller`, `order_no`, `status`, `total_amount`
- 服务方法签名一致：`create_order(user, transaction_id, seller_id, ...)`, `confirm(order_id, user)`, `ship(order_id, user, tracking_info)`, `invoice(order_id, user)`, `complete(order_id, user)`, `cancel(order_id, user, reason)`
- 序列化器字段名与模型一致
- API 端点与路由配置一致：`purchase-orders/`, `confirm/`, `ship/`, `invoice/`, `complete/`, `cancel/`
