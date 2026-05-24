import pytest
from datetime import date
from rest_framework.test import APIClient
from apps.users.models import User
from apps.teaching.models import Semester, Course, TeachingClass


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def teacher():
    return User.objects.create_user(
        username='api_teacher', password='pass', user_type='teacher',
        email='api_teacher@test.com',
    )


@pytest.fixture
def student():
    return User.objects.create_user(
        username='api_student', password='pass', user_type='student',
        email='api_student@test.com',
    )


@pytest.fixture
def setup_data(teacher):
    semester = Semester.objects.create(
        name='API 学期', code='API-SEM',
        start_date=date(2026, 2, 1), end_date=date(2026, 6, 30),
    )
    course = Course.objects.create(
        semester=semester, name='API 课', code='API-C',
    )
    course.teachers.add(teacher)
    cls = TeachingClass.objects.create(
        course=course, name='API 班',
    )
    return {'semester': semester, 'course': course, 'class': cls}


@pytest.mark.django_db
def test_semester_crud(api_client, teacher):
    api_client.force_authenticate(user=teacher)
    # Create
    resp = api_client.post('/api/v1/teaching/semesters/', {
        'name': '新学期', 'code': 'API-NEW-SEM',
        'start_date': '2026-09-01', 'end_date': '2027-01-15',
    })
    assert resp.status_code == 201
    semester_id = resp.data['id']
    # List
    resp = api_client.get('/api/v1/teaching/semesters/')
    assert resp.status_code == 200
    # Activate
    resp = api_client.post(
        f'/api/v1/teaching/semesters/{semester_id}/activate/',
    )
    assert resp.status_code == 200


@pytest.mark.django_db
def test_student_enroll(api_client, student, setup_data):
    cls = setup_data['class']
    api_client.force_authenticate(user=student)
    resp = api_client.post(
        f'/api/v1/teaching/classes/{cls.id}/enroll/',
        {'enrollment_code': cls.enrollment_code},
    )
    assert resp.status_code == 200
    assert resp.data['code'] == 0


@pytest.mark.django_db
def test_student_enroll_wrong_code(api_client, student, setup_data):
    cls = setup_data['class']
    api_client.force_authenticate(user=student)
    resp = api_client.post(
        f'/api/v1/teaching/classes/{cls.id}/enroll/',
        {'enrollment_code': 'WRONG'},
    )
    assert resp.status_code == 400


@pytest.mark.django_db
def test_assignment_flow(api_client, teacher, student, setup_data):
    cls = setup_data['class']
    # Teacher creates assignment
    api_client.force_authenticate(user=teacher)
    resp = api_client.post('/api/v1/teaching/assignments/', {
        'teaching_class': cls.id,
        'title': 'API 测试作业',
        'max_score': 100,
        'due_date': '2026-04-01T23:59:59Z',
    })
    assert resp.status_code == 201
    assignment_id = resp.data['id']

    # Student submits
    api_client.force_authenticate(user=student)
    resp = api_client.post(
        f'/api/v1/teaching/assignments/{assignment_id}/submit/',
        {'content': '我的答案'},
    )
    assert resp.status_code == 200

    # Teacher grades
    submission_id = resp.data['data']['id']
    api_client.force_authenticate(user=teacher)
    resp = api_client.post(
        f'/api/v1/teaching/submissions/{submission_id}/grade/',
        {'score': 95.0, 'feedback': '很好'},
    )
    assert resp.status_code == 200
    assert resp.data['data']['score'] == '95.00'
