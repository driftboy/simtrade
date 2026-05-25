"""tests/e2e/trade_flow/test_06_inspection.py — 阶段6：商检申请 → 检验 → 出证"""

import pytest

pytestmark = pytest.mark.e2e


@pytest.mark.trade_phase('06')
def test_exporter_applies_inspection(page, base_url, test_users, trade_context,
                                     error_collector):
    from tests.e2e.pages.exporter_workspace import ExporterWorkspace
    exporter = ExporterWorkspace(page, base_url, error_collector)

    exporter.login(test_users['exporter'].username, 'testpass123')
    exporter.navigate()
    app = exporter.apply_inspection(trade_context.get('order_id', 1))
    trade_context['inspection_id'] = app.get('id')
    assert not exporter.has_errors()


@pytest.mark.trade_phase('06')
def test_inspection_certifies(page, base_url, test_users, trade_context,
                              error_collector):
    from tests.e2e.pages.inspection_workspace import InspectionWorkspace
    insp = InspectionWorkspace(page, base_url, error_collector)

    insp.login(test_users['inspection'].username, 'testpass123')
    insp.navigate()

    insp.inspect(trade_context.get('inspection_id', 1))
    assert not insp.has_errors()

    insp.pass_inspection(trade_context.get('inspection_id', 1))
    assert not insp.has_errors()

    insp.certify(trade_context.get('inspection_id', 1))
    assert not insp.has_errors()
