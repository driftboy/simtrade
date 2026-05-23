import pytest
import random
from datetime import date
from django.core.exceptions import ValidationError
from apps.teaching.models import Semester
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
