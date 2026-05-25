"""tests/e2e/conftest.py — E2E 测试公共 fixtures"""

import json
import os

import pytest
from playwright.sync_api import sync_playwright

from tests.e2e.error_capture.collector import ErrorCollector
from tests.e2e.error_capture.reporter import DiagnosticReport
from tests.e2e.auto_fix.analyzer import ErrorAnalyzer
from tests.e2e.auto_fix.fixer import AutoFixer
from tests.e2e.fixtures.users import get_or_create_test_users
from tests.e2e.fixtures.trade_data import create_test_product


SNAPSHOT_DIR = os.path.join(os.path.dirname(__file__), 'artifacts', 'snapshots')


# ── Django fixtures ──

@pytest.fixture(scope='session')
def django_db_setup(django_test_environment, django_db_blocker):
    with django_db_blocker.unblock():
        yield


@pytest.fixture(scope='session')
def test_users(django_db_setup):
    return get_or_create_test_users()


@pytest.fixture(scope='session')
def test_product(test_users, django_db_setup):
    factory_user = test_users['factory']
    return create_test_product(factory_user)


# ── Live server fixture ──

@pytest.fixture(scope='session')
def base_url(live_server):
    return live_server.url


# ── Playwright fixtures ──

@pytest.fixture(scope='session')
def playwright_instance():
    with sync_playwright() as pw:
        yield pw


@pytest.fixture(scope='session')
def browser(playwright_instance):
    b = playwright_instance.chromium.launch(
        headless=True,
        args=['--no-sandbox'],
    )
    yield b
    b.close()


@pytest.fixture
def context(browser):
    ctx = browser.new_context(
        viewport={'width': 1280, 'height': 720},
        ignore_https_errors=True,
    )
    yield ctx
    ctx.close()


@pytest.fixture
def page(context):
    p = context.new_page()
    yield p
    p.close()


@pytest.fixture
def error_collector(page):
    return ErrorCollector(page)


# ── Trade context (shared state across tests) ──

@pytest.fixture(scope='session')
def trade_context():
    snapshot_file = os.path.join(SNAPSHOT_DIR, 'trade_context.json')
    if os.path.exists(snapshot_file):
        with open(snapshot_file, 'r') as f:
            return json.load(f)
    return {
        'product_id': None,
        'inquiry_id': None,
        'order_id': None,
        'contract_id': None,
        'shipment_id': None,
        'insurance_id': None,
        'inspection_id': None,
        'customs_export_id': None,
        'customs_import_id': None,
        'lc_id': None,
        'forex_id': None,
        'tax_id': None,
        'transaction_id': None,
        'completed_phases': [],
    }


@pytest.fixture(autouse=True, scope='session')
def save_trade_context(trade_context):
    yield
    os.makedirs(SNAPSHOT_DIR, exist_ok=True)
    snapshot_file = os.path.join(SNAPSHOT_DIR, 'trade_context.json')
    with open(snapshot_file, 'w') as f:
        json.dump(trade_context, f, indent=2, ensure_ascii=False)


# ── Page Object fixtures (one per role) ──

@pytest.fixture
def importer_page(page, base_url, error_collector):
    from tests.e2e.pages.importer_workspace import ImporterWorkspace
    return ImporterWorkspace(page, base_url, error_collector)


@pytest.fixture
def exporter_page(page, base_url, error_collector):
    from tests.e2e.pages.exporter_workspace import ExporterWorkspace
    return ExporterWorkspace(page, base_url, error_collector)


@pytest.fixture
def factory_page(page, base_url, error_collector):
    from tests.e2e.pages.factory_workspace import FactoryWorkspace
    return FactoryWorkspace(page, base_url, error_collector)


@pytest.fixture
def shipping_page(page, base_url, error_collector):
    from tests.e2e.pages.shipping_workspace import ShippingWorkspace
    return ShippingWorkspace(page, base_url, error_collector)


@pytest.fixture
def insurance_page(page, base_url, error_collector):
    from tests.e2e.pages.insurance_workspace import InsuranceWorkspace
    return InsuranceWorkspace(page, base_url, error_collector)


@pytest.fixture
def inspection_page(page, base_url, error_collector):
    from tests.e2e.pages.inspection_workspace import InspectionWorkspace
    return InspectionWorkspace(page, base_url, error_collector)


@pytest.fixture
def customs_page(page, base_url, error_collector):
    from tests.e2e.pages.customs_workspace import CustomsWorkspace
    return CustomsWorkspace(page, base_url, error_collector)


@pytest.fixture
def bank_page(page, base_url, error_collector):
    from tests.e2e.pages.bank_workspace import BankWorkspace
    return BankWorkspace(page, base_url, error_collector)


@pytest.fixture
def forex_page(page, base_url, error_collector):
    from tests.e2e.pages.forex_workspace import ForexWorkspace
    return ForexWorkspace(page, base_url, error_collector)


@pytest.fixture
def tax_page(page, base_url, error_collector):
    from tests.e2e.pages.tax_workspace import TaxWorkspace
    return TaxWorkspace(page, base_url, error_collector)


# ── Auto-fix hook ──

@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()

    if report.when == 'call' and report.failed:
        page = item.funcargs.get('page')
        error_collector = item.funcargs.get('error_collector')
        if page and error_collector:
            diag = DiagnosticReport()
            diag_report = diag.generate(item.name, error_collector, page)
            diag.save(diag_report)

            contexts = ErrorAnalyzer().analyze(diag_report)
            if contexts:
                try:
                    fixer = AutoFixer()
                    fixer.fix_loop(
                        test_func=item.obj,
                        fix_contexts=contexts,
                        page=page,
                        error_collector=error_collector,
                    )
                except Exception:
                    pass
