"""tests/e2e/trade_flow/test_01_inquiry.py — 阶段1：进口商询价 → 出口商报价"""

import pytest

pytestmark = pytest.mark.e2e


@pytest.mark.trade_phase('01')
def test_importer_creates_inquiry(page, base_url, test_users, test_product,
                                  trade_context, error_collector):
    from tests.e2e.pages.importer_workspace import ImporterWorkspace
    importer = ImporterWorkspace(page, base_url, error_collector)

    importer.login(test_users['importer'].username, 'testpass123')
    importer.navigate()
    trade_context['product_id'] = test_product.id

    result = importer.create_inquiry(
        product_id=test_product.id,
        quantity=100,
        target_price=50.00,
    )
    assert not importer.has_errors(), f'Errors: {error_collector.get_all_errors()}'


@pytest.mark.trade_phase('01')
def test_exporter_responds_offer(page, base_url, test_users, trade_context,
                                 error_collector):
    from tests.e2e.pages.exporter_workspace import ExporterWorkspace
    exporter = ExporterWorkspace(page, base_url, error_collector)

    exporter.login(test_users['exporter'].username, 'testpass123')
    exporter.navigate()

    result = exporter.send_offer(
        order_id=trade_context.get('inquiry_id', 1),
        price=55.00,
        delivery_days=30,
    )
    assert not exporter.has_errors(), f'Errors: {error_collector.get_all_errors()}'
