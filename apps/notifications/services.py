from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync


class NotificationService:
    """通知服务"""

    @staticmethod
    def get_company_member_ids(company):
        """获取公司的活跃成员用户 ID 列表"""
        if not company:
            return []
        # 获取公司所有活跃成员的用户 ID
        from apps.roles.models import UserCompanyRole
        return list(
            UserCompanyRole.objects.filter(
                company=company,
                is_active=True
            ).values_list('user_id', flat=True)
        )

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
        # 获取卖方公司的成员用户 ID 列表
        user_ids = NotificationService.get_company_member_ids(transaction.seller)
        # transaction.buyer 现在是 Company 对象，需要获取公司名称
        NotificationService.send_notification(
            user_ids,
            'inquiry_received',
            {
                'transaction_id': transaction.id,
                'sender': transaction.buyer.name if hasattr(transaction.buyer, 'name') else str(transaction.buyer),
                'message': message.content[:50],
                'url': f'/transactions/{transaction.id}/'
            }
        )

    @staticmethod
    def send_offer_notification(transaction, message):
        """发送发盘通知"""
        # 获取买方公司的成员用户 ID 列表
        user_ids = NotificationService.get_company_member_ids(transaction.buyer)
        # transaction.seller 现在是 Company 对象，需要获取公司名称
        NotificationService.send_notification(
            user_ids,
            'offer_received',
            {
                'transaction_id': transaction.id,
                'sender': transaction.seller.name if hasattr(transaction.seller, 'name') else str(transaction.seller),
                'offered_price': str(message.offered_price) if message.offered_price else None,
                'url': f'/transactions/{transaction.id}/'
            }
        )

    @staticmethod
    def send_counter_offer_notification(transaction, message):
        """发送还盘通知"""
        # 确定接收公司
        receiver_company = transaction.seller if message.sender_role == 'buyer' else transaction.buyer
        user_ids = NotificationService.get_company_member_ids(receiver_company)
        # message.sender 仍然是 User 对象
        sender_name = message.sender.username if hasattr(message.sender, 'username') else str(message.sender)
        NotificationService.send_notification(
            user_ids,
            'counter_offer_received',
            {
                'transaction_id': transaction.id,
                'sender': sender_name,
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
