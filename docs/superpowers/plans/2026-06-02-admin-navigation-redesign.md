# Admin 导航重构实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 统一管理后台入口为 `/admin/`，添加左侧导航栏和面包屑导航，优化系统设置页面布局。

**Architecture:**
- 创建可复用的侧边导航组件模板
- 使用继承机制让所有 admin 页面共享统一布局
- 通过 JavaScript 实现菜单高亮和面包屑生成
- 保持现有 Bootstrap 3 样式体系

**Tech Stack:** Django 2.2, Bootstrap 3.3.7, jQuery 3.6.0, Python 3.7+

---

## 文件结构

### 新建文件
- `templates/admin/base.html` - Admin 后台基础模板（含侧边导航）
- `templates/admin/dashboard.html` - 概览页面（合并图表）
- `templates/admin/user_list.html` - 用户管理页面
- `templates/admin/system.html` - 系统设置页面
- `static/css/admin-sidebar.css` - 侧边导航样式
- `static/js/admin-sidebar.js` - 侧边导航交互逻辑

### 修改文件
- `simtrade/urls.py` - 更新 URL 路由
- `templates/base.html` - 更新顶部导航链接
- `static/css/dashboard.css` - 可选：调整统计卡片样式

### 废弃文件
- `templates/admin_panel/dashboard.html` - 迁移后删除
- `templates/admin_panel/user_list.html` - 迁移后删除
- `templates/admin_panel/system.html` - 迁移后删除
- `templates/dashboard/admin.html` - 图表功能合并到新概览页面

---

## Task 1: 创建侧边导航样式

**Files:**
- Create: `static/css/admin-sidebar.css`

- [ ] **Step 1: 创建侧边导航 CSS 文件**

```css
/* ==========================================
   Admin Sidebar Navigation Styles
   ========================================== */

/* Admin Layout Wrapper */
.admin-layout {
    display: flex;
    min-height: calc(100vh - 50px);
    margin-top: 20px;
}

/* Sidebar */
.admin-sidebar {
    width: 200px;
    background-color: #262626;
    min-height: calc(100vh - 70px);
    border-radius: 4px;
    overflow: hidden;
}

.admin-sidebar .navbar-brand {
    padding: 15px 20px;
    color: #fff;
    font-size: 16px;
    font-weight: 600;
    background-color: #1a1a1a;
    margin: 0;
}

.admin-sidebar .list-group-item {
    background-color: transparent;
    border: none;
    color: #b0b0b0;
    padding: 12px 20px;
    border-left: 3px solid transparent;
    transition: all 0.2s;
}

.admin-sidebar .list-group-item:hover {
    background-color: #333;
    color: #fff;
}

.admin-sidebar .list-group-item.active {
    background-color: #4a90d9;
    color: #fff;
    border-left-color: #6ab0f9;
}

.admin-sidebar .list-group-item .glyphicon {
    margin-right: 8px;
    width: 16px;
    text-align: center;
}

/* Main Content Area */
.admin-main {
    flex: 1;
    padding-left: 20px;
    overflow-x: hidden;
}

/* Breadcrumb */
.admin-breadcrumb {
    background-color: #f5f5f5;
    padding: 10px 15px;
    border-radius: 4px;
    margin-bottom: 20px;
}

.admin-breadcrumb ol.breadcrumb {
    margin: 0;
    padding: 0;
    background-color: transparent;
}

/* Responsive */
@media (max-width: 768px) {
    .admin-layout {
        flex-direction: column;
    }

    .admin-sidebar {
        width: 100%;
        min-height: auto;
        margin-bottom: 15px;
    }
}
```

---

## Task 2: 创建侧边导航交互逻辑

**Files:**
- Create: `static/js/admin-sidebar.js`

- [ ] **Step 1: 创建侧边导航 JS 文件**

```javascript
/**
 * Admin Sidebar Navigation
 */
(function() {
    'use strict';

    // Menu configuration
    var MENU_ITEMS = [
        { path: '/admin/', icon: 'home', label: '概览' },
        { path: '/admin/users/', icon: 'user', label: '用户管理' },
        { path: '/teaching/', icon: 'book', label: '教学管理' },
        { path: '/documents/', icon: 'file', label: '单证管理' },
        { path: '/companies/', icon: 'briefcase', label: '公司管理' },
        { path: '/admin/system/', icon: 'cog', label: '系统设置' }
    ];

    /**
     * Get current page info from path
     */
    function getCurrentPage() {
        var path = window.location.pathname;
        for (var i = 0; i < MENU_ITEMS.length; i++) {
            if (path.indexOf(MENU_ITEMS[i].path) === 0) {
                return MENU_ITEMS[i];
            }
        }
        return MENU_ITEMS[0]; // Default to overview
    }

    /**
     * Generate breadcrumb HTML
     */
    function generateBreadcrumb() {
        var current = getCurrentPage();
        var html = '<ol class="breadcrumb">' +
            '<li><a href="/">首页</a></li>' +
            '<li><a href="/admin/">管理后台</a></li>' +
            '<li class="active">' + current.label + '</li>' +
            '</ol>';
        return html;
    }

    /**
     * Set active menu item
     */
    function setActiveMenu() {
        var path = window.location.pathname;
        $('.admin-sidebar .list-group-item').each(function() {
            var href = $(this).attr('href');
            if (href && path.indexOf(href) === 0) {
                $(this).addClass('active');
            } else {
                $(this).removeClass('active');
            }
        });
    }

    /**
     * Initialize sidebar
     */
    function initSidebar() {
        // Render breadcrumb
        var breadcrumbHtml = generateBreadcrumb();
        $('.admin-breadcrumb').html(breadcrumbHtml);

        // Set active menu
        setActiveMenu();
    };

    // Export for external use
    window.AdminSidebar = {
        init: initSidebar,
        getCurrentPage: getCurrentPage,
        generateBreadcrumb: generateBreadcrumb,
        setActiveMenu: setActiveMenu
    };

    // Auto-initialize on document ready
    $(document).ready(function() {
        if ($('.admin-sidebar').length > 0) {
            initSidebar();
        }
    });

})();
```

---

## Task 3: 创建 Admin 基础模板

**Files:**
- Create: `templates/admin/base.html`

- [ ] **Step 1: 创建 admin/base.html 模板**

```django
{% extends "base.html" %}
{% load static %}
{% load bilingual %}

{% block title %}管理后台 - SimTrade{% endblock %}

{% block extra_css %}
<link href="{% static 'css/dashboard.css' %}" rel="stylesheet">
<link href="{% static 'css/admin-sidebar.css' %}" rel="stylesheet">
{% endblock %}

{% block content %}
<div class="admin-layout">
    <!-- Sidebar -->
    <div class="admin-sidebar">
        <div class="navbar-brand">管理后台</div>
        <div class="list-group">
            <a href="/admin/" class="list-group-item">
                <span class="glyphicon glyphicon-home"></span> {{ "概览"|bilingual }}
            </a>
            <a href="/admin/users/" class="list-group-item">
                <span class="glyphicon glyphicon-user"></span> {{ "用户管理"|bilingual }}
            </a>
            <a href="/teaching/" class="list-group-item">
                <span class="glyphicon glyphicon-book"></span> {{ "教学管理"|bilingual }}
            </a>
            <a href="/documents/" class="list-group-item">
                <span class="glyphicon glyphicon-file"></span> {{ "单证管理"|bilingual }}
            </a>
            <a href="/companies/" class="list-group-item">
                <span class="glyphicon glyphicon-briefcase"></span> {{ "公司管理"|bilingual }}
            </a>
            <a href="/admin/system/" class="list-group-item">
                <span class="glyphicon glyphicon-cog"></span> {{ "系统设置"|bilingual }}
            </a>
        </div>
    </div>

    <!-- Main Content -->
    <div class="admin-main">
        <!-- Breadcrumb -->
        <div class="admin-breadcrumb">
            <ol class="breadcrumb">
                <li><a href="/">首页</a></li>
                <li><a href="/admin/">管理后台</a></li>
                <li class="active">{% block page_title %}概览{% endblock %}</li>
            </ol>
        </div>

        <!-- Page Content -->
        {% block admin_content %}{% endblock %}
    </div>
</div>
{% endblock %}

{% block extra_js %}
<script src="{% static 'js/admin-sidebar.js' %}"></script>
{% endblock %}
```

---

## Task 4: 创建概览页面（合并图表）

**Files:**
- Create: `templates/admin/dashboard.html`

- [ ] **Step 1: 创建概览页面模板，合并统计卡片和图表**

```django
{% extends "admin/base.html" %}
{% load static %}
{% load bilingual %}

{% block page_title %}{{ "概览"|bilingual }}{% endblock %}

{% block extra_css %}
<style>
.chart-container {
    position: relative;
    height: 220px;
    margin: 10px 0;
}
.dash-section { margin-bottom: 20px; }
.dash-section h3 {
    font-size: 16px;
    font-weight: 600;
    border-bottom: 2px solid #4a90d9;
    padding-bottom: 6px;
    margin-bottom: 12px;
}
.todo-item {
    display: flex;
    align-items: center;
    padding: 8px 12px;
    border-bottom: 1px solid #f0f0f0;
}
.todo-item:last-child { border-bottom: none; }
.todo-badge {
    display: inline-block;
    min-width: 24px;
    height: 24px;
    line-height: 24px;
    text-align: center;
    border-radius: 12px;
    color: #fff;
    font-size: 12px;
    font-weight: bold;
    margin-right: 10px;
}
.todo-badge.badge-warning { background: #f0ad4e; }
.todo-badge.badge-info { background: #5bc0de; }
.todo-badge.badge-danger { background: #d9534f; }
.activity-item {
    padding: 8px 12px;
    border-bottom: 1px solid #f0f0f0;
    font-size: 13px;
}
.activity-item:last-child { border-bottom: none; }
.activity-time { color: #999; font-size: 12px; }
.status-dot {
    display: inline-block;
    width: 8px; height: 8px;
    border-radius: 50%;
    margin-right: 6px;
}
.status-dot.draft { background: #999; }
.status-dot.pending_review { background: #f0ad4e; }
.status-dot.approved { background: #5cb85c; }
.status-dot.rejected { background: #d9534f; }
</style>
{% endblock %}

{% block admin_content %}
<!-- Page Header -->
<div class="row" style="margin-bottom:8px;">
    <div class="col-md-12">
        <h4 style="font-weight:600;color:#262626;margin:0;">{{ "管理员仪表盘"|bilingual }}</h4>
        <p class="text-muted" style="margin:4px 0 0;">{{ "欢迎回来"|bilingual }}，{{ user.username }}</p>
    </div>
</div>

<!-- 统计卡片 -->
<div class="row dashboard-stats">
    <div class="col-md-3">
        <a href="/admin/users/" class="dash-stat-card card-blue">
            <div class="dash-stat-icon"><span class="glyphicon glyphicon-user"></span></div>
            <div class="dash-stat-info">
                <div class="dash-stat-label">{{ "注册用户"|bilingual }}</div>
            </div>
            <div class="dash-stat-right">
                <div class="dash-stat-value" id="stat-users">-</div>
                <span class="dash-stat-arrow glyphicon glyphicon-menu-right"></span>
            </div>
        </a>
    </div>
    <div class="col-md-3">
        <a href="/documents/" class="dash-stat-card card-green">
            <div class="dash-stat-icon"><span class="glyphicon glyphicon-file"></span></div>
            <div class="dash-stat-info">
                <div class="dash-stat-label">{{ "单证总数"|bilingual }}</div>
            </div>
            <div class="dash-stat-right">
                <div class="dash-stat-value" id="stat-documents">-</div>
                <span class="dash-stat-arrow glyphicon glyphicon-menu-right"></span>
            </div>
        </a>
    </div>
    <div class="col-md-3">
        <a href="/teaching/courses/" class="dash-stat-card card-orange">
            <div class="dash-stat-icon"><span class="glyphicon glyphicon-transfer"></span></div>
            <div class="dash-stat-info">
                <div class="dash-stat-label">{{ "课程总数"|bilingual }}</div>
            </div>
            <div class="dash-stat-right">
                <div class="dash-stat-value" id="stat-courses">-</div>
                <span class="dash-stat-arrow glyphicon glyphicon-menu-right"></span>
            </div>
        </a>
    </div>
    <div class="col-md-3">
        <a href="/admin/system/" class="dash-stat-card card-purple">
            <div class="dash-stat-icon"><span class="glyphicon glyphicon-calendar"></span></div>
            <div class="dash-stat-info">
                <div class="dash-stat-label">{{ "活跃学期"|bilingual }}</div>
            </div>
            <div class="dash-stat-right">
                <div class="dash-stat-value" id="stat-semesters">-</div>
                <span class="dash-stat-arrow glyphicon glyphicon-menu-right"></span>
            </div>
        </a>
    </div>
</div>

<!-- 图表区域 -->
<div class="row">
    <div class="col-md-4">
        <div class="panel panel-default">
            <div class="panel-heading"><h3 class="panel-title">{{ "单证类型分布"|bilingual }}</h3></div>
            <div class="panel-body">
                <div class="chart-container"><canvas id="chartDocType"></canvas></div>
            </div>
        </div>
    </div>
    <div class="col-md-4">
        <div class="panel panel-default">
            <div class="panel-heading"><h3 class="panel-title">{{ "用户类型分布"|bilingual }}</h3></div>
            <div class="panel-body">
                <div class="chart-container"><canvas id="chartUserType"></canvas></div>
            </div>
        </div>
    </div>
    <div class="col-md-4">
        <div class="panel panel-default">
            <div class="panel-heading"><h3 class="panel-title">{{ "单证状态分布"|bilingual }}</h3></div>
            <div class="panel-body">
                <div class="chart-container"><canvas id="chartDocStatus"></canvas></div>
            </div>
        </div>
    </div>
</div>

<!-- 最近活动 + 待办事项 -->
<div class="row">
    <div class="col-md-8">
        <div class="panel panel-default">
            <div class="panel-heading"><h3 class="panel-title">{{ "最近活动"|bilingual }}</h3></div>
            <div class="panel-body" id="recent-activity" style="padding:0;">
                <div class="text-muted text-center" style="padding:20px;">加载中...</div>
            </div>
        </div>
    </div>
    <div class="col-md-4">
        <div class="panel panel-default">
            <div class="panel-heading"><h3 class="panel-title">{{ "待办事项"|bilingual }}</h3></div>
            <div class="panel-body" id="todo-list" style="padding:0;">
                <div class="text-muted text-center" style="padding:20px;">加载中...</div>
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block extra_js %}
<script src="{% static 'js/chart.umd.min.js' %}"></script>
<script>
$(document).ready(function() {
    'use strict';

    var statusLabels = {
        'draft': '草稿', 'pending_review': '待审核',
        'approved': '已审核', 'rejected': '已驳回',
        'submitted': '已提交', 'received': '已接收', 'archived': '已归档'
    };
    var statusColors = {
        'draft': '#999', 'pending_review': '#f0ad4e',
        'approved': '#5cb85c', 'rejected': '#d9534f',
        'submitted': '#5bc0de', 'received': '#3b5998', 'archived': '#777'
    };
    var userTypeLabels = {
        'admin': '管理员', 'teacher': '教师', 'student': '学生'
    };
    var userTypeColors = {
        'admin': '#d9534f', 'teacher': '#5bc0de', 'student': '#5cb85c'
    };
    var docTypeColors = {
        'commercial_invoice': '#4479C1', 'packing_list': '#81C14B',
        'bill_of_exchange': '#FF9933', 'sales_contract': '#DC3912',
        'letter_of_credit': '#949494', 'bill_of_lading': '#109618',
        'air_waybill': '#990099', 'insurance_policy': '#3B3EAC',
        'insurance_application': '#0099C6', 'export_declaration': '#DD4477',
        'import_declaration': '#66AA00', 'inspection_application': '#B82EE8',
        'inspection_certificate': '#316395', 'certificate_of_origin': '#994499',
        'beneficiary_certificate': '#22AA99', 'shipping_advice': '#AA0033'
    };

    $.get('/api/v1/dashboard/stats/', function(resp) {
        // Summary cards
        $('#stat-users').text(resp.summary.total_users);
        $('#stat-documents').text(resp.summary.total_documents);
        $('#stat-courses').text(resp.summary.total_courses);

        // Active semesters
        $.get('/api/v1/teaching/semesters/', function(semResp) {
            var semesters = semResp.results || semResp.data || [];
            var activeCount = 0;
            for (var i = 0; i < semesters.length; i++) {
                if (semesters[i].status === 'active') activeCount++;
            }
            $('#stat-semesters').text(activeCount);
        }).fail(function() {
            $('#stat-semesters').text('-');
        });

        // Charts (keep existing chart logic from dashboard/admin.html)
        // ... [chart rendering code - same as original]
        // Recent activity
        var actHtml = '';
        if (resp.recent_documents.length === 0) {
            actHtml = '<div class="text-muted text-center" style="padding:20px;">暂无活动</div>';
        } else {
            resp.recent_documents.forEach(function(d) {
                var st = d.status || 'draft';
                actHtml += '<div class="activity-item">'
                    + '<span class="status-dot ' + st + '"></span>'
                    + '<strong>' + (d.template_name || '') + '</strong>'
                    + ' - ' + (d.created_by || '未知')
                    + ' <span class="activity-time">' + formatTime(d.created_at) + '</span>'
                    + '</div>';
            });
        }
        $('#recent-activity').html(actHtml);

        // Todo list
        var todoHtml = '';
        var todos = [];
        if (resp.summary.pending_review > 0) {
            todos.push({ badge: 'badge-warning', count: resp.summary.pending_review, text: '待审核单证', href: '/admin/' });
        }
        if (todos.length === 0) {
            todoHtml = '<div class="text-muted text-center" style="padding:20px;">暂无待办</div>';
        } else {
            todos.forEach(function(t) {
                todoHtml += '<a href="' + t.href + '" class="todo-item">'
                    + '<span class="todo-badge ' + t.badge + '">' + t.count + '</span> '
                    + t.text
                    + '</a>';
            });
        }
        $('#todo-list').html(todoHtml);
    });

    function formatTime(iso) {
        if (!iso) return '';
        var d = new Date(iso);
        return d.getFullYear() + '-' + pad(d.getMonth()+1) + '-' + pad(d.getDate())
            + ' ' + pad(d.getHours()) + ':' + pad(d.getMinutes());
    }
    function pad(n) { return n < 10 ? '0'+n : n; }
});
</script>
{% endblock %}
```

---

## Task 5: 创建用户管理页面

**Files:**
- Create: `templates/admin/user_list.html`

- [ ] **Step 1: 创建用户管理页面模板**

```django
{% extends "admin/base.html" %}
{% load static %}
{% load bilingual %}

{% block page_title %}{{ "用户管理"|bilingual }}{% endblock %}

{% block admin_content %}
<div class="row">
    <div class="col-md-12">
        <h2>{{ "用户管理"|bilingual }}</h2>
        <hr>
    </div>
</div>

<!-- 筛选和搜索 -->
<div class="row">
    <div class="col-md-12">
        <div class="panel panel-default">
            <div class="panel-body">
                <div class="row">
                    <div class="col-md-3">
                        <select id="filter-user-type" class="form-control">
                            <option value="">{{ "所有类型"|bilingual }}</option>
                            <option value="student">{{ "学生"|bilingual }}</option>
                            <option value="teacher">{{ "教师"|bilingual }}</option>
                            <option value="admin">{{ "管理员"|bilingual }}</option>
                        </select>
                    </div>
                    <div class="col-md-6">
                        <input type="text" id="search-user" class="form-control" placeholder="{{ "搜索用户名或邮箱..."|bilingual }}">
                    </div>
                    <div class="col-md-3">
                        <button id="btn-search-user" class="btn btn-primary btn-block">{{ "搜索"|bilingual }}</button>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>

<!-- 用户表格 -->
<div class="row">
    <div class="col-md-12">
        <div class="panel panel-default">
            <div class="panel-heading">
                <h3 class="panel-title">{{ "用户列表"|bilingual }}</h3>
            </div>
            <div class="panel-body">
                <table class="table table-bordered table-striped">
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>{{ "用户名"|bilingual }}</th>
                            <th>{{ "邮箱"|bilingual }}</th>
                            <th>{{ "类型"|bilingual }}</th>
                            <th>{{ "修改类型"|bilingual }}</th>
                            <th>{{ "操作"|bilingual }}</th>
                        </tr>
                    </thead>
                    <tbody id="user-table-body">
                        <tr><td colspan="6" class="text-center">{{ "加载中..."|bilingual }}</td></tr>
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block extra_js %}
<script src="{% static 'js/admin.js' %}"></script>
<script>
$(document).ready(function() {
    'use strict';
    loadUsers();

    $('#btn-search-user').on('click', function() {
        loadUsers();
    });

    $('#search-user').keypress(function(e) {
        if (e.which === 13) {
            e.preventDefault();
            loadUsers();
        }
    });
});
</script>
{% endblock %}
```

---

## Task 6: 创建系统设置页面

**Files:**
- Create: `templates/admin/system.html`

- [ ] **Step 1: 创建系统设置页面模板（移除学期管理，保留汇率、HS编码、海关参数）**

```django
{% extends "admin/base.html" %}
{% load static %}
{% load bilingual %}

{% block page_title %}{{ "系统设置"|bilingual }}{% endblock %}

{% block extra_css %}
<link href="{% static 'css/teaching.css' %}" rel="stylesheet">
<style>
@keyframes gly-spin { to { transform: rotate(360deg); } }
.gly-spin { animation: gly-spin 1s infinite linear; }
.panel-section {
    margin-bottom: 25px;
}
.panel-section h4 {
    font-size: 15px;
    font-weight: 600;
    color: #262626;
    margin-bottom: 12px;
    padding-bottom: 8px;
    border-bottom: 1px solid #eee;
}
</style>
{% endblock %}

{% block admin_content %}
<div class="row">
    <div class="col-md-12">
        <h2>{{ "系统设置"|bilingual }}</h2>
        <hr>
    </div>
</div>

<div class="row">
    <!-- 左侧：海关参数 + HS编码明细 -->
    <div class="col-md-8">
        <!-- 海关参数代码表 -->
        <div class="panel panel-default panel-section">
            <div class="panel-heading">
                <h3 class="panel-title">{{ "海关参数代码表"|bilingual }}</h3>
            </div>
            <div class="panel-body">
                <table class="table table-bordered table-striped">
                    <thead>
                        <tr><th>{{ "参数表"|bilingual }}</th><th>{{ "记录数"|bilingual }}</th><th>{{ "启用数"|bilingual }}</th><th>{{ "状态"|bilingual }}</th><th>{{ "操作"|bilingual }}</th></tr>
                    </thead>
                    <tbody id="customs-params-body">
                        <tr><td colspan="5" class="text-center">{{ "加载中..."|bilingual }}</td></tr>
                    </tbody>
                </table>
            </div>
        </div>

        <!-- HS编码明细表 -->
        <div class="panel panel-default panel-section">
            <div class="panel-heading clearfix">
                <h3 class="panel-title pull-left">{{ "HS编码明细"|bilingual }}</h3>
                <div class="pull-right" style="display:flex;align-items:center;gap:6px;">
                    <select class="form-control input-sm" id="hs-chapter-filter" style="width:auto;">
                        <option value="">{{ "全部章节"|bilingual }}</option>
                    </select>
                    <input type="text" class="form-control input-sm" id="hs-search-input" placeholder="{{ "搜索编码/名称"|bilingual }}" style="width:140px;">
                </div>
            </div>
            <div class="panel-body">
                <table class="table table-bordered table-striped table-condensed">
                    <thead>
                        <tr><th>{{ "HS编码"|bilingual }}</th><th>{{ "商品名称"|bilingual }}</th><th>{{ "单位"|bilingual }}</th>
                        <th>{{ "增值税率"|bilingual }}</th><th>{{ "退税率"|bilingual }}</th><th>{{ "最惠国税率"|bilingual }}</th>
                        <th>{{ "出口税率"|bilingual }}</th><th>{{ "消费税率"|bilingual }}</th><th>{{ "章节"|bilingual }}</th><th>{{ "状态"|bilingual }}</th></tr>
                    </thead>
                    <tbody id="hs-table-body">
                        <tr><td colspan="10" class="text-center text-muted">{{ "暂无数据，请先同步HS编码"|bilingual }}</td></tr>
                    </tbody>
                </table>
                <div class="clearfix">
                    <span class="pull-left text-muted" style="line-height:30px;font-size:12px;" id="hs-page-info">{{ "共 0 条"|bilingual }}</span>
                    <div class="pull-right btn-group btn-group-xs" id="hs-pagination"></div>
                    <select class="pull-right form-control input-xs" id="hs-page-size" style="width:90px;height:24px;margin-right:6px;font-size:11px;">
                        <option value="5">5{{ "条/页"|bilingual }}</option>
                        <option value="10">10{{ "条/页"|bilingual }}</option>
                        <option value="20">20{{ "条/页"|bilingual }}</option>
                        <option value="50">50{{ "条/页"|bilingual }}</option>
                    </select>
                </div>
            </div>
        </div>
    </div>

    <!-- 右侧：汇率 + HS编码管理 -->
    <div class="col-md-4">
        <!-- 汇率同步 -->
        <div class="panel panel-info panel-section">
            <div class="panel-heading clearfix">
                <h3 class="panel-title pull-left">{{ "汇率管理"|bilingual }}</h3>
                <button class="btn btn-primary btn-sm pull-right" id="btn-sync-rates">
                    <span class="glyphicon glyphicon-refresh"></span> {{ "同步最新汇率"|bilingual }}
                </button>
            </div>
            <div class="panel-body">
                <div id="rate-status">
                    <p>{{ "上次同步日期"|bilingual }}：<strong id="rate-date-text">-</strong></p>
                    <p>{{ "汇率条数"|bilingual }}：<strong id="rate-count-text">0</strong></p>
                </div>
                <table class="table table-condensed table-bordered" id="rate-preview-table">
                    <thead>
                        <tr><th>{{ "货币"|bilingual }}</th><th>{{ "代码"|bilingual }}</th><th>{{ "兑人民币"|bilingual }}</th></tr>
                    </thead>
                    <tbody id="rate-preview-body">
                        <tr><td colspan="3" class="text-center">{{ "加载中..."|bilingual }}</td></tr>
                    </tbody>
                </table>
            </div>
        </div>

        <!-- HS编码管理 -->
        <div class="panel panel-info panel-section">
            <div class="panel-heading clearfix">
                <h3 class="panel-title pull-left">{{ "HS编码管理"|bilingual }}</h3>
                <label class="pull-right" style="margin-right:12px;line-height:30px;font-weight:normal;font-size:13px;cursor:pointer;">
                    <input type="checkbox" id="chk-sync-tax" style="margin-right:4px;">{{ "同步税率"|bilingual }}
                </label>
                <button class="btn btn-primary btn-sm pull-right" id="btn-sync-hs" disabled>
                    <span class="glyphicon glyphicon-download"></span> {{ "同步选中章节"|bilingual }}
                </button>
            </div>
            <div class="panel-body">
                <div id="hs-stats">
                    <p>{{ "编码总数"|bilingual }}：<strong id="hs-total-text">-</strong>
                       （{{ "有效"|bilingual }} <strong id="hs-active-text">-</strong>）</p>
                </div>
                <div style="max-height:260px;overflow-y:auto;border:1px solid #ddd;border-radius:4px;padding:8px;margin-bottom:10px;">
                    <div class="row" id="hs-chapter-grid">
                        <div class="text-center text-muted" style="width:100%">{{ "加载中..."|bilingual }}</div>
                    </div>
                </div>
                <div style="margin-bottom:8px;">
                    <button class="btn btn-xs btn-default" id="btn-hs-select-all">{{ "全选"|bilingual }}</button>
                    <button class="btn btn-xs btn-default" id="btn-hs-select-none">{{ "取消全选"|bilingual }}</button>
                </div>
                <div id="hs-sync-log" style="display:none;">
                    <div class="alert alert-info" style="padding:6px 12px;margin-bottom:0;">
                        <span class="glyphicon glyphicon-refresh gly-spin"></span>
                        <span id="hs-sync-status">{{ "同步中..."|bilingual }}</span>
                    </div>
                </div>
            </div>
        </div>

        <!-- 数据初始化说明 -->
        <div class="panel panel-default panel-section">
            <div class="panel-heading">
                <h3 class="panel-title">{{ "数据初始化"|bilingual }}</h3>
            </div>
            <div class="panel-body">
                <table class="table table-bordered">
                    <thead>
                        <tr><th>{{ "命令"|bilingual }}</th><th>{{ "说明"|bilingual }}</th></tr>
                    </thead>
                    <tbody>
                        <tr><td><code>init_data</code></td><td>{{ "基础数据（角色、国家等）"|bilingual }}</td></tr>
                        <tr><td><code>init_products</code></td><td>{{ "商品目录数据"|bilingual }}</td></tr>
                        <tr><td><code>sync_exchange_rates</code></td><td>{{ "同步商务部汇率"|bilingual }}</td></tr>
                        <tr><td><code>sync_customs_params</code></td><td>{{ "同步海关参数代码表"|bilingual }}</td></tr>
                        <tr><td><code>sync_hs_codes</code></td><td>{{ "同步HS编码数据"|bilingual }}</td></tr>
                    </tbody>
                </table>
                <p class="text-muted"><small>{{ "在命令行执行"|bilingual }}：<code>python manage.py init_data</code></small></p>
            </div>
        </div>
    </div>
</div>

<!-- 明细查看模态框 -->
<div class="modal fade" id="detailModal" tabindex="-1" role="dialog">
    <div class="modal-dialog modal-lg" role="document">
        <div class="modal-content">
            <div class="modal-header">
                <button type="button" class="close" data-dismiss="modal"><span>&times;</span></button>
                <h4 class="modal-title" id="detail-modal-title">{{ "明细"|bilingual }}</h4>
            </div>
            <div class="modal-body" style="max-height:70vh;overflow-y:auto;">
                <div class="input-group" style="margin-bottom:10px;max-width:300px;">
                    <input type="text" class="form-control" id="detail-search-input" placeholder="{{ "搜索编码或名称..."|bilingual }}">
                    <span class="input-group-btn">
                        <button class="btn btn-default" id="detail-search-btn">{{ "搜索"|bilingual }}</button>
                    </span>
                </div>
                <p class="text-muted"><small id="detail-count-text">{{ "共 0 条"|bilingual }}</small></p>
                <table class="table table-bordered table-striped table-condensed">
                    <thead id="detail-thead"></thead>
                    <tbody id="detail-tbody">
                        <tr><td colspan="10" class="text-center">{{ "加载中..."|bilingual }}</td></tr>
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block extra_js %}
<script src="{% static 'js/admin.js' %}"></script>
<script>
// 保持原有的 system.html JS 逻辑，移除学期管理相关代码
// ... [existing HS codes, exchange rates, customs params code]
</script>
{% endblock %}
```

---

## Task 7: 更新 URL 路由

**Files:**
- Modify: `simtrade/urls.py`

- [ ] **Step 1: 修改 URL 配置，将 `/admin-panel/` 改为 `/admin/`**

找到以下行（约 777-780 行）：
```python
# Admin panel
path('admin-panel/', admin_panel_dashboard, name='admin-dashboard'),
path('admin-panel/users/', admin_panel_users, name='admin-users'),
path('admin-panel/system/', admin_panel_system, name='admin-system'),
```

替换为：
```python
# Admin panel
path('admin/', admin_panel_dashboard, name='admin-dashboard'),
path('admin/users/', admin_panel_users, name='admin-users'),
path('admin/system/', admin_panel_system, name='admin-system'),
```

- [ ] **Step 2: 更新视图函数返回的模板路径**

找到 `admin_panel_dashboard` 函数（约 681 行），修改返回的模板：
```python
# 原来返回 'admin_panel/dashboard.html'
# 改为返回 'admin/dashboard.html'
return render(request, 'admin/dashboard.html', context)
```

找到 `admin_panel_users` 函数（约 689 行），修改返回的模板：
```python
# 原来返回 'admin_panel/user_list.html'
# 改为返回 'admin/user_list.html'
return render(request, 'admin/user_list.html')
```

找到 `admin_panel_system` 函数（约 697 行），修改返回的模板：
```python
# 原来返回 'admin_panel/system.html'
# 改为返回 'admin/system.html'
return render(request, 'admin/system.html')
```

---

## Task 8: 更新顶部导航链接

**Files:**
- Modify: `templates/base.html`

- [ ] **Step 1: 修改顶部导航中的管理后台链接**

找到第 54 行：
```django
{% if user.user_type == 'admin' %}
<li><a href="/admin-panel/">{{ "管理后台"|bilingual }}</a></li>
```

替换为：
```django
{% if user.user_type == 'admin' %}
<li><a href="/admin/">{{ "管理后台"|bilingual }}</a></li>
```

---

## Task 9: 验证功能

**Files:**
- Test: Manual testing in browser

- [ ] **Step 1: 启动开发服务器**

```bash
python manage.py runserver
```

- [ ] **Step 2: 测试访问路径**

用浏览器访问以下 URL，确认页面正常显示：
- `http://localhost:8000/admin/` - 概览页面
- `http://localhost:8000/admin/users/` - 用户管理
- `http://localhost:8000/admin/system/` - 系统设置

- [ ] **Step 3: 验证侧边导航**

确认：
- 左侧导航栏显示正常
- 当前页菜单项高亮
- 点击菜单项可以跳转

- [ ] **Step 4: 验证面包屑导航**

确认面包屑显示正确格式：`首页 > 管理后台 > 当前页面`

- [ ] **Step 5: 验证响应式布局**

缩小浏览器窗口，确认在移动设备下侧边导航在顶部显示

---

## Task 10: 清理废弃文件

**Files:**
- Delete: `templates/admin_panel/dashboard.html`
- Delete: `templates/admin_panel/user_list.html`
- Delete: `templates/admin_panel/system.html`
- Delete: `templates/dashboard/admin.html`

- [ ] **Step 1: 删除旧的 admin_panel 模板文件**

```bash
# Windows
del templates\admin_panel\dashboard.html
del templates\admin_panel\user_list.html
del templates\admin_panel\system.html

# 或者在 Git Bash 中
rm templates/admin_panel/dashboard.html
rm templates/admin_panel/user_list.html
rm templates/admin_panel/system.html
```

- [ ] **Step 2: 删除旧的 dashboard/admin.html**

```bash
# Windows
del templates\dashboard\admin.html

# 或者在 Git Bash 中
rm templates/dashboard/admin.html
```

- [ ] **Step 3: 删除空的 admin_panel 目录（如果有）**

```bash
# Windows
rmdir templates\admin_panel

# 或者在 Git Bash 中
rmdir templates/admin_panel
```

---

## Task 11: 提交代码

**Files:**
- Git commit

- [ ] **Step 1: 查看更改状态**

```bash
git status
```

- [ ] **Step 2: 添加所有更改**

```bash
git add .
```

- [ ] **Step 3: 提交代码**

```bash
git commit -m "refactor: unify admin navigation to /admin/ with sidebar

- Create admin base template with sidebar navigation
- Migrate admin-panel URLs to admin URLs
- Add breadcrumb navigation
- Optimize system settings page layout
- Remove duplicate admin dashboard

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## 测试清单

完成实现后，验证以下功能：

- [ ] `/admin/` 概览页面显示统计卡片和图表
- [ ] `/admin/users/` 用户管理页面正常工作
- [ ] `/admin/system/` 系统设置页面正常工作
- [ ] 侧边导航在所有页面显示
- [ ] 当前页菜单项正确高亮
- [ ] 面包屑导航正确显示
- [ ] 顶部导航链接指向正确的 URL
- [ ] 移动设备下布局正常
- [ ] 旧路径 `/admin-panel/` 返回 404（已迁移）
