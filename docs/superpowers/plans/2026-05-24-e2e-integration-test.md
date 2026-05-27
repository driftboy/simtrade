# 端到端集成测试实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 用 Playwright 浏览器自动化测试覆盖 10 个角色的完整国际贸易链路，测试失败时通过 Claude API 自动分析并修复前端 JS 错误。

**架构：** Playwright 启动 Chromium 连接 Django live_server，Page Object 封装每个角色工作台，10 个阶段按贸易时序串行执行。失败时 ErrorCollector 采集浏览器异常，DiagnosticReport 生成诊断包，AutoFixer 调用 Claude API 修改前端代码并重跑测试验证。

**技术栈：** Playwright + pytest-playwright + Django live_server + Anthropic SDK

**规格文档：** `docs/superpowers/specs/2026-05-24-e2e-integration-test-design.md`

---

## 文件结构

| 操作 | 文件路径 | 职责 |
|------|---------|------|
| 创建 | `tests/e2e/__init__.py` | 包标识 |
| 创建 | `tests/e2e/conftest.py` | 公共 fixtures：live_server、browser、page、error_collector、trade_context、auto_fix hook |
| 创建 | `tests/e2e/fixtures/__init__.py` | 包标识 |
| 创建 | `tests/e2e/fixtures/users.py` | 10 个角色用户 + 10 家公司的工厂函数 |
| 创建 | `tests/e2e/fixtures/trade_data.py` | 产品、币种、港口等种子数据 |
| 创建 | `tests/e2e/pages/__init__.py` | 包标识 |
| 创建 | `tests/e2e/pages/base.py` | BasePage：登录、错误监听、截图、等待加载 |
| 创建 | `tests/e2e/pages/importer_workspace.py` | ImporterWorkspace Page Object |
| 创建 | `tests/e2e/pages/exporter_workspace.py` | ExporterWorkspace Page Object |
| 创建 | `tests/e2e/pages/factory_workspace.py` | FactoryWorkspace Page Object |
| 创建 | `tests/e2e/pages/shipping_workspace.py` | ShippingWorkspace Page Object |
| 创建 | `tests/e2e/pages/insurance_workspace.py` | InsuranceWorkspace Page Object |
| 创建 | `tests/e2e/pages/inspection_workspace.py` | InspectionWorkspace Page Object |
| 创建 | `tests/e2e/pages/customs_workspace.py` | CustomsWorkspace Page Object |
| 创建 | `tests/e2e/pages/bank_workspace.py` | BankWorkspace Page Object |
| 创建 | `tests/e2e/pages/forex_workspace.py` | ForexWorkspace Page Object |
| 创建 | `tests/e2e/pages/tax_workspace.py` | TaxWorkspace Page Object |
| 创建 | `tests/e2e/error_capture/__init__.py` | 包标识 |
| 创建 | `tests/e2e/error_capture/collector.py` | ErrorCollector：监听 console/pageerror/requestfailed |
| 创建 | `tests/e2e/error_capture/reporter.py` | DiagnosticReport：生成 JSON + 截图诊断包 |
| 创建 | `tests/e2e/auto_fix/__init__.py` | 包标识 |
| 创建 | `tests/e2e/auto_fix/analyzer.py` | ErrorAnalyzer：解析堆栈、定位源码、分类错误 |
| 创建 | `tests/e2e/auto_fix/fixer.py` | AutoFixer：Claude API 调用、代码修改、重试循环 |
| 创建 | `tests/e2e/trade_flow/__init__.py` | 包标识 |
| 创建 | `tests/e2e/trade_flow/test_01_inquiry.py` | 阶段 1：进口商询价 → 出口商报价 |
| 创建 | `tests/e2e/trade_flow/test_02_contract.py` | 阶段 2：谈判 → 双方签约 → 合同生效 |
| 创建 | `tests/e2e/trade_flow/test_03_purchase.py` | 阶段 3：出口商下单 → 工厂确认发货 |
| 创建 | `tests/e2e/trade_flow/test_04_shipping.py` | 阶段 4：货运订舱 → 装船 → 签发提单 |
| 创建 | `tests/e2e/trade_flow/test_05_insurance.py` | 阶段 5：保险投保 → 出单 |
| 创建 | `tests/e2e/trade_flow/test_06_inspection.py` | 阶段 6：商检申请 → 检验 → 出证 |
| 创建 | `tests/e2e/trade_flow/test_07_customs.py` | 阶段 7：海关出口 + 进口报关 → 放行 |
| 创建 | `tests/e2e/trade_flow/test_08_bank.py` | 阶段 8：信用证申请 → 开证 → 付款 |
| 创建 | `tests/e2e/trade_flow/test_09_forex.py` | 阶段 9：外汇结算 |
| 创建 | `tests/e2e/trade_flow/test_10_tax.py` | 阶段 10：退税 → 验证交易完成 |
| 修改 | `requirements.txt` | 新增 pytest-playwright、playwright、anthropic |
| 修改 | `pytest.ini` | 新增 e2e marker、testpaths 追加 tests/e2e |

---

## 任务 1：环境搭建 — 依赖安装与 pytest 配置

**文件：**
- 修改：`requirements.txt`
- 修改：`pytest.ini`

- [ ] **步骤 1：在 requirements.txt 追加依赖**

在 `requirements.txt` 末尾追加：

```
# E2E testing
pytest-playwright==0.5.0
playwright==1.40.0
anthropic==0.40.0
```

- [ ] **步骤 2：安装依赖**

```bash
pip install pytest-playwright==0.5.0 playwright==1.40.0 anthropic==0.40.0
playwright install chromium
```

预期：无报错，chromium 下载完成。

- [ ] **步骤 3：修改 pytest.ini**

在 `pytest.ini` 的 `testpaths` 中追加 `tests/e2e`，新增 `e2e` 和 `trade_phase` marker：

```ini
[pytest]
DJANGO_SETTINGS_MODULE = simtrade.settings
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    -v
    --tb=short
    --strict-markers
testpaths = apps tests/e2e
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    integration: marks tests as integration tests
    e2e: 端到端浏览器测试
    trade_phase(phase): 贸易阶段标记
filterwarnings =
    ignore::django.utils.deprecation.RemovedInDjango41Warning
```

- [ ] **步骤 4：创建目录结构**

```bash
mkdir -p tests/e2e/fixtures tests/e2e/pages tests/e2e/error_capture tests/e2e/auto_fix tests/e2e/trade_flow tests/e2e/artifacts/{snapshots,screenshots,reports,fixes}
touch tests/e2e/__init__.py tests/e2e/fixtures/__init__.py tests/e2e/pages/__init__.py tests/e2e/error_capture/__init__.py tests/e2e/auto_fix/__init__.py tests/e2e/trade_flow/__init__.py
```

- [ ] **步骤 5：运行现有测试确认不破坏**

```bash
pytest apps/ -x -q
```

预期：所有现有测试通过，pytest 识别 `tests/e2e` 路径。

- [ ] **步骤 6：Commit**

```bash
git add requirements.txt pytest.ini tests/e2e/
git commit -m "chore: set up Playwright e2e test infrastructure"
```

---

## 任务 2：错误采集器

**文件：**
- 创建：`tests/e2e/error_capture/collector.py`
- 创建：`tests/e2e/error_capture/reporter.py`

- [ ] **步骤 1：编写 collector.py**

```python
"""tests/e2e/error_capture/collector.py — 浏览器运行时错误采集器"""

import os
from datetime import datetime


class ErrorCollector:
    """注入到 Playwright page，监听浏览器运行时错误"""

    def __init__(self, page):
        self.page = page
        self.console_errors = []
        self.js_exceptions = []
        self.network_errors = []
        self.page_crashes = []
        self._setup_listeners()

    def _setup_listeners(self):
        self.page.on('console', self._on_console)
        self.page.on('pageerror', self._on_pageerror)
        self.page.on('requestfailed', self._on_request_failed)
        self.page.on('crash', self._on_crash)

    def _on_console(self, msg):
        if msg.type in ('error', 'warning'):
            self.console_errors.append({
                'type': msg.type,
                'text': msg.text,
                'location': f"{msg.location.get('url', '')}:{msg.location.get('lineNumber', '')}",
                'timestamp': datetime.now().isoformat(),
            })

    def _on_pageerror(self, exc):
        self.js_exceptions.append({
            'message': str(exc),
            'timestamp': datetime.now().isoformat(),
        })

    def _on_request_failed(self, request):
        self.network_errors.append({
            'url': request.url,
            'method': request.method,
            'failure': request.failure,
            'timestamp': datetime.now().isoformat(),
        })

    def _on_crash(self):
        self.page_crashes.append({
            'timestamp': datetime.now().isoformat(),
        })

    def has_errors(self):
        return bool(self.console_errors or self.js_exceptions or self.network_errors or self.page_crashes)

    def get_all_errors(self):
        return {
            'console_errors': self.console_errors,
            'js_exceptions': self.js_exceptions,
            'network_errors': self.network_errors,
            'page_crashes': self.page_crashes,
        }

    def clear(self):
        self.console_errors.clear()
        self.js_exceptions.clear()
        self.network_errors.clear()
        self.page_crashes.clear()
```

- [ ] **步骤 2：编写 reporter.py**

```python
"""tests/e2e/error_capture/reporter.py — 诊断报告生成器"""

import json
import os
from datetime import datetime


ARTIFACTS_DIR = os.path.join(os.path.dirname(__file__), '..', 'artifacts')


class DiagnosticReport:
    """测试失败时生成结构化诊断包"""

    def generate(self, test_name, error_collector, page):
        screenshot_path = os.path.join(
            ARTIFACTS_DIR, 'screenshots', f'{test_name}_fail.png'
        )
        os.makedirs(os.path.dirname(screenshot_path), exist_ok=True)
        try:
            page.screenshot(path=screenshot_path, full_page=True)
        except Exception:
            screenshot_path = None

        report = {
            'test': test_name,
            'timestamp': datetime.now().isoformat(),
            'url': page.url,
            'screenshot': screenshot_path,
            'console_errors': error_collector.console_errors,
            'js_exceptions': error_collector.js_exceptions,
            'network_errors': error_collector.network_errors,
            'page_crashes': error_collector.page_crashes,
            'page_html': None,
        }
        try:
            report['page_html'] = page.content()
        except Exception:
            pass
        return report

    def save(self, report):
        reports_dir = os.path.join(ARTIFACTS_DIR, 'reports')
        os.makedirs(reports_dir, exist_ok=True)
        path = os.path.join(reports_dir, f"{report['test']}_report.json")
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)
        return path
```

- [ ] **步骤 3：验证导入无错**

```bash
python -c "from tests.e2e.error_capture.collector import ErrorCollector; from tests.e2e.error_capture.reporter import DiagnosticReport; print('OK')"
```

预期：输出 `OK`。

- [ ] **步骤 4：Commit**

```bash
git add tests/e2e/error_capture/
git commit -m "feat(e2e): add browser error collector and diagnostic reporter"
```

---

## 任务 3：自动修复器

**文件：**
- 创建：`tests/e2e/auto_fix/analyzer.py`
- 创建：`tests/e2e/auto_fix/fixer.py`

- [ ] **步骤 1：编写 analyzer.py**

```python
"""tests/e2e/auto_fix/analyzer.py — 错误分析 + 源码定位"""

import os
import re

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), '..', '..', '..')
STATIC_JS_DIR = os.path.join(PROJECT_ROOT, 'static', 'js')
TEMPLATES_DIR = os.path.join(PROJECT_ROOT, 'templates')


class FixContext:
    """修复上下文：包含错误信息和源码定位"""

    def __init__(self, error_type, file_path, line_number, error_message,
                 context_code, suggestions=None):
        self.error_type = error_type        # JS_RUNTIME / NETWORK / DOM / STATE
        self.file_path = file_path          # 出错文件绝对路径
        self.line_number = line_number      # 出错行号
        self.error_message = error_message  # 错误信息
        self.context_code = context_code    # 出错上下文代码（前后各10行）
        self.suggestions = suggestions or []


class ErrorAnalyzer:
    """分析诊断报告，定位源码错误位置"""

    def analyze(self, report):
        """分析诊断报告，返回 FixContext 列表"""
        contexts = []
        for exc in report.get('js_exceptions', []):
            ctx = self._analyze_js_exception(exc)
            if ctx:
                contexts.append(ctx)
        for err in report.get('console_errors', []):
            ctx = self._analyze_console_error(err)
            if ctx:
                contexts.append(ctx)
        for err in report.get('network_errors', []):
            ctx = self._analyze_network_error(err, report.get('page_html', ''))
            if ctx:
                contexts.append(ctx)
        return contexts

    def _parse_stack_location(self, message):
        """从 JS 异常消息中提取文件路径和行号"""
        patterns = [
            r'(https?://[^/]+)?(/static/js/[^\s:]+):(\d+)',
            r'(https?://[^/]+)?(/static/[^\s:]+):(\d+)',
            r'at\s+[^\(]*\(([^:]+):(\d+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, message)
            if match:
                path = match.group(2) if match.lastindex >= 2 else match.group(1)
                line = int(match.group(3) if match.lastindex >= 3 else match.group(2))
                full_path = os.path.join(PROJECT_ROOT, path.lstrip('/'))
                if os.path.exists(full_path):
                    return full_path, line
        return None, None

    def _read_context(self, file_path, line_number, context_lines=10):
        """读取出错文件，返回前后各 context_lines 行的上下文"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            start = max(0, line_number - context_lines - 1)
            end = min(len(lines), line_number + context_lines)
            context = ''.join(lines[start:end])
            return context
        except Exception:
            return ''

    def _classify_error(self, message):
        """分类错误类型"""
        if any(kw in message for kw in ('TypeError', 'ReferenceError', 'SyntaxError')):
            return 'JS_RUNTIME'
        if any(kw in message for kw in ('Cannot read', 'undefined', 'null')):
            return 'DOM'
        return 'JS_RUNTIME'

    def _analyze_js_exception(self, exc):
        message = exc.get('message', '')
        file_path, line_number = self._parse_stack_location(message)
        if not file_path:
            return None
        context = self._read_context(file_path, line_number)
        return FixContext(
            error_type=self._classify_error(message),
            file_path=file_path,
            line_number=line_number,
            error_message=message,
            context_code=context,
        )

    def _analyze_console_error(self, err):
        text = err.get('text', '')
        location = err.get('location', '')
        file_path, line_number = None, None
        if location:
            parts = location.split(':')
            if len(parts) >= 2:
                try:
                    line_number = int(parts[-1])
                    rel_path = ':'.join(parts[:-1])
                    if rel_path.startswith('/'):
                        file_path = os.path.join(PROJECT_ROOT, rel_path.lstrip('/'))
                except ValueError:
                    pass
        if file_path and os.path.exists(file_path):
            context = self._read_context(file_path, line_number)
            return FixContext(
                error_type=self._classify_error(text),
                file_path=file_path,
                line_number=line_number,
                error_message=text,
                context_code=context,
            )
        return None

    def _analyze_network_error(self, err, page_html=''):
        url = err.get('url', '')
        failure = err.get('failure', '')
        js_files = [f for f in os.listdir(STATIC_JS_DIR) if f.endswith('.js')]
        for js_file in js_files:
            file_path = os.path.join(STATIC_JS_DIR, js_file)
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            if url in content:
                lines = content.split('\n')
                for i, line in enumerate(lines, 1):
                    if url in line:
                        context = self._read_context(file_path, i)
                        return FixContext(
                            error_type='NETWORK',
                            file_path=file_path,
                            line_number=i,
                            error_message=f"Request to {url} failed: {failure}",
                            context_code=context,
                        )
        return None
```

- [ ] **步骤 2：编写 fixer.py**

```python
"""tests/e2e/auto_fix/fixer.py — Claude API 自动修复"""

import json
import os
import subprocess

import anthropic

from tests.e2e.auto_fix.analyzer import FixContext
from tests.e2e.error_capture.reporter import DiagnosticReport


ARTIFACTS_DIR = os.path.join(os.path.dirname(__file__), '..', 'artifacts')
PROJECT_ROOT = os.path.join(os.path.dirname(__file__), '..', '..', '..')
MAX_RETRIES = 3


class FixResult:
    def __init__(self, success, description='', file_path='', old_code='', new_code=''):
        self.success = success
        self.description = description
        self.file_path = file_path
        self.old_code = old_code
        self.new_code = new_code


class AutoFixer:
    """调用 Claude API 分析错误并修改前端代码"""

    def __init__(self):
        self.client = anthropic.Anthropic()
        self.model = 'claude-sonnet-4-20250514'

    def fix(self, fix_context):
        """对单个 FixContext 执行修复"""
        prompt = self._build_prompt(fix_context)
        response = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            messages=[{'role': 'user', 'content': prompt}],
        )
        answer = response.content[0].text
        return self._parse_and_apply(answer, fix_context.file_path)

    def fix_loop(self, test_func, fix_contexts, page, error_collector):
        """完整修复循环：最多 MAX_RETRIES 轮"""
        from tests.e2e.error_capture.collector import ErrorCollector

        results = []
        for attempt in range(MAX_RETRIES):
            for ctx in fix_contexts:
                result = self.fix(ctx)
                results.append(result)
                if result.success:
                    self._save_fix_record(result, attempt)

            error_collector.clear()
            try:
                test_func()
                return True, results
            except Exception:
                report = DiagnosticReport().generate(
                    test_func.__name__, error_collector, page
                )
                from tests.e2e.auto_fix.analyzer import ErrorAnalyzer
                fix_contexts = ErrorAnalyzer().analyze(report)

        report_path = DiagnosticReport().save(report)
        return False, results

    def _build_prompt(self, fix_context):
        rel_path = os.path.relpath(fix_context.file_path, PROJECT_ROOT)
        return f"""你是前端 JS 修复专家。分析以下错误并给出修复方案。

项目：SimTrade 国际贸易模拟教学平台（Django + jQuery + Bootstrap 3）

出错文件：{rel_path}（第 {fix_context.line_number} 行附近）
错误类型：{fix_context.error_type}
错误信息：{fix_context.error_message}

出错上下文代码：
```
{fix_context.context_code}
```

请严格按以下 JSON 格式返回修复方案（不要返回其他内容）：
{{
    "description": "修复说明（一句话）",
    "old_code": "需要替换的原始代码片段",
    "new_code": "修复后的代码片段"
}}

要求：
1. old_code 必须是源文件中存在的精确文本片段
2. new_code 只修改有问题的部分，不做无关改动
3. 修复必须保持与 jQuery + Bootstrap 3 兼容"""

    def _parse_and_apply(self, answer, file_path):
        """解析 Claude 响应并应用修复"""
        try:
            json_match = answer
            if '```json' in answer:
                json_match = answer.split('```json')[1].split('```')[0]
            elif '```' in answer:
                json_match = answer.split('```')[1].split('```')[0]
            fix_data = json.loads(json_match.strip())
        except (json.JSONDecodeError, IndexError):
            return FixResult(False, 'Failed to parse Claude response')

        old_code = fix_data.get('old_code', '')
        new_code = fix_data.get('new_code', '')
        if not old_code or not new_code:
            return FixResult(False, 'Empty old_code or new_code in response')

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        if old_code not in content:
            return FixResult(False, f'old_code not found in {file_path}')

        content = content.replace(old_code, new_code, 1)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        return FixResult(
            success=True,
            description=fix_data.get('description', ''),
            file_path=file_path,
            old_code=old_code,
            new_code=new_code,
        )

    def _save_fix_record(self, result, attempt):
        """保存修复记录"""
        fixes_dir = os.path.join(ARTIFACTS_DIR, 'fixes')
        os.makedirs(fixes_dir, exist_ok=True)
        record = {
            'attempt': attempt + 1,
            'file': os.path.relpath(result.file_path, PROJECT_ROOT),
            'description': result.description,
            'old_code': result.old_code,
            'new_code': result.new_code,
        }
        path = os.path.join(fixes_dir, f'fix_{attempt + 1:03d}.json')
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(record, f, indent=2, ensure_ascii=False)
```

- [ ] **步骤 3：验证导入无错**

```bash
python -c "from tests.e2e.auto_fix.analyzer import ErrorAnalyzer, FixContext; from tests.e2e.auto_fix.fixer import AutoFixer; print('OK')"
```

预期：输出 `OK`。

- [ ] **步骤 4：Commit**

```bash
git add tests/e2e/auto_fix/
git commit -m "feat(e2e): add error analyzer and Claude-powered auto-fixer"
```

---

## 任务 4：测试数据工厂

**文件：**
- 创建：`tests/e2e/fixtures/users.py`
- 创建：`tests/e2e/fixtures/trade_data.py`

- [ ] **步骤 1：编写 users.py — 10 个角色用户 + 公司**

```python
"""tests/e2e/fixtures/users.py — 创建 10 个角色的测试用户和公司"""

from apps.users.models import User
from apps.roles.models import Company, TradeRole, UserCompanyRole
from apps.core.models import Country


ROLE_COMPANY_NAMES = {
    'importer': '测试进口公司',
    'exporter': '测试出口公司',
    'factory': '测试工厂',
    'bank': '测试银行',
    'shipping': '测试货运公司',
    'insurance': '测试保险公司',
    'inspection': '测试商检机构',
    'customs': '测试海关',
    'forex': '测试外汇局',
    'tax': '测试税务局',
}


def create_test_users():
    """创建 10 个角色用户和对应公司，返回 {role_code: user} 字典"""
    china, _ = Country.objects.get_or_create(
        code='CN',
        defaults={'name': '中国', 'name_en': 'China'},
    )
    users = {}
    for role_code, company_name in ROLE_COMPANY_NAMES.items():
        company = Company.objects.create(
            name=company_name,
            name_en=f'Test {role_code.title()} Co.',
            code=f'TEST_{role_code.upper()}',
            type='trade',
            country=china,
        )
        trade_role = TradeRole.objects.get(role_type=role_code)
        user = User.objects.create_user(
            username=f'e2e_{role_code}',
            password='testpass123',
            email=f'{role_code}@e2e.test',
            user_type='student',
        )
        ucr = UserCompanyRole.objects.create(
            user=user,
            company=company,
            role=trade_role,
            status='approved',
        )
        ucr.activate()
        users[role_code] = user
    return users


def get_or_create_test_users():
    """获取或创建测试用户（幂等）"""
    existing = {}
    for role_code in ROLE_COMPANY_NAMES:
        try:
            user = User.objects.get(username=f'e2e_{role_code}')
            existing[role_code] = user
        except User.DoesNotExist:
            return create_test_users()
    if len(existing) == 10:
        return existing
    return create_test_users()
```

- [ ] **步骤 2：编写 trade_data.py — 产品种子数据**

```python
"""tests/e2e/fixtures/trade_data.py — 测试贸易数据"""

from apps.products.models import Product
from apps.users.models import User


def create_test_product(factory_user):
    """创建测试产品，返回 Product 实例"""
    ucr = factory_user.usercompanyrole_set.filter(status='active').first()
    company = ucr.company
    product = Product.objects.create(
        name='测试商品-电子元器件',
        name_en='Test Electronic Components',
        hs_code='8542390000',
        category='electronics',
        description='用于 E2E 测试的标准商品',
        unit='piece',
        unit_price=100.00,
        currency='USD',
        company=company,
        min_order_quantity=10,
        stock_quantity=10000,
    )
    return product
```

- [ ] **步骤 3：验证数据工厂可运行**

```bash
pytest apps/ -x -q --co 2>/dev/null | head -5
python -c "
import django, os
os.environ['DJANGO_SETTINGS_MODULE'] = 'simtrade.settings'
django.setup()
from tests.e2e.fixtures.users import get_or_create_test_users
print('Factory imports OK')
"
```

预期：输出 `Factory imports OK`。

- [ ] **步骤 4：Commit**

```bash
git add tests/e2e/fixtures/
git commit -m "feat(e2e): add test user and trade data factories"
```

---

## 任务 5：BasePage — 工作台公共基类

**文件：**
- 创建：`tests/e2e/pages/base.py`

- [ ] **步骤 1：编写 base.py**

```python
"""tests/e2e/pages/base.py — 所有工作台的公共基类"""

import os
import time

from tests.e2e.error_capture.collector import ErrorCollector
from tests.e2e.error_capture.reporter import DiagnosticReport


ARTIFACTS_DIR = os.path.join(os.path.dirname(__file__), '..', 'artifacts')


class BasePage:
    """所有角色工作台 Page Object 的公共基类"""

    LOGIN_URL = '/login/'
    WORKSPACE_URL = '/workspace/'
    CURRENT_ROLE_API = '/api/v1/my-roles/current/'
    ROLE_ACTIVATE_URL = '/api/v1/my-roles/{id}/activate/'

    def __init__(self, page, base_url, error_collector=None):
        self.page = page
        self.base_url = base_url
        self.collector = error_collector or ErrorCollector(page)

    @property
    def full_url(self):
        return self.page.url

    def goto(self, path):
        self.page.goto(f'{self.base_url}{path}')
        self.page.wait_for_load_state('networkidle')

    def login(self, username, password):
        """登录系统"""
        self.goto(self.LOGIN_URL)
        self.page.fill('input[name="username"]', username)
        self.page.fill('input[name="password"]', password)
        self.page.click('button[type="submit"]')
        self.page.wait_for_load_state('networkidle')
        self.page.wait_for_timeout(500)

    def switch_role(self, role_code):
        """切换到指定角色"""
        self.goto(f'{self.WORKSPACE_URL}{role_code}/')
        self.page.wait_for_load_state('networkidle')
        self.page.wait_for_timeout(500)
        self._wait_for_workspace_loaded()

    def _wait_for_workspace_loaded(self):
        """等待工作台 AJAX 请求完成"""
        try:
            self.page.wait_for_function(
                "() => document.querySelector('.workspace-content') !== null",
                timeout=10000,
            )
        except Exception:
            pass
        self.page.wait_for_timeout(1000)

    def click_action_button(self, action_name):
        """按 action 值匹配并点击工作台动作按钮"""
        button = self.page.locator(f'button[data-action="{action_name}"]')
        if button.count() == 0:
            button = self.page.locator(f'.action-btn:has-text("{action_name}")')
        button.first.click()
        self.page.wait_for_load_state('networkidle')
        self.page.wait_for_timeout(500)

    def get_current_status(self):
        """读取当前列表第一行的状态"""
        status_cell = self.page.locator('table tbody tr:first-child td:nth-child(3)')
        if status_cell.count() > 0:
            return status_cell.first.text_content().strip()
        return None

    def get_table_rows(self):
        """获取列表数据行数"""
        return self.page.locator('table tbody tr').count()

    def click_table_row_action(self, row_index, action_name):
        """点击指定行的操作按钮"""
        row = self.page.locator('table tbody tr').nth(row_index)
        action_btn = row.locator(f'button[data-action="{action_name}"]')
        if action_btn.count() == 0:
            action_btn = row.locator(f'button:has-text("{action_name}")')
        action_btn.first.click()
        self.page.wait_for_load_state('networkidle')
        self.page.wait_for_timeout(500)

    def click_first_row(self):
        """点击第一行进入详情"""
        self.page.locator('table tbody tr:first-child').first.click()
        self.page.wait_for_load_state('networkidle')
        self.page.wait_for_timeout(500)

    def fill_form_field(self, selector, value):
        """填写表单字段"""
        self.page.fill(selector, str(value))

    def submit_form(self, selector='button[type="submit"]'):
        """提交表单"""
        self.page.click(selector)
        self.page.wait_for_load_state('networkidle')
        self.page.wait_for_timeout(500)

    def has_errors(self):
        return self.collector.has_errors()

    def take_screenshot(self, name):
        """截图保存到 artifacts/"""
        path = os.path.join(ARTIFACTS_DIR, 'screenshots', f'{name}.png')
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.page.screenshot(path=path, full_page=True)
        return path

    def wait_for_api_response(self, url_pattern, timeout=10000):
        """等待特定 API 响应"""
        with self.page.expect_response(url_pattern, timeout=timeout) as resp:
            pass
        return resp.value

    def get_element_text(self, selector):
        """获取元素文本"""
        el = self.page.locator(selector)
        if el.count() > 0:
            return el.first.text_content()
        return None
```

- [ ] **步骤 2：验证导入无错**

```bash
python -c "from tests.e2e.pages.base import BasePage; print('OK')"
```

预期：输出 `OK`。

- [ ] **步骤 3：Commit**

```bash
git add tests/e2e/pages/base.py
git commit -m "feat(e2e): add BasePage with login, role switching, and error capture"
```

---

## 任务 6：10 个角色 Page Objects

**文件：**
- 创建：`tests/e2e/pages/importer_workspace.py`
- 创建：`tests/e2e/pages/exporter_workspace.py`
- 创建：`tests/e2e/pages/factory_workspace.py`
- 创建：`tests/e2e/pages/shipping_workspace.py`
- 创建：`tests/e2e/pages/insurance_workspace.py`
- 创建：`tests/e2e/pages/inspection_workspace.py`
- 创建：`tests/e2e/pages/customs_workspace.py`
- 创建：`tests/e2e/pages/bank_workspace.py`
- 创建：`tests/e2e/pages/forex_workspace.py`
- 创建：`tests/e2e/pages/tax_workspace.py`

- [ ] **步骤 1：编写 importer_workspace.py**

```python
"""tests/e2e/pages/importer_workspace.py — 进口商工作台"""

from tests.e2e.pages.base import BasePage


class ImporterWorkspace(BasePage):
    """进口商工作台：询价、接受报价、申请信用证、进口报关、外汇结算"""

    ROLE_CODE = 'importer'
    LIST_API = '/api/v1/purchase-orders/'

    def __init__(self, page, base_url, error_collector=None):
        super().__init__(page, base_url, error_collector)

    def navigate(self):
        self.switch_role(self.ROLE_CODE)

    def create_inquiry(self, product_id, quantity, target_price):
        """创建询价单"""
        self.goto(f'/workspace/{self.ROLE_CODE}/')
        self.click_action_button('create_order')
        self.page.wait_for_selector('form', timeout=5000)
        self.fill_form_field('#id_product', str(product_id))
        self.fill_form_field('#id_quantity', str(quantity))
        self.fill_form_field('#id_target_price', str(target_price))
        self.submit_form()
        return self._parse_api_response()

    def accept_offer(self, order_id):
        """接受报价"""
        self.goto(f'/workspace/{self.ROLE_CODE}/')
        self.click_table_row_action(0, 'accept')
        return self._parse_api_response()

    def apply_letter_of_credit(self, contract_id):
        """申请信用证"""
        self.goto(f'/workspace/{self.ROLE_CODE}/')
        self.click_action_button('apply_lc')
        self.fill_form_field('#id_contract', str(contract_id))
        self.submit_form()
        return self._parse_api_response()

    def declare_import_customs(self, shipment_id):
        """申报进口报关"""
        self.goto(f'/workspace/{self.ROLE_CODE}/')
        self.click_action_button('declare_import')
        self.fill_form_field('#id_shipment', str(shipment_id))
        self.submit_form()
        return self._parse_api_response()

    def apply_forex_settlement(self, payment_id):
        """申请外汇结算"""
        self.goto(f'/workspace/{self.ROLE_CODE}/')
        self.click_action_button('apply_forex')
        self.fill_form_field('#id_payment', str(payment_id))
        self.submit_form()
        return self._parse_api_response()

    def _parse_api_response(self):
        """解析最近一次 API 响应"""
        try:
            resp = self.page.evaluate("() => window.__lastApiResponse || {}")
            return resp
        except Exception:
            return {}
```

- [ ] **步骤 2：编写 exporter_workspace.py**

```python
"""tests/e2e/pages/exporter_workspace.py — 出口商工作台"""

from tests.e2e.pages.base import BasePage


class ExporterWorkspace(BasePage):
    """出口商工作台：报价、创建合同、签约、订舱、投保、商检、出口报关、退税"""

    ROLE_CODE = 'exporter'

    def __init__(self, page, base_url, error_collector=None):
        super().__init__(page, base_url, error_collector)

    def navigate(self):
        self.switch_role(self.ROLE_CODE)

    def send_offer(self, order_id, price, delivery_days=30):
        """发送报价"""
        self.goto(f'/workspace/{self.ROLE_CODE}/')
        self.click_table_row_action(0, 'offer')
        self.fill_form_field('#id_price', str(price))
        self.fill_form_field('#id_delivery_days', str(delivery_days))
        self.submit_form()
        return self._parse_api_response()

    def create_contract(self, inquiry_id, payment_term='L/C'):
        """创建销售合同"""
        self.goto(f'/workspace/{self.ROLE_CODE}/')
        self.click_action_button('create_contract')
        self.fill_form_field('#id_inquiry', str(inquiry_id))
        self.fill_form_field('#id_payment_term', payment_term)
        self.submit_form()
        return self._parse_api_response()

    def sign_contract(self, contract_id):
        """签署合同"""
        self.goto(f'/workspace/{self.ROLE_CODE}/')
        self.click_table_row_action(0, 'sign')
        self.page.wait_for_load_state('networkidle')
        return self._parse_api_response()

    def create_purchase_order(self, contract_id):
        """创建采购订单（向工厂）"""
        self.goto(f'/workspace/{self.ROLE_CODE}/')
        self.click_action_button('create_po')
        self.fill_form_field('#id_contract', str(contract_id))
        self.submit_form()
        return self._parse_api_response()

    def book_shipment(self, order_id):
        """申请订舱"""
        self.goto(f'/workspace/{self.ROLE_CODE}/')
        self.click_action_button('book_shipment')
        self.fill_form_field('#id_order', str(order_id))
        self.submit_form()
        return self._parse_api_response()

    def apply_insurance(self, shipment_id):
        """投保"""
        self.goto(f'/workspace/{self.ROLE_CODE}/')
        self.click_action_button('apply_insurance')
        self.fill_form_field('#id_shipment', str(shipment_id))
        self.submit_form()
        return self._parse_api_response()

    def apply_inspection(self, order_id):
        """申请商检"""
        self.goto(f'/workspace/{self.ROLE_CODE}/')
        self.click_action_button('apply_inspection')
        self.fill_form_field('#id_order', str(order_id))
        self.submit_form()
        return self._parse_api_response()

    def declare_export_customs(self, shipment_id):
        """申报出口报关"""
        self.goto(f'/workspace/{self.ROLE_CODE}/')
        self.click_action_button('declare_export')
        self.fill_form_field('#id_shipment', str(shipment_id))
        self.submit_form()
        return self._parse_api_response()

    def apply_tax_refund(self, customs_id):
        """申请退税"""
        self.goto(f'/workspace/{self.ROLE_CODE}/')
        self.click_action_button('apply_tax_refund')
        self.fill_form_field('#id_customs', str(customs_id))
        self.submit_form()
        return self._parse_api_response()

    def view_transaction(self, transaction_id):
        """查看交易状态"""
        self.goto(f'/workspace/{self.ROLE_CODE}/')
        return self._parse_api_response()

    def _parse_api_response(self):
        try:
            resp = self.page.evaluate("() => window.__lastApiResponse || {}")
            return resp
        except Exception:
            return {}
```

- [ ] **步骤 3：编写 factory_workspace.py**

```python
"""tests/e2e/pages/factory_workspace.py — 工厂工作台"""

from tests.e2e.pages.base import BasePage


class FactoryWorkspace(BasePage):
    """工厂工作台：确认订单、发货"""

    ROLE_CODE = 'factory'

    def __init__(self, page, base_url, error_collector=None):
        super().__init__(page, base_url, error_collector)

    def navigate(self):
        self.switch_role(self.ROLE_CODE)

    def accept_order(self, order_id):
        self.goto(f'/workspace/{self.ROLE_CODE}/')
        self.click_table_row_action(0, 'confirm')
        self.page.wait_for_load_state('networkidle')
        return self._parse_api_response()

    def mark_shipped(self, order_id):
        self.goto(f'/workspace/{self.ROLE_CODE}/')
        self.click_table_row_action(0, 'ship')
        self.page.wait_for_load_state('networkidle')
        return self._parse_api_response()

    def _parse_api_response(self):
        try:
            return self.page.evaluate("() => window.__lastApiResponse || {}")
        except Exception:
            return {}
```

- [ ] **步骤 4：编写 shipping_workspace.py、insurance_workspace.py、inspection_workspace.py、customs_workspace.py、bank_workspace.py、forex_workspace.py、tax_workspace.py**

每个文件遵循相同模式 — 继承 BasePage，暴露 ACTION_MAP 对应的动作方法。以下一次性创建剩余 7 个文件：

```python
# tests/e2e/pages/shipping_workspace.py
from tests.e2e.pages.base import BasePage

class ShippingWorkspace(BasePage):
    ROLE_CODE = 'shipping'

    def __init__(self, page, base_url, error_collector=None):
        super().__init__(page, base_url, error_collector)

    def navigate(self):
        self.switch_role(self.ROLE_CODE)

    def confirm_booking(self, shipment_id):
        self.goto(f'/workspace/{self.ROLE_CODE}/')
        self.click_table_row_action(0, 'book')
        self.page.wait_for_load_state('networkidle')
        return self._resp()

    def load_cargo(self, shipment_id):
        self.goto(f'/workspace/{self.ROLE_CODE}/')
        self.click_table_row_action(0, 'load')
        self.page.wait_for_load_state('networkidle')
        return self._resp()

    def issue_bill_of_lading(self, shipment_id):
        self.goto(f'/workspace/{self.ROLE_CODE}/')
        self.click_table_row_action(0, 'issue_bl')
        self.page.wait_for_load_state('networkidle')
        return self._resp()

    def _resp(self):
        try:
            return self.page.evaluate("() => window.__lastApiResponse || {}")
        except Exception:
            return {}
```

```python
# tests/e2e/pages/insurance_workspace.py
from tests.e2e.pages.base import BasePage

class InsuranceWorkspace(BasePage):
    ROLE_CODE = 'insurance'

    def __init__(self, page, base_url, error_collector=None):
        super().__init__(page, base_url, error_collector)

    def navigate(self):
        self.switch_role(self.ROLE_CODE)

    def underwrite(self, insurance_id):
        self.goto(f'/workspace/{self.ROLE_CODE}/')
        self.click_table_row_action(0, 'underwrite')
        self.page.wait_for_load_state('networkidle')
        return self._resp()

    def issue_policy(self, insurance_id):
        self.goto(f'/workspace/{self.ROLE_CODE}/')
        self.click_table_row_action(0, 'issue')
        self.page.wait_for_load_state('networkidle')
        return self._resp()

    def _resp(self):
        try:
            return self.page.evaluate("() => window.__lastApiResponse || {}")
        except Exception:
            return {}
```

```python
# tests/e2e/pages/inspection_workspace.py
from tests.e2e.pages.base import BasePage

class InspectionWorkspace(BasePage):
    ROLE_CODE = 'inspection'

    def __init__(self, page, base_url, error_collector=None):
        super().__init__(page, base_url, error_collector)

    def navigate(self):
        self.switch_role(self.ROLE_CODE)

    def inspect(self, application_id):
        self.goto(f'/workspace/{self.ROLE_CODE}/')
        self.click_table_row_action(0, 'inspect')
        self.page.wait_for_load_state('networkidle')
        return self._resp()

    def pass_inspection(self, application_id):
        self.goto(f'/workspace/{self.ROLE_CODE}/')
        self.click_table_row_action(0, 'pass_inspection')
        self.page.wait_for_load_state('networkidle')
        return self._resp()

    def certify(self, application_id):
        self.goto(f'/workspace/{self.ROLE_CODE}/')
        self.click_table_row_action(0, 'certify')
        self.page.wait_for_load_state('networkidle')
        return self._resp()

    def _resp(self):
        try:
            return self.page.evaluate("() => window.__lastApiResponse || {}")
        except Exception:
            return {}
```

```python
# tests/e2e/pages/customs_workspace.py
from tests.e2e.pages.base import BasePage

class CustomsWorkspace(BasePage):
    ROLE_CODE = 'customs'

    def __init__(self, page, base_url, error_collector=None):
        super().__init__(page, base_url, error_collector)

    def navigate(self):
        self.switch_role(self.ROLE_CODE)

    def review(self, declaration_id):
        self.goto(f'/workspace/{self.ROLE_CODE}/')
        self.click_table_row_action(0, 'review')
        self.page.wait_for_load_state('networkidle')
        return self._resp()

    def assess(self, declaration_id):
        self.goto(f'/workspace/{self.ROLE_CODE}/')
        self.click_table_row_action(0, 'assess')
        self.page.wait_for_load_state('networkidle')
        return self._resp()

    def clear(self, declaration_id):
        self.goto(f'/workspace/{self.ROLE_CODE}/')
        self.click_table_row_action(0, 'clear')
        self.page.wait_for_load_state('networkidle')
        return self._resp()

    def _resp(self):
        try:
            return self.page.evaluate("() => window.__lastApiResponse || {}")
        except Exception:
            return {}
```

```python
# tests/e2e/pages/bank_workspace.py
from tests.e2e.pages.base import BasePage

class BankWorkspace(BasePage):
    ROLE_CODE = 'bank'

    def __init__(self, page, base_url, error_collector=None):
        super().__init__(page, base_url, error_collector)

    def navigate(self):
        self.switch_role(self.ROLE_CODE)

    def issue_lc(self, lc_id):
        self.goto(f'/workspace/{self.ROLE_CODE}/')
        self.click_table_row_action(0, 'issue')
        self.page.wait_for_load_state('networkidle')
        return self._resp()

    def review_documents(self, lc_id):
        self.goto(f'/workspace/{self.ROLE_CODE}/')
        self.click_table_row_action(0, 'advise')
        self.page.wait_for_load_state('networkidle')
        return self._resp()

    def process_payment(self, lc_id):
        self.goto(f'/workspace/{self.ROLE_CODE}/')
        self.click_table_row_action(0, 'pay')
        self.page.wait_for_load_state('networkidle')
        return self._resp()

    def _resp(self):
        try:
            return self.page.evaluate("() => window.__lastApiResponse || {}")
        except Exception:
            return {}
```

```python
# tests/e2e/pages/forex_workspace.py
from tests.e2e.pages.base import BasePage

class ForexWorkspace(BasePage):
    ROLE_CODE = 'forex'

    def __init__(self, page, base_url, error_collector=None):
        super().__init__(page, base_url, error_collector)

    def navigate(self):
        self.switch_role(self.ROLE_CODE)

    def review(self, settlement_id):
        self.goto(f'/workspace/{self.ROLE_CODE}/')
        self.click_table_row_action(0, 'verify')
        self.page.wait_for_load_state('networkidle')
        return self._resp()

    def approve(self, settlement_id):
        self.goto(f'/workspace/{self.ROLE_CODE}/')
        self.click_table_row_action(0, 'settle')
        self.page.wait_for_load_state('networkidle')
        return self._resp()

    def _resp(self):
        try:
            return self.page.evaluate("() => window.__lastApiResponse || {}")
        except Exception:
            return {}
```

```python
# tests/e2e/pages/tax_workspace.py
from tests.e2e.pages.base import BasePage

class TaxWorkspace(BasePage):
    ROLE_CODE = 'tax'

    def __init__(self, page, base_url, error_collector=None):
        super().__init__(page, base_url, error_collector)

    def navigate(self):
        self.switch_role(self.ROLE_CODE)

    def review(self, refund_id):
        self.goto(f'/workspace/{self.ROLE_CODE}/')
        self.click_table_row_action(0, 'review')
        self.page.wait_for_load_state('networkidle')
        return self._resp()

    def approve(self, refund_id):
        self.goto(f'/workspace/{self.ROLE_CODE}/')
        self.click_table_row_action(0, 'approve')
        self.page.wait_for_load_state('networkidle')
        return self._resp()

    def _resp(self):
        try:
            return self.page.evaluate("() => window.__lastApiResponse || {}")
        except Exception:
            return {}
```

- [ ] **步骤 5：验证所有 Page Objects 可导入**

```bash
python -c "
from tests.e2e.pages.importer_workspace import ImporterWorkspace
from tests.e2e.pages.exporter_workspace import ExporterWorkspace
from tests.e2e.pages.factory_workspace import FactoryWorkspace
from tests.e2e.pages.shipping_workspace import ShippingWorkspace
from tests.e2e.pages.insurance_workspace import InsuranceWorkspace
from tests.e2e.pages.inspection_workspace import InspectionWorkspace
from tests.e2e.pages.customs_workspace import CustomsWorkspace
from tests.e2e.pages.bank_workspace import BankWorkspace
from tests.e2e.pages.forex_workspace import ForexWorkspace
from tests.e2e.pages.tax_workspace import TaxWorkspace
print('All 10 Page Objects imported OK')
"
```

预期：输出 `All 10 Page Objects imported OK`。

- [ ] **步骤 6：Commit**

```bash
git add tests/e2e/pages/
git commit -m "feat(e2e): add all 10 role workspace Page Objects"
```

---

## 任务 7：conftest.py — 公共 fixtures 与自动修复 hook

**文件：**
- 创建：`tests/e2e/conftest.py`

- [ ] **步骤 1：编写 conftest.py**

```python
"""tests/e2e/conftest.py — E2E 测试公共 fixtures"""

import json
import os

import pytest
from playwright.sync_api import sync_playwright

from tests.e2e.error_capture.collector import ErrorCollector
from tests.e2e.error_capture.reporter import DiagnosticReport
from tests.e2e.auto_fix.analyzer import ErrorAnalyzer
from tests.e2e.auto_fix.fixer import AutoFixer
from tests.e2e.fixtures.users import get_or_create_test_users
from tests.e2e.fixtures.trade_data import create_test_product


SNAPSHOT_DIR = os.path.join(os.path.dirname(__file__), 'artifacts', 'snapshots')


# ── Django fixtures ──

@pytest.fixture(scope='session')
def django_db_setup(django_test_environment, django_db_blocker):
    with django_db_blocker.unblock():
        yield


@pytest.fixture(scope='session')
def test_users(django_db_setup):
    """创建并缓存 10 个角色的测试用户"""
    return get_or_create_test_users()


@pytest.fixture(scope='session')
def test_product(test_users, django_db_setup):
    """创建测试产品"""
    factory_user = test_users['factory']
    return create_test_product(factory_user)


# ── Live server fixture ──

@pytest.fixture(scope='session')
def base_url(live_server):
    return live_server.url


# ── Playwright fixtures ──

@pytest.fixture(scope='session')
def playwright_instance():
    with sync_playwright() as pw:
        yield pw


@pytest.fixture(scope='session')
def browser(playwright_instance):
    browser = playwright_instance.chromium.launch(
        headless=True,
        args=['--no-sandbox'],
    )
    yield browser
    browser.close()


@pytest.fixture
def context(browser):
    ctx = browser.new_context(
        viewport={'width': 1280, 'height': 720},
        ignore_https_errors=True,
    )
    yield ctx
    ctx.close()


@pytest.fixture
def page(context):
    p = context.new_page()
    yield p
    p.close()


@pytest.fixture
def error_collector(page):
    return ErrorCollector(page)


# ── Trade context (shared state across tests) ──

@pytest.fixture(scope='session')
def trade_context():
    """全链路共享的测试上下文"""
    snapshot_file = os.path.join(SNAPSHOT_DIR, 'trade_context.json')
    if os.path.exists(snapshot_file):
        with open(snapshot_file, 'r') as f:
            return json.load(f)
    return {
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


@pytest.fixture(autouse=True, scope='session')
def save_trade_context(trade_context):
    """session 结束时保存快照"""
    yield
    os.makedirs(SNAPSHOT_DIR, exist_ok=True)
    snapshot_file = os.path.join(SNAPSHOT_DIR, 'trade_context.json')
    with open(snapshot_file, 'w') as f:
        json.dump(trade_context, f, indent=2, ensure_ascii=False)


# ── Page Object fixtures (one per role) ──

@pytest.fixture
def importer_page(page, base_url, error_collector):
    from tests.e2e.pages.importer_workspace import ImporterWorkspace
    return ImporterWorkspace(page, base_url, error_collector)


@pytest.fixture
def exporter_page(page, base_url, error_collector):
    from tests.e2e.pages.exporter_workspace import ExporterWorkspace
    return ExporterWorkspace(page, base_url, error_collector)


@pytest.fixture
def factory_page(page, base_url, error_collector):
    from tests.e2e.pages.factory_workspace import FactoryWorkspace
    return FactoryWorkspace(page, base_url, error_collector)


@pytest.fixture
def shipping_page(page, base_url, error_collector):
    from tests.e2e.pages.shipping_workspace import ShippingWorkspace
    return ShippingWorkspace(page, base_url, error_collector)


@pytest.fixture
def insurance_page(page, base_url, error_collector):
    from tests.e2e.pages.insurance_workspace import InsuranceWorkspace
    return InsuranceWorkspace(page, base_url, error_collector)


@pytest.fixture
def inspection_page(page, base_url, error_collector):
    from tests.e2e.pages.inspection_workspace import InspectionWorkspace
    return InspectionWorkspace(page, base_url, error_collector)


@pytest.fixture
def customs_page(page, base_url, error_collector):
    from tests.e2e.pages.customs_workspace import CustomsWorkspace
    return CustomsWorkspace(page, base_url, error_collector)


@pytest.fixture
def bank_page(page, base_url, error_collector):
    from tests.e2e.pages.bank_workspace import BankWorkspace
    return BankWorkspace(page, base_url, error_collector)


@pytest.fixture
def forex_page(page, base_url, error_collector):
    from tests.e2e.pages.forex_workspace import ForexWorkspace
    return ForexWorkspace(page, base_url, error_collector)


@pytest.fixture
def tax_page(page, base_url, error_collector):
    from tests.e2e.pages.tax_workspace import TaxWorkspace
    return TaxWorkspace(page, base_url, error_collector)


# ── Auto-fix hook ──

@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()

    if report.when == 'call' and report.failed:
        page = item.funcargs.get('page')
        error_collector = item.funcargs.get('error_collector')
        if page and error_collector:
            diag = DiagnosticReport()
            diag_report = diag.generate(item.name, error_collector, page)
            diag.save(diag_report)

            contexts = ErrorAnalyzer().analyze(diag_report)
            if contexts:
                fixer = AutoFixer()
                fixer.fix_loop(
                    test_func=item.obj,
                    fix_contexts=contexts,
                    page=page,
                    error_collector=error_collector,
                )
```

- [ ] **步骤 2：验证 conftest 可被 pytest 加载**

```bash
pytest tests/e2e/ --co -q 2>&1 | head -10
```

预期：无 import 错误（可能显示 collected 0 items，因为没有测试文件）。

- [ ] **步骤 3：Commit**

```bash
git add tests/e2e/conftest.py
git commit -m "feat(e2e): add conftest with fixtures, trade context, and auto-fix hook"
```

---

## 任务 8：冒烟测试 — 登录 + 角色切换

**文件：**
- 创建：`tests/e2e/trade_flow/test_00_smoke.py`

这个测试验证基础架构能跑通，不依赖贸易流程。

- [ ] **步骤 1：编写冒烟测试**

```python
"""tests/e2e/trade_flow/test_00_smoke.py — 基础冒烟测试：登录 + 角色切换"""

import pytest

pytestmark = pytest.mark.e2e


@pytest.mark.trade_phase('00')
def test_login_works(page, base_url, test_users):
    """验证用户可以登录"""
    user = test_users['importer']
    page.goto(f'{base_url}/login/')
    page.fill('input[name="username"]', user.username)
    page.fill('input[name="password"]', 'testpass123')
    page.click('button[type="submit"]')
    page.wait_for_load_state('networkidle')
    assert '/login/' not in page.url, 'Login failed — still on login page'


@pytest.mark.trade_phase('00')
def test_workspace_loads(page, base_url, test_users, error_collector):
    """验证工作台页面加载无 JS 错误"""
    user = test_users['exporter']
    page.goto(f'{base_url}/login/')
    page.fill('input[name="username"]', user.username)
    page.fill('input[name="password"]', 'testpass123')
    page.click('button[type="submit"]')
    page.wait_for_load_state('networkidle')

    page.goto(f'{base_url}/workspace/exporter/')
    page.wait_for_load_state('networkidle')
    page.wait_for_timeout(2000)

    assert not error_collector.has_errors(), (
        f'JS errors on workspace: {error_collector.get_all_errors()}'
    )
```

- [ ] **步骤 2：运行冒烟测试**

```bash
pytest tests/e2e/trade_flow/test_00_smoke.py -v
```

预期：2 个测试通过。如果有 JS 错误，自动修复 hook 会尝试修复。

- [ ] **步骤 3：Commit**

```bash
git add tests/e2e/trade_flow/test_00_smoke.py
git commit -m "test(e2e): add smoke test for login and workspace loading"
```

---

## 任务 9：阶段 1-3 — 询价 → 签约 → 采购

**文件：**
- 创建：`tests/e2e/trade_flow/test_01_inquiry.py`
- 创建：`tests/e2e/trade_flow/test_02_contract.py`
- 创建：`tests/e2e/trade_flow/test_03_purchase.py`

- [ ] **步骤 1：编写 test_01_inquiry.py**

```python
"""tests/e2e/trade_flow/test_01_inquiry.py — 阶段1：进口商询价 → 出口商报价"""

import pytest

pytestmark = pytest.mark.e2e


@pytest.mark.trade_phase('01')
def test_importer_creates_inquiry(page, base_url, test_users, test_product,
                                  trade_context, error_collector):
    """进口商创建询价单"""
    from tests.e2e.pages.importer_workspace import ImporterWorkspace
    importer = ImporterWorkspace(page, base_url, error_collector)

    user = test_users['importer']
    importer.login(user.username, 'testpass123')
    importer.navigate()

    trade_context['product_id'] = test_product.id
    result = importer.create_inquiry(
        product_id=test_product.id,
        quantity=100,
        target_price=50.00,
    )
    assert not importer.has_errors(), f'Errors: {error_collector.get_all_errors()}'


@pytest.mark.trade_phase('01')
def test_exporter_responds_offer(page, base_url, test_users, trade_context,
                                 error_collector):
    """出口商查看询价并发送报价"""
    from tests.e2e.pages.exporter_workspace import ExporterWorkspace
    exporter = ExporterWorkspace(page, base_url, error_collector)

    user = test_users['exporter']
    exporter.login(user.username, 'testpass123')
    exporter.navigate()

    result = exporter.send_offer(
        order_id=trade_context.get('inquiry_id', 1),
        price=55.00,
        delivery_days=30,
    )
    assert not exporter.has_errors(), f'Errors: {error_collector.get_all_errors()}'
```

- [ ] **步骤 2：编写 test_02_contract.py**

```python
"""tests/e2e/trade_flow/test_02_contract.py — 阶段2：谈判 → 双方签约"""

import pytest

pytestmark = pytest.mark.e2e


@pytest.mark.trade_phase('02')
def test_importer_accepts_offer(page, base_url, test_users, trade_context,
                                error_collector):
    """进口商接受报价"""
    from tests.e2e.pages.importer_workspace import ImporterWorkspace
    importer = ImporterWorkspace(page, base_url, error_collector)

    user = test_users['importer']
    importer.login(user.username, 'testpass123')
    importer.navigate()
    importer.accept_offer(trade_context.get('order_id', 1))
    assert not importer.has_errors()


@pytest.mark.trade_phase('02')
def test_exporter_creates_contract(page, base_url, test_users, trade_context,
                                   error_collector):
    """出口商创建合同并发送确认"""
    from tests.e2e.pages.exporter_workspace import ExporterWorkspace
    exporter = ExporterWorkspace(page, base_url, error_collector)

    user = test_users['exporter']
    exporter.login(user.username, 'testpass123')
    exporter.navigate()
    contract = exporter.create_contract(
        inquiry_id=trade_context.get('inquiry_id', 1),
        payment_term='L/C',
    )
    trade_context['contract_id'] = contract.get('id')
    assert not exporter.has_errors()


@pytest.mark.trade_phase('02')
def test_both_sign_contract(page, base_url, test_users, trade_context,
                            error_collector):
    """双方签署合同"""
    from tests.e2e.pages.exporter_workspace import ExporterWorkspace
    from tests.e2e.pages.importer_workspace import ImporterWorkspace

    # 出口商先签
    exporter = ExporterWorkspace(page, base_url, error_collector)
    exporter.login(test_users['exporter'].username, 'testpass123')
    exporter.navigate()
    exporter.sign_contract(trade_context.get('contract_id', 1))
    assert not exporter.has_errors()

    # 进口商再签
    importer = ImporterWorkspace(page, base_url, error_collector)
    importer.login(test_users['importer'].username, 'testpass123')
    importer.navigate()
    importer.sign_contract(trade_context.get('contract_id', 1))
    assert not importer.has_errors()
```

- [ ] **步骤 3：编写 test_03_purchase.py**

```python
"""tests/e2e/trade_flow/test_03_purchase.py — 阶段3：出口商下单 → 工厂确认发货"""

import pytest

pytestmark = pytest.mark.e2e


@pytest.mark.trade_phase('03')
def test_exporter_orders_from_factory(page, base_url, test_users, trade_context,
                                     error_collector):
    """出口商创建采购订单"""
    from tests.e2e.pages.exporter_workspace import ExporterWorkspace
    exporter = ExporterWorkspace(page, base_url, error_collector)

    exporter.login(test_users['exporter'].username, 'testpass123')
    exporter.navigate()
    order = exporter.create_purchase_order(
        contract_id=trade_context.get('contract_id', 1)
    )
    trade_context['order_id'] = order.get('id')
    assert not exporter.has_errors()


@pytest.mark.trade_phase('03')
def test_factory_confirms_and_ships(page, base_url, test_users, trade_context,
                                    error_collector):
    """工厂确认订单并发货"""
    from tests.e2e.pages.factory_workspace import FactoryWorkspace
    factory = FactoryWorkspace(page, base_url, error_collector)

    factory.login(test_users['factory'].username, 'testpass123')
    factory.navigate()
    factory.accept_order(trade_context.get('order_id', 1))
    assert not factory.has_errors()

    factory.mark_shipped(trade_context.get('order_id', 1))
    assert not factory.has_errors()
```

- [ ] **步骤 4：运行阶段 1-3 测试**

```bash
pytest tests/e2e/trade_flow/test_01_inquiry.py tests/e2e/trade_flow/test_02_contract.py tests/e2e/trade_flow/test_03_purchase.py -v
```

预期：5 个测试通过。

- [ ] **步骤 5：Commit**

```bash
git add tests/e2e/trade_flow/test_01_inquiry.py tests/e2e/trade_flow/test_02_contract.py tests/e2e/trade_flow/test_03_purchase.py
git commit -m "test(e2e): add trade flow phases 1-3 (inquiry, contract, purchase)"
```

---

## 任务 10：阶段 4-6 — 货运 → 保险 → 商检

**文件：**
- 创建：`tests/e2e/trade_flow/test_04_shipping.py`
- 创建：`tests/e2e/trade_flow/test_05_insurance.py`
- 创建：`tests/e2e/trade_flow/test_06_inspection.py`

- [ ] **步骤 1：编写 test_04_shipping.py**

```python
"""tests/e2e/trade_flow/test_04_shipping.py — 阶段4：货运订舱 → 装船 → 签发提单"""

import pytest

pytestmark = pytest.mark.e2e


@pytest.mark.trade_phase('04')
def test_exporter_books_shipment(page, base_url, test_users, trade_context,
                                 error_collector):
    """出口商申请订舱"""
    from tests.e2e.pages.exporter_workspace import ExporterWorkspace
    exporter = ExporterWorkspace(page, base_url, error_collector)

    exporter.login(test_users['exporter'].username, 'testpass123')
    exporter.navigate()
    shipment = exporter.book_shipment(trade_context.get('order_id', 1))
    trade_context['shipment_id'] = shipment.get('id')
    assert not exporter.has_errors()


@pytest.mark.trade_phase('04')
def test_shipping_company_processes(page, base_url, test_users, trade_context,
                                    error_collector):
    """货运公司：确认订舱 → 装船 → 签发提单"""
    from tests.e2e.pages.shipping_workspace import ShippingWorkspace
    shipping = ShippingWorkspace(page, base_url, error_collector)

    shipping.login(test_users['shipping'].username, 'testpass123')
    shipping.navigate()

    shipping.confirm_booking(trade_context.get('shipment_id', 1))
    assert not shipping.has_errors()

    shipping.load_cargo(trade_context.get('shipment_id', 1))
    assert not shipping.has_errors()

    shipping.issue_bill_of_lading(trade_context.get('shipment_id', 1))
    assert not shipping.has_errors()
```

- [ ] **步骤 2：编写 test_05_insurance.py**

```python
"""tests/e2e/trade_flow/test_05_insurance.py — 阶段5：保险投保 → 出单"""

import pytest

pytestmark = pytest.mark.e2e


@pytest.mark.trade_phase('05')
def test_exporter_applies_insurance(page, base_url, test_users, trade_context,
                                    error_collector):
    """出口商投保"""
    from tests.e2e.pages.exporter_workspace import ExporterWorkspace
    exporter = ExporterWorkspace(page, base_url, error_collector)

    exporter.login(test_users['exporter'].username, 'testpass123')
    exporter.navigate()
    insurance = exporter.apply_insurance(trade_context.get('shipment_id', 1))
    trade_context['insurance_id'] = insurance.get('id')
    assert not exporter.has_errors()


@pytest.mark.trade_phase('05')
def test_insurance_company_issues(page, base_url, test_users, trade_context,
                                  error_collector):
    """保险公司：审核 → 出单"""
    from tests.e2e.pages.insurance_workspace import InsuranceWorkspace
    ins = InsuranceWorkspace(page, base_url, error_collector)

    ins.login(test_users['insurance'].username, 'testpass123')
    ins.navigate()
    ins.underwrite(trade_context.get('insurance_id', 1))
    assert not ins.has_errors()

    ins.issue_policy(trade_context.get('insurance_id', 1))
    assert not ins.has_errors()
```

- [ ] **步骤 3：编写 test_06_inspection.py**

```python
"""tests/e2e/trade_flow/test_06_inspection.py — 阶段6：商检申请 → 检验 → 出证"""

import pytest

pytestmark = pytest.mark.e2e


@pytest.mark.trade_phase('06')
def test_exporter_applies_inspection(page, base_url, test_users, trade_context,
                                     error_collector):
    """出口商申请商检"""
    from tests.e2e.pages.exporter_workspace import ExporterWorkspace
    exporter = ExporterWorkspace(page, base_url, error_collector)

    exporter.login(test_users['exporter'].username, 'testpass123')
    exporter.navigate()
    app = exporter.apply_inspection(trade_context.get('order_id', 1))
    trade_context['inspection_id'] = app.get('id')
    assert not exporter.has_errors()


@pytest.mark.trade_phase('06')
def test_inspection_certifies(page, base_url, test_users, trade_context,
                              error_collector):
    """商检：检验 → 通过 → 出证"""
    from tests.e2e.pages.inspection_workspace import InspectionWorkspace
    insp = InspectionWorkspace(page, base_url, error_collector)

    insp.login(test_users['inspection'].username, 'testpass123')
    insp.navigate()

    insp.inspect(trade_context.get('inspection_id', 1))
    assert not insp.has_errors()

    insp.pass_inspection(trade_context.get('inspection_id', 1))
    assert not insp.has_errors()

    insp.certify(trade_context.get('inspection_id', 1))
    assert not insp.has_errors()
```

- [ ] **步骤 4：运行阶段 4-6 测试**

```bash
pytest tests/e2e/trade_flow/test_04_shipping.py tests/e2e/trade_flow/test_05_insurance.py tests/e2e/trade_flow/test_06_inspection.py -v
```

预期：6 个测试通过。

- [ ] **步骤 5：Commit**

```bash
git add tests/e2e/trade_flow/test_04_shipping.py tests/e2e/trade_flow/test_05_insurance.py tests/e2e/trade_flow/test_06_inspection.py
git commit -m "test(e2e): add trade flow phases 4-6 (shipping, insurance, inspection)"
```

---

## 任务 11：阶段 7-8 — 海关 → 银行

**文件：**
- 创建：`tests/e2e/trade_flow/test_07_customs.py`
- 创建：`tests/e2e/trade_flow/test_08_bank.py`

- [ ] **步骤 1：编写 test_07_customs.py**

```python
"""tests/e2e/trade_flow/test_07_customs.py — 阶段7：海关出口+进口报关 → 放行"""

import pytest

pytestmark = pytest.mark.e2e


@pytest.mark.trade_phase('07')
def test_exporter_declares_export_customs(page, base_url, test_users,
                                          trade_context, error_collector):
    """出口商申报出口报关"""
    from tests.e2e.pages.exporter_workspace import ExporterWorkspace
    exporter = ExporterWorkspace(page, base_url, error_collector)

    exporter.login(test_users['exporter'].username, 'testpass123')
    exporter.navigate()
    decl = exporter.declare_export_customs(trade_context.get('shipment_id', 1))
    trade_context['customs_export_id'] = decl.get('id')
    assert not exporter.has_errors()


@pytest.mark.trade_phase('07')
def test_customs_clears_export(page, base_url, test_users, trade_context,
                                error_collector):
    """海关：审核 → 评估 → 放行（出口）"""
    from tests.e2e.pages.customs_workspace import CustomsWorkspace
    customs = CustomsWorkspace(page, base_url, error_collector)

    customs.login(test_users['customs'].username, 'testpass123')
    customs.navigate()

    customs.review(trade_context.get('customs_export_id', 1))
    assert not customs.has_errors()

    customs.assess(trade_context.get('customs_export_id', 1))
    assert not customs.has_errors()

    customs.clear(trade_context.get('customs_export_id', 1))
    assert not customs.has_errors()


@pytest.mark.trade_phase('07')
def test_importer_declares_import_customs(page, base_url, test_users,
                                          trade_context, error_collector):
    """进口商申报进口报关"""
    from tests.e2e.pages.importer_workspace import ImporterWorkspace
    importer = ImporterWorkspace(page, base_url, error_collector)

    importer.login(test_users['importer'].username, 'testpass123')
    importer.navigate()
    decl = importer.declare_import_customs(trade_context.get('shipment_id', 1))
    trade_context['customs_import_id'] = decl.get('id')
    assert not importer.has_errors()


@pytest.mark.trade_phase('07')
def test_customs_clears_import(page, base_url, test_users, trade_context,
                                error_collector):
    """海关：审核 → 评估 → 放行（进口）"""
    from tests.e2e.pages.customs_workspace import CustomsWorkspace
    customs = CustomsWorkspace(page, base_url, error_collector)

    customs.login(test_users['customs'].username, 'testpass123')
    customs.navigate()

    customs.review(trade_context.get('customs_import_id', 1))
    assert not customs.has_errors()

    customs.assess(trade_context.get('customs_import_id', 1))
    assert not customs.has_errors()

    customs.clear(trade_context.get('customs_import_id', 1))
    assert not customs.has_errors()
```

- [ ] **步骤 2：编写 test_08_bank.py**

```python
"""tests/e2e/trade_flow/test_08_bank.py — 阶段8：信用证申请 → 开证 → 付款"""

import pytest

pytestmark = pytest.mark.e2e


@pytest.mark.trade_phase('08')
def test_importer_applies_lc(page, base_url, test_users, trade_context,
                             error_collector):
    """进口商申请信用证"""
    from tests.e2e.pages.importer_workspace import ImporterWorkspace
    importer = ImporterWorkspace(page, base_url, error_collector)

    importer.login(test_users['importer'].username, 'testpass123')
    importer.navigate()
    lc = importer.apply_letter_of_credit(trade_context.get('contract_id', 1))
    trade_context['lc_id'] = lc.get('id')
    assert not importer.has_errors()


@pytest.mark.trade_phase('08')
def test_bank_issues_lc_and_pays(page, base_url, test_users, trade_context,
                                 error_collector):
    """银行：开证 → 审单 → 付款"""
    from tests.e2e.pages.bank_workspace import BankWorkspace
    bank = BankWorkspace(page, base_url, error_collector)

    bank.login(test_users['bank'].username, 'testpass123')
    bank.navigate()

    bank.issue_lc(trade_context.get('lc_id', 1))
    assert not bank.has_errors()

    bank.review_documents(trade_context.get('lc_id', 1))
    assert not bank.has_errors()

    bank.process_payment(trade_context.get('lc_id', 1))
    assert not bank.has_errors()
```

- [ ] **步骤 3：运行阶段 7-8 测试**

```bash
pytest tests/e2e/trade_flow/test_07_customs.py tests/e2e/trade_flow/test_08_bank.py -v
```

预期：6 个测试通过。

- [ ] **步骤 4：Commit**

```bash
git add tests/e2e/trade_flow/test_07_customs.py tests/e2e/trade_flow/test_08_bank.py
git commit -m "test(e2e): add trade flow phases 7-8 (customs, bank/LC)"
```

---

## 任务 12：阶段 9-10 — 外汇 → 退税 → 完成

**文件：**
- 创建：`tests/e2e/trade_flow/test_09_forex.py`
- 创建：`tests/e2e/trade_flow/test_10_tax.py`

- [ ] **步骤 1：编写 test_09_forex.py**

```python
"""tests/e2e/trade_flow/test_09_forex.py — 阶段9：外汇结算"""

import pytest

pytestmark = pytest.mark.e2e


@pytest.mark.trade_phase('09')
def test_importer_applies_forex(page, base_url, test_users, trade_context,
                                error_collector):
    """进口商申请外汇结算"""
    from tests.e2e.pages.importer_workspace import ImporterWorkspace
    importer = ImporterWorkspace(page, base_url, error_collector)

    importer.login(test_users['importer'].username, 'testpass123')
    importer.navigate()
    forex = importer.apply_forex_settlement(trade_context.get('lc_id', 1))
    trade_context['forex_id'] = forex.get('id')
    assert not importer.has_errors()


@pytest.mark.trade_phase('09')
def test_forex_bureau_approves(page, base_url, test_users, trade_context,
                               error_collector):
    """外汇局：审核 → 批准"""
    from tests.e2e.pages.forex_workspace import ForexWorkspace
    forex = ForexWorkspace(page, base_url, error_collector)

    forex.login(test_users['forex'].username, 'testpass123')
    forex.navigate()

    forex.review(trade_context.get('forex_id', 1))
    assert not forex.has_errors()

    forex.approve(trade_context.get('forex_id', 1))
    assert not forex.has_errors()
```

- [ ] **步骤 2：编写 test_10_tax.py**

```python
"""tests/e2e/trade_flow/test_10_tax.py — 阶段10：退税 → 验证交易完成"""

import pytest

pytestmark = pytest.mark.e2e


@pytest.mark.trade_phase('10')
def test_exporter_applies_tax_refund(page, base_url, test_users, trade_context,
                                     error_collector):
    """出口商申请退税"""
    from tests.e2e.pages.exporter_workspace import ExporterWorkspace
    exporter = ExporterWorkspace(page, base_url, error_collector)

    exporter.login(test_users['exporter'].username, 'testpass123')
    exporter.navigate()
    tax = exporter.apply_tax_refund(trade_context.get('customs_export_id', 1))
    trade_context['tax_id'] = tax.get('id')
    assert not exporter.has_errors()


@pytest.mark.trade_phase('10')
def test_tax_bureau_approves(page, base_url, test_users, trade_context,
                             error_collector):
    """税务局：审核 → 批准退税"""
    from tests.e2e.pages.tax_workspace import TaxWorkspace
    tax = TaxWorkspace(page, base_url, error_collector)

    tax.login(test_users['tax'].username, 'testpass123')
    tax.navigate()

    tax.review(trade_context.get('tax_id', 1))
    assert not tax.has_errors()

    tax.approve(trade_context.get('tax_id', 1))
    assert not tax.has_errors()


@pytest.mark.trade_phase('10')
def test_transaction_completed(page, base_url, test_users, trade_context,
                               error_collector):
    """验证整个交易已完成"""
    from tests.e2e.pages.exporter_workspace import ExporterWorkspace
    exporter = ExporterWorkspace(page, base_url, error_collector)

    exporter.login(test_users['exporter'].username, 'testpass123')
    exporter.navigate()

    tx = exporter.view_transaction(trade_context.get('transaction_id', 1))
    assert not exporter.has_errors()
```

- [ ] **步骤 3：运行阶段 9-10 测试**

```bash
pytest tests/e2e/trade_flow/test_09_forex.py tests/e2e/trade_flow/test_10_tax.py -v
```

预期：5 个测试通过。

- [ ] **步骤 4：运行全链路测试**

```bash
pytest tests/e2e/ -v --tb=short
```

预期：24 个测试全部通过（2+3+2+2+2+2+4+2+2+3 = 24，加上冒烟测试 2 个 = 26）。

- [ ] **步骤 5：Commit**

```bash
git add tests/e2e/trade_flow/test_09_forex.py tests/e2e/trade_flow/test_10_tax.py
git commit -m "test(e2e): add trade flow phases 9-10 (forex, tax, completion)"
```

---

## 任务 13：集成验证 — 全链路测试 + 自动修复实战

**文件：** 无新文件，验证整个系统。

- [ ] **步骤 1：运行全链路测试**

```bash
pytest tests/e2e/ -v --tb=short 2>&1 | tee tests/e2e/artifacts/full_run.log
```

预期：26 个测试通过。如果有失败，自动修复 hook 会尝试修复。

- [ ] **步骤 2：检查自动修复产物**

```bash
ls tests/e2e/artifacts/fixes/
ls tests/e2e/artifacts/screenshots/
ls tests/e2e/artifacts/reports/
```

预期：如果测试全部通过，这些目录为空或不存在。如果有失败后被修复的，fixes/ 中有修复记录。

- [ ] **步骤 3：确认现有测试未受影响**

```bash
pytest apps/ -x -q
```

预期：所有现有单元测试仍然通过。

- [ ] **步骤 4：最终 Commit**

```bash
git add -A tests/e2e/
git commit -m "feat(e2e): complete end-to-end integration test suite with auto-fix"
```
