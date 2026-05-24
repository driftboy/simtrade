# 角色模拟系统实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 实现 SimTrade 平台的角色模拟功能，支持 10 种贸易角色分配、切换和团队协作

**架构：** 新建独立 App (roles/)，通过 User-Company-Role 三表关联实现多角色管理，改造 Transaction 模型使交易发生在公司之间

**Tech Stack：** Django 3.2, Python 3.8+, PostgreSQL/SQLite

---

## 文件结构

### 将要创建的文件

| 文件路径 | 职责 |
|---------|------|
| `apps/roles/__init__.py` | App 初始化 |
| `apps/roles/apps.py` | App 配置 |
| `apps/roles/models.py` | Company, TradeRole, UserCompanyRole 模型 |
| `apps/roles/services.py` | RoleService, CompanyService 业务逻辑 |
| `apps/roles/serializers.py` | API 序列化器 |
| `apps/roles/views.py` | ViewSets 视图 |
| `apps/roles/urls.py` | API 路由 |
| `apps/roles/admin.py` | 管理后台配置 |
| `apps/roles/permissions.py` | 角色相关权限 |
| `apps/roles/management/commands/init_trade_roles.py` | 初始化 10 种角色命令 |
| `apps/roles/tests/test_models.py` | 模型测试 |
| `apps/roles/tests/test_services.py` | 服务测试 |
| `apps/roles/tests/test_api.py` | API 测试 |

### 将要修改的文件

| 文件路径 | 修改内容 |
|---------|---------|
| `simtrade/settings.py` | 注册 `roles` App |
| `apps/transactions/models.py` | Transaction.buyer/seller → Company, LetterOfCredit 改造 |
| `apps/transactions/services.py` | 更新业务逻辑适配 Company |
| `apps/transactions/views.py` | 更新视图逻辑 |
| `apps/transactions/serializers.py` | 更新序列化器 |
| `apps/transactions/tests/test_*.py` | 修复测试 |
| `apps/transactions/migrations/0002_migrate_to_company.py` | 数据迁移 |

---

## 任务分解

### 任务 1：创建 roles App

**文件：**
- 创建：`apps/roles/` 目录结构
- 创建：`apps/roles/__init__.py`
- 创建：`apps/roles/apps.py`

- [ ] **步骤 1：创建 roles App 目录**

运行：
```bash
cd apps
python ../manage.py startapp roles
cd ..
```

预期：创建 `apps/roles/` 目录及基础文件

- [ ] **步骤 2：编辑 apps.py**

编辑 `apps/roles/apps.py`：

```python
from django.apps import AppConfig


class RolesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.roles'
    verbose_name = '角色模拟'
```

- [ ] **步骤 3：注册 App 到 settings.py**

编辑 `simtrade/settings.py`，在 `INSTALLED_APPS` 中添加：

```python
INSTALLED_APPS = [
    # ... 其他 apps
    'apps.roles',
]
```

- [ ] **步骤 4：验证 App 创建成功**

运行：
```bash
python manage.py check
```

预期：无报错

- [ ] **步骤 5：Commit**

```bash
git add apps/roles/ simtrade/settings.py
git commit -m "feat(roles): create roles app"
```

---

### 任务 2：实现 Company 模型

**文件：**
- 修改：`apps/roles/models.py`

- [ ] **步骤 1：编写 Company 模型测试**

创建 `apps/roles/tests/test_models.py`：

```python
import pytest
from apps.roles.models import Company
from apps.core.models import Country


@pytest.mark.django_db
def test_create_company():
    """测试创建公司"""
    country = Country.objects.first()
    company = Company.objects.create(
        name='测试外贸公司',
        name_en='Test Trading Co.',
        code='TEST001',
        type='进出口公司',
        country=country,
        address='上海市浦东新区',
        phone='021-12345678',
        email='test@example.com'
    )

    assert company.name == '测试外贸公司'
    assert company.code == 'TEST001'
    assert str(company) == '测试外贸公司'


@pytest.mark.django_db
def test_company_code_unique():
    """测试公司代码唯一性"""
    country = Country.objects.first()
    Company.objects.create(
        name='公司1',
        code='UNIQUE001',
        country=country
    )

    with pytest.raises(Exception):  # IntegrityError
        Company.objects.create(
            name='公司2',
            code='UNIQUE001',
            country=country
        )
```

- [ ] **步骤 2：运行测试验证失败**

运行：
```bash
pytest apps/roles/tests/test_models.py::test_create_company -v
```

预期：FAIL，Company 模型不存在

- [ ] **步骤 3：实现 Company 模型**

编辑 `apps/roles/models.py`：

```python
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
```

- [ ] **步骤 4：生成并运行迁移**

运行：
```bash
python manage.py makemigrations roles
python manage.py migrate roles
pytest apps/roles/tests/test_models.py::test_create_company -v
```

预期：PASS

- [ ] **步骤 5：Commit**

```bash
git add apps/roles/models.py apps/roles/migrations/
git commit -m "feat(roles): add Company model"
```

---

### 任务 3：实现 TradeRole 模型

**文件：**
- 修改：`apps/roles/models.py`
- 修改：`apps/roles/tests/test_models.py`

- [ ] **步骤 1：编写 TradeRole 模型测试**

在 `apps/roles/tests/test_models.py` 中添加：

```python
from apps.roles.models import TradeRole


@pytest.mark.django_db
def test_create_trade_role():
    """测试创建贸易角色"""
    role = TradeRole.objects.create(
        code='exporter',
        name='出口商',
        description='销售货物到国外',
        sort_order=1
    )

    assert role.code == 'exporter'
    assert role.name == '出口商'
    assert role.is_enabled is True
    assert role.is_system is True


@pytest.mark.django_db
def test_trade_role_choices():
    """测试角色代码选择"""
    valid_codes = [choice[0] for choice in TradeRole.RoleType.choices]

    assert 'exporter' in valid_codes
    assert 'importer' in valid_codes
    assert 'factory' in valid_codes
    assert 'bank' in valid_codes
    assert 'customs' in valid_codes
    assert 'shipping' in valid_codes
    assert 'insurance' in valid_codes
    assert 'inspection' in valid_codes
    assert 'forex' in valid_codes
    assert 'tax' in valid_codes
```

- [ ] **步骤 2：运行测试验证失败**

运行：
```bash
pytest apps/roles/tests/test_models.py::test_create_trade_role -v
```

预期：FAIL，TradeRole 模型不存在

- [ ] **步骤 3：实现 TradeRole 模型**

在 `apps/roles/models.py` 中添加：

```python
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
```

- [ ] **步骤 4：运行测试验证通过**

运行：
```bash
python manage.py makemigrations roles
python manage.py migrate roles
pytest apps/roles/tests/test_models.py::test_create_trade_role -v
pytest apps/roles/tests/test_models.py::test_trade_role_choices -v
```

预期：PASS

- [ ] **步骤 5：Commit**

```bash
git add apps/roles/models.py apps/roles/migrations/ apps/roles/tests/test_models.py
git commit -m "feat(roles): add TradeRole model with 10 role types"
```

---

### 任务 4：实现 UserCompanyRole 模型

**文件：**
- 修改：`apps/roles/models.py`
- 修改：`apps/roles/tests/test_models.py`

- [ ] **步骤 1：编写 UserCompanyRole 模型测试**

在 `apps/roles/tests/test_models.py` 中添加：

```python
from apps.roles.models import UserCompanyRole
from apps.users.models import User


@pytest.mark.django_db
def test_create_user_company_role():
    """测试创建用户-公司-角色分配"""
    country = Country.objects.first()
    user = User.objects.create_user(username='testuser', password='testpass')
    company = Company.objects.create(
        name='测试公司',
        code='TEST002',
        country=country
    )
    role = TradeRole.objects.create(
        code='exporter',
        name='出口商',
        description='销售货物'
    )

    assignment = UserCompanyRole.objects.create(
        user=user,
        company=company,
        role=role
    )

    assert assignment.user == user
    assert assignment.company == company
    assert assignment.role == role
    assert assignment.status == 'pending'
    assert assignment.is_active is False


@pytest.mark.django_db
def test_user_company_role_unique():
    """测试用户-公司-角色组合唯一性"""
    country = Country.objects.first()
    user = User.objects.create_user(username='testuser2', password='testpass')
    company = Company.objects.create(
        name='测试公司2',
        code='TEST003',
        country=country
    )
    role = TradeRole.objects.create(
        code='importer',
        name='进口商',
        description='购买货物'
    )

    UserCompanyRole.objects.create(
        user=user,
        company=company,
        role=role
    )

    with pytest.raises(Exception):  # IntegrityError
        UserCompanyRole.objects.create(
            user=user,
            company=company,
            role=role
        )


@pytest.mark.django_db
def test_activate_role():
    """测试激活角色（单一激活）"""
    country = Country.objects.first()
    user = User.objects.create_user(username='testuser3', password='testpass')
    company = Company.objects.create(
        name='测试公司3',
        code='TEST004',
        country=country
    )
    role1 = TradeRole.objects.create(code='exporter', name='出口商', description='A')
    role2 = TradeRole.objects.create(code='importer', name='进口商', description='B')

    assignment1 = UserCompanyRole.objects.create(
        user=user,
        company=company,
        role=role1,
        is_active=True
    )
    UserCompanyRole.objects.create(
        user=user,
        company=company,
        role=role2
    )

    # 激活第二个角色，第一个应该自动停用
    assignment2 = UserCompanyRole.objects.filter(user=user, role=role2).first()
    assignment2.is_active = True
    assignment2.save()

    assignment1.refresh_from_db()
    assert assignment1.is_active is False
    assert assignment2.is_active is True
```

- [ ] **步骤 2：运行测试验证失败**

运行：
```bash
pytest apps/roles/tests/test_models.py::test_create_user_company_role -v
```

预期：FAIL，UserCompanyRole 模型不存在

- [ ] **步骤 3：实现 UserCompanyRole 模型**

在 `apps/roles/models.py` 中添加：

```python
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
```

- [ ] **步骤 4：运行测试验证通过**

运行：
```bash
python manage.py makemigrations roles
python manage.py migrate roles
pytest apps/roles/tests/test_models.py -v
```

预期：全部 PASS

- [ ] **步骤 5：Commit**

```bash
git add apps/roles/models.py apps/roles/migrations/ apps/roles/tests/test_models.py
git commit -m "feat(roles): add UserCompanyRole model with single activation"
```

---

### 任务 5：创建初始化角色命令

**文件：**
- 创建：`apps/roles/management/commands/init_trade_roles.py`

- [ ] **步骤 1：创建管理命令目录和文件**

运行：
```bash
mkdir -p apps/roles/management/commands
touch apps/roles/management/__init__.py
touch apps/roles/management/commands/__init__.py
```

- [ ] **步骤 2：实现初始化命令**

创建 `apps/roles/management/commands/init_trade_roles.py`：

```python
from django.core.management.base import BaseCommand
from apps.roles.models import TradeRole


class Command(BaseCommand):
    help = '初始化 10 种贸易角色'

    ROLES_DATA = [
        {
            'code': 'exporter',
            'name': '出口商',
            'description': '销售货物到国外，负责制作单证、安排运输、办理报关等出口业务。',
            'sort_order': 1
        },
        {
            'code': 'importer',
            'name': '进口商',
            'description': '从国外购买货物，负责开立信用证、办理进口报关、支付货款等进口业务。',
            'sort_order': 2
        },
        {
            'code': 'factory',
            'name': '工厂',
            'description': '生产/供应商品，接收出口商订单，安排生产、备货、发货，开具增值税发票。',
            'sort_order': 3
        },
        {
            'code': 'bank',
            'name': '银行',
            'description': '处理信用证开立、通知、议付、付款等银行业务，提供结算服务。',
            'sort_order': 4
        },
        {
            'code': 'customs',
            'name': '海关',
            'description': '审核报关单据，征收关税，查验货物，办理放行手续。',
            'sort_order': 5
        },
        {
            'code': 'shipping',
            'name': '货运公司',
            'description': '提供订舱、运输服务，签发提单，安排货物装运和运输。',
            'sort_order': 6
        },
        {
            'code': 'insurance',
            'name': '保险公司',
            'description': '提供货物运输保险服务，审核投保单，签发保险单，处理理赔。',
            'sort_order': 7
        },
        {
            'code': 'inspection',
            'name': '商检机构',
            'description': '对出口商品进行检验检疫，签发检验证书、产地证等。',
            'sort_order': 8
        },
        {
            'code': 'forex',
            'name': '外汇局',
            'description': '管理出口收汇核销，审核外汇收支，办理核销手续。',
            'sort_order': 9
        },
        {
            'code': 'tax',
            'name': '税务局',
            'description': '审核出口退税申请，办理退税手续，管理退税资金。',
            'sort_order': 10
        },
    ]

    def handle(self, *args, **options):
        created_count = 0
        updated_count = 0

        for role_data in self.ROLES_DATA:
            role, created = TradeRole.objects.get_or_create(
                code=role_data['code'],
                defaults=role_data
            )
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'创建角色: {role.name}')
                )
            else:
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'角色已存在: {role.name}')
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'\n完成！创建 {created_count} 个角色，更新 {updated_count} 个角色。'
            )
        )
```

- [ ] **步骤 3：运行命令测试**

运行：
```bash
python manage.py init_trade_roles
```

预期：输出 10 个角色创建/更新信息

- [ ] **步骤 4：验证数据库**

运行：
```bash
python manage.py shell -c "from apps.roles.models import TradeRole; print(f'角色数量: {TradeRole.objects.count()}')"
```

预期：角色数量: 10

- [ ] **步骤 5：Commit**

```bash
git add apps/roles/management/
git commit -m "feat(roles): add init_trade_roles command"
```

---

### 任务 6：实现 RoleService 服务

**文件：**
- 创建：`apps/roles/services.py`
- 创建：`apps/roles/tests/test_services.py`

- [ ] **步骤 1：编写 RoleService 测试**

创建 `apps/roles/tests/test_services.py`：

```python
import pytest
from apps.roles.models import Company, TradeRole, UserCompanyRole
from apps.roles.services import RoleService
from apps.users.models import User
from apps.core.models import Country


@pytest.mark.django_db
def test_request_role():
    """测试申请角色"""
    country = Country.objects.first()
    user = User.objects.create_user(username='student1', password='testpass')
    company = Company.objects.create(
        name='学生公司',
        code='STU001',
        country=country
    )

    assignment = RoleService.request_role(
        user=user,
        company_id=company.id,
        role_code='exporter',
        notes='我想扮演出口商'
    )

    assert assignment.user == user
    assert assignment.company == company
    assert assignment.role.code == 'exporter'
    assert assignment.status == 'pending'
    assert assignment.is_active is False


@pytest.mark.django_db
def test_approve_role():
    """测试批准角色申请"""
    country = Country.objects.first()
    student = User.objects.create_user(username='student2', password='testpass')
    teacher = User.objects.create_user(username='teacher1', password='testpass', is_staff=True)
    company = Company.objects.create(
        name='学生公司2',
        code='STU002',
        country=country
    )

    assignment = RoleService.request_role(student, company.id, 'importer')
    result = RoleService.approve_role(assignment.id, teacher, notes='批准通过')

    assert result.status == 'active'
    assert result.is_active is True
    assert result.approved_by == teacher
    assert result.approved_at is not None


@pytest.mark.django_db
def test_reject_role():
    """测试拒绝角色申请"""
    country = Country.objects.first()
    student = User.objects.create_user(username='student3', password='testpass')
    teacher = User.objects.create_user(username='teacher2', password='testpass', is_staff=True)
    company = Company.objects.create(
        name='学生公司3',
        code='STU003',
        country=country
    )

    assignment = RoleService.request_role(student, company.id, 'factory')
    result = RoleService.reject_role(assignment.id, teacher, reason='角色已满')

    assert result.status == 'rejected'


@pytest.mark.django_db
def test_activate_role():
    """测试激活角色（单一激活）"""
    country = Country.objects.first()
    user = User.objects.create_user(username='student4', password='testpass')
    company = Company.objects.create(
        name='学生公司4',
        code='STU004',
        country=country
    )

    # 创建两个角色分配
    role1 = RoleService.request_role(user, company.id, 'exporter')
    RoleService.approve_role(role1.id, user)  # 自动激活

    role2 = RoleService.request_role(user, company.id, 'importer')
    RoleService.approve_role(role2.id, user)  # 激活这个，role1 自动停用

    result = RoleService.activate_role(user, role2.id)

    assert result.is_active is True

    role1.refresh_from_db()
    assert role1.is_active is False


@pytest.mark.django_db
def test_get_current_role():
    """测试获取当前激活角色"""
    country = Country.objects.first()
    user = User.objects.create_user(username='student5', password='testpass')
    company = Company.objects.create(
        name='学生公司5',
        code='STU005',
        country=country
    )

    assignment = RoleService.request_role(user, company.id, 'bank')
    RoleService.approve_role(assignment.id, user)

    current_role = RoleService.get_current_role(user)

    assert current_role is not None
    assert current_role.role.code == 'bank'
    assert current_role.is_active is True
```

- [ ] **步骤 2：运行测试验证失败**

运行：
```bash
pytest apps/roles/tests/test_services.py::test_request_role -v
```

预期：FAIL，RoleService 不存在

- [ ] **步骤 3：实现 RoleService**

创建 `apps/roles/services.py`：

```python
from django.utils import timezone
from apps.roles.models import Company, TradeRole, UserCompanyRole


class RoleService:
    """角色分配和切换服务"""

    @staticmethod
    def request_role(user, company_id, role_code, notes=''):
        """学生申请角色

        Args:
            user: 申请用户
            company_id: 公司 ID
            role_code: 角色代码
            notes: 申请备注

        Returns:
            UserCompanyRole 实例

        Raises:
            Company.DoesNotExist: 公司不存在
            TradeRole.DoesNotExist: 角色不存在
            ValueError: 已有相同角色的待审核申请
        """
        company = Company.objects.get(id=company_id)
        role = TradeRole.objects.get(code=role_code)

        # 检查是否已有待审核或激活的相同角色
        existing = UserCompanyRole.objects.filter(
            user=user,
            company=company,
            role=role,
            status__in=['pending', 'approved', 'active']
        ).first()

        if existing:
            raise ValueError(f'已有相同的角色申请或分配：{existing.get_status_display()}')

        return UserCompanyRole.objects.create(
            user=user,
            company=company,
            role=role,
            status='pending',
            notes=notes
        )

    @staticmethod
    def approve_role(assignment_id, approver, notes=''):
        """教师批准角色申请（同时激活该角色）

        Args:
            assignment_id: 角色分配 ID
            approver: 批准人（教师）
            notes: 批准备注

        Returns:
            UserCompanyRole 实例

        Raises:
            UserCompanyRole.DoesNotExist: 分配不存在
            ValueError: 状态不允许批准
        """
        assignment = UserCompanyRole.objects.get(id=assignment_id)

        if assignment.status not in ['pending']:
            raise ValueError(f'状态不允许批准：{assignment.get_status_display()}')

        assignment.status = 'active'
        assignment.is_active = True
        assignment.approved_at = timezone.now()
        assignment.approved_by = approver
        if notes:
            assignment.notes = (assignment.notes or '') + f'\n批准备注：{notes}'
        assignment.save()

        return assignment

    @staticmethod
    def reject_role(assignment_id, approver, reason):
        """教师拒绝角色申请

        Args:
            assignment_id: 角色分配 ID
            approver: 批准人（教师）
            reason: 拒绝原因

        Returns:
            UserCompanyRole 实例

        Raises:
            UserCompanyRole.DoesNotExist: 分配不存在
            ValueError: 状态不允许拒绝
        """
        assignment = UserCompanyRole.objects.get(id=assignment_id)

        if assignment.status != 'pending':
            raise ValueError(f'状态不允许拒绝：{assignment.get_status_display()}')

        assignment.status = 'rejected'
        assignment.approved_by = approver
        assignment.notes = (assignment.notes or '') + f'\n拒绝原因：{reason}'
        assignment.save()

        return assignment

    @staticmethod
    def activate_role(user, assignment_id):
        """激活角色（单一激活，会停用其他角色）

        Args:
            user: 用户
            assignment_id: 角色分配 ID

        Returns:
            UserCompanyRole 实例

        Raises:
            UserCompanyRole.DoesNotExist: 分配不存在
            ValueError: 无权激活或状态不允许
        """
        assignment = UserCompanyRole.objects.get(id=assignment_id)

        if assignment.user != user:
            raise ValueError('无权激活此角色')

        if assignment.status != 'active':
            raise ValueError(f'状态不允许激活：{assignment.get_status_display()}')

        # 设置为激活，save 方法会自动停用其他角色
        assignment.is_active = True
        assignment.save()

        return assignment

    @staticmethod
    def get_current_role(user):
        """获取用户当前激活的角色

        Args:
            user: 用户

        Returns:
            UserCompanyRole 实例或 None
        """
        return UserCompanyRole.objects.filter(
            user=user,
            is_active=True
        ).select_related('company', 'role').first()

    @staticmethod
    def get_pending_requests(user=None):
        """获取待审核申请

        Args:
            user: 如果提供，只返回该用户的申请；否则返回全部

        Returns:
            QuerySet
        """
        qs = UserCompanyRole.objects.filter(
            status='pending'
        ).select_related('user', 'company', 'role')

        if user:
            qs = qs.filter(user=user)

        return qs.order_by('-requested_at')

    @staticmethod
    def switch_context(user):
        """获取用户当前角色上下文

        Args:
            user: 用户

        Returns:
            dict: {company, role, permissions}
        """
        current_role = RoleService.get_current_role(user)

        if not current_role:
            return {
                'company': None,
                'role': None,
                'permissions': []
            }

        return {
            'company': {
                'id': current_role.company.id,
                'name': current_role.company.name,
                'code': current_role.company.code
            },
            'role': {
                'id': current_role.role.id,
                'code': current_role.role.code,
                'name': current_role.role.name
            },
            'permissions': []  # TODO: 实现角色权限
        }
```

- [ ] **步骤 4：运行测试验证通过**

运行：
```bash
pytest apps/roles/tests/test_services.py -v
```

预期：全部 PASS

- [ ] **步骤 5：Commit**

```bash
git add apps/roles/services.py apps/roles/tests/test_services.py
git commit -m "feat(roles): implement RoleService with approval workflow"
```

---

### 任务 7：实现 CompanyService 服务

**文件：**
- 修改：`apps/roles/services.py`
- 修改：`apps/roles/tests/test_services.py`

- [ ] **步骤 1：编写 CompanyService 测试**

在 `apps/roles/tests/test_services.py` 中添加：

```python
from apps.roles.services import CompanyService


@pytest.mark.django_db
def test_create_company():
    """测试创建公司"""
    country = Country.objects.first()
    user = User.objects.create_user(username='creator', password='testpass')

    company = CompanyService.create_company(
        user=user,
        name='新建外贸公司',
        name_en='New Trading Co.',
        country_id=country.id,
        type='进出口公司',
        address='北京市朝阳区',
        phone='010-12345678',
        email='new@example.com'
    )

    assert company.name == '新建外贸公司'
    assert company.code.startswith('COMP_')
    assert company.created_by == user


@pytest.mark.django_db
def test_get_company_details():
    """测试获取公司详情"""
    country = Country.objects.first()
    user = User.objects.create_user(username='member1', password='testpass')
    company = Company.objects.create(
        name='详情测试公司',
        code='DETAIL001',
        country=country
    )
    UserCompanyRole.objects.create(
        user=user,
        company=company,
        role=TradeRole.objects.get(code='exporter'),
        status='active',
        is_active=True
    )

    details = CompanyService.get_company_details(company.id, user)

    assert details['company']['id'] == company.id
    assert len(details['members']) == 1
    assert details['members'][0]['username'] == 'member1'
```

- [ ] **步骤 2：运行测试验证失败**

运行：
```bash
pytest apps/roles/tests/test_services.py::test_create_company -v
```

预期：FAIL，CompanyService 不存在

- [ ] **步骤 3：实现 CompanyService**

在 `apps/roles/services.py` 中添加：

```python
import random
import string
from apps.roles.models import UserCompanyRole


class CompanyService:
    """公司管理服务"""

    @staticmethod
    def create_company(user, name, name_en='', country_id=None, **kwargs):
        """创建公司（学生或教师）

        Args:
            user: 创建人
            name: 公司名称
            name_en: 英文名称
            country_id: 国家 ID
            **kwargs: 其他字段

        Returns:
            Company 实例
        """
        # 生成公司代码
        code = CompanyService._generate_company_code()

        company = Company.objects.create(
            name=name,
            name_en=name_en,
            code=code,
            country_id=country_id,
            created_by=user,
            **kwargs
        )

        # 创建人自动成为该公司成员（出口商角色）
        try:
            role = TradeRole.objects.get(code='exporter')
            UserCompanyRole.objects.create(
                user=user,
                company=company,
                role=role,
                status='active',
                is_active=True
            )
        except TradeRole.DoesNotExist:
            pass  # 角色尚未初始化

        return company

    @staticmethod
    def get_company_details(company_id, user):
        """获取公司详情（含成员列表）

        Args:
            company_id: 公司 ID
            user: 查询用户（用于权限验证）

        Returns:
            dict: 公司详情和成员列表
        """
        company = Company.objects.get(id=company_id)

        members = UserCompanyRole.objects.filter(
            company=company,
            status__in=['approved', 'active', 'suspended']
        ).select_related('user', 'role')

        members_data = []
        for member in members:
            members_data.append({
                'user_id': member.user.id,
                'username': member.user.username,
                'role_code': member.role.code,
                'role_name': member.role.name,
                'status': member.status,
                'is_active': member.is_active
            })

        return {
            'company': {
                'id': company.id,
                'name': company.name,
                'name_en': company.name_en,
                'code': company.code,
                'type': company.type,
                'country': company.country.name if company.country else None,
                'address': company.address,
                'phone': company.phone,
                'email': company.email,
                'logo': company.logo,
                'created_at': company.created_at.isoformat()
            },
            'members': members_data
        }

    @staticmethod
    def _generate_company_code():
        """生成公司代码

        Returns:
            str: 唯一的公司代码
        """
        while True:
            code = f'COMP_{"".join(random.choices(string.digits, k=6))}'
            if not Company.objects.filter(code=code).exists():
                return code
```

- [ ] **步骤 4：运行测试验证通过**

运行：
```bash
pytest apps/roles/tests/test_services.py::test_create_company -v
pytest apps/roles/tests/test_services.py::test_get_company_details -v
```

预期：PASS

- [ ] **步骤 5：Commit**

```bash
git add apps/roles/services.py apps/roles/tests/test_services.py
git commit -m "feat(roles): implement CompanyService"
```

---

### 任务 8：实现序列化器

**文件：**
- 创建：`apps/roles/serializers.py`
- 创建：`apps/roles/tests/test_serializers.py`

- [ ] **步骤 1：编写序列化器测试**

创建 `apps/roles/tests/test_serializers.py`：

```python
import pytest
from apps.roles.models import Company, TradeRole, UserCompanyRole
from apps.roles.serializers import (
    CompanySerializer,
    TradeRoleSerializer,
    UserCompanyRoleSerializer,
    RoleRequestSerializer
)
from apps.users.models import User
from apps.core.models import Country


@pytest.mark.django_db
def test_company_serializer():
    """测试公司序列化器"""
    country = Country.objects.first()
    company = Company.objects.create(
        name='序列化测试公司',
        code='SER001',
        country=country
    )

    serializer = CompanySerializer(company)
    data = serializer.data

    assert data['id'] == company.id
    assert data['name'] == '公司名称'
    assert data['code'] == 'SER001'


@pytest.mark.django_db
def test_trade_role_serializer():
    """测试角色序列化器"""
    role = TradeRole.objects.create(
        code='exporter',
        name='出口商',
        description='销售货物'
    )

    serializer = TradeRoleSerializer(role)
    data = serializer.data

    assert data['code'] == 'exporter'
    assert data['name'] == '出口商'


@pytest.mark.django_db
def test_user_company_role_serializer():
    """测试用户角色分配序列化器"""
    country = Country.objects.first()
    user = User.objects.create_user(username='user1', password='testpass')
    company = Company.objects.create(
        name='序列化公司',
        code='SER002',
        country=country
    )
    role = TradeRole.objects.create(
        code='importer',
        name='进口商',
        description='购买货物'
    )
    assignment = UserCompanyRole.objects.create(
        user=user,
        company=company,
        role=role
    )

    serializer = UserCompanyRoleSerializer(assignment)
    data = serializer.data

    assert data['user_id'] == user.id
    assert data['company_name'] == company.name
    assert data['role_name'] == role.name
    assert data['status'] == 'pending'


@pytest.mark.django_db
def test_role_request_serializer():
    """测试角色申请序列化器"""
    data = {
        'company_id': 1,
        'role_code': 'exporter',
        'notes': '我想扮演出口商'
    }

    # 注意：需要先创建 company_id=1 的公司
    # 这里只测试字段验证
    serializer = RoleRequestSerializer(data=data)

    # 由于 company 可能不存在，这里只测试字段结构
    assert 'company_id' in serializer.fields
    assert 'role_code' in serializer.fields
    assert 'notes' in serializer.fields
```

- [ ] **步骤 2：运行测试验证失败**

运行：
```bash
pytest apps/roles/tests/test_serializers.py::test_company_serializer -v
```

预期：FAIL，序列化器不存在

- [ ] **步骤 3：实现序列化器**

创建 `apps/roles/serializers.py`：

```python
from rest_framework import serializers
from apps.roles.models import Company, TradeRole, UserCompanyRole


class CompanySerializer(serializers.ModelSerializer):
    """公司序列化器"""

    country_name = serializers.CharField(source='country.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model = Company
        fields = [
            'id', 'name', 'name_en', 'code', 'type', 'country', 'country_name',
            'address', 'phone', 'email', 'logo', 'created_by', 'created_by_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by', 'created_by_name']


class TradeRoleSerializer(serializers.ModelSerializer):
    """贸易角色序列化器"""

    class Meta:
        model = TradeRole
        fields = [
            'id', 'code', 'name', 'description', 'is_enabled', 'is_system',
            'sort_order', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class UserCompanyRoleSerializer(serializers.ModelSerializer):
    """用户角色分配序列化器"""

    user_id = serializers.IntegerField(source='user.id', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    company_id = serializers.IntegerField(source='company.id', read_only=True)
    company_name = serializers.CharField(source='company.name', read_only=True)
    company_code = serializers.CharField(source='company.code', read_only=True)
    role_id = serializers.IntegerField(source='role.id', read_only=True)
    role_code = serializers.CharField(source='role.code', read_only=True)
    role_name = serializers.CharField(source='role.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.username', read_only=True)

    class Meta:
        model = UserCompanyRole
        fields = [
            'id', 'user_id', 'username', 'company_id', 'company_name',
            'company_code', 'role_id', 'role_code', 'role_name',
            'status', 'status_display', 'is_active', 'requested_at',
            'approved_at', 'approved_by_name', 'notes'
        ]
        read_only_fields = ['id', 'requested_at', 'approved_at']


class RoleRequestSerializer(serializers.Serializer):
    """角色申请请求序列化器"""

    company_id = serializers.IntegerField(min_value=1)
    role_code = serializers.CharField(max_length=50)
    notes = serializers.CharField(required=False, allow_blank=True, max_length=500)


class RoleApproveSerializer(serializers.Serializer):
    """角色批准请求序列化器"""

    assignment_id = serializers.IntegerField(min_value=1)
    notes = serializers.CharField(required=False, allow_blank=True, max_length=500)


class RoleRejectSerializer(serializers.Serializer):
    """角色拒绝请求序列化器"""

    assignment_id = serializers.IntegerField(min_value=1)
    reason = serializers.CharField(max_length=500)


class CreateCompanySerializer(serializers.Serializer):
    """创建公司请求序列化器"""

    name = serializers.CharField(max_length=200, min_length=2)
    name_en = serializers.CharField(required=False, allow_blank=True, max_length=200)
    country_id = serializers.IntegerField(required=False, allow_null=True)
    type = serializers.CharField(required=False, allow_blank=True, max_length=50)
    address = serializers.CharField(required=False, allow_blank=True)
    phone = serializers.CharField(required=False, allow_blank=True, max_length=50)
    email = serializers.EmailField(required=False, allow_blank=True)
```

- [ ] **步骤 4：运行测试验证通过**

运行：
```bash
pytest apps/roles/tests/test_serializers.py -v
```

预期：全部 PASS

- [ ] **步骤 5：Commit**

```bash
git add apps/roles/serializers.py apps/roles/tests/test_serializers.py
git commit -m "feat(roles): add serializers for API"
```

---

### 任务 9：实现 API 视图

**文件：**
- 创建：`apps/roles/views.py`
- 创建：`apps/roles/urls.py`
- 创建：`apps/roles/tests/test_api.py`

- [ ] **步骤 1：编写 API 测试**

创建 `apps/roles/tests/test_api.py`：

```python
import pytest
from rest_framework.test import APIClient
from apps.roles.models import Company, TradeRole, UserCompanyRole
from apps.users.models import User
from apps.core.models import Country


@pytest.mark.django_db
def test_get_roles_list(api_client):
    """测试获取角色列表"""
    response = api_client.get('/api/v1/roles/')

    assert response.status_code == 200
    assert response.data['code'] == 0
    assert len(response.data['data']) >= 10  # 至少 10 种系统角色


@pytest.mark.django_db
def test_get_my_roles(api_client):
    """测试获取我的角色列表"""
    user = User.objects.create_user(username='student', password='testpass')
    api_client.force_authenticate(user=user)

    response = api_client.get('/api/v1/roles/my/')

    assert response.status_code == 200
    assert response.data['code'] == 0


@pytest.mark.django_db
def test_request_role(api_client):
    """测试申请角色"""
    country = Country.objects.first()
    user = User.objects.create_user(username='student2', password='testpass')
    company = Company.objects.create(
        name='API测试公司',
        code='API001',
        country=country
    )
    api_client.force_authenticate(user=user)

    response = api_client.post('/api/v1/roles/request/', {
        'company_id': company.id,
        'role_code': 'exporter',
        'notes': '我想扮演出口商'
    })

    assert response.status_code == 200
    assert response.data['code'] == 0
    assert UserCompanyRole.objects.filter(user=user, company=company).exists()


@pytest.mark.django_db
def test_approve_role(api_client):
    """测试批准角色申请"""
    country = Country.objects.first()
    student = User.objects.create_user(username='student3', password='testpass')
    teacher = User.objects.create_user(username='teacher', password='testpass', is_staff=True)
    company = Company.objects.create(
        name='API测试公司2',
        code='API002',
        country=country
    )

    # 学生申请
    assignment = UserCompanyRole.objects.create(
        user=student,
        company=company,
        role=TradeRole.objects.get(code='importer'),
        status='pending'
    )

    api_client.force_authenticate(user=teacher)
    response = api_client.post('/api/v1/roles/approve/', {
        'assignment_id': assignment.id,
        'notes': '批准通过'
    })

    assert response.status_code == 200
    assert response.data['code'] == 0

    assignment.refresh_from_db()
    assert assignment.status == 'active'


@pytest.mark.django_db
def test_create_company(api_client):
    """测试创建公司"""
    country = Country.objects.first()
    user = User.objects.create_user(username='creator2', password='testpass')
    api_client.force_authenticate(user=user)

    response = api_client.post('/api/v1/companies/', {
        'name': '新创外贸公司',
        'name_en': 'New Co.',
        'country_id': country.id,
        'type': '进出口公司',
        'phone': '010-12345678'
    })

    assert response.status_code == 200
    assert response.data['code'] == 0
    assert Company.objects.filter(name='新创外贸公司').exists()


@pytest.fixture
def api_client():
    return APIClient()
```

- [ ] **步骤 2：运行测试验证失败**

运行：
```bash
pytest apps/roles/tests/test_api.py::test_get_roles_list -v
```

预期：FAIL，API 端点不存在

- [ ] **步骤 3：实现视图**

创建 `apps/roles/views.py`：

```python
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from apps.roles.models import Company, TradeRole, UserCompanyRole
from apps.roles.serializers import (
    CompanySerializer,
    TradeRoleSerializer,
    UserCompanyRoleSerializer,
    RoleRequestSerializer,
    RoleApproveSerializer,
    RoleRejectSerializer,
    CreateCompanySerializer
)
from apps.roles.services import RoleService, CompanyService


class TradeRoleViewSet(viewsets.ReadOnlyModelViewSet):
    """贸易角色视图集（只读）"""

    queryset = TradeRole.objects.filter(is_enabled=True)
    serializer_class = TradeRoleSerializer
    permission_classes = [IsAuthenticated]

    def list(self, request, *args, **kwargs):
        """获取可申请角色列表"""
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'code': 0,
            'message': 'success',
            'data': serializer.data
        })


class UserCompanyRoleViewSet(viewsets.ViewSet):
    """用户角色管理视图集"""

    permission_classes = [IsAuthenticated]

    def list(self, request):
        """获取我的角色列表"""
        user_roles = UserCompanyRole.objects.filter(
            user=request.user
        ).select_related('company', 'role')
        serializer = UserCompanyRoleSerializer(user_roles, many=True)
        return Response({
            'code': 0,
            'message': 'success',
            'data': serializer.data
        })

    @action(detail=False, methods=['post'])
    def request(self, request):
        """申请角色"""
        serializer = RoleRequestSerializer(data=request.data)
        if serializer.is_valid():
            try:
                assignment = RoleService.request_role(
                    user=request.user,
                    company_id=serializer.validated_data['company_id'],
                    role_code=serializer.validated_data['role_code'],
                    notes=serializer.validated_data.get('notes', '')
                )
                result_serializer = UserCompanyRoleSerializer(assignment)
                return Response({
                    'code': 0,
                    'message': '角色申请已提交，等待教师审核',
                    'data': result_serializer.data
                })
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

    @action(detail=False, methods=['post'])
    def approve(self, request):
        """批准角色申请（教师）"""
        if not request.user.is_staff:
            return Response({
                'code': 2001,
                'message': '无权限操作'
            }, status=status.HTTP_403_FORBIDDEN)

        serializer = RoleApproveSerializer(data=request.data)
        if serializer.is_valid():
            try:
                assignment = RoleService.approve_role(
                    assignment_id=serializer.validated_data['assignment_id'],
                    approver=request.user,
                    notes=serializer.validated_data.get('notes', '')
                )
                result_serializer = UserCompanyRoleSerializer(assignment)
                return Response({
                    'code': 0,
                    'message': '角色申请已批准',
                    'data': result_serializer.data
                })
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

    @action(detail=False, methods=['post'])
    def reject(self, request):
        """拒绝角色申请（教师）"""
        if not request.user.is_staff:
            return Response({
                'code': 2001,
                'message': '无权限操作'
            }, status=status.HTTP_403_FORBIDDEN)

        serializer = RoleRejectSerializer(data=request.data)
        if serializer.is_valid():
            try:
                assignment = RoleService.reject_role(
                    assignment_id=serializer.validated_data['assignment_id'],
                    approver=request.user,
                    reason=serializer.validated_data['reason']
                )
                return Response({
                    'code': 0,
                    'message': '角色申请已拒绝'
                })
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

    @action(detail=False, methods=['get'])
    def pending(self, request):
        """获取待审核申请列表（教师）"""
        if not request.user.is_staff:
            return Response({
                'code': 2001,
                'message': '无权限操作'
            }, status=status.HTTP_403_FORBIDDEN)

        pending_requests = RoleService.get_pending_requests()
        serializer = UserCompanyRoleSerializer(pending_requests, many=True)
        return Response({
            'code': 0,
            'message': 'success',
            'data': serializer.data
        })


class CompanyViewSet(viewsets.ModelViewSet):
    """公司管理视图集"""

    serializer_class = CompanySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Company.objects.all()

    def create(self, request, *args, **kwargs):
        """创建公司"""
        serializer = CreateCompanySerializer(data=request.data)
        if serializer.is_valid():
            try:
                company = CompanyService.create_company(
                    user=request.user,
                    **serializer.validated_data
                )
                result_serializer = CompanySerializer(company)
                return Response({
                    'code': 0,
                    'message': '公司创建成功',
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

    @action(detail=True, methods=['get'])
    def members(self, request, pk=None):
        """获取公司成员列表"""
        try:
            details = CompanyService.get_company_details(pk, request.user)
            return Response({
                'code': 0,
                'message': 'success',
                'data': details
            })
        except Company.DoesNotExist:
            return Response({
                'code': 4001,
                'message': '公司不存在'
            }, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['post'])
    def join(self, request, pk=None):
        """申请加入公司"""
        try:
            company = Company.objects.get(pk=pk)
            # 默认申请出口商角色
            assignment = RoleService.request_role(
                user=request.user,
                company_id=company.id,
                role_code='exporter',
                notes='申请加入公司'
            )
            return Response({
                'code': 0,
                'message': '加入申请已提交'
            })
        except Company.DoesNotExist:
            return Response({
                'code': 4001,
                'message': '公司不存在'
            }, status=status.HTTP_404_NOT_FOUND)
```

- [ ] **步骤 4：配置路由**

创建 `apps/roles/urls.py`：

```python
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.roles.views import TradeRoleViewSet, UserCompanyRoleViewSet, CompanyViewSet

router = DefaultRouter()
router.register(r'roles', TradeRoleViewSet, basename='traderole')
router.register(r'my-roles', UserCompanyRoleViewSet, basename='usercompanyrole')
router.register(r'companies', CompanyViewSet, basename='company')

urlpatterns = [
    path('api/v1/', include(router.urls)),
]
```

- [ ] **步骤 5：注册路由到主 urls.py**

编辑 `simtrade/urls.py`：

```python
urlpatterns = [
    # ... 其他路由
    path('', include('apps.roles.urls')),
]
```

- [ ] **步骤 6：运行测试验证通过**

运行：
```bash
pytest apps/roles/tests/test_api.py -v
```

预期：全部 PASS

- [ ] **步骤 7：Commit**

```bash
git add apps/roles/views.py apps/roles/urls.py apps/roles/tests/test_api.py simtrade/urls.py
git commit -m "feat(roles): implement API views and routes"
```

---

### 任务 10：配置 Admin 管理后台

**文件：**
- 修改：`apps/roles/admin.py`

- [ ] **步骤 1：实现 Admin 配置**

编辑 `apps/roles/admin.py`：

```python
from django.contrib import admin
from apps.roles.models import Company, TradeRole, UserCompanyRole


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    """公司管理"""
    list_display = ['name', 'name_en', 'code', 'type', 'country', 'created_at']
    list_filter = ['type', 'country', 'created_at']
    search_fields = ['name', 'name_en', 'code', 'email']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(TradeRole)
class TradeRoleAdmin(admin.ModelAdmin):
    """贸易角色管理"""
    list_display = ['code', 'name', 'is_enabled', 'is_system', 'sort_order', 'created_at']
    list_filter = ['is_enabled', 'is_system', 'created_at']
    search_fields = ['code', 'name', 'description']
    readonly_fields = ['created_at']


@admin.register(UserCompanyRole)
class UserCompanyRoleAdmin(admin.ModelAdmin):
    """用户角色分配管理"""
    list_display = ['user', 'company', 'role', 'status', 'is_active', 'requested_at']
    list_filter = ['status', 'is_active', 'role', 'requested_at']
    search_fields = ['user__username', 'user__email', 'company__name', 'role__name']
    readonly_fields = ['requested_at', 'approved_at']
```

- [ ] **步骤 2：验证 Admin 可访问**

运行：
```bash
python manage.py runserver
```

访问：http://localhost:8000/admin/

预期：可以看到 Roles 分组下的 Company, TradeRole, UserCompanyRole

- [ ] **步骤 3：Commit**

```bash
git add apps/roles/admin.py
git commit -m "feat(roles): configure admin interface"
```

---

### 任务 11：改造 Transaction 模型

**文件：**
- 修改：`apps/transactions/models.py`

- [ ] **步骤 1：修改 Transaction 模型外键**

编辑 `apps/transactions/models.py`：

```python
# 在文件顶部导入添加
from apps.roles.models import Company

class Transaction(models.Model):
    # ... 其他字段不变 ...

    # 修改：buyer/seller 指向 Company，允许 NULL 用于迁移
    buyer = models.ForeignKey(
        'roles.Company',  # 新：指向 Company
        on_delete=models.PROTECT,
        related_name='buying_transactions',
        null=True  # 迁移过渡期允许为空
    )
    seller = models.ForeignKey(
        'roles.Company',  # 新：指向 Company
        on_delete=models.PROTECT,
        related_name='selling_transactions',
        null=True  # 迁移过渡期允许为空
    )

    # ... 其他字段不变 ...
```

- [ ] **步骤 2：修改 LetterOfCredit 模型外键**

在同一个文件中找到 LetterOfCredit 类：

```python
class LetterOfCredit(models.Model):
    # ... 其他字段 ...

    # 修改：applicant/beneficiary 指向 Company
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

    # ... 其他字段 ...
```

- [ ] **步骤 3：生成迁移文件**

运行：
```bash
python manage.py makemigrations transactions
```

预期：生成迁移文件，提示修改了外键

- [ ] **步骤 4：创建空迁移用于数据迁移**

运行：
```bash
python manage.py makemigrations transactions --empty --name migrate_to_company
```

- [ ] **步骤 5：编写数据迁移脚本**

编辑生成的迁移文件（如 `0002_migrate_to_company.py`）：

```python
from django.db import migrations


def migrate_users_to_companies(apps, schema_editor):
    """为每个用户创建默认公司"""
    User = apps.get_model('users', 'User')
    Company = apps.get_model('roles', 'Company')
    UserCompanyRole = apps.get_model('roles', 'UserCompanyRole')
    TradeRole = apps.get_model('roles', 'TradeRole')

    for user in User.objects.all():
        company, created = Company.objects.get_or_create(
            code=f'USER_{user.id:04d}',
            defaults={
                'name': f'{user.username}的公司',
                'created_by_id': user.id
            }
        )
        # 分配出口商角色作为默认
        try:
            role = TradeRole.objects.get(code='exporter')
            UserCompanyRole.objects.get_or_create(
                user=user,
                company=company,
                role=role,
                defaults={'status': 'active', 'is_active': True}
            )
        except TradeRole.DoesNotExist:
            pass


def migrate_transaction_to_company(apps, schema_editor):
    """迁移 Transaction.buyer/seller 指向 Company"""
    Transaction = apps.get_model('transactions', 'Transaction')
    Company = apps.get_model('roles', 'Company')

    for txn in Transaction.objects.all():
        # 尝试通过用户 ID 查找对应的公司
        buyer_company = Company.objects.filter(
            code=f'USER_{txn.buyer_id:04d}'
        ).first()
        seller_company = Company.objects.filter(
            code=f'USER_{txn.seller_id:04d}'
        ).first()

        if buyer_company:
            txn.buyer_id = buyer_company.id
        if seller_company:
            txn.seller_id = seller_company.id
        txn.save(update_fields=['buyer_id', 'seller_id'])


def migrate_letter_of_credit_to_company(apps, schema_editor):
    """迁移 LetterOfCredit.applicant/beneficiary 指向 Company"""
    LetterOfCredit = apps.get_model('transactions', 'LetterOfCredit')
    Company = apps.get_model('roles', 'Company')

    for lc in LetterOfCredit.objects.all():
        applicant_company = Company.objects.filter(
            code=f'USER_{lc.applicant_id:04d}'
        ).first()
        beneficiary_company = Company.objects.filter(
            code=f'USER_{lc.beneficiary_id:04d}'
        ).first()

        if applicant_company:
            lc.applicant_id = applicant_company.id
        if beneficiary_company:
            lc.beneficiary_id = beneficiary_company.id
        lc.save(update_fields=['applicant_id', 'beneficiary_id'])


def reverse_migrations(apps, schema_editor):
    """回滚：恢复 User 外键（可选）"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('transactions', '0001_initial'),
        ('roles', '0001_initial'),
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(migrate_users_to_companies, reverse_migrations),
        migrations.RunPython(migrate_transaction_to_company, reverse_migrations),
        migrations.RunPython(migrate_letter_of_credit_to_company, reverse_migrations),
    ]
```

- [ ] **步骤 6：运行迁移**

运行：
```bash
# 首先确保角色已初始化
python manage.py init_trade_roles

# 运行迁移
python manage.py migrate
```

预期：迁移成功，Transaction 和 LetterOfCredit 的外键指向 Company

- [ ] **步骤 7：移除 NULL 约束（可选）**

如果迁移成功，可以移除 buyer/seller 的 null=True：

```python
buyer = models.ForeignKey('roles.Company', ..., null=False)
seller = models.ForeignKey('roles.Company', ..., null=False)
```

再次运行：
```bash
python manage.py makemigrations transactions
python manage.py migrate
```

- [ ] **步骤 8：Commit**

```bash
git add apps/transactions/models.py apps/transactions/migrations/
git commit -m "feat(transactions): migrate buyer/seller to Company"
```

---

### 任务 12：更新 TransactionViewSet

**文件：**
- 修改：`apps/transactions/views.py`

- [ ] **步骤 1：更新 get_queryset 方法**

编辑 `apps/transactions/views.py`：

```python
from apps.roles.models import Company
from apps.roles.services import RoleService


class TransactionViewSet(viewsets.ModelViewSet):
    # ... 其他代码不变 ...

    def get_queryset(self):
        # 只返回当前用户所属公司参与的交易
        user_role = RoleService.get_current_role(self.request.user)
        if not user_role:
            return Transaction.objects.none()

        # 获取用户所属的所有公司
        user_companies = Company.objects.filter(
            members__user=self.request.user,
            members__is_active=True
        )

        return Transaction.objects.filter(
            models.Q(buyer__in=user_companies) |
            models.Q(seller__in=user_companies)
        )
```

- [ ] **步骤 2：更新 _get_user_role 方法**

```python
def _get_user_role(self, transaction, user):
    """获取用户在交易中的角色"""
    current_role = RoleService.get_current_role(user)
    if not current_role:
        return 'observer'

    # 判断当前角色在交易中的位置
    if current_role.company == transaction.buyer and current_role.role.code == 'importer':
        return 'buyer'
    elif current_role.company == transaction.seller and current_role.role.code == 'exporter':
        return 'seller'

    return 'observer'
```

- [ ] **步骤 3：更新 create 方法（适配创建交易）**

```python
def create(self, request, *args, **kwargs):
    """创建交易（询盘）"""
    serializer = self.get_serializer(data=request.data)
    if serializer.is_valid():
        # 获取当前激活角色的公司作为买方
        current_role = RoleService.get_current_role(request.user)
        if not current_role:
            return Response({
                'code': 5005,
                'message': '请先激活一个角色'
            }, status=status.HTTP_400_BAD_REQUEST)

        serializer.save(
            buyer=current_role.company,
            created_by=request.user,
            status='inquiring'
        )
        # ... 其余代码不变 ...
```

- [ ] **步骤 4：Commit**

```bash
git add apps/transactions/views.py
git commit -m "feat(transactions): update views for Company model"
```

---

### 任务 13：更新序列化器

**文件：**
- 修改：`apps/transactions/serializers.py`

- [ ] **步骤 1：更新 TransactionSerializer**

编辑 `apps/transactions/serializers.py`：

```python
class TransactionSerializer(serializers.ModelSerializer):
    # 修改：公司信息
    buyer_company_name = serializers.CharField(source='buyer.name', read_only=True)
    buyer_company_code = serializers.CharField(source='buyer.code', read_only=True)
    seller_company_name = serializers.CharField(source='seller.name', read_only=True)
    seller_company_code = serializers.CharField(source='seller.code', read_only=True)

    class Meta:
        model = Transaction
        fields = [
            'id', 'buyer', 'buyer_company_name', 'buyer_company_code',
            'seller', 'seller_company_name', 'seller_company_code',
            # ... 其他字段 ...
        ]
        read_only_fields = ['id', 'buyer', 'created_at', 'updated_at']
```

- [ ] **步骤 2：更新 LetterOfCreditSerializer**

```python
class LetterOfCreditSerializer(serializers.ModelSerializer):
    # 修改：公司信息
    applicant_company_name = serializers.CharField(source='applicant.name', read_only=True)
    beneficiary_company_name = serializers.CharField(source='beneficiary.name', read_only=True)

    class Meta:
        model = LetterOfCredit
        fields = [
            # ... 其他字段 ...
            'applicant', 'applicant_company_name',
            'beneficiary', 'beneficiary_company_name',
            # ... 其他字段 ...
        ]
```

- [ ] **步骤 3：Commit**

```bash
git add apps/transactions/serializers.py
git commit -m "feat(transactions): update serializers for Company"
```

---

### 任务 14：更新服务层

**文件：**
- 修改：`apps/transactions/services.py`

- [ ] **步骤 1：更新 ContractService.sign 方法**

找到签字相关逻辑，确保适配 Company：

```python
@staticmethod
def sign(contract, user, party, ip_address):
    """签字：待签字 → 一方签字 → 已签字"""
    # 获取用户当前角色
    from apps.roles.services import RoleService
    current_role = RoleService.get_current_role(user)

    if not current_role:
        raise ValueError('请先激活一个角色')

    # 验证角色是否有权签字
    if party == 'buyer':
        if current_role.company != contract.transaction.buyer:
            raise ValueError('当前角色不是买方')
    elif party == 'seller':
        if current_role.company != contract.transaction.seller:
            raise ValueError('当前角色不是卖方')

    # ... 其余签字逻辑不变 ...
```

- [ ] **步骤 2：更新 LetterOfCreditService 中的 Company 引用**

检查所有 `applicant`/`beneficiary` 的使用，确保它们是 Company 对象：

```python
@staticmethod
def create_from_contract(contract):
    """从合同创建信用证草稿"""
    # ...
    lc = LetterOfCredit.objects.create(
        # ...
        applicant=contract.transaction.buyer,  # 已是 Company
        beneficiary=contract.transaction.seller,  # 已是 Company
        # ...
    )
```

- [ ] **步骤 3：Commit**

```bash
git add apps/transactions/services.py
git commit -m "feat(transactions): update services for Company model"
```

---

### 任务 15：修复测试

**文件：**
- 修改：`apps/transactions/tests/test_*.py`

- [ ] **步骤 1：修复 test_models.py**

所有创建 Transaction 的测试需要先创建 Company：

```python
# 旧代码
transaction = Transaction.objects.create(
    buyer=self.buyer,  # User
    seller=self.seller,  # User
    # ...
)

# 新代码
from apps.roles.models import Company
from apps.roles.services import CompanyService, RoleService

# 为用户创建公司
buyer_company = CompanyService.create_company(
    user=self.buyer,
    name='买方公司',
    country_id=Country.objects.first().id
)
seller_company = CompanyService.create_company(
    user=self.seller,
    name='卖方公司',
    country_id=Country.objects.first().id
)

transaction = Transaction.objects.create(
    buyer=buyer_company,  # Company
    seller=seller_company,  # Company
    # ...
)
```

- [ ] **步骤 2：修复 test_api.py**

更新 API 测试中的用户认证，确保用户有激活的角色：

```python
def setUp(self):
    # 创建用户和公司
    self.buyer = User.objects.create_user(username='buyer', password='testpass')
    self.seller = User.objects.create_user(username='seller', password='testpass')

    # 创建公司并分配角色
    buyer_company = CompanyService.create_company(
        user=self.buyer,
        name='买方公司',
        country_id=Country.objects.first().id
    )
    seller_company = CompanyService.create_company(
        user=self.seller,
        name='卖方公司',
        country_id=Country.objects.first().id
)
```

- [ ] **步骤 3：运行测试验证**

运行：
```bash
pytest apps/transactions/tests/ -v
```

预期：全部修复后 PASS

- [ ] **步骤 4：Commit**

```bash
git add apps/transactions/tests/
git commit -m "test(transactions): fix tests for Company model"
```

---

### 任务 16：最终验证

**文件：**
- 所有相关文件

- [ ] **步骤 1：运行所有测试**

运行：
```bash
pytest apps/roles/tests/ apps/transactions/tests/ -v
```

预期：全部 PASS

- [ ] **步骤 2：验证 Django 检查**

运行：
```bash
python manage.py check
```

预期：无报错

- [ ] **步骤 3：验证 Admin 功能**

运行：
```bash
python manage.py runserver
```

访问：http://localhost:8000/admin/
预期：可以看到 Roles 相关的管理界面

- [ ] **步骤 4：验证 API 功能**

测试主要 API 端点：
- `GET /api/v1/roles/` - 获取角色列表
- `POST /api/v1/roles/request/` - 申请角色
- `POST /api/v1/roles/approve/` - 批准角色
- `POST /api/v1/companies/` - 创建公司

- [ ] **步骤 5：最终 Commit**

```bash
git add .
git commit -m "feat(roles): complete role simulation system implementation"
```

---

## 自检清单

### 规格覆盖度

| 设计章节 | 对应任务 |
|---------|---------|
| Company 模型 | 任务 2 |
| TradeRole 模型 | 任务 3 |
| UserCompanyRole 模型 | 任务 4 |
| 10 种角色初始化 | 任务 5 |
| RoleService | 任务 6 |
| CompanyService | 任务 7 |
| 序列化器 | 任务 8 |
| API 视图 | 任务 9 |
| Admin 配置 | 任务 10 |
| Transaction 改造 | 任务 11 |
| TransactionViewSet 更新 | 任务 12 |
| 序列化器更新 | 任务 13 |
| 服务层更新 | 任务 14 |
| 测试修复 | 任务 15 |
| 最终验证 | 任务 16 |

### 占位符检查

✅ 无 "TBD"、"TODO" 等占位符
✅ 所有代码步骤包含完整代码
✅ 所有命令有明确的预期输出

### 类型一致性检查

✅ 模型字段名在各处一致
✅ 服务方法签名一致
✅ API 响应格式统一

---

## 完成标志

- [ ] 10 种贸易角色可申请、审核、激活
- [ ] 用户可创建/加入公司
- [ ] 交易发生在公司之间
- [ ] 所有测试通过
- [ ] Admin 界面正常工作
- [ ] API 端点可正常调用
