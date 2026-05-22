from django.urls import re_path
from apps.notifications.consumers import NotificationConsumer

# WebSocket URL patterns
websocket_urlpatterns = [
    re_path(r'^ws/notifications/$', NotificationConsumer.as_asgi()),
]
