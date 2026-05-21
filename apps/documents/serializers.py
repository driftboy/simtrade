"""
Serializers for Document models.
"""
from rest_framework import serializers
from apps.documents.models import (
    Document, DocumentTemplate, TemplateField,
    DocumentDependency, DocumentValidation
)
from apps.users.serializers import UserSerializer


class TemplateFieldSerializer(serializers.ModelSerializer):
    """模板字段序列化器"""

    class Meta:
        model = TemplateField
        fields = ['id', 'field_name', 'label', 'field_type',
                  'required', 'default_value', 'help_text', 'sort_order']


class DocumentTemplateSerializer(serializers.ModelSerializer):
    """单证模板序列化器"""
    fields = TemplateFieldSerializer(many=True, read_only=True)
    created_by = UserSerializer(read_only=True)

    class Meta:
        model = DocumentTemplate
        fields = ['id', 'code', 'name', 'version', 'is_system',
                  'is_active', 'created_by', 'created_at', 'fields']
        read_only_fields = ['id', 'created_at']


class DocumentValidationSerializer(serializers.ModelSerializer):
    """单证校验记录序列化器"""

    class Meta:
        model = DocumentValidation
        fields = ['id', 'rule', 'passed', 'error_message',
                  'score_deduction', 'validation_type', 'created_at']


class DocumentSerializer(serializers.ModelSerializer):
    """单证序列化器"""
    template_name = serializers.CharField(source='template.name', read_only=True)
    template_code = serializers.CharField(source='template.code', read_only=True)
    created_by = UserSerializer(read_only=True)
    reviewed_by = UserSerializer(read_only=True)
    validations = DocumentValidationSerializer(many=True, read_only=True)

    class Meta:
        model = Document
        fields = ['id', 'template', 'template_name', 'template_code',
                  'status', 'data', 'created_by', 'reviewed_by',
                  'auto_validation_result', 'manual_review_status',
                  'manual_review_comment', 'submitted_at', 'reviewed_at',
                  'created_at', 'updated_at', 'validations']
        read_only_fields = ['id', 'created_at', 'updated_at', 'auto_validation_result']


class DocumentCreateSerializer(serializers.ModelSerializer):
    """创建单证序列化器（简化版）"""

    class Meta:
        model = Document
        fields = ['template', 'data']

    def validate_template(self, value):
        """验证模板是否启用"""
        if not value.is_active:
            raise serializers.ValidationError('该单证模板未启用')
        return value


class DocumentSubmitSerializer(serializers.Serializer):
    """提交审核序列化器"""
    comment = serializers.CharField(required=False, allow_blank=True)
