from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync


class NotificationService:
    """通知服务"""

    @staticmethod
    def send_notification(user_ids, notification_type, data):
        """发送通知给指定用户列表

        Args:
            user_ids: 用户 ID 列表
            notification_type: 通知类型 (inquiry_received, offer_received, etc.)
            data: 通知数据
        """
        channel_layer = get_channel_layer()

        notification = {
            'type': 'notify',
            'data': {
                'type': notification_type,
                **data
            }
        }

        for user_id in user_ids:
            group_name = f'user_{user_id}'
            async_to_sync(channel_layer.group_send)(
                group_name,
                notification
            )

    @staticmethod
    def send_inquiry_notification(transaction, message):
        """发送询盘通知"""
        NotificationService.send_notification(
            [transaction.seller_id],
            'inquiry_received',
            {
                'transaction_id': transaction.id,
                'sender': transaction.buyer.username,
                'message': message.content[:50],
                'url': f'/transactions/{transaction.id}/'
            }
        )

    @staticmethod
    def send_offer_notification(transaction, message):
        """发送发盘通知"""
        NotificationService.send_notification(
            [transaction.buyer_id],
            'offer_received',
            {
                'transaction_id': transaction.id,
                'sender': transaction.seller.username,
                'offered_price': str(message.offered_price) if message.offered_price else None,
                'url': f'/transactions/{transaction.id}/'
            }
        )

    @staticmethod
    def send_counter_offer_notification(transaction, message):
        """发送还盘通知"""
        # 确定接收者
        receiver_id = transaction.seller_id if message.sender_role == 'buyer' else transaction.buyer_id
        NotificationService.send_notification(
            [receiver_id],
            'counter_offer_received',
            {
                'transaction_id': transaction.id,
                'sender': message.sender.username,
                'offered_price': str(message.offered_price) if message.offered_price else None,
                'url': f'/transactions/{transaction.id}/'
            }
        )

    @staticmethod
    def send_lc_created_notification(lc):
        """发送信用证创建通知"""
        NotificationService.send_notification(
            [lc.applicant_id],
            'lc_created',
            {
                'lc_id': lc.id,
                'lc_no': lc.lc_no,
                'amount': str(lc.amount),
                'currency': lc.currency,
                'url': f'/letters-of-credit/{lc.id}/'
            }
        )
