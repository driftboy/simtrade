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
