# 单证管理三级权限设计

## Context

单证管理页面无法查到样本数据。根因：`DocumentViewSet` 只返回 `created_by=request.user` 的记录，而样本数据 `created_by=None`。

同时，系统缺少基于角色的文档可见性设计：
- Admin 应看到所有单证
- Teacher 应只看到自己班级学生产生的课堂相关单证
- Student 应只看到自己的单证

## 方案

给 Document 模型增加 `teaching_class` FK，实现三级权限查询。

### 1. Model 变更

**文件**: `apps/documents/models.py`

Document 模型新增字段：

```python
teaching_class = models.ForeignKey(
    'teaching.TeachingClass',
    on_delete=models.SET_NULL,
    null=True, blank=True,
    related_name='documents',
    verbose_name='所属班级',
)
```

- 可空——样本数据和课堂外单证 `teaching_class=None`
- `SET_NULL`——班级删除后单证保留
- 需要生成 migration

### 2. 自动填入 teaching_class

**文件**: `apps/documents/views.py` — `DocumentViewSet.create()`

学生创建单证时，自动从活跃选课记录填入 `teaching_class`：

```python
from apps.teaching.models import StudentEnrollment

enrollment = StudentEnrollment.objects.filter(
    student=request.user,
    status='enrolled',
).select_related('teaching_class').first()

if enrollment:
    document.teaching_class = enrollment.teaching_class
```

- 取第一条活跃选课记录
- 无选课记录则 `teaching_class` 保持 `None`

### 3. 查询权限

**文件**: `apps/documents/views.py` — `DocumentViewSet.get_queryset()`

```
admin   → Document.objects.all()
teacher → Document.objects.filter(teaching_class__course__teachers=request.user)
student → Document.objects.filter(created_by=request.user)
```

- 都支持额外 `transaction_id` 参数过滤
- teacher/admin 支持 `teaching_class_id` 参数按班级过滤
- 去掉之前的 `all=1` query param hack

### 4. API 参数

| 参数 | 说明 | 适用角色 |
|------|------|---------|
| `transaction_id` | 按交易 ID 过滤 | 全部 |
| `teaching_class_id` | 按班级过滤 | teacher/admin |

前端无需改动。

### 5. 样本数据

`init_sample_trade` 创建的样本单证保持 `teaching_class=None`：
- Admin 可见（查全部）
- Teacher 不可见（只查有班级的）
- Student 不可见（只查 `created_by=自己`）

## 涉及文件

- `apps/documents/models.py` — 新增 `teaching_class` 字段
- `apps/documents/views.py` — 修改 `get_queryset()` 和 `create()`
- `apps/documents/migrations/0005_*.py` — 新 migration

## 验证

1. 运行 `python manage.py makemigrations documents` 确认 migration 生成
2. 运行 `python manage.py migrate` 确认无报错
3. Student 用户创建单证，确认 `teaching_class` 自动填入
4. Admin 访问 `/api/v1/documents/documents/` 确认返回全部单证
5. Teacher 访问 API 确认只返回自己班级的单证
6. Student 访问 API 确认只返回自己的单证
