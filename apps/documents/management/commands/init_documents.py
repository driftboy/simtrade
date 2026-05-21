"""
Django management command to initialize document system data.
"""
from django.core.management.base import BaseCommand
from django.core.management import call_command
from apps.documents.models import DocumentTemplate, TemplateField


class Command(BaseCommand):
    help = '初始化单证系统数据'

    def handle(self, *args, **options):
        self.stdout.write('开始初始化单证系统数据...')

        # 加载依赖关系
        try:
            call_command('loaddata', 'dependencies', app_label='documents')
            self.stdout.write(self.style.SUCCESS('  [OK] 单证依赖关系加载完成'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  [FAIL] 加载失败: {e}'))

        # 创建标准单证模板
        templates_data = [
            ('commercial_invoice', '商业发票', self._get_invoice_template(), self._get_invoice_fields()),
            ('packing_list', '装箱单', self._get_packing_list_template(), self._get_packing_list_fields()),
            ('bill_of_exchange', '汇票', self._get_draft_template(), self._get_draft_fields()),
            ('sales_contract', '外销合同', self._get_contract_template(), []),
            ('letter_of_credit', '信用证', self._get_lc_template(), self._get_lc_fields()),
            ('bill_of_lading', '海运提单', self._get_bl_template(), self._get_bl_fields()),
            ('insurance_policy', '保险单', self._get_policy_template(), self._get_policy_fields()),
            ('insurance_application', '投保单', self._get_application_template(), []),
            ('export_declaration', '出口报关单', self._get_declaration_template(), []),
            ('import_declaration', '进口报关单', self._get_import_declaration_template(), []),
            ('inspection_application', '报检单', self._get_inspection_app_template(), []),
            ('inspection_certificate', '检验证书', self._get_inspection_cert_template(), []),
            ('certificate_of_origin', '产地证', self._get_origin_template(), []),
            ('beneficiary_certificate', '受益人证明', self._get_beneficiary_template(), []),
            ('shipping_advice', '装船通知', self._get_shipping_advice_template(), []),
        ]

        for code, name, content, fields in templates_data:
            template, created = DocumentTemplate.objects.get_or_create(
                code=code,
                defaults={
                    'name': name,
                    'content': content,
                    'is_system': True
                }
            )
            if created:
                self._create_template_fields(template, fields)
                self.stdout.write(self.style.SUCCESS(f'  [OK] 创建模板: {name}'))
            else:
                self.stdout.write(f'  [SKIP] 模板已存在: {name}')

        self.stdout.write(self.style.SUCCESS('\n单证系统初始化完成！'))

    def _get_invoice_template(self):
        return '''<div class="invoice" style="font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto;">
    <h2 style="text-align: center;">商业发票</h2>
    <table style="width: 100%; border-collapse: collapse;">
        <tr><td style="border: 1px solid #ccc; padding: 8px;">发票编号</td><td style="border: 1px solid #ccc; padding: 8px;">{{invoice_no}}</td></tr>
        <tr><td style="border: 1px solid #ccc; padding: 8px;">发票日期</td><td style="border: 1px solid #ccc; padding: 8px;">{{invoice_date}}</td></tr>
        <tr><td style="border: 1px solid #ccc; padding: 8px;">买方</td><td style="border: 1px solid #ccc; padding: 8px;">{{buyer_name}}</td></tr>
        <tr><td style="border: 1px solid #ccc; padding: 8px;">卖方</td><td style="border: 1px solid #ccc; padding: 8px;">{{seller_name}}</td></tr>
        <tr><td style="border: 1px solid #ccc; padding: 8px;">金额</td><td style="border: 1px solid #ccc; padding: 8px;">{{invoice_amount}} {{currency}}</td></tr>
    </table>
</div>'''

    def _get_invoice_fields(self):
        return [
            ('invoice_no', '发票编号', 'text', True),
            ('invoice_date', '发票日期', 'date', True),
            ('buyer_name', '买方名称', 'text', True),
            ('buyer_address', '买方地址', 'textarea', False),
            ('seller_name', '卖方名称', 'text', True),
            ('seller_address', '卖方地址', 'textarea', False),
            ('invoice_amount', '发票金额', 'decimal', True),
            ('currency', '币种', 'currency', True),
            ('trade_term', '贸易术语', 'text', False),
            ('payment_term', '付款方式', 'text', False),
        ]

    def _get_packing_list_template(self):
        return '''<div class="packing-list" style="font-family: Arial, sans-serif;">
    <h2 style="text-align: center;">装箱单</h2>
    <table style="width: 100%; border-collapse: collapse;">
        <tr><td style="border: 1px solid #ccc; padding: 8px;">装箱单编号</td><td style="border: 1px solid #ccc; padding: 8px;">{{packing_list_no}}</td></tr>
        <tr><td style="border: 1px solid #ccc; padding: 8px;">关联发票号</td><td style="border: 1px solid #ccc; padding: 8px;">{{invoice_no}}</td></tr>
        <tr><td style="border: 1px solid #ccc; padding: 8px;">数量</td><td style="border: 1px solid #ccc; padding: 8px;">{{quantity}}</td></tr>
        <tr><td style="border: 1px solid #ccc; padding: 8px;">净重</td><td style="border: 1px solid #ccc; padding: 8px;">{{net_weight}}</td></tr>
        <tr><td style="border: 1px solid #ccc; padding: 8px;">毛重</td><td style="border: 1px solid #ccc; padding: 8px;">{{gross_weight}}</td></tr>
    </table>
</div>'''

    def _get_packing_list_fields(self):
        return [
            ('packing_list_no', '装箱单编号', 'text', True),
            ('invoice_no', '关联发票号', 'text', True),
            ('packing_date', '装箱日期', 'date', True),
            ('quantity', '数量', 'number', True),
            ('net_weight', '净重', 'decimal', True),
            ('gross_weight', '毛重', 'decimal', True),
            ('package_type', '包装类型', 'text', False),
        ]

    def _get_draft_template(self):
        return '<div class="draft"><h2>汇票</h2><p>号码: {{draft_no}}</p><p>金额: {{draft_amount}}</p></div>'

    def _get_draft_fields(self):
        return [
            ('draft_no', '汇票编号', 'text', True),
            ('draft_date', '汇票日期', 'date', True),
            ('draft_amount', '汇票金额', 'decimal', True),
            ('payee', '收款人', 'text', True),
        ]

    def _get_contract_template(self):
        return '<div class="contract"><h2>外销合同</h2><p>合同号: {{contract_no}}</p></div>'

    def _get_lc_template(self):
        return '<div class="lc"><h2>信用证</h2><p>信用证号: {{lc_no}}</p><p>开证日期: {{lc_issue_date}}</p></div>'

    def _get_lc_fields(self):
        return [
            ('lc_no', '信用证编号', 'text', True),
            ('lc_issue_date', '开证日期', 'date', True),
            ('issuing_bank', '开证行', 'text', True),
        ]

    def _get_bl_template(self):
        return '<div class="bl"><h2>海运提单</h2><p>提单号: {{bl_no}}</p><p>装运港: {{port_of_loading}}</p></div>'

    def _get_bl_fields(self):
        return [
            ('bl_no', '提单号', 'text', True),
            ('port_of_loading', '装运港', 'port', True),
            ('port_of_discharge', '卸货港', 'port', True),
        ]

    def _get_policy_template(self):
        return '<div class="policy"><h2>保险单</h2><p>保单号: {{policy_no}}</p></div>'

    def _get_policy_fields(self):
        return [
            ('policy_no', '保单号', 'text', True),
            ('insurance_amount', '保险金额', 'decimal', True),
        ]

    def _get_application_template(self):
        return '<div class="application"><h2>投保单</h2></div>'

    def _get_declaration_template(self):
        return '<div class="declaration"><h2>出口报关单</h2></div>'

    def _get_import_declaration_template(self):
        return '<div class="import-declaration"><h2>进口报关单</h2></div>'

    def _get_inspection_app_template(self):
        return '<div class="inspection-app"><h2>报检单</h2></div>'

    def _get_inspection_cert_template(self):
        return '<div class="inspection-cert"><h2>检验证书</h2></div>'

    def _get_origin_template(self):
        return '<div class="origin"><h2>产地证</h2></div>'

    def _get_beneficiary_template(self):
        return '<div class="beneficiary"><h2>受益人证明</h2></div>'

    def _get_shipping_advice_template(self):
        return '<div class="shipping-advice"><h2>装船通知</h2></div>'

    def _create_template_fields(self, template, fields):
        """创建模板字段配置"""
        for i, (name, label, field_type, required) in enumerate(fields):
            TemplateField.objects.get_or_create(
                template=template,
                field_name=name,
                defaults={
                    'label': label,
                    'field_type': field_type,
                    'required': required,
                    'sort_order': i
                }
            )
