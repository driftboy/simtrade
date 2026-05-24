# 前端页面与角色工作台设计

日期: 2026-05-24
状态: 已批准

## 概述

完善 SimTrade 三端（学生端、教师端、管理端）的前端页面，为 10 种贸易角色建立专属工作台，补充缺失的后端 API（LetterOfCredit ViewSet、注册端点）。

技术栈: Bootstrap 3.3.7 + jQuery + Django Templates（与现有代码一致）。

## 页面路由

```
/                           → 重定向到仪表盘
/dashboard/                 → 根据 user_type 分发

/workspace/                 → 当前活跃角色的工作台
/workspace/<role_code>/     → 指定角色的工作台

/market/                    → 已有
/transactions/              → 已有
/transactions/<id>/         → 已有
/documents/                 → 已有
/documents/create/          → 已有
/documents/<id>/preview/    → 已有

/teaching/                  → 教学仪表盘
/teaching/courses/          → 课程列表
/teaching/courses/<id>/     → 课程详情
/teaching/experiments/      → 实验管理
/teaching/grading/          → 评分

/admin-panel/               → 管理仪表盘
/admin-panel/users/         → 用户管理
/admin-panel/system/        → 系统配置

/register/                  → 注册页面
/profile/                   → 个人中心
```

## 后端补充

### LetterOfCredit ViewSet

模型和序列化器已存在（`apps/transactions/models.py` L273-394），需补建 ViewSet 和 URL 注册。

API 端点:

| 方法 | URL | 说明 | 角色 |
|------|-----|------|------|
| GET | `/api/v1/letters-of-credit/` | 列表（按角色过滤） | 全部 |
| POST | `/api/v1/letters-of-credit/` | 申请开证 | 进口商 |
| GET | `/api/v1/letters-of-credit/<id>/` | 详情 | 全部 |
| POST | `.../<id>/issue/` | 开证 | 银行 |
| POST | `.../<id>/advise/` | 通知 | 银行 |
| POST | `.../<id>/submit_docs/` | 交单 | 出口商 |
| POST | `.../<id>/negotiate/` | 议付 | 银行 |
| POST | `.../<id>/pay/` | 付款 | 银行 |
| POST | `.../<id>/cancel/` | 取消 | 申请方 |

LC 状态流转: 草稿 → 待开证 → 已开证 → 已交单 → 已议付 → 已付款，支持"已开证 → 修改中 → 已开证"分支。

### 注册端点

`POST /api/v1/auth/register/` — 学生自注册。

字段: username(必填), password(必填), email(必填), student_id(选填)。注册后 user_type 默认 `student`。

### Workspace Django View

Django view 函数（非 lambda），查当前角色后渲染对应面板:

```python
PANEL_MAP = {
    'exporter': 'trader',    'importer': 'trader',
    'customs': 'approver',   'inspection': 'approver',
    'forex': 'approver',     'tax': 'approver',
    'factory': 'provider',   'bank': 'provider',
    'shipping': 'provider',  'insurance': 'provider',
}
```

角色配置 `ROLE_CONFIGS` 字典定义每个角色的导航菜单、统计指标 API、列表 API、快捷操作。

### Dashboard View

根据 `user.user_type` 分发到对应仪表盘模板。

## 模板结构

```
templates/
├── base.html                       # 已有，修改 navbar 菜单条件化
├── dashboard/
│   ├── student.html                # 学生仪表盘
│   ├── teacher.html                # 教师仪表盘
│   └── admin.html                  # 管理员仪表盘
├── workspace/
│   ├── base.html                   # 工作台 base（双栏布局）
│   ├── workspace.html              # 通用工作台主模板
│   └── panels/
│       ├── trader.html             # 贸易发起方面板（出口商/进口商）
│       ├── approver.html           # 审批处理方面板（海关/商检/外汇/税务）
│       └── provider.html           # 服务提供方面板（工厂/银行/货运/保险）
├── teaching/
│   ├── dashboard.html              # 教学仪表盘
│   ├── course_list.html            # 课程列表
│   ├── course_detail.html          # 课程详情
│   └── grading.html                # 评分管理
├── admin_panel/
│   ├── dashboard.html              # 管理仪表盘
│   ├── user_list.html              # 用户管理
│   └── system.html                 # 系统配置
├── registration/
│   └── register.html               # 注册页面
└── profile.html                    # 个人中心
```

共 ~17 个新模板。

## 三种工作台 UI 模式

### 贸易发起方（出口商、进口商）

统计卡片: 活跃交易数 | 待签约数 | 进行中数
Tab 导航: 我的交易 | 外销合同 | 信用证
列表: 交易列表（可创建新交易）
快捷操作: + 发询盘、查看合同、申请信用证
数据源: `/api/v1/transactions/`, `/api/v1/contracts/`, `/api/v1/letters-of-credit/`

### 审批处理方（海关、商检、外汇局、税务局）

统计卡片: 待处理数 | 已完成数 | 已驳回数
Tab 导航: 待处理 | 已处理 | 全部
列表: 申报/申请列表（每行有审核/批准操作按钮）
数据源按角色:
- 海关: `/api/v1/customs-declarations/`
- 商检: `/api/v1/inspection-applications/`
- 外汇局: `/api/v1/forex-settlements/`
- 税务局: `/api/v1/tax-refund-applications/`

### 服务提供方（工厂、银行、货运、保险）

统计卡片: 待接单数 | 执行中数 | 已完成数
Tab 导航: 待处理 | 执行中 | 已完成
列表: 订单/保单列表（每行有接单/执行操作按钮）
数据源按角色:
- 工厂: `/api/v1/purchase-orders/`
- 银行: `/api/v1/letters-of-credit/`
- 货运: `/api/v1/shipments/`
- 保险: `/api/v1/insurance-policies/`

## 工作台布局

workspace/base.html 使用独立双栏布局，不修改全局 base.html 的 container 单栏:

- 左侧面板: 当前角色名称 + 导航菜单 + 快捷操作
- 右侧主区: 统计卡片行 + Tab 导航 + 数据列表 + 分页

导航菜单和快捷操作由 Django view 通过 `ROLE_CONFIGS` context 渲染，列表数据由 jQuery AJAX 从 API 加载。

## 仪表盘设计

### 学生仪表盘

统计卡片: 活跃角色数 | 进行中交易 | 待处理单证 | 未读通知
两栏: 最近交易动态 | 待办事项
底部: 进入工作台 / 查看市场 按钮

### 教师仪表盘

统计卡片: 我的课程 | 活跃班级 | 待评分 | 待审核角色
两栏: 课程概览（课程名+人数）| 待处理事项（角色申请+作业评分+实验评分）

### 管理员仪表盘

统计卡片: 注册用户 | 活跃学期 | 虚拟公司 | 交易总量
两栏: 系统状态 | 最近活动

## Navbar 扩展

base.html 的 navbar 按用户类型条件渲染:

| 用户类型 | 菜单项 |
|---------|--------|
| 未登录 | 登录、注册 |
| 学生 | 仪表盘、工作台、市场、交易、单证 |
| 教师 | 仪表盘、教学管理、市场、交易、单证 |
| 管理员 | 仪表盘、管理后台、教学管理、市场、交易 |

## 教师端页面

### 教学仪表盘

学期选择器 + 课程卡片列表（名称、班级数、学生数、状态）+ 创建课程快捷按钮。

### 课程列表

当前学期课程表格，支持创建课程弹窗。

### 课程详情

课程信息 + 三个 Tab（班级/实验/作业）。班级管理: 查看学生、生成邀请码。实验管理: 创建实验、分组、启动/结束。

### 评分管理

选择实验 → 查看学生成绩单表格 → 调整分数 → 提交。数据源: `/api/v1/teaching/reports/class_report/`。

## 管理端页面

### 管理仪表盘

全局统计卡片 + 最近注册用户列表 + 快捷入口。

### 用户管理

用户表格，支持按类型筛选和搜索。操作: 编辑用户类型、重置密码、禁用。

### 系统配置

学期管理（创建/激活/结束）+ 数据初始化按钮（调用 init_data 等 management commands）+ 角色审批列表。

## 注册页面

表单字段: 用户名、密码、确认密码、邮箱、学号(选填)。AJAX 提交，成功后跳转登录页。

## 个人中心

用户信息展示与编辑 + 所有角色列表 + 修改密码。

## 静态文件

### 新增 JS

| 文件 | 职责 |
|------|------|
| `static/js/workspace.js` | 工作台: 加载统计、列表、执行操作 |
| `static/js/dashboard.js` | 仪表盘: 统计卡片、最近动态、待办 |
| `static/js/teaching.js` | 教学端: 课程管理、实验、评分 |
| `static/js/admin.js` | 管理端: 用户管理、系统配置 |

### 新增 CSS

| 文件 | 职责 |
|------|------|
| `static/css/workspace.css` | 工作台双栏布局、侧边栏、统计卡片 |
| `static/css/dashboard.css` | 仪表盘样式 |
| `static/css/teaching.css` | 教学端样式 |

## 文件改动汇总

### 后端改动（4 个文件）

| 文件 | 改动 |
|------|------|
| `apps/transactions/views.py` | 新增 LetterOfCreditViewSet |
| `apps/transactions/urls.py` | 注册 LC router |
| `apps/users/views.py` | 新增 RegisterView |
| `simtrade/urls.py` | 新增页面路由和 Django view 函数 |

### 前端新增（~20 个文件）

17 个 HTML 模板 + 4 个 JS + 3 个 CSS。

### 现有文件修改（3 个文件）

| 文件 | 改动范围 |
|------|---------|
| `templates/base.html` | navbar 菜单条件化（~15 行） |
| `static/js/role-switcher.js` | 切换后跳转 `/workspace/`（1 行） |
| `static/css/custom.css` | 可能需微调 |
