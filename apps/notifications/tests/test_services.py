import pytest
from django.contrib.auth import get_user_model
from apps.notifications.models import Notification
from apps.notifications.services import NotificationService

User = get_user_model()


@pytest.mark.django_db
def test_create_and_get_notifications():
    user = User.objects.create_user(username='s1', password='testpass', email='s1@test.com')
    NotificationService.create_notification(
        user=user, notification_type='inquiry',
        title='收到询盘', content='测试询盘内容',
        related_transaction_id=1
    )
    NotificationService.create_notification(
        user=user, notification_type='offer',
        title='收到发盘', content='测试发盘内容'
    )
    notifications = NotificationService.get_notifications(user)
    assert len(notifications) == 2
    assert notifications[0].title == '收到发盘'  # 最新的在前


@pytest.mark.django_db
def test_get_notifications_filter_read():
    user = User.objects.create_user(username='s2', password='testpass', email='s2@test.com')
    NotificationService.create_notification(user=user, notification_type='inquiry', title='未读', content='c')
    NotificationService.create_notification(user=user, notification_type='offer', title='已读', content='c')
    n = Notification.objects.get(title='已读')
    n.is_read = True
    n.save()

    unread = NotificationService.get_notifications(user, is_read=False)
    assert len(unread) == 1
    assert unread[0].title == '未读'


@pytest.mark.django_db
def test_mark_as_read():
    user = User.objects.create_user(username='s3', password='testpass', email='s3@test.com')
    notification = NotificationService.create_notification(
        user=user, notification_type='inquiry', title='测试', content='c'
    )
    assert notification.is_read is False

    result = NotificationService.mark_as_read(notification.id, user)
    assert result.is_read is True


@pytest.mark.django_db
def test_mark_all_read():
    user = User.objects.create_user(username='s4', password='testpass', email='s4@test.com')
    NotificationService.create_notification(user=user, notification_type='inquiry', title='n1', content='c')
    NotificationService.create_notification(user=user, notification_type='offer', title='n2', content='c')

    NotificationService.mark_all_read(user)
    unread = NotificationService.get_notifications(user, is_read=False)
    assert len(unread) == 0


@pytest.mark.django_db
def test_get_unread_count():
    user = User.objects.create_user(username='s5', password='testpass', email='s5@test.com')
    NotificationService.create_notification(user=user, notification_type='inquiry', title='n1', content='c')
    NotificationService.create_notification(user=user, notification_type='offer', title='n2', content='c')
    NotificationService.create_notification(user=user, notification_type='system', title='n3', content='c')

    assert NotificationService.get_unread_count(user) == 3
    NotificationService.mark_as_read(
        Notification.objects.get(title='n1').id, user
    )
    assert NotificationService.get_unread_count(user) == 2


@pytest.mark.django_db
def test_mark_as_read_wrong_user():
    user1 = User.objects.create_user(username='s6', password='testpass', email='s6@test.com')
    user2 = User.objects.create_user(username='s7', password='testpass', email='s7@test.com')
    notification = NotificationService.create_notification(
        user=user1, notification_type='inquiry', title='私有', content='c'
    )
    with pytest.raises(ValueError):
        NotificationService.mark_as_read(notification.id, user2)
