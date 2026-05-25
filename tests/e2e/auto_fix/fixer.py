"""tests/e2e/auto_fix/fixer.py — Claude API 自动修复"""

import json
import os

import anthropic

from tests.e2e.auto_fix.analyzer import FixContext
from tests.e2e.error_capture.reporter import DiagnosticReport


ARTIFACTS_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'artifacts'))
PROJECT_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
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
        prompt = self._build_prompt(fix_context)
        response = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            messages=[{'role': 'user', 'content': prompt}],
        )
        answer = response.content[0].text
        return self._parse_and_apply(answer, fix_context.file_path)

    def fix_loop(self, test_func, fix_contexts, page, error_collector):
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
