# 双语菜单设计文档

**日期**: 2026-06-01
**状态**: 待实施
**作者**: Claude

---

## 1. 概述

将 SimTrade 系统中的所有菜单名称和标签改为中英文双语格式，格式为 `中文-English`，使用短横线连接。

### 设计目标

- 统一所有菜单和标签的显示格式
- 采用可维护的实现方式，便于后续扩展
- 保持代码整洁，避免硬编码重复

---

## 2. 实现方案

采用 **Django 模板过滤器** 方案，创建自定义过滤器 `bilingual`。

### 2.1 方案选择理由

| 方案 | 优点 | 缺点 | 结论 |
|------|------|------|------|
| Django模板过滤器 | 集中管理、易维护、符合Django最佳实践 | 需创建新文件 | **采用** |
| JavaScript替换 | 无需后端修改 | 闪烁问题、SEO不友好 | 不采用 |
| 硬编码替换 | 简单直接 | 难维护、代码重复 | 不采用 |

---

## 3. 翻译表设计

### 3.1 内置翻译映射表

| 中文 | 英文 | 上下文 |
|------|------|--------|
| 仪表盘 | Dashboard | 通用 |
| 工作台 | Workspace | 学生角色工作区 |
| 教学管理 | Teaching Management | 教师专区 |
| 管理后台 | Admin Panel | 管理员专区 |
| 市场 | Market | 市场大厅 |
| 交易 | Transactions | 交易管理 |
| 单证 | Documents | 单证管理 |
| 个人中心 | Profile | 用户个人信息 |
| 退出登录 | Logout | |
| 登录 | Login | |
| 注册 | Register | |
| 活跃交易 | Active Transactions | 学生仪表盘 |
| 我的单证 | My Documents | 学生仪表盘 |
| 待处理单证 | Pending Documents | 通用 |
| 未读通知 | Unread Notifications | 学生仪表盘 |
| 市场大厅 | Market Hall | 快捷入口 |
| 我的交易 | My Transactions | 快捷入口 |
| 单证管理 | Document Management | 快捷入口 |
| 我的课程 | My Courses | 教师仪表盘 |
| 我的班级 | My Classes | 教师仪表盘 |
| 待批改单证 | Pending Grading | 教师仪表盘 |
| 成绩管理 | Grade Management | 教师专区 |
| 课程管理 | Course Management | 教师专区 |
| 注册用户 | Registered Users | 管理员统计 |
| 单证总数 | Total Documents | 管理员统计 |
| 课程总数 | Total Courses | 管理员统计 |
| 待审核单证 | Pending Review | 管理员统计 |
| 待审核反馈 | Pending Review Feedback | 学生待办 |
| 即将到期交易 | Expiring Transactions | 学生待办 |
| 用户管理 | User Management | 管理员专区 |
| 系统设置 | System Settings | 管理员专区 |
| 最近活动 | Recent Activity | 仪表盘 |
| 待办事项 | To-Do List | 仪表盘 |
| 快捷入口 | Quick Links | 仪表盘 |
| 暂无数据 | No Data | 空状态 |
| 加载中 | Loading | |
| 暂无活动 | No Activity | |
| 暂无待办 | No Tasks | |
| 数据加载失败 | Data Load Failed | |

---

## 4. 文件结构

```
simtrade/
├── simtrade/
│   ├── templatetags/              # 新建目录
│   │   ├── __init__.py           # 新建
│   │   └── bilingual.py          # 新建：双语过滤器
├── templates/
│   ├── base.html                 # 需要修改：主导航
│   ├── dashboard/
│   │   ├── student.html          # 需要修改
│   │   ├── teacher.html          # 需要修改
│   │   └── admin.html            # 需要修改
│   └── workspace/
│       └── workspace.html        # 需要修改：tab标签
```

---

## 5. 过滤器设计

### 5.1 使用方式

```django
{% load bilingual %}

# 使用内置翻译表
{{ "仪表盘"|bilingual }}  →  仪表盘-Dashboard

# 自定义英文翻译
{{ "自定义名称"|bilingual:"Custom Name" }}  →  自定义名称-Custom Name
```

### 5.2 过滤器逻辑

1. 接收中文字符串作为输入
2. 查内置翻译表查找对应英文
3. 如果有参数，优先使用参数作为英文
4. 返回格式：`中文-English`

---

## 6. 模板修改清单

### 6.1 templates/base.html

**位置**: 第 30-100 行，主导航菜单

需要修改的菜单项：
- 仪表盘
- 工作台
- 教学管理
- 管理后台
- 市场
- 交易
- 单证
- 个人中心
- 退出登录
- 登录
- 注册

### 6.2 templates/dashboard/student.html

**位置**: 统计卡片、快捷入口区域

需要修改的标签：
- 活跃交易
- 我的单证
- 待处理单证
- 未读通知
- 工作台
- 市场大厅
- 我的交易
- 单证管理
- 最近活动
- 待办事项
- 快捷入口
- 我的单证状态
- 交易进度
- 角色分布

### 6.3 templates/dashboard/teacher.html

**位置**: 统计卡片、快捷入口区域

需要修改的标签：
- 我的课程
- 我的班级
- 待批改单证
- 成绩管理
- 教学管理
- 课程管理
- 单证管理
- 课程进度分布
- 学生单证状态
- 班级活跃度
- 最近活动
- 待办事项
- 快捷入口

### 6.4 templates/dashboard/admin.html

**位置**: 统计卡片、快捷入口区域

需要修改的标签：
- 注册用户
- 单证总数
- 课程总数
- 待审核单证
- 用户管理
- 系统设置
- 教学管理
- 单证管理
- 市场大厅
- 单证类型分布
- 用户类型分布
- 单证状态分布
- 最近活动
- 待办事项
- 快捷入口

### 6.5 templates/workspace/workspace.html

**位置**: 第 27-46 行，Tab 导航

**处理方式**: 动态标签使用过滤器包装

```django
{% for nav in role_config.nav_items %}
    <a ...>{{ nav.label|bilingual }}</a>
{% endfor %}
```

---

## 7. 验证标准

实施完成后，需验证以下内容：

1. 所有主导航菜单项显示为双语格式
2. 各仪表盘统计卡片标签显示为双语格式
3. 快捷入口链接显示为双语格式
4. 工作台Tab标签显示为双语格式
5. 空状态提示文本（如"暂无数据"）显示为双语格式
6. 所有页面正常加载，无模板语法错误
7. 英文翻译准确、专业

---

## 8. 后续扩展

本设计预留了扩展空间，将来可支持：

- 纯英文模式：修改过滤器返回逻辑
- 语言切换：结合用户设置动态返回
- 更多语言：扩展翻译表支持多语言

---

## 9. 文档版本历史

| 版本 | 日期 | 变更说明 |
|------|------|----------|
| 1.0 | 2026-06-01 | 初始版本 |
