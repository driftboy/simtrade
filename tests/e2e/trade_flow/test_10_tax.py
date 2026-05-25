"""tests/e2e/trade_flow/test_10_tax.py — 阶段10：退税 → 验证交易完成"""

import pytest

pytestmark = pytest.mark.e2e


@pytest.mark.trade_phase('10')
def test_exporter_applies_tax_refund(page, base_url, test_users, trade_context,
                                     error_collector):
    from tests.e2e.pages.exporter_workspace import ExporterWorkspace
    exporter = ExporterWorkspace(page, base_url, error_collector)

    exporter.login(test_users['exporter'].username, 'testpass123')
    exporter.navigate()
    tax = exporter.apply_tax_refund(trade_context.get('customs_export_id', 1))
    trade_context['tax_id'] = tax.get('id')
    assert not exporter.has_errors()


@pytest.mark.trade_phase('10')
def test_tax_bureau_approves(page, base_url, test_users, trade_context,
                             error_collector):
    from tests.e2e.pages.tax_workspace import TaxWorkspace
    tax = TaxWorkspace(page, base_url, error_collector)

    tax.login(test_users['tax'].username, 'testpass123')
    tax.navigate()

    tax.review(trade_context.get('tax_id', 1))
    assert not tax.has_errors()

    tax.approve(trade_context.get('tax_id', 1))
    assert not tax.has_errors()


@pytest.mark.trade_phase('10')
def test_transaction_completed(page, base_url, test_users, trade_context,
                               error_collector):
    from tests.e2e.pages.exporter_workspace import ExporterWorkspace
    exporter = ExporterWorkspace(page, base_url, error_collector)

    exporter.login(test_users['exporter'].username, 'testpass123')
    exporter.navigate()

    tx = exporter.view_transaction(trade_context.get('transaction_id', 1))
    assert not exporter.has_errors()
