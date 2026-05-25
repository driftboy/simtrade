"""tests/e2e/trade_flow/test_04_shipping.py — 阶段4：货运订舱 → 装船 → 签发提单"""

import pytest

pytestmark = pytest.mark.e2e


@pytest.mark.trade_phase('04')
def test_exporter_books_shipment(page, base_url, test_users, trade_context,
                                 error_collector):
    from tests.e2e.pages.exporter_workspace import ExporterWorkspace
    exporter = ExporterWorkspace(page, base_url, error_collector)

    exporter.login(test_users['exporter'].username, 'testpass123')
    exporter.navigate()
    shipment = exporter.book_shipment(trade_context.get('order_id', 1))
    trade_context['shipment_id'] = shipment.get('id')
    assert not exporter.has_errors()


@pytest.mark.trade_phase('04')
def test_shipping_company_processes(page, base_url, test_users, trade_context,
                                    error_collector):
    from tests.e2e.pages.shipping_workspace import ShippingWorkspace
    shipping = ShippingWorkspace(page, base_url, error_collector)

    shipping.login(test_users['shipping'].username, 'testpass123')
    shipping.navigate()

    shipping.confirm_booking(trade_context.get('shipment_id', 1))
    assert not shipping.has_errors()

    shipping.load_cargo(trade_context.get('shipment_id', 1))
    assert not shipping.has_errors()

    shipping.issue_bill_of_lading(trade_context.get('shipment_id', 1))
    assert not shipping.has_errors()
