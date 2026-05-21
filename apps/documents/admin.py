"""
Django admin configuration for Document models.
"""
from django.contrib import admin
from apps.documents.models import (
    Document, DocumentTemplate, TemplateField,
    DocumentDependency, DocumentValidation
)


@admin.register(DocumentTemplate)
class DocumentTemplateAdmin(admin.ModelAdmin):
    """单证模板管理"""
    list_display = ['code', 'name', 'version', 'is_system', 'is_active', 'created_at']
    list_filter = ['is_system', 'is_active', 'created_at']
    search_fields = ['code', 'name']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(TemplateField)
class TemplateFieldAdmin(admin.ModelAdmin):
    """模板字段管理"""
    list_display = ['template', 'field_name', 'label', 'field_type', 'required', 'sort_order']
    list_filter = ['field_type', 'required', 'template']
    search_fields = ['field_name', 'label']


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    """单证管理"""
    list_display = ['id', 'template_code', 'template_name', 'status', 'created_by', 'created_at']
    list_filter = ['status', 'template', 'created_at']
    search_fields = ['created_by__username']
    readonly_fields = ['auto_validation_result', 'created_at', 'updated_at']

    def template_code(self, obj):
        return obj.template.code if obj.template else '-'
    template_code.short_description = '单证代码'

    def template_name(self, obj):
        return obj.template.name if obj.template else '-'
    template_name.short_description = '单证名称'

    def get_readonly_fields(self, request, obj=None):
        readonly = ['auto_validation_result', 'created_at', 'updated_at']
        if obj and obj.status != 'draft':
            readonly.extend(['template', 'data'])
        return readonly


@admin.register(DocumentDependency)
class DocumentDependencyAdmin(admin.ModelAdmin):
    """单证依赖管理"""
    list_display = ['document_type', 'depends_on', 'dependency_type', 'is_required']
    list_filter = ['dependency_type', 'is_required']


@admin.register(DocumentValidation)
class DocumentValidationAdmin(admin.ModelAdmin):
    """单证校验记录管理"""
    list_display = ['document', 'rule', 'passed', 'validation_type', 'created_at']
    list_filter = ['passed', 'validation_type', 'rule']
    readonly_fields = ['created_at']
