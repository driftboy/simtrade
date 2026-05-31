# apps/teaching/tests/test_student_profile.py
import pytest
from django.contrib.auth import get_user_model
from apps.teaching.models import StudentProfile

User = get_user_model()


@pytest.mark.django_db
class TestStudentProfile:
    def test_create_student_profile(self):
        """测试创建学生档案"""
        user = User.objects.create_user(
            username='test_student',
            email='test@example.com',
            user_type='student',
        )
        profile = StudentProfile.objects.create(
            user=user,
            student_id='2024001',
            admin_class='计算机1班',
            grade='2024级',
            phone='13800138000',
            enrollment_year=2024,
        )
        assert profile.student_id == '2024001'
        assert profile.admin_class == '计算机1班'
        assert profile.grade == '2024级'

    def test_student_id_unique(self):
        """测试学号唯一性"""
        user1 = User.objects.create_user(username='s1', email='s1@example.com', user_type='student')
        user2 = User.objects.create_user(username='s2', email='s2@example.com', user_type='student')
        StudentProfile.objects.create(user=user1, student_id='2024001')

        with pytest.raises(Exception):  # IntegrityError
            StudentProfile.objects.create(user=user2, student_id='2024001')

    def test_one_to_one_relation(self):
        """测试一对一关系"""
        user = User.objects.create_user(username='test', user_type='student')
        profile = StudentProfile.objects.create(user=user, student_id='2024001')
        assert user.student_profile == profile
