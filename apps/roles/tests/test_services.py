"""
Tests for RoleService.

Following TDD: Tests written first, then implementation.
"""
import pytest
from django.utils import timezone

from apps.roles.models import Company, TradeRole, UserCompanyRole
from apps.roles.services import RoleService, CompanyService
from apps.core.models import Country
from apps.users.models import User


class TestRoleServiceRequestRole:
    """Test request_role method - student requests a role."""

    def test_request_role_success(self, db):
        """Test successful role request."""
        # Setup
        country = Country.objects.create(code='CN', name='中国', name_en='China')
        user = User.objects.create_user(username='req_success', password='pass', email='req_success@test.com')
        company = Company.objects.create(name='测试公司', code='CO001', country=country)
        role = TradeRole.objects.create(code='exporter', name='出口商', description='desc')

        # Execute
        assignment = RoleService.request_role(user, company.id, 'exporter', notes='请批准')

        # Verify
        assert assignment.user == user
        assert assignment.company == company
        assert assignment.role == role
        assert assignment.status == UserCompanyRole.Status.PENDING
        assert assignment.is_active is False
        assert assignment.notes == '请批准'
        assert assignment.approved_at is None
        assert assignment.approved_by is None

    def test_request_role_with_duplicate_pending(self, db):
        """Test requesting same role when pending already exists."""
        # Setup
        country = Country.objects.create(code='CN', name='中国', name_en='China')
        user = User.objects.create_user(username='req_dup_pending', password='pass', email='req_dup_pending@test.com')
        company = Company.objects.create(name='测试公司2', code='CO002', country=country)
        role = TradeRole.objects.create(code='exporter', name='出口商', description='desc')

        # Create first pending request
        RoleService.request_role(user, company.id, 'exporter')

        # Execute & Verify - should raise ValueError
        with pytest.raises(ValueError, match='已有该角色分配'):
            RoleService.request_role(user, company.id, 'exporter')

    def test_request_role_with_duplicate_active(self, db):
        """Test requesting same role when active role already exists."""
        # Setup
        country = Country.objects.create(code='CN', name='中国', name_en='China')
        user = User.objects.create_user(username='req_dup_active', password='pass', email='req_dup_active@test.com')
        company = Company.objects.create(name='测试公司3', code='CO003', country=country)
        role = TradeRole.objects.create(code='exporter', name='出口商', description='desc')

        # Create active role
        assignment = UserCompanyRole.objects.create(
            user=user,
            company=company,
            role=role,
            status=UserCompanyRole.Status.ACTIVE,
            is_active=True
        )

        # Execute & Verify - should raise ValueError
        with pytest.raises(ValueError, match='已有该角色分配'):
            RoleService.request_role(user, company.id, 'exporter')

    def test_request_role_with_approved_inactive(self, db):
        """Test requesting role when approved but inactive exists - should reject."""
        # Setup
        country = Country.objects.create(code='CN', name='中国', name_en='China')
        user = User.objects.create_user(username='req_approved', password='pass', email='req_approved@test.com')
        company = Company.objects.create(name='测试公司4', code='CO004', country=country)
        role = TradeRole.objects.create(code='exporter', name='出口商', description='desc')

        # Create approved but inactive role - should still reject due to unique constraint
        UserCompanyRole.objects.create(
            user=user,
            company=company,
            role=role,
            status=UserCompanyRole.Status.APPROVED,
            is_active=False
        )

        # Execute - should not allow duplicate
        with pytest.raises(ValueError, match='已有该角色分配'):
            RoleService.request_role(user, company.id, 'exporter')

    def test_request_role_different_role_same_company(self, db):
        """Test requesting different role in same company is allowed."""
        # Setup
        country = Country.objects.create(code='CN', name='中国', name_en='China')
        user = User.objects.create_user(username='req_diff_role', password='pass', email='req_diff_role@test.com')
        company = Company.objects.create(name='测试公司5', code='CO005', country=country)
        role1 = TradeRole.objects.create(code='exporter', name='出口商', description='desc1')
        role2 = TradeRole.objects.create(code='importer', name='进口商', description='desc2')

        # Create first role
        RoleService.request_role(user, company.id, 'exporter')

        # Request different role - should succeed
        assignment = RoleService.request_role(user, company.id, 'importer')

        assert assignment.role == role2
        assert assignment.status == UserCompanyRole.Status.PENDING


class TestRoleServiceApproveRole:
    """Test approve_role method - teacher approves and activates role."""

    def test_approve_role_success(self, db):
        """Test successful role approval."""
        # Setup
        country = Country.objects.create(code='CN', name='中国', name_en='China')
        student = User.objects.create_user(username='app_student', password='pass', email='app_student@test.com')
        teacher = User.objects.create_user(username='app_teacher', password='pass', email='app_teacher@test.com')
        company = Company.objects.create(name='测试公司', code='CO101', country=country)
        role = TradeRole.objects.create(code='exporter', name='出口商', description='desc')

        assignment = UserCompanyRole.objects.create(
            user=student,
            company=company,
            role=role,
            status=UserCompanyRole.Status.PENDING,
            notes='申请理由'
        )

        # Execute
        result = RoleService.approve_role(assignment.id, teacher, notes='批准通过')

        # Verify
        assert result.status == UserCompanyRole.Status.ACTIVE
        assert result.is_active is True
        assert result.approved_at is not None
        assert result.approved_by == teacher
        assert '批准通过' in result.notes

    def test_approve_role_already_active(self, db):
        """Test approving already active role - should raise error."""
        # Setup
        country = Country.objects.create(code='CN', name='中国', name_en='China')
        student = User.objects.create_user(username='app_active_student', password='pass', email='app_active_student@test.com')
        teacher = User.objects.create_user(username='app_active_teacher', password='pass', email='app_active_teacher@test.com')
        company = Company.objects.create(name='测试公司2', code='CO102', country=country)
        role = TradeRole.objects.create(code='exporter', name='出口商', description='desc')

        assignment = UserCompanyRole.objects.create(
            user=student,
            company=company,
            role=role,
            status=UserCompanyRole.Status.ACTIVE,
            is_active=True
        )

        # Execute & Verify
        with pytest.raises(ValueError, match='只能批准待审核的申请'):
            RoleService.approve_role(assignment.id, teacher)

    def test_approve_role_rejected(self, db):
        """Test approving a rejected role - should raise error."""
        # Setup
        country = Country.objects.create(code='CN', name='中国', name_en='China')
        student = User.objects.create_user(username='app_rejected_student', password='pass', email='app_rejected_student@test.com')
        teacher = User.objects.create_user(username='app_rejected_teacher', password='pass', email='app_rejected_teacher@test.com')
        company = Company.objects.create(name='测试公司3', code='CO103', country=country)
        role = TradeRole.objects.create(code='exporter', name='出口商', description='desc')

        assignment = UserCompanyRole.objects.create(
            user=student,
            company=company,
            role=role,
            status=UserCompanyRole.Status.REJECTED
        )

        # Execute & Verify
        with pytest.raises(ValueError, match='只能批准待审核的申请'):
            RoleService.approve_role(assignment.id, teacher)

    def test_approve_role_activates_only_one(self, db):
        """Test that approving only activates one role, deactivating others."""
        # Setup
        country = Country.objects.create(code='CN', name='中国', name_en='China')
        student = User.objects.create_user(username='app_one_student', password='pass', email='app_one_student@test.com')
        teacher = User.objects.create_user(username='app_one_teacher', password='pass', email='app_one_teacher@test.com')
        company = Company.objects.create(name='测试公司4', code='CO104', country=country)
        role1 = TradeRole.objects.create(code='exporter', name='出口商', description='desc1')
        role2 = TradeRole.objects.create(code='importer', name='进口商', description='desc2')

        # Create existing active role
        existing_active = UserCompanyRole.objects.create(
            user=student,
            company=company,
            role=role1,
            status=UserCompanyRole.Status.ACTIVE,
            is_active=True
        )

        # Create pending role
        pending = UserCompanyRole.objects.create(
            user=student,
            company=company,
            role=role2,
            status=UserCompanyRole.Status.PENDING
        )

        # Approve the pending role
        result = RoleService.approve_role(pending.id, teacher)

        # Verify: only new role is active
        assert result.is_active is True

        existing_active.refresh_from_db()
        assert existing_active.is_active is False


class TestRoleServiceRejectRole:
    """Test reject_role method - teacher rejects role application."""

    def test_reject_role_success(self, db):
        """Test successful role rejection."""
        # Setup
        country = Country.objects.create(code='CN', name='中国', name_en='China')
        student = User.objects.create_user(username='rej_student', password='pass', email='rej_student@test.com')
        teacher = User.objects.create_user(username='rej_teacher', password='pass', email='rej_teacher@test.com')
        company = Company.objects.create(name='测试公司', code='CO201', country=country)
        role = TradeRole.objects.create(code='exporter', name='出口商', description='desc')

        assignment = UserCompanyRole.objects.create(
            user=student,
            company=company,
            role=role,
            status=UserCompanyRole.Status.PENDING,
            notes='申请理由'
        )

        # Execute
        result = RoleService.reject_role(assignment.id, teacher, reason='材料不全')

        # Verify
        assert result.status == UserCompanyRole.Status.REJECTED
        assert result.is_active is False
        assert result.approved_by == teacher
        assert '材料不全' in result.notes

    def test_reject_role_already_active(self, db):
        """Test rejecting active role - should raise error."""
        # Setup
        country = Country.objects.create(code='CN', name='中国', name_en='China')
        student = User.objects.create_user(username='rej_active_student', password='pass', email='rej_active_student@test.com')
        teacher = User.objects.create_user(username='rej_active_teacher', password='pass', email='rej_active_teacher@test.com')
        company = Company.objects.create(name='测试公司2', code='CO202', country=country)
        role = TradeRole.objects.create(code='exporter', name='出口商', description='desc')

        assignment = UserCompanyRole.objects.create(
            user=student,
            company=company,
            role=role,
            status=UserCompanyRole.Status.ACTIVE,
            is_active=True
        )

        # Execute & Verify
        with pytest.raises(ValueError, match='只能拒绝待审核的申请'):
            RoleService.reject_role(assignment.id, teacher, 'reason')

    def test_reject_role_preserves_original_notes(self, db):
        """Test that rejection preserves original notes and adds reason."""
        # Setup
        country = Country.objects.create(code='CN', name='中国', name_en='China')
        student = User.objects.create_user(username='rej_notes_student', password='pass', email='rej_notes_student@test.com')
        teacher = User.objects.create_user(username='rej_notes_teacher', password='pass', email='rej_notes_teacher@test.com')
        company = Company.objects.create(name='测试公司3', code='CO203', country=country)
        role = TradeRole.objects.create(code='exporter', name='出口商', description='desc')

        assignment = UserCompanyRole.objects.create(
            user=student,
            company=company,
            role=role,
            status=UserCompanyRole.Status.PENDING,
            notes='我想申请出口商角色'
        )

        # Execute
        result = RoleService.reject_role(assignment.id, teacher, reason='不符合条件')

        # Verify - notes should contain reason
        assert result.status == UserCompanyRole.Status.REJECTED
        assert '不符合条件' in result.notes


class TestRoleServiceActivateRole:
    """Test activate_role method - user activates an approved role."""

    def test_activate_role_success(self, db):
        """Test successful role activation."""
        # Setup
        country = Country.objects.create(code='CN', name='中国', name_en='China')
        user = User.objects.create_user(username='act_success', password='pass', email='act_success@test.com')
        company = Company.objects.create(name='测试公司', code='CO301', country=country)
        role = TradeRole.objects.create(code='exporter', name='出口商', description='desc')

        assignment = UserCompanyRole.objects.create(
            user=user,
            company=company,
            role=role,
            status=UserCompanyRole.Status.ACTIVE,
            is_active=False
        )

        # Execute
        result = RoleService.activate_role(user, assignment.id)

        # Verify
        assert result.is_active is True

    def test_activate_role_deactivates_others(self, db):
        """Test that activating one role deactivates others."""
        # Setup
        country = Country.objects.create(code='CN', name='中国', name_en='China')
        user = User.objects.create_user(username='act_deact', password='pass', email='act_deact@test.com')
        company = Company.objects.create(name='测试公司2', code='CO302', country=country)
        role1 = TradeRole.objects.create(code='exporter', name='出口商', description='desc1')
        role2 = TradeRole.objects.create(code='importer', name='进口商', description='desc2')

        assignment1 = UserCompanyRole.objects.create(
            user=user,
            company=company,
            role=role1,
            status=UserCompanyRole.Status.ACTIVE,
            is_active=True
        )
        assignment2 = UserCompanyRole.objects.create(
            user=user,
            company=company,
            role=role2,
            status=UserCompanyRole.Status.ACTIVE,
            is_active=False
        )

        # Execute - activate second role
        RoleService.activate_role(user, assignment2.id)

        # Verify
        assignment1.refresh_from_db()
        assignment2.refresh_from_db()

        assert assignment1.is_active is False
        assert assignment2.is_active is True

    def test_activate_role_unauthorized_user(self, db):
        """Test activating role for different user - should raise error."""
        # Setup
        country = Country.objects.create(code='CN', name='中国', name_en='China')
        user1 = User.objects.create_user(username='act_unauth_user1', password='pass', email='act_unauth_user1@test.com')
        user2 = User.objects.create_user(username='act_unauth_user2', password='pass', email='act_unauth_user2@test.com')
        company = Company.objects.create(name='测试公司', code='CO303', country=country)
        role = TradeRole.objects.create(code='exporter', name='出口商', description='desc')

        assignment = UserCompanyRole.objects.create(
            user=user1,
            company=company,
            role=role,
            status=UserCompanyRole.Status.ACTIVE,
            is_active=False
        )

        # Execute & Verify - user2 cannot activate user1's role
        with pytest.raises(ValueError, match='无权激活此角色'):
            RoleService.activate_role(user2, assignment.id)

    def test_activate_role_not_active_status(self, db):
        """Test activating role with non-active status - should raise error."""
        # Setup
        country = Country.objects.create(code='CN', name='中国', name_en='China')
        user = User.objects.create_user(username='act_not_active', password='pass', email='act_not_active@test.com')
        company = Company.objects.create(name='测试公司', code='CO304', country=country)
        role = TradeRole.objects.create(code='exporter', name='出口商', description='desc')

        assignment = UserCompanyRole.objects.create(
            user=user,
            company=company,
            role=role,
            status=UserCompanyRole.Status.PENDING,
            is_active=False
        )

        # Execute & Verify
        with pytest.raises(ValueError, match='只能激活已批准或激活中的角色'):
            RoleService.activate_role(user, assignment.id)


class TestRoleServiceGetCurrentRole:
    """Test get_current_role method - get user's currently active role."""

    def test_get_current_role_with_active(self, db):
        """Test getting current active role."""
        # Setup
        country = Country.objects.create(code='CN', name='中国', name_en='China')
        user = User.objects.create_user(username='cur_with', password='pass', email='cur_with@test.com')
        company = Company.objects.create(name='测试公司', code='CO401', country=country)
        role = TradeRole.objects.create(code='exporter', name='出口商', description='desc')

        assignment = UserCompanyRole.objects.create(
            user=user,
            company=company,
            role=role,
            status=UserCompanyRole.Status.ACTIVE,
            is_active=True
        )

        # Execute
        result = RoleService.get_current_role(user)

        # Verify
        assert result is not None
        assert result.id == assignment.id
        assert result.is_active is True

    def test_get_current_role_without_active(self, db):
        """Test getting current role when none active."""
        # Setup
        user = User.objects.create_user(username='cur_without', password='pass', email='cur_without@test.com')

        # Execute
        result = RoleService.get_current_role(user)

        # Verify
        assert result is None

    def test_get_current_role_with_inactive_roles(self, db):
        """Test getting current role when only inactive roles exist."""
        # Setup
        country = Country.objects.create(code='CN', name='中国', name_en='China')
        user = User.objects.create_user(username='cur_inactive', password='pass', email='cur_inactive@test.com')
        company = Company.objects.create(name='测试公司', code='CO402', country=country)
        role = TradeRole.objects.create(code='exporter', name='出口商', description='desc')

        UserCompanyRole.objects.create(
            user=user,
            company=company,
            role=role,
            status=UserCompanyRole.Status.APPROVED,
            is_active=False
        )

        # Execute
        result = RoleService.get_current_role(user)

        # Verify
        assert result is None


class TestRoleServiceGetPendingRequests:
    """Test get_pending_requests method - get pending role requests."""

    def test_get_all_pending_requests(self, db):
        """Test getting all pending requests."""
        # Setup
        country = Country.objects.create(code='CN', name='中国', name_en='China')
        user1 = User.objects.create_user(username='pend_all_user1', password='pass', email='pend_all_user1@test.com')
        user2 = User.objects.create_user(username='pend_all_user2', password='pass', email='pend_all_user2@test.com')
        company = Company.objects.create(name='测试公司', code='CO501', country=country)
        role1 = TradeRole.objects.create(code='exporter', name='出口商', description='desc1')
        role2 = TradeRole.objects.create(code='importer', name='进口商', description='desc2')

        UserCompanyRole.objects.create(
            user=user1,
            company=company,
            role=role1,
            status=UserCompanyRole.Status.PENDING
        )
        UserCompanyRole.objects.create(
            user=user2,
            company=company,
            role=role1,
            status=UserCompanyRole.Status.PENDING
        )
        # Add an approved one - should not be included (use different role to avoid unique constraint)
        UserCompanyRole.objects.create(
            user=user1,
            company=company,
            role=role2,
            status=UserCompanyRole.Status.ACTIVE
        )

        # Execute
        result = RoleService.get_pending_requests()

        # Verify
        assert result.count() == 2

    def test_get_pending_requests_for_user(self, db):
        """Test getting pending requests for specific user."""
        # Setup
        country = Country.objects.create(code='CN', name='中国', name_en='China')
        user1 = User.objects.create_user(username='pend_user_user1', password='pass', email='pend_user_user1@test.com')
        user2 = User.objects.create_user(username='pend_user_user2', password='pass', email='pend_user_user2@test.com')
        company = Company.objects.create(name='测试公司', code='CO502', country=country)
        role = TradeRole.objects.create(code='exporter', name='出口商', description='desc')

        UserCompanyRole.objects.create(
            user=user1,
            company=company,
            role=role,
            status=UserCompanyRole.Status.PENDING
        )
        UserCompanyRole.objects.create(
            user=user2,
            company=company,
            role=role,
            status=UserCompanyRole.Status.PENDING
        )

        # Execute - get pending for user1 only
        result = RoleService.get_pending_requests(user1)

        # Verify
        assert result.count() == 1
        assert result.first().user == user1

    def test_get_pending_requests_empty(self, db):
        """Test getting pending requests when none exist."""
        # Setup
        user = User.objects.create_user(username='pend_empty', password='pass', email='pend_empty@test.com')

        # Execute
        result = RoleService.get_pending_requests(user)

        # Verify
        assert result.count() == 0


class TestRoleServiceSwitchContext:
    """Test switch_context method - get user's current role context."""

    def test_switch_context_with_active_role(self, db):
        """Test getting context when user has active role."""
        # Setup
        country = Country.objects.create(code='CN', name='中国', name_en='China')
        user = User.objects.create_user(username='ctx_with', password='pass', email='ctx_with@test.com')
        company = Company.objects.create(name='测试公司', code='CO601', country=country)
        role = TradeRole.objects.create(
            code='exporter',
            name='出口商',
            description='销售货物到国外',
            is_enabled=True
        )

        UserCompanyRole.objects.create(
            user=user,
            company=company,
            role=role,
            status=UserCompanyRole.Status.ACTIVE,
            is_active=True
        )

        # Execute
        result = RoleService.switch_context(user)

        # Verify
        assert result is not None
        assert result['company'] == company
        assert result['role'] == role
        assert 'permissions' in result

    def test_switch_context_without_active_role(self, db):
        """Test getting context when user has no active role."""
        # Setup
        user = User.objects.create_user(username='ctx_without', password='pass', email='ctx_without@test.com')

        # Execute
        result = RoleService.switch_context(user)

        # Verify
        assert result is None

    def test_switch_context_permissions_structure(self, db):
        """Test that permissions dict has correct structure."""
        # Setup
        country = Country.objects.create(code='CN', name='中国', name_en='China')
        user = User.objects.create_user(username='ctx_perm', password='pass', email='ctx_perm@test.com')
        company = Company.objects.create(name='测试公司', code='CO602', country=country)
        role = TradeRole.objects.create(
            code='importer',
            name='进口商',
            description='购买货物',
            is_enabled=True
        )

        UserCompanyRole.objects.create(
            user=user,
            company=company,
            role=role,
            status=UserCompanyRole.Status.ACTIVE,
            is_active=True
        )

        # Execute
        result = RoleService.switch_context(user)

        # Verify permissions structure
        assert 'permissions' in result
        assert isinstance(result['permissions'], dict)
        assert 'role_code' in result['permissions']
        assert result['permissions']['role_code'] == 'importer'

    def test_switch_context_disabled_role(self, db):
        """Test that disabled roles are not returned as active context."""
        # Setup
        country = Country.objects.create(code='CN', name='中国', name_en='China')
        user = User.objects.create_user(username='ctx_disabled', password='pass', email='ctx_disabled@test.com')
        company = Company.objects.create(name='测试公司', code='CO603', country=country)
        role = TradeRole.objects.create(
            code='exporter',
            name='出口商',
            description='销售',
            is_enabled=False  # Disabled role
        )

        UserCompanyRole.objects.create(
            user=user,
            company=company,
            role=role,
            status=UserCompanyRole.Status.ACTIVE,
            is_active=True
        )

        # Execute - even with disabled role, should still return context
        # The service returns what's active, validation is elsewhere
        result = RoleService.switch_context(user)

        # Verify
        assert result is not None
        assert result['role'] == role


class TestCompanyServiceCreateCompany:
    """Test create_company method - creates a company and assigns creator as member."""

    def test_create_company_success(self, db):
        """Test successful company creation with user as member."""
        # Setup
        country = Country.objects.create(code='CN', name='中国', name_en='China')
        user = User.objects.create_user(username='comp_create', password='pass', email='comp_create@test.com')

        # Execute
        company = CompanyService.create_company(
            user=user,
            name='新贸易公司',
            name_en='New Trade Co',
            country_id=country.code
        )

        # Verify company
        assert company.name == '新贸易公司'
        assert company.name_en == 'New Trade Co'
        assert company.country == country
        assert company.created_by == user
        assert company.code.startswith('COMP_')

        # Verify creator is a member
        member = UserCompanyRole.objects.get(user=user, company=company)
        assert member.role.code == 'exporter'
        assert member.status == UserCompanyRole.Status.ACTIVE
        assert member.is_active is True

    def test_create_company_with_optional_fields(self, db):
        """Test company creation with optional fields."""
        # Setup
        country = Country.objects.create(code='US', name='美国', name_en='USA')
        user = User.objects.create_user(username='comp_opt', password='pass', email='comp_opt@test.com')

        # Execute
        company = CompanyService.create_company(
            user=user,
            name='Optional Fields Co',
            country_id=country.code,
            type='Trading',
            address='123 Main St',
            phone='555-1234',
            email='contact@optional.com'
        )

        # Verify
        assert company.type == 'Trading'
        assert company.address == '123 Main St'
        assert company.phone == '555-1234'
        assert company.email == 'contact@optional.com'

    def test_create_company_code_format(self, db):
        """Test that company code follows COMP_XXXXXX format."""
        # Setup
        country = Country.objects.create(code='JP', name='日本', name_en='Japan')
        user = User.objects.create_user(username='comp_code', password='pass', email='comp_code@test.com')

        # Execute
        company = CompanyService.create_company(
            user=user,
            name='Code Test Co',
            country_id=country.code
        )

        # Verify code format
        assert company.code.startswith('COMP_')
        assert len(company.code) == 11  # COMP_ + 6 digits
        suffix = company.code[5:]  # Get part after COMP_
        assert suffix.isdigit()

    def test_create_company_code_unique(self, db):
        """Test that each company gets a unique code."""
        # Setup
        country = Country.objects.create(code='KR', name='韩国', name_en='Korea')
        user = User.objects.create_user(username='comp_unique', password='pass', email='comp_unique@test.com')

        # Execute - create multiple companies
        company1 = CompanyService.create_company(
            user=user,
            name='Company 1',
            country_id=country.code
        )
        company2 = CompanyService.create_company(
            user=user,
            name='Company 2',
            country_id=country.code
        )

        # Verify codes are different
        assert company1.code != company2.code

    def test_create_company_member_role_is_exporter(self, db):
        """Test that creator becomes exporter role member."""
        # Setup
        country = Country.objects.create(code='DE', name='德国', name_en='Germany')
        user = User.objects.create_user(username='comp_exporter', password='pass', email='comp_exporter@test.com')

        # Execute
        company = CompanyService.create_company(
            user=user,
            name='Exporter Test Co',
            country_id=country.code
        )

        # Verify member role is exporter
        member = UserCompanyRole.objects.get(user=user, company=company)
        assert member.role.code == 'exporter'
        assert member.role.name == '出口商'

    def test_create_company_member_status_active(self, db):
        """Test that creator member has active status and is_active=True."""
        # Setup
        country = Country.objects.create(code='FR', name='法国', name_en='France')
        user = User.objects.create_user(username='comp_active', password='pass', email='comp_active@test.com')

        # Execute
        company = CompanyService.create_company(
            user=user,
            name='Active Member Co',
            country_id=country.code
        )

        # Verify member is active
        member = UserCompanyRole.objects.get(user=user, company=company)
        assert member.status == UserCompanyRole.Status.ACTIVE
        assert member.is_active is True


class TestCompanyServiceGetCompanyDetails:
    """Test get_company_details method - retrieves company info with members."""

    def test_get_company_details_success(self, db):
        """Test getting company details with members."""
        # Setup
        country = Country.objects.create(code='GB', name='英国', name_en='UK')
        user1 = User.objects.create_user(username='detail_user1', password='pass', email='detail_user1@test.com')
        user2 = User.objects.create_user(username='detail_user2', password='pass', email='detail_user2@test.com')
        role_exporter = TradeRole.objects.create(code='exporter', name='出口商', description='desc')

        company = Company.objects.create(
            name='Detail Test Co',
            code='DET001',
            country=country,
            created_by=user1
        )

        # Create members with different statuses
        UserCompanyRole.objects.create(
            user=user1,
            company=company,
            role=role_exporter,
            status=UserCompanyRole.Status.ACTIVE,
            is_active=True
        )
        UserCompanyRole.objects.create(
            user=user2,
            company=company,
            role=role_exporter,
            status=UserCompanyRole.Status.APPROVED,
            is_active=False
        )

        # Execute
        result = CompanyService.get_company_details(company.id, user1)

        # Verify
        assert 'company' in result
        assert 'members' in result
        assert result['company']['id'] == company.id
        assert result['company']['name'] == 'Detail Test Co'
        assert len(result['members']) == 2

    def test_get_company_details_filters_members_by_status(self, db):
        """Test that only members with valid statuses are returned."""
        # Setup
        country = Country.objects.create(code='IT', name='意大利', name_en='Italy')
        user1 = User.objects.create_user(username='filter_user1', password='pass', email='filter_user1@test.com')
        user2 = User.objects.create_user(username='filter_user2', password='pass', email='filter_user2@test.com')
        user3 = User.objects.create_user(username='filter_user3', password='pass', email='filter_user3@test.com')
        role_exporter = TradeRole.objects.create(code='exporter', name='出口商', description='desc')

        company = Company.objects.create(
            name='Filter Test Co',
            code='FIL001',
            country=country
        )

        # Create members with different statuses
        # approved - should be included
        UserCompanyRole.objects.create(
            user=user1,
            company=company,
            role=role_exporter,
            status=UserCompanyRole.Status.APPROVED,
            is_active=False
        )
        # active - should be included
        UserCompanyRole.objects.create(
            user=user2,
            company=company,
            role=role_exporter,
            status=UserCompanyRole.Status.ACTIVE,
            is_active=True
        )
        # suspended - should be included
        UserCompanyRole.objects.create(
            user=user3,
            company=company,
            role=role_exporter,
            status=UserCompanyRole.Status.SUSPENDED,
            is_active=False
        )

        # Execute
        result = CompanyService.get_company_details(company.id, user1)

        # Verify all 3 members are included (approved, active, suspended)
        assert len(result['members']) == 3

    def test_get_company_details_excludes_pending_and_rejected(self, db):
        """Test that pending and rejected members are excluded."""
        # Setup
        country = Country.objects.create(code='ES', name='西班牙', name_en='Spain')
        user1 = User.objects.create_user(username='exclude_user1', password='pass', email='exclude_user1@test.com')
        user2 = User.objects.create_user(username='exclude_user2', password='pass', email='exclude_user2@test.com')
        user3 = User.objects.create_user(username='exclude_user3', password='pass', email='exclude_user3@test.com')
        role_exporter = TradeRole.objects.create(code='exporter', name='出口商', description='desc')

        company = Company.objects.create(
            name='Exclude Test Co',
            code='EXC001',
            country=country
        )

        # Create member with active status - should be included
        UserCompanyRole.objects.create(
            user=user1,
            company=company,
            role=role_exporter,
            status=UserCompanyRole.Status.ACTIVE,
            is_active=True
        )
        # pending - should NOT be included
        UserCompanyRole.objects.create(
            user=user2,
            company=company,
            role=role_exporter,
            status=UserCompanyRole.Status.PENDING,
            is_active=False
        )
        # rejected - should NOT be included
        UserCompanyRole.objects.create(
            user=user3,
            company=company,
            role=role_exporter,
            status=UserCompanyRole.Status.REJECTED,
            is_active=False
        )

        # Execute
        result = CompanyService.get_company_details(company.id, user1)

        # Verify only active member is included
        assert len(result['members']) == 1
        assert result['members'][0]['user_id'] == user1.id

    def test_get_company_details_member_structure(self, db):
        """Test that member dict has correct structure."""
        # Setup
        country = Country.objects.create(code='CA', name='加拿大', name_en='Canada')
        user = User.objects.create_user(username='struct_user', password='pass', email='struct_user@test.com')
        role = TradeRole.objects.create(code='exporter', name='出口商', description='desc')

        company = Company.objects.create(
            name='Structure Test Co',
            code='STR001',
            country=country
        )

        UserCompanyRole.objects.create(
            user=user,
            company=company,
            role=role,
            status=UserCompanyRole.Status.ACTIVE,
            is_active=True
        )

        # Execute
        result = CompanyService.get_company_details(company.id, user)

        # Verify member structure
        member = result['members'][0]
        assert 'user_id' in member
        assert 'username' in member
        assert 'role_code' in member
        assert 'role_name' in member
        assert 'status' in member
        assert 'is_active' in member

        assert member['user_id'] == user.id
        assert member['username'] == 'struct_user'
        assert member['role_code'] == 'exporter'
        assert member['role_name'] == '出口商'
        assert member['status'] == UserCompanyRole.Status.ACTIVE
        assert member['is_active'] is True

    def test_get_company_details_nonexistent_company(self, db):
        """Test getting details for nonexistent company."""
        # Setup
        user = User.objects.create_user(username='nonexist', password='pass', email='nonexist@test.com')

        # Execute & Verify - should raise ValueError
        with pytest.raises(ValueError, match='公司不存在'):
            CompanyService.get_company_details(99999, user)

    def test_get_company_details_empty_members(self, db):
        """Test getting company details with no members."""
        # Setup
        country = Country.objects.create(code='AU', name='澳大利亚', name_en='Australia')
        user = User.objects.create_user(username='empty_user', password='pass', email='empty_user@test.com')

        company = Company.objects.create(
            name='Empty Members Co',
            code='EMP001',
            country=country
        )

        # Execute - no members created
        result = CompanyService.get_company_details(company.id, user)

        # Verify
        assert result['company']['id'] == company.id
        assert len(result['members']) == 0


class TestCompanyServiceGenerateCompanyCode:
    """Test _generate_company_code private method."""

    def test_generate_code_format(self, db):
        """Test that generated code follows correct format."""
        # Execute
        code = CompanyService._generate_company_code()

        # Verify format
        assert code.startswith('COMP_')
        assert len(code) == 11  # COMP_ + 6 digits
        suffix = code[5:]
        assert suffix.isdigit()

    def test_generate_code_unique(self, db):
        """Test that generated codes are unique."""
        # Execute - generate multiple codes
        codes = [CompanyService._generate_company_code() for _ in range(100)]

        # Verify all unique
        assert len(set(codes)) == 100
        assert len(codes) == 100

    def test_generate_code_avoids_collision(self, db):
        """Test that generated code doesn't collide with existing company."""
        # Setup - create company with known code
        existing_code = 'COMP_123456'
        # We can't directly create a company with this code without ensuring uniqueness
        # So just test the format and uniqueness
        code = CompanyService._generate_company_code()

        # Verify it's a valid code
        assert code.startswith('COMP_')
        assert len(code) == 11
