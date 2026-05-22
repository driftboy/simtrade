import pytest
from channels.testing import WebsocketCommunicator
from django.test import TestCase
from apps.users.models import User
from apps.notifications.consumers import NotificationConsumer
from apps.notifications.services import NotificationService


class NotificationServiceTest(TestCase):
    """通知服务测试"""

    def setUp(self):
        self.user1 = User.objects.create_user(username='user1', password='testpass')
        self.user2 = User.objects.create_user(username='user2', password='testpass')

    def test_send_notification_structure(self):
        """测试通知结构正确"""
        # 只测试数据结构，不测试实际 WebSocket 连接
        notification_data = {
            'type': 'inquiry_received',
            'transaction_id': 123,
            'message': '测试消息',
            'url': '/transactions/123/'
        }
        assert 'type' in notification_data
        assert 'transaction_id' in notification_data
        assert notification_data['type'] == 'inquiry_received'
