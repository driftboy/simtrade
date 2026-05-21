import pytest
from django.contrib.auth import get_user_model
from apps.documents.validators import DocumentValidator
from apps.documents.models import Document, DocumentTemplate, DocumentValidation

User = get_user_model()


@pytest.mark.django_db
class TestDocumentValidator:
    """测试 DocumentValidator 校验器"""

    def test_date_logic_validation_pass(self):
        """测试日期逻辑校验 - 正确的情况"""
        template = DocumentTemplate.objects.create(
            code='commercial_invoice',
            name='商业发票',
            content='<html>...</html>'
        )
        user = User.objects.create_user(username='test', password='pass')

        doc = Document.objects.create(
            template=template,
            created_by=user,
            data='{"invoice_date": "2026-05-01", "shipment_date": "2026-05-10", "insurance_date": "2026-05-15"}'
        )

        validator = DocumentValidator(doc)
        results = validator.validate_all()

        assert 'date_logic' in results
        assert results['date_logic']['passed'] is True
        assert len(results['date_logic']['errors']) == 0

    def test_date_logic_validation_fail_invoice_after_shipment(self):
        """测试日期逻辑校验 - 发票日期晚于装运日期"""
        template = DocumentTemplate.objects.create(
            code='commercial_invoice',
            name='商业发票',
            content='<html>...</html>'
        )
        user = User.objects.create_user(username='test', password='pass')

        doc = Document.objects.create(
            template=template,
            created_by=user,
            data='{"invoice_date": "2026-05-10", "shipment_date": "2026-05-01"}'
        )

        validator = DocumentValidator(doc)
        results = validator.validate_all()

        assert results['date_logic']['passed'] is False
        assert len(results['date_logic']['errors']) > 0
        assert any('发票日期不能晚于装运日期' in err for err in results['date_logic']['errors'])

    def test_date_logic_validation_fail_shipment_after_insurance(self):
        """测试日期逻辑校验 - 装运日期晚于保险日期"""
        template = DocumentTemplate.objects.create(
            code='commercial_invoice',
            name='商业发票',
            content='<html>...</html>'
        )
        user = User.objects.create_user(username='test', password='pass')

        doc = Document.objects.create(
            template=template,
            created_by=user,
            data='{"invoice_date": "2026-05-01", "shipment_date": "2026-05-10", "insurance_date": "2026-05-05"}'
        )

        validator = DocumentValidator(doc)
        results = validator.validate_all()

        assert results['date_logic']['passed'] is False
        assert any('装运日期不能晚于保险日期' in err for err in results['date_logic']['errors'])

    def test_amount_consistency_validation_pass(self):
        """测试金额一致性校验 - 正确的情况"""
        template = DocumentTemplate.objects.create(
            code='commercial_invoice',
            name='商业发票',
            content='<html>...</html>'
        )
        user = User.objects.create_user(username='test', password='pass')

        doc = Document.objects.create(
            template=template,
            created_by=user,
            data='{"invoice_amount": 10000.00, "draft_amount": 10000.00, "insurance_amount": 12000.00}'
        )

        validator = DocumentValidator(doc)
        results = validator.validate_all()

        assert results['amount_consistency']['passed'] is True
        assert len(results['amount_consistency']['errors']) == 0

    def test_amount_consistency_validation_fail_invoice_draft_mismatch(self):
        """测试金额一致性校验 - 发票金额与汇票金额不一致"""
        template = DocumentTemplate.objects.create(
            code='commercial_invoice',
            name='商业发票',
            content='<html>...</html>'
        )
        user = User.objects.create_user(username='test', password='pass')

        doc = Document.objects.create(
            template=template,
            created_by=user,
            data='{"invoice_amount": 10000.00, "draft_amount": 9000.00}'
        )

        validator = DocumentValidator(doc)
        results = validator.validate_all()

        assert results['amount_consistency']['passed'] is False
        assert any('发票金额必须等于汇票金额' in err for err in results['amount_consistency']['errors'])

    def test_amount_consistency_validation_fail_insurance_insufficient(self):
        """测试金额一致性校验 - 保险金额不足"""
        template = DocumentTemplate.objects.create(
            code='commercial_invoice',
            name='商业发票',
            content='<html>...</html>'
        )
        user = User.objects.create_user(username='test', password='pass')

        doc = Document.objects.create(
            template=template,
            created_by=user,
            data='{"invoice_amount": 10000.00, "insurance_amount": 10000.00}'
        )

        validator = DocumentValidator(doc)
        results = validator.validate_all()

        assert results['amount_consistency']['passed'] is False
        assert any('保险金额应至少为发票金额的110%' in err for err in results['amount_consistency']['errors'])

    def test_quantity_consistency_validation_pass(self):
        """测试数量一致性校验 - 正确的情况"""
        template = DocumentTemplate.objects.create(
            code='commercial_invoice',
            name='商业发票',
            content='<html>...</html>'
        )
        user = User.objects.create_user(username='test', password='pass')

        doc = Document.objects.create(
            template=template,
            created_by=user,
            data='{"quantity": 1000, "net_weight": 5000, "gross_weight": 5500}'
        )

        validator = DocumentValidator(doc)
        results = validator.validate_all()

        assert results['quantity_consistency']['passed'] is True
        assert len(results['quantity_consistency']['errors']) == 0

    def test_quantity_consistency_validation_fail_weight_mismatch(self):
        """测试数量一致性校验 - 净重大于毛重"""
        template = DocumentTemplate.objects.create(
            code='commercial_invoice',
            name='商业发票',
            content='<html>...</html>'
        )
        user = User.objects.create_user(username='test', password='pass')

        doc = Document.objects.create(
            template=template,
            created_by=user,
            data='{"quantity": 1000, "net_weight": 6000, "gross_weight": 5500}'
        )

        validator = DocumentValidator(doc)
        results = validator.validate_all()

        assert results['quantity_consistency']['passed'] is False
        assert any('净重不能大于毛重' in err for err in results['quantity_consistency']['errors'])

    def test_required_fields_validation_pass(self):
        """测试必填字段校验 - 正确的情况"""
        template = DocumentTemplate.objects.create(
            code='commercial_invoice',
            name='商业发票',
            content='<html>...</html>'
        )
        user = User.objects.create_user(username='test', password='pass')

        doc = Document.objects.create(
            template=template,
            created_by=user,
            data='{"invoice_no": "INV001", "invoice_date": "2026-05-01", "buyer_name": "ABC Corp", "seller_name": "XYZ Corp", "invoice_amount": 10000.00, "currency": "USD"}'
        )

        validator = DocumentValidator(doc)
        results = validator.validate_all()

        assert results['required_fields']['passed'] is True
        assert len(results['required_fields']['errors']) == 0

    def test_required_fields_validation_fail(self):
        """测试必填字段校验 - 缺少必填字段"""
        template = DocumentTemplate.objects.create(
            code='commercial_invoice',
            name='商业发票',
            content='<html>...</html>'
        )
        user = User.objects.create_user(username='test', password='pass')

        doc = Document.objects.create(
            template=template,
            created_by=user,
            data='{"invoice_no": "INV001"}'  # 缺少 invoice_date 和 buyer_name
        )

        validator = DocumentValidator(doc)
        results = validator.validate_all()

        assert results['required_fields']['passed'] is False
        assert len(results['required_fields']['errors']) > 0

    def test_save_validation_results(self):
        """测试保存校验结果"""
        template = DocumentTemplate.objects.create(
            code='commercial_invoice',
            name='商业发票',
            content='<html>...</html>'
        )
        user = User.objects.create_user(username='test', password='pass')
        doc = Document.objects.create(
            template=template,
            created_by=user,
            data='{"invoice_date": "2026-05-10", "shipment_date": "2026-05-01"}'
        )

        validator = DocumentValidator(doc)
        validator.save_results()

        # 检查是否创建了 DocumentValidation 记录
        assert doc.validations.count() > 0

        # 检查是否保存了 auto_validation_result
        doc.refresh_from_db()
        assert doc.auto_validation_result is not None
