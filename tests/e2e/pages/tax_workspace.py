"""tests/e2e/pages/tax_workspace.py — 税务局工作台"""

from tests.e2e.pages.base import BasePage


class TaxWorkspace(BasePage):
    ROLE_CODE = 'tax'

    def navigate(self):
        self.switch_role(self.ROLE_CODE)

    def review(self, refund_id):
        self.goto(f'/workspace/{self.ROLE_CODE}/')
        self.click_table_row_action(0, 'review')
        self.page.wait_for_load_state('networkidle')
        return self._parse_api_response()

    def approve(self, refund_id):
        self.goto(f'/workspace/{self.ROLE_CODE}/')
        self.click_table_row_action(0, 'approve')
        self.page.wait_for_load_state('networkidle')
        return self._parse_api_response()
