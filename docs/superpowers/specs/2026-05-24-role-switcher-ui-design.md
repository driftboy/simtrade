# 角色切换器 UI 设计文档

**版本**: 1.0
**日期**: 2026-05-24
**状态**: 待审核

---

## 1. 概述

### 1.1 设计目标

在导航栏添加角色切换器，让已登录用户可以一键查看和切换已激活的贸易角色。

### 1.2 核心决策

| 决策点 | 选择 | 理由 |
|--------|------|------|
| UI 位置 | 导航栏用户名左侧 dropdown | 与现有导航栏 dropdown 风格一致，操作路径最短 |
| 技术栈 | Bootstrap 3 Dropdown + jQuery | 与项目现有前端一致，无需引入新依赖 |
| 切换方式 | API 调用后刷新页面 | 角色上下文影响全局（交易列表、单证等），刷新最可靠 |
| 角色视觉 | 10 种角色各一种颜色徽章 | 直观区分角色，降低认知负荷 |

---

## 2. 后端 API

### 2.1 新增 activate 端点

在 `UserCompanyRoleViewSet` 添加 `activate` action：

| 端点 | 方法 | 说明 | 权限 |
|------|------|------|------|
| `/api/v1/my-roles/{id}/activate/` | POST | 激活指定角色（自动停用其他角色） | 本人 |

请求体：无

响应：
```json
{
  "code": 0,
  "message": "角色已切换",
  "data": {
    "id": 1,
    "company_name": "测试外贸公司",
    "role_code": "exporter",
    "role_name": "出口商",
    "is_active": true
  }
}
```

### 2.2 新增 current 端点

在 `UserCompanyRoleViewSet` 添加 `current` action：

| 端点 | 方法 | 说明 | 权限 |
|------|------|------|------|
| `/api/v1/my-roles/current/` | GET | 获取当前激活的角色上下文 | 登录用户 |

响应：
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 1,
    "company_name": "测试外贸公司",
    "company_code": "COMP_123456",
    "role_code": "exporter",
    "role_name": "出口商",
    "is_active": true
  }
}
```

无激活角色时：
```json
{
  "code": 0,
  "message": "success",
  "data": null
}
```

### 2.3 修改 list 端点

现有 `/api/v1/my-roles/` 返回所有角色分配，前端用此接口渲染切换列表。无需修改后端，现有数据已足够。

---

## 3. 前端实现

### 3.1 base.html 导航栏修改

在用户名 dropdown 左侧添加角色切换 dropdown：

```
导航栏右侧布局：
[角色切换器 dropdown] | [用户名 dropdown]
```

未登录时隐藏角色切换器。无激活角色时显示"选择角色"引导。

### 3.2 role-switcher.js

职责：
1. 页面加载时调用 `/api/v1/my-roles/current/` 获取当前角色
2. 渲染角色徽章到导航栏 dropdown 按钮
3. 点击 dropdown 时调用 `/api/v1/my-roles/` 获取角色列表
4. 点击角色项调用 `/api/v1/my-roles/{id}/activate/` 激活
5. 激活成功后刷新页面

### 3.3 角色颜色映射

10 种角色使用 Bootstrap 3 label 颜色：

| 角色 | 颜色 | label class |
|------|------|-------------|
| 出口商 exporter | 蓝色 | label-primary |
| 进口商 importer | 绿色 | label-success |
| 工厂 factory | 橙色 | label-warning |
| 银行 bank | 深蓝 | label-info |
| 海关 customs | 红色 | label-danger |
| 货运公司 shipping | 灰色 | label-default |
| 保险公司 insurance | 蓝色 | label-primary |
| 商检机构 inspection | 绿色 | label-success |
| 外汇局 forex | 橙色 | label-warning |
| 税务局 tax | 深蓝 | label-info |

### 3.4 状态显示

| 角色状态 | 切换列表中的显示 |
|---------|-----------------|
| active + is_active | 高亮显示，带 ✓ 标记 |
| active + !is_active | 正常显示，可点击切换 |
| pending | 灰色显示，标注"待审核" |
| rejected | 不显示 |

---

## 4. 文件变更清单

| 文件 | 变更 |
|------|------|
| `apps/roles/views.py` | 添加 `activate` 和 `current` action |
| `templates/base.html` | 导航栏添加角色切换 dropdown |
| `static/js/role-switcher.js` | 新建，角色切换逻辑 |
| `static/css/role-switcher.css` | 新建，角色切换器样式 |

---

## 5. 测试

- 后端：在 `apps/roles/tests/test_api.py` 添加 `test_activate_role_api` 和 `test_get_current_role_api`
- 前端：手动验证导航栏显示和切换功能
