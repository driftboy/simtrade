from django.urls import re_path

# WebSocket URL patterns
# TODO: Uncomment when consumers are implemented
# from . import consumers

websocket_urlpatterns = [
    # re_path(r'ws/notifications/$', consumers.NotificationConsumer.as_asgi()),
]
