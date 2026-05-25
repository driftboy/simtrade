"""tests/e2e/pages/bank_workspace.py — 银行工作台"""

from tests.e2e.pages.base import BasePage


class BankWorkspace(BasePage):
    ROLE_CODE = 'bank'

    def navigate(self):
        self.switch_role(self.ROLE_CODE)

    def issue_lc(self, lc_id):
        self.goto(f'/workspace/{self.ROLE_CODE}/')
        self.click_table_row_action(0, 'issue')
        self.page.wait_for_load_state('networkidle')
        return self._parse_api_response()

    def review_documents(self, lc_id):
        self.goto(f'/workspace/{self.ROLE_CODE}/')
        self.click_table_row_action(0, 'advise')
        self.page.wait_for_load_state('networkidle')
        return self._parse_api_response()

    def process_payment(self, lc_id):
        self.goto(f'/workspace/{self.ROLE_CODE}/')
        self.click_table_row_action(0, 'pay')
        self.page.wait_for_load_state('networkidle')
        return self._parse_api_response()
