"""tests/e2e/trade_flow/test_05_insurance.py — 阶段5：保险投保 → 出单"""

import pytest

pytestmark = pytest.mark.e2e


@pytest.mark.trade_phase('05')
def test_exporter_applies_insurance(page, base_url, test_users, trade_context,
                                    error_collector):
    from tests.e2e.pages.exporter_workspace import ExporterWorkspace
    exporter = ExporterWorkspace(page, base_url, error_collector)

    exporter.login(test_users['exporter'].username, 'testpass123')
    exporter.navigate()
    insurance = exporter.apply_insurance(trade_context.get('shipment_id', 1))
    trade_context['insurance_id'] = insurance.get('id')
    assert not exporter.has_errors()


@pytest.mark.trade_phase('05')
def test_insurance_company_issues(page, base_url, test_users, trade_context,
                                  error_collector):
    from tests.e2e.pages.insurance_workspace import InsuranceWorkspace
    ins = InsuranceWorkspace(page, base_url, error_collector)

    ins.login(test_users['insurance'].username, 'testpass123')
    ins.navigate()
    ins.underwrite(trade_context.get('insurance_id', 1))
    assert not ins.has_errors()

    ins.issue_policy(trade_context.get('insurance_id', 1))
    assert not ins.has_errors()
