"""tests/e2e/trade_flow/test_07_customs.py — 阶段7：海关出口+进口报关 → 放行"""

import pytest

pytestmark = pytest.mark.e2e


@pytest.mark.trade_phase('07')
def test_exporter_declares_export_customs(page, base_url, test_users,
                                          trade_context, error_collector):
    from tests.e2e.pages.exporter_workspace import ExporterWorkspace
    exporter = ExporterWorkspace(page, base_url, error_collector)

    exporter.login(test_users['exporter'].username, 'testpass123')
    exporter.navigate()
    decl = exporter.declare_export_customs(trade_context.get('shipment_id', 1))
    trade_context['customs_export_id'] = decl.get('id')
    assert not exporter.has_errors()


@pytest.mark.trade_phase('07')
def test_customs_clears_export(page, base_url, test_users, trade_context,
                                error_collector):
    from tests.e2e.pages.customs_workspace import CustomsWorkspace
    customs = CustomsWorkspace(page, base_url, error_collector)

    customs.login(test_users['customs'].username, 'testpass123')
    customs.navigate()

    customs.review(trade_context.get('customs_export_id', 1))
    assert not customs.has_errors()

    customs.assess(trade_context.get('customs_export_id', 1))
    assert not customs.has_errors()

    customs.clear(trade_context.get('customs_export_id', 1))
    assert not customs.has_errors()


@pytest.mark.trade_phase('07')
def test_importer_declares_import_customs(page, base_url, test_users,
                                          trade_context, error_collector):
    from tests.e2e.pages.importer_workspace import ImporterWorkspace
    importer = ImporterWorkspace(page, base_url, error_collector)

    importer.login(test_users['importer'].username, 'testpass123')
    importer.navigate()
    decl = importer.declare_import_customs(trade_context.get('shipment_id', 1))
    trade_context['customs_import_id'] = decl.get('id')
    assert not importer.has_errors()


@pytest.mark.trade_phase('07')
def test_customs_clears_import(page, base_url, test_users, trade_context,
                                error_collector):
    from tests.e2e.pages.customs_workspace import CustomsWorkspace
    customs = CustomsWorkspace(page, base_url, error_collector)

    customs.login(test_users['customs'].username, 'testpass123')
    customs.navigate()

    customs.review(trade_context.get('customs_import_id', 1))
    assert not customs.has_errors()

    customs.assess(trade_context.get('customs_import_id', 1))
    assert not customs.has_errors()

    customs.clear(trade_context.get('customs_import_id', 1))
    assert not customs.has_errors()
