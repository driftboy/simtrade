# apps/teaching/tests/test_class_management_api.py
import pytest
import tempfile
import os
from openpyxl import Workbook
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from apps.teaching.models import Semester, Course, TeachingClass, StudentEnrollment, StudentProfile

User = get_user_model()


@pytest.mark.django_db
class TestClassManagementAPI:
    @pytest.fixture
    def api_client(self):
        return APIClient()

    @pytest.fixture
    def setup_data(self, db):
        teacher = User.objects.create_user(username='teacher', email='teacher@example.com', user_type='teacher')
        other_teacher = User.objects.create_user(username='other_teacher', email='other@example.com', user_type='teacher')
        student = User.objects.create_user(
            username='student', email='student@example.com', user_type='student',
        )
        StudentProfile.objects.create(user=student, student_id='2024001')

        semester = Semester.objects.create(
            name='2024春', code='2024SP',
            start_date='2024-03-01', end_date='2024-07-01',
            created_by=teacher,
        )
        course = Course.objects.create(
            semester=semester, name='国际贸易', code='TRADE101',
            created_by=teacher,
        )
        course.teachers.add(teacher)
        teaching_class = TeachingClass.objects.create(
            course=course, name='1班', capacity=40,
            created_by=teacher,
        )

        return {
            'teacher': teacher,
            'other_teacher': other_teacher,
            'student': student,
            'teaching_class': teaching_class,
        }

    def test_get_class_students(self, api_client, setup_data):
        """测试获取班级学生列表"""
        api_client.force_authenticate(user=setup_data['teacher'])

        StudentEnrollment.objects.create(
            teaching_class=setup_data['teaching_class'],
            student=setup_data['student'],
            role='student',
        )

        url = f'/api/v1/teaching/classes/{setup_data["teaching_class"].id}/students/'
        response = api_client.get(url)

        assert response.status_code == 200
        data = response.json()
        assert data['code'] == 0
        assert len(data['data']) == 1
        assert data['data'][0]['student_id'] == '2024001'

    def test_add_student_existing(self, api_client, setup_data):
        """测试添加现有学生"""
        api_client.force_authenticate(user=setup_data['teacher'])

        url = f'/api/v1/teaching/classes/{setup_data["teaching_class"].id}/students/'
        response = api_client.post(url, {'student_id': '2024001'})

        assert response.status_code == 200
        assert StudentEnrollment.objects.filter(
            teaching_class=setup_data['teaching_class'],
            student=setup_data['student'],
        ).exists()

    def test_add_student_new(self, api_client, setup_data):
        """测试创建新学生"""
        api_client.force_authenticate(user=setup_data['teacher'])

        url = f'/api/v1/teaching/classes/{setup_data["teaching_class"].id}/students/'
        data = {
            'student_id_new': '2024002',
            'username': '新学生',
            'name': '新学生',
        }
        response = api_client.post(url, data)

        assert response.status_code == 200
        assert User.objects.filter(username='新学生').exists()

    def test_remove_student(self, api_client, setup_data):
        """测试移除学生（软删除）"""
        api_client.force_authenticate(user=setup_data['teacher'])

        enrollment = StudentEnrollment.objects.create(
            teaching_class=setup_data['teaching_class'],
            student=setup_data['student'],
            role='student',
        )

        url = f'/api/v1/teaching/classes/{setup_data["teaching_class"].id}/students/{setup_data["student"].id}/'
        response = api_client.delete(url)

        assert response.status_code == 200
        enrollment.refresh_from_db()
        assert enrollment.status == 'dropped'

    def test_update_student_role(self, api_client, setup_data):
        """测试修改学生角色"""
        api_client.force_authenticate(user=setup_data['teacher'])

        enrollment = StudentEnrollment.objects.create(
            teaching_class=setup_data['teaching_class'],
            student=setup_data['student'],
            role='student',
        )

        url = f'/api/v1/teaching/classes/{setup_data["teaching_class"].id}/student-role/'
        response = api_client.patch(url, {'enrollment_id': enrollment.id, 'role': 'assistant'})

        assert response.status_code == 200
        enrollment.refresh_from_db()
        assert enrollment.role == 'assistant'

    def test_batch_update_roles(self, api_client, setup_data):
        """测试批量修改角色"""
        api_client.force_authenticate(user=setup_data['teacher'])

        s1 = User.objects.create_user(username='s1', email='s1@example.com', user_type='student')
        StudentProfile.objects.create(user=s1, student_id='2024002')
        s2 = User.objects.create_user(username='s2', email='s2@example.com', user_type='student')
        StudentProfile.objects.create(user=s2, student_id='2024003')

        e1 = StudentEnrollment.objects.create(
            teaching_class=setup_data['teaching_class'], student=s1, role='student',
        )
        e2 = StudentEnrollment.objects.create(
            teaching_class=setup_data['teaching_class'], student=s2, role='student',
        )

        url = f'/api/v1/teaching/classes/{setup_data["teaching_class"].id}/students/batch/'
        response = api_client.patch(url, {'student_ids': [e1.id, e2.id], 'role': 'monitor'})

        assert response.status_code == 200
        e1.refresh_from_db()
        e2.refresh_from_db()
        assert e1.role == 'monitor'
        assert e2.role == 'monitor'

    def test_batch_import(self, api_client, setup_data):
        """测试批量导入"""
        api_client.force_authenticate(user=setup_data['teacher'])

        wb = Workbook()
        ws = wb.active
        ws.append(['学号', '姓名'])
        ws.append(['2024005', '王五'])
        ws.append(['2024006', '赵六'])

        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as f:
            wb.save(f.name)
            temp_path = f.name
        try:
            with open(temp_path, 'rb') as file:
                from django.core.files.uploadedfile import SimpleUploadedFile
                uploaded_file = SimpleUploadedFile(
                    'test.xlsx', file.read(),
                    content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                )
                url = f'/api/v1/teaching/classes/{setup_data["teaching_class"].id}/import/'
                response = api_client.post(url, {'file': uploaded_file})
        finally:
            os.unlink(temp_path)

        assert response.status_code == 200
        result = response.json()['data']
        assert result['success'] is True
        assert result['summary']['created'] == 2

    def test_permission_denied(self, api_client, setup_data):
        """测试非任课教师权限被拒绝"""
        api_client.force_authenticate(user=setup_data['other_teacher'])

        url = f'/api/v1/teaching/classes/{setup_data["teaching_class"].id}/students/'
        response = api_client.get(url)

        assert response.status_code == 403

    def test_capacity_exceeded(self, api_client, setup_data):
        """测试容量超出"""
        # 创建容量为 2 的班级
        small_class = TeachingClass.objects.create(
            course=setup_data['teaching_class'].course,
            name='小班',
            capacity=2,
            created_by=setup_data['teacher'],
        )

        api_client.force_authenticate(user=setup_data['teacher'])

        # 添加 2 个学生
        for i in range(2):
            s = User.objects.create_user(username=f's{i}', email=f's{i}@example.com', user_type='student')
            StudentProfile.objects.create(user=s, student_id=f'20240{i}')
            StudentEnrollment.objects.create(
                teaching_class=small_class, student=s, status='enrolled',
            )

        # 尝试导入第 3 个
        wb = Workbook()
        ws = wb.active
        ws.append(['学号', '姓名'])
        ws.append(['2024005', '王五'])

        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as f:
            wb.save(f.name)
            temp_path = f.name
        try:
            with open(temp_path, 'rb') as file:
                from django.core.files.uploadedfile import SimpleUploadedFile
                uploaded_file = SimpleUploadedFile(
                    'test.xlsx', file.read(),
                    content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                )
                url = f'/api/v1/teaching/classes/{small_class.id}/import/'
                response = api_client.post(url, {'file': uploaded_file})
        finally:
            os.unlink(temp_path)

        assert response.status_code == 400
        assert '超出班级容量' in response.json()['message']
