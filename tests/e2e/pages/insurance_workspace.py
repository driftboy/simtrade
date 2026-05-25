"""tests/e2e/pages/insurance_workspace.py — 保险公司工作台"""

from tests.e2e.pages.base import BasePage


class InsuranceWorkspace(BasePage):
    ROLE_CODE = 'insurance'

    def navigate(self):
        self.switch_role(self.ROLE_CODE)

    def underwrite(self, insurance_id):
        self.goto(f'/workspace/{self.ROLE_CODE}/')
        self.click_table_row_action(0, 'underwrite')
        self.page.wait_for_load_state('networkidle')
        return self._parse_api_response()

    def issue_policy(self, insurance_id):
        self.goto(f'/workspace/{self.ROLE_CODE}/')
        self.click_table_row_action(0, 'issue')
        self.page.wait_for_load_state('networkidle')
        return self._parse_api_response()
