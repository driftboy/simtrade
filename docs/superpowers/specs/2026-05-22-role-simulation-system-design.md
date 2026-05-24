# 角色模拟系统设计文档

**版本**: 1.0
**日期**: 2026-05-22
**作者**: Claude
**状态**: 待审核

---

## 1. 概述

### 1.1 设计目标

实现 SimTrade 平台的角色模拟功能，支持学生在多贸易角色间切换，以团队协作模式完成外贸业务流程。

### 1.2 核心决策

| 决策点 | 选择 | 理由 |
|--------|------|------|
| 架构模式 | 独立 App (roles/) | 职责清晰，易于扩展 |
| 角色切换 | 分配模式 + 单一激活 | 学生被分配固定角色，同时只能激活一个 |
| Company 模型 | 多学生共享一公司 | 支持团队协作教学 |
| 角色范围 | 全部 10 种贸易角色 | 完整覆盖外贸业务 |
| 分配权限 | 混合模式 | 学生选意向 + 教师审核 |
| Transaction 改造 | buyer/seller → Company | 交易发生在公司之间 |

---

## 2. 数据模型设计

### 2.1 模型关系图

```
User (existing)
  ↓ 1:N
UserCompanyRole (junction)
  ↓ N:1
Company ────────────────→ TradeRole
  ↓ 1:N                    ↓
Transaction             UserCompanyRole
```

### 2.2 Company 模型

```python
class Company(models.Model):
    """虚拟公司 — 学生的企业实体"""
    name = models.CharField('公司名称', max_length=200, unique=True)
    name_en = models.CharField('英文名称', max_length=200, blank=True)
    code = models.CharField('公司代码', max_length=20, unique=True)
    type = models.CharField('企业类型', max_length=50, blank=True)
    country = models.ForeignKey('core.Country', on_delete=models.PROTECT,
                              null=True, related_name='companies')
    address = models.TextField('地址', blank=True)
    phone = models.CharField('电话', max_length=50, blank=True)
    email = models.EmailField('邮箱', blank=True)
    logo = models.URLField('Logo URL', blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                 null=True, related_name='created_companies')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'companies'
        verbose_name = '公司'
        verbose_name_plural = '公司'
        ordering = ['-created_at']
```

### 2.3 TradeRole 模型

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

    code = models.CharField('角色代码', max_length=50, choices=RoleType.choices, unique=True)
    name = models.CharField('角色名称', max_length=100)
    description = models.TextField('职责说明')
    is_enabled = models.BooleanField('是否启用', default=True)
    is_system = models.BooleanField('系统预置', default=True)
    sort_order = models.IntegerField('排序', default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'trade_roles'
        verbose_name = '贸易角色'
        verbose_name_plural = '贸易角色'
        ordering = ['sort_order', 'code']
```

### 2.4 UserCompanyRole 模型

```python
class UserCompanyRole(models.Model):
    """用户-公司-角色分配（支持多学生共享一公司）"""
    class Status(models.TextChoices):
        PENDING = 'pending', '待审核'
        APPROVED = 'approved', '已批准'
        REJECTED = 'rejected', '已拒绝'
        ACTIVE = 'active', '激活中'
        SUSPENDED = 'suspended', '已暂停'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                           related_name='trade_roles')
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='members')
    role = models.ForeignKey(TradeRole, on_delete=models.CASCADE, related_name='assignees')
    status = models.CharField('状态', max_length=20, choices=Status.choices, default=PENDING)
    is_active = models.BooleanField('当前激活', default=False)
    requested_at = models.DateTimeField('申请时间', auto_now_add=True)
    approved_at = models.DateTimeField('批准时间', null=True, blank=True)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                   null=True, related_name='approved_role_assignments')
    notes = models.TextField('备注', blank=True)

    class Meta:
        db_table = 'user_company_roles'
        unique_together = [['user', 'company', 'role']]
        verbose_name = '用户角色分配'
        verbose_name_plural = '用户角色分配'
        ordering = ['-requested_at']
```

---

## 3. Transaction 模型改造

### 3.1 字段变更

| 字段 | 原类型 | 新类型 | 说明 |
|------|--------|--------|------|
| buyer | FK(User) | FK(Company) | 买方公司 |
| seller | FK(User) | FK(Company) | 卖方公司 |

保留字段：`created_by` 仍指向 User（记录操作人）

### 3.2 LetterOfCredit 同步改造

```python
class LetterOfCredit(models.Model):
    # 同样改为 Company
    applicant = models.ForeignKey('roles.Company', ...)  # 进口商公司
    beneficiary = models.ForeignKey('roles.Company', ...)  # 出口商公司
```

---

## 4. 服务层设计

### 4.1 RoleService

```python
class RoleService:
    """角色分配和切换服务"""

    @staticmethod
    def request_role(user, company_id, role_code, notes=''):
        """学生申请角色
        返回: UserCompanyRole 实例
        """

    @staticmethod
    def approve_role(assignment_id, approver, notes=''):
        """教师批准角色申请（同时激活该角色）
        返回: UserCompanyRole 实例
        """

    @staticmethod
    def reject_role(assignment_id, approver, reason):
        """教师拒绝角色申请
        返回: UserCompanyRole 实例
        """

    @staticmethod
    def activate_role(user, assignment_id):
        """激活角色（单一激活，会停用其他角色）
        返回: UserCompanyRole 实例
        """

    @staticmethod
    def get_current_role(user):
        """获取用户当前激活的角色
        返回: UserCompanyRole 或 None
        """

    @staticmethod
    def get_pending_requests(user=None):
        """获取待审核申请
        返回: QuerySet
        """

    @staticmethod
    def switch_context(user):
        """获取用户当前角色上下文
        返回: dict {company, role, permissions}
        """
```

### 4.2 CompanyService

```python
class CompanyService:
    """公司管理服务"""

    @staticmethod
    def create_company(user, name, name_en='', country_id=None, **kwargs):
        """创建公司（学生或教师）
        返回: Company 实例
        """

    @staticmethod
    def get_company_details(company_id, user):
        """获取公司详情（含成员列表）
        返回: dict
        """

    @staticmethod
    def update_company(company_id, user, **kwargs):
        """更新公司信息（仅成员或教师可操作）
        返回: Company 实例
        """

    @staticmethod
    def add_member(company_id, user_id, role_code, invited_by):
        """邀请用户加入公司（教师操作）
        返回: UserCompanyRole 实例
        """

    @staticmethod
    def remove_member(company_id, user_id, operator):
        """移除公司成员
        返回: bool
        """
```

---

## 5. API 接口设计

### 5.1 角色管理 API

| 端点 | 方法 | 说明 | 权限 |
|------|------|------|------|
| `/api/v1/roles/` | GET | 获取可申请角色列表 | 登录 |
| `/api/v1/roles/my/` | GET | 获取我的角色列表 | 登录 |
| `/api/v1/roles/request/` | POST | 申请角色 | 登录 |
| `/api/v1/roles/{id}/activate/` | POST | 激活角色 | 本人 |
| `/api/v1/roles/approve/` | POST | 批准申请 | 教师 |
| `/api/v1/roles/reject/` | POST | 拒绝申请 | 教师 |
| `/api/v1/roles/pending/` | GET | 获取待审核申请列表 | 教师 |

### 5.2 公司管理 API

| 端点 | 方法 | 说明 | 权限 |
|------|------|------|------|
| `/api/v1/companies/` | GET | 获取公司列表 | 登录 |
| `/api/v1/companies/` | POST | 创建公司 | 登录 |
| `/api/v1/companies/{id}/` | GET | 获取公司详情 | 登录 |
| `/api/v1/companies/{id}/` | PUT | 更新公司信息 | 成员/教师 |
| `/api/v1/companies/{id}/members/` | GET | 获取公司成员 | 成员 |
| `/api/v1/companies/{id}/join/` | POST | 申请加入公司 | 登录 |

### 5.3 请求/响应格式

**申请角色请求：**
```json
{
  "company_id": 1,
  "role_code": "exporter",
  "notes": "我想扮演出口商角色"
}
```

**批准角色请求：**
```json
{
  "assignment_id": 123,
  "notes": "批准通过"
}
```

---

## 6. 初始化数据

### 6.1 10 种贸易角色初始数据

| 代码 | 名称 | 描述 | 排序 |
|------|------|------|------|
| exporter | 出口商 | 销售货物到国外，负责制作单证、安排运输 | 1 |
| importer | 进口商 | 从国外购买货物，负责开证、付款 | 2 |
| factory | 工厂 | 生产/供应商品，接收订单、安排生产 | 3 |
| bank | 银行 | 信用证开立、议付、结算业务 | 4 |
| customs | 海关 | 报关审核、征税、放行 | 5 |
| shipping | 货运公司 | 订舱、运输、签发提单 | 6 |
| insurance | 保险公司 | 承保、签发保险单 | 7 |
| inspection | 商检机构 | 商品检验、签发检验证书 | 8 |
| forex | 外汇局 | 出口收汇核销管理 | 9 |
| tax | 税务局 | 出口退税审核 | 10 |

### 6.2 初始化命令

```python
# apps/roles/management/commands/init_trade_roles.py

class Command(BaseCommand):
    help = '初始化 10 种贸易角色'

    def handle(self, *args, **options):
        roles_data = [
            {'code': 'exporter', 'name': '出口商', 'description': '...', 'sort_order': 1},
            # ... 其他 9 种
        ]
        for data in roles_data:
            TradeRole.objects.get_or_create(code=data['code'], defaults=data)
```

---

## 7. 迁移策略

### 7.1 迁移步骤

```
阶段 1: 创建新模型
  └── 生成 Company, TradeRole, UserCompanyRole 迁移文件

阶段 2: 数据迁移
  └── 为每个现有 User 创建默认 Company
  └── 迁移 Transaction.buyer/seller 指向新的 Company
  └── 迁移 LetterOfCredit.applicant/beneficiary

阶段 3: 更新业务逻辑
  └── 更新 services.py
  └── 更新 views.py
  └── 更新 serializers.py

阶段 4: 更新测试
  └── 修复 test_models.py
  └── 修复 test_services.py
  └── 修复 test_api.py

阶段 5: 清理
  └── 删除过渡期 NULL 约束
```

### 7.2 数据迁移脚本

```python
# apps/transactions/migrations/0002_migrate_to_company.py

def migrate_users_to_companies(apps, schema_editor):
    """为每个用户创建默认公司"""
    User = apps.get_model('users', 'User')
    Company = apps.get_model('roles', 'Company')
    UserCompanyRole = apps.get_model('roles', 'UserCompanyRole')

    for user in User.objects.all():
        company, created = Company.objects.get_or_create(
            code=f'USER_{user.id:04d}',
            defaults={
                'name': f'{user.username}的公司',
                'created_by': user
            }
        )
        # 分配出口商角色作为默认
        UserCompanyRole.objects.get_or_create(
            user=user,
            company=company,
            role__code='exporter',
            defaults={'status': 'active', 'is_active': True}
        )

def migrate_transaction_to_company(apps, schema_editor):
    """迁移 Transaction.buyer/seller"""
    Transaction = apps.get_model('transactions', 'Transaction')
    Company = apps.get_model('roles', 'Company')
    User = apps.get_model('users', 'User')

    for txn in Transaction.objects.all():
        # 查找用户对应的默认公司
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
        txn.save()
```

---

## 8. 测试策略

### 8.1 单元测试

- `apps/roles/tests/test_models.py` - 模型测试
- `apps/roles/tests/test_services.py` - 服务测试
- `apps/roles/tests/test_serializers.py` - 序列化器测试

### 8.2 API 测试

- `apps/roles/tests/test_api.py` - API 端点测试
- `apps/roles/tests/test_permissions.py` - 权限测试

### 8.3 集成测试

- `apps/roles/tests/test_integration.py` - 完整流程测试
  - 学生申请角色 → 教师批准 → 学生激活角色
  - 多学生共享公司场景
  - 角色切换场景

### 8.4 迁移测试

- `apps/transactions/tests/test_migration.py` - 验证迁移前后数据一致性

---

## 9. 前端集成（简要）

### 9.1 角色切换器

```javascript
// 显示当前激活角色，允许切换
<div class="role-switcher">
  <span>当前角色: {{ current_role.company.name }} - {{ current_role.role.name }}</span>
  <button onclick="showRoleModal()">切换角色</button>
</div>
```

### 9.2 权限控制

```javascript
// 根据当前角色控制界面元素显示
if (currentRole.role.code === 'exporter') {
  // 显示出口商相关操作
}
```

---

## 10. 后续扩展

- 角色权限细化（不同角色的操作权限）
- 角色工作台（独立界面）
- 角色间消息系统
- 角色协作日志
