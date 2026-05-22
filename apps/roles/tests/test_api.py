"""
Tests for Role API endpoints.
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from apps.roles.models import Company, TradeRole, UserCompanyRole
from apps.users.models import Role

User = get_user_model()


class TestTradeRoleAPI:
    """Test cases for TradeRole API (Read-only)."""

    @pytest.fixture(autouse=True)
    def setup(self, db):
        """Set up test fixtures."""
        self.client = APIClient()

        # Create test users
        self.student = User.objects.create_user(
            username='student',
            email='student@example.com',
            password='testpass123',
            user_type='student'
        )

        self.teacher = User.objects.create_user(
            username='teacher',
            email='teacher@example.com',
            password='teacherpass123',
            user_type='teacher',
            is_staff=True
        )

        # Create trade roles
        self.exporter_role = TradeRole.objects.create(
            code='exporter',
            name='出口商',
            description='负责出口贸易业务',
            is_enabled=True
        )
        self.importer_role = TradeRole.objects.create(
            code='importer',
            name='进口商',
            description='负责进口贸易业务',
            is_enabled=True
        )
        self.disabled_role = TradeRole.objects.create(
            code='factory',
            name='工厂',
            description='生产制造企业',
            is_enabled=False
        )

    def test_list_trade_roles_success(self, db):
        """Test listing enabled trade roles."""
        self.client.force_authenticate(user=self.student)
        response = self.client.get('/api/v1/roles/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['code'] == 0
        assert response.data['message'] == 'success'
        assert 'data' in response.data
        # Should return all roles (including disabled)
        assert len(response.data['data']) == 3

    def test_list_trade_roles_unauthenticated(self, db):
        """Test listing roles without authentication."""
        self.client.force_authenticate(user=None)
        response = self.client.get('/api/v1/roles/')

        # Unauthenticated users should be able to view available roles
        assert response.status_code == status.HTTP_200_OK
        assert response.data['code'] == 0
        assert 'data' in response.data


class TestUserCompanyRoleAPI:
    """Test cases for UserCompanyRole API."""

    @pytest.fixture(autouse=True)
    def setup(self, db):
        """Set up test fixtures."""
        self.client = APIClient()

        # Create test users
        self.student = User.objects.create_user(
            username='student',
            email='student@example.com',
            password='testpass123',
            user_type='student'
        )

        self.student2 = User.objects.create_user(
            username='student2',
            email='student2@example.com',
            password='testpass123',
            user_type='student'
        )

        self.teacher = User.objects.create_user(
            username='teacher',
            email='teacher@example.com',
            password='teacherpass123',
            user_type='teacher',
            is_staff=True
        )

        # Create company
        self.company = Company.objects.create(
            name='测试贸易公司',
            code='COMP_000001',
            type='进出口贸易'
        )

        # Create trade roles
        self.exporter_role = TradeRole.objects.create(
            code='exporter',
            name='出口商',
            description='负责出口贸易业务'
        )
        self.importer_role = TradeRole.objects.create(
            code='importer',
            name='进口商',
            description='负责进口贸易业务'
        )

    def test_list_my_roles_empty(self, db):
        """Test listing my roles when user has no roles."""
        self.client.force_authenticate(user=self.student)
        response = self.client.get('/api/v1/my-roles/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['code'] == 0
        assert response.data['message'] == 'success'
        assert 'data' in response.data
        assert len(response.data['data']) == 0

    def test_list_my_roles_with_data(self, db):
        """Test listing my roles when user has roles."""
        # Create a role assignment
        UserCompanyRole.objects.create(
            user=self.student,
            company=self.company,
            role=self.exporter_role,
            status=UserCompanyRole.Status.ACTIVE,
            is_active=True
        )

        self.client.force_authenticate(user=self.student)
        response = self.client.get('/api/v1/my-roles/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['code'] == 0
        assert len(response.data['data']) == 1
        assert response.data['data'][0]['username'] == 'student'
        assert response.data['data'][0]['company_name'] == '测试贸易公司'
        assert response.data['data'][0]['role_name'] == '出口商'
        assert response.data['data'][0]['status'] == 'active'

    def test_request_role_success(self, db):
        """Test requesting a role successfully."""
        self.client.force_authenticate(user=self.student)
        response = self.client.post('/api/v1/my-roles/request/', {
            'company_id': self.company.id,
            'role_code': 'importer',
            'notes': '希望申请进口商角色'
        })

        assert response.status_code == status.HTTP_200_OK
        assert response.data['code'] == 0
        assert response.data['message'] == '申请已提交，等待审核'
        assert 'data' in response.data

        # Verify the role was created
        assignment = UserCompanyRole.objects.get(
            user=self.student,
            company=self.company,
            role__code='importer'
        )
        assert assignment.status == UserCompanyRole.Status.PENDING
        assert assignment.notes == '希望申请进口商角色'

    def test_request_role_duplicate(self, db):
        """Test requesting a role that already exists."""
        # Create existing assignment
        UserCompanyRole.objects.create(
            user=self.student,
            company=self.company,
            role=self.exporter_role,
            status=UserCompanyRole.Status.PENDING
        )

        self.client.force_authenticate(user=self.student)
        response = self.client.post('/api/v1/my-roles/request/', {
            'company_id': self.company.id,
            'role_code': 'exporter'
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['code'] == 5005  # Business logic error

    def test_request_role_company_not_found(self, db):
        """Test requesting a role with non-existent company."""
        self.client.force_authenticate(user=self.student)
        response = self.client.post('/api/v1/my-roles/request/', {
            'company_id': 99999,
            'role_code': 'exporter'
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['code'] == 4001  # Company not found

    def test_request_role_invalid_parameters(self, db):
        """Test requesting a role with invalid parameters."""
        self.client.force_authenticate(user=self.student)
        response = self.client.post('/api/v1/my-roles/request/', {
            'company_id': 'invalid',
            'role_code': ''
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['code'] == 3002  # Parameter error

    def test_approve_role_as_teacher(self, db):
        """Test approving a role request as teacher."""
        # Create pending assignment
        assignment = UserCompanyRole.objects.create(
            user=self.student,
            company=self.company,
            role=self.exporter_role,
            status=UserCompanyRole.Status.PENDING,
            notes='申请理由'
        )

        self.client.force_authenticate(user=self.teacher)
        response = self.client.post('/api/v1/my-roles/approve/', {
            'assignment_id': assignment.id,
            'notes': '批准申请'
        })

        assert response.status_code == status.HTTP_200_OK
        assert response.data['code'] == 0
        assert response.data['message'] == '角色已批准并激活'

        # Verify the role was approved
        assignment.refresh_from_db()
        assert assignment.status == UserCompanyRole.Status.ACTIVE
        assert assignment.is_active is True
        assert assignment.approved_by == self.teacher

    def test_approve_role_as_student_forbidden(self, db):
        """Test that students cannot approve roles."""
        assignment = UserCompanyRole.objects.create(
            user=self.student,
            company=self.company,
            role=self.exporter_role,
            status=UserCompanyRole.Status.PENDING
        )

        self.client.force_authenticate(user=self.student2)
        response = self.client.post('/api/v1/my-roles/approve/', {
            'assignment_id': assignment.id
        })

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data['code'] == 2001  # Permission denied

    def test_approve_non_pending_role(self, db):
        """Test approving a role that is not pending."""
        assignment = UserCompanyRole.objects.create(
            user=self.student,
            company=self.company,
            role=self.exporter_role,
            status=UserCompanyRole.Status.ACTIVE
        )

        self.client.force_authenticate(user=self.teacher)
        response = self.client.post('/api/v1/my-roles/approve/', {
            'assignment_id': assignment.id
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['code'] == 5005  # Business logic error

    def test_reject_role_as_teacher(self, db):
        """Test rejecting a role request as teacher."""
        assignment = UserCompanyRole.objects.create(
            user=self.student,
            company=self.company,
            role=self.exporter_role,
            status=UserCompanyRole.Status.PENDING
        )

        self.client.force_authenticate(user=self.teacher)
        response = self.client.post('/api/v1/my-roles/reject/', {
            'assignment_id': assignment.id,
            'reason': '暂不批准'
        })

        assert response.status_code == status.HTTP_200_OK
        assert response.data['code'] == 0
        assert response.data['message'] == '角色申请已拒绝'

        # Verify the role was rejected
        assignment.refresh_from_db()
        assert assignment.status == UserCompanyRole.Status.REJECTED

    def test_reject_role_as_student_forbidden(self, db):
        """Test that students cannot reject roles."""
        assignment = UserCompanyRole.objects.create(
            user=self.student,
            company=self.company,
            role=self.exporter_role,
            status=UserCompanyRole.Status.PENDING
        )

        self.client.force_authenticate(user=self.student2)
        response = self.client.post('/api/v1/my-roles/reject/', {
            'assignment_id': assignment.id,
            'reason': '拒绝'
        })

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data['code'] == 2001  # Permission denied

    def test_pending_requests_as_teacher(self, db):
        """Test getting pending requests as teacher."""
        # Create pending assignments
        UserCompanyRole.objects.create(
            user=self.student,
            company=self.company,
            role=self.exporter_role,
            status=UserCompanyRole.Status.PENDING
        )
        UserCompanyRole.objects.create(
            user=self.student2,
            company=self.company,
            role=self.importer_role,
            status=UserCompanyRole.Status.PENDING
        )
        # Create an active assignment (should not appear)
        UserCompanyRole.objects.create(
            user=self.student,
            company=self.company,
            role=self.importer_role,
            status=UserCompanyRole.Status.ACTIVE
        )

        self.client.force_authenticate(user=self.teacher)
        response = self.client.get('/api/v1/my-roles/pending/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['code'] == 0
        assert len(response.data['data']) == 2

    def test_pending_requests_as_student_forbidden(self, db):
        """Test that students cannot view pending requests."""
        self.client.force_authenticate(user=self.student)
        response = self.client.get('/api/v1/my-roles/pending/')

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data['code'] == 2001  # Permission denied


class TestCompanyAPI:
    """Test cases for Company API."""

    @pytest.fixture(autouse=True)
    def setup(self, db):
        """Set up test fixtures."""
        self.client = APIClient()

        # Create test users
        self.student = User.objects.create_user(
            username='student',
            email='student@example.com',
            password='testpass123',
            user_type='student'
        )

        self.student2 = User.objects.create_user(
            username='student2',
            email='student2@example.com',
            password='testpass123',
            user_type='student'
        )

        self.teacher = User.objects.create_user(
            username='teacher',
            email='teacher@example.com',
            password='teacherpass123',
            user_type='teacher',
            is_staff=True
        )

        # Create trade role
        self.exporter_role = TradeRole.objects.create(
            code='exporter',
            name='出口商',
            description='负责出口贸易业务'
        )

    def test_create_company_success(self, db):
        """Test creating a company successfully."""
        self.client.force_authenticate(user=self.student)
        response = self.client.post('/api/v1/companies/', {
            'name': '新贸易公司',
            'name_en': 'New Trading Co.',
            'type': '进出口贸易',
            'address': '测试地址',
            'phone': '123456789',
            'email': 'test@company.com'
        })

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['code'] == 0
        assert response.data['message'] == '公司创建成功'
        assert 'data' in response.data
        assert response.data['data']['name'] == '新贸易公司'

        # Verify company was created
        company = Company.objects.get(name='新贸易公司')
        assert company.created_by == self.student

        # Verify user was added as member
        assignment = UserCompanyRole.objects.get(
            user=self.student,
            company=company
        )
        assert assignment.role.code == 'exporter'
        assert assignment.status == UserCompanyRole.Status.ACTIVE
        assert assignment.is_active is True

    def test_create_company_missing_name(self, db):
        """Test creating a company without name."""
        self.client.force_authenticate(user=self.student)
        response = self.client.post('/api/v1/companies/', {
            'type': '进出口贸易'
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['code'] == 3002  # Parameter error

    def test_create_company_duplicate_name(self, db):
        """Test creating a company with duplicate name."""
        # Create existing company
        Company.objects.create(
            name='已存在公司',
            code='COMP_000001'
        )

        self.client.force_authenticate(user=self.student)
        response = self.client.post('/api/v1/companies/', {
            'name': '已存在公司'
        })

        # Should get database integrity error
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_get_company_members(self, db):
        """Test getting company members."""
        # Create company with members
        company = Company.objects.create(
            name='测试公司',
            code='COMP_000001'
        )

        UserCompanyRole.objects.create(
            user=self.student,
            company=company,
            role=self.exporter_role,
            status=UserCompanyRole.Status.ACTIVE,
            is_active=True
        )
        # Create pending assignment (should not appear in members)
        UserCompanyRole.objects.create(
            user=self.student2,
            company=company,
            role=self.exporter_role,
            status=UserCompanyRole.Status.PENDING
        )

        self.client.force_authenticate(user=self.student)
        response = self.client.get(f'/api/v1/companies/{company.id}/members/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['code'] == 0
        assert 'data' in response.data
        assert 'company' in response.data['data']
        assert 'members' in response.data['data']
        assert len(response.data['data']['members']) == 1
        assert response.data['data']['members'][0]['username'] == 'student'

    def test_get_company_members_not_found(self, db):
        """Test getting members of non-existent company."""
        self.client.force_authenticate(user=self.student)
        response = self.client.get('/api/v1/companies/99999/members/')

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data['code'] == 4001  # Company not found

    def test_join_company_success(self, db):
        """Test joining a company successfully."""
        company = Company.objects.create(
            name='测试公司',
            code='COMP_000001'
        )

        self.client.force_authenticate(user=self.student)
        response = self.client.post(f'/api/v1/companies/{company.id}/join/', {
            'role_code': 'exporter',
            'notes': '希望加入贵公司'
        })

        assert response.status_code == status.HTTP_200_OK
        assert response.data['code'] == 0
        assert response.data['message'] == '申请已提交，等待审核'

        # Verify the role was created
        assignment = UserCompanyRole.objects.get(
            user=self.student,
            company=company
        )
        assert assignment.status == UserCompanyRole.Status.PENDING

    def test_join_company_not_found(self, db):
        """Test joining a non-existent company."""
        self.client.force_authenticate(user=self.student)
        response = self.client.post('/api/v1/companies/99999/join/', {
            'role_code': 'exporter'
        })

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data['code'] == 4001  # Company not found
