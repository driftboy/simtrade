"""tests/e2e/trade_flow/test_02_contract.py — 阶段2：谈判 → 双方签约"""

import pytest

pytestmark = pytest.mark.e2e


@pytest.mark.trade_phase('02')
def test_importer_accepts_offer(page, base_url, test_users, trade_context,
                                error_collector):
    from tests.e2e.pages.importer_workspace import ImporterWorkspace
    importer = ImporterWorkspace(page, base_url, error_collector)

    importer.login(test_users['importer'].username, 'testpass123')
    importer.navigate()
    importer.accept_offer(trade_context.get('order_id', 1))
    assert not importer.has_errors()


@pytest.mark.trade_phase('02')
def test_exporter_creates_contract(page, base_url, test_users, trade_context,
                                   error_collector):
    from tests.e2e.pages.exporter_workspace import ExporterWorkspace
    exporter = ExporterWorkspace(page, base_url, error_collector)

    exporter.login(test_users['exporter'].username, 'testpass123')
    exporter.navigate()
    contract = exporter.create_contract(
        inquiry_id=trade_context.get('inquiry_id', 1),
        payment_term='L/C',
    )
    trade_context['contract_id'] = contract.get('id')
    assert not exporter.has_errors()


@pytest.mark.trade_phase('02')
def test_both_sign_contract(page, base_url, test_users, trade_context,
                            error_collector):
    from tests.e2e.pages.exporter_workspace import ExporterWorkspace
    from tests.e2e.pages.importer_workspace import ImporterWorkspace

    exporter = ExporterWorkspace(page, base_url, error_collector)
    exporter.login(test_users['exporter'].username, 'testpass123')
    exporter.navigate()
    exporter.sign_contract(trade_context.get('contract_id', 1))
    assert not exporter.has_errors()

    importer = ImporterWorkspace(page, base_url, error_collector)
    importer.login(test_users['importer'].username, 'testpass123')
    importer.navigate()
    importer.sign_contract(trade_context.get('contract_id', 1))
    assert not importer.has_errors()
