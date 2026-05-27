import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.documents.models import DocumentTemplate, TemplateField, DocumentDependency, Document, DocumentValidation


class DocumentTemplateTest(TestCase):
    def test_create_template(self):
        template = DocumentTemplate.objects.create(
            code='commercial_invoice',
            name='商业发票',
            version='1.0',
            content='<html>...</html>',
            is_system=True
        )
        self.assertEqual(template.code, 'commercial_invoice')
        self.assertTrue(template.is_system)

    def test_template_code_choices(self):
        template = DocumentTemplate.objects.create(
            code='commercial_invoice',
            name='商业发票',
            content='<html>...</html>'
        )
        self.assertEqual(template.get_code_display(), '商业发票')


class TemplateFieldTest(TestCase):
    def test_create_field(self):
        template = DocumentTemplate.objects.create(
            code='commercial_invoice',
            name='商业发票',
            content='<html>...</html>'
        )
        field = TemplateField.objects.create(
            template=template,
            field_name='invoice_no',
            label='发票编号',
            field_type='text',
            required=True
        )
        self.assertEqual(field.field_name, 'invoice_no')
        self.assertTrue(field.required)


class DocumentDependencyTest(TestCase):
    def test_create_dependency(self):
        dep = DocumentDependency.objects.create(
            document_type='packing_list',
            depends_on='commercial_invoice',
            dependency_type='sequential'
        )
        self.assertEqual(dep.document_type, 'packing_list')
        self.assertEqual(dep.depends_on, 'commercial_invoice')

    def test_circular_dependency_detection(self):
        DocumentDependency.objects.create(
            document_type='packing_list',
            depends_on='commercial_invoice'
        )
        DocumentDependency.objects.create(
            document_type='commercial_invoice',
            depends_on='packing_list'
        )
        # 后续实现循环检测方法


class DocumentTest(TestCase):
    def test_create_document(self):
        template = DocumentTemplate.objects.create(
            code='commercial_invoice',
            name='商业发票',
            content='<html>...</html>'
        )
        user = get_user_model().objects.create_user(username='test', password='pass')
        doc = Document.objects.create(
            template=template,
            created_by=user,
            data={'invoice_no': 'INV001'}
        )
        self.assertEqual(doc.status, 'draft')
        self.assertEqual(doc.data['invoice_no'], 'INV001')

    def test_document_status_transition(self):
        template = DocumentTemplate.objects.create(
            code='commercial_invoice',
            name='商业发票',
            content='<html>...</html>'
        )
        user = get_user_model().objects.create_user(username='test', password='pass')
        doc = Document.objects.create(template=template, created_by=user)

        doc.status = 'pending_review'
        doc.save()
        self.assertEqual(doc.get_status_display(), '待审核')


class DocumentValidationTest(TestCase):
    def test_create_validation(self):
        template = DocumentTemplate.objects.create(
            code='commercial_invoice',
            name='商业发票',
            content='<html>...</html>'
        )
        user = get_user_model().objects.create_user(username='test', password='pass')
        doc = Document.objects.create(template=template, created_by=user)

        validation = DocumentValidation.objects.create(
            document=doc,
            rule='date_logic',
            passed=True,
            validation_type='auto'
        )
        self.assertEqual(validation.rule, 'date_logic')
        self.assertTrue(validation.passed)


class DocumentTeachingClassTest(TestCase):
    def test_document_can_link_teaching_class(self):
        from apps.documents.models import Document, DocumentTemplate
        doc = Document.objects.create(
            template=DocumentTemplate.objects.create(
                code='test_tc', name='测试', content='<p></p>'
            ),
            data='{}',
        )
        # teaching_class 应该是可空的
        self.assertIsNone(doc.teaching_class)