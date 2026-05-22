import json
from channels.generic.websocket import AsyncWebsocketConsumer


class NotificationConsumer(AsyncWebsocketConsumer):
    """通知 WebSocket 消费者"""

    async def connect(self):
        """建立连接"""
        if self.scope["user"].is_anonymous:
            await self.close()
        else:
            self.user_group_name = f'user_{self.scope["user"].id}'
            await self.channel_layer.group_add(
                self.user_group_name,
                self.channel_name
            )
            await self.accept()

    async def disconnect(self, close_code):
        """断开连接"""
        await self.channel_layer.group_discard(
            self.user_group_name,
            self.channel_name
        )

    async def notify(self, event):
        """接收并发送通知"""
        await self.send(text_data=json.dumps(event['data']))

    async def receive(self, text_data):
        """接收客户端消息（可用于心跳检测）"""
        data = json.loads(text_data)
        if data.get('type') == 'ping':
            await self.send(text_data=json.dumps({'type': 'pong'}))
