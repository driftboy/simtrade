# 单证列表分页功能实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 为单证管理列表添加服务端分页功能，支持每页 5/10/20/50 条可配置，分页控件在顶部和底部显示

**架构：** 使用 Django REST Framework 的 PageNumberPagination 实现服务端分页，用户偏好保存在 User 模型的 documents_per_page 字段中

**技术栈：** Django REST Framework, jQuery (已有), Bootstrap 3 (已有)

---

## 文件结构

### 将创建的文件

| 文件路径 | 职责 |
|---------|------|
| `apps/documents/pagination.py` | 自定义分页类配置 |
| `apps/users/serializers.py` (添加) | 用户偏好序列化器 |
| `apps/users/views.py` (添加) | 用户偏好 API 端点 |
| `apps/users/migrations/000X_add_documents_per_page.py` | 数据库迁移文件 |

### 将修改的文件

| 文件路径 | 修改内容 |
|---------|---------|
| `apps/documents/views.py` | 启用分页，移除自定义 list 方法 |
| `apps/documents/serializers.py` | 确保序列化器包含分页所需字段 |
| `templates/documents/list.html` | 添加分页控件 HTML 和 JavaScript 逻辑 |
| `apps/users/models.py` | 添加 documents_per_page 字段 |
| `apps/users/urls.py` | 添加偏好设置端点路由 |

---

## 任务 1：创建自定义分页类

**文件：**
- 创建：`apps/documents/pagination.py`

- [ ] **步骤 1：编写分页类代码**

创建 `apps/documents/pagination.py` 文件，内容如下：

```python
"""
Pagination configuration for Document API.
"""
from rest_framework.pagination import PageNumberPagination


class DocumentPagination(PageNumberPagination):
    """
    分页配置类 - 单证列表
    - 默认每页 5 条
    - 支持通过 URL 参数 page_size 自定义
    - 最大每页 50 条
    """
    page_size = 5
    page_size_query_param = 'page_size'
    max_page_size = 50
```

- [ ] **步骤 2：验证文件创建成功**

运行：`python manage.py check`
预期：无错误输出

- [ ] **步骤 3：Commit**

```bash
git add apps/documents/pagination.py
git commit -m "feat: add DocumentPagination class

- Add custom pagination with default 5 items per page
- Support page_size query param up to 50 max

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## 任务 2：扩展用户模型添加偏好字段

**文件：**
- 修改：`apps/users/models.py`
- 创建：`apps/users/migrations/000X_add_documents_per_page.py`

- [ ] **步骤 1：在 User 模型中添加字段**

在 `apps/users/models.py` 的 `User` 类中，在 `avatar` 字段后添加：

```python
documents_per_page = models.PositiveIntegerField(
    default=5,
    validators=[MinValueValidator(5), MaxValueValidator(50)],
    help_text='单证列表每页显示数量'
)
```

需要在文件顶部添加导入：
```python
from django.core.validators import MinValueValidator, MaxValueValidator
```

- [ ] **步骤 2：创建数据库迁移**

运行：`python manage.py makemigrations users`
预期：生成迁移文件，提示 "Add field documents_per_page to user"

- [ ] **步骤 3：应用迁移**

运行：`python manage.py migrate users`
预期：显示 "Running migrations" 和 "OK"

- [ ] **步骤 4：验证字段添加**

运行 Django shell：
```bash
python manage.py shell
```
执行：
```python
from django.contrib.auth import get_user_model
User = get_user_model()
u = User.objects.first()
print(u.documents_per_page)  # 应输出 5
```

- [ ] **步骤 5：Commit**

```bash
git add apps/users/models.py apps/users/migrations/
git commit -m "feat: add documents_per_page preference to User model

- Add field for user's preferred items per page (5/10/20/50)
- Default 5, validated between 5 and 50

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## 任务 3：创建用户偏好序列化器

**文件：**
- 修改：`apps/users/serializers.py`

- [ ] **步骤 1：添加偏好设置序列化器**

在 `apps/users/serializers.py` 文件末尾添加：

```python
class UserPreferenceSerializer(serializers.Serializer):
    """用户偏好设置序列化器"""
    documents_per_page = serializers.IntegerField(
        min_value=5,
        max_value=50,
        help_text='单证列表每页显示数量（5/10/20/50）'
    )

    def validate_documents_per_page(self, value):
        """验证每页条数必须是预定义选项之一"""
        valid_values = [5, 10, 20, 50]
        if value not in valid_values:
            raise serializers.ValidationError(
                f'每页显示数量必须是以下值之一: {valid_values}'
            )
        return value
```

- [ ] **步骤 2：更新 UserSerializer**

在 `UserSerializer` 的 `fields` 列表中添加 `'documents_per_page'`：

```python
class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model."""

    roles = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'user_type', 'phone',
            'student_id', 'avatar', 'documents_per_page',  # 添加此项
            'is_active', 'is_superuser', 'roles',
            'created_at', 'updated_at'
        ]
        # ... 其余保持不变
```

- [ ] **步骤 3：验证序列化器**

运行：`python manage.py check`
预期：无错误

- [ ] **步骤 4：Commit**

```bash
git add apps/users/serializers.py
git commit -m "feat: add UserPreferenceSerializer

- Add serializer for user preference settings
- Validate documents_per_page against allowed values
- Include documents_per_page in UserSerializer

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## 任务 4：创建用户偏好 API 端点

**文件：**
- 修改：`apps/users/views.py`
- 修改：`apps/users/urls.py`

- [ ] **步骤 1：在 views.py 中添加 CurrentUserView 的 PUT 方法**

在 `CurrentUserView` 类中添加 `put` 方法：

```python
def put(self, request):
    """
    Update current user preferences.

    Request body:
        documents_per_page: int - Items per page for document list

    Returns:
        200: Preferences updated successfully
            UserSerializer data
        400: Invalid input data
    """
    from apps.users.serializers import UserPreferenceSerializer

    serializer = UserPreferenceSerializer(data=request.data)
    if serializer.is_valid():
        # 更新用户偏好
        request.user.documents_per_page = serializer.validated_data['documents_per_page']
        request.user.save(update_fields=['documents_per_page'])

        # 返回更新后的用户信息
        user_serializer = UserSerializer(request.user)
        return Response({
            'code': 0,
            'message': '偏好设置已更新',
            'data': user_serializer.data
        }, status=status.HTTP_200_OK)

    return Response({
        'code': 4000,
        'message': '无效的偏好设置',
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)
```

- [ ] **步骤 2：验证视图修改**

运行：`python manage.py check`
预期：无错误

- [ ] **步骤 3：测试 API 端点（手动）**

启动服务器：`python manage.py runserver`

使用 curl 或 Postman 测试：
```bash
# 先登录获取 session
curl -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"your_password"}' \
  -c cookies.txt

# 测试偏好设置更新
curl -X PUT http://localhost:8000/api/v1/auth/me/ \
  -H "Content-Type: application/json" \
  -d '{"documents_per_page":10}' \
  -b cookies.txt
```

预期响应：
```json
{
  "code": 0,
  "message": "偏好设置已更新",
  "data": {
    "id": 1,
    "username": "admin",
    "documents_per_page": 10,
    ...
  }
}
```

- [ ] **步骤 4：Commit**

```bash
git add apps/users/views.py
git commit -m "feat: add user preferences API endpoint

- Add PUT method to CurrentUserView for updating preferences
- Support updating documents_per_page setting
- Return updated user data after successful update

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## 任务 5：启用 DocumentViewSet 分页

**文件：**
- 修改：`apps/documents/views.py`

- [ ] **步骤 1：添加分页类导入**

在文件顶部添加导入：

```python
from apps.documents.pagination import DocumentPagination
```

- [ ] **步骤 2：配置 DocumentViewSet 使用分页**

在 `DocumentViewSet` 类中添加 `pagination_class` 属性：

```python
class DocumentViewSet(ModelViewSet):
    """单证视图集"""
    permission_classes = [IsAuthenticated]
    pagination_class = DocumentPagination  # 添加此行
```

- [ ] **步骤 3：移除自定义 list 方法**

删除或注释掉整个 `list` 方法（第 54-62 行），因为 DRF 的默认分页列表已经满足需求。

- [ ] **步骤 4：验证分页配置**

运行：`python manage.py check`
预期：无错误

- [ ] **步骤 5：手动测试 API**

启动服务器，测试分页：

```bash
# 测试默认分页（第1页，每页5条）
curl http://localhost:8000/api/v1/documents/documents/ -b cookies.txt

# 测试指定页大小
curl "http://localhost:8000/api/v1/documents/documents/?page=2&page_size=10" -b cookies.txt
```

预期响应格式：
```json
{
  "count": 25,
  "next": "http://localhost:8000/api/v1/documents/documents/?page=2&page_size=5",
  "previous": null,
  "results": [...]
}
```

- [ ] **步骤 6：Commit**

```bash
git add apps/documents/views.py
git commit -m "feat: enable pagination for DocumentViewSet

- Configure DocumentViewSet to use DocumentPagination
- Remove custom list method in favor of DRF default
- API now returns paginated response with count/next/previous/results

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## 任务 6：添加前端分页控件 HTML

**文件：**
- 修改：`templates/documents/list.html`

- [ ] **步骤 1：在筛选器后添加顶部分页控件**

在 `<!-- 筛选器 -->` 的闭合 `</div>` 后（约第 41 行），添加：

```html
<!-- 顶部分页控件 -->
<div id="paginationControlsTop" class="pagination-container" style="margin-bottom: 15px;"></div>
```

- [ ] **步骤 2：在列表后添加底部分页控件**

在 `<!-- 单证列表 -->` 的 `</div>` 后（约第 46 行），添加：

```html
<!-- 底部分页控件 -->
<div id="paginationControlsBottom" class="pagination-container" style="margin-top: 15px;"></div>
```

- [ ] **步骤 3：验证页面加载**

运行服务器，访问单证列表页面，检查页面结构正确。

- [ ] **步骤 4：Commit**

```bash
git add templates/documents/list.html
git commit -m "feat: add pagination control containers to document list

- Add top and bottom pagination control placeholders
- Controls will be rendered by JavaScript

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## 任务 7：实现前端分页 JavaScript 逻辑

**文件：**
- 修改：`templates/documents/list.html`

- [ ] **步骤 1：添加分页状态变量**

在 `<script>` 标签内，`$(document).ready()` 函数开头添加：

```javascript
// 分页状态
var paginationState = {
    currentPage: 1,
    pageSize: 5,
    totalCount: 0,
    totalPages: 1,
    nextUrl: null,
    previousUrl: null
};
```

- [ ] **步骤 2：添加分页控件渲染函数**

在 `getStatusClass` 函数后添加：

```javascript
// 渲染分页控件
function renderPaginationControls() {
    var controlsHtml = `
        <div class="row">
            <div class="col-md-4">
                <select id="pageSizeSelect" class="form-control input-sm">
                    <option value="5" ${paginationState.pageSize === 5 ? 'selected' : ''}>每页 5 条</option>
                    <option value="10" ${paginationState.pageSize === 10 ? 'selected' : ''}>每页 10 条</option>
                    <option value="20" ${paginationState.pageSize === 20 ? 'selected' : ''}>每页 20 条</option>
                    <option value="50" ${paginationState.pageSize === 50 ? 'selected' : ''}>每页 50 条</option>
                </select>
            </div>
            <div class="col-md-8 text-right">
                <span class="page-info" style="margin-right: 10px;">
                    第 ${paginationState.currentPage} / ${paginationState.totalPages} 页，共 ${paginationState.totalCount} 条
                </span>
                <button class="btn btn-sm btn-default" ${!paginationState.previousUrl ? 'disabled' : ''}>首页</button>
                <button class="btn btn-sm btn-default pagination-prev" ${!paginationState.previousUrl ? 'disabled' : ''}>上一页</button>
                <button class="btn btn-sm btn-default pagination-next" ${!paginationState.nextUrl ? 'disabled' : ''}>下一页</button>
                <button class="btn btn-sm btn-default pagination-last" ${!paginationState.nextUrl ? 'disabled' : ''}>末页</button>
            </div>
        </div>
    `;

    $('#paginationControlsTop').html(controlsHtml);
    $('#paginationControlsBottom').html(controlsHtml);

    // 绑定事件（仅顶部控件）
    $('#paginationControlsTop #pageSizeSelect').change(function() {
        var newSize = parseInt($(this).val());
        saveUserPreference(newSize);
    });

    $('#paginationControlsTop .pagination-prev').click(function() {
        if (paginationState.previousUrl) {
            loadPageFromUrl(paginationState.previousUrl);
        }
    });

    $('#paginationControlsTop .pagination-next').click(function() {
        if (paginationState.nextUrl) {
            loadPageFromUrl(paginationState.nextUrl);
        }
    });

    $('#paginationControlsTop button:contains("首页")').click(function() {
        loadPage(1);
    });

    $('#paginationControlsTop button:contains("末页")').click(function() {
        loadPage(paginationState.totalPages);
    });
}
```

- [ ] **步骤 3：修改 loadDocuments 函数支持分页**

替换整个 `loadDocuments` 函数为：

```javascript
function loadDocuments(page, pageSize, filters) {
    page = page || 1;
    pageSize = pageSize || paginationState.pageSize;
    filters = filters || {};

    var params = $.param(filters);
    var url = '/api/v1/documents/documents/?page=' + page + '&page_size=' + pageSize;
    if (params) {
        url += '&' + params;
    }

    $.ajax({
        url: url,
        method: 'GET',
        headers: {
            'X-CSRFToken': $.cookie('csrftoken')
        },
        success: function(response) {
            // 更新分页状态
            paginationState.currentPage = page;
            paginationState.pageSize = pageSize;
            paginationState.totalCount = response.count;
            paginationState.totalPages = Math.ceil(response.count / pageSize);
            paginationState.nextUrl = response.next ? extractPageFromUrl(response.next) : null;
            paginationState.previousUrl = response.previous ? extractPageFromUrl(response.previous) : null;

            // 渲染列表
            var html = '';
            var items = response.results || [];
            if (items.length === 0) {
                html = '<div class="alert alert-info">暂无单证</div>';
            } else {
                items.forEach(function(doc) {
                    var statusClass = getStatusClass(doc.status);
                    html += `
                        <div class="document-card">
                            <div class="row">
                                <div class="col-md-6">
                                    <h4>${doc.template_name}</h4>
                                    <p class="text-muted">创建时间: ${doc.created_at}</p>
                                    ${doc.transaction_id ? '<p>交易号: #' + doc.transaction_id + '</p>' : ''}
                                </div>
                                <div class="col-md-3">
                                    <span class="status-badge ${statusClass}">${doc.status_display}</span>
                                </div>
                                <div class="col-md-3 text-right">
                                    <a href="/documents/${doc.id}/preview/" class="btn btn-default btn-sm">预览</a>
                                    ${doc.status === 'draft' ? '<a href="/documents/' + doc.id + '/edit/" class="btn btn-primary btn-sm">编辑</a>' : ''}
                                </div>
                            </div>
                        </div>
                    `;
                });
            }
            $('#documentList').html(html);
            renderPaginationControls();
        },
        error: function(xhr) {
            var msg = '加载失败';
            if (xhr.status === 403) msg = '未登录或权限不足，请重新登录';
            else if (xhr.status === 0) msg = '网络错误，请检查连接';
            else if (xhr.responseText) {
                try { msg += ': ' + JSON.parse(xhr.responseText).detail; } catch(e) {}
            }
            $('#documentList').html('<div class="alert alert-danger">' + msg + '</div>');
        }
    });
}

// 从 URL 中提取页码
function extractPageFromUrl(url) {
    var match = url.match(/[?&]page=(\d+)/);
    return match ? parseInt(match[1]) : null;
}

// 加载指定页
function loadPage(pageNum) {
    loadDocuments(pageNum, paginationState.pageSize, getCurrentFilters());
}

// 从 URL 加载页面
function loadPageFromUrl(url) {
    if (!url) return;
    var page = extractPageFromUrl(url);
    if (page) {
        loadPage(page);
    }
}

// 获取当前筛选条件
function getCurrentFilters() {
    var filters = {};
    if ($('#filterType').val()) filters.template = $('#filterType').val();
    if ($('#filterStatus').val()) filters.status = $('#filterStatus').val();
    if ($('#filterTransaction').val()) filters.transaction_id = $('#filterTransaction').val();
    return filters;
}
```

- [ ] **步骤 4：添加用户偏好保存和加载函数**

在脚本末尾添加：

```javascript
// 保存用户偏好设置
function saveUserPreference(pageSize) {
    $.ajax({
        url: '/api/v1/auth/me/',
        method: 'PUT',
        headers: {
            'X-CSRFToken': $.cookie('csrftoken'),
            'Content-Type': 'application/json'
        },
        data: JSON.stringify({ documents_per_page: pageSize }),
        success: function(response) {
            // 保存成功，重新加载第一页
            loadDocuments(1, pageSize, getCurrentFilters());
        },
        error: function() {
            // 保存失败，仍使用新设置但仅本地生效
            loadDocuments(1, pageSize, getCurrentFilters());
        }
    });
}

// 加载用户偏好设置
function loadUserPreferences() {
    $.ajax({
        url: '/api/v1/auth/me/',
        method: 'GET',
        headers: {
            'X-CSRFToken': $.cookie('csrftoken')
        },
        success: function(response) {
            var userPref = response.data;
            if (userPref && userPref.documents_per_page) {
                paginationState.pageSize = userPref.documents_per_page;
            }
        },
        complete: function() {
            // 加载完偏好后加载列表
            var urlParams = getUrlParams();
            if (urlParams.status) $('#filterStatus').val(urlParams.status);
            if (urlParams.template) $('#filterType').val(urlParams.template);
            loadDocuments(1, paginationState.pageSize, urlParams);
        }
    });
}
```

- [ ] **步骤 5：修改初始化代码使用用户偏好**

将原有的初始化代码替换为：

```javascript
// 初始加载 - 先加载用户偏好
loadUserPreferences();
```

- [ ] **步骤 6：修改筛选按钮事件**

修改筛选按钮点击事件：

```javascript
$('#filterBtn').click(function() {
    var filters = getCurrentFilters();
    loadDocuments(1, paginationState.pageSize, filters);
});
```

- [ ] **步骤 7：验证页面功能**

运行服务器，访问单证列表页面，测试：
1. 分页控件显示在顶部和底部
2. 翻页按钮工作正常
3. 每页条数切换功能正常
4. 刷新页面后保持用户选择的每页条数

- [ ] **步骤 8：Commit**

```bash
git add templates/documents/list.html
git commit -m "feat: implement frontend pagination logic

- Add pagination state management
- Render top and bottom pagination controls
- Implement page navigation and page size selection
- Load and save user preferences via API
- Handle filter conditions with pagination

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## 任务 8：编写后端测试

**文件：**
- 创建：`apps/documents/tests/test_pagination.py`

- [ ] **步骤 1：创建分页测试文件**

创建 `apps/documents/tests/test_pagination.py`：

```python
"""
Tests for Document pagination functionality.
"""
from django.test import TestCase
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

from apps.documents.models import Document, DocumentTemplate

User = get_user_model()


class DocumentPaginationTestCase(TestCase):
    """测试单证分页功能"""

    def setUp(self):
        """创建测试数据"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass',
            user_type='student'
        )
        self.template = DocumentTemplate.objects.create(
            code='test_invoice',
            name='测试发票',
            content='<html></html>'
        )

        # 创建 15 条单证记录
        for i in range(15):
            Document.objects.create(
                template=self.template,
                created_by=self.user,
                status='draft'
            )

        self.client.force_authenticate(user=self.user)

    def test_default_page_size(self):
        """测试默认每页 5 条"""
        response = self.client.get('/api/v1/documents/documents/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 15)
        self.assertEqual(len(response.data['results']), 5)

    def test_custom_page_size(self):
        """测试自定义每页条数"""
        response = self.client.get(
            '/api/v1/documents/documents/?page_size=10'
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 10)

    def test_page_navigation(self):
        """测试翻页功能"""
        # 第一页
        response = self.client.get('/api/v1/documents/documents/?page=1')
        self.assertEqual(len(response.data['results']), 5)

        # 第二页
        response = self.client.get('/api/v1/documents/documents/?page=2')
        self.assertEqual(len(response.data['results']), 5)

        # 第三页（剩余 5 条）
        response = self.client.get('/api/v1/documents/documents/?page=3')
        self.assertEqual(len(response.data['results']), 5)

    def test_next_previous_urls(self):
        """测试 next 和 previous URL"""
        response = self.client.get('/api/v1/documents/documents/')
        self.assertIsNone(response.data['previous'])
        self.assertIsNotNone(response.data['next'])

    def test_max_page_size_limit(self):
        """测试最大每页条数限制"""
        response = self.client.get(
            '/api/v1/documents/documents/?page_size=100'
        )
        # DRF 会限制为 max_page_size
        self.assertEqual(len(response.data['results']), 50)
```

- [ ] **步骤 2：运行分页测试**

运行：`pytest apps/documents/tests/test_pagination.py -v`
预期：所有测试通过

- [ ] **步骤 3：Commit**

```bash
git add apps/documents/tests/test_pagination.py
git commit -m "test: add Document pagination tests

- Test default page size (5 items)
- Test custom page size via query param
- Test page navigation
- Test next/previous URL generation
- Test max page size limit enforcement

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## 任务 9：编写用户偏好测试

**文件：**
- 创建：`apps/users/tests/test_preferences.py`

- [ ] **步骤 1：创建用户偏好测试文件**

创建 `apps/users/tests/test_preferences.py`：

```python
"""
Tests for User preferences functionality.
"""
from django.test import TestCase
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

User = get_user_model()


class UserPreferencesTestCase(TestCase):
    """测试用户偏好设置功能"""

    def setUp(self):
        """创建测试数据"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass'
        )
        self.client.force_authenticate(user=self.user)

    def test_default_documents_per_page(self):
        """测试默认每页条数为 5"""
        self.assertEqual(self.user.documents_per_page, 5)

    def test_update_valid_preference(self):
        """测试更新有效偏好值"""
        response = self.client.put(
            '/api/v1/auth/me/',
            data={'documents_per_page': 10},
            format='json'
        )
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.documents_per_page, 10)

    def test_update_invalid_preference(self):
        """测试更新无效偏好值"""
        response = self.client.put(
            '/api/v1/auth/me/',
            data={'documents_per_page': 15},
            format='json'
        )
        self.assertEqual(response.status_code, 400)

    def test_preference_range_validation(self):
        """测试偏好值范围验证"""
        # 最小值测试
        response = self.client.put(
            '/api/v1/auth/me/',
            data={'documents_per_page': 3},
            format='json'
        )
        self.assertEqual(response.status_code, 400)

        # 最大值测试
        response = self.client.put(
            '/api/v1/auth/me/',
            data={'documents_per_page': 100},
            format='json'
        )
        self.assertEqual(response.status_code, 400)
```

- [ ] **步骤 2：运行用户偏好测试**

运行：`pytest apps/users/tests/test_preferences.py -v`
预期：所有测试通过

- [ ] **步骤 3：Commit**

```bash
git add apps/users/tests/test_preferences.py
git commit -m "test: add User preferences tests

- Test default documents_per_page value
- Test valid preference updates
- Test invalid preference values rejection
- Test preference value range validation

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## 任务 10：端到端测试和验证

- [ ] **步骤 1：运行完整测试套件**

运行：`pytest apps/documents/tests/ apps/users/tests/ -v`
预期：所有测试通过

- [ ] **步骤 2：手动验证功能**

启动服务器：`python manage.py runserver`

验证清单：
1. [ ] 以 admin 用户登录
2. [ ] 点击"单证管理"
3. [ ] 验证列表默认显示最多 5 条记录
4. [ ] 验证顶部和底部都有分页控件
5. [ ] 点击"下一页"，验证翻页正常
6. [ ] 将每页条数改为 10，验证列表刷新
7. [ ] 刷新页面，验证每页仍显示 10 条
8. [ ] 使用筛选功能，验证分页与筛选配合正常
9. [ ] 验证"首页"和"末页"按钮正常工作

- [ ] **步骤 3：最终 Commit**

```bash
git add -A
git commit -m "feat: complete document pagination feature

All pagination functionality implemented and tested:
- Backend pagination with DRF PageNumberPagination
- User preference storage and API
- Frontend pagination controls with JavaScript
- Comprehensive test coverage

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## 验收标准

完成所有任务后，系统应满足以下条件：

1. ✅ 单证列表默认每页显示 5 条记录
2. ✅ 用户可选择 5/10/20/50 条每页
3. ✅ 分页控件在列表顶部和底部显示
4. ✅ 翻页功能正常（首页、上一页、下一页、末页）
5. ✅ 显示当前页/总页数和总记录数
6. ✅ 用户偏好保存在数据库中
7. ✅ 刷新页面后保持用户选择的每页条数
8. ✅ 分页与筛选功能配合正常
9. ✅ 所有测试通过
