import pytest
import json
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from apps.transactions.models import Transaction, InquiryMessage
from apps.users.models import User
from apps.roles.services import CompanyService
from apps.core.models import Country
from apps.products.models import Product


def get_or_create_country():
    """获取或创建默认国家"""
    country, _ = Country.objects.get_or_create(
        code='CN',
        defaults={
            'name': '中国',
            'name_en': 'China',
            'phone_code': '86'
        }
    )
    return country


def create_company_for_user(user, name_suffix=''):
    """为用户创建公司"""
    country = get_or_create_country()
    return CompanyService.create_company(
        user=user,
        name=f'{user.username}{name_suffix}公司',
        name_en=f'{user.username}{name_suffix} Company',
        country_id=country.code
    )


class TransactionAPITest(TestCase):
    """测试交易 API"""

    def setUp(self):
        self.buyer = User.objects.create_user(username='buyer', password='testpass', email='buyer@example.com')
        self.seller = User.objects.create_user(username='seller', password='testpass', email='seller@example.com')
        self.buyer_company = create_company_for_user(self.buyer, '_API买方')
        self.seller_company = create_company_for_user(self.seller, '_API卖方')
        self.product = Product.objects.create(code='API-P001', name='Test Product', category='electronics', unit='PCS')
        self.client = APIClient()

    def test_create_transaction(self):
        """测试创建交易"""
        self.client.force_authenticate(user=self.buyer)
        url = reverse('transactions:transaction-list')
        data = {
            'seller': self.seller.id,
            'product': self.product.id,
            'quantity': 1000,
            'unit_price': 10.00,
            'currency': 'USD'
        }
        response = self.client.post(url, data, format='json')
        assert response.status_code == 200 or response.status_code == 201
        assert response.json()['code'] == 0

    def test_list_my_transactions(self):
        """测试获取我的交易列表"""
        self.client.force_authenticate(user=self.buyer)
        # 先创建一个交易
        Transaction.objects.create(
            buyer=self.buyer_company,
            seller=self.seller_company,
            product=self.product,
            quantity=1000,
            unit_price=10.00
        )
        url = reverse('transactions:transaction-list')
        response = self.client.get(url)
        assert response.status_code == 200
        assert len(response.json()['data']) >= 1

    def test_transaction_detail(self):
        """测试获取交易详情"""
        self.client.force_authenticate(user=self.buyer)
        transaction = Transaction.objects.create(
            buyer=self.buyer_company,
            seller=self.seller_company,
            product=self.product,
            quantity=1000,
            unit_price=10.00
        )
        url = reverse('transactions:transaction-detail', kwargs={'pk': transaction.id})
        response = self.client.get(url)
        assert response.status_code == 200
        assert response.json()['code'] == 0
        assert response.json()['data']['id'] == transaction.id

    def test_send_message(self):
        """测试发送磋商消息"""
        self.client.force_authenticate(user=self.buyer)
        transaction = Transaction.objects.create(
            buyer=self.buyer_company,
            seller=self.seller_company,
            product=self.product,
            quantity=1000,
            unit_price=10.00
        )
        url = reverse('transactions:transaction-send-message', kwargs={'pk': transaction.id})
        data = {
            'message_type': 'inquiry',
            'content': '请报价1000吨',
            'offered_product_name': 'Test Product'
        }
        response = self.client.post(url, data, format='json')
        assert response.status_code == 200
        assert response.json()['code'] == 0

    def test_get_messages(self):
        """测试获取消息列表"""
        self.client.force_authenticate(user=self.buyer)
        transaction = Transaction.objects.create(
            buyer=self.buyer_company,
            seller=self.seller_company,
            product=self.product,
            quantity=1000,
            unit_price=10.00
        )
        InquiryMessage.objects.create(
            transaction=transaction,
            sender=self.buyer,
            sender_role='buyer',
            message_type='inquiry',
            content='请报价'
        )
        url = reverse('transactions:transaction-messages', kwargs={'pk': transaction.id})
        response = self.client.get(url)
        assert response.status_code == 200
        assert len(response.json()['data']) >= 1

    def test_cancel_transaction(self):
        """测试取消交易"""
        self.client.force_authenticate(user=self.buyer)
        transaction = Transaction.objects.create(
            buyer=self.buyer_company,
            seller=self.seller_company,
            product=self.product,
            quantity=1000,
            unit_price=10.00,
            status='inquiring'
        )
        url = reverse('transactions:transaction-cancel', kwargs={'pk': transaction.id})
        response = self.client.post(url)
        assert response.status_code == 200
        assert response.json()['code'] == 0

        # 验证状态已更新
        transaction.refresh_from_db()
        assert transaction.status == 'cancelled'

    def test_accept_negotiation_syncs_to_transaction(self):
        """测试接受磋商时同步条款到 Transaction"""
        self.client.force_authenticate(user=self.buyer)
        transaction = Transaction.objects.create(
            buyer=self.buyer_company,
            seller=self.seller_company,
            product=self.product,
            quantity=1000,
            unit_price=10.00
        )
        message_data = {
            'message_type': 'accept',
            'content': '接受报价',
            'offered_product_name': '测试产品',
            'offered_payment_term': 'lc',
            'offered_delivery_date': '2024-12-31',
            'offered_packing': '纸箱包装',
            'offered_insurance': 'CIF条款加成110%'
        }
        url = reverse('transactions:transaction-send-message', kwargs={'pk': transaction.id})
        response = self.client.post(url, data=json.dumps(message_data), content_type='application/json')
        assert response.status_code == 200

        # 验证 Transaction 已更新
        transaction.refresh_from_db()
        assert transaction.product_name == '测试产品'
        assert transaction.payment_term == 'lc'
        assert str(transaction.delivery_date) == '2024-12-31'
        assert transaction.packing == '纸箱包装'
        assert transaction.insurance == 'CIF条款加成110%'
