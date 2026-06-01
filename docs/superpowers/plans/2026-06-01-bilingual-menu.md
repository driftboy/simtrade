# 双语菜单实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**目标:** 为 SimTrade 系统添加中英文双语菜单和标签，格式为 `中文-English`。

**架构:** 使用 Django 自定义模板过滤器 `bilingual`，创建翻译映射表，在模板中应用过滤器。

**技术栈:** Django 模板系统、Python

---

## 文件结构概览

```
simtrade/
├── simtrade/
│   ├── templatetags/              # 新建目录
│   │   ├── __init__.py           # 新建：空文件，使目录成为Python包
│   │   └── bilingual.py          # 新建：双语过滤器及翻译表
├── templates/
│   ├── base.html                 # 修改：主导航菜单
│   ├── dashboard/
│   │   ├── student.html          # 修改：学生仪表盘标签
│   │   ├── teacher.html          # 修改：教师仪表盘标签
│   │   └── admin.html            # 修改：管理员仪表盘标签
│   └── workspace/
│       └── workspace.html        # 修改：工作台tab标签
```

---

## Task 1: 创建模板过滤器目录结构

**文件:**
- Create: `simtrade/templatetags/__init__.py`
- Create: `simtrade/templatetags/bilingual.py`

- [ ] **Step 1: 创建 templatetags 目录**

```bash
mkdir -p f:/vsworkspace/simtrade/simtrade/templatetags
```

- [ ] **Step 2: 创建 __init__.py 文件**

```bash
touch f:/vsworkspace/simtrade/simtrade/templatetags/__init__.py
```

- [ ] **Step 3: 验证目录结构**

```bash
ls -la f:/vsworkspace/simtrade/simtrade/templatetags/
```

Expected: 显示 `__init__.py` 文件

- [ ] **Step 4: 提交**

```bash
git add simtrade/templatetags/__init__.py
git commit -m "feat: create templatetags directory structure"
```

---

## Task 2: 实现双语过滤器

**文件:**
- Create: `simtrade/templatetags/bilingual.py`

- [ ] **Step 1: 创建 bilingual.py 过滤器文件**

```python
"""
双语过滤器 - 为中文标签添加英文翻译
格式：中文-English
"""
from django import template

register = template.Library()

# 翻译映射表：中文 -> 英文
TRANSLATION_MAP = {
    # 主导航
    '仪表盘': 'Dashboard',
    '工作台': 'Workspace',
    '教学管理': 'Teaching Management',
    '管理后台': 'Admin Panel',
    '市场': 'Market',
    '交易': 'Transactions',
    '单证': 'Documents',
    '个人中心': 'Profile',
    '退出登录': 'Logout',
    '登录': 'Login',
    '注册': 'Register',

    # 学生仪表盘
    '活跃交易': 'Active Transactions',
    '我的单证': 'My Documents',
    '待处理单证': 'Pending Documents',
    '未读通知': 'Unread Notifications',
    '市场大厅': 'Market Hall',
    '我的交易': 'My Transactions',
    '单证管理': 'Document Management',
    '待审核反馈': 'Pending Review Feedback',
    '即将到期交易': 'Expiring Transactions',

    # 教师仪表盘
    '我的课程': 'My Courses',
    '我的班级': 'My Classes',
    '待批改单证': 'Pending Grading',
    '成绩管理': 'Grade Management',
    '课程管理': 'Course Management',

    # 管理员仪表盘
    '注册用户': 'Registered Users',
    '单证总数': 'Total Documents',
    '课程总数': 'Total Courses',
    '待审核单证': 'Pending Review',
    '用户管理': 'User Management',
    '系统设置': 'System Settings',

    # 通用
    '最近活动': 'Recent Activity',
    '待办事项': 'To-Do List',
    '快捷入口': 'Quick Links',
    '暂无数据': 'No Data',
    '加载中': 'Loading',
    '暂无活动': 'No Activity',
    '暂无待办': 'No Tasks',
    '数据加载失败': 'Data Load Failed',
    '我的单证状态': 'My Document Status',
    '交易进度': 'Transaction Progress',
    '角色分布': 'Role Distribution',
    '课程进度分布': 'Course Progress Distribution',
    '学生单证状态': 'Student Document Status',
    '班级活跃度': 'Class Activity',
    '单证类型分布': 'Document Type Distribution',
    '用户类型分布': 'User Type Distribution',
    '单证状态分布': 'Document Status Distribution',
}


@register.filter
def bilingual(text, english=None):
    """
    将中文文本转换为双语格式：中文-English

    用法:
        {{ "仪表盘"|bilingual }}        → 仪表盘-Dashboard
        {{ "自定义"|bilingual:"Custom" }} → 自定义-Custom
    """
    if not text:
        return text

    # 如果提供了英文参数，优先使用
    if english:
        return f"{text}-{english}"

    # 查翻译表
    english = TRANSLATION_MAP.get(text)

    # 如果找到翻译，返回双语格式
    if english:
        return f"{text}-{english}"

    # 未找到翻译，返回原文
    return text
```

- [ ] **Step 2: 提交**

```bash
git add simtrade/templatetags/bilingual.py
git commit -m "feat: add bilingual template filter with translation map"
```

---

## Task 3: 修改主导航菜单 (base.html)

**文件:**
- Modify: `templates/base.html`

- [ ] **Step 1: 在 base.html 顶部加载 bilingual 标签库**

在第 2 行 `{% load static %}` 后添加：

```django
{% load static %}
{% load bilingual %}
```

- [ ] **Step 2: 修改主导航菜单项**

找到第 43-60 行的导航菜单项，修改为：

```django
<ul class="nav navbar-nav">
    <li><a href="/dashboard/">{{ "仪表盘"|bilingual }}</a></li>
    {% if user.is_authenticated %}
        {% if user.user_type == 'student' %}
        <li><a href="/workspace/">{{ "工作台"|bilingual }}</a></li>
        {% endif %}
        {% if user.user_type == 'teacher' %}
        <li><a href="/teaching/">{{ "教学管理"|bilingual }}</a></li>
        {% endif %}
        {% if user.user_type == 'admin' %}
        <li><a href="/admin-panel/">{{ "管理后台"|bilingual }}</a></li>
        <li><a href="/teaching/">{{ "教学管理"|bilingual }}</a></li>
        {% endif %}
        <li><a href="/market/">{{ "市场"|bilingual }}</a></li>
        <li><a href="/transactions/">{{ "交易"|bilingual }}</a></li>
        <li><a href="/documents/">{{ "单证"|bilingual }}</a></li>
    {% endif %}
</ul>
```

- [ ] **Step 3: 修改用户菜单**

找到第 83-91 行的用户下拉菜单，修改为：

```django
<ul class="dropdown-menu">
    <li><a href="/profile/">{{ "个人中心"|bilingual }}</a></li>
    <li role="separator" class="divider"></li>
    <li><a href="#" id="logout-link">{{ "退出登录"|bilingual }}</a></li>
</ul>
```

- [ ] **Step 4: 修改登录/注册菜单**

找到第 94-95 行，修改为：

```django
<li><a href="/login/">{{ "登录"|bilingual }}</a></li>
<li><a href="/register/">{{ "注册"|bilingual }}</a></li>
```

- [ ] **Step 5: 提交**

```bash
git add templates/base.html
git commit -m "feat: apply bilingual filter to main navigation menu"
```

---

## Task 4: 修改学生仪表盘 (student.html)

**文件:**
- Modify: `templates/dashboard/student.html`

- [ ] **Step 1: 在 student.html 顶部加载 bilingual 标签库**

在第 2 行 `{% load static %}` 后添加：

```django
{% load static %}
{% load bilingual %}
```

- [ ] **Step 2: 修改统计卡片标签**

找到第 78-107 行的统计卡片，修改 dash-stat-label：

```django
<div class="dash-stat-info">
    <div class="dash-stat-label">{{ "活跃交易"|bilingual }}</div>
</div>
```

```django
<div class="dash-stat-info">
    <div class="dash-stat-label">{{ "我的单证"|bilingual }}</div>
</div>
```

```django
<div class="dash-stat-info">
    <div class="dash-stat-label">{{ "待处理单证"|bilingual }}</div>
</div>
```

```django
<div class="dash-stat-info">
    <div class="dash-stat-label">{{ "未读通知"|bilingual }}</div>
</div>
```

- [ ] **Step 3: 修改图表标题**

找到第 131-153 行的图表标题：

```django
<div class="panel-heading"><h3 class="panel-title">{{ "我的单证状态"|bilingual }}</h3></div>
```

```django
<div class="panel-heading"><h3 class="panel-title">{{ "交易进度"|bilingual }}</h3></div>
```

```django
<div class="panel-heading"><h3 class="panel-title">{{ "角色分布"|bilingual }}</h3></div>
```

- [ ] **Step 4: 修改活动/待办面板标题**

找到第 159-173 行：

```django
<div class="panel-heading"><h3 class="panel-title">{{ "最近活动"|bilingual }}</h3></div>
```

```django
<div class="panel-heading"><h3 class="panel-title">{{ "待办事项"|bilingual }}</h3></div>
```

- [ ] **Step 5: 修改快捷入口**

找到第 179-195 行的快捷入口链接：

```django
<div class="panel-heading"><h3 class="panel-title">{{ "快捷入口"|bilingual }}</h3></div>
```

```django
<a href="/workspace/" class="dash-quick-link">
    <span class="glyphicon glyphicon-briefcase"></span> {{ "工作台"|bilingual }}
</a>
<a href="/market/" class="dash-quick-link">
    <span class="glyphicon glyphicon-shopping-cart"></span> {{ "市场大厅"|bilingual }}
</a>
<a href="/transactions/" class="dash-quick-link">
    <span class="glyphicon glyphicon-list"></span> {{ "我的交易"|bilingual }}
</a>
<a href="/documents/" class="dash-quick-link">
    <span class="glyphicon glyphicon-file"></span> {{ "单证管理"|bilingual }}
</a>
```

- [ ] **Step 6: 提交**

```bash
git add templates/dashboard/student.html
git commit -m "feat: apply bilingual filter to student dashboard"
```

---

## Task 5: 修改教师仪表盘 (teacher.html)

**文件:**
- Modify: `templates/dashboard/teacher.html`

- [ ] **Step 1: 在 teacher.html 顶部加载 bilingual 标签库**

在第 2 行 `{% load static %}` 后添加：

```django
{% load static %}
{% load bilingual %}
```

- [ ] **Step 2: 修改统计卡片标签**

找到第 74-120 行的统计卡片：

```django
<div class="dash-stat-label">{{ "我的课程"|bilingual }}</div>
```

```django
<div class="dash-stat-label">{{ "我的班级"|bilingual }}</div>
```

```django
<div class="dash-stat-label">{{ "待批改单证"|bilingual }}</div>
```

```django
<div class="dash-stat-label">{{ "成绩管理"|bilingual }}</div>
```

- [ ] **Step 3: 修改图表标题**

找到第 126-148 行：

```django
<div class="panel-heading"><h3 class="panel-title">{{ "课程进度分布"|bilingual }}</h3></div>
```

```django
<div class="panel-heading"><h3 class="panel-title">{{ "学生单证状态"|bilingual }}</h3></div>
```

```django
<div class="panel-heading"><h3 class="panel-title">{{ "班级活跃度"|bilingual }}</h3></div>
```

- [ ] **Step 4: 修改活动/待办面板标题**

找到第 154-168 行：

```django
<div class="panel-heading"><h3 class="panel-title">{{ "最近活动"|bilingual }}</h3></div>
```

```django
<div class="panel-heading"><h3 class="panel-title">{{ "待办事项"|bilingual }}</h3></div>
```

- [ ] **Step 5: 修改快捷入口**

找到第 174-194 行：

```django
<div class="panel-heading"><h3 class="panel-title">{{ "快捷入口"|bilingual }}</h3></div>
```

```django
<a href="/teaching/" class="dash-quick-link">
    <span class="glyphicon glyphicon-blackboard"></span> {{ "教学管理"|bilingual }}
</a>
<a href="/teaching/grading/" class="dash-quick-link">
    <span class="glyphicon glyphicon-check"></span> {{ "成绩管理"|bilingual }}
</a>
<a href="/teaching/courses/" class="dash-quick-link">
    <span class="glyphicon glyphicon-list"></span> {{ "课程管理"|bilingual }}
</a>
<a href="/documents/" class="dash-quick-link">
    <span class="glyphicon glyphicon-file"></span> {{ "单证管理"|bilingual }}
</a>
```

- [ ] **Step 6: 提交**

```bash
git add templates/dashboard/teacher.html
git commit -m "feat: apply bilingual filter to teacher dashboard"
```

---

## Task 6: 修改管理员仪表盘 (admin.html)

**文件:**
- Modify: `templates/dashboard/admin.html`

- [ ] **Step 1: 在 admin.html 顶部加载 bilingual 标签库**

在第 2 行 `{% load static %}` 后添加：

```django
{% load static %}
{% load bilingual %}
```

- [ ] **Step 2: 修改统计卡片标签**

找到第 72-118 行的统计卡片：

```django
<div class="dash-stat-label">{{ "注册用户"|bilingual }}</div>
```

```django
<div class="dash-stat-label">{{ "单证总数"|bilingual }}</div>
```

```django
<div class="dash-stat-label">{{ "课程总数"|bilingual }}</div>
```

```django
<div class="dash-stat-label">{{ "待审核单证"|bilingual }}</div>
```

- [ ] **Step 3: 修改图表标题**

找到第 124-146 行：

```django
<div class="panel-heading"><h3 class="panel-title">{{ "单证类型分布"|bilingual }}</h3></div>
```

```django
<div class="panel-heading"><h3 class="panel-title">{{ "用户类型分布"|bilingual }}</h3></div>
```

```django
<div class="panel-heading"><h3 class="panel-title">{{ "单证状态分布"|bilingual }}</h3></div>
```

- [ ] **Step 4: 修改活动/待办面板标题**

找到第 151-166 行：

```django
<div class="panel-heading"><h3 class="panel-title">{{ "最近活动"|bilingual }}</h3></div>
```

```django
<div class="panel-heading"><h3 class="panel-title">{{ "待办事项"|bilingual }}</h3></div>
```

- [ ] **Step 5: 修改快捷入口**

找到第 172-195 行：

```django
<div class="panel-heading"><h3 class="panel-title">{{ "快捷入口"|bilingual }}</h3></div>
```

```django
<a href="/admin-panel/users/" class="dash-quick-link">
    <span class="glyphicon glyphicon-user"></span> {{ "用户管理"|bilingual }}
</a>
<a href="/admin-panel/system/" class="dash-quick-link">
    <span class="glyphicon glyphicon-cog"></span> {{ "系统设置"|bilingual }}
</a>
<a href="/teaching/" class="dash-quick-link">
    <span class="glyphicon glyphicon-book"></span> {{ "教学管理"|bilingual }}
</a>
<a href="/documents/" class="dash-quick-link">
    <span class="glyphicon glyphicon-file"></span> {{ "单证管理"|bilingual }}
</a>
<a href="/market/" class="dash-quick-link">
    <span class="glyphicon glyphicon-shopping-cart"></span> {{ "市场大厅"|bilingual }}
</a>
```

- [ ] **Step 6: 提交**

```bash
git add templates/dashboard/admin.html
git commit -m "feat: apply bilingual filter to admin dashboard"
```

---

## Task 7: 修改工作台 Tab 标签 (workspace.html)

**文件:**
- Modify: `templates/workspace/workspace.html`

- [ ] **Step 1: 在 workspace.html 顶部加载 bilingual 标签库**

在第 2 行 `{% load static %}` 后添加：

```django
{% load static %}
{% load bilingual %}
```

- [ ] **Step 2: 修改 tab 导航标签**

找到第 29-35 行的 tab 导航，修改为：

```django
<ul class="nav nav-tabs" id="workspace-tab-nav" role="tablist">
    {% for nav in role_config.nav_items %}
    <li role="presentation"{% if forloop.first %} class="active"{% endif %}>
        <a href="#list-{{ forloop.counter }}" data-tab="{{ forloop.counter }}" data-api="{{ nav.api }}" aria-controls="list-{{ forloop.counter }}" role="tab" data-toggle="tab">{{ nav.label|bilingual }}</a>
    </li>
    {% endfor %}
</ul>
```

- [ ] **Step 3: 修改加载中提示文本**

找到第 40-42 行，修改为：

```django
<div class="text-center" style="padding: 40px; color: #999;">
    <span class="spinner"></span> {{ "加载中"|bilingual }}
</div>
```

- [ ] **Step 4: 提交**

```bash
git add templates/workspace/workspace.html
git commit -m "feat: apply bilingual filter to workspace tabs"
```

---

## Task 8: 验证测试

- [ ] **Step 1: 启动开发服务器**

```bash
cd f:/vsworkspace/simtrade
python manage.py runserver
```

- [ ] **Step 2: 访问主页验证主导航**

访问: `http://localhost:8000/`

检查项:
- [ ] 仪表盘 显示为 `仪表盘-Dashboard`
- [ ] 市场显示为 `市场-Market`
- [ ] 交易显示为 `交易-Transactions`
- [ ] 单证显示为 `单证-Documents`
- [ ] 个人中心显示为 `个人中心-Profile`
- [ ] 退出登录显示为 `退出登录-Logout`
- [ ] 登录显示为 `登录-Login`
- [ ] 注册显示为 `注册-Register`

- [ ] **Step 3: 访问学生仪表盘**

访问: `http://localhost:8000/dashboard/` (以学生身份登录)

检查项:
- [ ] 统计卡片标签显示双语
- [ ] 图表标题显示双语
- [ ] 快捷入口显示双语
- [ ] 待办事项标签显示双语

- [ ] **Step 4: 访问教师仪表盘**

访问: `http://localhost:8000/dashboard/` (以教师身份登录)

检查项:
- [ ] 统计卡片标签显示双语
- [ ] 图表标题显示双语
- [ ] 快捷入口显示双语

- [ ] **Step 5: 访问管理员仪表盘**

访问: `http://localhost:8000/dashboard/` (以管理员身份登录)

检查项:
- [ ] 统计卡片标签显示双语
- [ ] 图表标题显示双语
- [ ] 快捷入口显示双语

- [ ] **Step 6: 访问工作台**

访问: `http://localhost:8000/workspace/` (以学生身份登录，选择角色后)

检查项:
- [ ] Tab 标签显示为双语格式
- [ ] 加载中提示显示双语

- [ ] **Step 7: 检查模板语法错误**

查看浏览器控制台和服务器日志，确认无模板语法错误。

- [ ] **Step 8: 最终提交**

```bash
git add .
git commit -m "test: verify bilingual menu implementation complete"
```

---

## 完成检查清单

实施完成后，验证以下内容：

- [ ] 所有主导航菜单项显示为双语格式
- [ ] 各仪表盘统计卡片标签显示为双语格式
- [ ] 快捷入口链接显示为双语格式
- [ ] 工作台Tab标签显示为双语格式
- [ ] 空状态提示文本显示为双语格式
- [ ] 所有页面正常加载，无模板语法错误
- [ ] 英文翻译准确、专业
