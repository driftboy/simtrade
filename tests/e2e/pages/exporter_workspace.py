"""tests/e2e/pages/exporter_workspace.py — 出口商工作台"""

from tests.e2e.pages.base import BasePage


class ExporterWorkspace(BasePage):
    ROLE_CODE = 'exporter'

    def navigate(self):
        self.switch_role(self.ROLE_CODE)

    def send_offer(self, order_id, price, delivery_days=30):
        self.goto(f'/workspace/{self.ROLE_CODE}/')
        self.click_table_row_action(0, 'offer')
        self.fill_form_field('#id_price', str(price))
        self.fill_form_field('#id_delivery_days', str(delivery_days))
        self.submit_form()
        return self._parse_api_response()

    def create_contract(self, inquiry_id, payment_term='L/C'):
        self.goto(f'/workspace/{self.ROLE_CODE}/')
        self.click_action_button('create_contract')
        self.fill_form_field('#id_inquiry', str(inquiry_id))
        self.fill_form_field('#id_payment_term', payment_term)
        self.submit_form()
        return self._parse_api_response()

    def sign_contract(self, contract_id):
        self.goto(f'/workspace/{self.ROLE_CODE}/')
        self.click_table_row_action(0, 'sign')
        self.page.wait_for_load_state('networkidle')
        return self._parse_api_response()

    def create_purchase_order(self, contract_id):
        self.goto(f'/workspace/{self.ROLE_CODE}/')
        self.click_action_button('create_po')
        self.fill_form_field('#id_contract', str(contract_id))
        self.submit_form()
        return self._parse_api_response()

    def book_shipment(self, order_id):
        self.goto(f'/workspace/{self.ROLE_CODE}/')
        self.click_action_button('book_shipment')
        self.fill_form_field('#id_order', str(order_id))
        self.submit_form()
        return self._parse_api_response()

    def apply_insurance(self, shipment_id):
        self.goto(f'/workspace/{self.ROLE_CODE}/')
        self.click_action_button('apply_insurance')
        self.fill_form_field('#id_shipment', str(shipment_id))
        self.submit_form()
        return self._parse_api_response()

    def apply_inspection(self, order_id):
        self.goto(f'/workspace/{self.ROLE_CODE}/')
        self.click_action_button('apply_inspection')
        self.fill_form_field('#id_order', str(order_id))
        self.submit_form()
        return self._parse_api_response()

    def declare_export_customs(self, shipment_id):
        self.goto(f'/workspace/{self.ROLE_CODE}/')
        self.click_action_button('declare_export')
        self.fill_form_field('#id_shipment', str(shipment_id))
        self.submit_form()
        return self._parse_api_response()

    def apply_tax_refund(self, customs_id):
        self.goto(f'/workspace/{self.ROLE_CODE}/')
        self.click_action_button('apply_tax_refund')
        self.fill_form_field('#id_customs', str(customs_id))
        self.submit_form()
        return self._parse_api_response()

    def view_transaction(self, transaction_id):
        self.goto(f'/workspace/{self.ROLE_CODE}/')
        return self._parse_api_response()
