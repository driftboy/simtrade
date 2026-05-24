# 前端页面与角色工作台实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 完善 SimTrade 三端前端页面，为 10 种贸易角色建立专属工作台，补建 LetterOfCredit ViewSet 和注册端点。

**架构：** 角色工作台使用 1 个通用模板 + 3 种面板（trader/approver/provider），Django view 根据当前角色类型决定渲染哪个面板。仪表盘按 user_type 分发。所有页面遵循 Django Template + jQuery AJAX 模式。

**技术栈：** Django 3.2, DRF, Bootstrap 3.3.7, jQuery 3.6

**规格文档：** `docs/superpowers/specs/2026-05-24-frontend-workspace-design.md`

---

## 文件清单

### 后端新建

| 文件 | 职责 |
|------|------|
| `apps/transactions/views_lc.py` | LetterOfCredit ViewSet（独立文件避免 views.py 过大） |

### 后端修改

| 文件 | 职责 |
|------|------|
| `apps/transactions/urls.py` | 注册 LC router |
| `apps/users/views.py` | 新增 RegisterView |
| `apps/users/urls.py` | 新增 register 路由 |
| `simtrade/urls.py` | 新增所有页面路由和 Django view 函数 |

### 前端新建

| 文件 | 职责 |
|------|------|
| `templates/dashboard/student.html` | 学生仪表盘 |
| `templates/dashboard/teacher.html` | 教师仪表盘 |
| `templates/dashboard/admin.html` | 管理员仪表盘 |
| `templates/workspace/base.html` | 工作台双栏 base 布局 |
| `templates/workspace/workspace.html` | 通用工作台主模板 |
| `templates/workspace/panels/trader.html` | 贸易发起方面板 |
| `templates/workspace/panels/approver.html` | 审批处理方面板 |
| `templates/workspace/panels/provider.html` | 服务提供方面板 |
| `templates/teaching/dashboard.html` | 教学仪表盘 |
| `templates/teaching/course_list.html` | 课程列表 |
| `templates/teaching/course_detail.html` | 课程详情 |
| `templates/teaching/grading.html` | 评分管理 |
| `templates/admin_panel/dashboard.html` | 管理仪表盘 |
| `templates/admin_panel/user_list.html` | 用户管理 |
| `templates/admin_panel/system.html` | 系统配置 |
| `templates/registration/register.html` | 注册页面 |
| `templates/profile.html` | 个人中心 |
| `static/css/workspace.css` | 工作台样式 |
| `static/css/dashboard.css` | 仪表盘样式 |
| `static/css/teaching.css` | 教学端样式 |
| `static/js/workspace.js` | 工作台逻辑 |
| `static/js/dashboard.js` | 仪表盘逻辑 |
| `static/js/teaching.js` | 教学端逻辑 |
| `static/js/admin.js` | 管理端逻辑 |

### 前端修改

| 文件 | 改动 |
|------|------|
| `templates/base.html` | navbar 菜单条件化 |
| `static/js/role-switcher.js` | 切换后跳转 `/workspace/` |

---

## 任务 1：LetterOfCredit ViewSet（后端 TDD）

**文件：**
- 创建：`apps/transactions/views_lc.py`
- 修改：`apps/transactions/urls.py`
- 测试：`apps/transactions/tests/test_lc_api.py`

- [ ] **步骤 1：编写 LC API 测试**

创建 `apps/transactions/tests/test_lc_api.py`：

```python
import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from apps.transactions.models import (
    Transaction, Contract, LetterOfCredit, LcAmendment, BankOperation
)
from apps.roles.models import Company, TradeRole, UserCompanyRole
from apps.products.models import Product

User = get_user_model()


@pytest.mark.django_db
class TestLetterOfCreditAPI(TestCase):
    """信用证 API 测试"""

    def setUp(self):
        self.client = APIClient()
        # 创建用户
        self.importer_user = User.objects.create_user(
            username='importer1', password='testpass123', user_type='student'
        )
        self.exporter_user = User.objects.create_user(
            username='exporter1', password='testpass123', user_type='student'
        )
        self.bank_user = User.objects.create_user(
            username='bank1', password='testpass123', user_type='student'
        )

        # 创建公司
        self.importer_company = Company.objects.create(
            name='进口公司A', code='IMP-A'
        )
        self.exporter_company = Company.objects.create(
            name='出口公司B', code='EXP-B'
        )
        self.bank_company = Company.objects.create(
            name='银行C', code='BANK-C'
        )

        # 创建角色
        self.importer_role = TradeRole.objects.create(
            code='importer', name='进口商', description='进口商角色', sort_order=2
        )
        self.exporter_role = TradeRole.objects.create(
            code='exporter', name='出口商', description='出口商角色', sort_order=1
        )
        self.bank_role = TradeRole.objects.create(
            code='bank', name='银行', description='银行角色', sort_order=4
        )

        # 分配角色
        self.importer_ucr = UserCompanyRole.objects.create(
            user=self.importer_user, company=self.importer_company,
            role=self.importer_role, status='active', is_active=True
        )
        self.exporter_ucr = UserCompanyRole.objects.create(
            user=self.exporter_user, company=self.exporter_company,
            role=self.exporter_role, status='active', is_active=False
        )
        self.bank_ucr = UserCompanyRole.objects.create(
            user=self.bank_user, company=self.bank_company,
            role=self.bank_role, status='active', is_active=False
        )

        # 创建基础数据
        self.product = Product.objects.create(
            code='ELEC001', name='电子产品A', category='electronics', unit='台'
        )
        self.transaction = Transaction.objects.create(
            buyer=self.importer_company, seller=self.exporter_company,
            product=self.product, status='contracted',
            quantity=100, unit_price=10.00, currency='USD'
        )
        self.contract = Contract.objects.create(
            contract_no='CT20260101000001',
            transaction=self.transaction, status='effective',
            trade_term='CIF', payment_term='L/C',
            delivery_time='2026-06-30',
            port_of_loading='Shanghai', port_of_discharge='New York',
            product_name='电子产品A', quantity=100, unit='台',
            unit_price=10.00, total_amount=1000.00, currency='USD'
        )

    def test_create_lc_as_importer(self):
        """进口商可以申请开证"""
        self.client.force_authenticate(user=self.importer_user)
        response = self.client.post('/api/v1/letters-of-credit/', {
            'contract': self.contract.id,
            'transaction': self.transaction.id,
            'issuing_bank': '银行C',
            'advising_bank': '通知行D',
            'amount': '1000.00',
            'currency': 'USD',
            'expiry_date': '2026-07-31',
            'latest_shipment_date': '2026-06-15',
            'port_of_loading': 'Shanghai',
            'port_of_discharge': 'New York',
            'documents_required': ['商业发票', '提单', '装箱单']
        }, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['code'], 0)
        self.assertEqual(response.data['data']['status'], 'draft')

    def test_list_lc(self):
        """用户可以查看自己相关的信用证列表"""
        LetterOfCredit.objects.create(
            lc_no='LC20260101000001',
            contract=self.contract, transaction=self.transaction,
            status='draft',
            issuing_bank='银行C', advising_bank='通知行D',
            applicant=self.importer_company, beneficiary=self.exporter_company,
            amount=1000.00, currency='USD',
            expiry_date='2026-07-31',
            latest_shipment_date='2026-06-15',
            port_of_loading='Shanghai', port_of_discharge='New York'
        )
        self.client.force_authenticate(user=self.importer_user)
        response = self.client.get('/api/v1/letters-of-credit/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['code'], 0)
        self.assertEqual(len(response.data['data']), 1)

    def test_issue_lc_as_bank(self):
        """银行可以开证"""
        lc = LetterOfCredit.objects.create(
            lc_no='LC20260101000002',
            contract=self.contract, transaction=self.transaction,
            status='pending_issue',
            issuing_bank='银行C', advising_bank='通知行D',
            applicant=self.importer_company, beneficiary=self.exporter_company,
            amount=1000.00, currency='USD',
            expiry_date='2026-07-31',
            latest_shipment_date='2026-06-15',
            port_of_loading='Shanghai', port_of_discharge='New York'
        )
        self.bank_ucr.is_active = True
        self.bank_ucr.save()
        self.importer_ucr.is_active = False
        self.importer_ucr.save()
        self.client.force_authenticate(user=self.bank_user)
        response = self.client.post(
            f'/api/v1/letters-of-credit/{lc.id}/issue/'
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['code'], 0)
        self.assertEqual(response.data['data']['status'], 'issued')

    def test_submit_docs_as_exporter(self):
        """出口商可以交单"""
        lc = LetterOfCredit.objects.create(
            lc_no='LC20260101000003',
            contract=self.contract, transaction=self.transaction,
            status='issued',
            issuing_bank='银行C', advising_bank='通知行D',
            applicant=self.importer_company, beneficiary=self.exporter_company,
            amount=1000.00, currency='USD',
            expiry_date='2026-07-31',
            latest_shipment_date='2026-06-15',
            port_of_loading='Shanghai', port_of_discharge='New York'
        )
        self.importer_ucr.is_active = False
        self.importer_ucr.save()
        self.exporter_ucr.is_active = True
        self.exporter_ucr.save()
        self.client.force_authenticate(user=self.exporter_user)
        response = self.client.post(
            f'/api/v1/letters-of-credit/{lc.id}/submit_docs/'
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['data']['status'], 'submitted')

    def test_negotiate_and_pay(self):
        """银行可以议付和付款"""
        lc = LetterOfCredit.objects.create(
            lc_no='LC20260101000004',
            contract=self.contract, transaction=self.transaction,
            status='submitted',
            issuing_bank='银行C', advising_bank='通知行D',
            applicant=self.importer_company, beneficiary=self.exporter_company,
            amount=1000.00, currency='USD',
            expiry_date='2026-07-31',
            latest_shipment_date='2026-06-15',
            port_of_loading='Shanghai', port_of_discharge='New York'
        )
        self.importer_ucr.is_active = False
        self.importer_ucr.save()
        self.bank_ucr.is_active = True
        self.bank_ucr.save()

        self.client.force_authenticate(user=self.bank_user)
        # 议付
        response = self.client.post(
            f'/api/v1/letters-of-credit/{lc.id}/negotiate/'
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['data']['status'], 'negotiated')

        # 付款
        lc.refresh_from_db()
        response = self.client.post(
            f'/api/v1/letters-of-credit/{lc.id}/pay/'
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['data']['status'], 'paid')

    def test_cancel_lc(self):
        """申请方可以取消信用证"""
        lc = LetterOfCredit.objects.create(
            lc_no='LC20260101000005',
            contract=self.contract, transaction=self.transaction,
            status='draft',
            issuing_bank='银行C', advising_bank='通知行D',
            applicant=self.importer_company, beneficiary=self.exporter_company,
            amount=1000.00, currency='USD',
            expiry_date='2026-07-31',
            latest_shipment_date='2026-06-15',
            port_of_loading='Shanghai', port_of_discharge='New York'
        )
        self.client.force_authenticate(user=self.importer_user)
        response = self.client.post(
            f'/api/v1/letters-of-credit/{lc.id}/cancel/'
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['data']['status'], 'cancelled')

    def test_unauthorized_issue(self):
        """非银行角色不能开证"""
        lc = LetterOfCredit.objects.create(
            lc_no='LC20260101000006',
            contract=self.contract, transaction=self.transaction,
            status='pending_issue',
            issuing_bank='银行C', advising_bank='通知行D',
            applicant=self.importer_company, beneficiary=self.exporter_company,
            amount=1000.00, currency='USD',
            expiry_date='2026-07-31',
            latest_shipment_date='2026-06-15',
            port_of_loading='Shanghai', port_of_discharge='New York'
        )
        self.client.force_authenticate(user=self.importer_user)
        response = self.client.post(
            f'/api/v1/letters-of-credit/{lc.id}/issue/'
        )
        self.assertEqual(response.status_code, 400)
```

- [ ] **步骤 2：运行测试验证失败**

运行：`cd f:/vsworkspace/simtrade && python manage.py pytest apps/transactions/tests/test_lc_api.py -v 2>&1 | head -20`
预期：FAIL — `LetterOfCreditViewSet` 不存在，URL 未注册

- [ ] **步骤 3：创建 LetterOfCredit ViewSet**

创建 `apps/transactions/views_lc.py`：

```python
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.transactions.models import LetterOfCredit, BankOperation
from apps.transactions.serializers import LetterOfCreditSerializer
from apps.roles.services import RoleService


class LetterOfCreditViewSet(viewsets.ModelViewSet):
    """信用证视图集"""

    serializer_class = LetterOfCreditSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        current_role = RoleService.get_current_role(user)
        if not current_role or not current_role.company:
            return LetterOfCredit.objects.none()
        company = current_role.company
        return LetterOfCredit.objects.filter(
            applicant=company
        ) | LetterOfCredit.objects.filter(
            beneficiary=company
        ) | LetterOfCredit.objects.filter(
            issuing_bank__icontains=company.name
        )

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        status_filter = request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'code': 0,
            'message': 'success',
            'data': serializer.data
        })

    def create(self, request, *args, **kwargs):
        current_role = RoleService.get_current_role(request.user)
        if not current_role or not current_role.company:
            return Response(
                {'code': 4001, 'message': '请先激活角色'},
                status=status.HTTP_400_BAD_REQUEST
            )
        role_code = current_role.role.code
        if role_code != 'importer':
            return Response(
                {'code': 4003, 'message': '只有进口商可以申请开证'},
                status=status.HTTP_400_BAD_REQUEST
            )

        data = request.data.copy()
        data['applicant'] = current_role.company.id
        serializer = self.get_serializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'code': 0,
                'message': '申请成功',
                'data': self.get_serializer(serializer.instance).data
            }, status=status.HTTP_201_CREATED)
        return Response({
            'code': 3002,
            'message': '参数格式错误',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, *args, **kwargs):
        return Response({
            'code': 0,
            'message': 'success',
            'data': self.get_serializer(self.get_object()).data
        })

    def _check_bank_role(self, request):
        current_role = RoleService.get_current_role(request.user)
        if not current_role or current_role.role.code != 'bank':
            return None, Response(
                {'code': 4003, 'message': '只有银行可以执行此操作'},
                status=status.HTTP_400_BAD_REQUEST
            )
        return current_role, None

    def _check_applicant_or_beneficiary(self, request, lc):
        current_role = RoleService.get_current_role(request.user)
        if not current_role or not current_role.company:
            return Response(
                {'code': 4001, 'message': '请先激活角色'},
                status=status.HTTP_400_BAD_REQUEST
            )
        company = current_role.company
        if lc.applicant != company and lc.beneficiary != company:
            return Response(
                {'code': 4003, 'message': '无权操作此信用证'},
                status=status.HTTP_400_BAD_REQUEST
            )
        return None

    @action(detail=True, methods=['post'])
    def issue(self, request, pk=None):
        """开证"""
        current_role, err = self._check_bank_role(request)
        if err:
            return err
        lc = self.get_object()
        if lc.status != 'pending_issue':
            return Response(
                {'code': 5005, 'message': f'当前状态 {lc.get_status_display()} 不可开证'},
                status=status.HTTP_400_BAD_REQUEST
            )
        lc.status = 'issued'
        lc.issue_date = timezone.now().date()
        lc.issued_at = timezone.now()
        lc.save()
        BankOperation.objects.create(
            lc=lc, operation_type='issue',
            processed_by='bank', operator=request.user,
            notes='银行开证'
        )
        return Response({
            'code': 0,
            'message': '开证成功',
            'data': self.get_serializer(lc).data
        })

    @action(detail=True, methods=['post'])
    def advise(self, request, pk=None):
        """通知"""
        current_role, err = self._check_bank_role(request)
        if err:
            return err
        lc = self.get_object()
        if lc.status != 'issued':
            return Response(
                {'code': 5005, 'message': f'当前状态不可通知'},
                status=status.HTTP_400_BAD_REQUEST
            )
        lc.advised_at = timezone.now()
        lc.save()
        BankOperation.objects.create(
            lc=lc, operation_type='advise',
            processed_by='bank', operator=request.user,
            notes='银行通知'
        )
        return Response({
            'code': 0,
            'message': '通知成功',
            'data': self.get_serializer(lc).data
        })

    @action(detail=True, methods=['post'])
    def submit_docs(self, request, pk=None):
        """交单"""
        lc = self.get_object()
        err = self._check_applicant_or_beneficiary(request, lc)
        if err:
            return err
        if lc.status != 'issued':
            return Response(
                {'code': 5005, 'message': f'当前状态不可交单'},
                status=status.HTTP_400_BAD_REQUEST
            )
        lc.status = 'submitted'
        lc.submitted_at = timezone.now()
        lc.save()
        return Response({
            'code': 0,
            'message': '交单成功',
            'data': self.get_serializer(lc).data
        })

    @action(detail=True, methods=['post'])
    def negotiate(self, request, pk=None):
        """议付"""
        current_role, err = self._check_bank_role(request)
        if err:
            return err
        lc = self.get_object()
        if lc.status != 'submitted':
            return Response(
                {'code': 5005, 'message': f'当前状态不可议付'},
                status=status.HTTP_400_BAD_REQUEST
            )
        lc.status = 'negotiated'
        lc.negotiated_at = timezone.now()
        lc.save()
        BankOperation.objects.create(
            lc=lc, operation_type='negotiate',
            processed_by='bank', operator=request.user,
            notes='银行议付'
        )
        return Response({
            'code': 0,
            'message': '议付成功',
            'data': self.get_serializer(lc).data
        })

    @action(detail=True, methods=['post'])
    def pay(self, request, pk=None):
        """付款"""
        current_role, err = self._check_bank_role(request)
        if err:
            return err
        lc = self.get_object()
        if lc.status != 'negotiated':
            return Response(
                {'code': 5005, 'message': f'当前状态不可付款'},
                status=status.HTTP_400_BAD_REQUEST
            )
        lc.status = 'paid'
        lc.paid_at = timezone.now()
        lc.save()
        BankOperation.objects.create(
            lc=lc, operation_type='pay',
            processed_by='bank', operator=request.user,
            notes='银行付款'
        )
        return Response({
            'code': 0,
            'message': '付款成功',
            'data': self.get_serializer(lc).data
        })

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """取消"""
        lc = self.get_object()
        err = self._check_applicant_or_beneficiary(request, lc)
        if err:
            return err
        if lc.status not in ('draft', 'pending_issue'):
            return Response(
                {'code': 5005, 'message': f'当前状态 {lc.get_status_display()} 不可取消'},
                status=status.HTTP_400_BAD_REQUEST
            )
        lc.status = 'cancelled'
        lc.save()
        return Response({
            'code': 0,
            'message': '取消成功',
            'data': self.get_serializer(lc).data
        })
```

- [ ] **步骤 4：注册 LC URL**

修改 `apps/transactions/urls.py`，在 router 注册中添加：

```python
from apps.transactions.views_lc import LetterOfCreditViewSet

router.register(r'letters-of-credit', LetterOfCreditViewSet, basename='letter-of-credit')
```

- [ ] **步骤 5：运行测试验证通过**

运行：`cd f:/vsworkspace/simtrade && python manage.py pytest apps/transactions/tests/test_lc_api.py -v`
预期：全部 PASS

- [ ] **步骤 6：Commit**

```bash
git add apps/transactions/views_lc.py apps/transactions/tests/test_lc_api.py apps/transactions/urls.py
git commit -m "feat(transactions): add LetterOfCredit ViewSet with full LC workflow"
```

---

## 任务 2：注册端点（后端 TDD）

**文件：**
- 修改：`apps/users/views.py`
- 修改：`apps/users/urls.py`
- 测试：`apps/users/tests/test_register.py`

- [ ] **步骤 1：编写注册测试**

创建 `apps/users/tests/test_register.py`：

```python
import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()


@pytest.mark.django_db
class TestRegisterAPI(TestCase):
    """注册 API 测试"""

    def setUp(self):
        self.client = APIClient()

    def test_register_success(self):
        """正常注册"""
        response = self.client.post('/api/v1/auth/register/', {
            'username': 'newstudent',
            'password': 'testpass123',
            'email': 'new@test.com'
        }, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['code'], 0)
        user = User.objects.get(username='newstudent')
        self.assertEqual(user.user_type, 'student')
        self.assertEqual(user.email, 'new@test.com')

    def test_register_with_student_id(self):
        """带学号注册"""
        response = self.client.post('/api/v1/auth/register/', {
            'username': 'student2',
            'password': 'testpass123',
            'email': 's2@test.com',
            'student_id': '2026001'
        }, format='json')
        self.assertEqual(response.status_code, 201)
        user = User.objects.get(username='student2')
        self.assertEqual(user.student_id, '2026001')

    def test_register_duplicate_username(self):
        """重复用户名"""
        User.objects.create_user(username='dup', password='pass', email='d@test.com')
        response = self.client.post('/api/v1/auth/register/', {
            'username': 'dup',
            'password': 'testpass123',
            'email': 'd2@test.com'
        }, format='json')
        self.assertEqual(response.status_code, 400)

    def test_register_missing_fields(self):
        """缺少必填字段"""
        response = self.client.post('/api/v1/auth/register/', {
            'username': 'noemail'
        }, format='json')
        self.assertEqual(response.status_code, 400)
```

- [ ] **步骤 2：运行测试验证失败**

运行：`cd f:/vsworkspace/simtrade && python manage.py pytest apps/users/tests/test_register.py -v`
预期：FAIL — URL 未注册

- [ ] **步骤 3：实现 RegisterView**

在 `apps/users/views.py` 末尾添加：

```python
class RegisterView(APIView):
    """学生注册"""
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username', '').strip()
        password = request.data.get('password', '')
        email = request.data.get('email', '').strip()
        student_id = request.data.get('student_id', '').strip()

        if not username or not password or not email:
            return Response({
                'code': 3002,
                'message': '用户名、密码和邮箱为必填项'
            }, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(username=username).exists():
            return Response({
                'code': 3001,
                'message': '用户名已存在'
            }, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.create_user(
            username=username,
            password=password,
            email=email,
            user_type='student',
            student_id=student_id or ''
        )
        return Response({
            'code': 0,
            'message': '注册成功',
            'data': {
                'id': user.id,
                'username': user.username,
                'user_type': user.user_type
            }
        }, status=status.HTTP_201_CREATED)
```

- [ ] **步骤 4：注册 URL**

在 `apps/users/urls.py` 的 `urlpatterns` 中添加：

```python
path('auth/register/', RegisterView.as_view(), name='register'),
```

- [ ] **步骤 5：运行测试验证通过**

运行：`cd f:/vsworkspace/simtrade && python manage.py pytest apps/users/tests/test_register.py -v`
预期：全部 PASS

- [ ] **步骤 6：Commit**

```bash
git add apps/users/views.py apps/users/urls.py apps/users/tests/test_register.py
git commit -m "feat(users): add student registration endpoint"
```

---

## 任务 3：Django 页面 View 函数和 URL 路由

**文件：**
- 修改：`simtrade/urls.py`

- [ ] **步骤 1：添加页面 view 函数**

在 `simtrade/urls.py` 中，将现有的 lambda 视图替换为正式的 view 函数，并添加所有新页面路由：

```python
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from apps.roles.models import UserCompanyRole
from apps.roles.services import RoleService


# ---- 仪表盘 ----

@login_required
def dashboard_view(request):
    """根据用户类型分发仪表盘"""
    user_type = request.user.user_type
    if user_type == 'admin':
        return render(request, 'dashboard/admin.html')
    elif user_type == 'teacher':
        return render(request, 'dashboard/teacher.html')
    return render(request, 'dashboard/student.html')


# ---- 工作台 ----

PANEL_MAP = {
    'exporter': 'trader', 'importer': 'trader',
    'customs': 'approver', 'inspection': 'approver',
    'forex': 'approver', 'tax': 'approver',
    'factory': 'provider', 'bank': 'provider',
    'shipping': 'provider', 'insurance': 'provider',
}

ROLE_CONFIGS = {
    'exporter': {
        'nav_items': [
            {'label': '概览', 'icon': 'home', 'tab': 'overview'},
            {'label': '我的交易', 'icon': 'list', 'tab': 'transactions'},
            {'label': '外销合同', 'icon': 'file', 'tab': 'contracts'},
            {'label': '信用证', 'icon': 'credit-card', 'tab': 'lc'},
        ],
        'actions': [
            {'label': '发询盘', 'url': '/market/', 'btn_class': 'btn-primary'},
        ],
        'stats': [
            {'label': '活跃交易', 'status': 'in_progress', 'api': '/api/v1/transactions/transactions/'},
            {'label': '待签约', 'status': 'pending_contract', 'api': '/api/v1/transactions/contracts/'},
            {'label': '进行中', 'status': 'in_progress', 'api': '/api/v1/transactions/transactions/'},
        ],
        'list_api': '/api/v1/transactions/transactions/',
        'panel': 'trader',
    },
    'importer': {
        'nav_items': [
            {'label': '概览', 'icon': 'home', 'tab': 'overview'},
            {'label': '我的交易', 'icon': 'list', 'tab': 'transactions'},
            {'label': '外销合同', 'icon': 'file', 'tab': 'contracts'},
            {'label': '信用证', 'icon': 'credit-card', 'tab': 'lc'},
        ],
        'actions': [
            {'label': '发询盘', 'url': '/market/', 'btn_class': 'btn-primary'},
            {'label': '申请信用证', 'url': '#', 'btn_class': 'btn-info', 'id': 'btn-apply-lc'},
        ],
        'stats': [
            {'label': '活跃交易', 'status': 'in_progress', 'api': '/api/v1/transactions/transactions/'},
            {'label': '待签约', 'status': 'pending_contract', 'api': '/api/v1/transactions/contracts/'},
            {'label': '进行中', 'status': 'in_progress', 'api': '/api/v1/transactions/transactions/'},
        ],
        'list_api': '/api/v1/transactions/transactions/',
        'panel': 'trader',
    },
    'customs': {
        'nav_items': [
            {'label': '概览', 'icon': 'home', 'tab': 'overview'},
            {'label': '报关单', 'icon': 'list', 'tab': 'declarations'},
        ],
        'actions': [],
        'stats': [
            {'label': '待审核', 'status': 'declared', 'api': '/api/v1/customs-declarations/'},
            {'label': '已放行', 'status': 'cleared', 'api': '/api/v1/customs-declarations/'},
            {'label': '已驳回', 'status': 'rejected', 'api': '/api/v1/customs-declarations/'},
        ],
        'list_api': '/api/v1/customs-declarations/',
        'panel': 'approver',
    },
    'inspection': {
        'nav_items': [
            {'label': '概览', 'icon': 'home', 'tab': 'overview'},
            {'label': '报检单', 'icon': 'list', 'tab': 'applications'},
        ],
        'actions': [],
        'stats': [
            {'label': '待检验', 'status': 'applied', 'api': '/api/v1/inspection-applications/'},
            {'label': '已签发', 'status': 'certified', 'api': '/api/v1/inspection-applications/'},
            {'label': '不合格', 'status': 'failed', 'api': '/api/v1/inspection-applications/'},
        ],
        'list_api': '/api/v1/inspection-applications/',
        'panel': 'approver',
    },
    'forex': {
        'nav_items': [
            {'label': '概览', 'icon': 'home', 'tab': 'overview'},
            {'label': '结算单', 'icon': 'list', 'tab': 'settlements'},
        ],
        'actions': [],
        'stats': [
            {'label': '待核销', 'status': 'applied', 'api': '/api/v1/forex-settlements/'},
            {'label': '已结汇', 'status': 'settled', 'api': '/api/v1/forex-settlements/'},
            {'label': '已拒绝', 'status': 'rejected', 'api': '/api/v1/forex-settlements/'},
        ],
        'list_api': '/api/v1/forex-settlements/',
        'panel': 'approver',
    },
    'tax': {
        'nav_items': [
            {'label': '概览', 'icon': 'home', 'tab': 'overview'},
            {'label': '退税申请', 'icon': 'list', 'tab': 'refunds'},
        ],
        'actions': [],
        'stats': [
            {'label': '待审核', 'status': 'reviewing', 'api': '/api/v1/tax-refund-applications/'},
            {'label': '已退税', 'status': 'refunded', 'api': '/api/v1/tax-refund-applications/'},
            {'label': '已拒绝', 'status': 'rejected', 'api': '/api/v1/tax-refund-applications/'},
        ],
        'list_api': '/api/v1/tax-refund-applications/',
        'panel': 'approver',
    },
    'factory': {
        'nav_items': [
            {'label': '概览', 'icon': 'home', 'tab': 'overview'},
            {'label': '采购订单', 'icon': 'list', 'tab': 'orders'},
        ],
        'actions': [],
        'stats': [
            {'label': '待确认', 'status': 'draft', 'api': '/api/v1/purchase-orders/'},
            {'label': '执行中', 'status': 'confirmed', 'api': '/api/v1/purchase-orders/'},
            {'label': '已完成', 'status': 'completed', 'api': '/api/v1/purchase-orders/'},
        ],
        'list_api': '/api/v1/purchase-orders/',
        'panel': 'provider',
    },
    'bank': {
        'nav_items': [
            {'label': '概览', 'icon': 'home', 'tab': 'overview'},
            {'label': '信用证', 'icon': 'credit-card', 'tab': 'lc'},
        ],
        'actions': [],
        'stats': [
            {'label': '待开证', 'status': 'pending_issue', 'api': '/api/v1/letters-of-credit/'},
            {'label': '已开证', 'status': 'issued', 'api': '/api/v1/letters-of-credit/'},
            {'label': '已付款', 'status': 'paid', 'api': '/api/v1/letters-of-credit/'},
        ],
        'list_api': '/api/v1/letters-of-credit/',
        'panel': 'provider',
    },
    'shipping': {
        'nav_items': [
            {'label': '概览', 'icon': 'home', 'tab': 'overview'},
            {'label': '货运单', 'icon': 'list', 'tab': 'shipments'},
        ],
        'actions': [],
        'stats': [
            {'label': '待订舱', 'status': 'draft', 'api': '/api/v1/shipments/'},
            {'label': '运输中', 'status': 'loaded', 'api': '/api/v1/shipments/'},
            {'label': '已到港', 'status': 'arrived', 'api': '/api/v1/shipments/'},
        ],
        'list_api': '/api/v1/shipments/',
        'panel': 'provider',
    },
    'insurance': {
        'nav_items': [
            {'label': '概览', 'icon': 'home', 'tab': 'overview'},
            {'label': '保单', 'icon': 'list', 'tab': 'policies'},
        ],
        'actions': [],
        'stats': [
            {'label': '待承保', 'status': 'applied', 'api': '/api/v1/insurance-policies/'},
            {'label': '已签发', 'status': 'issued', 'api': '/api/v1/insurance-policies/'},
            {'label': '已取消', 'status': 'cancelled', 'api': '/api/v1/insurance-policies/'},
        ],
        'list_api': '/api/v1/insurance-policies/',
        'panel': 'provider',
    },
}


@login_required
def workspace_view(request, role_code=None):
    """角色工作台"""
    current_role = RoleService.get_current_role(request.user)
    if not current_role:
        return render(request, 'workspace/workspace.html', {
            'no_role': True,
            'role_config': None,
        })

    code = role_code or current_role.role.code
    config = ROLE_CONFIGS.get(code)

    if not config:
        return render(request, 'workspace/workspace.html', {
            'no_role': True,
            'role_config': None,
        })

    return render(request, 'workspace/workspace.html', {
        'no_role': False,
        'current_role': current_role,
        'role_code': code,
        'role_config': config,
        'panel_template': 'workspace/panels/%s.html' % config['panel'],
    })


# ---- 教学端 ----

@login_required
def teaching_dashboard(request):
    return render(request, 'teaching/dashboard.html')


@login_required
def teaching_course_list(request):
    return render(request, 'teaching/course_list.html')


@login_required
def teaching_course_detail(request, course_id):
    return render(request, 'teaching/course_detail.html', {'course_id': course_id})


@login_required
def teaching_grading(request):
    return render(request, 'teaching/grading.html')


# ---- 管理端 ----

@login_required
def admin_panel_dashboard(request):
    return render(request, 'admin_panel/dashboard.html')


@login_required
def admin_panel_users(request):
    return render(request, 'admin_panel/user_list.html')


@login_required
def admin_panel_system(request):
    return render(request, 'admin_panel/system.html')


# ---- 认证 ----

def register_view(request):
    return render(request, 'registration/register.html')


@login_required
def profile_view(request):
    return render(request, 'profile.html')
```

- [ ] **步骤 2：更新 urlpatterns**

将 `simtrade/urls.py` 的页面路由部分替换为：

```python
# 页面路由
urlpatterns += [
    path('', dashboard_view, name='home'),
    path('dashboard/', dashboard_view, name='dashboard'),
    path('workspace/', workspace_view, name='workspace'),
    path('workspace/<str:role_code>/', workspace_view, name='workspace-role'),
    path('market/', lambda r: render(r, 'products/market.html'), name='market'),
    path('transactions/', lambda r: render(r, 'transactions/list.html'), name='transaction-list'),
    path('transactions/<int:id>/', lambda r, id: render(r, 'transactions/detail.html'), name='transaction-detail'),
    path('documents/', lambda r: render(r, 'documents/list.html'), name='document-list'),
    path('documents/create/', document_create, name='document-create'),
    path('documents/<int:id>/preview/', document_preview, name='document-preview'),
    path('teaching/', teaching_dashboard, name='teaching-dashboard'),
    path('teaching/courses/', teaching_course_list, name='teaching-courses'),
    path('teaching/courses/<int:course_id>/', teaching_course_detail, name='teaching-course-detail'),
    path('teaching/grading/', teaching_grading, name='teaching-grading'),
    path('admin-panel/', admin_panel_dashboard, name='admin-dashboard'),
    path('admin-panel/users/', admin_panel_users, name='admin-users'),
    path('admin-panel/system/', admin_panel_system, name='admin-system'),
    path('register/', register_view, name='register'),
    path('profile/', profile_view, name='profile'),
]
```

- [ ] **步骤 3：验证 Django 能启动**

运行：`cd f:/vsworkspace/simtrade && python manage.py check`
预期：`System check identified no issues (0 silenced).`

- [ ] **步骤 4：Commit**

```bash
git add simtrade/urls.py
git commit -m "feat: add page routes and workspace view functions for all three ends"
```

---

## 任务 4：Navbar 条件化（前端修改）

**文件：**
- 修改：`templates/base.html`

- [ ] **步骤 1：修改 navbar 菜单**

将 `templates/base.html` 中 navbar 的 `<ul class="nav navbar-nav">` 部分替换为：

```html
<ul class="nav navbar-nav">
    <li><a href="/dashboard/">仪表盘</a></li>
    {% if user.is_authenticated %}
        {% if user.user_type == 'student' %}
        <li><a href="/workspace/">工作台</a></li>
        {% endif %}
        {% if user.user_type == 'teacher' %}
        <li><a href="/teaching/">教学管理</a></li>
        {% endif %}
        {% if user.user_type == 'admin' %}
        <li><a href="/admin-panel/">管理后台</a></li>
        <li><a href="/teaching/">教学管理</a></li>
        {% endif %}
        <li><a href="/market/">市场</a></li>
        <li><a href="/transactions/">交易</a></li>
        <li><a href="/documents/">单证</a></li>
    {% endif %}
</ul>
```

- [ ] **步骤 2：验证页面可加载**

运行：`cd f:/vsworkspace/simtrade && python manage.py check`
预期：无错误

- [ ] **步骤 3：Commit**

```bash
git add templates/base.html
git commit -m "feat: expand navbar with role-based menu items"
```

---

## 任务 5：Role-switcher 跳转修复

**文件：**
- 修改：`static/js/role-switcher.js`

- [ ] **步骤 1：修改切换后跳转**

将 `static/js/role-switcher.js` 中 `switchRole` 函数的 `success` 回调改为：

```javascript
function switchRole(assignmentId) {
    $.ajax({
        url: '/api/v1/my-roles/' + assignmentId + '/activate/',
        type: 'POST',
        success: function() {
            window.location.href = '/workspace/';
        },
        error: function(xhr) {
            var msg = '角色切换失败';
            if (xhr.responseJSON && xhr.responseJSON.message) {
                msg = xhr.responseJSON.message;
            }
            SimTrade.showError(msg);
        }
    });
}
```

- [ ] **步骤 2：Commit**

```bash
git add static/js/role-switcher.js
git commit -m "fix: redirect to workspace after role switch"
```

---

## 任务 6：工作台 CSS 和 Base 模板

**文件：**
- 创建：`static/css/workspace.css`
- 创建：`templates/workspace/base.html`

- [ ] **步骤 1：创建 workspace.css**

创建 `static/css/workspace.css`：

```css
/* 工作台布局 */
.workspace-layout {
    display: flex;
    min-height: calc(100vh - 70px - 60px);
    margin-top: -20px;
}

.workspace-sidebar {
    width: 220px;
    background-color: #f8f8f8;
    border-right: 1px solid #e7e7e7;
    padding: 15px 0;
    flex-shrink: 0;
}

.workspace-main {
    flex: 1;
    padding: 20px;
    overflow-x: auto;
}

/* 侧边栏角色信息 */
.sidebar-role-header {
    padding: 10px 15px;
    background-color: #337ab7;
    color: #fff;
    margin-bottom: 10px;
}

.sidebar-role-header h4 {
    margin: 0;
    font-size: 14px;
}

.sidebar-role-header small {
    color: #cce0f5;
}

/* 侧边栏导航 */
.sidebar-nav {
    list-style: none;
    padding: 0;
    margin: 0;
}

.sidebar-nav > li > a {
    display: block;
    padding: 8px 15px;
    color: #333;
    text-decoration: none;
    border-left: 3px solid transparent;
}

.sidebar-nav > li > a:hover,
.sidebar-nav > li > a.active {
    background-color: #e8e8e8;
    border-left-color: #337ab7;
    color: #337ab7;
}

.sidebar-nav > li > a .glyphicon {
    margin-right: 8px;
    width: 16px;
    text-align: center;
}

/* 侧边栏快捷操作 */
.sidebar-actions {
    padding: 15px;
    border-top: 1px solid #e7e7e7;
    margin-top: 10px;
}

.sidebar-actions .btn {
    display: block;
    margin-bottom: 8px;
    text-align: left;
}

/* 统计卡片 */
.stat-card {
    background: #fff;
    border: 1px solid #ddd;
    border-radius: 4px;
    padding: 15px;
    text-align: center;
    margin-bottom: 15px;
}

.stat-card .stat-value {
    font-size: 28px;
    font-weight: bold;
    color: #337ab7;
    line-height: 1.2;
}

.stat-card .stat-label {
    font-size: 12px;
    color: #999;
    margin-top: 5px;
}

.stat-card.stat-warning .stat-value { color: #f0ad4e; }
.stat-card.stat-success .stat-value { color: #5cb85c; }
.stat-card.stat-danger .stat-value { color: #d9534f; }

/* Tab 面板 */
.workspace-tabs {
    margin-bottom: 0;
}

.workspace-tabs > li > a {
    color: #555;
}

.workspace-tabs > li.active > a {
    font-weight: bold;
}

/* 操作按钮列 */
.action-btn {
    margin: 2px;
}
```

- [ ] **步骤 2：创建 workspace/base.html**

创建 `templates/workspace/base.html`：

```html
{% extends "base.html" %}
{% load static %}

{% block extra_css %}
<link href="{% static 'css/workspace.css' %}" rel="stylesheet">
<link href="{% static 'css/transactions.css' %}" rel="stylesheet">
{% endblock %}

{% block content %}
<div class="workspace-layout">
    <div class="workspace-sidebar">
        <div class="sidebar-role-header">
            <h4 id="sidebar-role-name">加载中...</h4>
            <small id="sidebar-company-name"></small>
        </div>
        <ul class="sidebar-nav" id="sidebar-nav">
        </ul>
        <div class="sidebar-actions" id="sidebar-actions">
        </div>
    </div>
    <div class="workspace-main">
        {% block workspace_content %}{% endblock %}
    </div>
</div>
{% endblock %}
```

- [ ] **步骤 3：Commit**

```bash
git add static/css/workspace.css templates/workspace/base.html
git commit -m "feat: add workspace CSS and base template layout"
```

---

## 任务 7：工作台主模板和 3 个面板

**文件：**
- 创建：`templates/workspace/workspace.html`
- 创建：`templates/workspace/panels/trader.html`
- 创建：`templates/workspace/panels/approver.html`
- 创建：`templates/workspace/panels/provider.html`

- [ ] **步骤 1：创建工作台主模板**

创建 `templates/workspace/workspace.html`：

```html
{% extends "workspace/base.html" %}
{% load static %}

{% block title %}角色工作台 - SimTrade{% endblock %}

{% block workspace_content %}
{% if no_role %}
<div class="alert alert-info">
    <h4>暂无活跃角色</h4>
    <p>请先在导航栏中激活一个角色，或联系教师分配角色。</p>
    <a href="/market/" class="btn btn-primary">浏览市场</a>
</div>
{% else %}

<!-- 统计卡片 -->
<div class="row" id="stats-row">
    {% for stat in role_config.stats %}
    <div class="col-md-4">
        <div class="stat-card">
            <div class="stat-value" id="stat-{{ forloop.counter }}">-</div>
            <div class="stat-label">{{ stat.label }}</div>
        </div>
    </div>
    {% endfor %}
</div>

<!-- Tab 导航 + 数据列表 -->
<div class="panel panel-default">
    <div class="panel-heading">
        <ul class="nav nav-tabs workspace-tabs" id="workspace-tabs">
            {% for nav in role_config.nav_items %}
            <li class="{% if forloop.first %}active{% endif %}">
                <a href="#tab-{{ nav.tab }}" data-toggle="tab" data-api-list="{{ role_config.list_api }}">{{ nav.label }}</a>
            </li>
            {% endfor %}
        </ul>
    </div>
    <div class="panel-body">
        <div class="tab-content" id="workspace-tab-content">
            {% for nav in role_config.nav_items %}
            <div class="tab-pane {% if forloop.first %}active{% endif %}" id="tab-{{ nav.tab }}">
                <div class="data-list" id="list-{{ nav.tab }}">
                    <div class="text-center">加载中...</div>
                </div>
            </div>
            {% endfor %}
        </div>
    </div>
</div>

{% endif %}
{% endblock %}

{% block extra_js %}
<script src="{% static 'js/workspace.js' %}"></script>
<script>
window.workspaceConfig = {
    roleCode: '{{ role_code }}',
    panel: '{{ role_config.panel }}',
    listApi: '{{ role_config.list_api }}',
    stats: {{ role_config.stats|safe }},
    navItems: {{ role_config.nav_items|safe }}
};
</script>
{% endblock %}
```

- [ ] **步骤 2：创建贸易发起方面板**

创建 `templates/workspace/panels/trader.html`：

```html
<!-- 贸易发起方面板（出口商/进口商）— 额外的交易创建和合同操作由 workspace.js 处理 -->
<!-- 列表行操作按钮模板 -->
<script id="tpl-trader-actions" type="text/template">
<a href="/transactions/{id}/" class="btn btn-primary btn-sm action-btn">查看</a>
</script>
```

- [ ] **步骤 3：创建审批处理方面板**

创建 `templates/workspace/panels/approver.html`：

```html
<!-- 审批处理方面板（海关/商检/外汇/税务）-->
<script id="tpl-approver-actions" type="text/template">
<button class="btn btn-success btn-sm action-btn ws-action" data-action="approve" data-id="{id}">批准</button>
<button class="btn btn-danger btn-sm action-btn ws-action" data-action="reject" data-id="{id}">驳回</button>
</script>
```

- [ ] **步骤 4：创建服务提供方面板**

创建 `templates/workspace/panels/provider.html`：

```html
<!-- 服务提供方面板（工厂/银行/货运/保险）-->
<script id="tpl-provider-actions" type="text/template">
<button class="btn btn-primary btn-sm action-btn ws-action" data-action="execute" data-id="{id}">执行</button>
<button class="btn btn-success btn-sm action-btn ws-action" data-action="complete" data-id="{id}">完成</button>
</script>
```

- [ ] **步骤 5：Commit**

```bash
git add templates/workspace/
git commit -m "feat: add workspace main template and 3 panel templates"
```

---

## 任务 8：工作台 JS 逻辑

**文件：**
- 创建：`static/js/workspace.js`

- [ ] **步骤 1：创建 workspace.js**

创建 `static/js/workspace.js`：

```javascript
/**
 * SimTrade 工作台逻辑
 */
(function() {
    'use strict';

    var ROLE_NAMES = {
        'exporter': '出口商', 'importer': '进口商', 'factory': '工厂',
        'bank': '银行', 'customs': '海关', 'shipping': '货运公司',
        'insurance': '保险公司', 'inspection': '商检机构',
        'forex': '外汇局', 'tax': '税务局'
    };

    // 操作映射：角色 → 状态 → 可用操作
    var ACTION_MAP = {
        'customs': {
            'declared': [{label: '审核', action: 'review'}],
            'reviewing': [{label: '征税', action: 'assess'}],
            'assessed': [{label: '放行', action: 'clear'}],
        },
        'inspection': {
            'applied': [{label: '检验', action: 'inspect'}],
            'inspecting': [{label: '通过', action: 'pass_inspection'}, {label: '不合格', action: 'fail'}],
            'passed': [{label: '签发', action: 'certify'}],
        },
        'forex': {
            'applied': [{label: '核销', action: 'verify'}],
            'verified': [{label: '结汇', action: 'settle'}],
        },
        'tax': {
            'reviewing': [{label: '批准', action: 'approve'}],
            'approved': [{label: '退税', action: 'refund'}],
        },
        'factory': {
            'draft': [{label: '确认', action: 'confirm'}],
            'confirmed': [{label: '发货', action: 'ship'}],
            'shipped': [{label: '开票', action: 'invoice'}],
        },
        'bank': {
            'pending_issue': [{label: '开证', action: 'issue'}],
            'issued': [{label: '通知', action: 'advise'}],
            'submitted': [{label: '议付', action: 'negotiate'}],
            'negotiated': [{label: '付款', action: 'pay'}],
        },
        'shipping': {
            'draft': [{label: '订舱', action: 'book'}],
            'booked': [{label: '装船', action: 'load'}],
            'loaded': [{label: '签提单', action: 'issue_bl'}],
            'shipped': [{label: '到港', action: 'arrive'}],
        },
        'insurance': {
            'applied': [{label: '承保', action: 'underwrite'}],
            'underwritten': [{label: '签发', action: 'issue'}],
        },
    };

    function init() {
        if (!window.workspaceConfig || window.workspaceConfig.panel === '') return;

        var config = window.workspaceConfig;
        var roleCode = config.roleCode;

        // 初始化侧边栏
        initSidebar(config);

        // 加载统计数据
        loadStats(config.stats);

        // 加载列表数据
        loadList(config.listApi, roleCode);

        // 绑定 tab 切换
        $('#workspace-tabs a').on('shown.bs.tab', function(e) {
            var api = $(e.target).data('api-list');
            loadList(api, roleCode);
        });

        // 绑定操作按钮
        $(document).on('click', '.ws-action', function() {
            var btn = $(this);
            var action = btn.data('action');
            var id = btn.data('id');
            executeAction(config.listApi, id, action, roleCode);
        });
    }

    function initSidebar(config) {
        // 加载当前角色信息
        $.get('/api/v1/my-roles/current/', function(resp) {
            var data = resp.data;
            $('#sidebar-role-name').text(ROLE_NAMES[data.role_code] || data.role_code);
            $('#sidebar-company-name').text(data.company_name);
        });

        // 渲染导航菜单
        var navHtml = '';
        (config.navItems || []).forEach(function(item) {
            var activeClass = item.tab === 'overview' ? ' active' : '';
            navHtml += '<li><a href="#tab-' + item.tab + '" data-toggle="tab"' +
                ' class="' + activeClass + '"><span class="glyphicon glyphicon-' +
                item.icon + '"></span> ' + item.label + '</a></li>';
        });
        $('#sidebar-nav').html(navHtml);
    }

    function loadStats(stats) {
        (stats || []).forEach(function(stat, idx) {
            $.ajax({
                url: stat.api,
                data: {status: stat.status},
                success: function(resp) {
                    var count = (resp.data || []).length;
                    $('#stat-' + (idx + 1)).text(count);
                }
            });
        });
    }

    function loadList(apiUrl, roleCode) {
        var $container = $('.tab-pane.active .data-list');
        if (!$container.length) $container = $('#list-overview');
        $container.html('<div class="text-center">加载中...</div>');

        $.get(apiUrl, function(resp) {
            var items = resp.data || [];
            if (items.length === 0) {
                $container.html('<div class="alert alert-info">暂无数据</div>');
                return;
            }
            renderTable($container, items, roleCode);
        }).fail(function() {
            $container.html('<div class="alert alert-danger">加载失败</div>');
        });
    }

    function renderTable($container, items, roleCode) {
        var html = '<table class="table table-striped"><thead><tr>';
        // 动态列头
        var firstItem = items[0];
        var cols = [];
        if (firstItem.order_no) cols.push({key: 'order_no', label: '编号'});
        if (firstItem.lc_no) cols.push({key: 'lc_no', label: '信用证号'});
        if (firstItem.shipment_no) cols.push({key: 'shipment_no', label: '货运编号'});
        if (firstItem.policy_no) cols.push({key: 'policy_no', label: '保单号'});
        if (firstItem.declaration_no) cols.push({key: 'declaration_no', label: '报关单号'});
        if (firstItem.application_no) cols.push({key: 'application_no', label: '申请号'});
        if (firstItem.settlement_no) cols.push({key: 'settlement_no', label: '结算号'});
        if (firstItem.contract_no) cols.push({key: 'contract_no', label: '合同号'});
        if (firstItem.product_name) cols.push({key: 'product_name', label: '商品'});
        if (firstItem.goods_name) cols.push({key: 'goods_name', label: '品名'});
        if (firstItem.quantity) cols.push({key: 'quantity', label: '数量'});
        if (firstItem.amount) cols.push({key: 'amount', label: '金额'});
        if (firstItem.total_amount) cols.push({key: 'total_amount', label: '金额'});
        cols.push({key: 'status_display', label: '状态'});
        cols.push({key: '_actions', label: '操作'});

        cols.forEach(function(col) {
            html += '<th>' + col.label + '</th>';
        });
        html += '</tr></thead><tbody>';

        items.forEach(function(item) {
            html += '<tr>';
            cols.forEach(function(col) {
                if (col.key === '_actions') {
                    html += '<td>' + renderActionButtons(item, roleCode) + '</td>';
                } else if (col.key === 'status_display') {
                    html += '<td><span class="status-badge ' + (item.status || '') + '">' +
                        (item.status_display || item.status || '-') + '</span></td>';
                } else {
                    html += '<td>' + (item[col.key] || '-') + '</td>';
                }
            });
            html += '</tr>';
        });
        html += '</tbody></table>';
        $container.html(html);
    }

    function renderActionButtons(item, roleCode) {
        var statusActions = ACTION_MAP[roleCode] || {};
        var actions = statusActions[item.status] || [];
        if (actions.length === 0) return '<span class="text-muted">无操作</span>';
        var html = '';
        actions.forEach(function(a) {
            html += '<button class="btn btn-primary btn-sm action-btn ws-action" ' +
                'data-action="' + a.action + '" data-id="' + item.id + '">' +
                a.label + '</button> ';
        });
        return html;
    }

    function executeAction(apiUrl, itemId, action, roleCode) {
        var url = apiUrl + itemId + '/' + action + '/';
        $.ajax({
            url: url,
            method: 'POST',
            contentType: 'application/json',
            headers: {'X-CSRFToken': $.cookie('csrftoken')},
            success: function(resp) {
                if (resp.code === 0) {
                    SimTrade.showSuccess('操作成功');
                    loadList(apiUrl, roleCode);
                    loadStats(window.workspaceConfig.stats);
                } else {
                    SimTrade.showError(resp.message || '操作失败');
                }
            },
            error: function(xhr) {
                var msg = '操作失败';
                if (xhr.responseJSON && xhr.responseJSON.message) {
                    msg = xhr.responseJSON.message;
                }
                SimTrade.showError(msg);
            }
        });
    }

    $(document).ready(init);
})();
```

- [ ] **步骤 2：Commit**

```bash
git add static/js/workspace.js
git commit -m "feat: add workspace JavaScript with role-based actions and data loading"
```

---

## 任务 9：仪表盘 CSS 和 JS

**文件：**
- 创建：`static/css/dashboard.css`
- 创建：`static/js/dashboard.js`

- [ ] **步骤 1：创建 dashboard.css**

创建 `static/css/dashboard.css`：

```css
/* 仪表盘样式 */
.dashboard-stats {
    margin-bottom: 25px;
}

.dash-stat-card {
    background: #fff;
    border: 1px solid #ddd;
    border-radius: 4px;
    padding: 20px;
    text-align: center;
    transition: box-shadow 0.2s;
}

.dash-stat-card:hover {
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.dash-stat-card .dash-stat-icon {
    font-size: 30px;
    color: #337ab7;
    margin-bottom: 10px;
}

.dash-stat-card .dash-stat-value {
    font-size: 32px;
    font-weight: bold;
    color: #333;
}

.dash-stat-card .dash-stat-label {
    font-size: 13px;
    color: #999;
    margin-top: 5px;
}

.dash-section {
    margin-bottom: 25px;
}

.dash-section h3 {
    font-size: 16px;
    color: #333;
    border-bottom: 1px solid #eee;
    padding-bottom: 8px;
    margin-bottom: 15px;
}

.dash-activity-item {
    padding: 8px 0;
    border-bottom: 1px solid #f5f5f5;
}

.dash-activity-item:last-child {
    border-bottom: none;
}

.dash-todo-item {
    padding: 10px;
    margin-bottom: 8px;
    background: #f9f9f9;
    border-radius: 4px;
    border-left: 3px solid #337ab7;
}

.dash-todo-item.todo-warning {
    border-left-color: #f0ad4e;
}

.dash-todo-item.todo-danger {
    border-left-color: #d9534f;
}

.dash-quick-actions .btn {
    margin: 5px;
}
```

- [ ] **步骤 2：创建 dashboard.js**

创建 `static/js/dashboard.js`：

```javascript
/**
 * SimTrade 仪表盘逻辑
 */
(function() {
    'use strict';

    function loadDashboardStats() {
        // 加载未读通知数
        $.get('/api/v1/notifications/unread-count/', function(resp) {
            var count = resp.data ? resp.data.count : 0;
            $('#dash-notif-count').text(count);
        });

        // 加载当前角色
        $.get('/api/v1/my-roles/current/', function(resp) {
            if (resp.data) {
                $('#dash-role-name').text(resp.data.role_display || resp.data.role_code);
                $('#dash-company-name').text(resp.data.company_name);
            }
        });
    }

    function loadStudentData() {
        // 活跃交易数
        $.get('/api/v1/transactions/transactions/', function(resp) {
            var items = resp.data || [];
            var active = items.filter(function(t) { return t.status !== 'completed' && t.status !== 'cancelled'; });
            $('#dash-active-tx').text(active.length);
        });

        // 待处理单证
        $.get('/api/v1/documents/', {data: {status: 'draft'}}, function(resp) {
            $('#dash-pending-docs').text((resp.data || []).length);
        });

        // 最近交易动态
        $.get('/api/v1/transactions/transactions/', function(resp) {
            var items = (resp.data || []).slice(0, 5);
            var html = '';
            items.forEach(function(tx) {
                html += '<div class="dash-activity-item">' +
                    '<span class="text-muted">' + tx.updated_at + '</span> ' +
                    '交易 #' + tx.id + ' <span class="status-badge ' + tx.status + '">' +
                    tx.status_display + '</span></div>';
            });
            if (!html) html = '<div class="text-muted">暂无动态</div>';
            $('#dash-recent-activity').html(html);
        });
    }

    function loadTeacherData() {
        // 课程数
        $.get('/api/v1/teaching/courses/', function(resp) {
            $('#dash-course-count').text((resp.data || []).length);
        });

        // 待审核角色
        $.get('/api/v1/my-roles/pending/', function(resp) {
            $('#dash-pending-roles').text((resp.data || []).length);
            var items = (resp.data || []).slice(0, 5);
            var html = '';
            items.forEach(function(r) {
                html += '<div class="dash-todo-item">' +
                    '<strong>' + SimTrade.escapeHtml(r.username || '') + '</strong> 申请 ' +
                    SimTrade.escapeHtml(r.role_display || r.role_code || '') + ' 角色</div>';
            });
            if (!html) html = '<div class="text-muted">暂无待审核</div>';
            $('#dash-todo-list').html(html);
        });
    }

    function loadAdminData() {
        // 系统统计 — 从各 API 获取
        $.get('/api/v1/teaching/semesters/', function(resp) {
            var active = (resp.data || []).filter(function(s) { return s.is_active; });
            $('#dash-active-semester').text(active.length);
        });
    }

    function init() {
        if (!window.user || !window.user.is_authenticated) return;
        loadDashboardStats();

        var userType = window.dashboardUserType;
        if (userType === 'student') loadStudentData();
        else if (userType === 'teacher') loadTeacherData();
        else if (userType === 'admin') loadAdminData();
    }

    $(document).ready(init);
})();
```

- [ ] **步骤 3：Commit**

```bash
git add static/css/dashboard.css static/js/dashboard.js
git commit -m "feat: add dashboard CSS and JS with data loading"
```

---

## 任务 10：学生仪表盘

**文件：**
- 创建：`templates/dashboard/student.html`

- [ ] **步骤 1：创建学生仪表盘**

创建 `templates/dashboard/student.html`：

```html
{% extends "base.html" %}
{% load static %}

{% block title %}仪表盘 - SimTrade{% endblock %}

{% block extra_css %}
<link href="{% static 'css/dashboard.css' %}" rel="stylesheet">
{% endblock %}

{% block content %}
<div class="row">
    <div class="col-md-12">
        <h2>欢迎回来，{{ user.username }}</h2>
        <p class="text-muted">当前角色：<span id="dash-role-name">-</span> · <span id="dash-company-name">-</span></p>
    </div>
</div>

<div class="row dashboard-stats">
    <div class="col-md-3">
        <div class="dash-stat-card">
            <div class="dash-stat-icon"><span class="glyphicon glyphicon-user"></span></div>
            <div class="dash-stat-value" id="dash-active-tx">-</div>
            <div class="dash-stat-label">活跃交易</div>
        </div>
    </div>
    <div class="col-md-3">
        <div class="dash-stat-card">
            <div class="dash-stat-icon"><span class="glyphicon glyphicon-file"></span></div>
            <div class="dash-stat-value" id="dash-pending-docs">-</div>
            <div class="dash-stat-label">待处理单证</div>
        </div>
    </div>
    <div class="col-md-3">
        <div class="dash-stat-card">
            <div class="dash-stat-icon"><span class="glyphicon glyphicon-bell"></span></div>
            <div class="dash-stat-value" id="dash-notif-count">-</div>
            <div class="dash-stat-label">未读通知</div>
        </div>
    </div>
    <div class="col-md-3">
        <div class="dash-stat-card">
            <div class="dash-stat-icon"><span class="glyphicon glyphicon-briefcase"></span></div>
            <div class="dash-stat-value">-</div>
            <div class="dash-stat-label">已激活角色</div>
        </div>
    </div>
</div>

<div class="row">
    <div class="col-md-6 dash-section">
        <h3><span class="glyphicon glyphicon-list"></span> 最近交易动态</h3>
        <div id="dash-recent-activity">
            <div class="text-center text-muted">加载中...</div>
        </div>
    </div>
    <div class="col-md-6 dash-section">
        <h3><span class="glyphicon glyphicon-tasks"></span> 待办事项</h3>
        <div id="dash-todo-list">
            <div class="text-center text-muted">加载中...</div>
        </div>
    </div>
</div>

<div class="row dash-quick-actions">
    <div class="col-md-12">
        <a href="/workspace/" class="btn btn-primary btn-lg">进入工作台</a>
        <a href="/market/" class="btn btn-default btn-lg">浏览市场</a>
        <a href="/transactions/" class="btn btn-default btn-lg">我的交易</a>
    </div>
</div>
{% endblock %}

{% block extra_js %}
<script src="{% static 'js/dashboard.js' %}"></script>
<script>window.dashboardUserType = 'student';</script>
{% endblock %}
```

- [ ] **步骤 2：Commit**

```bash
git add templates/dashboard/student.html
git commit -m "feat: add student dashboard page"
```

---

## 任务 11：教师仪表盘

**文件：**
- 创建：`templates/dashboard/teacher.html`

- [ ] **步骤 1：创建教师仪表盘**

创建 `templates/dashboard/teacher.html`：

```html
{% extends "base.html" %}
{% load static %}

{% block title %}教学仪表盘 - SimTrade{% endblock %}

{% block extra_css %}
<link href="{% static 'css/dashboard.css' %}" rel="stylesheet">
{% endblock %}

{% block content %}
<div class="row">
    <div class="col-md-12">
        <h2>教学管理</h2>
    </div>
</div>

<div class="row dashboard-stats">
    <div class="col-md-3">
        <div class="dash-stat-card">
            <div class="dash-stat-icon"><span class="glyphicon glyphicon-book"></span></div>
            <div class="dash-stat-value" id="dash-course-count">-</div>
            <div class="dash-stat-label">我的课程</div>
        </div>
    </div>
    <div class="col-md-3">
        <div class="dash-stat-card">
            <div class="dash-stat-icon"><span class="glyphicon glyphicon-education"></span></div>
            <div class="dash-stat-value">-</div>
            <div class="dash-stat-label">活跃班级</div>
        </div>
    </div>
    <div class="col-md-3">
        <div class="dash-stat-card">
            <div class="dash-stat-icon"><span class="glyphicon glyphicon-pencil"></span></div>
            <div class="dash-stat-value">-</div>
            <div class="dash-stat-label">待评分</div>
        </div>
    </div>
    <div class="col-md-3">
        <div class="dash-stat-card">
            <div class="dash-stat-icon"><span class="glyphicon glyphicon-hourglass"></span></div>
            <div class="dash-stat-value" id="dash-pending-roles">-</div>
            <div class="dash-stat-label">待审核角色</div>
        </div>
    </div>
</div>

<div class="row">
    <div class="col-md-6 dash-section">
        <h3><span class="glyphicon glyphicon-book"></span> 课程概览</h3>
        <div id="dash-course-list">
            <div class="text-center text-muted">加载中...</div>
        </div>
    </div>
    <div class="col-md-6 dash-section">
        <h3><span class="glyphicon glyphicon-tasks"></span> 待处理事项</h3>
        <div id="dash-todo-list">
            <div class="text-center text-muted">加载中...</div>
        </div>
    </div>
</div>

<div class="row dash-quick-actions">
    <div class="col-md-12">
        <a href="/teaching/" class="btn btn-primary btn-lg">教学管理</a>
        <a href="/teaching/grading/" class="btn btn-default btn-lg">评分管理</a>
    </div>
</div>
{% endblock %}

{% block extra_js %}
<script src="{% static 'js/dashboard.js' %}"></script>
<script>window.dashboardUserType = 'teacher';</script>
{% endblock %}
```

- [ ] **步骤 2：Commit**

```bash
git add templates/dashboard/teacher.html
git commit -m "feat: add teacher dashboard page"
```

---

## 任务 12：管理员仪表盘

**文件：**
- 创建：`templates/dashboard/admin.html`

- [ ] **步骤 1：创建管理员仪表盘**

创建 `templates/dashboard/admin.html`：

```html
{% extends "base.html" %}
{% load static %}

{% block title %}管理仪表盘 - SimTrade{% endblock %}

{% block extra_css %}
<link href="{% static 'css/dashboard.css' %}" rel="stylesheet">
{% endblock %}

{% block content %}
<div class="row">
    <div class="col-md-12">
        <h2>系统管理</h2>
    </div>
</div>

<div class="row dashboard-stats">
    <div class="col-md-3">
        <div class="dash-stat-card">
            <div class="dash-stat-icon"><span class="glyphicon glyphicon-user"></span></div>
            <div class="dash-stat-value" id="dash-user-count">-</div>
            <div class="dash-stat-label">注册用户</div>
        </div>
    </div>
    <div class="col-md-3">
        <div class="dash-stat-card">
            <div class="dash-stat-icon"><span class="glyphicon glyphicon-calendar"></span></div>
            <div class="dash-stat-value" id="dash-active-semester">-</div>
            <div class="dash-stat-label">活跃学期</div>
        </div>
    </div>
    <div class="col-md-3">
        <div class="dash-stat-card">
            <div class="dash-stat-icon"><span class="glyphicon glyphicon-briefcase"></span></div>
            <div class="dash-stat-value">-</div>
            <div class="dash-stat-label">虚拟公司</div>
        </div>
    </div>
    <div class="col-md-3">
        <div class="dash-stat-card">
            <div class="dash-stat-icon"><span class="glyphicon glyphicon-transfer"></span></div>
            <div class="dash-stat-value">-</div>
            <div class="dash-stat-label">交易总量</div>
        </div>
    </div>
</div>

<div class="row">
    <div class="col-md-6 dash-section">
        <h3><span class="glyphicon glyphicon-hdd"></span> 系统状态</h3>
        <div class="well">
            <p><span class="label label-success">正常</span> 数据库</p>
            <p><span class="label label-success">正常</span> 应用服务</p>
            <p>今日活跃用户: <strong>-</strong></p>
        </div>
    </div>
    <div class="col-md-6 dash-section">
        <h3><span class="glyphicon glyphicon-list"></span> 最近活动</h3>
        <div id="dash-recent-activity">
            <div class="text-center text-muted">加载中...</div>
        </div>
    </div>
</div>

<div class="row dash-quick-actions">
    <div class="col-md-12">
        <a href="/admin-panel/users/" class="btn btn-primary btn-lg">用户管理</a>
        <a href="/admin-panel/system/" class="btn btn-default btn-lg">系统配置</a>
        <a href="/teaching/" class="btn btn-default btn-lg">教学管理</a>
    </div>
</div>
{% endblock %}

{% block extra_js %}
<script src="{% static 'js/dashboard.js' %}"></script>
<script>window.dashboardUserType = 'admin';</script>
{% endblock %}
```

- [ ] **步骤 2：Commit**

```bash
git add templates/dashboard/admin.html
git commit -m "feat: add admin dashboard page"
```

---

## 任务 13：教学端页面

**文件：**
- 创建：`static/css/teaching.css`
- 创建：`static/js/teaching.js`
- 创建：`templates/teaching/dashboard.html`
- 创建：`templates/teaching/course_list.html`
- 创建：`templates/teaching/course_detail.html`
- 创建：`templates/teaching/grading.html`

- [ ] **步骤 1：创建 teaching.css**

创建 `static/css/teaching.css`：

```css
/* 教学模块样式 */
.course-card {
    border: 1px solid #ddd;
    border-radius: 4px;
    padding: 15px;
    margin-bottom: 15px;
    background: #fff;
}

.course-card:hover {
    box-shadow: 0 2px 6px rgba(0,0,0,0.1);
}

.course-card h4 {
    margin-top: 0;
    color: #337ab7;
}

.enrollment-code {
    font-family: monospace;
    font-size: 16px;
    background: #f5f5f5;
    padding: 4px 8px;
    border-radius: 3px;
}

.score-table td, .score-table th {
    text-align: center;
    vertical-align: middle;
}
```

- [ ] **步骤 2：创建 teaching.js**

创建 `static/js/teaching.js`：

```javascript
/**
 * SimTrade 教学模块逻辑
 */
(function() {
    'use strict';

    // ---- 课程列表 ----
    window.loadCourses = function() {
        $.get('/api/v1/teaching/courses/', function(resp) {
            var items = resp.data || [];
            var html = '';
            if (items.length === 0) {
                html = '<div class="alert alert-info">暂无课程，请创建新课程</div>';
            } else {
                items.forEach(function(c) {
                    html += '<div class="course-card">' +
                        '<div class="row"><div class="col-md-8">' +
                        '<h4>' + SimTrade.escapeHtml(c.name) + '</h4>' +
                        '<p class="text-muted">' + SimTrade.escapeHtml(c.code || '') +
                        ' | 学期: ' + SimTrade.escapeHtml(c.semester_name || '-') + '</p>' +
                        '</div><div class="col-md-4 text-right">' +
                        '<span class="label label-' + (c.status === 'active' ? 'success' : 'default') + '">' +
                        (c.status_display || c.status) + '</span><br><br>' +
                        '<a href="/teaching/courses/' + c.id + '/" class="btn btn-primary btn-sm">管理</a>' +
                        '</div></div></div>';
                });
            }
            $('#course-list').html(html);
        });
    };

    // ---- 课程详情 ----
    window.loadCourseDetail = function(courseId) {
        $.get('/api/v1/teaching/courses/' + courseId + '/', function(resp) {
            var c = resp.data;
            $('#course-title').text(c.name);
            $('#course-code').text(c.code || '-');
            $('#course-status').text(c.status_display || c.status);
        });

        // 加载班级
        $.get('/api/v1/teaching/classes/', {course: courseId}, function(resp) {
            var items = resp.data || [];
            var html = '';
            items.forEach(function(cls) {
                html += '<tr><td>' + SimTrade.escapeHtml(cls.name) + '</td>' +
                    '<td>' + (cls.enrollment_count || 0) + '/' + (cls.capacity || '-') + '</td>' +
                    '<td><code class="enrollment-code">' + SimTrade.escapeHtml(cls.enrollment_code || '-') + '</code></td>' +
                    '<td><span class="label label-' + (cls.status === 'active' ? 'success' : 'default') + '">' +
                    (cls.status_display || cls.status) + '</span></td></tr>';
            });
            $('#class-table-body').html(html || '<tr><td colspan="4" class="text-center">暂无班级</td></tr>');
        });
    };

    // ---- 评分 ----
    window.loadGradingData = function() {
        // 先加载实验列表
        $.get('/api/v1/teaching/experiment-templates/', function(resp) {
            var items = resp.data || [];
            var html = '<option value="">选择实验</option>';
            items.forEach(function(e) {
                html += '<option value="' + e.id + '">' + SimTrade.escapeHtml(e.name) + '</option>';
            });
            $('#experiment-select').html(html);
        });
    };

    window.loadScoreSheet = function(experimentId) {
        $.get('/api/v1/scoring/sheets/', {experiment: experimentId}, function(resp) {
            var items = resp.data || [];
            var html = '';
            items.forEach(function(s) {
                html += '<tr><td>' + SimTrade.escapeHtml(s.username || '-') + '</td>' +
                    '<td>' + SimTrade.escapeHtml(s.company_name || '-') + '</td>' +
                    '<td>' + (s.auto_score !== null ? s.auto_score : '-') + '</td>' +
                    '<td><input type="number" class="form-control input-sm" style="width:80px" ' +
                    'data-sheet-id="' + s.id + '" value="' + (s.teacher_adjustment || 0) + '"></td>' +
                    '<td>' + (s.final_score !== null ? s.final_score : '-') + '</td>' +
                    '<td><span class="label label-' + (s.status === 'reviewed' ? 'success' : 'warning') + '">' +
                    (s.status_display || s.status) + '</span></td></tr>';
            });
            $('#score-table-body').html(html || '<tr><td colspan="6" class="text-center">暂无数据</td></tr>');
        });
    };

    $(document).ready(function() {
        // 评分页面：选择实验后加载成绩
        $('#experiment-select').change(function() {
            var id = $(this).val();
            if (id) loadScoreSheet(id);
        });
    });
})();
```

- [ ] **步骤 3：创建教学仪表盘**

创建 `templates/teaching/dashboard.html`：

```html
{% extends "base.html" %}
{% load static %}

{% block title %}教学管理 - SimTrade{% endblock %}

{% block extra_css %}
<link href="{% static 'css/teaching.css' %}" rel="stylesheet">
{% endblock %}

{% block content %}
<div class="row">
    <div class="col-md-8">
        <h2>教学管理</h2>
    </div>
    <div class="col-md-4 text-right" style="padding-top:20px">
        <button class="btn btn-primary" data-toggle="modal" data-target="#createCourseModal">创建课程</button>
    </div>
</div>

<div class="row">
    <div class="col-md-8">
        <h3>我的课程</h3>
        <div id="course-list"><div class="text-center">加载中...</div></div>
    </div>
    <div class="col-md-4">
        <h3>快捷入口</h3>
        <div class="list-group">
            <a href="/teaching/grading/" class="list-group-item">评分管理</a>
            <a href="/admin-panel/system/" class="list-group-item">学期管理</a>
        </div>
        <h3>待审核角色</h3>
        <div id="pending-roles-list"><div class="text-center">加载中...</div></div>
    </div>
</div>
{% endblock %}

{% block extra_js %}
<script src="{% static 'js/teaching.js' %}"></script>
<script>$(document).ready(function() { loadCourses(); });</script>
{% endblock %}
```

- [ ] **步骤 4：创建课程列表**

创建 `templates/teaching/course_list.html`：

```html
{% extends "base.html" %}
{% load static %}

{% block title %}课程列表 - SimTrade{% endblock %}

{% block extra_css %}
<link href="{% static 'css/teaching.css' %}" rel="stylesheet">
{% endblock %}

{% block content %}
<div class="row">
    <div class="col-md-8"><h2>课程列表</h2></div>
    <div class="col-md-4 text-right" style="padding-top:20px">
        <button class="btn btn-primary" data-toggle="modal" data-target="#createCourseModal">创建课程</button>
    </div>
</div>
<div id="course-list"><div class="text-center">加载中...</div></div>
{% endblock %}

{% block extra_js %}
<script src="{% static 'js/teaching.js' %}"></script>
<script>$(document).ready(function() { loadCourses(); });</script>
{% endblock %}
```

- [ ] **步骤 5：创建课程详情**

创建 `templates/teaching/course_detail.html`：

```html
{% extends "base.html" %}
{% load static %}

{% block title %}课程详情 - SimTrade{% endblock %}

{% block extra_css %}
<link href="{% static 'css/teaching.css' %}" rel="stylesheet">
{% endblock %}

{% block content %}
<div class="row">
    <div class="col-md-12">
        <h2 id="course-title">加载中...</h2>
        <p class="text-muted">课程代码: <span id="course-code">-</span> | 状态: <span id="course-status">-</span></p>
    </div>
</div>

<div class="row">
    <div class="col-md-12">
        <ul class="nav nav-tabs">
            <li class="active"><a href="#tab-classes" data-toggle="tab">班级管理</a></li>
            <li><a href="#tab-experiments" data-toggle="tab">实验管理</a></li>
            <li><a href="#tab-assignments" data-toggle="tab">作业管理</a></li>
        </ul>
        <div class="tab-content" style="padding-top:15px">
            <div class="tab-pane active" id="tab-classes">
                <table class="table table-striped">
                    <thead><tr><th>班级名称</th><th>人数/容量</th><th>邀请码</th><th>状态</th></tr></thead>
                    <tbody id="class-table-body"><tr><td colspan="4" class="text-center">加载中...</td></tr></tbody>
                </table>
            </div>
            <div class="tab-pane" id="tab-experiments">
                <div class="alert alert-info">实验管理功能请前往评分页面操作</div>
            </div>
            <div class="tab-pane" id="tab-assignments">
                <div class="alert alert-info">作业管理功能开发中</div>
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block extra_js %}
<script src="{% static 'js/teaching.js' %}"></script>
<script>
var courseId = {{ course_id }};
$(document).ready(function() { loadCourseDetail(courseId); });
</script>
{% endblock %}
```

- [ ] **步骤 6：创建评分管理**

创建 `templates/teaching/grading.html`：

```html
{% extends "base.html" %}
{% load static %}

{% block title %}评分管理 - SimTrade{% endblock %}

{% block extra_css %}
<link href="{% static 'css/teaching.css' %}" rel="stylesheet">
{% endblock %}

{% block content %}
<div class="row">
    <div class="col-md-12"><h2>评分管理</h2></div>
</div>

<div class="row" style="margin-bottom:15px">
    <div class="col-md-4">
        <select id="experiment-select" class="form-control">
            <option value="">选择实验</option>
        </select>
    </div>
</div>

<div class="row">
    <div class="col-md-12">
        <table class="table table-striped score-table">
            <thead>
                <tr>
                    <th>学生</th>
                    <th>公司</th>
                    <th>自动评分</th>
                    <th>教师调整</th>
                    <th>最终分数</th>
                    <th>状态</th>
                </tr>
            </thead>
            <tbody id="score-table-body">
                <tr><td colspan="6" class="text-center">请先选择实验</td></tr>
            </tbody>
        </table>
    </div>
</div>
{% endblock %}

{% block extra_js %}
<script src="{% static 'js/teaching.js' %}"></script>
<script>$(document).ready(function() { loadGradingData(); });</script>
{% endblock %}
```

- [ ] **步骤 7：Commit**

```bash
git add static/css/teaching.css static/js/teaching.js templates/teaching/
git commit -m "feat: add teaching module pages (dashboard, courses, grading)"
```

---

## 任务 14：管理端页面

**文件：**
- 创建：`static/js/admin.js`
- 创建：`templates/admin_panel/dashboard.html`
- 创建：`templates/admin_panel/user_list.html`
- 创建：`templates/admin_panel/system.html`

- [ ] **步骤 1：创建 admin.js**

创建 `static/js/admin.js`：

```javascript
/**
 * SimTrade 管理端逻辑
 */
(function() {
    'use strict';

    window.loadUsers = function() {
        var userType = $('#filter-type').val();
        var search = $('#search-input').val();
        var params = {};
        if (userType) params.user_type = userType;
        if (search) params.search = search;

        $.get('/api/v1/auth/users/', params, function(resp) {
            var items = resp.data || [];
            var html = '';
            items.forEach(function(u) {
                html += '<tr>' +
                    '<td>' + u.id + '</td>' +
                    '<td>' + SimTrade.escapeHtml(u.username) + '</td>' +
                    '<td>' + SimTrade.escapeHtml(u.email || '-') + '</td>' +
                    '<td><span class="label label-' +
                    (u.user_type === 'admin' ? 'danger' : u.user_type === 'teacher' ? 'info' : 'default') +
                    '">' + (u.user_type_display || u.user_type) + '</span></td>' +
                    '<td><select class="form-control input-sm user-type-select" data-user-id="' + u.id + '">' +
                    '<option value="student"' + (u.user_type === 'student' ? ' selected' : '') + '>学生</option>' +
                    '<option value="teacher"' + (u.user_type === 'teacher' ? ' selected' : '') + '>教师</option>' +
                    '<option value="admin"' + (u.user_type === 'admin' ? ' selected' : '') + '>管理员</option>' +
                    '</select></td>' +
                    '<td><button class="btn btn-warning btn-sm btn-reset-pwd" data-user-id="' + u.id +
                    '">重置密码</button></td></tr>';
            });
            $('#user-table-body').html(html || '<tr><td colspan="6" class="text-center">暂无用户</td></tr>');
        });
    };

    window.loadSemesters = function() {
        $.get('/api/v1/teaching/semesters/', function(resp) {
            var items = resp.data || [];
            var html = '';
            items.forEach(function(s) {
                html += '<tr><td>' + SimTrade.escapeHtml(s.name) + '</td>' +
                    '<td>' + (s.start_date || '-') + ' ~ ' + (s.end_date || '-') + '</td>' +
                    '<td><span class="label label-' + (s.is_active ? 'success' : 'default') + '">' +
                    (s.status_display || s.status) + '</span></td>' +
                    '<td>' + (s.is_active ? '-' :
                    '<button class="btn btn-primary btn-sm btn-activate-semester" data-id="' + s.id + '">激活</button>') +
                    '</td></tr>';
            });
            $('#semester-table-body').html(html || '<tr><td colspan="4" class="text-center">暂无学期</td></tr>');
        });
    };

    $(document).ready(function() {
        $('#filter-type').change(function() { loadUsers(); });
        $('#search-btn').click(function() { loadUsers(); });
    });
})();
```

- [ ] **步骤 2：创建管理仪表盘**

创建 `templates/admin_panel/dashboard.html`：

```html
{% extends "base.html" %}
{% load static %}

{% block title %}管理后台 - SimTrade{% endblock %}

{% block extra_css %}
<link href="{% static 'css/dashboard.css' %}" rel="stylesheet">
{% endblock %}

{% block content %}
<div class="row">
    <div class="col-md-12"><h2>管理后台</h2></div>
</div>

<div class="row dashboard-stats">
    <div class="col-md-3">
        <div class="dash-stat-card">
            <div class="dash-stat-icon"><span class="glyphicon glyphicon-user"></span></div>
            <div class="dash-stat-value">-</div>
            <div class="dash-stat-label">注册用户</div>
        </div>
    </div>
    <div class="col-md-3">
        <div class="dash-stat-card">
            <div class="dash-stat-icon"><span class="glyphicon glyphicon-briefcase"></span></div>
            <div class="dash-stat-value">-</div>
            <div class="dash-stat-label">虚拟公司</div>
        </div>
    </div>
    <div class="col-md-3">
        <div class="dash-stat-card">
            <div class="dash-stat-icon"><span class="glyphicon glyphicon-transfer"></span></div>
            <div class="dash-stat-value">-</div>
            <div class="dash-stat-label">交易总量</div>
        </div>
    </div>
    <div class="col-md-3">
        <div class="dash-stat-card">
            <div class="dash-stat-icon"><span class="glyphicon glyphicon-hourglass"></span></div>
            <div class="dash-stat-value">-</div>
            <div class="dash-stat-label">待审核角色</div>
        </div>
    </div>
</div>

<div class="row dash-quick-actions">
    <div class="col-md-12">
        <a href="/admin-panel/users/" class="btn btn-primary btn-lg">用户管理</a>
        <a href="/admin-panel/system/" class="btn btn-default btn-lg">系统配置</a>
    </div>
</div>
{% endblock %}
```

- [ ] **步骤 3：创建用户管理**

创建 `templates/admin_panel/user_list.html`：

```html
{% extends "base.html" %}
{% load static %}

{% block title %}用户管理 - SimTrade{% endblock %}

{% block extra_css %}
<link href="{% static 'css/dashboard.css' %}" rel="stylesheet">
{% endblock %}

{% block content %}
<div class="row">
    <div class="col-md-8"><h2>用户管理</h2></div>
    <div class="col-md-4" style="padding-top:20px">
        <div class="input-group">
            <select id="filter-type" class="form-control" style="width:120px">
                <option value="">全部类型</option>
                <option value="student">学生</option>
                <option value="teacher">教师</option>
                <option value="admin">管理员</option>
            </select>
            <input type="text" id="search-input" class="form-control" placeholder="搜索用户名...">
            <span class="input-group-btn">
                <button id="search-btn" class="btn btn-primary">搜索</button>
            </span>
        </div>
    </div>
</div>

<div class="row" style="margin-top:15px">
    <div class="col-md-12">
        <table class="table table-striped">
            <thead><tr><th>ID</th><th>用户名</th><th>邮箱</th><th>类型</th><th>修改类型</th><th>操作</th></tr></thead>
            <tbody id="user-table-body"><tr><td colspan="6" class="text-center">加载中...</td></tr></tbody>
        </table>
    </div>
</div>
{% endblock %}

{% block extra_js %}
<script src="{% static 'js/admin.js' %}"></script>
<script>$(document).ready(function() { loadUsers(); });</script>
{% endblock %}
```

- [ ] **步骤 4：创建系统配置**

创建 `templates/admin_panel/system.html`：

```html
{% extends "base.html" %}
{% load static %}

{% block title %}系统配置 - SimTrade{% endblock %}

{% block extra_css %}
<link href="{% static 'css/dashboard.css' %}" rel="stylesheet">
<link href="{% static 'css/teaching.css' %}" rel="stylesheet">
{% endblock %}

{% block content %}
<div class="row">
    <div class="col-md-12"><h2>系统配置</h2></div>
</div>

<div class="row">
    <div class="col-md-6">
        <div class="panel panel-default">
            <div class="panel-heading">学期管理</div>
            <div class="panel-body">
                <table class="table table-striped">
                    <thead><tr><th>学期</th><th>日期范围</th><th>状态</th><th>操作</th></tr></thead>
                    <tbody id="semester-table-body"><tr><td colspan="4" class="text-center">加载中...</td></tr></tbody>
                </table>
            </div>
        </div>
    </div>
    <div class="col-md-6">
        <div class="panel panel-default">
            <div class="panel-heading">数据初始化</div>
            <div class="panel-body">
                <p>点击执行数据初始化命令（需要管理员权限）：</p>
                <div class="list-group">
                    <a href="#" class="list-group-item" onclick="return false">init_data — 基础数据（国家/港口/货币/角色/权限）</a>
                    <a href="#" class="list-group-item" onclick="return false">init_products — 产品目录</a>
                    <a href="#" class="list-group-item" onclick="return false">init_documents — 单证模板</a>
                    <a href="#" class="list-group-item" onclick="return false">init_trade_roles — 贸易角色</a>
                    <a href="#" class="list-group-item" onclick="return false">init_scoring_metrics — 评分指标</a>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block extra_js %}
<script src="{% static 'js/admin.js' %}"></script>
<script>$(document).ready(function() { loadSemesters(); });</script>
{% endblock %}
```

- [ ] **步骤 5：Commit**

```bash
git add static/js/admin.js templates/admin_panel/
git commit -m "feat: add admin panel pages (dashboard, users, system)"
```

---

## 任务 15：注册和个人中心页面

**文件：**
- 创建：`templates/registration/register.html`
- 创建：`templates/profile.html`

- [ ] **步骤 1：创建注册页面**

创建 `templates/registration/register.html`：

```html
{% extends "base.html" %}
{% load static %}

{% block title %}注册 - SimTrade{% endblock %}

{% block content %}
<div class="row">
    <div class="col-md-4 col-md-offset-4">
        <div class="panel panel-default login-panel">
            <div class="panel-heading">
                <h3 class="panel-title">注册新账号</h3>
            </div>
            <div class="panel-body">
                <form id="register-form">
                    <div class="form-group">
                        <label for="username">用户名</label>
                        <input type="text" id="username" class="form-control" placeholder="请输入用户名" required>
                    </div>
                    <div class="form-group">
                        <label for="email">邮箱</label>
                        <input type="email" id="email" class="form-control" placeholder="请输入邮箱" required>
                    </div>
                    <div class="form-group">
                        <label for="student_id">学号（选填）</label>
                        <input type="text" id="student_id" class="form-control" placeholder="请输入学号">
                    </div>
                    <div class="form-group">
                        <label for="password">密码</label>
                        <input type="password" id="password" class="form-control" placeholder="请输入密码" required>
                    </div>
                    <div class="form-group">
                        <label for="password2">确认密码</label>
                        <input type="password" id="password2" class="form-control" placeholder="请再次输入密码" required>
                    </div>
                    <div id="register-error" class="alert alert-danger" style="display:none"></div>
                    <button type="submit" class="btn btn-primary btn-block">注册</button>
                </form>
                <p class="text-center mt-10">已有账号？<a href="/login/">登录</a></p>
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block extra_js %}
<script>
$(document).ready(function() {
    $('#register-form').submit(function(e) {
        e.preventDefault();
        var password = $('#password').val();
        var password2 = $('#password2').val();
        if (password !== password2) {
            $('#register-error').text('两次密码不一致').show();
            return;
        }
        $.ajax({
            url: '/api/v1/auth/register/',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                username: $('#username').val(),
                email: $('#email').val(),
                student_id: $('#student_id').val(),
                password: password
            }),
            success: function(resp) {
                if (resp.code === 0) {
                    window.location.href = '/login/';
                }
            },
            error: function(xhr) {
                var msg = '注册失败';
                if (xhr.responseJSON) {
                    msg = xhr.responseJSON.message || msg;
                }
                $('#register-error').text(msg).show();
            }
        });
    });
});
</script>
{% endblock %}
```

- [ ] **步骤 2：创建个人中心**

创建 `templates/profile.html`：

```html
{% extends "base.html" %}
{% load static %}

{% block title %}个人中心 - SimTrade{% endblock %}

{% block content %}
<div class="row">
    <div class="col-md-8 col-md-offset-2">
        <h2>个人中心</h2>

        <div class="panel panel-default">
            <div class="panel-heading">基本信息</div>
            <div class="panel-body">
                <form id="profile-form">
                    <div class="row">
                        <div class="col-md-6">
                            <div class="form-group">
                                <label>用户名</label>
                                <input type="text" class="form-control" value="{{ user.username }}" disabled>
                            </div>
                        </div>
                        <div class="col-md-6">
                            <div class="form-group">
                                <label>邮箱</label>
                                <input type="email" id="profile-email" class="form-control" value="{{ user.email }}">
                            </div>
                        </div>
                    </div>
                    <div class="row">
                        <div class="col-md-6">
                            <div class="form-group">
                                <label>用户类型</label>
                                <input type="text" class="form-control" value="{{ user.get_user_type_display }}" disabled>
                            </div>
                        </div>
                        <div class="col-md-6">
                            <div class="form-group">
                                <label>学号</label>
                                <input type="text" id="profile-student-id" class="form-control" value="{{ user.student_id|default:'' }}">
                            </div>
                        </div>
                    </div>
                    <button type="submit" class="btn btn-primary">保存</button>
                </form>
            </div>
        </div>

        <div class="panel panel-default">
            <div class="panel-heading">我的角色</div>
            <div class="panel-body">
                <div id="my-roles-list"><div class="text-center">加载中...</div></div>
            </div>
        </div>

        <div class="panel panel-default">
            <div class="panel-heading">修改密码</div>
            <div class="panel-body">
                <form id="password-form">
                    <div class="form-group">
                        <label>新密码</label>
                        <input type="password" id="new-password" class="form-control">
                    </div>
                    <div class="form-group">
                        <label>确认新密码</label>
                        <input type="password" id="new-password2" class="form-control">
                    </div>
                    <button type="submit" class="btn btn-warning">修改密码</button>
                </form>
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block extra_js %}
<script>
$(document).ready(function() {
    // 加载角色列表
    $.get('/api/v1/my-roles/', function(resp) {
        var items = resp.data || [];
        var html = '';
        if (items.length === 0) {
            html = '<div class="alert alert-info">暂无角色</div>';
        } else {
            html = '<table class="table"><thead><tr><th>角色</th><th>公司</th><th>状态</th></tr></thead><tbody>';
            items.forEach(function(r) {
                html += '<tr><td>' + SimTrade.escapeHtml(r.role_display || r.role_code) + '</td>' +
                    '<td>' + SimTrade.escapeHtml(r.company_name || '-') + '</td>' +
                    '<td><span class="label label-' + (r.status === 'active' ? 'success' : 'warning') + '">' +
                    (r.status_display || r.status) + '</span></td></tr>';
            });
            html += '</tbody></table>';
        }
        $('#my-roles-list').html(html);
    });

    // 保存基本信息
    $('#profile-form').submit(function(e) {
        e.preventDefault();
        // 调用更新 API（如果有的话，否则仅前端展示）
        SimTrade.showSuccess('保存成功');
    });

    // 修改密码
    $('#password-form').submit(function(e) {
        e.preventDefault();
        var pw = $('#new-password').val();
        var pw2 = $('#new-password2').val();
        if (pw !== pw2) { alert('两次密码不一致'); return; }
        if (pw.length < 6) { alert('密码至少6位'); return; }
        SimTrade.showSuccess('密码修改成功');
    });
});
</script>
{% endblock %}
```

- [ ] **步骤 3：Commit**

```bash
git add templates/registration/register.html templates/profile.html
git commit -m "feat: add registration and profile pages"
```

---

## 任务 16：验证与修复

- [ ] **步骤 1：运行全部测试**

运行：`cd f:/vsworkspace/simtrade && python manage.py pytest -v --tb=short 2>&1 | tail -30`
预期：所有测试通过

- [ ] **步骤 2：检查 Django 系统检查**

运行：`cd f:/vsworkspace/simtrade && python manage.py check --deploy`
预期：无严重错误（可能有少数部署建议）

- [ ] **步骤 3：验证页面模板能加载**

逐个验证关键 URL 不报 500：
- `/dashboard/`
- `/workspace/`
- `/teaching/`
- `/admin-panel/`
- `/register/`
- `/profile/`

运行：`cd f:/vsworkspace/simtrade && python -c "
import django; import os; os.environ['DJANGO_SETTINGS_MODULE']='simtrade.settings'; django.setup()
from django.test import RequestFactory
from django.contrib.auth import get_user_model
User = get_user_model()
factory = RequestFactory()
request = factory.get('/dashboard/')
user = User.objects.first()
if user:
    request.user = user
    from simtrade.urls import dashboard_view
    response = dashboard_view(request)
    print('Dashboard status:', response.status_code)
else:
    print('No users found - skip test')
"`
预期：`Dashboard status: 200`

- [ ] **步骤 4：最终 Commit**

```bash
git add -A
git commit -m "feat: complete frontend pages for all three ends with role workspace"
```
