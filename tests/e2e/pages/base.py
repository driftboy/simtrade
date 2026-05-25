"""tests/e2e/pages/base.py — 所有工作台的公共基类"""

import os

from tests.e2e.error_capture.collector import ErrorCollector
from tests.e2e.error_capture.reporter import DiagnosticReport


ARTIFACTS_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'artifacts'))


class BasePage:
    """所有角色工作台 Page Object 的公共基类"""

    LOGIN_URL = '/login/'
    WORKSPACE_URL = '/workspace/'

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
        self.goto(self.LOGIN_URL)
        self.page.fill('input[name="username"]', username)
        self.page.fill('input[name="password"]', password)
        self.page.click('button[type="submit"]')
        self.page.wait_for_load_state('networkidle')
        self.page.wait_for_timeout(500)

    def switch_role(self, role_code):
        self.goto(f'{self.WORKSPACE_URL}{role_code}/')
        self.page.wait_for_load_state('networkidle')
        self.page.wait_for_timeout(500)
        self._wait_for_workspace_loaded()

    def _wait_for_workspace_loaded(self):
        try:
            self.page.wait_for_function(
                "() => document.querySelector('.workspace-content') !== null",
                timeout=10000,
            )
        except Exception:
            pass
        self.page.wait_for_timeout(1000)

    def click_action_button(self, action_name):
        button = self.page.locator(f'button[data-action="{action_name}"]')
        if button.count() == 0:
            button = self.page.locator(f'.action-btn:has-text("{action_name}")')
        button.first.click()
        self.page.wait_for_load_state('networkidle')
        self.page.wait_for_timeout(500)

    def get_current_status(self):
        status_cell = self.page.locator('table tbody tr:first-child td:nth-child(3)')
        if status_cell.count() > 0:
            return status_cell.first.text_content().strip()
        return None

    def get_table_rows(self):
        return self.page.locator('table tbody tr').count()

    def click_table_row_action(self, row_index, action_name):
        row = self.page.locator('table tbody tr').nth(row_index)
        action_btn = row.locator(f'button[data-action="{action_name}"]')
        if action_btn.count() == 0:
            action_btn = row.locator(f'button:has-text("{action_name}")')
        action_btn.first.click()
        self.page.wait_for_load_state('networkidle')
        self.page.wait_for_timeout(500)

    def click_first_row(self):
        self.page.locator('table tbody tr:first-child').first.click()
        self.page.wait_for_load_state('networkidle')
        self.page.wait_for_timeout(500)

    def fill_form_field(self, selector, value):
        self.page.fill(selector, str(value))

    def submit_form(self, selector='button[type="submit"]'):
        self.page.click(selector)
        self.page.wait_for_load_state('networkidle')
        self.page.wait_for_timeout(500)

    def has_errors(self):
        return self.collector.has_errors()

    def take_screenshot(self, name):
        path = os.path.join(ARTIFACTS_DIR, 'screenshots', f'{name}.png')
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.page.screenshot(path=path, full_page=True)
        return path

    def get_element_text(self, selector):
        el = self.page.locator(selector)
        if el.count() > 0:
            return el.first.text_content()
        return None

    def _parse_api_response(self):
        try:
            return self.page.evaluate("() => window.__lastApiResponse || {}")
        except Exception:
            return {}
