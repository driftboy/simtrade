# 货运与保险 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 在 apps/transactions 中实现 Shipment 和 InsurancePolicy 模型及服务层，支持合同生效后的货运订舱/提单签发和保险投保/承保/签发流程

**架构：** 在现有 transactions app 中新增 Shipment 和 InsurancePolicy 模型（均通过 OneToOneField 关联 Contract），新增 ShipmentService 和 InsuranceService 处理状态流转和角色校验

**Tech Stack：** Django 3.2, DRF, pytest, Python 3.8+

---

## 文件结构

### 将要创建的文件

| 文件路径 | 职责 |
|---------|------|
| `apps/transactions/tests/test_shipment_models.py` | Shipment 模型测试 |
| `apps/transactions/tests/test_insurance_models.py` | InsurancePolicy 模型测试 |
| `apps/transactions/tests/test_shipment_services.py` | ShipmentService 服务测试 |
| `apps/transactions/tests/test_insurance_services.py` | InsuranceService 服务测试 |
| `apps/transactions/tests/test_shipment_insurance_api.py` | 货运+保险 API 测试 |

### 将要修改的文件

| 文件路径 | 修改内容 |
|---------|---------|
| `apps/transactions/models.py` | 新增 Shipment、InsurancePolicy 模型 |
| `apps/transactions/services.py` | 新增 ShipmentService、InsuranceService |
| `apps/transactions/serializers.py` | 新增货运和保险相关序列化器 |
| `apps/transactions/views.py` | 新增 ShipmentViewSet、InsurancePolicyViewSet |
| `apps/transactions/urls.py` | 注册新的 ViewSet |
| `apps/transactions/admin.py` | 新增 ShipmentAdmin、InsurancePolicyAdmin |

---

## 公共辅助函数

以下辅助函数在多个测试文件中重复使用：

```python
# 位于每个测试文件内部
import pytest
from django.test import TestCase
from datetime import date
from decimal import Decimal
from apps.transactions.models import Transaction, Contract, Shipment, InsurancePolicy
from apps.transactions.services import ShipmentService, InsuranceService
from apps.users.models import User
from apps.roles.services import CompanyService
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
    UserCompanyRole.objects.get_or_create(
        user=user, company=company, role=role,
        defaults={'status': 'active', 'is_active': True}
    )


def create_effective_contract(seller_company, buyer_company, seller_user):
    """创建一个已生效的合同（含交易）"""
    transaction = Transaction.objects.create(
        buyer=buyer_company,
        seller=seller_company,
        product_id=1,
        quantity=1000,
        unit_price=10.00,
        status='in_progress',
        created_by=seller_user
    )
    contract = Contract.objects.create(
        contract_no=f'SC{Transaction.objects.count()+1:04d}',
        transaction=transaction,
        trade_term='CIF',
        payment_term='L/C at sight',
        delivery_time=date(2026, 12, 31),
        port_of_loading='Shanghai',
        port_of_discharge='Los Angeles',
        product_name='Cotton T-Shirt',
        product_spec='100% Cotton',
        quantity=1000,
        unit='pcs',
        unit_price=10.00,
        total_amount=10000.00,
        currency='USD',
        status='effective'
    )
    return contract
```

---

## 任务分解

### 任务 1：实现 Shipment 模型

**文件：**
- 修改：`apps/transactions/models.py`
- 创建：`apps/transactions/tests/test_shipment_models.py`

- [ ] **步骤 1：编写 Shipment 模型测试**

创建 `apps/transactions/tests/test_shipment_models.py`：

```python
import pytest
from django.test import TestCase
from datetime import date
from decimal import Decimal
from apps.transactions.models import Transaction, Contract, Shipment
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


class ShipmentModelTest(TestCase):
    def setUp(self):
        self.exporter = User.objects.create_user(username='sh_mod_exp', password='testpass', email='sme@test.com')
        self.carrier_user = User.objects.create_user(username='sh_mod_car', password='testpass', email='smc@test.com')
        self.buyer_user = User.objects.create_user(username='sh_mod_buy', password='testpass', email='smb@test.com')
        self.exporter_company = create_company_for_user(self.exporter, '_货运出口商')
        self.carrier_company = create_company_for_user(self.carrier_user, '_货运公司')
        self.buyer_company = create_company_for_user(self.buyer_user, '_货运买方')
        self.transaction = Transaction.objects.create(
            buyer=self.buyer_company,
            seller=self.exporter_company,
            product_id=1, quantity=1000, unit_price=10.00,
            status='in_progress', created_by=self.exporter
        )
        self.contract = Contract.objects.create(
            contract_no='SM-TEST-001',
            transaction=self.transaction,
            trade_term='CIF', payment_term='L/C at sight',
            delivery_time=date(2026, 12, 31),
            port_of_loading='Shanghai', port_of_discharge='Los Angeles',
            product_name='Test Product', product_spec='Spec',
            quantity=1000, unit='pcs', unit_price=10.00,
            total_amount=10000.00, currency='USD',
            status='effective'
        )

    def test_create_shipment(self):
        shipment = Shipment.objects.create(
            contract=self.contract,
            shipper=self.exporter_company,
            carrier=self.carrier_company,
            port_of_loading='Shanghai',
            port_of_discharge='Los Angeles',
            freight_amount=Decimal('300.00'),
            freight_currency='USD',
            created_by=self.exporter
        )
        assert shipment.shipment_no is not None
        assert shipment.shipment_no.startswith('SH')
        assert shipment.status == 'draft'
        assert str(shipment) == shipment.shipment_no

    def test_shipment_no_unique(self):
        s1 = Shipment.objects.create(
            contract=self.contract,
            shipper=self.exporter_company,
            carrier=self.carrier_company,
            port_of_loading='Shanghai',
            port_of_discharge='Los Angeles',
            created_by=self.exporter
        )
        # 需要另一个合同因为 OneToOne
        txn2 = Transaction.objects.create(
            buyer=self.buyer_company, seller=self.exporter_company,
            product_id=2, quantity=100, unit_price=5.00,
            created_by=self.exporter
        )
        c2 = Contract.objects.create(
            contract_no='SM-TEST-002', transaction=txn2,
            trade_term='FOB', payment_term='T/T',
            delivery_time=date(2026, 12, 31),
            port_of_loading='Shanghai', port_of_discharge='Tokyo',
            product_name='P2', product_spec='',
            quantity=100, unit='pcs', unit_price=5.00,
            total_amount=500.00, currency='USD', status='effective'
        )
        s2 = Shipment.objects.create(
            contract=c2,
            shipper=self.exporter_company,
            carrier=self.carrier_company,
            port_of_loading='Shanghai',
            port_of_discharge='Tokyo',
            created_by=self.exporter
        )
        assert s1.shipment_no != s2.shipment_no

    def test_shipment_status_choices(self):
        valid = [c[0] for c in Shipment.Status.choices]
        assert 'draft' in valid
        assert 'booked' in valid
        assert 'loaded' in valid
        assert 'shipped' in valid
        assert 'arrived' in valid
        assert 'cancelled' in valid
```

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest apps/transactions/tests/test_shipment_models.py -v`
预期：FAIL，ImportError: cannot import name 'Shipment'

- [ ] **步骤 3：实现 Shipment 模型**

在 `apps/transactions/models.py` 末尾（PurchaseOrder 之后）添加：

```python
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
```

- [ ] **步骤 4：生成迁移并运行测试**

运行：
```bash
python manage.py makemigrations transactions
python manage.py migrate
pytest apps/transactions/tests/test_shipment_models.py -v
```

预期：全部 PASS

- [ ] **步骤 5：Commit**

```bash
git add apps/transactions/models.py apps/transactions/migrations/ apps/transactions/tests/test_shipment_models.py
git commit -m "feat(transactions): add Shipment model"
```

---

### 任务 2：实现 InsurancePolicy 模型

**文件：**
- 修改：`apps/transactions/models.py`
- 创建：`apps/transactions/tests/test_insurance_models.py`

- [ ] **步骤 1：编写 InsurancePolicy 模型测试**

创建 `apps/transactions/tests/test_insurance_models.py`：

```python
import pytest
from django.test import TestCase
from datetime import date
from decimal import Decimal
from apps.transactions.models import Transaction, Contract, Shipment, InsurancePolicy
from apps.users.models import User
from apps.roles.services import CompanyService
from apps.core.models import Country


def get_or_create_country():
    country, _ = Country.objects.get_or_create(
        code='CN', defaults={'name': '中国', 'name_en': 'China', 'phone_code': '86'}
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


class InsurancePolicyModelTest(TestCase):
    def setUp(self):
        self.exporter = User.objects.create_user(username='in_mod_exp', password='testpass', email='ime@test.com')
        self.insurer_user = User.objects.create_user(username='in_mod_ins', password='testpass', email='imi@test.com')
        self.buyer_user = User.objects.create_user(username='in_mod_buy', password='testpass', email='imb@test.com')
        self.exporter_company = create_company_for_user(self.exporter, '_保险出口商')
        self.insurer_company = create_company_for_user(self.insurer_user, '_保险公司')
        self.buyer_company = create_company_for_user(self.buyer_user, '_保险买方')
        self.transaction = Transaction.objects.create(
            buyer=self.buyer_company, seller=self.exporter_company,
            product_id=1, quantity=1000, unit_price=10.00,
            status='in_progress', created_by=self.exporter
        )
        self.contract = Contract.objects.create(
            contract_no='IN-TEST-001', transaction=self.transaction,
            trade_term='CIF', payment_term='L/C at sight',
            delivery_time=date(2026, 12, 31),
            port_of_loading='Shanghai', port_of_discharge='Los Angeles',
            product_name='Test Product', product_spec='Spec',
            quantity=1000, unit='pcs', unit_price=10.00,
            total_amount=10000.00, currency='USD', status='effective'
        )

    def test_create_insurance_policy(self):
        policy = InsurancePolicy.objects.create(
            contract=self.contract,
            insured=self.exporter_company,
            insurer=self.insurer_company,
            cargo_description='1000件棉质T恤',
            insured_amount=Decimal('11000.00'),
            premium=Decimal('88.00'),
            premium_currency='CNY',
            coverage_type='all_risk',
            created_by=self.exporter
        )
        assert policy.policy_no is not None
        assert policy.policy_no.startswith('IN')
        assert policy.status == 'applied'
        assert str(policy) == policy.policy_no

    def test_policy_coverage_types(self):
        valid = [c[0] for c in InsurancePolicy.CoverageType.choices]
        assert 'fpa' in valid
        assert 'wa' in valid
        assert 'all_risk' in valid

    def test_policy_status_choices(self):
        valid = [c[0] for c in InsurancePolicy.Status.choices]
        assert 'applied' in valid
        assert 'underwritten' in valid
        assert 'issued' in valid
        assert 'cancelled' in valid
```

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest apps/transactions/tests/test_insurance_models.py -v`
预期：FAIL

- [ ] **步骤 3：实现 InsurancePolicy 模型**

在 `apps/transactions/models.py` 末尾（Shipment 之后）添加：

```python
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
```

- [ ] **步骤 4：生成迁移并运行测试**

运行：
```bash
python manage.py makemigrations transactions
python manage.py migrate
pytest apps/transactions/tests/test_insurance_models.py -v
```

预期：全部 PASS

- [ ] **步骤 5：Commit**

```bash
git add apps/transactions/models.py apps/transactions/migrations/ apps/transactions/tests/test_insurance_models.py
git commit -m "feat(transactions): add InsurancePolicy model"
```

---

### 任务 3：实现 ShipmentService

**文件：**
- 修改：`apps/transactions/services.py`
- 创建：`apps/transactions/tests/test_shipment_services.py`

- [ ] **步骤 1：编写 ShipmentService 测试**

创建 `apps/transactions/tests/test_shipment_services.py`。测试包含：
- `test_create_shipment_success` — 出口商创建货运订单
- `test_create_shipment_non_exporter_rejected` — 非出口商角色被拒
- `test_calculate_freight_cif` — CIF 运费计算（3%）
- `test_calculate_freight_fob` — FOB 运费为 0
- `test_book_by_carrier_success` — 货运公司确认订舱
- `test_book_by_exporter_rejected` — 出口商不能订舱
- `test_load_by_carrier_success` — 货运公司确认装船
- `test_issue_bl_by_carrier_success` — 货运公司签发提单
- `test_arrive_by_carrier_success` — 货运公司确认到港
- `test_cancel_draft_by_exporter` — 出口商取消草稿
- `test_cancel_booked_rejected_after_load` — 已装船不可取消

测试文件完整代码（包含所有辅助函数，使用上面"公共辅助函数"中的 `create_effective_contract`）：

```python
import pytest
from django.test import TestCase
from datetime import date
from decimal import Decimal
from apps.transactions.models import Transaction, Contract, Shipment
from apps.transactions.services import ShipmentService
from apps.users.models import User
from apps.roles.services import CompanyService
from apps.roles.models import TradeRole, UserCompanyRole
from apps.core.models import Country


def get_or_create_country():
    country, _ = Country.objects.get_or_create(
        code='CN', defaults={'name': '中国', 'name_en': 'China', 'phone_code': '86'}
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
    UserCompanyRole.objects.get_or_create(
        user=user, company=company, role=role,
        defaults={'status': 'active', 'is_active': True}
    )


def create_effective_contract(seller_company, buyer_company, seller_user, trade_term='CIF'):
    transaction = Transaction.objects.create(
        buyer=buyer_company, seller=seller_company,
        product_id=1, quantity=1000, unit_price=10.00,
        status='in_progress', created_by=seller_user
    )
    contract = Contract.objects.create(
        contract_no=f'SC{Transaction.objects.count()+1:04d}',
        transaction=transaction,
        trade_term=trade_term, payment_term='L/C at sight',
        delivery_time=date(2026, 12, 31),
        port_of_loading='Shanghai', port_of_discharge='Los Angeles',
        product_name='Test Product', product_spec='Spec',
        quantity=1000, unit='pcs', unit_price=10.00,
        total_amount=10000.00, currency='USD', status='effective'
    )
    return contract


class ShipmentServiceTest(TestCase):
    def setUp(self):
        from django.core.management import call_command
        call_command('init_trade_roles')

        self.exporter = User.objects.create_user(username='ss_exp', password='testpass', email='sse@test.com')
        self.carrier_user = User.objects.create_user(username='ss_car', password='testpass', email='ssc@test.com')
        self.buyer_user = User.objects.create_user(username='ss_buy', password='testpass', email='ssb@test.com')
        self.exporter_company = create_company_for_user(self.exporter, '_SS出口商')
        self.carrier_company = create_company_for_user(self.carrier_user, '_SS货运公司')
        self.buyer_company = create_company_for_user(self.buyer_user, '_SS买方')

        setup_role(self.exporter, self.exporter_company, 'exporter')
        setup_role(self.carrier_user, self.carrier_company, 'shipping')
        self.contract = create_effective_contract(
            self.exporter_company, self.buyer_company, self.exporter
        )

    def test_create_shipment_success(self):
        shipment = ShipmentService.create_shipment(
            user=self.exporter,
            contract_id=self.contract.id,
            carrier_id=self.carrier_company.id,
            port_of_loading='Shanghai',
            port_of_discharge='Los Angeles'
        )
        assert shipment.shipper == self.exporter_company
        assert shipment.carrier == self.carrier_company
        assert shipment.status == 'draft'

    def test_create_shipment_non_exporter_rejected(self):
        with pytest.raises(ValueError, match='只有出口商角色才能创建货运订单'):
            ShipmentService.create_shipment(
                user=self.carrier_user,
                contract_id=self.contract.id,
                carrier_id=self.carrier_company.id,
                port_of_loading='Shanghai',
                port_of_discharge='Los Angeles'
            )

    def test_calculate_freight_cif(self):
        amount = ShipmentService.calculate_freight(self.contract.id)
        assert amount == Decimal('300.00')  # 10000 * 3%

    def test_calculate_freight_fob(self):
        fob_contract = create_effective_contract(
            self.exporter_company, self.buyer_company, self.exporter, trade_term='FOB'
        )
        amount = ShipmentService.calculate_freight(fob_contract.id)
        assert amount == Decimal('0.00')

    def test_book_by_carrier_success(self):
        shipment = ShipmentService.create_shipment(
            user=self.exporter, contract_id=self.contract.id,
            carrier_id=self.carrier_company.id,
            port_of_loading='Shanghai', port_of_discharge='Los Angeles'
        )
        result = ShipmentService.book(
            shipment.id, self.carrier_user,
            booking_no='BK20260001', vessel_name='OOCL PIRAEUS',
            etd=date(2026, 10, 1), eta=date(2026, 11, 1)
        )
        assert result.status == 'booked'
        assert result.booking_no == 'BK20260001'
        assert result.booked_at is not None

    def test_book_by_exporter_rejected(self):
        shipment = ShipmentService.create_shipment(
            user=self.exporter, contract_id=self.contract.id,
            carrier_id=self.carrier_company.id,
            port_of_loading='Shanghai', port_of_discharge='Los Angeles'
        )
        with pytest.raises(ValueError, match='只有货运公司角色才能订舱'):
            ShipmentService.book(
                shipment.id, self.exporter,
                booking_no='BK001', vessel_name='Vessel',
                etd=date(2026, 10, 1), eta=date(2026, 11, 1)
            )

    def test_load_by_carrier_success(self):
        shipment = ShipmentService.create_shipment(
            user=self.exporter, contract_id=self.contract.id,
            carrier_id=self.carrier_company.id,
            port_of_loading='Shanghai', port_of_discharge='Los Angeles'
        )
        ShipmentService.book(
            shipment.id, self.carrier_user,
            booking_no='BK001', vessel_name='Vessel',
            etd=date(2026, 10, 1), eta=date(2026, 11, 1)
        )
        result = ShipmentService.load(shipment.id, self.carrier_user, container_no='MSKU1234567')
        assert result.status == 'loaded'
        assert result.container_no == 'MSKU1234567'

    def test_issue_bl_by_carrier_success(self):
        shipment = ShipmentService.create_shipment(
            user=self.exporter, contract_id=self.contract.id,
            carrier_id=self.carrier_company.id,
            port_of_loading='Shanghai', port_of_discharge='Los Angeles'
        )
        ShipmentService.book(shipment.id, self.carrier_user, booking_no='BK001', vessel_name='V', etd=date(2026, 10, 1), eta=date(2026, 11, 1))
        ShipmentService.load(shipment.id, self.carrier_user)
        result = ShipmentService.issue_bl(shipment.id, self.carrier_user, bl_no='B/L NO.123456')
        assert result.status == 'shipped'
        assert result.bl_no == 'B/L NO.123456'

    def test_arrive_by_carrier_success(self):
        shipment = ShipmentService.create_shipment(
            user=self.exporter, contract_id=self.contract.id,
            carrier_id=self.carrier_company.id,
            port_of_loading='Shanghai', port_of_discharge='Los Angeles'
        )
        ShipmentService.book(shipment.id, self.carrier_user, booking_no='BK001', vessel_name='V', etd=date(2026, 10, 1), eta=date(2026, 11, 1))
        ShipmentService.load(shipment.id, self.carrier_user)
        ShipmentService.issue_bl(shipment.id, self.carrier_user, bl_no='BL001')
        result = ShipmentService.arrive(shipment.id, self.carrier_user)
        assert result.status == 'arrived'
        assert result.arrived_at is not None

    def test_cancel_draft_by_exporter(self):
        shipment = ShipmentService.create_shipment(
            user=self.exporter, contract_id=self.contract.id,
            carrier_id=self.carrier_company.id,
            port_of_loading='Shanghai', port_of_discharge='Los Angeles'
        )
        result = ShipmentService.cancel(shipment.id, self.exporter, reason='不需要了')
        assert result.status == 'cancelled'

    def test_cancel_loaded_rejected(self):
        shipment = ShipmentService.create_shipment(
            user=self.exporter, contract_id=self.contract.id,
            carrier_id=self.carrier_company.id,
            port_of_loading='Shanghai', port_of_discharge='Los Angeles'
        )
        ShipmentService.book(shipment.id, self.carrier_user, booking_no='BK001', vessel_name='V', etd=date(2026, 10, 1), eta=date(2026, 11, 1))
        ShipmentService.load(shipment.id, self.carrier_user)
        with pytest.raises(ValueError, match='订单状态不允许取消'):
            ShipmentService.cancel(shipment.id, self.exporter)
```

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest apps/transactions/tests/test_shipment_services.py -v`
预期：FAIL

- [ ] **步骤 3：实现 ShipmentService**

在 `apps/transactions/services.py` 末尾添加：

```python
from apps.transactions.models import Shipment


# 贸易术语运费率表
FREIGHT_RATES = {
    'FOB': Decimal('0'),
    'CFR': Decimal('0.03'),
    'CIF': Decimal('0.03'),
    'EXW': Decimal('0'),
    'FCA': Decimal('0'),
    'CPT': Decimal('0.03'),
    'CIP': Decimal('0.03'),
    'DAP': Decimal('0.03'),
    'DDP': Decimal('0.03'),
}


class ShipmentService:
    """货运服务"""

    @staticmethod
    def calculate_freight(contract_id):
        """根据贸易术语计算运费"""
        contract = Contract.objects.get(id=contract_id)
        rate = FREIGHT_RATES.get(contract.trade_term, Decimal('0'))
        return contract.total_amount * rate

    @staticmethod
    def create_shipment(user, contract_id, carrier_id, **kwargs):
        """出口商创建货运订单"""
        current_role = RoleService.get_current_role(user)
        if not current_role or current_role.role.code != 'exporter':
            raise ValueError('只有出口商角色才能创建货运订单')

        contract = Contract.objects.get(id=contract_id)
        if contract.transaction.seller_id != current_role.company_id:
            raise ValueError('只能为自己的出口合同创建货运订单')

        if contract.status != 'effective':
            raise ValueError('合同未生效，无法创建货运订单')

        carrier = Company.objects.get(id=carrier_id)
        freight_amount = ShipmentService.calculate_freight(contract_id)

        return Shipment.objects.create(
            contract=contract,
            shipper=current_role.company,
            carrier=carrier,
            freight_amount=freight_amount,
            created_by=user,
            **kwargs
        )

    @staticmethod
    def book(shipment_id, user, booking_no, vessel_name, etd, eta):
        """货运公司确认订舱"""
        current_role = RoleService.get_current_role(user)
        if not current_role or current_role.role.code != 'shipping':
            raise ValueError('只有货运公司角色才能订舱')

        shipment = Shipment.objects.get(id=shipment_id)
        if shipment.carrier_id != current_role.company_id:
            raise ValueError('只能订舱自己公司的货运订单')

        if shipment.status != 'draft':
            raise ValueError(f'订单状态不允许订舱: {shipment.get_status_display()}')

        shipment.status = 'booked'
        shipment.booking_no = booking_no
        shipment.vessel_name = vessel_name
        shipment.etd = etd
        shipment.eta = eta
        shipment.booked_at = timezone.now()
        shipment.save()

        TransactionService.log_transaction(
            shipment.contract.transaction, user, 'shipment_booked',
            {'shipment_no': shipment.shipment_no, 'booking_no': booking_no}
        )
        return shipment

    @staticmethod
    def load(shipment_id, user, container_no=''):
        """货运公司确认装船"""
        current_role = RoleService.get_current_role(user)
        if not current_role or current_role.role.code != 'shipping':
            raise ValueError('只有货运公司角色才能确认装船')

        shipment = Shipment.objects.get(id=shipment_id)
        if shipment.carrier_id != current_role.company_id:
            raise ValueError('只能确认自己公司的货运订单')

        if shipment.status != 'booked':
            raise ValueError(f'订单状态不允许装船: {shipment.get_status_display()}')

        shipment.status = 'loaded'
        shipment.container_no = container_no
        shipment.loaded_at = timezone.now()
        shipment.save()

        TransactionService.log_transaction(
            shipment.contract.transaction, user, 'shipment_loaded',
            {'shipment_no': shipment.shipment_no, 'container_no': container_no}
        )
        return shipment

    @staticmethod
    def issue_bl(shipment_id, user, bl_no):
        """货运公司签发提单"""
        current_role = RoleService.get_current_role(user)
        if not current_role or current_role.role.code != 'shipping':
            raise ValueError('只有货运公司角色才能签发提单')

        shipment = Shipment.objects.get(id=shipment_id)
        if shipment.carrier_id != current_role.company_id:
            raise ValueError('只能为自己公司的货运订单签发提单')

        if shipment.status != 'loaded':
            raise ValueError(f'订单状态不允许签发提单: {shipment.get_status_display()}')

        shipment.status = 'shipped'
        shipment.bl_no = bl_no
        shipment.shipped_at = timezone.now()
        shipment.save()

        TransactionService.log_transaction(
            shipment.contract.transaction, user, 'shipment_bl_issued',
            {'shipment_no': shipment.shipment_no, 'bl_no': bl_no}
        )
        return shipment

    @staticmethod
    def arrive(shipment_id, user):
        """货运公司确认到港"""
        current_role = RoleService.get_current_role(user)
        if not current_role or current_role.role.code != 'shipping':
            raise ValueError('只有货运公司角色才能确认到港')

        shipment = Shipment.objects.get(id=shipment_id)
        if shipment.carrier_id != current_role.company_id:
            raise ValueError('只能确认自己公司的货运订单')

        if shipment.status != 'shipped':
            raise ValueError(f'订单状态不允许确认到港: {shipment.get_status_display()}')

        shipment.status = 'arrived'
        shipment.arrived_at = timezone.now()
        shipment.save()

        TransactionService.log_transaction(
            shipment.contract.transaction, user, 'shipment_arrived',
            {'shipment_no': shipment.shipment_no}
        )
        return shipment

    @staticmethod
    def cancel(shipment_id, user, reason=''):
        """取消货运订单"""
        current_role = RoleService.get_current_role(user)
        if not current_role:
            raise ValueError('请先激活一个角色')

        shipment = Shipment.objects.get(id=shipment_id)
        company_id = current_role.company_id

        if shipment.status not in ('draft', 'booked'):
            raise ValueError(f'订单状态不允许取消: {shipment.get_status_display()}')

        if shipment.status == 'draft':
            if current_role.role.code != 'exporter' or company_id != shipment.shipper_id:
                raise ValueError('草稿订单只能由出口商取消')
        elif shipment.status == 'booked':
            is_shipper = current_role.role.code == 'exporter' and company_id == shipment.shipper_id
            is_carrier = current_role.role.code == 'shipping' and company_id == shipment.carrier_id
            if not (is_shipper or is_carrier):
                raise ValueError('已订舱订单只能由出口商或货运公司取消')

        shipment.status = 'cancelled'
        shipment.save()

        TransactionService.log_transaction(
            shipment.contract.transaction, user, 'shipment_cancelled',
            {'shipment_no': shipment.shipment_no, 'reason': reason}
        )
        return shipment
```

同时在文件顶部 import 添加：
```python
from apps.transactions.models import PurchaseOrder, Shipment
```

注意：如果之前已添加 `PurchaseOrder`，改为 `from apps.transactions.models import PurchaseOrder, Shipment`。

- [ ] **步骤 4：运行测试验证通过**

运行：`pytest apps/transactions/tests/test_shipment_services.py -v`
预期：全部 PASS

- [ ] **步骤 5：Commit**

```bash
git add apps/transactions/services.py apps/transactions/tests/test_shipment_services.py
git commit -m "feat(transactions): implement ShipmentService with freight calculation"
```

---

### 任务 4：实现 InsuranceService

**文件：**
- 修改：`apps/transactions/services.py`
- 创建：`apps/transactions/tests/test_insurance_services.py`

- [ ] **步骤 1：编写 InsuranceService 测试**

创建 `apps/transactions/tests/test_insurance_services.py`：

```python
import pytest
from django.test import TestCase
from datetime import date
from decimal import Decimal
from apps.transactions.models import Transaction, Contract, InsurancePolicy
from apps.transactions.services import InsuranceService
from apps.users.models import User
from apps.roles.services import CompanyService
from apps.roles.models import TradeRole, UserCompanyRole
from apps.core.models import Country


def get_or_create_country():
    country, _ = Country.objects.get_or_create(
        code='CN', defaults={'name': '中国', 'name_en': 'China', 'phone_code': '86'}
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
    UserCompanyRole.objects.get_or_create(
        user=user, company=company, role=role,
        defaults={'status': 'active', 'is_active': True}
    )


def create_effective_contract(seller_company, buyer_company, seller_user):
    transaction = Transaction.objects.create(
        buyer=buyer_company, seller=seller_company,
        product_id=1, quantity=1000, unit_price=10.00,
        status='in_progress', created_by=seller_user
    )
    contract = Contract.objects.create(
        contract_no=f'SC{Transaction.objects.count()+1:04d}',
        transaction=transaction,
        trade_term='CIF', payment_term='L/C at sight',
        delivery_time=date(2026, 12, 31),
        port_of_loading='Shanghai', port_of_discharge='Los Angeles',
        product_name='Test Product', product_spec='Spec',
        quantity=1000, unit='pcs', unit_price=10.00,
        total_amount=10000.00, currency='USD', status='effective'
    )
    return contract


class InsuranceServiceTest(TestCase):
    def setUp(self):
        from django.core.management import call_command
        call_command('init_trade_roles')

        self.exporter = User.objects.create_user(username='is_exp', password='testpass', email='ise@test.com')
        self.insurer_user = User.objects.create_user(username='is_ins', password='testpass', email='isi@test.com')
        self.buyer_user = User.objects.create_user(username='is_buy', password='testpass', email='isb@test.com')
        self.exporter_company = create_company_for_user(self.exporter, '_IS出口商')
        self.insurer_company = create_company_for_user(self.insurer_user, '_IS保险公司')
        self.buyer_company = create_company_for_user(self.buyer_user, '_IS买方')

        setup_role(self.exporter, self.exporter_company, 'exporter')
        setup_role(self.insurer_user, self.insurer_company, 'insurance')
        self.contract = create_effective_contract(
            self.exporter_company, self.buyer_company, self.exporter
        )

    def test_calculate_premium_all_risk(self):
        """一切险：0.8%"""
        premium = InsuranceService.calculate_premium(Decimal('11000.00'), 'all_risk')
        assert premium == Decimal('88.00')

    def test_calculate_premium_fpa(self):
        """平安险：0.3%"""
        premium = InsuranceService.calculate_premium(Decimal('11000.00'), 'fpa')
        assert premium == Decimal('33.00')

    def test_calculate_premium_wa(self):
        """水渍险：0.5%"""
        premium = InsuranceService.calculate_premium(Decimal('11000.00'), 'wa')
        assert premium == Decimal('55.00')

    def test_create_policy_success(self):
        policy = InsuranceService.create_policy(
            user=self.exporter,
            contract_id=self.contract.id,
            insurer_id=self.insurer_company.id,
            coverage_type='all_risk',
            cargo_description='1000件棉质T恤'
        )
        assert policy.insured == self.exporter_company
        assert policy.insurer == self.insurer_company
        assert policy.status == 'applied'
        assert policy.premium == Decimal('88.00')  # 11000 * 0.8%
        assert policy.insured_amount == Decimal('11000.00')  # 10000 * 110%

    def test_create_policy_non_exporter_rejected(self):
        with pytest.raises(ValueError, match='只有出口商角色才能投保'):
            InsuranceService.create_policy(
                user=self.insurer_user,
                contract_id=self.contract.id,
                insurer_id=self.insurer_company.id,
                coverage_type='all_risk',
                cargo_description='Test'
            )

    def test_underwrite_by_insurer_success(self):
        policy = InsuranceService.create_policy(
            user=self.exporter, contract_id=self.contract.id,
            insurer_id=self.insurer_company.id,
            coverage_type='all_risk', cargo_description='Test'
        )
        result = InsuranceService.underwrite(policy.id, self.insurer_user)
        assert result.status == 'underwritten'
        assert result.underwritten_at is not None

    def test_underwrite_by_exporter_rejected(self):
        policy = InsuranceService.create_policy(
            user=self.exporter, contract_id=self.contract.id,
            insurer_id=self.insurer_company.id,
            coverage_type='all_risk', cargo_description='Test'
        )
        with pytest.raises(ValueError, match='只有保险公司角色才能承保'):
            InsuranceService.underwrite(policy.id, self.exporter)

    def test_issue_by_insurer_success(self):
        policy = InsuranceService.create_policy(
            user=self.exporter, contract_id=self.contract.id,
            insurer_id=self.insurer_company.id,
            coverage_type='all_risk', cargo_description='Test'
        )
        InsuranceService.underwrite(policy.id, self.insurer_user)
        result = InsuranceService.issue(policy.id, self.insurer_user)
        assert result.status == 'issued'
        assert result.issued_at is not None

    def test_cancel_by_exporter(self):
        policy = InsuranceService.create_policy(
            user=self.exporter, contract_id=self.contract.id,
            insurer_id=self.insurer_company.id,
            coverage_type='all_risk', cargo_description='Test'
        )
        result = InsuranceService.cancel(policy.id, self.exporter, reason='不需要了')
        assert result.status == 'cancelled'

    def test_cancel_issued_rejected(self):
        policy = InsuranceService.create_policy(
            user=self.exporter, contract_id=self.contract.id,
            insurer_id=self.insurer_company.id,
            coverage_type='all_risk', cargo_description='Test'
        )
        InsuranceService.underwrite(policy.id, self.insurer_user)
        InsuranceService.issue(policy.id, self.insurer_user)
        with pytest.raises(ValueError, match='已签发的保单不能取消'):
            InsuranceService.cancel(policy.id, self.exporter)
```

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest apps/transactions/tests/test_insurance_services.py -v`
预期：FAIL

- [ ] **步骤 3：实现 InsuranceService**

在 `apps/transactions/services.py` 末尾添加：

```python
from apps.transactions.models import InsurancePolicy


# 保险费率表
INSURANCE_RATES = {
    'fpa': Decimal('0.003'),      # 平安险 0.3%
    'wa': Decimal('0.005'),       # 水渍险 0.5%
    'all_risk': Decimal('0.008'), # 一切险 0.8%
}

# CIF 惯例加成比例
INSURANCE_MARKUP = Decimal('1.10')  # 110%


class InsuranceService:
    """保险服务"""

    @staticmethod
    def calculate_premium(insured_amount, coverage_type):
        """保费精算"""
        rate = INSURANCE_RATES.get(coverage_type, Decimal('0.008'))
        return insured_amount * rate

    @staticmethod
    def create_policy(user, contract_id, insurer_id, coverage_type='all_risk', **kwargs):
        """出口商投保"""
        current_role = RoleService.get_current_role(user)
        if not current_role or current_role.role.code != 'exporter':
            raise ValueError('只有出口商角色才能投保')

        contract = Contract.objects.get(id=contract_id)
        if contract.transaction.seller_id != current_role.company_id:
            raise ValueError('只能为自己的出口合同投保')

        if contract.status != 'effective':
            raise ValueError('合同未生效，无法投保')

        insurer = Company.objects.get(id=insurer_id)

        # 投保金额 = 合同金额 × 110%
        insured_amount = contract.total_amount * INSURANCE_MARKUP
        premium = InsuranceService.calculate_premium(insured_amount, coverage_type)

        return InsurancePolicy.objects.create(
            contract=contract,
            insured=current_role.company,
            insurer=insurer,
            insured_amount=insured_amount,
            premium=premium,
            coverage_type=coverage_type,
            created_by=user,
            **kwargs
        )

    @staticmethod
    def underwrite(policy_id, user):
        """保险公司审核承保"""
        current_role = RoleService.get_current_role(user)
        if not current_role or current_role.role.code != 'insurance':
            raise ValueError('只有保险公司角色才能承保')

        policy = InsurancePolicy.objects.get(id=policy_id)
        if policy.insurer_id != current_role.company_id:
            raise ValueError('只能承保自己公司收到的保单')

        if policy.status != 'applied':
            raise ValueError(f'保单状态不允许承保: {policy.get_status_display()}')

        policy.status = 'underwritten'
        policy.underwritten_at = timezone.now()
        policy.save()

        TransactionService.log_transaction(
            policy.contract.transaction, user, 'insurance_underwritten',
            {'policy_no': policy.policy_no}
        )
        return policy

    @staticmethod
    def issue(policy_id, user):
        """保险公司签发保单"""
        current_role = RoleService.get_current_role(user)
        if not current_role or current_role.role.code != 'insurance':
            raise ValueError('只有保险公司角色才能签发保单')

        policy = InsurancePolicy.objects.get(id=policy_id)
        if policy.insurer_id != current_role.company_id:
            raise ValueError('只能签发自己公司的保单')

        if policy.status != 'underwritten':
            raise ValueError(f'保单状态不允许签发: {policy.get_status_display()}')

        policy.status = 'issued'
        policy.issued_at = timezone.now()
        policy.save()

        TransactionService.log_transaction(
            policy.contract.transaction, user, 'insurance_issued',
            {'policy_no': policy.policy_no}
        )
        return policy

    @staticmethod
    def cancel(policy_id, user, reason=''):
        """取消保单"""
        current_role = RoleService.get_current_role(user)
        if not current_role:
            raise ValueError('请先激活一个角色')

        policy = InsurancePolicy.objects.get(id=policy_id)
        company_id = current_role.company_id

        if policy.status == 'issued':
            raise ValueError('已签发的保单不能取消')

        if policy.status not in ('applied', 'underwritten'):
            raise ValueError(f'保单状态不允许取消: {policy.get_status_display()}')

        if policy.status == 'applied':
            if current_role.role.code != 'exporter' or company_id != policy.insured_id:
                raise ValueError('已投保保单只能由投保人取消')
        elif policy.status == 'underwritten':
            is_insured = current_role.role.code == 'exporter' and company_id == policy.insured_id
            is_insurer = current_role.role.code == 'insurance' and company_id == policy.insurer_id
            if not (is_insured or is_insurer):
                raise ValueError('已承保保单只能由投保人或保险公司取消')

        policy.status = 'cancelled'
        policy.save()

        TransactionService.log_transaction(
            policy.contract.transaction, user, 'insurance_cancelled',
            {'policy_no': policy.policy_no, 'reason': reason}
        )
        return policy
```

同时在文件顶部 import 更新：
```python
from apps.transactions.models import PurchaseOrder, Shipment, InsurancePolicy
```

- [ ] **步骤 4：运行测试验证通过**

运行：`pytest apps/transactions/tests/test_insurance_services.py -v`
预期：全部 PASS

- [ ] **步骤 5：Commit**

```bash
git add apps/transactions/services.py apps/transactions/tests/test_insurance_services.py
git commit -m "feat(transactions): implement InsuranceService with premium calculation"
```

---

### 任务 5：实现序列化器、API 视图和路由

**文件：**
- 修改：`apps/transactions/serializers.py`
- 修改：`apps/transactions/views.py`
- 修改：`apps/transactions/urls.py`
- 创建：`apps/transactions/tests/test_shipment_insurance_api.py`

- [ ] **步骤 1：添加序列化器**

在 `apps/transactions/serializers.py` 顶部 import 添加 `Shipment, InsurancePolicy`：

```python
from apps.transactions.models import (
    Transaction, InquiryMessage, Contract, ContractSignature,
    ContractAmendment, LetterOfCredit, LcAmendment, BankOperation,
    PurchaseOrder, Shipment, InsurancePolicy
)
```

在文件末尾添加：

```python
class ShipmentSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    shipper_name = serializers.CharField(source='shipper.name', read_only=True)
    carrier_name = serializers.CharField(source='carrier.name', read_only=True)
    contract_no = serializers.CharField(source='contract.contract_no', read_only=True)

    class Meta:
        model = Shipment
        fields = [
            'id', 'shipment_no', 'contract', 'contract_no',
            'shipper', 'shipper_name', 'carrier', 'carrier_name',
            'booking_no', 'bl_no', 'vessel_name',
            'port_of_loading', 'port_of_discharge',
            'etd', 'eta', 'container_no',
            'freight_amount', 'freight_currency',
            'status', 'status_display', 'notes',
            'created_by', 'booked_at', 'loaded_at', 'shipped_at', 'arrived_at',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'shipment_no', 'created_by',
            'booked_at', 'loaded_at', 'shipped_at', 'arrived_at',
            'created_at', 'updated_at'
        ]


class CreateShipmentSerializer(serializers.Serializer):
    contract_id = serializers.IntegerField(min_value=1)
    carrier_id = serializers.IntegerField(min_value=1)
    port_of_loading = serializers.CharField(max_length=100)
    port_of_discharge = serializers.CharField(max_length=100)
    notes = serializers.CharField(required=False, allow_blank=True)


class InsurancePolicySerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    coverage_type_display = serializers.CharField(source='get_coverage_type_display', read_only=True)
    insured_name = serializers.CharField(source='insured.name', read_only=True)
    insurer_name = serializers.CharField(source='insurer.name', read_only=True)
    contract_no = serializers.CharField(source='contract.contract_no', read_only=True)

    class Meta:
        model = InsurancePolicy
        fields = [
            'id', 'policy_no', 'contract', 'contract_no', 'shipment',
            'insured', 'insured_name', 'insurer', 'insurer_name',
            'cargo_description', 'insured_amount',
            'premium', 'premium_currency', 'coverage_type', 'coverage_type_display',
            'status', 'status_display', 'notes',
            'created_by', 'underwritten_at', 'issued_at',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'policy_no', 'created_by', 'insured_amount', 'premium',
            'underwritten_at', 'issued_at',
            'created_at', 'updated_at'
        ]


class CreateInsurancePolicySerializer(serializers.Serializer):
    contract_id = serializers.IntegerField(min_value=1)
    insurer_id = serializers.IntegerField(min_value=1)
    coverage_type = serializers.ChoiceField(
        choices=['fpa', 'wa', 'all_risk'], default='all_risk'
    )
    cargo_description = serializers.CharField()
    notes = serializers.CharField(required=False, allow_blank=True)
```

- [ ] **步骤 2：添加 ViewSet**

在 `apps/transactions/views.py` 顶部 import 更新：

```python
from apps.transactions.models import Transaction, InquiryMessage, Contract, PurchaseOrder, Shipment, InsurancePolicy
from apps.transactions.serializers import (
    TransactionSerializer, InquiryMessageSerializer, ContractSerializer,
    PurchaseOrderSerializer, CreatePurchaseOrderSerializer,
    ShipmentSerializer, CreateShipmentSerializer,
    InsurancePolicySerializer, CreateInsurancePolicySerializer
)
from apps.transactions.services import TransactionService, PurchaseOrderService, ShipmentService, InsuranceService
```

在文件末尾添加：

```python
class ShipmentViewSet(viewsets.ModelViewSet):
    serializer_class = ShipmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        current_role = RoleService.get_current_role(user)
        if not current_role or not current_role.company:
            return Shipment.objects.none()
        company = current_role.company
        return Shipment.objects.filter(shipper=company) | Shipment.objects.filter(carrier=company)

    def list(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_queryset(), many=True)
        return Response({'code': 0, 'message': 'success', 'data': serializer.data})

    def create(self, request, *args, **kwargs):
        serializer = CreateShipmentSerializer(data=request.data)
        if serializer.is_valid():
            try:
                shipment = ShipmentService.create_shipment(user=request.user, **serializer.validated_data)
                return Response({
                    'code': 0, 'message': '货运订单创建成功',
                    'data': ShipmentSerializer(shipment).data
                }, status=status.HTTP_201_CREATED)
            except Exception as e:
                return Response({'code': 5005, 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'code': 3002, 'message': '参数格式错误', 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, *args, **kwargs):
        return Response({'code': 0, 'message': 'success', 'data': self.get_serializer(self.get_object()).data})

    @action(detail=True, methods=['post'])
    def book(self, request, pk=None):
        try:
            result = ShipmentService.book(
                self.get_object().id, request.user,
                booking_no=request.data['booking_no'],
                vessel_name=request.data['vessel_name'],
                etd=request.data.get('etd'),
                eta=request.data.get('eta')
            )
            return Response({'code': 0, 'message': '订舱成功', 'data': ShipmentSerializer(result).data})
        except Exception as e:
            return Response({'code': 5005, 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def load(self, request, pk=None):
        try:
            result = ShipmentService.load(
                self.get_object().id, request.user,
                container_no=request.data.get('container_no', '')
            )
            return Response({'code': 0, 'message': '装船确认', 'data': ShipmentSerializer(result).data})
        except Exception as e:
            return Response({'code': 5005, 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def issue_bl(self, request, pk=None):
        try:
            result = ShipmentService.issue_bl(
                self.get_object().id, request.user,
                bl_no=request.data['bl_no']
            )
            return Response({'code': 0, 'message': '提单已签发', 'data': ShipmentSerializer(result).data})
        except Exception as e:
            return Response({'code': 5005, 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def arrive(self, request, pk=None):
        try:
            result = ShipmentService.arrive(self.get_object().id, request.user)
            return Response({'code': 0, 'message': '已确认到港', 'data': ShipmentSerializer(result).data})
        except Exception as e:
            return Response({'code': 5005, 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        try:
            result = ShipmentService.cancel(
                self.get_object().id, request.user,
                reason=request.data.get('reason', '')
            )
            return Response({'code': 0, 'message': '已取消', 'data': ShipmentSerializer(result).data})
        except Exception as e:
            return Response({'code': 5005, 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class InsurancePolicyViewSet(viewsets.ModelViewSet):
    serializer_class = InsurancePolicySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        current_role = RoleService.get_current_role(user)
        if not current_role or not current_role.company:
            return InsurancePolicy.objects.none()
        company = current_role.company
        return InsurancePolicy.objects.filter(insured=company) | InsurancePolicy.objects.filter(insurer=company)

    def list(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_queryset(), many=True)
        return Response({'code': 0, 'message': 'success', 'data': serializer.data})

    def create(self, request, *args, **kwargs):
        serializer = CreateInsurancePolicySerializer(data=request.data)
        if serializer.is_valid():
            try:
                policy = InsuranceService.create_policy(user=request.user, **serializer.validated_data)
                return Response({
                    'code': 0, 'message': '投保成功',
                    'data': InsurancePolicySerializer(policy).data
                }, status=status.HTTP_201_CREATED)
            except Exception as e:
                return Response({'code': 5005, 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'code': 3002, 'message': '参数格式错误', 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, *args, **kwargs):
        return Response({'code': 0, 'message': 'success', 'data': self.get_serializer(self.get_object()).data})

    @action(detail=True, methods=['post'])
    def underwrite(self, request, pk=None):
        try:
            result = InsuranceService.underwrite(self.get_object().id, request.user)
            return Response({'code': 0, 'message': '承保成功', 'data': InsurancePolicySerializer(result).data})
        except Exception as e:
            return Response({'code': 5005, 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def issue(self, request, pk=None):
        try:
            result = InsuranceService.issue(self.get_object().id, request.user)
            return Response({'code': 0, 'message': '保单已签发', 'data': InsurancePolicySerializer(result).data})
        except Exception as e:
            return Response({'code': 5005, 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        try:
            result = InsuranceService.cancel(
                self.get_object().id, request.user,
                reason=request.data.get('reason', '')
            )
            return Response({'code': 0, 'message': '已取消', 'data': InsurancePolicySerializer(result).data})
        except Exception as e:
            return Response({'code': 5005, 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)
```

- [ ] **步骤 3：更新路由**

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
router.register(r'shipments', views.ShipmentViewSet, basename='shipment')
router.register(r'insurance-policies', views.InsurancePolicyViewSet, basename='insurancepolicy')

urlpatterns = router.urls
```

- [ ] **步骤 4：创建 API 测试**

创建 `apps/transactions/tests/test_shipment_insurance_api.py`（包含公共辅助函数 + 8 个测试覆盖两个 ViewSet 的核心端点）：

```python
import pytest
from decimal import Decimal
from datetime import date
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from apps.transactions.models import Transaction, Contract, Shipment, InsurancePolicy
from apps.transactions.services import ShipmentService
from apps.users.models import User
from apps.roles.services import CompanyService
from apps.roles.models import TradeRole, UserCompanyRole
from apps.core.models import Country


def get_or_create_country():
    country, _ = Country.objects.get_or_create(
        code='CN', defaults={'name': '中国', 'name_en': 'China', 'phone_code': '86'}
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
    UserCompanyRole.objects.get_or_create(
        user=user, company=company, role=role,
        defaults={'status': 'active', 'is_active': True}
    )


class ShipmentInsuranceAPITest(TestCase):
    def setUp(self):
        from django.core.management import call_command
        call_command('init_trade_roles')

        self.exporter = User.objects.create_user(username='si_exp', password='testpass', email='sie@test.com')
        self.carrier_user = User.objects.create_user(username='si_car', password='testpass', email='sic@test.com')
        self.insurer_user = User.objects.create_user(username='si_ins', password='testpass', email='sii@test.com')
        self.buyer_user = User.objects.create_user(username='si_buy', password='testpass', email='sib@test.com')
        self.exporter_company = create_company_for_user(self.exporter, '_SI出口商')
        self.carrier_company = create_company_for_user(self.carrier_user, '_SI货运公司')
        self.insurer_company = create_company_for_user(self.insurer_user, '_SI保险公司')
        self.buyer_company = create_company_for_user(self.buyer_user, '_SI买方')

        setup_role(self.exporter, self.exporter_company, 'exporter')
        setup_role(self.carrier_user, self.carrier_company, 'shipping')
        setup_role(self.insurer_user, self.insurer_company, 'insurance')

        self.transaction = Transaction.objects.create(
            buyer=self.buyer_company, seller=self.exporter_company,
            product_id=1, quantity=1000, unit_price=10.00,
            status='in_progress', created_by=self.exporter
        )
        self.contract = Contract.objects.create(
            contract_no='SI-TEST-001', transaction=self.transaction,
            trade_term='CIF', payment_term='L/C at sight',
            delivery_time=date(2026, 12, 31),
            port_of_loading='Shanghai', port_of_discharge='Los Angeles',
            product_name='Test', product_spec='',
            quantity=1000, unit='pcs', unit_price=10.00,
            total_amount=10000.00, currency='USD', status='effective'
        )
        self.client = APIClient()

    def test_create_shipment(self):
        self.client.force_authenticate(user=self.exporter)
        url = reverse('transactions:shipment-list')
        response = self.client.post(url, {
            'contract_id': self.contract.id,
            'carrier_id': self.carrier_company.id,
            'port_of_loading': 'Shanghai',
            'port_of_discharge': 'Los Angeles'
        }, format='json')
        assert response.status_code == 201
        assert response.json()['code'] == 0

    def test_shipment_book_flow(self):
        shipment = ShipmentService.create_shipment(
            user=self.exporter, contract_id=self.contract.id,
            carrier_id=self.carrier_company.id,
            port_of_loading='Shanghai', port_of_discharge='Los Angeles'
        )
        self.client.force_authenticate(user=self.carrier_user)
        url = reverse('transactions:shipment-book', kwargs={'pk': shipment.id})
        response = self.client.post(url, {
            'booking_no': 'BK001', 'vessel_name': 'OOCL',
            'etd': '2026-10-01', 'eta': '2026-11-01'
        }, format='json')
        assert response.status_code == 200
        shipment.refresh_from_db()
        assert shipment.status == 'booked'

    def test_shipment_full_lifecycle(self):
        shipment = ShipmentService.create_shipment(
            user=self.exporter, contract_id=self.contract.id,
            carrier_id=self.carrier_company.id,
            port_of_loading='Shanghai', port_of_discharge='Los Angeles'
        )
        self.client.force_authenticate(user=self.carrier_user)
        # Book
        self.client.post(reverse('transactions:shipment-book', kwargs={'pk': shipment.id}), {
            'booking_no': 'BK001', 'vessel_name': 'OOCL',
            'etd': '2026-10-01', 'eta': '2026-11-01'
        }, format='json')
        # Load
        self.client.post(reverse('transactions:shipment-load', kwargs={'pk': shipment.id}), {
            'container_no': 'MSKU1234567'
        }, format='json')
        # Issue BL
        self.client.post(reverse('transactions:shipment-issue-bl', kwargs={'pk': shipment.id}), {
            'bl_no': 'BL123456'
        }, format='json')
        # Arrive
        resp = self.client.post(reverse('transactions:shipment-arrive', kwargs={'pk': shipment.id}))
        assert resp.status_code == 200
        shipment.refresh_from_db()
        assert shipment.status == 'arrived'

    def test_create_insurance_policy(self):
        self.client.force_authenticate(user=self.exporter)
        url = reverse('transactions:insurancepolicy-list')
        response = self.client.post(url, {
            'contract_id': self.contract.id,
            'insurer_id': self.insurer_company.id,
            'coverage_type': 'all_risk',
            'cargo_description': '1000件棉质T恤'
        }, format='json')
        assert response.status_code == 201
        assert response.json()['code'] == 0

    def test_insurance_full_lifecycle(self):
        self.client.force_authenticate(user=self.exporter)
        # Create
        resp = self.client.post(reverse('transactions:insurancepolicy-list'), {
            'contract_id': self.contract.id,
            'insurer_id': self.insurer_company.id,
            'coverage_type': 'all_risk',
            'cargo_description': 'Test'
        }, format='json')
        policy_id = resp.json()['data']['id']
        # Underwrite
        self.client.force_authenticate(user=self.insurer_user)
        resp = self.client.post(reverse('transactions:insurancepolicy-underwrite', kwargs={'pk': policy_id}))
        assert resp.status_code == 200
        # Issue
        resp = self.client.post(reverse('transactions:insurancepolicy-issue', kwargs={'pk': policy_id}))
        assert resp.status_code == 200
        policy = InsurancePolicy.objects.get(id=policy_id)
        assert policy.status == 'issued'

    def test_unauthenticated_shipment_rejected(self):
        url = reverse('transactions:shipment-list')
        response = self.client.get(url)
        assert response.status_code in (401, 403)

    def test_unauthenticated_insurance_rejected(self):
        url = reverse('transactions:insurancepolicy-list')
        response = self.client.get(url)
        assert response.status_code in (401, 403)
```

- [ ] **步骤 5：运行测试验证通过**

运行：`pytest apps/transactions/tests/test_shipment_insurance_api.py -v`
预期：全部 PASS

- [ ] **步骤 6：Commit**

```bash
git add apps/transactions/serializers.py apps/transactions/views.py apps/transactions/urls.py apps/transactions/tests/test_shipment_insurance_api.py
git commit -m "feat(transactions): add Shipment and InsurancePolicy API endpoints"
```

---

### 任务 6：配置 Admin + 最终验证

**文件：**
- 修改：`apps/transactions/admin.py`

- [ ] **步骤 1：添加 Admin 配置**

在 `apps/transactions/admin.py` 顶部 import 添加 `Shipment, InsurancePolicy`：

```python
from apps.transactions.models import (
    Transaction, InquiryMessage, Contract,
    ContractSignature, TransactionLog, ContractAmendment,
    LetterOfCredit, LcAmendment, BankOperation,
    PurchaseOrder, Shipment, InsurancePolicy
)
```

在文件末尾添加：

```python
@admin.register(Shipment)
class ShipmentAdmin(admin.ModelAdmin):
    list_display = [
        'shipment_no', 'shipper', 'carrier', 'vessel_name',
        'port_of_loading', 'port_of_discharge',
        'freight_amount', 'status', 'created_at'
    ]
    list_filter = ['status', 'freight_currency', 'created_at']
    search_fields = ['shipment_no', 'booking_no', 'bl_no', 'vessel_name']
    readonly_fields = [
        'created_at', 'updated_at', 'booked_at',
        'loaded_at', 'shipped_at', 'arrived_at'
    ]


@admin.register(InsurancePolicy)
class InsurancePolicyAdmin(admin.ModelAdmin):
    list_display = [
        'policy_no', 'insured', 'insurer',
        'insured_amount', 'premium', 'coverage_type',
        'status', 'created_at'
    ]
    list_filter = ['status', 'coverage_type', 'created_at']
    search_fields = ['policy_no', 'cargo_description']
    readonly_fields = [
        'created_at', 'updated_at',
        'underwritten_at', 'issued_at'
    ]
```

- [ ] **步骤 2：运行全部测试**

运行：
```bash
pytest apps/transactions/tests/ apps/roles/tests/ -q
python manage.py check
```

预期：全部 PASS，Django check 无致命错误

- [ ] **步骤 3：Commit**

```bash
git add apps/transactions/admin.py
git commit -m "feat(transactions): add Shipment and InsurancePolicy admin"
```

---

## 自检清单

### 规格覆盖度

| 设计章节 | 对应任务 |
|---------|---------|
| Shipment 模型 | 任务 1 |
| InsurancePolicy 模型 | 任务 2 |
| 运费计算（费率表） | 任务 3（ShipmentService.calculate_freight） |
| 保费精算（费率表） | 任务 4（InsuranceService.calculate_premium） |
| ShipmentService | 任务 3 |
| InsuranceService | 任务 4 |
| 序列化器 | 任务 5 |
| API 端点 | 任务 5 |
| Admin 配置 | 任务 6 |

### 占位符检查

- 无 TBD、TODO 等占位符
- 所有代码步骤包含完整代码

### 类型一致性检查

- Shipment 状态：draft, booked, loaded, shipped, arrived, cancelled — 一致
- InsurancePolicy 状态：applied, underwritten, issued, cancelled — 一致
- CoverageType：fpa, wa, all_risk — 费率表和服务层一致
- 服务方法签名在测试和实现中一致
- API 端点名称在 urls.py 和测试 reverse() 中一致
