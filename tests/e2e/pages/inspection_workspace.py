"""tests/e2e/pages/inspection_workspace.py — 商检机构工作台"""

from tests.e2e.pages.base import BasePage


class InspectionWorkspace(BasePage):
    ROLE_CODE = 'inspection'

    def navigate(self):
        self.switch_role(self.ROLE_CODE)

    def inspect(self, application_id):
        self.goto(f'/workspace/{self.ROLE_CODE}/')
        self.click_table_row_action(0, 'inspect')
        self.page.wait_for_load_state('networkidle')
        return self._parse_api_response()

    def pass_inspection(self, application_id):
        self.goto(f'/workspace/{self.ROLE_CODE}/')
        self.click_table_row_action(0, 'pass_inspection')
        self.page.wait_for_load_state('networkidle')
        return self._parse_api_response()

    def certify(self, application_id):
        self.goto(f'/workspace/{self.ROLE_CODE}/')
        self.click_table_row_action(0, 'certify')
        self.page.wait_for_load_state('networkidle')
        return self._parse_api_response()
