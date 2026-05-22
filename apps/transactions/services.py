from django.utils import timezone
from apps.transactions.models import Transaction, InquiryMessage, TransactionLog, Contract
from apps.transactions.models import ContractAmendment, ContractSignature
from apps.transactions.models import LetterOfCredit, LcAmendment, BankOperation
from apps.notifications.services import NotificationService
from apps.roles.services import RoleService


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

        # 获取用户当前激活的角色
        current_role = RoleService.get_current_role(user)
        if not current_role:
            raise ValueError("用户没有激活的角色，无法签字")

        # 验证角色是否有权签字（当前角色的公司必须是交易的一方）
        buyer_id = contract.transaction.buyer_id
        seller_id = contract.transaction.seller_id

        if party == 'buyer' and current_role.company_id != buyer_id:
            raise ValueError("用户当前角色不属于买方公司，无权代表买方签字")
        elif party == 'seller' and current_role.company_id != seller_id:
            raise ValueError("用户当前角色不属于卖方公司，无权代表卖方签字")

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

        # 触发状态联动
        StateTransitionService.on_contract_effective(contract)

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


class LetterOfCreditService:
    """信用证业务服务"""

    @staticmethod
    def create_from_contract(contract):
        """从合同创建信用证草稿"""
        # 检查支付方式是否为 L/C
        # 支持 L/C, L/C at sight 等格式
        if not contract.payment_term or 'L/C' not in contract.payment_term:
            return None

        lc_no = LetterOfCreditService._generate_lc_no()

        # 默认单据要求
        documents_required = [
            'commercial_invoice',
            'bill_of_lading',
            'insurance_policy',
            'packing_list'
        ]

        lc = LetterOfCredit.objects.create(
            lc_no=lc_no,
            contract=contract,
            transaction=contract.transaction,
            applicant=contract.transaction.buyer,
            beneficiary=contract.transaction.seller,
            amount=contract.total_amount,
            currency=contract.currency,
            expiry_date=contract.delivery_time + timezone.timedelta(days=90),
            latest_shipment_date=contract.delivery_time,
            port_of_loading=contract.port_of_loading,
            port_of_discharge=contract.port_of_discharge,
            documents_required=documents_required,
            issuing_bank='中国银行',
            advising_bank='通知银行'
        )

        TransactionService.log_transaction(
            contract.transaction,
            contract.transaction.created_by,
            'lc_created',
            {'lc_id': lc.id}
        )
        return lc

    @staticmethod
    def apply_for_issue(lc, user):
        """申请开证：草稿 -> 待开证"""
        if lc.status != 'draft':
            raise ValueError(f"信用证状态不允许申请开证: {lc.status}")

        lc.status = 'pending_issue'
        lc.save()

        TransactionService.log_transaction(
            lc.transaction,
            user,
            'lc_applied_for_issue',
            {'lc_id': lc.id}
        )
        return lc

    @staticmethod
    def auto_issue(lc):
        """系统自动开证：待开证 -> 已开证"""
        if lc.status != 'pending_issue':
            raise ValueError(f"信用证状态不允许开证: {lc.status}")

        lc.status = 'issued'
        lc.issue_date = timezone.now().date()
        lc.issued_at = timezone.now()
        lc.advised_at = timezone.now()
        lc.save()

        BankOperation.objects.create(
            lc=lc,
            operation_type='issue',
            processed_by='system',
            notes='系统自动开证'
        )

        BankOperation.objects.create(
            lc=lc,
            operation_type='advise',
            processed_by='system',
            notes='系统自动通知'
        )

        TransactionService.log_transaction(
            lc.transaction,
            lc.transaction.created_by,
            'lc_issued',
            {'lc_id': lc.id}
        )
        return lc

    @staticmethod
    def request_amendment(lc, content, reason, user):
        """请求修改：已开证 -> 修改中"""
        if lc.status != 'issued':
            raise ValueError(f"信用证状态不允许请求修改: {lc.status}")

        amendment_no = LetterOfCreditService._generate_amendment_no(lc)
        amendment = LcAmendment.objects.create(
            lc=lc,
            amendment_no=amendment_no,
            initiated_by=user,
            content=content,
            reason=reason
        )

        lc.status = 'amending'
        lc.save()
        return amendment

    @staticmethod
    def approve_amendment(lc, amendment_id):
        """批准修改：修改中 -> 已开证"""
        if lc.status != 'amending':
            raise ValueError(f"信用证状态不允许批准修改: {lc.status}")

        amendment = LcAmendment.objects.get(id=amendment_id)
        amendment.status = 'approved'
        amendment.processed_at = timezone.now()
        amendment.save()

        for key, value in amendment.content.items():
            setattr(lc, key, value)

        lc.status = 'issued'
        lc.save()
        return lc

    @staticmethod
    def withdraw_amendment(lc, user):
        """撤回修改请求：修改中 -> 已开证"""
        if lc.status != 'amending':
            raise ValueError(f"信用证状态不允许撤回修改: {lc.status}")

        lc.amendments.filter(status='pending').delete()
        lc.status = 'issued'
        lc.save()
        return lc

    @staticmethod
    def submit_documents(lc, document_ids, user):
        """交单：已开证 -> 已交单"""
        if lc.status != 'issued':
            raise ValueError(f"信用证状态不允许交单: {lc.status}")

        lc.status = 'submitted'
        lc.submitted_at = timezone.now()
        lc.save()

        TransactionService.log_transaction(
            lc.transaction,
            user,
            'lc_documents_submitted',
            {'lc_id': lc.id, 'document_count': len(document_ids)}
        )
        return lc

    @staticmethod
    def auto_negotiate(lc):
        """系统自动议付：已交单 -> 已议付"""
        if lc.status != 'submitted':
            return lc

        lc.status = 'negotiated'
        lc.negotiated_at = timezone.now()
        lc.save()

        BankOperation.objects.create(
            lc=lc,
            operation_type='negotiate',
            processed_by='system',
            notes='单据齐全，自动议付',
            result={'documents_count': len(lc.documents_required)}
        )

        LetterOfCreditService.auto_pay(lc)
        return lc

    @staticmethod
    def auto_pay(lc):
        """系统自动付款：已议付 -> 已付款"""
        if lc.status != 'negotiated':
            return lc

        lc.status = 'paid'
        lc.paid_at = timezone.now()
        lc.save()

        BankOperation.objects.create(
            lc=lc,
            operation_type='pay',
            processed_by='system',
            notes=f'自动付款 {lc.amount} {lc.currency}',
            result={'amount': str(lc.amount), 'currency': lc.currency}
        )

        return lc

    @staticmethod
    def cancel(lc, user, reason):
        """取消信用证"""
        if lc.status in ['negotiated', 'paid']:
            raise ValueError(f"信用证状态不允许取消: {lc.status}")

        lc.status = 'cancelled'
        lc.save()

        TransactionService.log_transaction(
            lc.transaction,
            user,
            'lc_cancelled',
            {'reason': reason}
        )
        return lc

    @staticmethod
    def _generate_lc_no():
        """生成信用证号"""
        import random
        import string
        year = timezone.now().year
        random_str = ''.join(random.choices(string.digits, k=6))
        return f"LC{year}{random_str}"

    @staticmethod
    def _generate_amendment_no(lc):
        """生成修改编号"""
        count = lc.amendments.count() + 1
        return f"{lc.lc_no}-A{count:02d}"


class StateTransitionService:
    """状态联动服务"""

    @staticmethod
    def on_contract_effective(contract):
        """合同生效联动"""
        # 更新交易状态
        transaction = contract.transaction
        if transaction.status == 'contracted':
            transaction.status = 'in_progress'
            transaction.save()

        # 如果付款方式是信用证，自动创建信用证
        if contract.payment_term and 'L/C' in contract.payment_term:
            LetterOfCreditService.create_from_contract(contract)

        # 使用 transaction.created_by 而非 transaction.buyer
        # 因为 log_transaction 需要 User 类型，而 buyer 现在是 Company
        TransactionService.log_transaction(
            transaction,
            transaction.created_by,
            'contract_became_effective',
            {'contract_id': contract.id}
        )

    @staticmethod
    def on_lc_created(lc):
        """信用证创建联动"""
        NotificationService.send_lc_created_notification(lc)

    @staticmethod
    def on_lc_issued(lc):
        """信用证开立联动"""
        TransactionService.log_transaction(
            lc.transaction,
            lc.transaction.created_by,
            'lc_issued',
            {'lc_id': lc.id}
        )

    @staticmethod
    def on_lc_paid(lc):
        """信用证付款联动"""
        TransactionService.log_transaction(
            lc.transaction,
            lc.transaction.created_by,
            'lc_paid',
            {'lc_id': lc.id, 'amount': str(lc.amount)}
        )
