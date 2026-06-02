# 单证列表分页功能设计文档

**创建日期：** 2026-06-02
**状态：** 待实现

---

## 1. 概述

为单证管理列表添加分页功能，允许用户控制每页显示的单证数量，提升用户体验和系统性能。

### 1.1 目标

- 实现服务端分页，避免一次性加载大量数据
- 提供灵活的每页显示数量选项（5, 10, 20, 50）
- 记住用户的分页偏好设置
- 在列表顶部和底部都显示分页控件

### 1.2 范围

- 后端：DRF 分页实现 + 用户偏好设置存储
- 前端：分页控件 UI + JavaScript 逻辑
- 仅限单证列表页面（`/documents/list/`）

---

## 2. 架构设计

### 2.1 技术选型

使用 Django REST Framework 内置的 `PageNumberPagination` 类，原因：
- 成熟稳定，减少自定义代码
- 标准化的分页响应格式
- 易于维护和扩展

### 2.2 系统架构

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Browser UI    │────▶│     API         │────▶│    Database     │
│                 │◀────│                 │◀────│                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
│                       │
│ - 分页控件             │ - DocumentPagination
│ - AJAX 请求           │ - 偏好设置 API
│ - localStorage 状态    │ - 偏好设置存储
└───────────────────────┴───────────────────────
```

---

## 3. 后端设计

### 3.1 分页配置

**文件：** `apps/documents/pagination.py`

```python
from rest_framework.pagination import PageNumberPagination

class DocumentPagination(PageNumberPagination):
    page_size = 5                    # 默认每页5条
    page_size_query_param = 'page_size'  # URL参数名
    max_page_size = 50               # 最大每页50条
```

### 3.2 视图修改

**文件：** `apps/documents/views.py`

为 `DocumentViewSet` 添加分页配置：

```python
from apps.documents.pagination import DocumentPagination

class DocumentViewSet(ModelViewSet):
    pagination_class = DocumentPagination
    # ... 其他配置
```

移除自定义的 `list` 方法，使用 DRF 默认的分页列表响应。

### 3.3 用户偏好设置

**模型扩展：** `apps/users/models.py`

```python
class User(AbstractUser):
    # ... 现有字段
    documents_per_page = models.PositiveIntegerField(
        default=5,
        validators=[MinValueValidator(5), MaxValueValidator(50)]
    )
```

**API 端点：** `apps/users/serializers.py` 和 `views.py`

```python
# PUT /api/v1/users/preferences/
{
    "documents_per_page": 10
}
```

### 3.4 API 响应格式

```
GET /api/v1/documents/documents/?page=2&page_size=10

Response:
{
  "code": 0,
  "message": "success",
  "data": {
    "count": 25,
    "next": "...?page=3&page_size=10",
    "previous": "...?page=1&page_size=10",
    "results": [...]
  }
}
```

---

## 4. 前端设计

### 4.1 分页控件 HTML

位置：列表顶部和底部

```html
<div class="pagination-controls">
  <div class="row">
    <div class="col-md-4">
      <select id="pageSizeSelect" class="form-control">
        <option value="5">每页 5 条</option>
        <option value="10">每页 10 条</option>
        <option value="20">每页 20 条</option>
        <option value="50">每页 50 条</option>
      </select>
    </div>
    <div class="col-md-8 text-right">
      <span id="pageInfo">第 1 / 5 页，共 25 条</span>
      <button id="firstPage" class="btn btn-sm btn-default">首页</button>
      <button id="prevPage" class="btn btn-sm btn-default">上一页</button>
      <button id="nextPage" class="btn btn-sm btn-default">下一页</button>
      <button id="lastPage" class="btn btn-sm btn-default">末页</button>
    </div>
  </div>
</div>
```

### 4.2 JavaScript 逻辑

**文件：** `templates/documents/list.html`

功能：
1. 初始化：加载用户偏好设置
2. 翻页：更新 URL 参数并重新请求数据
3. 每页条数变化：保存到后端并刷新
4. 按钮状态：根据是否有下一页/上一页启用/禁用

```javascript
// 状态管理
var state = {
    page: 1,
    pageSize: 5,
    totalPages: 1,
    totalCount: 0
};

// 加载数据
function loadDocuments(page, pageSize) {
    $.ajax({
        url: '/api/v1/documents/documents/',
        data: { page: page, page_size: pageSize },
        success: function(response) {
            state.page = page;
            state.pageSize = pageSize;
            state.totalCount = response.data.count;
            state.totalPages = Math.ceil(state.totalCount / pageSize);
            renderList(response.data.results);
            renderPagination();
        }
    });
}

// 保存偏好设置
function savePreference(pageSize) {
    $.ajax({
        url: '/api/v1/users/preferences/',
        method: 'PUT',
        data: { documents_per_page: pageSize }
    });
}
```

---

## 5. 数据库迁移

需要创建迁移文件：

```python
# apps/users/migrations/XXXX_add_documents_per_page_preference.py

class Migration(migrations.Migration):
    dependencies = [
        ('users', '初始迁移文件'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='documents_per_page',
            field=models.PositiveIntegerField(default=5),
        ),
    ]
```

---

## 6. 错误处理

| 场景 | 处理方式 |
|------|---------|
| 页码超出范围 | 返回第一页或最后一页数据 |
| 无效的 page_size | 使用默认值 5 |
| API 失败 | 显示错误提示，禁用分页控件 |
| 网络超时 | 显示重试按钮 |

---

## 7. 测试要点

1. **分页功能**：验证每页显示正确的记录数
2. **翻页操作**：验证首页、上一页、下一页、末页按钮
3. **每页条数切换**：验证切换后数据正确刷新
4. **偏好保存**：刷新页面后保持用户选择的每页条数
5. **边界情况**：最后一页、空列表、单条记录

---

## 8. 实施顺序

1. 创建 `pagination.py` 和分页类
2. 修改 `DocumentViewSet` 启用分页
3. 创建用户模型迁移并添加 `documents_per_page` 字段
4. 创建偏好设置 API
5. 修改前端模板添加分页控件 HTML
6. 实现前端 JavaScript 分页逻辑
7. 样式调整和测试
