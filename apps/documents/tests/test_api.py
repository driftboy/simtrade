"""
API tests for Document views.
"""
import pytest
import json
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from apps.documents.models import Document, DocumentTemplate, DocumentDependency, DocumentValidation
from apps.teaching.models import Semester, Course, TeachingClass, StudentEnrollment

User = get_user_model()


def json_d(data):
    """Helper to serialize data to JSON string for Document.data field"""
    return json.dumps(data, ensure_ascii=False)


class DocumentAPITest(TestCase):
    """测试单证 API"""

    def setUp(self):
        """设置测试数据"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='testuser@example.com',
            password='testpass'
        )
        self.staff_user = User.objects.create_user(
            username='staff',
            email='staff@example.com',
            password='staffpass',
            is_staff=True
        )

        # 创建模板
        self.template = DocumentTemplate.objects.create(
            code='commercial_invoice',
            name='商业发票',
            content='<html>...</html>'
        )

    def test_list_documents(self):
        """测试获取单证列表"""
        self.client.force_authenticate(user=self.user)
        url = '/api/v1/documents/documents/'
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['code'], 0)

    def test_create_document(self):
        """测试创建单证"""
        self.client.force_authenticate(user=self.user)
        url = '/api/v1/documents/documents/'
        data = {
            'template': self.template.id,
            'data': {'invoice_no': 'INV001'}
        }
        response = self.client.post(url, data, format='json')

        if response.status_code != 200:
            print(f"Error response: {response.content.decode('utf-8')}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Document.objects.count(), 1)

    def test_create_document_check_dependency(self):
        """测试创建单证时检查依赖"""
        # 创建依赖关系：装箱单依赖于商业发票
        DocumentDependency.objects.create(
            document_type='packing_list',
            depends_on='commercial_invoice',
            dependency_type='sequential'
        )

        packing_template = DocumentTemplate.objects.create(
            code='packing_list',
            name='装箱单',
            content='<html>...</html>'
        )

        self.client.force_authenticate(user=self.user)
        url = '/api/v1/documents/documents/'
        data = {
            'template': packing_template.id,
            'data': {}
        }
        response = self.client.post(url, data, format='json')

        # 应该返回错误，因为依赖未满足
        self.assertEqual(response.status_code, 400)
        result = response.json()
        self.assertEqual(result['code'], 5001)
        self.assertIn('商业发票', result['message'])

    def test_submit_document(self):
        """测试提交审核"""
        self.client.force_authenticate(user=self.user)
        # 提供完整的必填字段
        doc = Document.objects.create(
            template=self.template,
            created_by=self.user,
            data=json_d({
                'invoice_no': 'INV001',
                'invoice_date': '2026-05-01',
                'invoice_amount': '1000',
                'buyer_name': 'ABC Trading',
                'seller_name': 'XYZ Export',
                'currency': 'USD'
            })
        )

        url = f'/api/v1/documents/documents/{doc.id}/submit/'
        response = self.client.post(url)

        if response.status_code != 200:
            print(f"Submit error: {response.content.decode('utf-8')}")

        self.assertEqual(response.status_code, 200)
        doc.refresh_from_db()
        self.assertEqual(doc.status, 'pending_review')

    def test_submit_document_validation_failed(self):
        """测试提交审核时校验失败"""
        self.client.force_authenticate(user=self.user)
        # 创建日期逻辑错误的数据（装运日期早于发票日期）
        doc = Document.objects.create(
            template=self.template,
            created_by=self.user,
            data=json_d({
                'invoice_no': 'INV001',
                'invoice_date': '2026-05-10',
                'shipment_date': '2026-05-01'
            })
        )

        url = f'/api/v1/documents/documents/{doc.id}/submit/'
        response = self.client.post(url)

        # 应该返回校验错误
        self.assertEqual(response.status_code, 400)
        result = response.json()
        self.assertEqual(result['code'], 5002)
        self.assertIn('校验不通过', result['message'])

    def test_approve_document(self):
        """测试审核通过单证（教师）"""
        doc = Document.objects.create(
            template=self.template,
            created_by=self.user,
            status='pending_review',
            data=json_d({})
        )

        self.client.force_authenticate(user=self.staff_user)
        url = f'/api/v1/documents/documents/{doc.id}/approve/'
        response = self.client.post(url)

        self.assertEqual(response.status_code, 200)
        doc.refresh_from_db()
        self.assertEqual(doc.status, 'approved')
        self.assertEqual(doc.reviewed_by, self.staff_user)

    def test_approve_document_permission_denied(self):
        """测试学生不能审核单证"""
        doc = Document.objects.create(
            template=self.template,
            created_by=self.user,
            status='pending_review',
            data=json_d({})
        )

        self.client.force_authenticate(user=self.user)
        url = f'/api/v1/documents/documents/{doc.id}/approve/'
        response = self.client.post(url)

        self.assertEqual(response.status_code, 403)

    def test_reject_document(self):
        """测试审核驳回单证"""
        doc = Document.objects.create(
            template=self.template,
            created_by=self.user,
            status='pending_review',
            data=json_d({})
        )

        self.client.force_authenticate(user=self.staff_user)
        url = f'/api/v1/documents/documents/{doc.id}/reject/'
        data = {'comment': '数据填写错误'}
        response = self.client.post(url, data, format='json')

        if response.status_code != 200:
            print(f"Reject error: {response.content.decode('utf-8')}")

        self.assertEqual(response.status_code, 200)
        doc.refresh_from_db()
        self.assertEqual(doc.status, 'rejected')
        self.assertEqual(doc.manual_review_comment, '数据填写错误')

    def test_template_list(self):
        """测试获取模板列表"""
        self.client.force_authenticate(user=self.user)
        url = '/api/v1/documents/templates/'
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result['code'], 0)
        self.assertGreater(len(result['data']), 0)

    def test_retrieve_document(self):
        """测试获取单个单证详情"""
        doc = Document.objects.create(
            template=self.template,
            created_by=self.user,
            data=json_d({'invoice_no': 'INV001'})
        )

        self.client.force_authenticate(user=self.user)
        url = f'/api/v1/documents/documents/{doc.id}/'
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result['data']['id'], doc.id)

    def test_update_document(self):
        """测试更新单证"""
        doc = Document.objects.create(
            template=self.template,
            created_by=self.user,
            data=json_d({'invoice_no': 'INV001'})
        )

        self.client.force_authenticate(user=self.user)
        url = f'/api/v1/documents/documents/{doc.id}/'
        data = {
            'data': {'invoice_no': 'INV002'}
        }
        response = self.client.put(url, data, format='json')

        if response.status_code != 200:
            print(f"Update error: {response.content.decode('utf-8')}")

        self.assertEqual(response.status_code, 200)
        doc.refresh_from_db()
        updated_data = json.loads(doc.data)
        self.assertEqual(updated_data['invoice_no'], 'INV002')

    def test_delete_document(self):
        """测试删除单证"""
        doc = Document.objects.create(
            template=self.template,
            created_by=self.user,
            data=json_d({'invoice_no': 'INV001'})
        )

        self.client.force_authenticate(user=self.user)
        url = f'/api/v1/documents/documents/{doc.id}/'
        response = self.client.delete(url)

        self.assertEqual(response.status_code, 204)
        self.assertEqual(Document.objects.count(), 0)

    def test_unauthenticated_access_denied(self):
        """测试未认证用户无法访问"""
        url = '/api/v1/documents/documents/'
        response = self.client.get(url)

        self.assertEqual(response.status_code, 401)


class DocumentVisibilityTest(TestCase):
    """测试单证三级可见性"""

    def setUp(self):
        self.client = APIClient()

        # 创建模板
        self.template = DocumentTemplate.objects.create(
            code='vis_test', name='可见性测试', content='<p></p>'
        )

        # 创建 admin 用户
        self.admin = User.objects.create_user(
            username='admin1', email='admin1@test.com',
            password='pass', user_type='admin', is_staff=True,
        )

        # 创建 teacher 用户 + 课程 + 班级
        self.teacher = User.objects.create_user(
            username='teacher1', email='teacher1@test.com',
            password='pass', user_type='teacher',
        )
        semester = Semester.objects.create(
            name='2026春', code='2026SP',
            start_date='2026-02-01', end_date='2026-06-30',
        )
        self.course = Course.objects.create(
            semester=semester, name='国际贸易实务', code='IR101',
        )
        self.course.teachers.add(self.teacher)
        self.tc = TeachingClass.objects.create(
            course=self.course, name='A班', enrollment_code='AAAA1111',
        )

        # 创建 student 用户并选课
        self.student = User.objects.create_user(
            username='student1', email='student1@test.com',
            password='pass', user_type='student',
        )
        StudentEnrollment.objects.create(
            teaching_class=self.tc, student=self.student,
        )

        # 创建另一个不在班级的学生
        self.other_student = User.objects.create_user(
            username='student2', email='student2@test.com',
            password='pass', user_type='student',
        )

        # 创建 3 份单证
        # student1 的课堂单证
        self.doc_in_class = Document.objects.create(
            template=self.template, created_by=self.student,
            teaching_class=self.tc, data='{}',
        )
        # student1 的无班级单证
        self.doc_no_class = Document.objects.create(
            template=self.template, created_by=self.student,
            data='{}',
        )
        # student2 的单证（不在班级里）
        self.doc_other = Document.objects.create(
            template=self.template, created_by=self.other_student,
            data='{}',
        )

    def test_admin_sees_all(self):
        """admin 可以看到所有单证"""
        self.client.force_authenticate(user=self.admin)
        resp = self.client.get('/api/v1/documents/documents/')
        ids = [d['id'] for d in resp.json()['data']]
        self.assertIn(self.doc_in_class.id, ids)
        self.assertIn(self.doc_no_class.id, ids)
        self.assertIn(self.doc_other.id, ids)

    def test_teacher_sees_class_docs_only(self):
        """teacher 只能看到自己班级的单证"""
        self.client.force_authenticate(user=self.teacher)
        resp = self.client.get('/api/v1/documents/documents/')
        ids = [d['id'] for d in resp.json()['data']]
        self.assertIn(self.doc_in_class.id, ids)
        self.assertNotIn(self.doc_no_class.id, ids)
        self.assertNotIn(self.doc_other.id, ids)

    def test_student_sees_own_docs_only(self):
        """student 只能看到自己的单证"""
        self.client.force_authenticate(user=self.student)
        resp = self.client.get('/api/v1/documents/documents/')
        ids = [d['id'] for d in resp.json()['data']]
        self.assertIn(self.doc_in_class.id, ids)
        self.assertIn(self.doc_no_class.id, ids)
        self.assertNotIn(self.doc_other.id, ids)

    def test_filter_by_transaction_id(self):
        """所有角色都可以用 transaction_id 过滤"""
        self.client.force_authenticate(user=self.admin)
        resp = self.client.get('/api/v1/documents/documents/?transaction_id=99999')
        self.assertEqual(len(resp.json()['data']), 0)

    def test_filter_by_teaching_class_id(self):
        """teacher 可以按班级 ID 过滤"""
        self.client.force_authenticate(user=self.teacher)
        resp = self.client.get(f'/api/v1/documents/documents/?teaching_class_id={self.tc.id}')
        ids = [d['id'] for d in resp.json()['data']]
        self.assertIn(self.doc_in_class.id, ids)
        self.assertEqual(len(ids), 1)
