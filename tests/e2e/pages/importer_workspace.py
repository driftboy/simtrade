"""tests/e2e/pages/importer_workspace.py — 进口商工作台"""

from tests.e2e.pages.base import BasePage


class ImporterWorkspace(BasePage):
    ROLE_CODE = 'importer'

    def navigate(self):
        self.switch_role(self.ROLE_CODE)

    def create_inquiry(self, product_id, quantity, target_price):
        self.goto(f'/workspace/{self.ROLE_CODE}/')
        self.click_action_button('create_order')
        self.page.wait_for_selector('form', timeout=5000)
        self.fill_form_field('#id_product', str(product_id))
        self.fill_form_field('#id_quantity', str(quantity))
        self.fill_form_field('#id_target_price', str(target_price))
        self.submit_form()
        return self._parse_api_response()

    def accept_offer(self, order_id):
        self.goto(f'/workspace/{self.ROLE_CODE}/')
        self.click_table_row_action(0, 'accept')
        return self._parse_api_response()

    def apply_letter_of_credit(self, contract_id):
        self.goto(f'/workspace/{self.ROLE_CODE}/')
        self.click_action_button('apply_lc')
        self.fill_form_field('#id_contract', str(contract_id))
        self.submit_form()
        return self._parse_api_response()

    def declare_import_customs(self, shipment_id):
        self.goto(f'/workspace/{self.ROLE_CODE}/')
        self.click_action_button('declare_import')
        self.fill_form_field('#id_shipment', str(shipment_id))
        self.submit_form()
        return self._parse_api_response()

    def apply_forex_settlement(self, payment_id):
        self.goto(f'/workspace/{self.ROLE_CODE}/')
        self.click_action_button('apply_forex')
        self.fill_form_field('#id_payment', str(payment_id))
        self.submit_form()
        return self._parse_api_response()
