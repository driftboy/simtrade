from apps.documents.models import DocumentTemplate, DocumentDependency, Document


class DependencyService:
    """单证依赖检查服务"""

    def __init__(self, user):
        self.user = user

    def can_create(self, document_type, transaction_id=None):
        """
        检查是否可以创建指定类型的单证

        返回: (can_create: bool, message: str)
        """
        # 获取该单证的所有依赖
        dependencies = DocumentDependency.objects.filter(
            document_type=document_type
        )

        if not dependencies.exists():
            return True, ''

        # 检查每个依赖是否满足
        missing_deps = []
        for dep in dependencies:
            if not self._check_dependency(dep, transaction_id):
                template = DocumentTemplate.objects.filter(
                    code=dep.depends_on
                ).first()
                if template:
                    missing_deps.append(template.name)

        if missing_deps:
            return False, f'需要先完成以下单证：{", ".join(missing_deps)}'

        return True, ''

    def _check_dependency(self, dependency, transaction_id=None):
        """检查单个依赖是否满足"""
        # 如果没有 user，表示仅获取全局顺序，跳过检查
        if not self.user:
            return True

        # 查找用户已完成的依赖单证
        query = Document.objects.filter(
            created_by=self.user,
            template__code=dependency.depends_on
        )

        if transaction_id:
            query = query.filter(transaction_id=transaction_id)

        # 检查是否有已审核通过的单证
        return query.filter(
            status__in=[Document.Status.APPROVED, Document.Status.ARCHIVED]
        ).exists()

    def get_creation_order(self):
        """获取所有单证的推荐创建顺序（拓扑排序）"""
        # 获取所有单证类型
        all_types = list(DocumentTemplate.objects.filter(
            is_active=True
        ).values_list('code', flat=True))

        # 获取所有依赖关系
        dependencies = DocumentDependency.objects.all()

        # 构建依赖图
        graph = {t: set() for t in all_types}
        in_degree = {t: 0 for t in all_types}

        for dep in dependencies:
            if dep.depends_on in graph and dep.document_type in graph:
                graph[dep.depends_on].add(dep.document_type)
                in_degree[dep.document_type] += 1

        # 拓扑排序
        order = []
        queue = [t for t in all_types if in_degree[t] == 0]

        while queue:
            node = queue.pop(0)
            order.append(node)

            for neighbor in graph[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        return order

    def get_next_available(self, transaction_id=None):
        """获取用户当前可以创建的单证类型列表"""
        all_types = DocumentTemplate.objects.filter(is_active=True)
        available = []

        for template in all_types:
            can_create, _ = self.can_create(template.code, transaction_id)
            if can_create:
                available.append({
                    'code': template.code,
                    'name': template.name,
                })

        return available


class DataFillService:
    """单证数据智能填充服务"""

    # 字段映射配置：从交易/已有单证到目标单证的映射
    # 格式：'target_field': 'source_field'
    FIELD_MAPPINGS = {
        'packing_list': {
            'invoice_no': 'invoice_no',
            'buyer_name': 'buyer_name',
            'seller_name': 'seller_name',
            'invoice_quantity': 'quantity',
            'amount': 'amount',
        },
        'bill_of_exchange': {
            'invoice_no': 'invoice_no',
            'buyer_name': 'payee_name',
            'amount': 'amount',
        },
        'insurance_application': {
            'invoice_no': 'invoice_no',
            'buyer_name': 'applicant',
            'amount': 'insured_amount',
        },
    }

    def fill_from_transaction(self, document_type, transaction_data):
        """
        从交易数据填充单证

        Args:
            document_type: 单证类型
            transaction_data: 交易数据字典

        Returns:
            填充后的单证数据字典
        """
        filled_data = {}

        # 根据单证类型填充默认字段
        if document_type == 'commercial_invoice':
            filled_data = {
                'buyer_name': transaction_data.get('buyer_name'),
                'seller_name': transaction_data.get('seller_name'),
                'amount': transaction_data.get('amount'),
                'quantity': transaction_data.get('quantity'),
                'product_name': transaction_data.get('product_name'),
                'invoice_date': transaction_data.get('contract_date'),
            }
        elif document_type == 'packing_list':
            filled_data = {
                'buyer_name': transaction_data.get('buyer_name'),
                'seller_name': transaction_data.get('seller_name'),
                'quantity': transaction_data.get('quantity'),
                'product_name': transaction_data.get('product_name'),
            }

        return filled_data

    def fill_from_document(self, document_type, source_document):
        """
        从已有单证填充数据

        Args:
            document_type: 目标单证类型
            source_document: 源单证实例

        Returns:
            填充后的单证数据字典
        """
        import json

        mappings = self.FIELD_MAPPINGS.get(document_type, {})
        filled_data = {}

        # 解析源单证数据（可能是 JSON 字符串或字典）
        if isinstance(source_document.data, str):
            try:
                source_data = json.loads(source_document.data)
            except:
                source_data = {}
        else:
            source_data = source_document.data

        for target_field, source_field in mappings.items():
            if source_field in source_data:
                filled_data[target_field] = source_data[source_field]

        return filled_data

    def fill_defaults(self, document_type):
        """
        填充默认值

        Args:
            document_type: 单证类型

        Returns:
            包含默认值的字典
        """
        from datetime import date

        defaults = {
            'invoice_date': str(date.today()),
            'currency': 'USD',
        }

        # 根据单证类型添加特定默认值
        if document_type == 'commercial_invoice':
            defaults.update({
                'trade_term': 'FOB',
                'payment_term': 'L/C',
            })

        return defaults
