"""tests/e2e/error_capture/collector.py — 浏览器运行时错误采集器"""

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
