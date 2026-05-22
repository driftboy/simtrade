# 单证系统前端设计规格

> **创建日期:** 2026-05-22
> **状态:** 已批准
> **优先级:** 高

## 概述

实现 SimTrade 平台单证系统的前端功能，包括单证列表、创建、编辑、预览和打印功能。后端 API 已完成（51 个测试通过），本设计专注于前端实现。

## 技术栈

- **框架:** Django 3.2 模板引擎
- **CSS:** Bootstrap 3.3.7 + 自定义样式
- **JS:** jQuery 1.12 + 自定义脚本
- **打印:** CSS print media queries

## 架构设计

```
单证系统前端架构
├── 单证列表页 (/documents/)
│   ├── 显示用户创建的所有单证
│   ├── 筛选：类型、状态、交易号
│   └── 操作：创建、查看、编辑、删除
│
├── 单证创建/编辑页 (/documents/create/:type/)
│   ├── 选择关联交易（可选）
│   ├── 智能数据填充
│   ├── 表单字段动态渲染
│   └── 自动校验反馈
│
├── 单证预览页 (/documents/preview/:id/)
│   ├── 渲染最终单证样式
│   ├── 显示校验结果
│   └── 提交审核操作
│
└── 打印模板 (templates/documents/print/*.html)
    └── 15种外贸单证的标准格式
```

## 用户流程

```
1. 用户进入单证列表页
   ↓
2. 点击"新建单证"，选择单证类型
   ↓
3. （可选）选择关联交易，系统自动填充数据
   ↓
4. 填写/编辑单证字段
   ↓
5. 点击"预览"查看最终效果
   ↓
6. 点击"自动校验"检查错误
   ↓
7. 点击"提交审核"
   ↓
8. 等待人工审核通过
   ↓
9. 打印/导出单证
```

## 页面设计

### 1. 单证列表页

**路由:** `/documents/`

**功能:**
- 显示当前用户的所有单证
- 筛选器：单证类型、状态、交易号
- 批量操作（暂不实现）
- 新建单证按钮

**数据来源:** `GET /api/v1/documents/documents/`

### 2. 单证创建/编辑页

**路由:** `/documents/create/:type/` 或 `/documents/edit/:id/`

**功能:**
- 动态表单渲染（基于模板字段配置）
- 智能数据填充（从交易获取）
- 实时保存草稿
- 自动校验反馈

**数据来源:**
- 模板字段: `GET /api/v1/documents/templates/`
- 智能填充: 后端 `DataFillService`

### 3. 单证预览页

**路由:** `/documents/preview/:id/`

**功能:**
- 渲染最终单证样式
- 显示校验结果（通过/失败）
- 提交审核按钮
- 打印/导出按钮

## 打印模板设计

### 模板结构

每个打印模板遵循统一结构：

```html
{% extends "documents/print/base.html" %}

{% block document_title %}
商业发票
{% endblock %}

{% block document_content %}
<!-- 单证具体内容 -->
{% endblock %}
```

### 15种单证模板

**第一批（高优先级）:**
1. `commercial_invoice.html` - 商业发票
2. `packing_list.html` - 装箱单
3. `bill_of_lading.html` - 海运提单
4. `sales_contract.html` - 外销合同
5. `certificate_of_origin.html` - 产地证

**第二批（中优先级）:**
6. `bill_of_exchange.html` - 汇票
7. `letter_of_credit.html` - 信用证
8. `insurance_policy.html` - 保险单
9. `insurance_application.html` - 投保单
10. `export_declaration.html` - 出口报关单
11. `inspection_application.html` - 报检单
12. `inspection_certificate.html` - 检验证书
13. `shipping_advice.html` - 装船通知

**第三批（低优先级）:**
14. `import_declaration.html` - 进口报关单
15. `beneficiary_certificate.html` - 受益人证明

## 文件结构

### 创建的文件

```
templates/documents/
├── list.html              # 单证列表页
├── create.html            # 单证创建/编辑页
├── preview.html           # 单证预览页
└── print/
    ├── base.html          # 打印模板基座
    ├── commercial_invoice.html
    ├── packing_list.html
    ├── bill_of_lading.html
    ├── sales_contract.html
    ├── certificate_of_origin.html
    └── ...（其余10个模板）

static/
├── css/
│   └── documents.css      # 单证模块样式
└── js/
    └── documents.js       # 单证模块脚本
```

### 修改的文件

```
simtrade/urls.py           # 添加页面路由
```

## API 集成

| 操作 | 方法 | 端点 | 说明 |
|-----|------|------|------|
| 获取列表 | GET | `/api/v1/documents/documents/` | 获取单证列表 |
| 获取详情 | GET | `/api/v1/documents/documents/:id/` | 获取单证详情 |
| 创建单证 | POST | `/api/v1/documents/documents/` | 创建新单证 |
| 更新单证 | PUT/PATCH | `/api/v1/documents/documents/:id/` | 更新单证 |
| 删除单证 | DELETE | `/api/v1/documents/documents/:id/` | 删除单证 |
| 获取模板 | GET | `/api/v1/documents/templates/` | 获取可用模板 |
| 提交审核 | POST | `/api/v1/documents/:id/submit/` | 提交单证 |

## 样式设计

### 单证卡片样式

```css
.document-card {
    border: 1px solid #ddd;
    border-radius: 4px;
    padding: 15px;
    margin-bottom: 15px;
    transition: box-shadow 0.2s;
}

.document-card:hover {
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.status-badge {
    padding: 4px 8px;
    border-radius: 3px;
    font-size: 12px;
}
```

### 打印样式

```css
@media print {
    .no-print { display: none !important; }
    .print-only { display: block !important; }
    @page { margin: 10mm; }
    body { font-size: 10pt; }
}
```

## 测试策略

1. **单元测试:** 每个页面的 JavaScript 函数
2. **集成测试:** 完整创建流程
3. **视觉测试:** 打印预览效果
4. **浏览器测试:** Chrome, Firefox, Safari

## 依赖关系

- 依赖现有的交易系统数据（用于智能填充）
- 依赖用户认证系统
- 依赖 WebSocket 通知（审核状态更新）

## 成功标准

1. 用户可以创建15种单证
2. 智能填充功能正常工作
3. 自动校验正确显示错误
4. 打印输出符合外贸单证标准
5. 所有页面响应式设计正常
