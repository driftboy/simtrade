"""
Tests for Document serializers.
"""
import pytest
import json
from apps.documents.serializers import (
    DocumentSerializer,
    DocumentTemplateSerializer,
    TemplateFieldSerializer,
    DocumentValidationSerializer,
    DocumentCreateSerializer,
    DocumentSubmitSerializer
)
from apps.documents.models import (
    Document,
    DocumentTemplate,
    TemplateField,
    DocumentValidation
)
from apps.users.models import User


@pytest.mark.django_db
class TestDocumentTemplateSerializer:
    """测试单证模板序列化器"""

    def test_serialize_template(self):
        """测试序列化模板"""
        template = DocumentTemplate.objects.create(
            code='commercial_invoice',
            name='商业发票',
            content='<html></html>'
        )

        serializer = DocumentTemplateSerializer(template)
        data = serializer.data

        assert data['code'] == 'commercial_invoice'
        assert data['name'] == '商业发票'
        assert data['version'] == '1.0'
        assert data['is_system'] is True
        assert data['is_active'] is True
        assert 'fields' in data
        assert 'created_by' in data

    def test_serialize_template_with_fields(self):
        """测试序列化带字段的模板"""
        template = DocumentTemplate.objects.create(
            code='commercial_invoice',
            name='商业发票',
            content='<html></html>'
        )
        TemplateField.objects.create(
            template=template,
            field_name='invoice_no',
            label='发票号',
            field_type='text',
            required=True,
            sort_order=1
        )

        serializer = DocumentTemplateSerializer(template)
        data = serializer.data

        assert len(data['fields']) == 1
        assert data['fields'][0]['field_name'] == 'invoice_no'
        assert data['fields'][0]['label'] == '发票号'
        assert data['fields'][0]['field_type'] == 'text'


@pytest.mark.django_db
class TestTemplateFieldSerializer:
    """测试模板字段序列化器"""

    def test_serialize_field(self):
        """测试序列化字段"""
        template = DocumentTemplate.objects.create(
            code='commercial_invoice',
            name='商业发票',
            content='<html></html>'
        )
        field = TemplateField.objects.create(
            template=template,
            field_name='invoice_no',
            label='发票号',
            field_type='text',
            required=True,
            default_value='INV-',
            help_text='请输入发票号',
            sort_order=1
        )

        serializer = TemplateFieldSerializer(field)
        data = serializer.data

        assert data['field_name'] == 'invoice_no'
        assert data['label'] == '发票号'
        assert data['field_type'] == 'text'
        assert data['required'] is True
        assert data['default_value'] == 'INV-'
        assert data['help_text'] == '请输入发票号'
        assert data['sort_order'] == 1


@pytest.mark.django_db
class TestDocumentSerializer:
    """测试单证序列化器"""

    def test_serialize_document(self):
        """测试序列化单证"""
        template = DocumentTemplate.objects.create(
            code='commercial_invoice',
            name='商业发票',
            content='<html></html>'
        )
        user = User.objects.create_user(username='test', password='pass')
        doc = Document.objects.create(
            template=template,
            created_by=user,
            data='{"invoice_no": "INV001"}'
        )

        serializer = DocumentSerializer(doc)
        data = serializer.data

        assert data['id'] == doc.id
        assert data['template'] == template.id
        assert data['status'] == 'draft'
        assert data['template_name'] == '商业发票'
        assert data['template_code'] == 'commercial_invoice'
        assert 'created_by' in data
        assert data['created_by']['username'] == 'test'

    def test_serialize_document_with_validations(self):
        """测试序列化带校验记录的单证"""
        template = DocumentTemplate.objects.create(
            code='commercial_invoice',
            name='商业发票',
            content='<html></html>'
        )
        user = User.objects.create_user(username='test', password='pass')
        doc = Document.objects.create(
            template=template,
            created_by=user,
            data='{}'
        )
        DocumentValidation.objects.create(
            document=doc,
            rule='required_field_check',
            passed=True,
            validation_type='auto'
        )

        serializer = DocumentSerializer(doc)
        data = serializer.data

        assert 'validations' in data
        assert len(data['validations']) == 1
        assert data['validations'][0]['rule'] == 'required_field_check'
        assert data['validations'][0]['passed'] is True

    def test_document_data_field(self):
        """测试单证数据字段序列化"""
        template = DocumentTemplate.objects.create(
            code='commercial_invoice',
            name='商业发票',
            content='<html></html>'
        )
        user = User.objects.create_user(username='test', password='pass')
        doc = Document.objects.create(
            template=template,
            created_by=user,
            data='{"invoice_no": "INV001", "amount": 1000}'
        )

        serializer = DocumentSerializer(doc)
        data = serializer.data

        assert data['data'] == '{"invoice_no": "INV001", "amount": 1000}'


@pytest.mark.django_db
class TestDocumentValidationSerializer:
    """测试单证校验序列化器"""

    def test_serialize_validation(self):
        """测试序列化校验记录"""
        template = DocumentTemplate.objects.create(
            code='commercial_invoice',
            name='商业发票',
            content='<html></html>'
        )
        user = User.objects.create_user(username='test', password='pass')
        doc = Document.objects.create(
            template=template,
            created_by=user,
            data='{}'
        )
        validation = DocumentValidation.objects.create(
            document=doc,
            rule='required_field_check',
            passed=False,
            error_message='发票号为必填项',
            score_deduction=10,
            validation_type='auto'
        )

        serializer = DocumentValidationSerializer(validation)
        data = serializer.data

        assert data['rule'] == 'required_field_check'
        assert data['passed'] is False
        assert data['error_message'] == '发票号为必填项'
        assert data['score_deduction'] == 10
        assert data['validation_type'] == 'auto'
        assert 'created_at' in data


@pytest.mark.django_db
class TestDocumentCreateSerializer:
    """测试创建单证序列化器"""

    def test_serialize_create_fields(self):
        """测试创建序列化器字段"""
        serializer = DocumentCreateSerializer()
        assert 'template' in serializer.fields
        assert 'data' in serializer.fields

    def test_validate_active_template(self):
        """测试验证启用的模板"""
        template = DocumentTemplate.objects.create(
            code='commercial_invoice',
            name='商业发票',
            content='<html></html>',
            is_active=True
        )
        serializer = DocumentCreateSerializer(data={
            'template': template.id,
            'data': '{}'
        })
        assert serializer.is_valid()
        assert serializer.validated_data['template'] == template

    def test_validate_inactive_template(self):
        """测试验证未启用的模板"""
        template = DocumentTemplate.objects.create(
            code='commercial_invoice',
            name='商业发票',
            content='<html></html>',
            is_active=False
        )
        serializer = DocumentCreateSerializer(data={
            'template': template.id,
            'data': '{}'
        })
        assert not serializer.is_valid()
        assert 'template' in serializer.errors


@pytest.mark.django_db
class TestDocumentSubmitSerializer:
    """测试提交审核序列化器"""

    def test_serialize_with_comment(self):
        """测试带评论的序列化"""
        serializer = DocumentSubmitSerializer(data={
            'comment': '请审核'
        })
        assert serializer.is_valid()
        assert serializer.validated_data['comment'] == '请审核'

    def test_serialize_without_comment(self):
        """测试不带评论的序列化"""
        serializer = DocumentSubmitSerializer(data={})
        assert serializer.is_valid()

    def test_comment_is_optional(self):
        """测试评论字段是可选的"""
        serializer = DocumentSubmitSerializer()
        assert serializer.fields['comment'].required is False
        assert serializer.fields['comment'].allow_blank is True
