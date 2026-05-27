# 角色切换器 UI 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 在导航栏添加角色切换 dropdown，让用户一键切换已激活的贸易角色

**架构：** 后端在 UserCompanyRoleViewSet 补充 `activate` 和 `current` 两个 action；前端在 `base.html` 导航栏用户名左侧添加 Bootstrap 3 dropdown 组件，通过 jQuery AJAX 调用 API 实现切换

**技术栈：** Django REST Framework, Bootstrap 3.3.7, jQuery 3.6.0

---

## 文件结构

### 将要创建的文件

| 文件路径 | 职责 |
|---------|------|
| `static/js/role-switcher.js` | 角色切换器前端逻辑：加载当前角色、渲染 dropdown、调用激活 API |
| `static/css/role-switcher.css` | 角色切换器样式：角色徽章颜色、dropdown 布局 |

### 将要修改的文件

| 文件路径 | 修改内容 |
|---------|---------|
| `apps/roles/views.py` | UserCompanyRoleViewSet 添加 `activate` 和 `current` action |
| `apps/roles/tests/test_api.py` | 添加 activate/current API 测试 |
| `templates/base.html` | 导航栏添加角色切换 dropdown HTML |

---

## 任务分解

### 任务 1：添加 activate API 端点

**文件：**
- 修改：`apps/roles/views.py` — UserCompanyRoleViewSet 添加 `activate` action
- 修改：`apps/roles/tests/test_api.py` — 添加 activate 测试

- [ ] **步骤 1：编写 activate 测试**

在 `apps/roles/tests/test_api.py` 的 `TestUserCompanyRoleAPI` 类中添加：

```python
def test_activate_role_success(self, db):
    """Test activating a role."""
    assignment1 = UserCompanyRole.objects.create(
        user=self.student,
        company=self.company,
        role=self.exporter_role,
        status=UserCompanyRole.Status.ACTIVE,
        is_active=True
    )
    assignment2 = UserCompanyRole.objects.create(
        user=self.student,
        company=self.company,
        role=self.importer_role,
        status=UserCompanyRole.Status.ACTIVE,
        is_active=False
    )

    self.client.force_authenticate(user=self.student)
    response = self.client.post(f'/api/v1/my-roles/{assignment2.id}/activate/')

    assert response.status_code == status.HTTP_200_OK
    assert response.data['code'] == 0
    assert response.data['data']['is_active'] is True
    assert response.data['data']['role_code'] == 'importer'

    assignment1.refresh_from_db()
    assert assignment1.is_active is False

def test_activate_role_not_owner(self, db):
    """Test activating a role that belongs to another user."""
    assignment = UserCompanyRole.objects.create(
        user=self.student,
        company=self.company,
        role=self.exporter_role,
        status=UserCompanyRole.Status.ACTIVE,
        is_active=True
    )

    self.client.force_authenticate(user=self.student2)
    response = self.client.post(f'/api/v1/my-roles/{assignment.id}/activate/')

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data['code'] == 5005

def test_activate_role_not_active_status(self, db):
    """Test activating a role that is still pending."""
    assignment = UserCompanyRole.objects.create(
        user=self.student,
        company=self.company,
        role=self.exporter_role,
        status=UserCompanyRole.Status.PENDING
    )

    self.client.force_authenticate(user=self.student)
    response = self.client.post(f'/api/v1/my-roles/{assignment.id}/activate/')

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data['code'] == 5005
```

- [ ] **步骤 2：运行测试验证失败**

运行：
```bash
pytest apps/roles/tests/test_api.py::TestUserCompanyRoleAPI::test_activate_role_success -v
```

预期：FAIL，`/api/v1/my-roles/{id}/activate/` 返回 405 Method Not Allowed（端点不存在）

- [ ] **步骤 3：实现 activate action**

在 `apps/roles/views.py` 的 `UserCompanyRoleViewSet` 类中，在 `pending` 方法之后添加：

```python
@action(detail=True, methods=['post'], url_path='activate')
def activate(self, request, pk=None):
    """
    Activate a role assignment (single activation).

    Args:
        pk: UserCompanyRole ID

    Returns:
        200: Role activated successfully
        400: Invalid state or not owner
    """
    try:
        assignment = RoleService.activate_role(
            user=request.user,
            assignment_id=pk
        )
        return Response({
            'code': 0,
            'message': '角色已切换',
            'data': UserCompanyRoleSerializer(assignment).data
        }, status=status.HTTP_200_OK)

    except ValueError as e:
        return Response({
            'code': 5005,
            'message': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
```

- [ ] **步骤 4：运行测试验证通过**

运行：
```bash
pytest apps/roles/tests/test_api.py::TestUserCompanyRoleAPI::test_activate_role_success apps/roles/tests/test_api.py::TestUserCompanyRoleAPI::test_activate_role_not_owner apps/roles/tests/test_api.py::TestUserCompanyRoleAPI::test_activate_role_not_active_status -v
```

预期：全部 PASS

- [ ] **步骤 5：Commit**

```bash
git add apps/roles/views.py apps/roles/tests/test_api.py
git commit -m "feat(roles): add activate API endpoint for role switching"
```

---

### 任务 2：添加 current API 端点

**文件：**
- 修改：`apps/roles/views.py` — UserCompanyRoleViewSet 添加 `current` action
- 修改：`apps/roles/tests/test_api.py` — 添加 current 测试

- [ ] **步骤 1：编写 current 测试**

在 `apps/roles/tests/test_api.py` 的 `TestUserCompanyRoleAPI` 类中添加：

```python
def test_get_current_role(self, db):
    """Test getting current active role."""
    UserCompanyRole.objects.create(
        user=self.student,
        company=self.company,
        role=self.exporter_role,
        status=UserCompanyRole.Status.ACTIVE,
        is_active=True
    )

    self.client.force_authenticate(user=self.student)
    response = self.client.get('/api/v1/my-roles/current/')

    assert response.status_code == status.HTTP_200_OK
    assert response.data['code'] == 0
    assert response.data['data'] is not None
    assert response.data['data']['company_name'] == '测试贸易公司'
    assert response.data['data']['role_code'] == 'exporter'
    assert response.data['data']['role_name'] == '出口商'
    assert response.data['data']['is_active'] is True

def test_get_current_role_none(self, db):
    """Test getting current role when user has no active role."""
    self.client.force_authenticate(user=self.student)
    response = self.client.get('/api/v1/my-roles/current/')

    assert response.status_code == status.HTTP_200_OK
    assert response.data['code'] == 0
    assert response.data['data'] is None
```

- [ ] **步骤 2：运行测试验证失败**

运行：
```bash
pytest apps/roles/tests/test_api.py::TestUserCompanyRoleAPI::test_get_current_role -v
```

预期：FAIL，`/api/v1/my-roles/current/` 返回 405（端点不存在）

- [ ] **步骤 3：实现 current action**

在 `apps/roles/views.py` 的 `UserCompanyRoleViewSet` 类中，在 `activate` 方法之后添加：

```python
@action(detail=False, methods=['get'], url_path='current')
def current(self, request):
    """
    Get current active role context.

    Returns:
        200: Current role data or null
    """
    assignment = RoleService.get_current_role(request.user)
    if not assignment:
        return Response({
            'code': 0,
            'message': 'success',
            'data': None
        }, status=status.HTTP_200_OK)

    serializer = UserCompanyRoleSerializer(assignment)
    return Response({
        'code': 0,
        'message': 'success',
        'data': serializer.data
    }, status=status.HTTP_200_OK)
```

- [ ] **步骤 4：运行测试验证通过**

运行：
```bash
pytest apps/roles/tests/test_api.py::TestUserCompanyRoleAPI::test_get_current_role apps/roles/tests/test_api.py::TestUserCompanyRoleAPI::test_get_current_role_none -v
```

预期：全部 PASS

- [ ] **步骤 5：运行全部 roles 测试确认无回归**

运行：
```bash
pytest apps/roles/tests/ -v
```

预期：全部 PASS

- [ ] **步骤 6：Commit**

```bash
git add apps/roles/views.py apps/roles/tests/test_api.py
git commit -m "feat(roles): add current API endpoint for active role context"
```

---

### 任务 3：创建角色切换器样式

**文件：**
- 创建：`static/css/role-switcher.css`

- [ ] **步骤 1：创建 CSS 文件**

创建 `static/css/role-switcher.css`：

```css
/* ==========================================
   角色切换器样式
   ========================================== */

/* 切换器按钮 */
.role-switcher .dropdown-toggle {
    padding: 8px 12px;
    color: #9d9d9d;
    cursor: pointer;
}

.role-switcher .dropdown-toggle:hover,
.role-switcher .dropdown-toggle:focus {
    color: #fff;
    background-color: transparent;
}

/* 角色徽章 */
.role-badge {
    display: inline-block;
    padding: 2px 8px;
    font-size: 12px;
    font-weight: bold;
    line-height: 1.5;
    color: #fff;
    border-radius: 3px;
    vertical-align: middle;
}

/* 10 种角色颜色 */
.role-badge.role-exporter   { background-color: #337ab7; }
.role-badge.role-importer   { background-color: #5cb85c; }
.role-badge.role-factory    { background-color: #f0ad4e; color: #333; }
.role-badge.role-bank       { background-color: #5bc0de; color: #333; }
.role-badge.role-customs    { background-color: #d9534f; }
.role-badge.role-shipping   { background-color: #777; }
.role-badge.role-insurance  { background-color: #337ab7; }
.role-badge.role-inspection { background-color: #5cb85c; }
.role-badge.role-forex      { background-color: #f0ad4e; color: #333; }
.role-badge.role-tax        { background-color: #5bc0de; color: #333; }

/* 导航栏角色标签 */
.role-switcher-label {
    font-size: 13px;
    color: #9d9d9d;
    max-width: 180px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    display: inline-block;
    vertical-align: middle;
}

/* 角色列表项 */
.role-item {
    padding: 8px 20px !important;
    cursor: pointer;
    white-space: nowrap;
}

.role-item:hover {
    background-color: #f5f5f5;
}

.role-item.active-role {
    background-color: #eef7ff;
    font-weight: bold;
}

.role-item .role-item-name {
    display: inline-block;
    max-width: 140px;
    overflow: hidden;
    text-overflow: ellipsis;
    vertical-align: middle;
}

.role-item .check-mark {
    color: #337ab7;
    margin-right: 5px;
}

.role-item .pending-label {
    font-size: 11px;
    color: #999;
    margin-left: 5px;
}

/* 无角色提示 */
.role-empty-hint {
    padding: 10px 20px;
    color: #999;
    font-size: 13px;
}
```

- [ ] **步骤 2：Commit**

```bash
git add static/css/role-switcher.css
git commit -m "feat(ui): add role switcher styles"
```

---

### 任务 4：创建角色切换器 JS

**文件：**
- 创建：`static/js/role-switcher.js`

- [ ] **步骤 1：创建 JS 文件**

创建 `static/js/role-switcher.js`：

```javascript
/**
 * SimTrade 角色切换器
 * 依赖：jQuery, Bootstrap 3 dropdown, SimTrade (main.js)
 */
(function() {
    'use strict';

    // 角色名称映射
    var ROLE_NAMES = {
        'exporter': '出口商', 'importer': '进口商', 'factory': '工厂',
        'bank': '银行', 'customs': '海关', 'shipping': '货运公司',
        'insurance': '保险公司', 'inspection': '商检机构',
        'forex': '外汇局', 'tax': '税务局'
    };

    /**
     * 渲染角色徽章 HTML
     */
    function renderBadge(roleCode) {
        var name = ROLE_NAMES[roleCode] || roleCode;
        return '<span class="role-badge role-' + roleCode + '">' + name + '</span>';
    }

    /**
     * 更新导航栏按钮显示
     */
    function updateButton(data) {
        var $label = $('#role-switcher-label');
        if (!data) {
            $label.html('选择角色');
            return;
        }
        $label.html(renderBadge(data.role_code) +
            ' <span class="role-switcher-label">' +
            SimTrade.escapeHtml(data.company_name) + '</span>');
    }

    /**
     * 渲染角色列表
     */
    function renderRoles(data) {
        var $menu = $('#role-dropdown-menu');
        $menu.empty();

        if (!data || data.length === 0) {
            $menu.append('<li class="role-empty-hint">暂无角色，请联系教师分配</li>');
            return;
        }

        // 分组：已激活角色 + 待审核角色
        var activeRoles = [];
        var pendingRoles = [];

        for (var i = 0; i < data.length; i++) {
            var item = data[i];
            if (item.status === 'active') {
                activeRoles.push(item);
            } else if (item.status === 'pending') {
                pendingRoles.push(item);
            }
            // rejected 状态不显示
        }

        // 已激活角色
        if (activeRoles.length > 0) {
            $menu.append('<li class="dropdown-header">已激活角色</li>');
            for (var j = 0; j < activeRoles.length; j++) {
                var role = activeRoles[j];
                var isActive = role.is_active;
                var checkMark = isActive ? '<span class="check-mark">&#10003;</span>' : '';
                var activeClass = isActive ? ' active-role' : '';
                var html = '<li class="role-item' + activeClass + '" data-id="' + role.id + '">' +
                    checkMark + renderBadge(role.role_code) +
                    ' <span class="role-item-name">' + SimTrade.escapeHtml(role.company_name) + '</span>' +
                    '</li>';
                $menu.append(html);
            }
        }

        // 待审核角色
        if (pendingRoles.length > 0) {
            if (activeRoles.length > 0) {
                $menu.append('<li role="separator" class="divider"></li>');
            }
            $menu.append('<li class="dropdown-header">待审核</li>');
            for (var k = 0; k < pendingRoles.length; k++) {
                var pRole = pendingRoles[k];
                $menu.append(
                    '<li class="role-item disabled">' +
                    renderBadge(pRole.role_code) +
                    ' <span class="role-item-name">' + SimTrade.escapeHtml(pRole.company_name) + '</span>' +
                    '<span class="pending-label">待审核</span></li>');
            }
        }
    }

    /**
     * 切换角色
     */
    function switchRole(assignmentId) {
        $.ajax({
            url: '/api/v1/my-roles/' + assignmentId + '/activate/',
            type: 'POST',
            success: function() {
                window.location.reload();
            },
            error: function(xhr) {
                var msg = '角色切换失败';
                if (xhr.responseJSON && xhr.responseJSON.message) {
                    msg = xhr.responseJSON.message;
                }
                SimTrade.showError(msg);
            }
        });
    }

    /**
     * 初始化角色切换器
     */
    function init() {
        if (!window.user || !window.user.is_authenticated) {
            return;
        }

        // 加载当前激活角色
        $.get('/api/v1/my-roles/current/', function(resp) {
            updateButton(resp.data);
        });

        // dropdown 展开时加载角色列表
        $('#role-dropdown').on('show.bs.dropdown', function() {
            $.get('/api/v1/my-roles/', function(resp) {
                renderRoles(resp.data);
            });
        });

        // 点击角色项切换
        $(document).on('click', '#role-dropdown-menu .role-item:not(.disabled):not(.active-role)', function(e) {
            var id = $(this).data('id');
            if (id) {
                switchRole(id);
            }
            e.stopPropagation();
        });
    }

    $(document).ready(init);

})();
```

注意：`SimTrade.escapeHtml` 需要在 `main.js` 中添加。下个任务处理。

- [ ] **步骤 2：Commit**

```bash
git add static/js/role-switcher.js
git commit -m "feat(ui): add role switcher JavaScript"
```

---

### 任务 5：修改 base.html 和 main.js

**文件：**
- 修改：`templates/base.html` — 添加角色切换 dropdown HTML + 引入新文件
- 修改：`static/js/main.js` — 添加 `escapeHtml` 工具函数

- [ ] **步骤 1：在 main.js 中添加 escapeHtml**

在 `static/js/main.js` 的 `SimTrade` 导出对象中（`isEmpty` 之后），添加：

```javascript
function escapeHtml(text) {
    if (!text) return '';
    var div = document.createElement('div');
    div.appendChild(document.createTextNode(text));
    return div.innerHTML;
}
```

在 `window.SimTrade` 对象中添加导出：

```javascript
window.SimTrade = {
    // ...existing exports...
    escapeHtml: escapeHtml
};
```

- [ ] **步骤 2：修改 base.html 导航栏**

在 `templates/base.html` 中，将 `<ul class="nav navbar-nav navbar-right">` 部分替换为：

```html
<ul class="nav navbar-nav navbar-right">
    {% if user.is_authenticated %}
        <!-- 角色切换器 -->
        <li class="dropdown role-switcher" id="role-dropdown">
            <a href="#" class="dropdown-toggle" data-toggle="dropdown" role="button" aria-haspopup="true" aria-expanded="false">
                <span id="role-switcher-label">选择角色</span> <span class="caret"></span>
            </a>
            <ul class="dropdown-menu" id="role-dropdown-menu">
                <li class="role-empty-hint">加载中...</li>
            </ul>
        </li>
        <!-- 用户菜单 -->
        <li class="dropdown">
            <a href="#" class="dropdown-toggle" data-toggle="dropdown" role="button" aria-haspopup="true" aria-expanded="false">
                {{ user.username }} <span class="caret"></span>
            </a>
            <ul class="dropdown-menu">
                <li><a href="/profile/">个人中心</a></li>
                <li role="separator" class="divider"></li>
                <li><a href="#" id="logout-link">退出登录</a></li>
            </ul>
        </li>
    {% else %}
        <li><a href="/login/">登录</a></li>
        <li><a href="/register/">注册</a></li>
    {% endif %}
</ul>
```

在 `base.html` 的 `{% block extra_css %}` 之前添加：

```html
<link href="{% static 'css/role-switcher.css' %}" rel="stylesheet">
```

在 `{% block extra_js %}` 之前添加：

```html
<script src="{% static 'js/role-switcher.js' %}"></script>
```

- [ ] **步骤 3：验证页面可加载**

运行：
```bash
python manage.py check
```

预期：无报错

- [ ] **步骤 4：Commit**

```bash
git add templates/base.html static/js/main.js
git commit -m "feat(ui): integrate role switcher into navbar"
```

---

### 任务 6：最终验证

**文件：**
- 所有相关文件

- [ ] **步骤 1：运行全部 roles 测试**

运行：
```bash
pytest apps/roles/tests/ -v
```

预期：全部 PASS

- [ ] **步骤 2：运行 Django 系统检查**

运行：
```bash
python manage.py check
```

预期：无报错（URL namespace 警告可忽略）

- [ ] **步骤 3：启动开发服务器手动验证**

运行：
```bash
python manage.py runserver
```

验证：
1. 访问 http://localhost:8000/ — 导航栏应显示「选择角色」dropdown
2. 登录后，如果有激活角色，应显示角色徽章 + 公司名
3. 点击 dropdown 展开角色列表
4. 点击另一个角色，页面刷新后角色切换成功

- [ ] **步骤 4：最终 Commit**

```bash
git add .
git commit -m "feat(ui): complete role switcher with activate/current API"
```

---

## 自检清单

### 规格覆盖度

| 设计章节 | 对应任务 |
|---------|---------|
| activate API 端点 | 任务 1 |
| current API 端点 | 任务 2 |
| 10 种角色颜色映射 | 任务 3 |
| role-switcher.js 逻辑 | 任务 4 |
| base.html 导航栏集成 | 任务 5 |
| main.js escapeHtml 工具 | 任务 5 |
| 最终验证 | 任务 6 |

### 占位符检查

- 无 "TBD"、"TODO" 等占位符
- 所有代码步骤包含完整代码
- 所有命令有明确的预期输出

### 类型一致性检查

- API 端点路径：`/api/v1/my-roles/{id}/activate/` 和 `/api/v1/my-roles/current/` 在 views.py 和 JS 中一致
- `UserCompanyRoleSerializer` 输出字段 `role_code`, `company_name`, `is_active` 在测试和 JS 中引用一致
- `RoleService.activate_role(user, assignment_id)` 签名与 views.py 调用一致
- `RoleService.get_current_role(user)` 签名与 views.py 调用一致
