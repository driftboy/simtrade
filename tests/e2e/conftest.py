"""tests/e2e/conftest.py — E2E 测试公共 fixtures"""

import json
import os
import sys

import django
os.environ.setdefault('DJANGO_ALLOW_ASYNC_UNSAFE', 'true')

import pytest
from playwright.sync_api import sync_playwright

if sys.platform == 'win32':
    import asyncio
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except Exception:
        pass

from tests.e2e.error_capture.collector import ErrorCollector
from tests.e2e.error_capture.reporter import DiagnosticReport
from tests.e2e.auto_fix.analyzer import ErrorAnalyzer
from tests.e2e.auto_fix.fixer import AutoFixer


SNAPSHOT_DIR = os.path.join(os.path.dirname(__file__), 'artifacts', 'snapshots')


# ── Live server fixture ──

@pytest.fixture(scope='session')
def base_url(live_server):
    return live_server.url


# ── Playwright + Django data fixtures ──
# All DB access happens BEFORE Playwright launches to avoid async context clash.

@pytest.fixture
def page_with_data(base_url):
    """Combined fixture: creates test data in Django, then launches Playwright browser.

    This ordering is critical: Django ORM must run in a pure-sync context,
    before any Playwright async event loop is created.
    """
    from apps.roles.models import TradeRole, Company
    from apps.core.models import Country
    from apps.users.models import User
    from apps.roles.models import Company, UserCompanyRole

    # ── Phase 1: Django data setup (pure sync, no async loop) ──
    roles_data = [
        ('exporter', '出口商', '负责出口业务'),
        ('importer', '进口商', '负责进口业务'),
        ('factory', '工厂', '负责生产商品'),
        ('bank', '银行', '负责信用证业务'),
        ('customs', '海关', '负责报关审核'),
        ('shipping', '货运公司', '负责国际货运'),
        ('insurance', '保险公司', '负责运输保险'),
        ('inspection', '商检机构', '负责商品检验'),
        ('forex', '外汇局', '负责外汇结算'),
        ('tax', '税务局', '负责出口退税'),
    ]
    for code, name, desc in roles_data:
        TradeRole.objects.get_or_create(code=code, defaults={'name': name, 'description': desc})

    china, _ = Country.objects.get_or_create(code='CN', defaults={'name': '中国', 'name_en': 'China'})

    users = {}
    for code, name, desc in roles_data:
        company, _ = Company.objects.get_or_create(
            code=f'TEST_{code.upper()}',
            defaults={'name': f'测试{name}', 'name_en': f'Test {code.title()}', 'type': 'trade', 'country': china},
        )
        trade_role = TradeRole.objects.get(code=code)
        user, created = User.objects.get_or_create(
            username=f'e2e_{code}',
            defaults={'email': f'{code}@e2e.test', 'user_type': 'student'},
        )
        if created:
            user.set_password('testpass123')
            user.save()
        UserCompanyRole.objects.get_or_create(
            user=user, company=company, role=trade_role,
            defaults={'status': 'approved', 'is_active': True},
        )
        users[code] = user

    # Create test product for factory
    from apps.products.models import Product, Catalog
    factory_ucr = users['factory'].trade_roles.filter(is_active=True).first()
    product, _ = Product.objects.get_or_create(
        code='E2E-001',
        defaults={
            'name': '测试商品-电子元器件', 'name_en': 'Test Electronic Components',
            'hs_code': '8542390000', 'category': 'electronics',
            'description': 'E2E test product', 'unit': 'PCS',
        },
    )
    Catalog.objects.get_or_create(
        product=product, company=factory_ucr.company,
        defaults={
            'sale_price': 100.00, 'currency': 'USD',
            'min_order': 10, 'is_available': True,
        },
    )

    # ── Phase 2: Launch Playwright (creates async loop) ──
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, args=['--no-sandbox'])
        ctx = browser.new_context(viewport={'width': 1280, 'height': 720}, ignore_https_errors=True)
        p = ctx.new_page()
        # Attach data to page for downstream fixtures
        p._test_users = users
        p._test_product = product
        p._company_ids = {code: Company.objects.get(code=f'TEST_{code.upper()}').id for code, _, _ in roles_data}
        yield p
        p.close()
        ctx.close()
        browser.close()


@pytest.fixture
def page(page_with_data):
    return page_with_data


@pytest.fixture
def test_users(page_with_data):
    return page_with_data._test_users


@pytest.fixture
def test_product(page_with_data):
    return page_with_data._test_product


@pytest.fixture
def companies(page_with_data):
    return page_with_data._company_ids


@pytest.fixture
def error_collector(page):
    return ErrorCollector(page)


# ── Trade context ──

@pytest.fixture(scope='session')
def trade_context():
    return {
        'product_id': None, 'inquiry_id': None, 'order_id': None,
        'contract_id': None, 'shipment_id': None, 'insurance_id': None,
        'inspection_id': None, 'customs_export_id': None, 'customs_import_id': None,
        'lc_id': None, 'forex_id': None, 'tax_id': None,
        'transaction_id': None, 'completed_phases': [],
    }


# ── Page Object fixtures ──

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
