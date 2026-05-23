import pytest
from datetime import date
from apps.users.models import User
from apps.teaching.models import Semester, Course, TeachingClass, StudentEnrollment
from apps.teaching.services import (
    SemesterService, CourseService, TeachingClassService,
)


@pytest.fixture
def teacher():
    return User.objects.create_user(
        username='teacher1', password='pass',
        email='teacher1@svc.test', user_type='teacher',
    )


@pytest.fixture
def student():
    return User.objects.create_user(
        username='student1', password='pass',
        email='student1@svc.test', user_type='student',
    )


@pytest.fixture
def semester():
    return Semester.objects.create(
        name='2026 春', code='SVC-SEM01',
        start_date=date(2026, 2, 1), end_date=date(2026, 6, 30),
    )


@pytest.fixture
def course(semester, teacher):
    course = Course.objects.create(
        semester=semester, name='国际贸易', code='SVC-C01',
    )
    course.teachers.add(teacher)
    return course


# === SemesterService ===

@pytest.mark.django_db
def test_activate_semester(semester):
    result = SemesterService.activate_semester(semester.id)
    assert result.is_active is True
    semester.refresh_from_db()
    assert semester.is_active is True


@pytest.mark.django_db
def test_activate_semester_deactivates_others(semester):
    other = Semester.objects.create(
        name='其他学期', code='SVC-SEM02',
        start_date=date(2025, 9, 1), end_date=date(2026, 1, 15),
        is_active=True,
    )
    SemesterService.activate_semester(semester.id)
    other.refresh_from_db()
    assert other.is_active is False


@pytest.mark.django_db
def test_get_active_semester(semester):
    SemesterService.activate_semester(semester.id)
    result = SemesterService.get_active_semester()
    assert result == semester


@pytest.mark.django_db
def test_get_active_semester_none():
    result = SemesterService.get_active_semester()
    assert result is None


# === CourseService ===

@pytest.mark.django_db
def test_create_course(semester, teacher):
    course = CourseService.create_course(
        user=teacher, semester_id=semester.id,
        name='新课程', code='NEW-C01',
        teacher_ids=[teacher.id],
    )
    assert course.name == '新课程'
    assert course.teachers.filter(id=teacher.id).exists()


@pytest.mark.django_db
def test_get_teacher_courses(teacher, course):
    courses = CourseService.get_teacher_courses(teacher)
    assert course in courses


# === TeachingClassService ===

@pytest.mark.django_db
def test_create_class(course, teacher):
    cls = TeachingClassService.create_class(
        user=teacher, course_id=course.id,
        name='1 班', capacity=35,
    )
    assert cls.course == course
    assert cls.enrollment_code
    assert cls.capacity == 35


@pytest.mark.django_db
def test_enroll_student(course, student):
    cls = TeachingClassService.create_class(
        user=course.teachers.first(),
        course_id=course.id, name='班',
    )
    enrollment = TeachingClassService.enroll_student(
        teaching_class_id=cls.id,
        student=student,
        enrollment_code=cls.enrollment_code,
    )
    assert enrollment.status == 'enrolled'
    assert enrollment.student == student


@pytest.mark.django_db
def test_enroll_wrong_code(course, student):
    cls = TeachingClassService.create_class(
        user=course.teachers.first(),
        course_id=course.id, name='班',
    )
    with pytest.raises(ValueError):
        TeachingClassService.enroll_student(
            teaching_class_id=cls.id,
            student=student,
            enrollment_code='WRONG',
        )


@pytest.mark.django_db
def test_drop_student(course, student):
    cls = TeachingClassService.create_class(
        user=course.teachers.first(),
        course_id=course.id, name='班',
    )
    enrollment = TeachingClassService.enroll_student(
        teaching_class_id=cls.id,
        student=student,
        enrollment_code=cls.enrollment_code,
    )
    TeachingClassService.drop_student(enrollment.id, student)
    enrollment.refresh_from_db()
    assert enrollment.status == 'dropped'
    assert enrollment.dropped_at is not None


@pytest.mark.django_db
def test_enroll_class_full(course, student):
    cls = TeachingClassService.create_class(
        user=course.teachers.first(),
        course_id=course.id, name='满班', capacity=1,
    )
    stu1 = User.objects.create_user(
        username='fullstu1', password='pass',
        email='fullstu1@svc.test',
    )
    TeachingClassService.enroll_student(
        teaching_class_id=cls.id, student=stu1,
        enrollment_code=cls.enrollment_code,
    )
    with pytest.raises(ValueError, match='班级已满'):
        TeachingClassService.enroll_student(
            teaching_class_id=cls.id, student=student,
            enrollment_code=cls.enrollment_code,
        )


@pytest.mark.django_db
def test_enroll_already_enrolled(course, student):
    cls = TeachingClassService.create_class(
        user=course.teachers.first(),
        course_id=course.id, name='班',
    )
    TeachingClassService.enroll_student(
        teaching_class_id=cls.id, student=student,
        enrollment_code=cls.enrollment_code,
    )
    with pytest.raises(ValueError, match='已经选过'):
        TeachingClassService.enroll_student(
            teaching_class_id=cls.id, student=student,
            enrollment_code=cls.enrollment_code,
        )
