"""tests/e2e/trade_flow/test_03_purchase.py — 阶段3：出口商下单 → 工厂确认发货"""

import pytest

pytestmark = pytest.mark.e2e


@pytest.mark.trade_phase('03')
def test_exporter_orders_from_factory(page, base_url, test_users, trade_context,
                                     error_collector):
    from tests.e2e.pages.exporter_workspace import ExporterWorkspace
    exporter = ExporterWorkspace(page, base_url, error_collector)

    exporter.login(test_users['exporter'].username, 'testpass123')
    exporter.navigate()
    order = exporter.create_purchase_order(
        contract_id=trade_context.get('contract_id', 1)
    )
    trade_context['order_id'] = order.get('id')
    assert not exporter.has_errors()


@pytest.mark.trade_phase('03')
def test_factory_confirms_and_ships(page, base_url, test_users, trade_context,
                                    error_collector):
    from tests.e2e.pages.factory_workspace import FactoryWorkspace
    factory = FactoryWorkspace(page, base_url, error_collector)

    factory.login(test_users['factory'].username, 'testpass123')
    factory.navigate()
    factory.accept_order(trade_context.get('order_id', 1))
    assert not factory.has_errors()

    factory.mark_shipped(trade_context.get('order_id', 1))
    assert not factory.has_errors()
