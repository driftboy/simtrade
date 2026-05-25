"""tests/e2e/pages/shipping_workspace.py — 货运公司工作台"""

from tests.e2e.pages.base import BasePage


class ShippingWorkspace(BasePage):
    ROLE_CODE = 'shipping'

    def navigate(self):
        self.switch_role(self.ROLE_CODE)

    def confirm_booking(self, shipment_id):
        self.goto(f'/workspace/{self.ROLE_CODE}/')
        self.click_table_row_action(0, 'book')
        self.page.wait_for_load_state('networkidle')
        return self._parse_api_response()

    def load_cargo(self, shipment_id):
        self.goto(f'/workspace/{self.ROLE_CODE}/')
        self.click_table_row_action(0, 'load')
        self.page.wait_for_load_state('networkidle')
        return self._parse_api_response()

    def issue_bill_of_lading(self, shipment_id):
        self.goto(f'/workspace/{self.ROLE_CODE}/')
        self.click_table_row_action(0, 'issue_bl')
        self.page.wait_for_load_state('networkidle')
        return self._parse_api_response()
