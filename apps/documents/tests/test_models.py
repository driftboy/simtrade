import pytest
from django.test import TestCase
from apps.documents.models import DocumentTemplate, TemplateField, DocumentDependency


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