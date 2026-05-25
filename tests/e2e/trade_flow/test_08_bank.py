"""tests/e2e/trade_flow/test_08_bank.py — 阶段8：信用证申请 → 开证 → 付款"""

import pytest

pytestmark = pytest.mark.e2e


@pytest.mark.trade_phase('08')
def test_importer_applies_lc(page, base_url, test_users, trade_context,
                             error_collector):
    from tests.e2e.pages.importer_workspace import ImporterWorkspace
    importer = ImporterWorkspace(page, base_url, error_collector)

    importer.login(test_users['importer'].username, 'testpass123')
    importer.navigate()
    lc = importer.apply_letter_of_credit(trade_context.get('contract_id', 1))
    trade_context['lc_id'] = lc.get('id')
    assert not importer.has_errors()


@pytest.mark.trade_phase('08')
def test_bank_issues_lc_and_pays(page, base_url, test_users, trade_context,
                                 error_collector):
    from tests.e2e.pages.bank_workspace import BankWorkspace
    bank = BankWorkspace(page, base_url, error_collector)

    bank.login(test_users['bank'].username, 'testpass123')
    bank.navigate()

    bank.issue_lc(trade_context.get('lc_id', 1))
    assert not bank.has_errors()

    bank.review_documents(trade_context.get('lc_id', 1))
    assert not bank.has_errors()

    bank.process_payment(trade_context.get('lc_id', 1))
    assert not bank.has_errors()
