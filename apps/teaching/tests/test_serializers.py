# apps/teaching/tests/test_serializers.py
import pytest
from apps.teaching.serializers import (
    StudentListSerializer, AddStudentSerializer,
    UpdateRoleSerializer, BatchUpdateRoleSerializer,
)


@pytest.mark.django_db
class TestClassManagementSerializers:
    def test_add_student_serializer_with_student_id(self):
        """测试添加学生序列化器（提供学号）"""
        serializer = AddStudentSerializer(data={'student_id': '2024001'})
        assert serializer.is_valid()

    def test_add_student_serializer_with_new_student(self):
        """测试添加学生序列化器（创建新学生）"""
        data = {
            'username': 'new_student',
            'student_id_new': '2024002',
            'name': '张三',
            'phone': '13800138000',
        }
        serializer = AddStudentSerializer(data=data)
        assert serializer.is_valid()

    def test_add_student_serializer_invalid(self):
        """测试添加学生序列化器（无效数据）"""
        serializer = AddStudentSerializer(data={})
        assert not serializer.is_valid()

    def test_update_role_serializer(self):
        """测试修改角色序列化器"""
        serializer = UpdateRoleSerializer(data={'role': 'assistant'})
        assert serializer.is_valid()

    def test_update_role_serializer_invalid_role(self):
        """测试修改角色序列化器（无效角色）"""
        serializer = UpdateRoleSerializer(data={'role': 'invalid'})
        assert not serializer.is_valid()

    def test_batch_update_role_serializer(self):
        """测试批量修改角色序列化器"""
        data = {'student_ids': [1, 2, 3], 'role': 'monitor'}
        serializer = BatchUpdateRoleSerializer(data=data)
        assert serializer.is_valid()
