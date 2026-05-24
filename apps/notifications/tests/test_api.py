import pytest
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from apps.notifications.models import Notification
from apps.notifications.services import NotificationService

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.mark.django_db
def test_list_notifications(api_client):
    user = User.objects.create_user(username='u1', email='u1@test.com', password='testpass')
    NotificationService.create_notification(user=user, notification_type='inquiry', title='测试1', content='c')
    NotificationService.create_notification(user=user, notification_type='offer', title='测试2', content='c')
    api_client.force_authenticate(user=user)

    response = api_client.get('/api/v1/notifications/')

    assert response.status_code == 200
    assert response.data['code'] == 0
    assert len(response.data['data']) == 2


@pytest.mark.django_db
def test_list_notifications_filter_unread(api_client):
    user = User.objects.create_user(username='u2', email='u2@test.com', password='testpass')
    NotificationService.create_notification(user=user, notification_type='inquiry', title='未读', content='c')
    n = NotificationService.create_notification(user=user, notification_type='offer', title='已读', content='c')
    NotificationService.mark_as_read(n.id, user)
    api_client.force_authenticate(user=user)

    response = api_client.get('/api/v1/notifications/', {'is_read': 'false'})

    assert response.status_code == 200
    assert len(response.data['data']) == 1
    assert response.data['data'][0]['title'] == '未读'


@pytest.mark.django_db
def test_mark_as_read(api_client):
    user = User.objects.create_user(username='u3', email='u3@test.com', password='testpass')
    notification = NotificationService.create_notification(
        user=user, notification_type='inquiry', title='测试', content='c'
    )
    api_client.force_authenticate(user=user)

    response = api_client.post(f'/api/v1/notifications/{notification.id}/read/')

    assert response.status_code == 200
    assert response.data['code'] == 0
    notification.refresh_from_db()
    assert notification.is_read is True


@pytest.mark.django_db
def test_mark_all_read(api_client):
    user = User.objects.create_user(username='u4', email='u4@test.com', password='testpass')
    NotificationService.create_notification(user=user, notification_type='inquiry', title='n1', content='c')
    NotificationService.create_notification(user=user, notification_type='offer', title='n2', content='c')
    api_client.force_authenticate(user=user)

    response = api_client.post('/api/v1/notifications/read-all/')

    assert response.status_code == 200
    assert NotificationService.get_unread_count(user) == 0


@pytest.mark.django_db
def test_delete_notification(api_client):
    user = User.objects.create_user(username='u5', email='u5@test.com', password='testpass')
    notification = NotificationService.create_notification(
        user=user, notification_type='inquiry', title='待删除', content='c'
    )
    api_client.force_authenticate(user=user)

    response = api_client.delete(f'/api/v1/notifications/{notification.id}/')

    assert response.status_code == 200
    assert not Notification.objects.filter(id=notification.id).exists()


@pytest.mark.django_db
def test_unread_count(api_client):
    user = User.objects.create_user(username='u6', email='u6@test.com', password='testpass')
    NotificationService.create_notification(user=user, notification_type='inquiry', title='n1', content='c')
    NotificationService.create_notification(user=user, notification_type='offer', title='n2', content='c')
    api_client.force_authenticate(user=user)

    response = api_client.get('/api/v1/notifications/unread-count/')

    assert response.status_code == 200
    assert response.data['data']['count'] == 2


@pytest.mark.django_db
def test_delete_other_user_notification_forbidden(api_client):
    user1 = User.objects.create_user(username='u7', email='u7@test.com', password='testpass')
    user2 = User.objects.create_user(username='u8', email='u8@test.com', password='testpass')
    notification = NotificationService.create_notification(
        user=user1, notification_type='inquiry', title='私有', content='c'
    )
    api_client.force_authenticate(user=user2)

    response = api_client.delete(f'/api/v1/notifications/{notification.id}/')

    assert response.status_code == status.HTTP_403_FORBIDDEN
