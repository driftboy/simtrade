import pytest
import random
from datetime import date
from decimal import Decimal
from apps.users.models import User
from apps.teaching.models import (
    Semester, Course, TeachingClass, StudentEnrollment, Assignment,
)
from apps.scoring.models import Experiment, ScoreSheet
from apps.roles.models import Company, TradeRole, UserCompanyRole
from apps.teaching.services import (
    GradeReportService, AssignmentService,
)


def _setup_class_with_data():
    semester = Semester.objects.create(
        name='学期', code=f'RPT-SEM-{random.randint(10000,99999)}',
        start_date=date(2026, 2, 1), end_date=date(2026, 6, 30),
    )
    course = Course.objects.create(
        semester=semester, name='报告课',
        code=f'RPT-C-{random.randint(10000,99999)}',
    )
    cls = TeachingClass.objects.create(course=course, name='报告班')
    students = []
    for i in range(3):
        s = User.objects.create_user(
            username=f'rptstu{i}_{random.randint(1000,9999)}',
            password='pass', user_type='student',
            email=f'rptstu{i}_{random.randint(1000,9999)}@test.com',
        )
        StudentEnrollment.objects.create(teaching_class=cls, student=s)
        students.append(s)
    teacher = User.objects.create_user(
        username=f'rpttchr_{random.randint(1000,9999)}',
        password='pass', user_type='teacher',
        email=f'rpttchr_{random.randint(1000,9999)}@test.com',
    )
    return cls, students, teacher


@pytest.mark.django_db
def test_student_report():
    cls, students, teacher = _setup_class_with_data()
    student = students[0]

    experiment = Experiment.objects.create(
        name='测试实验', start_date='2026-03-01 00:00:00',
        teaching_class=cls,
    )
    company = Company.objects.create(
        name=f'报告公司_{random.randint(1000,9999)}',
        code=f'RPTCO{random.randint(1000,9999)}',
    )
    trade_role = TradeRole.objects.create(
        code='exporter', name='出口商', sort_order=1,
    )
    ucr = UserCompanyRole.objects.create(
        user=student, company=company, role=trade_role, status='active',
    )
    ScoreSheet.objects.create(
        experiment=experiment, user=student, user_company_role=ucr,
        auto_score=Decimal('80.0'), status='finalized',
    )

    assignment = Assignment.objects.create(
        teaching_class=cls, title='作业',
        max_score=100, due_date='2026-04-01T23:59:59Z',
    )
    AssignmentService.submit(assignment_id=assignment.id, student=student, content='答')
    AssignmentService.grade(
        submission_id=assignment.submissions.first().id,
        teacher=teacher, score=90.0,
    )

    report = GradeReportService.get_student_report(student, cls.id)
    assert 'experiment_score' in report
    assert 'assignment_score' in report
    assert 'total_score' in report
    assert report['experiment_score'] == 80.0
    assert report['assignment_score'] == 90.0


@pytest.mark.django_db
def test_class_report():
    cls, students, teacher = _setup_class_with_data()

    assignment = Assignment.objects.create(
        teaching_class=cls, title='作业',
        max_score=100, due_date='2026-04-01T23:59:59Z',
    )
    for i, student in enumerate(students):
        AssignmentService.submit(
            assignment_id=assignment.id, student=student, content=f'答案{i}',
        )
        AssignmentService.grade(
            submission_id=assignment.submissions.first().id,
            teacher=teacher, score=70.0 + i * 10,
        )

    report = GradeReportService.get_class_report(cls.id)
    assert 'avg_score' in report
    assert 'max_score' in report
    assert 'min_score' in report
    assert 'student_count' in report
    assert report['student_count'] == 3


@pytest.mark.django_db
def test_course_report():
    cls, students, teacher = _setup_class_with_data()
    report = GradeReportService.get_course_report(cls.course.id)
    assert 'class_reports' in report
    assert len(report['class_reports']) >= 1
