# apps/teaching/tests/test_import_service.py
import pytest
import tempfile
import os
from openpyxl import Workbook
from django.contrib.auth import get_user_model
from apps.teaching.models import Semester, Course, TeachingClass, StudentEnrollment, StudentProfile
from apps.teaching.services.import_service import ImportService

User = get_user_model()


@pytest.mark.django_db
class TestImportService:
    @pytest.fixture
    def setup_data(self, db):
        teacher = User.objects.create_user(username='teacher', user_type='teacher')
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
        return teaching_class

    def test_parse_excel_file(self, setup_data):
        """测试解析 Excel 文件"""
        wb = Workbook()
        ws = wb.active
        ws.title = "学生导入"
        ws.append(['学号', '姓名', '手机号', '邮箱', '行政班级', '年级', '初始角色'])
        ws.append(['2024001', '张三', '13800138001', 'zhangsan@example.com', '计算机1班', '2024级', 'student'])
        ws.append(['2024002', '李四', '13800138002', '', '计算机1班', '2024级', 'student'])

        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as f:
            wb.save(f.name)
            temp_path = f.name
        try:
            with open(temp_path, 'rb') as file:
                data = ImportService.parse_import_file(file)
        finally:
            os.unlink(temp_path)

        assert len(data) == 2
        assert data[0]['学号'] == '2024001'
        assert data[0]['姓名'] == '张三'

    def test_validate_import_data_success(self, setup_data):
        """测试数据验证成功"""
        data = [
            {'学号': '2024001', '姓名': '张三', '手机号': '13800138001'},
            {'学号': '2024002', '姓名': '李四', '手机号': '13800138002'},
        ]
        errors = ImportService.validate_import_data(data)
        assert len(errors) == 0

    def test_validate_import_data_missing_required(self, setup_data):
        """测试必填字段缺失"""
        data = [
            {'学号': '', '姓名': '张三'},
            {'学号': '2024002', '姓名': ''},
        ]
        errors = ImportService.validate_import_data(data)
        assert len(errors) == 2

    def test_check_capacity_success(self, setup_data):
        """测试容量检查成功"""
        available = ImportService.check_capacity(setup_data, 10)
        assert available == 40  # capacity is 40, 0 enrolled

    def test_check_capacity_exceeded(self, setup_data):
        """测试容量超出"""
        for i in range(35):
            student = User.objects.create_user(username=f's{i}', email=f's{i}@example.com', user_type='student')
            StudentEnrollment.objects.create(
                teaching_class=setup_data, student=student, status='enrolled',
            )

        with pytest.raises(ValueError) as exc_info:
            ImportService.check_capacity(setup_data, 10)
        assert '仅可再添加' in str(exc_info.value)

    def test_process_import_row_new_user(self, setup_data):
        """测试导入新用户"""
        row = {
            '学号': '2024001',
            '姓名': '张三',
            '手机号': '13800138001',
            '邮箱': 'zhangsan@example.com',
            '行政班级': '计算机1班',
            '年级': '2024级',
            '初始角色': 'student',
        }
        enrollment = ImportService.process_import_row(row, setup_data)

        assert enrollment is not None
        assert enrollment.student.username == '张三'
        assert enrollment.role == 'student'
        assert User.objects.filter(username='张三').exists()

    def test_process_import_row_existing_user(self, setup_data):
        """测试导入现有用户"""
        student = User.objects.create_user(
            username='张三', email='zhangsan@example.com', user_type='student',
        )
        StudentProfile.objects.create(user=student, student_id='2024001')

        row = {'学号': '2024001', '姓名': '张三', '初始角色': 'student'}
        enrollment = ImportService.process_import_row(row, setup_data)

        assert enrollment is not None
        assert enrollment.student == student

    def test_batch_import_summary(self, setup_data):
        """测试批量导入摘要"""
        wb = Workbook()
        ws = wb.active
        ws.append(['学号', '姓名'])
        ws.append(['2024001', '张三'])
        ws.append(['2024002', '李四'])

        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as f:
            wb.save(f.name)
            temp_path = f.name
        try:
            with open(temp_path, 'rb') as file:
                result = ImportService.batch_import(file, setup_data)
        finally:
            os.unlink(temp_path)

        assert result['success'] is True
        assert result['summary']['total'] == 2
        assert result['summary']['created'] == 2
        assert result['summary']['failed'] == 0
