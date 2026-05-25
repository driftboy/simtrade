"""tests/e2e/pages/factory_workspace.py — 工厂工作台"""

from tests.e2e.pages.base import BasePage


class FactoryWorkspace(BasePage):
    ROLE_CODE = 'factory'

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
