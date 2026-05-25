"""tests/e2e/trade_flow/test_09_forex.py — 阶段9：外汇结算"""

import pytest

pytestmark = pytest.mark.e2e


@pytest.mark.trade_phase('09')
def test_importer_applies_forex(page, base_url, test_users, trade_context,
                                error_collector):
    from tests.e2e.pages.importer_workspace import ImporterWorkspace
    importer = ImporterWorkspace(page, base_url, error_collector)

    importer.login(test_users['importer'].username, 'testpass123')
    importer.navigate()
    forex = importer.apply_forex_settlement(trade_context.get('lc_id', 1))
    trade_context['forex_id'] = forex.get('id')
    assert not importer.has_errors()


@pytest.mark.trade_phase('09')
def test_forex_bureau_approves(page, base_url, test_users, trade_context,
                               error_collector):
    from tests.e2e.pages.forex_workspace import ForexWorkspace
    forex = ForexWorkspace(page, base_url, error_collector)

    forex.login(test_users['forex'].username, 'testpass123')
    forex.navigate()

    forex.review(trade_context.get('forex_id', 1))
    assert not forex.has_errors()

    forex.approve(trade_context.get('forex_id', 1))
    assert not forex.has_errors()
