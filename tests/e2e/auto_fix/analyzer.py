"""tests/e2e/auto_fix/analyzer.py — 错误分析 + 源码定位"""

import os
import re

PROJECT_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
STATIC_JS_DIR = os.path.join(PROJECT_ROOT, 'static', 'js')
TEMPLATES_DIR = os.path.join(PROJECT_ROOT, 'templates')


class FixContext:
    """修复上下文：包含错误信息和源码定位"""

    def __init__(self, error_type, file_path, line_number, error_message,
                 context_code, suggestions=None):
        self.error_type = error_type
        self.file_path = file_path
        self.line_number = line_number
        self.error_message = error_message
        self.context_code = context_code
        self.suggestions = suggestions or []


class ErrorAnalyzer:
    """分析诊断报告，定位源码错误位置"""

    def analyze(self, report):
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
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            start = max(0, line_number - context_lines - 1)
            end = min(len(lines), line_number + context_lines)
            return ''.join(lines[start:end])
        except Exception:
            return ''

    def _classify_error(self, message):
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
        if not os.path.isdir(STATIC_JS_DIR):
            return None
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
