"""tests/e2e/pages/forex_workspace.py — 外汇局工作台"""

from tests.e2e.pages.base import BasePage


class ForexWorkspace(BasePage):
    ROLE_CODE = 'forex'

    def navigate(self):
        self.switch_role(self.ROLE_CODE)

    def review(self, settlement_id):
        self.goto(f'/workspace/{self.ROLE_CODE}/')
        self.click_table_row_action(0, 'verify')
        self.page.wait_for_load_state('networkidle')
        return self._parse_api_response()

    def approve(self, settlement_id):
        self.goto(f'/workspace/{self.ROLE_CODE}/')
        self.click_table_row_action(0, 'settle')
        self.page.wait_for_load_state('networkidle')
        return self._parse_api_response()
