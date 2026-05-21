"""
单证自动校验规则引擎

实现单证数据的自动校验规则，包括：
- 日期逻辑校验
- 金额一致性校验
- 数量一致性校验
- 必填字段校验
"""
import json
from datetime import datetime
from typing import Dict, List, Any
from apps.documents.models import Document, DocumentValidation


class DocumentValidator:
    """单证校验器"""

    # 商业发票必填字段
    REQUIRED_FIELDS_COMMERCIAL_INVOICE = [
        'invoice_no',        # 发票编号
        'invoice_date',      # 发票日期
        'buyer_name',        # 买方名称
        'seller_name',       # 卖方名称
        'invoice_amount',    # 发票金额
        'currency',          # 币种
    ]

    # 装箱单必填字段
    REQUIRED_FIELDS_PACKING_LIST = [
        'packing_list_no',   # 装箱单编号
        'packing_date',      # 装箱日期
        'quantity',          # 数量
        'net_weight',        # 净重
        'gross_weight',      # 毛重
    ]

    def __init__(self, document: Document):
        """
        初始化校验器

        Args:
            document: 要校验的单证对象
        """
        self.document = document
        self.data = self._parse_data()
        self.results = {}

    def _parse_data(self) -> Dict[str, Any]:
        """
        解析单证数据

        Returns:
            解析后的数据字典
        """
        if not self.document.data:
            return {}

        # 如果是字符串，尝试解析为 JSON
        if isinstance(self.document.data, str):
            try:
                return json.loads(self.document.data)
            except json.JSONDecodeError:
                return {}

        # 如果已经是字典，直接返回
        return self.document.data

    def validate_all(self) -> Dict[str, Dict[str, Any]]:
        """
        执行所有校验规则

        Returns:
            校验结果字典，格式为：
            {
                'rule_name': {
                    'passed': bool,
                    'errors': List[str]
                }
            }
        """
        self.results = {
            'date_logic': self._validate_date_logic(),
            'amount_consistency': self._validate_amount_consistency(),
            'quantity_consistency': self._validate_quantity_consistency(),
            'required_fields': self._validate_required_fields(),
        }

        return self.results

    def _validate_date_logic(self) -> Dict[str, Any]:
        """
        校验日期逻辑

        规则：
        - 发票日期 <= 装运日期
        - 装运日期 <= 保险日期

        Returns:
            {'passed': bool, 'errors': List[str]}
        """
        errors = []

        # 获取日期字段
        invoice_date_str = self.data.get('invoice_date')
        shipment_date_str = self.data.get('shipment_date')
        insurance_date_str = self.data.get('insurance_date')

        # 如果没有日期字段，跳过校验
        if not any([invoice_date_str, shipment_date_str, insurance_date_str]):
            return {'passed': True, 'errors': []}

        # 解析日期
        invoice_date = self._parse_date(invoice_date_str)
        shipment_date = self._parse_date(shipment_date_str)
        insurance_date = self._parse_date(insurance_date_str)

        # 校验：发票日期 <= 装运日期
        if invoice_date and shipment_date:
            if invoice_date > shipment_date:
                errors.append('发票日期不能晚于装运日期')

        # 校验：装运日期 <= 保险日期
        if shipment_date and insurance_date:
            if shipment_date > insurance_date:
                errors.append('装运日期不能晚于保险日期')

        return {
            'passed': len(errors) == 0,
            'errors': errors
        }

    def _validate_amount_consistency(self) -> Dict[str, Any]:
        """
        校验金额一致性

        规则：
        - 发票金额 = 汇票金额
        - 保险金额 >= 发票金额 × 1.1

        Returns:
            {'passed': bool, 'errors': List[str]}
        """
        errors = []

        # 获取金额字段
        invoice_amount = self._parse_amount(self.data.get('invoice_amount'))
        draft_amount = self._parse_amount(self.data.get('draft_amount'))
        insurance_amount = self._parse_amount(self.data.get('insurance_amount'))

        # 校验：发票金额 = 汇票金额
        if invoice_amount is not None and draft_amount is not None:
            if abs(invoice_amount - draft_amount) > 0.01:  # 允许 0.01 的浮点误差
                errors.append(f'发票金额必须等于汇票金额（当前：发票 {invoice_amount}，汇票 {draft_amount}）')

        # 校验：保险金额 >= 发票金额 × 1.1
        if invoice_amount is not None and insurance_amount is not None:
            min_insurance = invoice_amount * 1.1
            if insurance_amount < min_insurance:
                errors.append(
                    f'保险金额应至少为发票金额的110%（当前：保险 {insurance_amount}，最低要求 {min_insurance:.2f}）'
                )

        return {
            'passed': len(errors) == 0,
            'errors': errors
        }

    def _validate_quantity_consistency(self) -> Dict[str, Any]:
        """
        校验数量一致性

        规则：
        - 净重 <= 毛重
        - 各单证数量一致（需要跨单证校验，暂时只校验单证内部）

        Returns:
            {'passed': bool, 'errors': List[str]}
        """
        errors = []

        # 获取重量字段
        net_weight = self._parse_amount(self.data.get('net_weight'))
        gross_weight = self._parse_amount(self.data.get('gross_weight'))

        # 校验：净重 <= 毛重
        if net_weight is not None and gross_weight is not None:
            if net_weight > gross_weight:
                errors.append(f'净重不能大于毛重（当前：净重 {net_weight}，毛重 {gross_weight}）')

        return {
            'passed': len(errors) == 0,
            'errors': errors
        }

    def _validate_required_fields(self) -> Dict[str, Any]:
        """
        校验必填字段

        根据单证类型校验必填字段

        Returns:
            {'passed': bool, 'errors': List[str]}
        """
        errors = []

        # 根据单证类型确定必填字段
        template_code = self.document.template.code if self.document.template else ''
        required_fields = []

        if template_code == 'commercial_invoice':
            required_fields = self.REQUIRED_FIELDS_COMMERCIAL_INVOICE
        elif template_code == 'packing_list':
            required_fields = self.REQUIRED_FIELDS_PACKING_LIST
        # 可以继续添加其他单证类型的必填字段

        # 检查必填字段是否存在
        for field in required_fields:
            value = self.data.get(field)
            if value is None or value == '':
                errors.append(f'缺少必填字段：{field}')

        return {
            'passed': len(errors) == 0,
            'errors': errors
        }

    def _parse_date(self, date_str: str) -> datetime:
        """
        解析日期字符串

        Args:
            date_str: 日期字符串

        Returns:
            datetime 对象，解析失败返回 None
        """
        if not date_str:
            return None

        # 尝试多种日期格式
        formats = [
            '%Y-%m-%d',
            '%Y/%m/%d',
            '%d-%m-%Y',
            '%d/%m/%Y',
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except (ValueError, TypeError):
                continue

        return None

    def _parse_amount(self, amount) -> float:
        """
        解析金额

        Args:
            amount: 金额值（可能是字符串、数字等）

        Returns:
            浮点数金额，解析失败返回 None
        """
        if amount is None:
            return None

        if isinstance(amount, (int, float)):
            return float(amount)

        if isinstance(amount, str):
            try:
                # 移除可能的货币符号和逗号
                cleaned = amount.replace(',', '').replace('$', '').replace('¥', '').strip()
                return float(cleaned)
            except ValueError:
                return None

        return None

    def save_results(self):
        """
        保存校验结果到数据库

        创建 DocumentValidation 记录，并更新 Document.auto_validation_result
        """
        # 先执行校验
        if not self.results:
            self.validate_all()

        # 清除旧的自动校验记录
        DocumentValidation.objects.filter(
            document=self.document,
            validation_type=DocumentValidation.ValidationType.AUTO
        ).delete()

        # 为每个校验规则创建记录
        for rule_name, result in self.results.items():
            DocumentValidation.objects.create(
                document=self.document,
                rule=rule_name,
                passed=result['passed'],
                error_message='; '.join(result['errors']) if result['errors'] else '',
                score_deduction=0 if result['passed'] else 10,  # 不通过扣 10 分
                validation_type=DocumentValidation.ValidationType.AUTO
            )

        # 保存汇总结果到 auto_validation_result
        summary = {
            'total_rules': len(self.results),
            'passed_rules': sum(1 for r in self.results.values() if r['passed']),
            'failed_rules': sum(1 for r in self.results.values() if not r['passed']),
            'all_passed': all(r['passed'] for r in self.results.values()),
            'details': self.results
        }

        self.document.auto_validation_result = json.dumps(summary, ensure_ascii=False)
        self.document.save()

        return summary
