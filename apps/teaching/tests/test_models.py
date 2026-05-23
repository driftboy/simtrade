import pytest
import random
from datetime import date
from django.core.exceptions import ValidationError
from apps.teaching.models import (
    Semester, Course, TeachingClass, StudentEnrollment,
    ExperimentTemplate, ExperimentGroup,
)
from apps.users.models import User


@pytest.mark.django_db
def test_create_semester():
    semester = Semester.objects.create(
        name='2026 春季学期', code='2026-SPRING',
        start_date=date(2026, 2, 20), end_date=date(2026, 6, 30),
    )
    assert semester.name == '2026 春季学期'
    assert semester.code == '2026-SPRING'
    assert semester.status == 'upcoming'
    assert semester.is_active is False
    assert str(semester) == '2026 春季学期'


@pytest.mark.django_db
def test_semester_code_unique():
    Semester.objects.create(
        name='学期1', code='UNIQUE01',
        start_date=date(2026, 2, 1), end_date=date(2026, 6, 30),
    )
    with pytest.raises(Exception):
        Semester.objects.create(
            name='学期2', code='UNIQUE01',
            start_date=date(2026, 7, 1), end_date=date(2027, 1, 15),
        )


@pytest.mark.django_db
def test_semester_date_validation():
    semester = Semester(
        name='错误学期', code='BAD-DATES',
        start_date=date(2026, 7, 1), end_date=date(2026, 6, 30),
    )
    with pytest.raises(ValidationError):
        semester.clean()


@pytest.mark.django_db
def test_semester_active_uniqueness():
    Semester.objects.create(
        name='活跃学期', code='ACTIVE01',
        start_date=date(2026, 2, 1), end_date=date(2026, 6, 30),
        is_active=True,
    )
    semester2 = Semester(
        name='冲突学期', code='ACTIVE02',
        start_date=date(2026, 7, 1), end_date=date(2027, 1, 15),
        is_active=True,
    )
    with pytest.raises(ValidationError):
        semester2.clean()


@pytest.mark.django_db
def test_create_course():
    semester = Semester.objects.create(
        name='2026 春', code='2026S',
        start_date=date(2026, 2, 1), end_date=date(2026, 6, 30),
    )
    course = Course.objects.create(
        semester=semester, name='国际贸易实务', code='INTL-301',
        description='外贸模拟课程',
    )
    assert course.name == '国际贸易实务'
    assert course.status == 'upcoming'
    assert str(course) == '2026 春 - 国际贸易实务'


@pytest.mark.django_db
def test_course_code_unique_per_semester():
    semester = Semester.objects.create(
        name='学期', code='SEM01',
        start_date=date(2026, 2, 1), end_date=date(2026, 6, 30),
    )
    Course.objects.create(semester=semester, name='课1', code='C01')
    with pytest.raises(Exception):
        Course.objects.create(semester=semester, name='课2', code='C01')


@pytest.mark.django_db
def test_course_weight_validation():
    semester = Semester.objects.create(
        name='学期', code='SEM02',
        start_date=date(2026, 2, 1), end_date=date(2026, 6, 30),
    )
    course = Course(
        semester=semester, name='权重课', code='W01',
        experiment_weight=0.50, assignment_weight=0.60,
    )
    with pytest.raises(ValidationError):
        course.clean()


@pytest.mark.django_db
def test_create_teaching_class():
    semester = Semester.objects.create(
        name='学期', code='TSEM01',
        start_date=date(2026, 2, 1), end_date=date(2026, 6, 30),
    )
    course = Course.objects.create(semester=semester, name='课', code='TC01')
    cls = TeachingClass.objects.create(course=course, name='3 班', capacity=30)
    assert cls.name == '3 班'
    assert cls.enrollment_code
    assert len(cls.enrollment_code) == 8
    assert str(cls) == '学期 - 课 - 3 班'


@pytest.mark.django_db
def test_enrollment_code_unique():
    semester = Semester.objects.create(
        name='学期', code='TSEM02',
        start_date=date(2026, 2, 1), end_date=date(2026, 6, 30),
    )
    course = Course.objects.create(semester=semester, name='课', code='TC02')
    cls1 = TeachingClass.objects.create(course=course, name='班1')
    cls2 = TeachingClass.objects.create(course=course, name='班2')
    assert cls1.enrollment_code != cls2.enrollment_code


def _make_class():
    semester = Semester.objects.create(
        name='学期', code=f'SEM-{random.randint(10000,99999)}',
        start_date=date(2026, 2, 1), end_date=date(2026, 6, 30),
    )
    course = Course.objects.create(
        semester=semester, name='课', code=f'C-{random.randint(10000,99999)}',
    )
    return TeachingClass.objects.create(course=course, name='班')


@pytest.mark.django_db
def test_create_enrollment():
    student = User.objects.create_user(username='stu1', password='pass')
    cls = _make_class()
    enrollment = StudentEnrollment.objects.create(
        teaching_class=cls, student=student,
    )
    assert enrollment.status == 'enrolled'
    assert enrollment.role == 'student'
    assert str(enrollment) == f'stu1 - {cls.name}'


@pytest.mark.django_db
def test_enrollment_unique():
    student = User.objects.create_user(username='stu2', password='pass')
    cls = _make_class()
    StudentEnrollment.objects.create(teaching_class=cls, student=student)
    with pytest.raises(Exception):
        StudentEnrollment.objects.create(teaching_class=cls, student=student)


@pytest.mark.django_db
def test_create_experiment_template():
    user = User.objects.create_user(
        username='tpl_creator', password='pass',
        email='tpl@test.com',
    )
    tpl = ExperimentTemplate.objects.create(
        name='CIF 出口完整流程',
        description='模拟 CIF 术语下的完整出口贸易流程',
        config={'roles_per_group': 5, 'trade_term': 'CIF'},
        is_public=True, created_by=user,
    )
    assert tpl.name == 'CIF 出口完整流程'
    assert tpl.use_count == 0
    assert str(tpl) == 'CIF 出口完整流程'


@pytest.mark.django_db
def test_create_experiment_group():
    from apps.roles.models import Company
    from apps.scoring.models import Experiment
    company = Company.objects.create(name='实验组公司', code='EXP-GRP01')
    experiment = Experiment.objects.create(
        name='测试实验', start_date='2026-03-01 00:00:00',
    )
    group = ExperimentGroup.objects.create(
        experiment=experiment, company=company, group_name='A 组',
    )
    assert group.group_name == 'A 组'
