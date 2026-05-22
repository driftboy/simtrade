from django.utils import timezone
from apps.transactions.models import Transaction, InquiryMessage, TransactionLog, Contract
from apps.transactions.models import ContractAmendment, ContractSignature
from apps.notifications.services import NotificationService


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
        if message.message_type == 'inquiry':
            # 询盘通知
            NotificationService.send_inquiry_notification(transaction, message)
        elif message.message_type == 'offer':
            # 发盘通知
            NotificationService.send_offer_notification(transaction, message)
            if transaction.status == 'inquiring':
                transaction.status = 'negotiating'
                transaction.save()
        elif message.message_type == 'counter_offer':
            # 还盘通知
            NotificationService.send_counter_offer_notification(transaction, message)
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


class ContractService:
    """合同业务服务"""

    @staticmethod
    def send_for_confirmation(contract, user):
        """发送确认：草稿 -> 待确认"""
        if contract.status != 'draft':
            raise ValueError(f"合同状态不允许发送确认: {contract.status}")

        contract.status = 'pending_confirm'
        contract.save()

        TransactionService.log_transaction(
            contract.transaction,
            user,
            'contract_sent_for_confirmation',
            {'contract_id': contract.id}
        )
        return contract

    @staticmethod
    def confirm_terms(contract, user):
        """确认条款：待确认 -> 待签字"""
        if contract.status != 'pending_confirm':
            raise ValueError(f"合同状态不允许确认: {contract.status}")

        contract.status = 'pending_sign'
        contract.save()

        TransactionService.log_transaction(
            contract.transaction,
            user,
            'contract_terms_confirmed',
            {'contract_id': contract.id}
        )
        return contract

    @staticmethod
    def request_amendment(contract, change_content, reason, user):
        """请求修改：待确认 -> 修改中"""
        if contract.status != 'pending_confirm':
            raise ValueError(f"合同状态不允许请求修改: {contract.status}")

        amendment_no = ContractService._generate_amendment_no(contract)
        ContractAmendment.objects.create(
            contract=contract,
            amendment_no=amendment_no,
            requested_by=user,
            change_content=change_content,
            reason=reason
        )

        contract.status = 'amending'
        contract.save()
        return contract

    @staticmethod
    def accept_amendment(contract, amendment_id, user):
        """接受修改：修改中 -> 待确认"""
        if contract.status != 'amending':
            raise ValueError(f"合同状态不允许接受修改: {contract.status}")

        amendment = ContractAmendment.objects.get(id=amendment_id)
        amendment.status = 'accepted'
        amendment.processed_at = timezone.now()
        amendment.save()

        # 应用修改内容到合同
        for key, value in amendment.change_content.items():
            setattr(contract, key, value)

        contract.status = 'pending_confirm'
        contract.save()
        return contract

    @staticmethod
    def sign(contract, user, party, ip_address):
        """签字：待签字 -> 一方签字 -> 已签字"""
        if contract.status not in ['pending_sign', 'one_signed']:
            raise ValueError(f"合同状态不允许签字: {contract.status}")

        signature, created = ContractSignature.objects.get_or_create(
            contract=contract,
            party=party,
            defaults={
                'signer': user,
                'signer_name': user.username,
                'ip_address': ip_address
            }
        )

        # 更新签字时间
        if party == 'buyer':
            contract.buyer_signed_at = timezone.now()
        elif party == 'seller':
            contract.seller_signed_at = timezone.now()

        # 检查是否双方都已签字
        if contract.buyer_signed_at and contract.seller_signed_at:
            contract.status = 'signed'
        else:
            contract.status = 'one_signed'

        contract.save()
        return contract

    @staticmethod
    def become_effective(contract):
        """合同生效：已签字 -> 已生效，触发联动"""
        if contract.status != 'signed':
            raise ValueError(f"合同状态不允许生效: {contract.status}")

        contract.status = 'effective'
        contract.effective_at = timezone.now()
        contract.save()

        # 触发状态联动（留待任务7实现）
        # StateTransitionService.on_contract_effective(contract)

        return contract

    @staticmethod
    def cancel(contract, user, reason):
        """取消合同"""
        if contract.status in ['effective', 'fulfilled', 'cancelled']:
            raise ValueError(f"合同状态不允许取消: {contract.status}")

        contract.status = 'cancelled'
        contract.save()

        TransactionService.log_transaction(
            contract.transaction,
            user,
            'contract_cancelled',
            {'reason': reason}
        )
        return contract

    @staticmethod
    def _generate_amendment_no(contract):
        """生成修改编号"""
        import random
        import string
        count = contract.amendments.count() + 1
        return f"{contract.contract_no}-A{count:02d}"
