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
