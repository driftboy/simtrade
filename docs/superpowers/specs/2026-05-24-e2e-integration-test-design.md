# 端到端集成测试设计 — 全链路自动化贸易流程验证

> 日期：2026-05-24
> 状态：已批准

## 目标

用 Playwright 浏览器自动化测试，覆盖 10 个角色的完整国际贸易链路。测试失败时自动采集浏览器错误（控制台异常、网络失败、页面崩溃），通过 Claude API 分析并自动修复前端 JS 代码，重跑测试验证修复效果。

## 方案

**Playwright 测试套件 + Claude 自动修复循环**

```
Playwright 测试 → 失败 → 错误采集 → 诊断报告 → Claude 分析修复 → 重跑测试 → 通过
```

## 目录结构

```
tests/
├── e2e/
│   ├── conftest.py               # 公共 fixtures + 数据快照 + 自动修复 hook
│   ├── fixtures/                 # 测试数据工厂
│   │   ├── users.py              # 10 个角色用户 + 公司
│   │   └── trade_data.py         # 产品、交易种子数据
│   ├── pages/                    # Page Object 层
│   │   ├── base.py               # 公共基类（登录、错误采集、截图）
│   │   ├── importer_workspace.py
│   │   ├── exporter_workspace.py
│   │   ├── factory_workspace.py
│   │   ├── shipping_workspace.py
│   │   ├── insurance_workspace.py
│   │   ├── inspection_workspace.py
│   │   ├── customs_workspace.py
│   │   ├── bank_workspace.py
│   │   ├── forex_workspace.py
│   │   └── tax_workspace.py
│   ├── trade_flow/               # 按贸易阶段组织的测试用例
│   │   ├── test_01_inquiry.py
│   │   ├── test_02_contract.py
│   │   ├── test_03_purchase.py
│   │   ├── test_04_shipping.py
│   │   ├── test_05_insurance.py
│   │   ├── test_06_inspection.py
│   │   ├── test_07_customs.py
│   │   ├── test_08_bank.py
│   │   ├── test_09_forex.py
│   │   └── test_10_tax.py
│   ├── error_capture/            # 错误采集模块
│   │   ├── collector.py          # console/pageerror/network 监听
│   │   └── reporter.py           # 诊断报告生成（JSON + 截图）
│   ├── auto_fix/                 # 自动修复模块
│   │   ├── analyzer.py           # 错误分析 + 源码定位
│   │   └── fixer.py              # Claude API 调用 + 代码修改 + 重试循环
│   └── artifacts/                # 测试产物
│       ├── snapshots/            # 数据快照（断点恢复）
│       ├── screenshots/          # 失败截图
│       ├── reports/              # 诊断报告 JSON
│       └── fixes/                # 修复记录 patch
```

## Page Object 层

### BasePage

所有工作台继承的公共基类：

- `__init__(page, base_url)` — 接收 Playwright page 对象，注册错误监听
- `_setup_listeners()` — 注册 `page.on('console')`、`page.on('pageerror')`、`page.on('requestfailed')`
- `login(username, password)` — 登录
- `switch_role(role_code)` — 切换角色
- `wait_for_workspace_loaded()` — 等待 AJAX 完成
- `click_action_button(action_name)` — 按 ACTION_MAP 的 action 值匹配按钮
- `get_current_status()` — 读取当前文档状态
- `get_table_rows()` — 获取列表数据行
- `has_errors() -> bool` — 是否采集到控制台/网络错误
- `take_screenshot(name)` — 截图保存到 artifacts/

### 角色工作台

每个角色一个 Page Object，暴露 ACTION_MAP 对应的业务方法：

| 角色 | 关键方法 |
|------|---------|
| ImporterWorkspace | create_inquiry, accept_offer, apply_letter_of_credit, declare_import_customs, apply_forex_settlement |
| ExporterWorkspace | send_offer, create_contract, sign_contract, book_shipment, apply_insurance, apply_inspection, declare_export_customs, apply_tax_refund |
| FactoryWorkspace | accept_order, mark_shipped |
| ShippingWorkspace | confirm_booking, load_cargo, issue_bill_of_lading |
| InsuranceWorkspace | underwrite, issue_policy |
| InspectionWorkspace | inspect, pass_inspection, certify |
| CustomsWorkspace | review, assess, clear |
| BankWorkspace | issue_lc, review_documents, process_payment |
| ForexWorkspace | review, approve |
| TaxWorkspace | review, approve |

## 错误采集器

### ErrorCollector

注入到 BasePage，监听四类浏览器事件：

| 监听器 | 采集内容 |
|--------|---------|
| `page.on('console')` | `console.error()` 输出，过滤 error/warning 级别 |
| `page.on('pageerror')` | 未捕获 JS 异常，含完整堆栈 |
| `page.on('requestfailed')` | 网络失败请求，含 URL 和失败原因 |
| `page.on('load')` | 页面加载完成时间点 |

### DiagnosticReport

测试失败时生成结构化诊断包：

```json
{
  "test": "test_01_importer_creates_inquiry",
  "timestamp": "2026-05-24T10:30:00",
  "screenshot": "screenshots/test_01_fail.png",
  "url": "/workspace/?role=importer",
  "console_errors": [{"text": "...", "location": "..."}],
  "js_exceptions": [{"message": "...", "stack": "..."}],
  "network_errors": [{"url": "...", "status": 500, "reason": "..."}],
  "page_html": "...",
  "server_logs": "..."
}
```

保存到 `tests/e2e/artifacts/reports/`。

## 自动修复器

### ErrorAnalyzer

分析诊断报告，定位源码错误位置：

1. 解析 JS 异常堆栈 → 文件路径 + 行号
2. 读取对应源文件，提取出错上下文（前后各 10 行）
3. 分析网络错误 → 定位对应 AJAX 调用代码
4. 分类错误类型：`JS_RUNTIME` / `NETWORK` / `DOM` / `STATE`
5. 组装 FixContext（文件路径、行号、错误类型、上下文代码）

### AutoFixer

调用 Claude API 修复前端代码，最多 3 轮：

```
修复循环（最多 3 轮）：
  1. 构造 prompt（错误信息 + 源码上下文 + 项目结构）
  2. 调用 Claude API 获取修复方案
  3. 解析响应中的代码修改（old_code → new_code）
  4. 用 Edit 工具应用到源文件
  5. 重跑测试
  6. 通过 → 记录成功，提交 [auto-fix] commit
  7. 失败 → 更新错误上下文，进入下一轮
  8. 3 轮用完 → 输出最终诊断报告，标记手动修复
```

约束：
- 只修改前端 JS 和模板文件，不动后端 Python
- 每次修复前 git stash，失败可回滚
- 修复成功自动 commit，消息前缀 `[auto-fix]`
- Claude API prompt 包含项目结构概要 + 文件上下文

## 全链路测试编排

24 个测试，10 个阶段，按文件名顺序串行执行：

| 阶段 | 文件 | 测试数 | 触发角色 |
|------|------|--------|---------|
| 01 询价 | test_01_inquiry.py | 2 | 进口商 → 出口商 |
| 02 签约 | test_02_contract.py | 3 | 进口商 → 出口商（双方签署） |
| 03 采购 | test_03_purchase.py | 2 | 出口商 → 工厂 |
| 04 货运 | test_04_shipping.py | 2 | 出口商 → 货运公司 |
| 05 保险 | test_05_insurance.py | 2 | 出口商 → 保险公司 |
| 06 商检 | test_06_inspection.py | 2 | 出口商 → 商检机构 |
| 07 海关 | test_07_customs.py | 4 | 出口商/进口商 → 海关（出口+进口两次） |
| 08 银行 | test_08_bank.py | 2 | 进口商 → 银行 |
| 09 外汇 | test_09_forex.py | 2 | 进口商 → 外汇局 |
| 10 退税 | test_10_tax.py | 3 | 出口商 → 税务局 → 验证交易完成 |

### 数据快照

- 每个阶段完成后保存 `trade_context.json`（所有已创建的实体 ID）
- 支持 `--replay-from-snapshot --start-from=05` 从任意阶段恢复
- 跳过已完成阶段，避免每次从头跑

### 测试上下文

```python
trade_context = {
    'product_id': None,
    'inquiry_id': None,
    'order_id': None,
    'contract_id': None,
    'shipment_id': None,
    'insurance_id': None,
    'inspection_id': None,
    'customs_export_id': None,
    'customs_import_id': None,
    'lc_id': None,
    'forex_id': None,
    'tax_id': None,
    'transaction_id': None,
    'completed_phases': [],
}
```

## 依赖与配置

### 新增依赖

```
pytest-playwright>=0.5.0
playwright>=1.40.0
anthropic>=0.40.0
```

### pytest 配置

```ini
[pytest]
testpaths = apps tests/e2e
markers =
    e2e: 端到端浏览器测试
    trade_phase(phase): 贸易阶段标记
```

### 运行命令

```bash
pytest tests/e2e/ -m e2e                    # 全链路 e2e 测试
pytest -m "not e2e"                         # 跳过 e2e，只跑单元测试
pytest tests/e2e/ --headed                  # 有头模式，可视化调试
pytest tests/e2e/ --slowmo=500              # 慢放调试
pytest tests/e2e/ --replay-from-snapshot    # 从快照恢复
pytest tests/e2e/trade_flow/test_07_customs.py  # 单阶段调试
```

### artifacts

```
tests/e2e/artifacts/
├── snapshots/trade_context.json    # 数据快照
├── screenshots/                    # 失败截图 PNG
├── reports/                        # 诊断报告 JSON
└── fixes/                          # 修复记录 patch
```

## 前端已知风险点

评估中发现 12 类潜在前端错误，自动修复器需重点处理：

1. AJAX 无 `.fail()` 回调 — 网络异常静默失败
2. `ACTION_MAP[roleCode][status]` 无防御 — undefined 导致渲染崩溃
3. `window.workspaceConfig` 可能 undefined — 模板变量缺失
4. CSRF Token cookie 解析无 fallback
5. WebSocket 重试仅 5 次后放弃
6. jQuery 选择器未检查元素是否存在
7. 模板内联 JS 的变量转义问题
8. 并发 AJAX 无协调 — 竞态条件
9. 全局变量依赖（window.user 等）
10. DOM 插入无 HTML 验证
11. Bootstrap 组件加载依赖
12. 自动保存定时器竞态
