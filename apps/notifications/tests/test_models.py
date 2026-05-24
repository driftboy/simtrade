import time
import pytest
from django.contrib.auth import get_user_model
from apps.notifications.models import Notification

User = get_user_model()


@pytest.mark.django_db
def test_create_notification():
    user = User.objects.create_user(username='testuser', password='testpass')
    notification = Notification.objects.create(
        user=user,
        type=Notification.Type.INQUIRY,
        title='收到询盘',
        content='公司A向您发送了询盘'
    )
    assert notification.user == user
    assert notification.type == 'inquiry'
    assert notification.is_read is False
    assert str(notification) == '收到询盘'


@pytest.mark.django_db
def test_notification_ordering():
    user = User.objects.create_user(username='testuser2', password='testpass')
    n1 = Notification.objects.create(user=user, type='inquiry', title='通知1', content='内容1')
    time.sleep(0.01)  # ensure distinct timestamps for ordering test
    n2 = Notification.objects.create(user=user, type='offer', title='通知2', content='内容2')
    notifications = list(Notification.objects.filter(user=user))
    assert notifications[0].id == n2.id  # 最新的在前


@pytest.mark.django_db
def test_notification_with_transaction_id():
    user = User.objects.create_user(username='testuser3', password='testpass')
    notification = Notification.objects.create(
        user=user,
        type=Notification.Type.LC_CREATED,
        title='信用证创建',
        content='信用证已创建',
        related_transaction_id=42
    )
    assert notification.related_transaction_id == 42
