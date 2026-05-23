from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.scoring.models import Experiment, ScoringMetric, ScoreSheet
from apps.users.models import User
from apps.roles.models import TradeRole, Company, UserCompanyRole


class ScoreSheetAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.teacher = User.objects.create_user(
            username='teacher1', password='test', user_type='teacher',
            email='teacher1@test.com',
        )
        self.student = User.objects.create_user(
            username='student1', password='test', user_type='student',
            email='student1@test.com',
        )
        self.experiment = Experiment.objects.create(
            name='测试实验',
            start_date=timezone.now(),
            status='active',
            created_by=self.teacher,
        )
        role = TradeRole.objects.create(
            code='exporter', name='出口商', description='', sort_order=1,
        )
        self.company = Company.objects.create(name='公司', code='C01')
        self.ucr = UserCompanyRole.objects.create(
            user=self.student, company=self.company, role=role,
            status='active', is_active=True,
        )

    def test_student_can_list_own_sheets(self):
        self.client.force_authenticate(self.student)
        ScoreSheet.objects.create(
            experiment=self.experiment, user=self.student,
            user_company_role=self.ucr, auto_score=Decimal('85'),
            final_score=Decimal('85'), status='auto_scored',
        )
        resp = self.client.get('/api/v1/scoring/sheets/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data['results']), 1)

    def test_student_cannot_see_others(self):
        other = User.objects.create_user(
            username='student2', password='test', user_type='student',
            email='student2@test.com',
        )
        self.client.force_authenticate(other)
        ScoreSheet.objects.create(
            experiment=self.experiment, user=self.student,
            user_company_role=self.ucr, auto_score=Decimal('85'),
            final_score=Decimal('85'), status='auto_scored',
        )
        resp = self.client.get('/api/v1/scoring/sheets/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data['results']), 0)

    def test_teacher_can_review(self):
        self.client.force_authenticate(self.teacher)
        sheet = ScoreSheet.objects.create(
            experiment=self.experiment, user=self.student,
            user_company_role=self.ucr, auto_score=Decimal('85'),
            final_score=Decimal('85'), status='auto_scored',
        )
        resp = self.client.post(
            f'/api/v1/scoring/sheets/{sheet.id}/review/',
            {'adjustment': -5, 'comment': '需要改进'},
        )
        self.assertEqual(resp.status_code, 200)
        sheet.refresh_from_db()
        self.assertEqual(sheet.final_score, Decimal('80'))
        self.assertEqual(sheet.status, 'teacher_reviewed')

    def test_teacher_adjustment_exceeds_limit(self):
        self.client.force_authenticate(self.teacher)
        sheet = ScoreSheet.objects.create(
            experiment=self.experiment, user=self.student,
            user_company_role=self.ucr, auto_score=Decimal('85'),
            final_score=Decimal('85'), status='auto_scored',
        )
        resp = self.client.post(
            f'/api/v1/scoring/sheets/{sheet.id}/review/',
            {'adjustment': 30, 'comment': '超限'},
        )
        self.assertEqual(resp.status_code, 400)

    def test_student_cannot_review(self):
        self.client.force_authenticate(self.student)
        sheet = ScoreSheet.objects.create(
            experiment=self.experiment, user=self.student,
            user_company_role=self.ucr, auto_score=Decimal('85'),
            final_score=Decimal('85'), status='auto_scored',
        )
        resp = self.client.post(
            f'/api/v1/scoring/sheets/{sheet.id}/review/',
            {'adjustment': 5, 'comment': '作弊'},
        )
        self.assertEqual(resp.status_code, 403)


class ScoringMetricAPITest(TestCase):
    def test_list_metrics(self):
        self.client = APIClient()
        user = User.objects.create_user(
            username='u1', password='test', email='u1@test.com',
        )
        self.client.force_authenticate(user)
        ScoringMetric.objects.create(
            name='m1', display_name='指标1',
            dimension='financial', calculation_method='profit_margin',
            weight=Decimal('20'),
        )
        resp = self.client.get('/api/v1/scoring/metrics/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data['results']), 1)
