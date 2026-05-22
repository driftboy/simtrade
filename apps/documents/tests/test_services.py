import pytest
from apps.documents.services import DependencyService, DataFillService
from apps.documents.models import DocumentTemplate, DocumentDependency, Document
from apps.users.models import User


class TestDependencyService:
    @pytest.fixture(autouse=True)
    def setup_dependencies(self, db):
        """设置测试用的依赖关系"""
        # 创建模板
        for code, name in [
            ('commercial_invoice', '商业发票'),
            ('packing_list', '装箱单'),
            ('bill_of_lading', '海运提单'),
        ]:
            DocumentTemplate.objects.create(code=code, name=name, content='<html></html>')

        # 创建依赖关系
        DocumentDependency.objects.create(
            document_type='packing_list',
            depends_on='commercial_invoice',
            dependency_type='sequential'
        )
        DocumentDependency.objects.create(
            document_type='bill_of_lading',
            depends_on='packing_list',
            dependency_type='sequential'
        )

    def test_can_create_document_without_dependencies(self, db):
        """测试创建没有依赖的单证"""
        user = User.objects.create_user(username='test', password='pass')
        service = DependencyService(user)

        can_create, message = service.can_create('commercial_invoice')

        assert can_create is True
        assert message == ''

    def test_cannot_create_document_with_unmet_dependencies(self, db):
        """测试依赖未满足时不能创建单证"""
        user = User.objects.create_user(username='test', password='pass')
        service = DependencyService(user)

        can_create, message = service.can_create('packing_list')

        assert can_create is False
        assert '商业发票' in message

    def test_can_create_document_with_met_dependencies(self, db):
        """测试依赖满足后可以创建单证"""
        user = User.objects.create_user(username='test', password='pass')

        # 先创建依赖的单证
        template = DocumentTemplate.objects.get(code='commercial_invoice')
        Document.objects.create(
            template=template,
            created_by=user,
            status='approved'
        )

        service = DependencyService(user)
        can_create, message = service.can_create('packing_list')

        assert can_create is True

    def test_get_creation_order(self, db):
        """测试获取单证创建顺序"""
        service = DependencyService(None)
        order = service.get_creation_order()

        assert 'commercial_invoice' in order
        assert order.index('commercial_invoice') < order.index('packing_list')
        assert order.index('packing_list') < order.index('bill_of_lading')


class TestDataFillService:
    """数据填充服务测试"""

    def test_fill_from_transaction(self, db):
        """测试从交易数据填充"""
        # 模拟交易数据
        transaction_data = {
            'buyer_name': 'ABC Trading Co.',
            'seller_name': 'XYZ Export Corp.',
            'amount': 10000.00,
            'quantity': 1000,
            'product_name': 'Cotton T-Shirts',
        }

        service = DataFillService()
        filled_data = service.fill_from_transaction('commercial_invoice', transaction_data)

        assert filled_data['buyer_name'] == 'ABC Trading Co.'
        assert filled_data['amount'] == 10000.00

    def test_fill_from_existing_document(self, db):
        """测试从已有单证继承数据"""
        template = DocumentTemplate.objects.create(
            code='commercial_invoice',
            name='商业发票',
            content='<html></html>'
        )
        user = User.objects.create_user(username='test', password='pass')

        # 创建已存在的发票
        existing_doc = Document.objects.create(
            template=template,
            created_by=user,
            data='{"invoice_no": "INV001", "buyer_name": "ABC Trading", "amount": 5000.00}'
        )

        service = DataFillService()
        filled_data = service.fill_from_document(
            'packing_list',
            existing_doc
        )

        assert filled_data['invoice_no'] == 'INV001'
        assert filled_data['amount'] == 5000.00
