# 海关报关与商检 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 在 apps/transactions 中实现 CustomsDeclaration 和 InspectionApplication 模型及服务层，支持提单签发后的出口报关和报检流程

**架构：** 在现有 transactions app 中新增 CustomsDeclaration 和 InspectionApplication 模型（均通过 FK 关联 Shipment），新增 CustomsService 和 InspectionService 处理状态流转和角色校验

**Tech Stack：** Django 3.2, DRF, pytest, Python 3.8+

---

## 文件结构

### 将要创建的文件

| 文件路径 | 职责 |
|---------|------|
| `apps/transactions/tests/test_customs_models.py` | CustomsDeclaration 模型测试 |
| `apps/transactions/tests/test_inspection_models.py` | InspectionApplication 模型测试 |
| `apps/transactions/tests/test_customs_services.py` | CustomsService 服务测试 |
| `apps/transactions/tests/test_inspection_services.py` | InspectionService 服务测试 |
| `apps/transactions/tests/test_customs_inspection_api.py` | 报关+商检 API 测试 |

### 将要修改的文件

| 文件路径 | 修改内容 |
|---------|---------|
| `apps/transactions/models.py` | 新增 CustomsDeclaration、InspectionApplication 模型 |
| `apps/transactions/services.py` | 新增 CustomsService、InspectionService |
| `apps/transactions/serializers.py` | 新增报关和商检相关序列化器 |
| `apps/transactions/views.py` | 新增 CustomsDeclarationViewSet、InspectionApplicationViewSet |
| `apps/transactions/urls.py` | 注册新的 ViewSet |
| `apps/transactions/admin.py` | 新增 CustomsDeclarationAdmin、InspectionApplicationAdmin |

---

## 公共辅助函数

以下辅助函数在多个测试文件中重复使用：

```python
import pytest
from django.test import TestCase
from datetime import date
from decimal import Decimal
from apps.transactions.models import Transaction, Contract, Shipment, CustomsDeclaration, InspectionApplication
from apps.transactions.services import ShipmentService
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


def create_shipped_shipment(seller_company, buyer_company, carrier_company, seller_user, carrier_user):
    """创建一个已签发提单的 Shipment（完整生命周期）"""
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
        product_name='Cotton T-Shirt', product_spec='100% Cotton',
        quantity=1000, unit='pcs', unit_price=10.00,
        total_amount=10000.00, currency='USD', status='effective'
    )
    shipment = ShipmentService.create_shipment(
        user=seller_user, contract_id=contract.id,
        carrier_id=carrier_company.id,
        port_of_loading='Shanghai', port_of_discharge='Los Angeles'
    )
    ShipmentService.book(
        shipment.id, carrier_user,
        booking_no='BK001', vessel_name='OOCL',
        etd=date(2026, 10, 1), eta=date(2026, 11, 1)
    )
    ShipmentService.load(shipment.id, carrier_user)
    ShipmentService.issue_bl(shipment.id, carrier_user, bl_no='BL001')
    shipment.refresh_from_db()
    return shipment
```

---

## 任务分解

### 任务 1：实现 CustomsDeclaration 模型

**文件：**
- 修改：`apps/transactions/models.py`
- 创建：`apps/transactions/tests/test_customs_models.py`

- [ ] **步骤 1：编写 CustomsDeclaration 模型测试**

创建 `apps/transactions/tests/test_customs_models.py`：

```python
import pytest
from django.test import TestCase
from datetime import date
from decimal import Decimal
from apps.transactions.models import Transaction, Contract, Shipment, CustomsDeclaration
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


class CustomsDeclarationModelTest(TestCase):
    def setUp(self):
        from django.core.management import call_command
        call_command('init_trade_roles')

        self.exporter = User.objects.create_user(username='cd_mod_exp', password='testpass', email='cde@test.com')
        self.carrier_user = User.objects.create_user(username='cd_mod_car', password='testpass', email='cdc@test.com')
        self.customs_user = User.objects.create_user(username='cd_mod_cus', password='testpass', email='cdcu@test.com')
        self.buyer_user = User.objects.create_user(username='cd_mod_buy', password='testpass', email='cdb@test.com')
        self.exporter_company = create_company_for_user(self.exporter, '_CD出口商')
        self.carrier_company = create_company_for_user(self.carrier_user, '_CD货运')
        self.customs_company = create_company_for_user(self.customs_user, '_CD海关')
        self.buyer_company = create_company_for_user(self.buyer_user, '_CD买方')

        setup_role(self.exporter, self.exporter_company, 'exporter')
        setup_role(self.carrier_user, self.carrier_company, 'shipping')

        # 创建已签发提单的货运
        transaction = Transaction.objects.create(
            buyer=self.buyer_company, seller=self.exporter_company,
            product_id=1, quantity=1000, unit_price=10.00,
            status='in_progress', created_by=self.exporter
        )
        contract = Contract.objects.create(
            contract_no='CD-TEST-001', transaction=transaction,
            trade_term='CIF', payment_term='L/C at sight',
            delivery_time=date(2026, 12, 31),
            port_of_loading='Shanghai', port_of_discharge='Los Angeles',
            product_name='T-Shirt', product_spec='Cotton',
            quantity=1000, unit='pcs', unit_price=10.00,
            total_amount=10000.00, currency='USD', status='effective'
        )
        shipment = ShipmentService.create_shipment(
            user=self.exporter, contract_id=contract.id,
            carrier_id=self.carrier_company.id,
            port_of_loading='Shanghai', port_of_discharge='Los Angeles'
        )
        ShipmentService.book(shipment.id, self.carrier_user, 'BK001', 'OOCL', date(2026, 10, 1), date(2026, 11, 1))
        ShipmentService.load(shipment.id, self.carrier_user)
        ShipmentService.issue_bl(shipment.id, self.carrier_user, bl_no='BL001')
        self.shipment = shipment

    def test_create_customs_declaration(self):
        decl = CustomsDeclaration.objects.create(
            shipment=self.shipment,
            declarant=self.exporter_company,
            customs_office=self.customs_company,
            hs_code='610910',
            goods_name='Cotton T-Shirt',
            quantity=Decimal('1000'),
            unit_value=Decimal('10.00'),
            total_value=Decimal('10000.00'),
            currency='USD',
            created_by=self.exporter
        )
        assert decl.declaration_no is not None
        assert decl.declaration_no.startswith('CD')
        assert decl.status == 'declared'
        assert str(decl) == decl.declaration_no

    def test_declaration_status_choices(self):
        valid = [c[0] for c in CustomsDeclaration.Status.choices]
        assert 'declared' in valid
        assert 'reviewing' in valid
        assert 'assessed' in valid
        assert 'cleared' in valid
        assert 'rejected' in valid
```

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest apps/transactions/tests/test_customs_models.py -v`
预期：FAIL，ImportError: cannot import name 'CustomsDeclaration'

- [ ] **步骤 3：实现 CustomsDeclaration 模型**

在 `apps/transactions/models.py` 末尾（InsurancePolicy 之后）添加：

```python
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
```

- [ ] **步骤 4：生成迁移并运行测试**

运行：
```bash
python manage.py makemigrations transactions
python manage.py migrate
pytest apps/transactions/tests/test_customs_models.py -v
```

预期：全部 PASS

- [ ] **步骤 5：Commit**

```bash
git add apps/transactions/models.py apps/transactions/migrations/ apps/transactions/tests/test_customs_models.py
git commit -m "feat(transactions): add CustomsDeclaration model"
```

---

### 任务 2：实现 InspectionApplication 模型

**文件：**
- 修改：`apps/transactions/models.py`
- 创建：`apps/transactions/tests/test_inspection_models.py`

- [ ] **步骤 1：编写 InspectionApplication 模型测试**

创建 `apps/transactions/tests/test_inspection_models.py`：

```python
import pytest
from django.test import TestCase
from datetime import date
from decimal import Decimal
from apps.transactions.models import Transaction, Contract, Shipment, InspectionApplication
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


class InspectionApplicationModelTest(TestCase):
    def setUp(self):
        from django.core.management import call_command
        call_command('init_trade_roles')

        self.exporter = User.objects.create_user(username='ia_mod_exp', password='testpass', email='iae@test.com')
        self.carrier_user = User.objects.create_user(username='ia_mod_car', password='testpass', email='iac@test.com')
        self.inspector_user = User.objects.create_user(username='ia_mod_ins', password='testpass', email='iai@test.com')
        self.buyer_user = User.objects.create_user(username='ia_mod_buy', password='testpass', email='iab@test.com')
        self.exporter_company = create_company_for_user(self.exporter, '_IA出口商')
        self.carrier_company = create_company_for_user(self.carrier_user, '_IA货运')
        self.inspector_company = create_company_for_user(self.inspector_user, '_IA商检')
        self.buyer_company = create_company_for_user(self.buyer_user, '_IA买方')

        setup_role(self.exporter, self.exporter_company, 'exporter')
        setup_role(self.carrier_user, self.carrier_company, 'shipping')

        transaction = Transaction.objects.create(
            buyer=self.buyer_company, seller=self.exporter_company,
            product_id=1, quantity=1000, unit_price=10.00,
            status='in_progress', created_by=self.exporter
        )
        contract = Contract.objects.create(
            contract_no='IA-TEST-001', transaction=transaction,
            trade_term='CIF', payment_term='L/C at sight',
            delivery_time=date(2026, 12, 31),
            port_of_loading='Shanghai', port_of_discharge='Los Angeles',
            product_name='T-Shirt', product_spec='Cotton',
            quantity=1000, unit='pcs', unit_price=10.00,
            total_amount=10000.00, currency='USD', status='effective'
        )
        shipment = ShipmentService.create_shipment(
            user=self.exporter, contract_id=contract.id,
            carrier_id=self.carrier_company.id,
            port_of_loading='Shanghai', port_of_discharge='Los Angeles'
        )
        ShipmentService.book(shipment.id, self.carrier_user, 'BK001', 'OOCL', date(2026, 10, 1), date(2026, 11, 1))
        ShipmentService.load(shipment.id, self.carrier_user)
        ShipmentService.issue_bl(shipment.id, self.carrier_user, bl_no='BL001')
        self.shipment = shipment

    def test_create_inspection_application(self):
        app = InspectionApplication.objects.create(
            shipment=self.shipment,
            applicant=self.exporter_company,
            inspector=self.inspector_company,
            product_name='Cotton T-Shirt',
            product_spec='100% Cotton',
            quantity=Decimal('1000'),
            goods_value=Decimal('10000.00'),
            inspection_type='legal',
            fee=Decimal('50.00'),
            created_by=self.exporter
        )
        assert app.application_no is not None
        assert app.application_no.startswith('IA')
        assert app.status == 'applied'
        assert str(app) == app.application_no

    def test_inspection_status_choices(self):
        valid = [c[0] for c in InspectionApplication.Status.choices]
        assert 'applied' in valid
        assert 'inspecting' in valid
        assert 'passed' in valid
        assert 'certified' in valid
        assert 'failed' in valid

    def test_inspection_type_choices(self):
        valid = [c[0] for c in InspectionApplication.InspectionType.choices]
        assert 'legal' in valid
        assert 'general' in valid
```

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest apps/transactions/tests/test_inspection_models.py -v`
预期：FAIL

- [ ] **步骤 3：实现 InspectionApplication 模型**

在 `apps/transactions/models.py` 末尾（CustomsDeclaration 之后）添加：

```python
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
```

- [ ] **步骤 4：生成迁移并运行测试**

运行：
```bash
python manage.py makemigrations transactions
python manage.py migrate
pytest apps/transactions/tests/test_inspection_models.py -v
```

预期：全部 PASS

- [ ] **步骤 5：Commit**

```bash
git add apps/transactions/models.py apps/transactions/migrations/ apps/transactions/tests/test_inspection_models.py
git commit -m "feat(transactions): add InspectionApplication model"
```

---

### 任务 3：实现 CustomsService

**文件：**
- 修改：`apps/transactions/services.py`
- 创建：`apps/transactions/tests/test_customs_services.py`

- [ ] **步骤 1：编写 CustomsService 测试**

创建 `apps/transactions/tests/test_customs_services.py`：

```python
import pytest
from django.test import TestCase
from datetime import date
from decimal import Decimal
from apps.transactions.models import Transaction, Contract, Shipment, CustomsDeclaration
from apps.transactions.services import ShipmentService, CustomsService
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
        product_name='T-Shirt', product_spec='Cotton',
        quantity=1000, unit='pcs', unit_price=10.00,
        total_amount=10000.00, currency='USD', status='effective'
    )
    return contract


class CustomsServiceTest(TestCase):
    def setUp(self):
        from django.core.management import call_command
        call_command('init_trade_roles')

        self.exporter = User.objects.create_user(username='cs_exp', password='testpass', email='cse@test.com')
        self.carrier_user = User.objects.create_user(username='cs_car', password='testpass', email='csc@test.com')
        self.customs_user = User.objects.create_user(username='cs_cus', password='testpass', email='csu@test.com')
        self.buyer_user = User.objects.create_user(username='cs_buy', password='testpass', email='csb@test.com')
        self.exporter_company = create_company_for_user(self.exporter, '_CS出口商')
        self.carrier_company = create_company_for_user(self.carrier_user, '_CS货运')
        self.customs_company = create_company_for_user(self.customs_user, '_CS海关')
        self.buyer_company = create_company_for_user(self.buyer_user, '_CS买方')

        setup_role(self.exporter, self.exporter_company, 'exporter')
        setup_role(self.carrier_user, self.carrier_company, 'shipping')
        setup_role(self.customs_user, self.customs_company, 'customs')

        contract = create_effective_contract(
            self.exporter_company, self.buyer_company, self.exporter
        )
        shipment = ShipmentService.create_shipment(
            user=self.exporter, contract_id=contract.id,
            carrier_id=self.carrier_company.id,
            port_of_loading='Shanghai', port_of_discharge='Los Angeles'
        )
        ShipmentService.book(shipment.id, self.carrier_user, 'BK001', 'OOCL', date(2026, 10, 1), date(2026, 11, 1))
        ShipmentService.load(shipment.id, self.carrier_user)
        ShipmentService.issue_bl(shipment.id, self.carrier_user, bl_no='BL001')
        self.shipment = shipment

    def test_create_declaration_success(self):
        decl = CustomsService.create_declaration(
            user=self.exporter,
            shipment_id=self.shipment.id,
            customs_office_id=self.customs_company.id,
            hs_code='610910',
            goods_name='Cotton T-Shirt',
            quantity=Decimal('1000'),
            unit_value=Decimal('10.00'),
            total_value=Decimal('10000.00'),
            currency='USD'
        )
        assert decl.declarant == self.exporter_company
        assert decl.customs_office == self.customs_company
        assert decl.status == 'declared'

    def test_create_declaration_non_exporter_rejected(self):
        with pytest.raises(ValueError, match='只有出口商角色才能申报报关'):
            CustomsService.create_declaration(
                user=self.customs_user,
                shipment_id=self.shipment.id,
                customs_office_id=self.customs_company.id,
                hs_code='610910',
                goods_name='Test',
                quantity=Decimal('1000'),
                unit_value=Decimal('10.00'),
                total_value=Decimal('10000.00')
            )

    def test_create_declaration_shipment_not_shipped_rejected(self):
        contract = create_effective_contract(
            self.exporter_company, self.buyer_company, self.exporter
        )
        shipment = ShipmentService.create_shipment(
            user=self.exporter, contract_id=contract.id,
            carrier_id=self.carrier_company.id,
            port_of_loading='Shanghai', port_of_discharge='Los Angeles'
        )
        with pytest.raises(ValueError, match='提单未签发'):
            CustomsService.create_declaration(
                user=self.exporter, shipment_id=shipment.id,
                customs_office_id=self.customs_company.id,
                hs_code='610910', goods_name='Test',
                quantity=Decimal('1000'), unit_value=Decimal('10.00'),
                total_value=Decimal('10000.00')
            )

    def test_calculate_duties_textile(self):
        duties = CustomsService.calculate_duties('610910', Decimal('10000.00'))
        assert duties['duty_rate'] == Decimal('0.10')
        assert duties['duty_amount'] == Decimal('1000.00')
        assert duties['vat_rate'] == Decimal('0.13')
        assert duties['vat_amount'] == Decimal('1430.00')  # (10000 + 1000) * 13%

    def test_calculate_duties_electronics(self):
        duties = CustomsService.calculate_duties('851712', Decimal('10000.00'))
        assert duties['duty_rate'] == Decimal('0.08')
        assert duties['duty_amount'] == Decimal('800.00')

    def test_calculate_duties_food(self):
        duties = CustomsService.calculate_duties('210690', Decimal('10000.00'))
        assert duties['duty_rate'] == Decimal('0.15')
        assert duties['vat_rate'] == Decimal('0.09')

    def test_calculate_duties_default(self):
        duties = CustomsService.calculate_duties('999999', Decimal('10000.00'))
        assert duties['duty_rate'] == Decimal('0.10')
        assert duties['vat_rate'] == Decimal('0.13')

    def test_review_by_customs_success(self):
        decl = CustomsService.create_declaration(
            user=self.exporter, shipment_id=self.shipment.id,
            customs_office_id=self.customs_company.id,
            hs_code='610910', goods_name='Test',
            quantity=Decimal('1000'), unit_value=Decimal('10.00'),
            total_value=Decimal('10000.00')
        )
        result = CustomsService.review(decl.id, self.customs_user)
        assert result.status == 'reviewing'
        assert result.reviewed_at is not None

    def test_assess_by_customs_success(self):
        decl = CustomsService.create_declaration(
            user=self.exporter, shipment_id=self.shipment.id,
            customs_office_id=self.customs_company.id,
            hs_code='610910', goods_name='Test',
            quantity=Decimal('1000'), unit_value=Decimal('10.00'),
            total_value=Decimal('10000.00')
        )
        CustomsService.review(decl.id, self.customs_user)
        result = CustomsService.assess(decl.id, self.customs_user)
        assert result.status == 'assessed'
        assert result.duty_amount == Decimal('1000.00')
        assert result.vat_amount == Decimal('1430.00')
        assert result.assessed_at is not None

    def test_clear_by_customs_success(self):
        decl = CustomsService.create_declaration(
            user=self.exporter, shipment_id=self.shipment.id,
            customs_office_id=self.customs_company.id,
            hs_code='610910', goods_name='Test',
            quantity=Decimal('1000'), unit_value=Decimal('10.00'),
            total_value=Decimal('10000.00')
        )
        CustomsService.review(decl.id, self.customs_user)
        CustomsService.assess(decl.id, self.customs_user)
        result = CustomsService.clear(decl.id, self.customs_user)
        assert result.status == 'cleared'
        assert result.cleared_at is not None

    def test_reject_by_customs_success(self):
        decl = CustomsService.create_declaration(
            user=self.exporter, shipment_id=self.shipment.id,
            customs_office_id=self.customs_company.id,
            hs_code='610910', goods_name='Test',
            quantity=Decimal('1000'), unit_value=Decimal('10.00'),
            total_value=Decimal('10000.00')
        )
        result = CustomsService.reject(decl.id, self.customs_user, reason='单据不齐全')
        assert result.status == 'rejected'
        assert result.rejected_at is not None

    def test_review_by_exporter_rejected(self):
        decl = CustomsService.create_declaration(
            user=self.exporter, shipment_id=self.shipment.id,
            customs_office_id=self.customs_company.id,
            hs_code='610910', goods_name='Test',
            quantity=Decimal('1000'), unit_value=Decimal('10.00'),
            total_value=Decimal('10000.00')
        )
        with pytest.raises(ValueError, match='只有海关角色才能审核'):
            CustomsService.review(decl.id, self.exporter)
```

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest apps/transactions/tests/test_customs_services.py -v`
预期：FAIL

- [ ] **步骤 3：实现 CustomsService**

在 `apps/transactions/services.py` 顶部 import 添加 `CustomsDeclaration`：
```python
from apps.transactions.models import PurchaseOrder, Shipment, InsurancePolicy, CustomsDeclaration
```

在文件末尾添加：

```python
# HS 编码税率表（基于前2位）
HS_DUTY_RATES = {
    '61': {'duty': Decimal('0.10'), 'vat': Decimal('0.13')},  # 纺织品
    '62': {'duty': Decimal('0.10'), 'vat': Decimal('0.13')},
    '63': {'duty': Decimal('0.10'), 'vat': Decimal('0.13')},
    '84': {'duty': Decimal('0.12'), 'vat': Decimal('0.13')},  # 机械
    '85': {'duty': Decimal('0.08'), 'vat': Decimal('0.13')},  # 电子产品
    '01': {'duty': Decimal('0.15'), 'vat': Decimal('0.09')},  # 食品
    '02': {'duty': Decimal('0.15'), 'vat': Decimal('0.09')},
    '03': {'duty': Decimal('0.15'), 'vat': Decimal('0.09')},
    '04': {'duty': Decimal('0.15'), 'vat': Decimal('0.09')},
    '05': {'duty': Decimal('0.15'), 'vat': Decimal('0.09')},
    '06': {'duty': Decimal('0.15'), 'vat': Decimal('0.09')},
    '07': {'duty': Decimal('0.15'), 'vat': Decimal('0.09')},
    '08': {'duty': Decimal('0.15'), 'vat': Decimal('0.09')},
    '09': {'duty': Decimal('0.15'), 'vat': Decimal('0.09')},
    '10': {'duty': Decimal('0.15'), 'vat': Decimal('0.09')},
    '11': {'duty': Decimal('0.15'), 'vat': Decimal('0.09')},
    '12': {'duty': Decimal('0.15'), 'vat': Decimal('0.09')},
    '13': {'duty': Decimal('0.15'), 'vat': Decimal('0.09')},
    '14': {'duty': Decimal('0.15'), 'vat': Decimal('0.09')},
    '15': {'duty': Decimal('0.15'), 'vat': Decimal('0.09')},
    '16': {'duty': Decimal('0.15'), 'vat': Decimal('0.09')},
    '17': {'duty': Decimal('0.15'), 'vat': Decimal('0.09')},
    '18': {'duty': Decimal('0.15'), 'vat': Decimal('0.09')},
    '19': {'duty': Decimal('0.15'), 'vat': Decimal('0.09')},
    '20': {'duty': Decimal('0.15'), 'vat': Decimal('0.09')},
    '21': {'duty': Decimal('0.15'), 'vat': Decimal('0.09')},
    '22': {'duty': Decimal('0.15'), 'vat': Decimal('0.09')},
    '23': {'duty': Decimal('0.15'), 'vat': Decimal('0.09')},
    '24': {'duty': Decimal('0.15'), 'vat': Decimal('0.09')},
}

DEFAULT_DUTY_RATE = Decimal('0.10')
DEFAULT_VAT_RATE = Decimal('0.13')


class CustomsService:
    """海关报关服务"""

    @staticmethod
    def calculate_duties(hs_code, total_value):
        """根据 HS 编码计算关税和增值税"""
        prefix = hs_code[:2] if len(hs_code) >= 2 else ''
        rates = HS_DUTY_RATES.get(prefix, {'duty': DEFAULT_DUTY_RATE, 'vat': DEFAULT_VAT_RATE})
        duty_rate = rates['duty']
        vat_rate = rates['vat']
        duty_amount = total_value * duty_rate
        vat_amount = (total_value + duty_amount) * vat_rate
        return {
            'duty_rate': duty_rate,
            'duty_amount': duty_amount,
            'vat_rate': vat_rate,
            'vat_amount': vat_amount,
        }

    @staticmethod
    def create_declaration(user, shipment_id, customs_office_id, hs_code, **kwargs):
        """出口商申报报关"""
        current_role = RoleService.get_current_role(user)
        if not current_role or current_role.role.code != 'exporter':
            raise ValueError('只有出口商角色才能申报报关')

        shipment = Shipment.objects.get(id=shipment_id)
        if shipment.shipper_id != current_role.company_id:
            raise ValueError('只能为自己的出口货运申报报关')

        if shipment.status != 'shipped':
            raise ValueError('提单未签发，无法申报报关')

        customs_office = Company.objects.get(id=customs_office_id)

        duties = CustomsService.calculate_duties(hs_code, kwargs.get('total_value', Decimal('0')))

        return CustomsDeclaration.objects.create(
            shipment=shipment,
            declarant=current_role.company,
            customs_office=customs_office,
            hs_code=hs_code,
            duty_rate=duties['duty_rate'],
            vat_rate=duties['vat_rate'],
            created_by=user,
            **kwargs
        )

    @staticmethod
    def review(declaration_id, user):
        """海关审核"""
        current_role = RoleService.get_current_role(user)
        if not current_role or current_role.role.code != 'customs':
            raise ValueError('只有海关角色才能审核')

        decl = CustomsDeclaration.objects.get(id=declaration_id)
        if decl.customs_office_id != current_role.company_id:
            raise ValueError('只能审核自己公司的报关单')

        if decl.status != 'declared':
            raise ValueError(f'报关单状态不允许审核: {decl.get_status_display()}')

        decl.status = 'reviewing'
        decl.reviewed_at = timezone.now()
        decl.save()

        TransactionService.log_transaction(
            decl.shipment.contract.transaction, user, 'customs_reviewed',
            {'declaration_no': decl.declaration_no}
        )
        return decl

    @staticmethod
    def assess(declaration_id, user):
        """海关征税"""
        current_role = RoleService.get_current_role(user)
        if not current_role or current_role.role.code != 'customs':
            raise ValueError('只有海关角色才能征税')

        decl = CustomsDeclaration.objects.get(id=declaration_id)
        if decl.customs_office_id != current_role.company_id:
            raise ValueError('只能处理自己公司的报关单')

        if decl.status != 'reviewing':
            raise ValueError(f'报关单状态不允许征税: {decl.get_status_display()}')

        duties = CustomsService.calculate_duties(decl.hs_code, decl.total_value)
        decl.duty_amount = duties['duty_amount']
        decl.vat_amount = duties['vat_amount']
        decl.status = 'assessed'
        decl.assessed_at = timezone.now()
        decl.save()

        TransactionService.log_transaction(
            decl.shipment.contract.transaction, user, 'customs_assessed',
            {'declaration_no': decl.declaration_no, 'duty': str(decl.duty_amount), 'vat': str(decl.vat_amount)}
        )
        return decl

    @staticmethod
    def clear(declaration_id, user):
        """海关放行"""
        current_role = RoleService.get_current_role(user)
        if not current_role or current_role.role.code != 'customs':
            raise ValueError('只有海关角色才能放行')

        decl = CustomsDeclaration.objects.get(id=declaration_id)
        if decl.customs_office_id != current_role.company_id:
            raise ValueError('只能处理自己公司的报关单')

        if decl.status != 'assessed':
            raise ValueError(f'报关单状态不允许放行: {decl.get_status_display()}')

        decl.status = 'cleared'
        decl.cleared_at = timezone.now()
        decl.save()

        TransactionService.log_transaction(
            decl.shipment.contract.transaction, user, 'customs_cleared',
            {'declaration_no': decl.declaration_no}
        )
        return decl

    @staticmethod
    def reject(declaration_id, user, reason=''):
        """海关退单"""
        current_role = RoleService.get_current_role(user)
        if not current_role or current_role.role.code != 'customs':
            raise ValueError('只有海关角色才能退单')

        decl = CustomsDeclaration.objects.get(id=declaration_id)
        if decl.customs_office_id != current_role.company_id:
            raise ValueError('只能处理自己公司的报关单')

        if decl.status not in ('declared', 'reviewing'):
            raise ValueError(f'报关单状态不允许退单: {decl.get_status_display()}')

        decl.status = 'rejected'
        decl.rejected_at = timezone.now()
        decl.save()

        TransactionService.log_transaction(
            decl.shipment.contract.transaction, user, 'customs_rejected',
            {'declaration_no': decl.declaration_no, 'reason': reason}
        )
        return decl
```

- [ ] **步骤 4：运行测试验证通过**

运行：`pytest apps/transactions/tests/test_customs_services.py -v`
预期：全部 PASS

- [ ] **步骤 5：Commit**

```bash
git add apps/transactions/services.py apps/transactions/tests/test_customs_services.py
git commit -m "feat(transactions): implement CustomsService with duty calculation"
```

---

### 任务 4：实现 InspectionService

**文件：**
- 修改：`apps/transactions/services.py`
- 创建：`apps/transactions/tests/test_inspection_services.py`

- [ ] **步骤 1：编写 InspectionService 测试**

创建 `apps/transactions/tests/test_inspection_services.py`：

```python
import pytest
from django.test import TestCase
from datetime import date
from decimal import Decimal
from apps.transactions.models import Transaction, Contract, Shipment, InspectionApplication
from apps.transactions.services import ShipmentService, InspectionService
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
        product_name='T-Shirt', product_spec='Cotton',
        quantity=1000, unit='pcs', unit_price=10.00,
        total_amount=10000.00, currency='USD', status='effective'
    )
    return contract


class InspectionServiceTest(TestCase):
    def setUp(self):
        from django.core.management import call_command
        call_command('init_trade_roles')

        self.exporter = User.objects.create_user(username='is_exp2', password='testpass', email='is2e@test.com')
        self.carrier_user = User.objects.create_user(username='is_car2', password='testpass', email='is2c@test.com')
        self.inspector_user = User.objects.create_user(username='is_ins2', password='testpass', email='is2i@test.com')
        self.buyer_user = User.objects.create_user(username='is_buy2', password='testpass', email='is2b@test.com')
        self.exporter_company = create_company_for_user(self.exporter, '_IS2出口商')
        self.carrier_company = create_company_for_user(self.carrier_user, '_IS2货运')
        self.inspector_company = create_company_for_user(self.inspector_user, '_IS2商检')
        self.buyer_company = create_company_for_user(self.buyer_user, '_IS2买方')

        setup_role(self.exporter, self.exporter_company, 'exporter')
        setup_role(self.carrier_user, self.carrier_company, 'shipping')
        setup_role(self.inspector_user, self.inspector_company, 'inspection')

        contract = create_effective_contract(
            self.exporter_company, self.buyer_company, self.exporter
        )
        shipment = ShipmentService.create_shipment(
            user=self.exporter, contract_id=contract.id,
            carrier_id=self.carrier_company.id,
            port_of_loading='Shanghai', port_of_discharge='Los Angeles'
        )
        ShipmentService.book(shipment.id, self.carrier_user, 'BK001', 'OOCL', date(2026, 10, 1), date(2026, 11, 1))
        ShipmentService.load(shipment.id, self.carrier_user)
        ShipmentService.issue_bl(shipment.id, self.carrier_user, bl_no='BL001')
        self.shipment = shipment

    def test_calculate_fee_legal(self):
        fee = InspectionService.calculate_fee('legal', Decimal('10000.00'))
        assert fee == Decimal('50.00')  # 10000 * 0.5%

    def test_calculate_fee_general(self):
        fee = InspectionService.calculate_fee('general', Decimal('10000.00'))
        assert fee == Decimal('30.00')  # 10000 * 0.3%

    def test_create_application_success(self):
        app = InspectionService.create_application(
            user=self.exporter,
            shipment_id=self.shipment.id,
            inspector_id=self.inspector_company.id,
            inspection_type='legal',
            product_name='Cotton T-Shirt',
            product_spec='100% Cotton',
            quantity=Decimal('1000'),
            goods_value=Decimal('10000.00')
        )
        assert app.applicant == self.exporter_company
        assert app.inspector == self.inspector_company
        assert app.status == 'applied'
        assert app.fee == Decimal('50.00')

    def test_create_application_non_exporter_rejected(self):
        with pytest.raises(ValueError, match='只有出口商角色才能报检'):
            InspectionService.create_application(
                user=self.inspector_user,
                shipment_id=self.shipment.id,
                inspector_id=self.inspector_company.id,
                inspection_type='legal',
                product_name='Test', quantity=Decimal('100'),
                goods_value=Decimal('1000.00')
            )

    def test_inspect_by_inspector_success(self):
        app = InspectionService.create_application(
            user=self.exporter, shipment_id=self.shipment.id,
            inspector_id=self.inspector_company.id,
            inspection_type='legal', product_name='Test',
            quantity=Decimal('100'), goods_value=Decimal('1000.00')
        )
        result = InspectionService.inspect(app.id, self.inspector_user)
        assert result.status == 'inspecting'
        assert result.inspecting_at is not None

    def test_pass_by_inspector_success(self):
        app = InspectionService.create_application(
            user=self.exporter, shipment_id=self.shipment.id,
            inspector_id=self.inspector_company.id,
            inspection_type='legal', product_name='Test',
            quantity=Decimal('100'), goods_value=Decimal('1000.00')
        )
        InspectionService.inspect(app.id, self.inspector_user)
        result = InspectionService.pass_inspection(app.id, self.inspector_user)
        assert result.status == 'passed'
        assert result.passed_at is not None

    def test_certify_by_inspector_success(self):
        app = InspectionService.create_application(
            user=self.exporter, shipment_id=self.shipment.id,
            inspector_id=self.inspector_company.id,
            inspection_type='legal', product_name='Test',
            quantity=Decimal('100'), goods_value=Decimal('1000.00')
        )
        InspectionService.inspect(app.id, self.inspector_user)
        InspectionService.pass_inspection(app.id, self.inspector_user)
        result = InspectionService.certify(
            app.id, self.inspector_user,
            certificate_no='CIQ20260001',
            origin_certificate_no='CO20260001'
        )
        assert result.status == 'certified'
        assert result.certificate_no == 'CIQ20260001'
        assert result.origin_certificate_no == 'CO20260001'
        assert result.certified_at is not None

    def test_fail_by_inspector_success(self):
        app = InspectionService.create_application(
            user=self.exporter, shipment_id=self.shipment.id,
            inspector_id=self.inspector_company.id,
            inspection_type='legal', product_name='Test',
            quantity=Decimal('100'), goods_value=Decimal('1000.00')
        )
        InspectionService.inspect(app.id, self.inspector_user)
        result = InspectionService.fail_inspection(app.id, self.inspector_user, reason='不合格')
        assert result.status == 'failed'
        assert result.failed_at is not None

    def test_inspect_by_exporter_rejected(self):
        app = InspectionService.create_application(
            user=self.exporter, shipment_id=self.shipment.id,
            inspector_id=self.inspector_company.id,
            inspection_type='legal', product_name='Test',
            quantity=Decimal('100'), goods_value=Decimal('1000.00')
        )
        with pytest.raises(ValueError, match='只有商检机构角色才能检验'):
            InspectionService.inspect(app.id, self.exporter)
```

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest apps/transactions/tests/test_inspection_services.py -v`
预期：FAIL

- [ ] **步骤 3：实现 InspectionService**

在 `apps/transactions/services.py` 顶部 import 更新：
```python
from apps.transactions.models import PurchaseOrder, Shipment, InsurancePolicy, CustomsDeclaration, InspectionApplication
```

在文件末尾添加：

```python
# 检验费率表
INSPECTION_RATES = {
    'legal': Decimal('0.005'),   # 法定检验 0.5%
    'general': Decimal('0.003'), # 一般鉴定 0.3%
}


class InspectionService:
    """商检服务"""

    @staticmethod
    def calculate_fee(inspection_type, goods_value):
        """检验费计算"""
        rate = INSPECTION_RATES.get(inspection_type, Decimal('0.005'))
        return goods_value * rate

    @staticmethod
    def create_application(user, shipment_id, inspector_id, inspection_type='legal', **kwargs):
        """出口商报检"""
        current_role = RoleService.get_current_role(user)
        if not current_role or current_role.role.code != 'exporter':
            raise ValueError('只有出口商角色才能报检')

        shipment = Shipment.objects.get(id=shipment_id)
        if shipment.shipper_id != current_role.company_id:
            raise ValueError('只能为自己的出口货运报检')

        if shipment.status != 'shipped':
            raise ValueError('提单未签发，无法报检')

        inspector = Company.objects.get(id=inspector_id)
        goods_value = kwargs.get('goods_value', Decimal('0'))
        fee = InspectionService.calculate_fee(inspection_type, goods_value)

        return InspectionApplication.objects.create(
            shipment=shipment,
            applicant=current_role.company,
            inspector=inspector,
            inspection_type=inspection_type,
            fee=fee,
            created_by=user,
            **kwargs
        )

    @staticmethod
    def inspect(application_id, user):
        """商检机构开始检验"""
        current_role = RoleService.get_current_role(user)
        if not current_role or current_role.role.code != 'inspection':
            raise ValueError('只有商检机构角色才能检验')

        app = InspectionApplication.objects.get(id=application_id)
        if app.inspector_id != current_role.company_id:
            raise ValueError('只能检验自己公司收到的报检单')

        if app.status != 'applied':
            raise ValueError(f'报检单状态不允许检验: {app.get_status_display()}')

        app.status = 'inspecting'
        app.inspecting_at = timezone.now()
        app.save()

        TransactionService.log_transaction(
            app.shipment.contract.transaction, user, 'inspection_started',
            {'application_no': app.application_no}
        )
        return app

    @staticmethod
    def pass_inspection(application_id, user):
        """商检合格"""
        current_role = RoleService.get_current_role(user)
        if not current_role or current_role.role.code != 'inspection':
            raise ValueError('只有商检机构角色才能判定合格')

        app = InspectionApplication.objects.get(id=application_id)
        if app.inspector_id != current_role.company_id:
            raise ValueError('只能处理自己公司的报检单')

        if app.status != 'inspecting':
            raise ValueError(f'报检单状态不允许判定: {app.get_status_display()}')

        app.status = 'passed'
        app.passed_at = timezone.now()
        app.save()

        TransactionService.log_transaction(
            app.shipment.contract.transaction, user, 'inspection_passed',
            {'application_no': app.application_no}
        )
        return app

    @staticmethod
    def certify(application_id, user, certificate_no, origin_certificate_no=''):
        """签发检验证书 + 产地证"""
        current_role = RoleService.get_current_role(user)
        if not current_role or current_role.role.code != 'inspection':
            raise ValueError('只有商检机构角色才能签发证书')

        app = InspectionApplication.objects.get(id=application_id)
        if app.inspector_id != current_role.company_id:
            raise ValueError('只能签发自己公司的证书')

        if app.status != 'passed':
            raise ValueError(f'报检单状态不允许签发证书: {app.get_status_display()}')

        app.status = 'certified'
        app.certificate_no = certificate_no
        app.origin_certificate_no = origin_certificate_no
        app.certified_at = timezone.now()
        app.save()

        TransactionService.log_transaction(
            app.shipment.contract.transaction, user, 'inspection_certified',
            {'application_no': app.application_no, 'certificate_no': certificate_no}
        )
        return app

    @staticmethod
    def fail_inspection(application_id, user, reason=''):
        """检验不合格"""
        current_role = RoleService.get_current_role(user)
        if not current_role or current_role.role.code != 'inspection':
            raise ValueError('只有商检机构角色才能判定不合格')

        app = InspectionApplication.objects.get(id=application_id)
        if app.inspector_id != current_role.company_id:
            raise ValueError('只能处理自己公司的报检单')

        if app.status != 'inspecting':
            raise ValueError(f'报检单状态不允许判定不合格: {app.get_status_display()}')

        app.status = 'failed'
        app.failed_at = timezone.now()
        app.save()

        TransactionService.log_transaction(
            app.shipment.contract.transaction, user, 'inspection_failed',
            {'application_no': app.application_no, 'reason': reason}
        )
        return app
```

- [ ] **步骤 4：运行测试验证通过**

运行：`pytest apps/transactions/tests/test_inspection_services.py -v`
预期：全部 PASS

- [ ] **步骤 5：Commit**

```bash
git add apps/transactions/services.py apps/transactions/tests/test_inspection_services.py
git commit -m "feat(transactions): implement InspectionService with fee calculation"
```

---

### 任务 5：实现序列化器、API 视图和路由

**文件：**
- 修改：`apps/transactions/serializers.py`
- 修改：`apps/transactions/views.py`
- 修改：`apps/transactions/urls.py`
- 创建：`apps/transactions/tests/test_customs_inspection_api.py`

- [ ] **步骤 1：添加序列化器**

在 `apps/transactions/serializers.py` 顶部 import 添加 `CustomsDeclaration, InspectionApplication`：
```python
from apps.transactions.models import (
    Transaction, InquiryMessage, Contract, ContractSignature,
    ContractAmendment, LetterOfCredit, LcAmendment, BankOperation,
    PurchaseOrder, Shipment, InsurancePolicy,
    CustomsDeclaration, InspectionApplication
)
```

在文件末尾添加：

```python
class CustomsDeclarationSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    declarant_name = serializers.CharField(source='declarant.name', read_only=True)
    customs_office_name = serializers.CharField(source='customs_office.name', read_only=True)
    shipment_no = serializers.CharField(source='shipment.shipment_no', read_only=True)

    class Meta:
        model = CustomsDeclaration
        fields = [
            'id', 'declaration_no', 'shipment', 'shipment_no',
            'declarant', 'declarant_name', 'customs_office', 'customs_office_name',
            'hs_code', 'goods_name', 'quantity', 'unit_value', 'total_value', 'currency',
            'duty_rate', 'duty_amount', 'vat_rate', 'vat_amount',
            'status', 'status_display', 'notes',
            'created_by', 'reviewed_at', 'assessed_at', 'cleared_at', 'rejected_at',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'declaration_no', 'created_by',
            'duty_rate', 'duty_amount', 'vat_rate', 'vat_amount',
            'reviewed_at', 'assessed_at', 'cleared_at', 'rejected_at',
            'created_at', 'updated_at'
        ]


class CreateCustomsDeclarationSerializer(serializers.Serializer):
    shipment_id = serializers.IntegerField(min_value=1)
    customs_office_id = serializers.IntegerField(min_value=1)
    hs_code = serializers.CharField(max_length=20)
    goods_name = serializers.CharField(max_length=200)
    quantity = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0.01)
    unit_value = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0.01)
    total_value = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=0.01)
    currency = serializers.CharField(max_length=10, default='USD')
    notes = serializers.CharField(required=False, allow_blank=True)


class InspectionApplicationSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    inspection_type_display = serializers.CharField(source='get_inspection_type_display', read_only=True)
    applicant_name = serializers.CharField(source='applicant.name', read_only=True)
    inspector_name = serializers.CharField(source='inspector.name', read_only=True)
    shipment_no = serializers.CharField(source='shipment.shipment_no', read_only=True)

    class Meta:
        model = InspectionApplication
        fields = [
            'id', 'application_no', 'shipment', 'shipment_no',
            'applicant', 'applicant_name', 'inspector', 'inspector_name',
            'product_name', 'product_spec', 'quantity', 'goods_value',
            'inspection_type', 'inspection_type_display',
            'fee', 'fee_currency',
            'certificate_no', 'origin_certificate_no',
            'status', 'status_display', 'notes',
            'created_by', 'inspecting_at', 'passed_at', 'certified_at', 'failed_at',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'application_no', 'created_by', 'fee',
            'certificate_no', 'origin_certificate_no',
            'inspecting_at', 'passed_at', 'certified_at', 'failed_at',
            'created_at', 'updated_at'
        ]


class CreateInspectionApplicationSerializer(serializers.Serializer):
    shipment_id = serializers.IntegerField(min_value=1)
    inspector_id = serializers.IntegerField(min_value=1)
    inspection_type = serializers.ChoiceField(
        choices=['legal', 'general'], default='legal'
    )
    product_name = serializers.CharField(max_length=200)
    product_spec = serializers.CharField(max_length=200, required=False, allow_blank=True)
    quantity = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0.01)
    goods_value = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=0.01)
    notes = serializers.CharField(required=False, allow_blank=True)
```

- [ ] **步骤 2：添加 ViewSet**

在 `apps/transactions/views.py` 顶部 import 更新：

```python
from apps.transactions.models import Transaction, InquiryMessage, Contract, PurchaseOrder, Shipment, InsurancePolicy, CustomsDeclaration, InspectionApplication
from apps.transactions.serializers import (
    TransactionSerializer,
    InquiryMessageSerializer,
    ContractSerializer,
    PurchaseOrderSerializer, CreatePurchaseOrderSerializer,
    ShipmentSerializer, CreateShipmentSerializer,
    InsurancePolicySerializer, CreateInsurancePolicySerializer,
    CustomsDeclarationSerializer, CreateCustomsDeclarationSerializer,
    InspectionApplicationSerializer, CreateInspectionApplicationSerializer
)
from apps.transactions.services import (
    TransactionService, PurchaseOrderService,
    ShipmentService, InsuranceService,
    CustomsService, InspectionService
)
```

在文件末尾添加：

```python
class CustomsDeclarationViewSet(viewsets.ModelViewSet):
    serializer_class = CustomsDeclarationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        current_role = RoleService.get_current_role(user)
        if not current_role or not current_role.company:
            return CustomsDeclaration.objects.none()
        company = current_role.company
        return CustomsDeclaration.objects.filter(declarant=company) | CustomsDeclaration.objects.filter(customs_office=company)

    def list(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_queryset(), many=True)
        return Response({'code': 0, 'message': 'success', 'data': serializer.data})

    def create(self, request, *args, **kwargs):
        serializer = CreateCustomsDeclarationSerializer(data=request.data)
        if serializer.is_valid():
            try:
                decl = CustomsService.create_declaration(user=request.user, **serializer.validated_data)
                return Response({
                    'code': 0, 'message': '报关申报成功',
                    'data': CustomsDeclarationSerializer(decl).data
                }, status=status.HTTP_201_CREATED)
            except Exception as e:
                return Response({'code': 5005, 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'code': 3002, 'message': '参数格式错误', 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, *args, **kwargs):
        return Response({'code': 0, 'message': 'success', 'data': self.get_serializer(self.get_object()).data})

    @action(detail=True, methods=['post'])
    def review(self, request, pk=None):
        try:
            result = CustomsService.review(self.get_object().id, request.user)
            return Response({'code': 0, 'message': '审核中', 'data': CustomsDeclarationSerializer(result).data})
        except Exception as e:
            return Response({'code': 5005, 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def assess(self, request, pk=None):
        try:
            result = CustomsService.assess(self.get_object().id, request.user)
            return Response({'code': 0, 'message': '征税完成', 'data': CustomsDeclarationSerializer(result).data})
        except Exception as e:
            return Response({'code': 5005, 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def clear(self, request, pk=None):
        try:
            result = CustomsService.clear(self.get_object().id, request.user)
            return Response({'code': 0, 'message': '已放行', 'data': CustomsDeclarationSerializer(result).data})
        except Exception as e:
            return Response({'code': 5005, 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        try:
            result = CustomsService.reject(
                self.get_object().id, request.user,
                reason=request.data.get('reason', '')
            )
            return Response({'code': 0, 'message': '已退单', 'data': CustomsDeclarationSerializer(result).data})
        except Exception as e:
            return Response({'code': 5005, 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class InspectionApplicationViewSet(viewsets.ModelViewSet):
    serializer_class = InspectionApplicationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        current_role = RoleService.get_current_role(user)
        if not current_role or not current_role.company:
            return InspectionApplication.objects.none()
        company = current_role.company
        return InspectionApplication.objects.filter(applicant=company) | InspectionApplication.objects.filter(inspector=company)

    def list(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_queryset(), many=True)
        return Response({'code': 0, 'message': 'success', 'data': serializer.data})

    def create(self, request, *args, **kwargs):
        serializer = CreateInspectionApplicationSerializer(data=request.data)
        if serializer.is_valid():
            try:
                app = InspectionService.create_application(user=request.user, **serializer.validated_data)
                return Response({
                    'code': 0, 'message': '报检成功',
                    'data': InspectionApplicationSerializer(app).data
                }, status=status.HTTP_201_CREATED)
            except Exception as e:
                return Response({'code': 5005, 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'code': 3002, 'message': '参数格式错误', 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, *args, **kwargs):
        return Response({'code': 0, 'message': 'success', 'data': self.get_serializer(self.get_object()).data})

    @action(detail=True, methods=['post'])
    def inspect(self, request, pk=None):
        try:
            result = InspectionService.inspect(self.get_object().id, request.user)
            return Response({'code': 0, 'message': '开始检验', 'data': InspectionApplicationSerializer(result).data})
        except Exception as e:
            return Response({'code': 5005, 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def pass_inspection(self, request, pk=None):
        try:
            result = InspectionService.pass_inspection(self.get_object().id, request.user)
            return Response({'code': 0, 'message': '检验合格', 'data': InspectionApplicationSerializer(result).data})
        except Exception as e:
            return Response({'code': 5005, 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def certify(self, request, pk=None):
        try:
            result = InspectionService.certify(
                self.get_object().id, request.user,
                certificate_no=request.data['certificate_no'],
                origin_certificate_no=request.data.get('origin_certificate_no', '')
            )
            return Response({'code': 0, 'message': '证书已签发', 'data': InspectionApplicationSerializer(result).data})
        except Exception as e:
            return Response({'code': 5005, 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def fail(self, request, pk=None):
        try:
            result = InspectionService.fail_inspection(
                self.get_object().id, request.user,
                reason=request.data.get('reason', '')
            )
            return Response({'code': 0, 'message': '检验不合格', 'data': InspectionApplicationSerializer(result).data})
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
router.register(r'customs-declarations', views.CustomsDeclarationViewSet, basename='customsdeclaration')
router.register(r'inspection-applications', views.InspectionApplicationViewSet, basename='inspectionapplication')

urlpatterns = router.urls
```

- [ ] **步骤 4：创建 API 测试**

创建 `apps/transactions/tests/test_customs_inspection_api.py`：

```python
import pytest
from decimal import Decimal
from datetime import date
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from apps.transactions.models import Transaction, Contract, Shipment, CustomsDeclaration, InspectionApplication
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


class CustomsInspectionAPITest(TestCase):
    def setUp(self):
        from django.core.management import call_command
        call_command('init_trade_roles')

        self.exporter = User.objects.create_user(username='ci_exp', password='testpass', email='cie@test.com')
        self.carrier_user = User.objects.create_user(username='ci_car', password='testpass', email='cic@test.com')
        self.customs_user = User.objects.create_user(username='ci_cus', password='testpass', email='ciu@test.com')
        self.inspector_user = User.objects.create_user(username='ci_ins', password='testpass', email='cii@test.com')
        self.buyer_user = User.objects.create_user(username='ci_buy', password='testpass', email='cib@test.com')
        self.exporter_company = create_company_for_user(self.exporter, '_CI出口商')
        self.carrier_company = create_company_for_user(self.carrier_user, '_CI货运')
        self.customs_company = create_company_for_user(self.customs_user, '_CI海关')
        self.inspector_company = create_company_for_user(self.inspector_user, '_CI商检')
        self.buyer_company = create_company_for_user(self.buyer_user, '_CI买方')

        setup_role(self.exporter, self.exporter_company, 'exporter')
        setup_role(self.carrier_user, self.carrier_company, 'shipping')
        setup_role(self.customs_user, self.customs_company, 'customs')
        setup_role(self.inspector_user, self.inspector_company, 'inspection')

        transaction = Transaction.objects.create(
            buyer=self.buyer_company, seller=self.exporter_company,
            product_id=1, quantity=1000, unit_price=10.00,
            status='in_progress', created_by=self.exporter
        )
        contract = Contract.objects.create(
            contract_no='CI-TEST-001', transaction=transaction,
            trade_term='CIF', payment_term='L/C at sight',
            delivery_time=date(2026, 12, 31),
            port_of_loading='Shanghai', port_of_discharge='Los Angeles',
            product_name='T-Shirt', product_spec='Cotton',
            quantity=1000, unit='pcs', unit_price=10.00,
            total_amount=10000.00, currency='USD', status='effective'
        )
        shipment = ShipmentService.create_shipment(
            user=self.exporter, contract_id=contract.id,
            carrier_id=self.carrier_company.id,
            port_of_loading='Shanghai', port_of_discharge='Los Angeles'
        )
        ShipmentService.book(shipment.id, self.carrier_user, 'BK001', 'OOCL', date(2026, 10, 1), date(2026, 11, 1))
        ShipmentService.load(shipment.id, self.carrier_user)
        ShipmentService.issue_bl(shipment.id, self.carrier_user, bl_no='BL001')
        self.shipment = shipment
        self.client = APIClient()

    def test_create_customs_declaration(self):
        self.client.force_authenticate(user=self.exporter)
        url = reverse('transactions:customsdeclaration-list')
        response = self.client.post(url, {
            'shipment_id': self.shipment.id,
            'customs_office_id': self.customs_company.id,
            'hs_code': '610910',
            'goods_name': 'Cotton T-Shirt',
            'quantity': '1000',
            'unit_value': '10.00',
            'total_value': '10000.00',
            'currency': 'USD'
        }, format='json')
        assert response.status_code == 201
        assert response.json()['code'] == 0

    def test_customs_full_lifecycle(self):
        from apps.transactions.services import CustomsService
        decl = CustomsService.create_declaration(
            user=self.exporter, shipment_id=self.shipment.id,
            customs_office_id=self.customs_company.id,
            hs_code='610910', goods_name='Test',
            quantity=Decimal('1000'), unit_value=Decimal('10.00'),
            total_value=Decimal('10000.00')
        )
        self.client.force_authenticate(user=self.customs_user)
        # Review
        self.client.post(reverse('transactions:customsdeclaration-review', kwargs={'pk': decl.id}))
        # Assess
        self.client.post(reverse('transactions:customsdeclaration-assess', kwargs={'pk': decl.id}))
        # Clear
        resp = self.client.post(reverse('transactions:customsdeclaration-clear', kwargs={'pk': decl.id}))
        assert resp.status_code == 200
        decl.refresh_from_db()
        assert decl.status == 'cleared'

    def test_create_inspection_application(self):
        self.client.force_authenticate(user=self.exporter)
        url = reverse('transactions:inspectionapplication-list')
        response = self.client.post(url, {
            'shipment_id': self.shipment.id,
            'inspector_id': self.inspector_company.id,
            'inspection_type': 'legal',
            'product_name': 'Cotton T-Shirt',
            'quantity': '1000',
            'goods_value': '10000.00'
        }, format='json')
        assert response.status_code == 201
        assert response.json()['code'] == 0

    def test_inspection_full_lifecycle(self):
        from apps.transactions.services import InspectionService
        app = InspectionService.create_application(
            user=self.exporter, shipment_id=self.shipment.id,
            inspector_id=self.inspector_company.id,
            inspection_type='legal', product_name='Test',
            quantity=Decimal('1000'), goods_value=Decimal('10000.00')
        )
        self.client.force_authenticate(user=self.inspector_user)
        # Inspect
        self.client.post(reverse('transactions:inspectionapplication-inspect', kwargs={'pk': app.id}))
        # Pass
        self.client.post(reverse('transactions:inspectionapplication-pass-inspection', kwargs={'pk': app.id}))
        # Certify
        resp = self.client.post(reverse('transactions:inspectionapplication-certify', kwargs={'pk': app.id}), {
            'certificate_no': 'CIQ001',
            'origin_certificate_no': 'CO001'
        }, format='json')
        assert resp.status_code == 200
        app.refresh_from_db()
        assert app.status == 'certified'

    def test_unauthenticated_customs_rejected(self):
        url = reverse('transactions:customsdeclaration-list')
        response = self.client.get(url)
        assert response.status_code in (401, 403)

    def test_unauthenticated_inspection_rejected(self):
        url = reverse('transactions:inspectionapplication-list')
        response = self.client.get(url)
        assert response.status_code in (401, 403)
```

- [ ] **步骤 5：运行测试验证通过**

运行：`pytest apps/transactions/tests/test_customs_inspection_api.py -v`
预期：全部 PASS

- [ ] **步骤 6：Commit**

```bash
git add apps/transactions/serializers.py apps/transactions/views.py apps/transactions/urls.py apps/transactions/tests/test_customs_inspection_api.py
git commit -m "feat(transactions): add CustomsDeclaration and InspectionApplication API endpoints"
```

---

### 任务 6：配置 Admin + 最终验证

**文件：**
- 修改：`apps/transactions/admin.py`

- [ ] **步骤 1：添加 Admin 配置**

在 `apps/transactions/admin.py` 顶部 import 添加 `CustomsDeclaration, InspectionApplication`：

```python
from apps.transactions.models import (
    Transaction, InquiryMessage, Contract,
    ContractSignature, TransactionLog, ContractAmendment,
    LetterOfCredit, LcAmendment, BankOperation,
    PurchaseOrder, Shipment, InsurancePolicy,
    CustomsDeclaration, InspectionApplication
)
```

在文件末尾添加：

```python
@admin.register(CustomsDeclaration)
class CustomsDeclarationAdmin(admin.ModelAdmin):
    list_display = [
        'declaration_no', 'declarant', 'customs_office',
        'hs_code', 'goods_name', 'total_value',
        'duty_amount', 'vat_amount', 'status', 'created_at'
    ]
    list_filter = ['status', 'currency', 'created_at']
    search_fields = ['declaration_no', 'hs_code', 'goods_name']
    readonly_fields = [
        'created_at', 'updated_at',
        'reviewed_at', 'assessed_at', 'cleared_at', 'rejected_at'
    ]


@admin.register(InspectionApplication)
class InspectionApplicationAdmin(admin.ModelAdmin):
    list_display = [
        'application_no', 'applicant', 'inspector',
        'product_name', 'inspection_type',
        'fee', 'status', 'created_at'
    ]
    list_filter = ['status', 'inspection_type', 'created_at']
    search_fields = ['application_no', 'product_name', 'certificate_no']
    readonly_fields = [
        'created_at', 'updated_at',
        'inspecting_at', 'passed_at', 'certified_at', 'failed_at'
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
git commit -m "feat(transactions): add CustomsDeclaration and InspectionApplication admin"
```

---

## 自检清单

### 规格覆盖度

| 设计章节 | 对应任务 |
|---------|---------|
| CustomsDeclaration 模型 | 任务 1 |
| InspectionApplication 模型 | 任务 2 |
| 关税计算（HS编码税率表） | 任务 3（CustomsService.calculate_duties） |
| 检验费计算（费率表） | 任务 4（InspectionService.calculate_fee） |
| CustomsService | 任务 3 |
| InspectionService | 任务 4 |
| 序列化器 | 任务 5 |
| API 端点 | 任务 5 |
| Admin 配置 | 任务 6 |

### 占位符检查

- 无 TBD、TODO 等占位符
- 所有代码步骤包含完整代码

### 类型一致性检查

- CustomsDeclaration 状态：declared, reviewing, assessed, cleared, rejected — 一致
- InspectionApplication 状态：applied, inspecting, passed, certified, failed — 一致
- InspectionType：legal, general — 费率表和服务层一致
- 服务方法签名在测试和实现中一致
- API 端点名称在 urls.py 和测试 reverse() 中一致
- FK 引用：CustomsDeclaration/InspectionApplication → Shipment — 一致
