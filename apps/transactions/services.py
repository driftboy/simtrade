from django.utils import timezone
from apps.transactions.models import Transaction, InquiryMessage, TransactionLog, Contract


class TransactionService:
    """交易业务服务"""

    @staticmethod
    def log_transaction(transaction, user, action, details):
        """记录交易日志"""
        return TransactionLog.objects.create(
            transaction=transaction,
            user=user,
            action=action,
            details=details
        )

    @staticmethod
    def handle_message(transaction, message):
        """处理消息，更新交易状态"""
        if message.message_type == 'offer':
            # 发盘后进入还盘中
            if transaction.status == 'inquiring':
                transaction.status = 'negotiating'
                transaction.save()
        elif message.message_type == 'accept':
            # 接受后进入待签约
            transaction.status = 'pending_contract'
            transaction.save()

    @staticmethod
    def create_contract(transaction, contract_data):
        """创建合同草稿"""
        contract_no = TransactionService._generate_contract_no()
        contract = Contract.objects.create(
            contract_no=contract_no,
            transaction=transaction,
            **contract_data
        )
        transaction.status = 'pending_contract'
        transaction.save()
        return contract

    @staticmethod
    def _generate_contract_no():
        """生成合同号"""
        import random
        import string
        year = timezone.now().year
        random_str = ''.join(random.choices(string.digits, k=4))
        return f"SC{year}{random_str}"
