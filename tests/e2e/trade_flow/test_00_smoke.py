"""tests/e2e/trade_flow/test_00_smoke.py — 冒烟测试：登录 + 工作台加载"""

import pytest

pytestmark = pytest.mark.e2e


@pytest.mark.trade_phase('00')
def test_login_works(page, base_url, test_users):
    user = test_users['importer']
    page.goto(f'{base_url}/login/')
    page.fill('input[name="username"]', user.username)
    page.fill('input[name="password"]', 'testpass123')
    page.click('button[type="submit"]')
    page.wait_for_load_state('networkidle')
    assert '/login/' not in page.url, 'Login failed — still on login page'


@pytest.mark.trade_phase('00')
def test_workspace_loads(page, base_url, test_users, error_collector):
    user = test_users['exporter']
    page.goto(f'{base_url}/login/')
    page.fill('input[name="username"]', user.username)
    page.fill('input[name="password"]', 'testpass123')
    page.click('button[type="submit"]')
    page.wait_for_load_state('networkidle')

    page.goto(f'{base_url}/workspace/exporter/')
    page.wait_for_load_state('networkidle')
    page.wait_for_timeout(2000)

    assert not error_collector.has_errors(), (
        f'JS errors on workspace: {error_collector.get_all_errors()}'
    )
