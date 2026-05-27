"""tests/e2e/trade_flow/test_full_chain.py — 全链路贸易流程端到端测试

完整贸易链路：10 个角色、10 个阶段，一个测试方法完成。
通过 API 驱动状态流转，每个阶段打开对应角色工作台验证页面无 JS 错误。
"""

import pytest

pytestmark = pytest.mark.e2e

from tests.e2e.pages.base import BasePage


class TestFullTradeChain:
    """完整贸易链路：10 个角色、10 个阶段"""

    def test_full_trade_chain(
        self, page, base_url, test_users, test_product, companies, error_collector
    ):
        ctx = {}  # shared state across phases

        # ── Phase 1: Inquiry (进口商询价 → 出口商报价) ──
        importer = BasePage(page, base_url, error_collector)
        importer.login(test_users['importer'].username, 'testpass123')

        status, resp = importer.api_post('/api/v1/transactions/', {
            'seller': companies['exporter'],
            'product': test_product.id,
            'quantity': 100,
            'unit_price': 55.00,
            'currency': 'USD',
        })
        assert status in (200, 201), f'Create transaction failed: {status} {resp}'

        # extract transaction id from response or list
        tx_id = None
        if isinstance(resp, dict):
            data = resp.get('data', resp)
            if isinstance(data, dict):
                tx_id = data.get('id')
        if not tx_id:
            status, resp = importer.api_get('/api/v1/transactions/')
            results = resp if isinstance(resp, list) else resp.get('results', resp.get('data', []))
            if isinstance(results, list) and results:
                tx_id = results[-1].get('id')
        ctx['transaction_id'] = tx_id

        importer.open_workspace('importer')
        assert not importer.has_errors(), f'JS errors on importer workspace: {error_collector.get_all_errors()}'

        # exporter sends offer
        exporter = BasePage(page, base_url, error_collector)
        exporter.login(test_users['exporter'].username, 'testpass123')
        if tx_id:
            exporter.api_post(
                f'/api/v1/transactions/{tx_id}/messages/',
                {'message_type': 'offer', 'content': 'USD 55/pc, 30 days delivery'},
            )
        exporter.open_workspace('exporter')
        assert not exporter.has_errors(), f'JS errors on exporter workspace: {error_collector.get_all_errors()}'

        # ── Phase 2: Contract (出口商创建合同 → 双方签署) ──
        status, resp = exporter.api_post('/api/v1/contracts/', {
            'payment_term': 'L/C',
        })
        contract_id = None
        if isinstance(resp, dict):
            data = resp.get('data', resp)
            if isinstance(data, dict):
                contract_id = data.get('id')
        ctx['contract_id'] = contract_id

        if contract_id:
            exporter.api_post(f'/api/v1/contracts/{contract_id}/send_for_confirmation/')
            exporter.api_post(f'/api/v1/contracts/{contract_id}/sign/')

        # importer signs
        importer = BasePage(page, base_url, error_collector)
        importer.login(test_users['importer'].username, 'testpass123')
        if contract_id:
            importer.api_post(f'/api/v1/contracts/{contract_id}/sign/')

        for role in ('exporter', 'importer'):
            ws = BasePage(page, base_url, error_collector)
            ws.login(test_users[role].username, 'testpass123')
            ws.open_workspace(role)
            assert not ws.has_errors(), f'JS errors on {role} workspace: {error_collector.get_all_errors()}'

        # ── Phase 3: Purchase Order (出口商下单 → 工厂确认发货) ──
        exporter = BasePage(page, base_url, error_collector)
        exporter.login(test_users['exporter'].username, 'testpass123')

        status, resp = exporter.api_post('/api/v1/purchase-orders/', {})
        po_id = None
        if isinstance(resp, dict):
            data = resp.get('data', resp)
            if isinstance(data, dict):
                po_id = data.get('id')
        ctx['po_id'] = po_id

        factory = BasePage(page, base_url, error_collector)
        factory.login(test_users['factory'].username, 'testpass123')
        if po_id:
            factory.api_post(f'/api/v1/purchase-orders/{po_id}/confirm/')
            factory.api_post(f'/api/v1/purchase-orders/{po_id}/ship/')

        factory.open_workspace('factory')
        assert not factory.has_errors(), f'JS errors on factory: {error_collector.get_all_errors()}'

        # ── Phase 4: Shipping (货运订舱 → 装船 → 提单) ──
        exporter = BasePage(page, base_url, error_collector)
        exporter.login(test_users['exporter'].username, 'testpass123')

        status, resp = exporter.api_post('/api/v1/shipments/', {})
        ship_id = None
        if isinstance(resp, dict):
            data = resp.get('data', resp)
            if isinstance(data, dict):
                ship_id = data.get('id')
        ctx['ship_id'] = ship_id

        shipping = BasePage(page, base_url, error_collector)
        shipping.login(test_users['shipping'].username, 'testpass123')
        if ship_id:
            shipping.api_post(f'/api/v1/shipments/{ship_id}/book/')
            shipping.api_post(f'/api/v1/shipments/{ship_id}/load/')
            shipping.api_post(f'/api/v1/shipments/{ship_id}/issue_bl/')

        shipping.open_workspace('shipping')
        assert not shipping.has_errors(), f'JS errors on shipping: {error_collector.get_all_errors()}'

        # ── Phase 5: Insurance (保险投保 → 出单) ──
        exporter = BasePage(page, base_url, error_collector)
        exporter.login(test_users['exporter'].username, 'testpass123')

        status, resp = exporter.api_post('/api/v1/insurance-policies/', {})
        ins_id = None
        if isinstance(resp, dict):
            data = resp.get('data', resp)
            if isinstance(data, dict):
                ins_id = data.get('id')
        ctx['ins_id'] = ins_id

        insurance = BasePage(page, base_url, error_collector)
        insurance.login(test_users['insurance'].username, 'testpass123')
        if ins_id:
            insurance.api_post(f'/api/v1/insurance-policies/{ins_id}/underwrite/')
            insurance.api_post(f'/api/v1/insurance-policies/{ins_id}/issue/')

        insurance.open_workspace('insurance')
        assert not insurance.has_errors(), f'JS errors on insurance: {error_collector.get_all_errors()}'

        # ── Phase 6: Inspection (商检 → 通过 → 出证) ──
        exporter = BasePage(page, base_url, error_collector)
        exporter.login(test_users['exporter'].username, 'testpass123')

        status, resp = exporter.api_post('/api/v1/inspection-applications/', {})
        app_id = None
        if isinstance(resp, dict):
            data = resp.get('data', resp)
            if isinstance(data, dict):
                app_id = data.get('id')
        ctx['app_id'] = app_id

        inspection = BasePage(page, base_url, error_collector)
        inspection.login(test_users['inspection'].username, 'testpass123')
        if app_id:
            inspection.api_post(f'/api/v1/inspection-applications/{app_id}/inspect/')
            inspection.api_post(f'/api/v1/inspection-applications/{app_id}/pass_inspection/')
            inspection.api_post(f'/api/v1/inspection-applications/{app_id}/certify/')

        inspection.open_workspace('inspection')
        assert not inspection.has_errors(), f'JS errors on inspection: {error_collector.get_all_errors()}'

        # ── Phase 7: Customs (出口+进口报关 → 放行) ──
        # export declaration
        exporter = BasePage(page, base_url, error_collector)
        exporter.login(test_users['exporter'].username, 'testpass123')

        status, resp = exporter.api_post('/api/v1/customs-declarations/', {
            'declaration_type': 'export',
        })
        export_decl_id = None
        if isinstance(resp, dict):
            data = resp.get('data', resp)
            if isinstance(data, dict):
                export_decl_id = data.get('id')

        customs = BasePage(page, base_url, error_collector)
        customs.login(test_users['customs'].username, 'testpass123')
        if export_decl_id:
            customs.api_post(f'/api/v1/customs-declarations/{export_decl_id}/review/')
            customs.api_post(f'/api/v1/customs-declarations/{export_decl_id}/assess/')
            customs.api_post(f'/api/v1/customs-declarations/{export_decl_id}/clear/')

        customs.open_workspace('customs')
        assert not customs.has_errors(), f'JS errors on customs: {error_collector.get_all_errors()}'

        # import declaration
        importer = BasePage(page, base_url, error_collector)
        importer.login(test_users['importer'].username, 'testpass123')

        status, resp = importer.api_post('/api/v1/customs-declarations/', {
            'declaration_type': 'import',
        })
        import_decl_id = None
        if isinstance(resp, dict):
            data = resp.get('data', resp)
            if isinstance(data, dict):
                import_decl_id = data.get('id')

        if import_decl_id:
            customs2 = BasePage(page, base_url, error_collector)
            customs2.login(test_users['customs'].username, 'testpass123')
            customs2.api_post(f'/api/v1/customs-declarations/{import_decl_id}/review/')
            customs2.api_post(f'/api/v1/customs-declarations/{import_decl_id}/assess/')
            customs2.api_post(f'/api/v1/customs-declarations/{import_decl_id}/clear/')

        # ── Phase 8: Letter of Credit (信用证 → 开证 → 付款) ──
        importer = BasePage(page, base_url, error_collector)
        importer.login(test_users['importer'].username, 'testpass123')

        status, resp = importer.api_post('/api/v1/letters-of-credit/', {})
        lc_id = None
        if isinstance(resp, dict):
            data = resp.get('data', resp)
            if isinstance(data, dict):
                lc_id = data.get('id')
        ctx['lc_id'] = lc_id

        bank = BasePage(page, base_url, error_collector)
        bank.login(test_users['bank'].username, 'testpass123')
        if lc_id:
            bank.api_post(f'/api/v1/letters-of-credit/{lc_id}/issue/')
            bank.api_post(f'/api/v1/letters-of-credit/{lc_id}/advise/')
            bank.api_post(f'/api/v1/letters-of-credit/{lc_id}/pay/')

        bank.open_workspace('bank')
        assert not bank.has_errors(), f'JS errors on bank: {error_collector.get_all_errors()}'

        # ── Phase 9: Forex Settlement (外汇结算) ──
        exporter = BasePage(page, base_url, error_collector)
        exporter.login(test_users['exporter'].username, 'testpass123')

        status, resp = exporter.api_post('/api/v1/forex-settlements/', {})
        forex_id = None
        if isinstance(resp, dict):
            data = resp.get('data', resp)
            if isinstance(data, dict):
                forex_id = data.get('id')

        forex = BasePage(page, base_url, error_collector)
        forex.login(test_users['forex'].username, 'testpass123')
        if forex_id:
            forex.api_post(f'/api/v1/forex-settlements/{forex_id}/verify/')
            forex.api_post(f'/api/v1/forex-settlements/{forex_id}/settle/')

        forex.open_workspace('forex')
        assert not forex.has_errors(), f'JS errors on forex: {error_collector.get_all_errors()}'

        # ── Phase 10: Tax Refund (退税 → 验证) ──
        exporter = BasePage(page, base_url, error_collector)
        exporter.login(test_users['exporter'].username, 'testpass123')

        status, resp = exporter.api_post('/api/v1/tax-refund-applications/', {})
        tax_id = None
        if isinstance(resp, dict):
            data = resp.get('data', resp)
            if isinstance(data, dict):
                tax_id = data.get('id')

        tax = BasePage(page, base_url, error_collector)
        tax.login(test_users['tax'].username, 'testpass123')
        if tax_id:
            tax.api_post(f'/api/v1/tax-refund-applications/{tax_id}/approve/')
            tax.api_post(f'/api/v1/tax-refund-applications/{tax_id}/refund/')

        tax.open_workspace('tax')
        assert not tax.has_errors(), f'JS errors on tax: {error_collector.get_all_errors()}'
