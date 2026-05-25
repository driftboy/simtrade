"""tests/e2e/pages/customs_workspace.py — 海关工作台"""

from tests.e2e.pages.base import BasePage


class CustomsWorkspace(BasePage):
    ROLE_CODE = 'customs'

    def navigate(self):
        self.switch_role(self.ROLE_CODE)

    def review(self, declaration_id):
        self.goto(f'/workspace/{self.ROLE_CODE}/')
        self.click_table_row_action(0, 'review')
        self.page.wait_for_load_state('networkidle')
        return self._parse_api_response()

    def assess(self, declaration_id):
        self.goto(f'/workspace/{self.ROLE_CODE}/')
        self.click_table_row_action(0, 'assess')
        self.page.wait_for_load_state('networkidle')
        return self._parse_api_response()

    def clear(self, declaration_id):
        self.goto(f'/workspace/{self.ROLE_CODE}/')
        self.click_table_row_action(0, 'clear')
        self.page.wait_for_load_state('networkidle')
        return self._parse_api_response()
