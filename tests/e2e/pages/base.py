"""tests/e2e/pages/base.py — 所有工作台的公共基类"""

import os
import json

from tests.e2e.error_capture.collector import ErrorCollector


ARTIFACTS_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'artifacts'))


class BasePage:
    """所有角色工作台 Page Object 的公共基类"""

    LOGIN_URL = '/login/'
    WORKSPACE_URL = '/workspace/'

    def __init__(self, page, base_url, error_collector=None):
        self.page = page
        self.base_url = base_url
        self.collector = error_collector or ErrorCollector(page)

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

    def open_workspace(self, role_code):
        """打开指定角色的工作台页面"""
        self.goto(f'{self.WORKSPACE_URL}{role_code}/')
        self.page.wait_for_load_state('networkidle')
        self.page.wait_for_timeout(1000)

    def api_post(self, path, data=None):
        """直接调用后端 API（POST），复用浏览器 cookie（登录态）"""
        csrftoken = ''
        cookies = self.page.context.cookies()
        for c in cookies:
            if c['name'] == 'csrftoken':
                csrftoken = c['value']
                break

        response = self.page.request.post(
            f'{self.base_url}{path}',
            data=data or {},
            headers={'X-CSRFToken': csrftoken},
        )
        try:
            body = response.json()
        except Exception:
            body = {}
        return response.status, body

    def api_get(self, path):
        """直接调用后端 API（GET）"""
        response = self.page.request.get(f'{self.base_url}{path}')
        try:
            body = response.json()
        except Exception:
            body = {}
        return response.status, body

    def has_errors(self):
        return self.collector.has_errors()

    def take_screenshot(self, name):
        path = os.path.join(ARTIFACTS_DIR, 'screenshots', f'{name}.png')
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.page.screenshot(path=path, full_page=True)
        return path
