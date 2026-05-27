"""
生成完整的国际贸易样本交易数据。

基于真实国际贸易惯例创建一个 CIF 术语 + 信用证付款的出口案例：
  出口商（深圳华信电子）向美国进口商（Pacific Digital）出口蓝牙耳机 5000 台，
  贸易术语 CIF Los Angeles，付款方式 L/C at sight。

涵盖全部 10 个贸易环节及对应单证数据。
"""
import json
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.core.models import Country, Currency, Port
from apps.products.models import Product
from apps.roles.models import Company, TradeRole, UserCompanyRole
from apps.users.models import User
from apps.transactions.models import (
    Transaction, Contract, LetterOfCredit, BankOperation,
    PurchaseOrder, Shipment, InsurancePolicy,
    CustomsDeclaration, InspectionApplication,
    ForexSettlement, TaxRefundApplication,
    TransactionLog,
)
from apps.documents.models import Document, DocumentTemplate


class Command(BaseCommand):
    help = '生成完整的国际贸易样本交易数据（CIF + L/C 场景）'

    # ──────────────────────────────────────────────────────────────
    # 辅助方法
    # ──────────────────────────────────────────────────────────────

    @staticmethod
    def _ensure_country(code, name, phone_code=''):
        """确保国家存在"""
        country, created = Country.objects.get_or_create(
            code=code,
            defaults={'name': name, 'phone_code': phone_code}
        )
        return country

    @staticmethod
    def _ensure_currency(code, name, symbol=''):
        """确保货币存在"""
        currency, created = Currency.objects.get_or_create(
            code=code,
            defaults={'name': name, 'symbol': symbol}
        )
        return currency

    @staticmethod
    def _ensure_product(code, name, name_en, category, unit, hs_code, description=''):
        """确保商品存在"""
        product, created = Product.objects.get_or_create(
            code=code,
            defaults={
                'name': name, 'name_en': name_en,
                'category': category, 'unit': unit,
                'hs_code': hs_code, 'description': description,
            }
        )
        return product

    @staticmethod
    def _create_company(code, name, name_en, country_code, ctype, addr, phone, email):
        """创建或获取公司，返回 (company, created) 元组"""
        country = Country.objects.filter(code=country_code).first()
        company, created = Company.objects.get_or_create(
            code=code,
            defaults={
                'name': name, 'name_en': name_en,
                'country': country, 'type': ctype,
                'address': addr, 'phone': phone, 'email': email,
            }
        )
        return company, created

    # ──────────────────────────────────────────────────────────────
    # 主入口
    # ──────────────────────────────────────────────────────────────

    def handle(self, *args, **options):
        now = timezone.now()

        # ── 0. 前置检查 ──────────────────────────────────────────
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write('初始化样本交易数据')
        self.stdout.write('=' * 60)

        # 确保基础数据存在
        cn = Country.objects.filter(code='CN').first()
        us = Country.objects.filter(code='US').first()
        if not cn or not us:
            self.stdout.write(self.style.ERROR(
                '缺少国家数据，请先运行: python manage.py init_data'))
            return

        product = Product.objects.filter(code='E001').first()
        if not product:
            self.stdout.write(self.style.ERROR(
                '缺少商品数据，请先运行: python manage.py init_products'))
            return

        usd = Currency.objects.filter(code='USD').first()
        cny = Currency.objects.filter(code='CNY').first()
        sz_port = Port.objects.filter(code='CNSZX').first()
        la_port = Port.objects.filter(code='USLAX').first()

        # ── 1. 创建样本公司 ──────────────────────────────────────
        self.stdout.write('\n[1/10] 创建样本公司...')

        companies = {}

        company, created = self._create_company(
            'EXP01', '深圳华信电子科技有限公司', 'Shenzhen Huaxin Electronics Tech Co., Ltd.',
            'CN', 'exporter',
            '深圳市南山区科技园南路88号华信大厦', '+86-755-86001234', 'trade@huaxin-elec.com')
        companies['exporter'] = company
        self.stdout.write(f'  [{"CREATE" if created else "SKIP"}] {company.name}')

        company, created = self._create_company(
            'IMP01', 'Pacific Digital Trading LLC', 'Pacific Digital Trading LLC',
            'US', 'importer',
            '1200 Wilshire Blvd, Suite 500, Los Angeles, CA 90017', '+1-213-555-0188', 'purchase@pacdigital.com')
        companies['importer'] = company
        self.stdout.write(f'  [{"CREATE" if created else "SKIP"}] {company.name}')

        company, created = self._create_company(
            'FAC01', '东莞光电制造厂', 'Dongguan Opto-Electronics Factory',
            'CN', 'factory',
            '东莞市长安镇霄边工业区第8栋', '+86-769-85001234', 'sales@dgeofactory.cn')
        companies['factory'] = company
        self.stdout.write(f'  [{"CREATE" if created else "SKIP"}] {company.name}')

        company, created = self._create_company(
            'BNK01', '中国银行深圳市分行', 'Bank of China Shenzhen Branch',
            'CN', 'bank',
            '深圳市福田区深南大道1003号', '+86-755-25801234', 'trade@boc-sz.com')
        companies['bank'] = company
        self.stdout.write(f'  [{"CREATE" if created else "SKIP"}] {company.name}')

        company, created = self._create_company(
            'CUS01', '深圳海关', 'Shenzhen Customs District',
            'CN', 'customs',
            '深圳市福田区福中三路海关大厦', '+86-755-84301234', 'service@szcustoms.gov.cn')
        companies['customs'] = company
        self.stdout.write(f'  [{"CREATE" if created else "SKIP"}] {company.name}')

        company, created = self._create_company(
            'SHP01', '中远海运集装箱运输有限公司', 'COSCO Shipping Lines Co., Ltd.',
            'CN', 'shipping',
            '上海市浦东新区滨江大道528号', '+86-21-65966138', 'booking@cosco.com')
        companies['shipping'] = company
        self.stdout.write(f'  [{"CREATE" if created else "SKIP"}] {company.name}')

        company, created = self._create_company(
            'INS01', '中国人民财产保险股份有限公司', 'PICC Property and Casualty Co., Ltd.',
            'CN', 'insurance',
            '北京市西城区西长安街88号', '+86-10-68301234', 'cargo@picc.com.cn')
        companies['insurance'] = company
        self.stdout.write(f'  [{"CREATE" if created else "SKIP"}] {company.name}')

        company, created = self._create_company(
            'IQ01', '深圳出入境检验检疫局', 'Shenzhen Entry-Exit Inspection and Quarantine Bureau',
            'CN', 'inspection',
            '深圳市福田区福强路1011号', '+86-755-83701234', 'inspect@szciq.gov.cn')
        companies['inspection'] = company
        self.stdout.write(f'  [{"CREATE" if created else "SKIP"}] {company.name}')

        company, created = self._create_company(
            'FX01', '国家外汇管理局深圳分局', 'SAFE Shenzhen Branch',
            'CN', 'forex',
            '深圳市福田区深南大道1099号', '+86-755-25591234', 'forex@safe-sz.gov.cn')
        companies['forex'] = company
        self.stdout.write(f'  [{"CREATE" if created else "SKIP"}] {company.name}')

        company, created = self._create_company(
            'TAX01', '深圳市国家税务局', 'Shenzhen State Tax Bureau',
            'CN', 'tax',
            '深圳市福田区沙嘴路38号', '+86-755-83801234', 'taxrefund@sz-tax.gov.cn')
        companies['tax'] = company
        self.stdout.write(f'  [{"CREATE" if created else "SKIP"}] {company.name}')

        # ── 1b. 创建样本用户 ───────────────────────────────────
        self.stdout.write('\n[1b] 创建样本用户...')

        huaxin_user, created = User.objects.get_or_create(
            username='huaxin',
            defaults={
                'email': 'trade@huaxin-elec.com',
                'user_type': 'student',
                'is_active': True,
            }
        )
        if created:
            huaxin_user.set_password('123456')
            huaxin_user.save()
            self.stdout.write(self.style.SUCCESS('  [CREATE] 用户 huaxin'))
        else:
            self.stdout.write('  [SKIP] 用户 huaxin 已存在')

        # 关联出口商角色
        exporter_role = TradeRole.objects.filter(code='exporter').first()
        if exporter_role and companies.get('exporter'):
            UserCompanyRole.objects.get_or_create(
                user=huaxin_user,
                company=companies['exporter'],
                role=exporter_role,
                defaults={'status': 'active'}
            )
            self.stdout.write('  [OK] 已关联出口商角色')

        # ── 创建场景数据 ──────────────────────────────────────
        result = self._create_scenario_cif_lc(now, companies, huaxin_user)

        # ── 场景 2：FOB + T/T ──────────────────────────────────
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write('场景 2：FOB + T/T（智能手表出口阿联酋）')
        self.stdout.write('=' * 60)
        result2 = self._create_scenario_fob_tt(now, companies, huaxin_user)

        # ── 汇总 ─────────────────────────────────────────────────
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('样本交易数据生成完毕！'))
        self.stdout.write('=' * 60)
        self.stdout.write(f'  公司: {Company.objects.count()} 家')
        self.stdout.write('')
        self.stdout.write('  场景 1: CIF + L/C（蓝牙耳机出口美国）')
        self.stdout.write(f'  交易: #{result["transaction"].id}')
        self.stdout.write(f'  合同: {result["contract"].contract_no}')
        self.stdout.write(f'  信用证: {result["lc"].lc_no}')
        self.stdout.write(f'  采购订单: {result["po"].order_no}')
        self.stdout.write(f'  货运: {result["shipment"].shipment_no}')
        self.stdout.write(f'  保险: {result["insurance"].policy_no}')
        self.stdout.write(f'  报检: {result["inspection"].application_no}')
        self.stdout.write(f'  报关: {result["customs"].declaration_no}')
        self.stdout.write(f'  外汇结算: {result["forex"].settlement_no}')
        self.stdout.write(f'  退税: {result["tax_refund"].application_no}')
        self.stdout.write('')
        self.stdout.write('  场景 2: FOB + T/T（智能手表出口阿联酋）')
        self.stdout.write(f'  交易: #{result2["transaction"].id}')
        self.stdout.write(f'  合同: {result2["contract"].contract_no}')
        self.stdout.write(f'  采购订单: {result2["po"].order_no}')
        self.stdout.write(f'  货运: {result2["shipment"].shipment_no}')
        self.stdout.write(f'  报检: {result2["inspection"].application_no}')
        self.stdout.write(f'  报关: {result2["customs"].declaration_no}')
        self.stdout.write(f'  外汇结算(30%): {result2["forex1"].settlement_no}')
        self.stdout.write(f'  外汇结算(70%): {result2["forex2"].settlement_no}')
        self.stdout.write(f'  退税: {result2["tax_refund"].application_no}')
        self.stdout.write(f'  单证记录: {Document.objects.count()} 份')

    # ──────────────────────────────────────────────────────────────
    # 场景：CIF + L/C 出口美国（蓝牙耳机）
    # ──────────────────────────────────────────────────────────────

    def _create_scenario_cif_lc(self, now, companies, huaxin_user):
        """CIF + L/C 场景：蓝牙耳机出口美国"""

        product = Product.objects.filter(code='E001').first()
        sz_port = Port.objects.filter(code='CNSZX').first()
        la_port = Port.objects.filter(code='USLAX').first()

        # ── 2. 创建交易 ──────────────────────────────────────────
        self.stdout.write('\n[2/10] 创建交易记录...')

        transaction, created = Transaction.objects.get_or_create(
            pk=9001,
            defaults={
                'buyer': companies['importer'],
                'seller': companies['exporter'],
                'product': product,
                'status': 'in_progress',
                'quantity': 5000,
                'unit_price': Decimal('12.50'),
                'currency': 'USD',
                'trade_term': 'CIF',
                'port_of_loading': 'Shenzhen' if not sz_port else sz_port.name,
                'port_of_discharge': 'Los Angeles' if not la_port else la_port.name,
                'notes': '样本交易：蓝牙耳机出口美国，CIF Los Angeles，L/C at sight',
            }
        )
        tag = 'CREATE' if created else 'SKIP'
        self.stdout.write(f'  [{tag}] 交易 #{transaction.id}')

        # ── 3. 创建外销合同 ──────────────────────────────────────
        self.stdout.write('\n[3/10] 创建外销合同...')

        contract_date = (now - timedelta(days=30)).date()
        delivery_date = (now - timedelta(days=5)).date()

        contract, created = Contract.objects.get_or_create(
            contract_no='HX2026SC001',
            defaults={
                'transaction': transaction,
                'status': 'effective',
                'trade_term': 'CIF',
                'payment_term': 'L/C at sight',
                'delivery_time': delivery_date,
                'port_of_loading': 'Shenzhen',
                'port_of_discharge': 'Los Angeles, USA',
                'product_name': '蓝牙耳机 Bluetooth Earphone',
                'product_spec': '型号: HX-BT5Pro / 蓝牙5.3 / ANC主动降噪 / 40小时续航 / IPX5防水',
                'quantity': 5000,
                'unit': 'PCS',
                'unit_price': Decimal('12.50'),
                'total_amount': Decimal('62500.00'),
                'currency': 'USD',
                'packing': '每只耳机独立包装，50只/外箱，100外箱/托盘，共2个托盘',
                'shipping_marks': (
                    'HX2026SC001\n'
                    'LOS ANGELES\n'
                    'C/NO.: 1-100\n'
                    'G.W.: 14.5 KGS\n'
                    'N.W.: 12.0 KGS\n'
                    'MEAS: 45×35×30 CM'
                ),
                'remarks': (
                    '1. 装运期：不迟于2026年6月15日\n'
                    '2. 允许分批装运：不允许\n'
                    '3. 允许转船：不允许\n'
                    '4. 品质以中国商品检验局检验证书为准\n'
                    '5. 按 CIF Los Angeles 成交，卖方负责投保一切险'
                ),
                'seller_signed_at': now - timedelta(days=30),
                'buyer_signed_at': now - timedelta(days=29),
                'effective_at': now - timedelta(days=29),
            }
        )
        tag = 'CREATE' if created else 'SKIP'
        self.stdout.write(f'  [{tag}] 合同 {contract.contract_no}')

        # ── 4. 创建信用证 ────────────────────────────────────────
        self.stdout.write('\n[4/10] 创建信用证...')

        lc_issue_date = (now - timedelta(days=27)).date()
        lc_expiry_date = (now + timedelta(days=15)).date()
        latest_shipment = (now - timedelta(days=3)).date()

        lc, created = LetterOfCredit.objects.get_or_create(
            lc_no='BOCSZ/2026/LC00856',
            defaults={
                'contract': contract,
                'transaction': transaction,
                'status': 'negotiated',
                'issuing_bank': 'Wells Fargo Bank, N.A., Los Angeles Branch',
                'advising_bank': '中国银行深圳市分行',
                'applicant': companies['importer'],
                'beneficiary': companies['exporter'],
                'amount': Decimal('62500.00'),
                'currency': 'USD',
                'issue_date': lc_issue_date,
                'expiry_date': lc_expiry_date,
                'latest_shipment_date': latest_shipment,
                'port_of_loading': 'Shenzhen, China',
                'port_of_discharge': 'Los Angeles, USA',
                'documents_required': [
                    'Signed Commercial Invoice in triplicate',
                    'Full set of 3/3 clean on board ocean Bills of Lading',
                    'Packing List in triplicate',
                    'Insurance Policy/Certificate for 110% of invoice value covering All Risks',
                    'Certificate of Origin (FORM A)',
                    'Inspection Certificate issued by CCIC',
                    'Beneficiary Certificate certifying that shipping advice has been sent',
                ],
                'issued_at': now - timedelta(days=27),
                'advised_at': now - timedelta(days=26),
                'submitted_at': now - timedelta(days=2),
                'negotiated_at': now - timedelta(days=1),
            }
        )
        tag = 'CREATE' if created else 'SKIP'
        self.stdout.write(f'  [{tag}] 信用证 {lc.lc_no}')

        # 银行操作记录
        bank_ops = [
            ('issue', 'system', lc_issue_date),
            ('advise', 'system', lc_issue_date + timedelta(days=1)),
            ('negotiate', 'system', now - timedelta(days=1)),
        ]
        for op_type, processed_by, op_date in bank_ops:
            BankOperation.objects.get_or_create(
                lc=lc, operation_type=op_type,
                defaults={
                    'processed_by': processed_by,
                    'notes': f'{dict(BankOperation.OPERATION_TYPES).get(op_type, op_type)}操作',
                    'result': {'status': 'success', 'date': str(op_date)},
                }
            )

        # ── 5. 创建采购订单 ──────────────────────────────────────
        self.stdout.write('\n[5/10] 创建采购订单...')

        po_delivery = (now - timedelta(days=10)).date()

        po, created = PurchaseOrder.objects.get_or_create(
            order_no='PO20260517001',
            defaults={
                'transaction': transaction,
                'buyer': companies['exporter'],
                'seller': companies['factory'],
                'product_name': '蓝牙耳机 HX-BT5Pro',
                'product_code': 'E001',
                'quantity': Decimal('5000'),
                'unit': 'PCS',
                'unit_price': Decimal('48.00'),
                'currency': 'CNY',
                'total_amount': Decimal('240000.00'),
                'delivery_date': po_delivery,
                'delivery_address': '深圳市南山区科技园南路88号华信大厦仓库',
                'status': 'completed',
                'notes': '含ANC降噪模块、蓝牙5.3芯片、IPX5防水结构',
                'shipped_at': now - timedelta(days=8),
                'invoiced_at': now - timedelta(days=7),
                'completed_at': now - timedelta(days=7),
            }
        )
        tag = 'CREATE' if created else 'SKIP'
        self.stdout.write(f'  [{tag}] 采购订单 {po.order_no}')

        # ── 6. 创建货运订单 ──────────────────────────────────────
        self.stdout.write('\n[6/10] 创建货运订单...')

        etd = (now - timedelta(days=5)).date()
        eta = etd + timedelta(days=18)

        shipment, created = Shipment.objects.get_or_create(
            shipment_no='SH20260522001',
            defaults={
                'contract': contract,
                'shipper': companies['exporter'],
                'carrier': companies['shipping'],
                'booking_no': 'COSCO26MA22HK003',
                'bl_no': 'COSU6289510340',
                'vessel_name': 'COSCO SHIPPING GALAXY V.025E',
                'port_of_loading': 'Shenzhen (Yantian), China',
                'port_of_discharge': 'Los Angeles, USA',
                'etd': etd,
                'eta': eta,
                'container_no': 'TGHU4729510 / 40HC',
                'freight_amount': Decimal('3200.00'),
                'freight_currency': 'USD',
                'status': 'shipped',
                'notes': 'CY to CY, 1×40\'HC Container',
                'booked_at': now - timedelta(days=12),
                'loaded_at': now - timedelta(days=5),
                'shipped_at': now - timedelta(days=4),
            }
        )
        tag = 'CREATE' if created else 'SKIP'
        self.stdout.write(f'  [{tag}] 货运订单 {shipment.shipment_no}')

        # ── 7. 创建保险单 ────────────────────────────────────────
        self.stdout.write('\n[7/10] 创建保险单...')

        insurance, created = InsurancePolicy.objects.get_or_create(
            policy_no='PICC2026SH05220001',
            defaults={
                'contract': contract,
                'shipment': shipment,
                'insured': companies['exporter'],
                'insurer': companies['insurance'],
                'cargo_description': (
                    '5000 PCS Bluetooth Earphone (HX-BT5Pro) '
                    'as per Contract No. HX2026SC001 '
                    'Shipped per COSCO SHIPPING GALAXY V.025E '
                    'from Shenzhen to Los Angeles'
                ),
                'insured_amount': Decimal('68750.00'),  # 110% of CIF value
                'premium': Decimal('412.50'),  # ~0.6% of insured amount
                'premium_currency': 'CNY',
                'coverage_type': 'all_risk',
                'status': 'issued',
                'notes': 'Covering All Risks and War Risk as per CIC 1/1/1981',
                'underwritten_at': now - timedelta(days=6),
                'issued_at': now - timedelta(days=5),
            }
        )
        tag = 'CREATE' if created else 'SKIP'
        self.stdout.write(f'  [{tag}] 保险单 {insurance.policy_no}')

        # ── 8. 创建报检记录 ──────────────────────────────────────
        self.stdout.write('\n[8/10] 创建报检记录...')

        inspection, created = InspectionApplication.objects.get_or_create(
            application_no='IA20260518001',
            defaults={
                'shipment': shipment,
                'applicant': companies['exporter'],
                'inspector': companies['inspection'],
                'product_name': '蓝牙耳机 HX-BT5Pro',
                'product_spec': '蓝牙5.3, ANC主动降噪, IPX5防水',
                'quantity': Decimal('5000'),
                'goods_value': Decimal('62500.00'),
                'inspection_type': 'legal',
                'fee': Decimal('800.00'),
                'fee_currency': 'CNY',
                'certificate_no': 'CIQ20260520001',
                'origin_certificate_no': 'GSP/CCPIT2026/00856',
                'status': 'certified',
                'notes': '依据 GB/T 14217-2011 标准，外观/功能/安全检验合格',
                'inspecting_at': now - timedelta(days=8),
                'passed_at': now - timedelta(days=7),
                'certified_at': now - timedelta(days=6),
            }
        )
        tag = 'CREATE' if created else 'SKIP'
        self.stdout.write(f'  [{tag}] 报检记录 {inspection.application_no}')

        # ── 9. 创建报关单 ────────────────────────────────────────
        self.stdout.write('\n[9/10] 创建报关单...')

        customs, created = CustomsDeclaration.objects.get_or_create(
            declaration_no='CD20260522001',
            defaults={
                'shipment': shipment,
                'declarant': companies['exporter'],
                'customs_office': companies['customs'],
                'hs_code': '85183000',
                'goods_name': '蓝牙耳机 Bluetooth Earphone (Headphone)',
                'quantity': Decimal('5000'),
                'unit_value': Decimal('12.50'),
                'total_value': Decimal('62500.00'),
                'currency': 'USD',
                'duty_rate': Decimal('0'),  # 出口关税为 0
                'duty_amount': Decimal('0'),
                'vat_rate': Decimal('0.13'),
                'vat_amount': Decimal('0'),  # 出口免增值税
                'status': 'cleared',
                'notes': '监管条件无特殊要求，出口退税率为13%',
                'reviewed_at': now - timedelta(days=5),
                'assessed_at': now - timedelta(days=5),
                'cleared_at': now - timedelta(days=5),
            }
        )
        tag = 'CREATE' if created else 'SKIP'
        self.stdout.write(f'  [{tag}] 报关单 {customs.declaration_no}')

        # ── 10. 创建外汇结算与退税 ────────────────────────────────
        self.stdout.write('\n[10/10] 创建外汇结算与退税...')

        forex, created = ForexSettlement.objects.get_or_create(
            settlement_no='FX20260525001',
            defaults={
                'customs_declaration': customs,
                'applicant': companies['exporter'],
                'forex_bureau': companies['forex'],
                'foreign_currency': 'USD',
                'foreign_amount': Decimal('62500.00'),
                'reference_rate': Decimal('7.2450'),
                'reference_cny_amount': Decimal('452812.50'),
                'settlement_rate': Decimal('7.2380'),
                'settlement_cny_amount': Decimal('452375.00'),
                'status': 'settled',
                'notes': '已收汇并结汇，收汇金额与报关金额一致',
                'verified_at': now - timedelta(days=1),
                'settled_at': now,
            }
        )
        tag = 'CREATE' if created else 'SKIP'
        self.stdout.write(f'  [{tag}] 外汇结算 {forex.settlement_no}')

        tax_refund, created = TaxRefundApplication.objects.get_or_create(
            application_no='TR20260526001',
            defaults={
                'customs_declaration': customs,
                'applicant': companies['exporter'],
                'tax_bureau': companies['tax'],
                'hs_code': '85183000',
                'total_value': Decimal('452375.00'),  # CNY equivalent
                'refund_rate': Decimal('0.13'),
                'refund_amount': Decimal('58808.75'),  # ~13% of VAT-paid value
                'refund_currency': 'CNY',
                'status': 'approved',
                'notes': '退税率13%，依据出口报关单及增值税发票核准',
                'reviewing_at': now - timedelta(days=1),
                'approved_at': now,
            }
        )
        tag = 'CREATE' if created else 'SKIP'
        self.stdout.write(f'  [{tag}] 退税申请 {tax_refund.application_no}')

        # ── 11. 生成单证记录 ─────────────────────────────────────
        self.stdout.write('\n[11] 生成单证记录...')

        self._create_documents(now, contract, transaction, lc, shipment,
                               insurance, inspection, customs, companies,
                               huaxin_user)

        return {
            'transaction': transaction,
            'contract': contract,
            'lc': lc,
            'po': po,
            'shipment': shipment,
            'insurance': insurance,
            'inspection': inspection,
            'customs': customs,
            'forex': forex,
            'tax_refund': tax_refund,
        }

    # ──────────────────────────────────────────────────────────────
    # 场景：FOB + T/T 出口阿联酋（智能手表）
    # ──────────────────────────────────────────────────────────────

    def _create_scenario_fob_tt(self, now, companies, sample_user):
        """FOB + T/T 场景：智能手表出口阿联酋"""

        # ── 新公司 ──────────────────────────────────────────
        self.stdout.write('\n[新增公司] 创建场景 2 公司...')

        exp02, created = self._create_company(
            'EXP02', '深圳华芯电子科技有限公司',
            'Shenzhen Huaxin Chip Electronics Co., Ltd.',
            'CN', 'electronics',
            '深圳市福田区华强北路赛格广场A座1208',
            '+86-755-83001234', 'trade@huaxin-chip.com')
        self.stdout.write(f'  [{"CREATE" if created else "SKIP"}] {exp02.name}')

        imp02, created = self._create_company(
            'IMP02', 'Al Rashid Trading LLC',
            'Al Rashid Trading LLC',
            'AE', 'trading',
            'Dubai Silicon Oasis, DDP Building A, Office 305',
            '+971-4-3201234', 'import@alrashid-trading.ae')
        self.stdout.write(f'  [{"CREATE" if created else "SKIP"}] {imp02.name}')

        # ── 商品 ──────────────────────────────────────────
        product = self._ensure_product(
            'E002', '智能手表 Smart Watch', 'Smart Watch HX-WatchPro',
            'electronics', 'PCS', '910212',
            '1.69寸AMOLED屏, 心率血氧, GPS, IP68防水, 7天续航')
        self.stdout.write(f'  [OK] 商品 {product.name}')

        # ── 交易 ──────────────────────────────────────────
        self.stdout.write('\n[2/10] 创建交易记录 (FOB+TT)...')

        transaction, created = Transaction.objects.get_or_create(
            pk=9002,
            defaults={
                'buyer': imp02,
                'seller': exp02,
                'product': product,
                'status': 'completed',
                'quantity': 2000,
                'unit_price': Decimal('25.00'),
                'currency': 'USD',
                'trade_term': 'FOB',
                'port_of_loading': 'Shenzhen',
                'port_of_discharge': 'Jebel Ali, Dubai',
                'notes': '样本交易：智能手表出口阿联酋，FOB Shenzhen，T/T 30%+70%',
            }
        )
        tag = 'CREATE' if created else 'SKIP'
        self.stdout.write(f'  [{tag}] 交易 #{transaction.id}')

        # ── 合同 ──────────────────────────────────────────
        self.stdout.write('\n[3/10] 创建外销合同 (FOB+TT)...')

        delivery_date = (now - timedelta(days=5)).date()

        contract, created = Contract.objects.get_or_create(
            contract_no='HXCHIP2026SC001',
            defaults={
                'transaction': transaction,
                'status': 'effective',
                'trade_term': 'FOB',
                'payment_term': 'T/T (30% advance + 70% against B/L copy)',
                'delivery_time': delivery_date,
                'port_of_loading': 'Shenzhen',
                'port_of_discharge': 'Jebel Ali, Dubai',
                'product_name': '智能手表 Smart Watch HX-WatchPro',
                'product_spec': '型号: HX-WatchPro / 1.69寸AMOLED / 心率血氧GPS / IP68防水 / 7天续航',
                'quantity': 2000,
                'unit': 'PCS',
                'unit_price': Decimal('25.00'),
                'total_amount': Decimal('50000.00'),
                'currency': 'USD',
                'packing': '每只手表独立包装，20只/外箱，共100外箱',
                'shipping_marks': (
                    'HXCHIP2026SC001\n'
                    'JEBEL ALI, DUBAI\n'
                    'C/NO.: 1-100\n'
                    'G.W.: 12.0 KGS\n'
                    'N.W.: 10.0 KGS\n'
                    'MEAS: 50×40×35 CM'
                ),
                'remarks': (
                    '1. 装运期：不迟于2026年6月10日\n'
                    '2. 允许分批装运：不允许\n'
                    '3. 允许转船：不允许\n'
                    '4. 品质以中国商品检验局检验证书为准\n'
                    '5. 按 FOB Shenzhen 成交，买方负责保险和运费'
                ),
                'seller_signed_at': now - timedelta(days=20),
                'buyer_signed_at': now - timedelta(days=19),
                'effective_at': now - timedelta(days=19),
            }
        )
        tag = 'CREATE' if created else 'SKIP'
        self.stdout.write(f'  [{tag}] 合同 {contract.contract_no}')

        # ── 无信用证（T/T 付款）──

        # ── 采购订单 ──────────────────────────────────────
        self.stdout.write('\n[5/10] 创建采购订单 (FOB+TT)...')

        po_delivery = (now - timedelta(days=10)).date()

        po, created = PurchaseOrder.objects.get_or_create(
            order_no='PO20260528002',
            defaults={
                'transaction': transaction,
                'buyer': exp02,
                'seller': companies['factory'],
                'product_name': '智能手表 HX-WatchPro',
                'product_code': 'E002',
                'quantity': Decimal('2000'),
                'unit': 'PCS',
                'unit_price': Decimal('128.00'),
                'currency': 'CNY',
                'total_amount': Decimal('256000.00'),
                'delivery_date': po_delivery,
                'delivery_address': '深圳市福田区华强北路赛格广场A座1208仓库',
                'status': 'completed',
                'notes': '智能手表HX-WatchPro，AMOLED屏+心率血氧+GPS+IP68',
                'shipped_at': now - timedelta(days=8),
                'invoiced_at': now - timedelta(days=7),
                'completed_at': now - timedelta(days=7),
            }
        )
        tag = 'CREATE' if created else 'SKIP'
        self.stdout.write(f'  [{tag}] 采购订单 {po.order_no}')

        # ── 货运 ──────────────────────────────────────────
        self.stdout.write('\n[6/10] 创建货运订单 (FOB+TT)...')

        etd = (now - timedelta(days=5)).date()
        eta = etd + timedelta(days=14)

        shipment, created = Shipment.objects.get_or_create(
            shipment_no='SH20260601001',
            defaults={
                'contract': contract,
                'shipper': exp02,
                'carrier': companies['shipping'],
                'booking_no': 'CMA26MA01SZ001',
                'bl_no': 'CMDU5678234100',
                'vessel_name': 'CMA CGM MARCO POLO V.023W',
                'port_of_loading': 'Shenzhen (Yantian), China',
                'port_of_discharge': 'Jebel Ali, Dubai, UAE',
                'etd': etd,
                'eta': eta,
                'container_no': 'BMOU3948201 / 20GP',
                'freight_amount': Decimal('1800.00'),
                'freight_currency': 'USD',
                'status': 'shipped',
                'notes': "CY to CY, 1x20'GP Container",
                'booked_at': now - timedelta(days=10),
                'loaded_at': now - timedelta(days=5),
                'shipped_at': now - timedelta(days=4),
            }
        )
        tag = 'CREATE' if created else 'SKIP'
        self.stdout.write(f'  [{tag}] 货运订单 {shipment.shipment_no}')

        # ── 无保险（FOB 术语下卖方不负责保险）──

        # ── 报检 ──────────────────────────────────────────
        self.stdout.write('\n[8/10] 创建报检记录 (FOB+TT)...')

        inspection, created = InspectionApplication.objects.get_or_create(
            application_no='IA20260528002',
            defaults={
                'shipment': shipment,
                'applicant': exp02,
                'inspector': companies['inspection'],
                'product_name': '智能手表 HX-WatchPro',
                'product_spec': '1.69寸AMOLED, 心率血氧, GPS, IP68防水',
                'quantity': Decimal('2000'),
                'goods_value': Decimal('50000.00'),
                'inspection_type': 'legal',
                'fee': Decimal('600.00'),
                'fee_currency': 'CNY',
                'certificate_no': 'CIQ20260529002',
                'origin_certificate_no': 'GSP/CCPIT2026/001',
                'status': 'certified',
                'notes': '依据 GB/T 22780-2017 标准，外观/功能/安全检验合格',
                'inspecting_at': now - timedelta(days=7),
                'passed_at': now - timedelta(days=6),
                'certified_at': now - timedelta(days=5),
            }
        )
        tag = 'CREATE' if created else 'SKIP'
        self.stdout.write(f'  [{tag}] 报检记录 {inspection.application_no}')

        # ── 报关 ──────────────────────────────────────────
        self.stdout.write('\n[9/10] 创建报关单 (FOB+TT)...')

        customs, created = CustomsDeclaration.objects.get_or_create(
            declaration_no='CD20260601002',
            defaults={
                'shipment': shipment,
                'declarant': exp02,
                'customs_office': companies['customs'],
                'hs_code': '910212',
                'goods_name': '智能手表 Smart Watch (Wrist-watch)',
                'quantity': Decimal('2000'),
                'unit_value': Decimal('25.00'),
                'total_value': Decimal('50000.00'),
                'currency': 'USD',
                'duty_rate': Decimal('0'),
                'duty_amount': Decimal('0'),
                'vat_rate': Decimal('0.13'),
                'vat_amount': Decimal('0'),
                'status': 'cleared',
                'notes': '监管条件无特殊要求，出口退税率为13%',
                'reviewed_at': now - timedelta(days=5),
                'assessed_at': now - timedelta(days=5),
                'cleared_at': now - timedelta(days=5),
            }
        )
        tag = 'CREATE' if created else 'SKIP'
        self.stdout.write(f'  [{tag}] 报关单 {customs.declaration_no}')

        # ── 外汇结算（两笔：30% 预付 + 70% 见提单副本）────
        self.stdout.write('\n[10/10] 创建外汇结算与退税 (FOB+TT)...')

        forex1, created = ForexSettlement.objects.get_or_create(
            settlement_no='FX20260530002',
            defaults={
                'customs_declaration': customs,
                'applicant': exp02,
                'forex_bureau': companies['forex'],
                'foreign_currency': 'USD',
                'foreign_amount': Decimal('15000.00'),
                'reference_rate': Decimal('7.2450'),
                'reference_cny_amount': Decimal('108675.00'),
                'settlement_rate': Decimal('7.2380'),
                'settlement_cny_amount': Decimal('108570.00'),
                'status': 'settled',
                'notes': 'T/T 预付 30%',
                'verified_at': now - timedelta(days=3),
                'settled_at': now - timedelta(days=3),
            }
        )
        tag = 'CREATE' if created else 'SKIP'
        self.stdout.write(f'  [{tag}] 外汇结算(30%预付) {forex1.settlement_no}')

        forex2, created = ForexSettlement.objects.get_or_create(
            settlement_no='FX20260602002',
            defaults={
                'customs_declaration': customs,
                'applicant': exp02,
                'forex_bureau': companies['forex'],
                'foreign_currency': 'USD',
                'foreign_amount': Decimal('35000.00'),
                'reference_rate': Decimal('7.2450'),
                'reference_cny_amount': Decimal('253575.00'),
                'settlement_rate': Decimal('7.2380'),
                'settlement_cny_amount': Decimal('253330.00'),
                'status': 'settled',
                'notes': 'T/T 尾款 70%，凭提单副本付款',
                'verified_at': now - timedelta(days=1),
                'settled_at': now,
            }
        )
        tag = 'CREATE' if created else 'SKIP'
        self.stdout.write(f'  [{tag}] 外汇结算(70%尾款) {forex2.settlement_no}')

        # ── 退税 ──────────────────────────────────────────
        total_value_cny = Decimal('361900.00')  # 50000 * 7.238

        tax_refund, created = TaxRefundApplication.objects.get_or_create(
            application_no='TR20260603002',
            defaults={
                'customs_declaration': customs,
                'applicant': exp02,
                'tax_bureau': companies['tax'],
                'hs_code': '910212',
                'total_value': total_value_cny,
                'refund_rate': Decimal('0.13'),
                'refund_amount': Decimal('47047.00'),
                'refund_currency': 'CNY',
                'status': 'approved',
                'notes': '退税率13%，依据出口报关单及增值税发票核准',
                'reviewing_at': now - timedelta(days=1),
                'approved_at': now,
            }
        )
        tag = 'CREATE' if created else 'SKIP'
        self.stdout.write(f'  [{tag}] 退税申请 {tax_refund.application_no}')

        # ── 单证 ──────────────────────────────────────────
        self.stdout.write('\n[单证] 生成场景 2 单证记录...')

        self._create_fob_tt_documents(
            now, contract, transaction, shipment,
            inspection, customs, companies,
            exp02, imp02, sample_user)

        return {
            'transaction': transaction,
            'contract': contract,
            'po': po,
            'shipment': shipment,
            'inspection': inspection,
            'customs': customs,
            'forex1': forex1,
            'forex2': forex2,
            'tax_refund': tax_refund,
        }

    def _create_fob_tt_documents(self, now, contract, transaction, shipment,
                                  inspection, customs, companies,
                                  exp02, imp02, sample_user):
        """创建 FOB + T/T 场景的单证记录"""

        invoice_date = (now - timedelta(days=5)).strftime('%Y-%m-%d')
        bl_date = (now - timedelta(days=4)).strftime('%Y-%m-%d')

        documents_data = [
            # 1. 商业发票
            {
                'template_code': 'commercial_invoice',
                'status': 'approved',
                'data': json.dumps({
                    'invoice_no': 'HXCHIP-INV-2026-001',
                    'invoice_date': invoice_date,
                    'seller_name': 'Shenzhen Huaxin Chip Electronics Co., Ltd.',
                    'seller_address': 'Seg Plaza Tower A, 1208 Huaqiang North Rd, Futian, Shenzhen, China',
                    'buyer_name': 'Al Rashid Trading LLC',
                    'buyer_address': 'Dubai Silicon Oasis, DDP Building A, Office 305, Dubai, UAE',
                    'contract_no': 'HXCHIP2026SC001',
                    'trade_term': 'FOB Shenzhen, Incoterms 2020',
                    'payment_term': 'T/T (30% advance + 70% against B/L copy)',
                    'from_port': 'Shenzhen (Yantian), China',
                    'to_port': 'Jebel Ali, Dubai, UAE',
                    'vessel': 'CMA CGM MARCO POLO V.023W',
                    'container_no': 'BMOU3948201',
                    'items': [
                        {
                            'marks': 'HXCHIP2026SC001\nJEBEL ALI, DUBAI\nC/NO.1-100\nG.W.:12.0KGS',
                            'description': 'Smart Watch Model HX-WatchPro\n1.69" AMOLED, Heart Rate, SpO2, GPS, IP68\nHS Code: 910212',
                            'quantity': '2000',
                            'unit': 'PCS',
                            'unit_price': '25.00',
                            'amount': '50000.00',
                        }
                    ],
                    'total_amount': 'USD 50,000.00',
                    'packing': '100 cartons',
                    'gross_weight': '1,200.00 KGS',
                    'net_weight': '1,000.00 KGS',
                    'total_packages': '100 CARTONS',
                }, ensure_ascii=False, indent=2),
            },

            # 2. 装箱单
            {
                'template_code': 'packing_list',
                'status': 'approved',
                'data': json.dumps({
                    'packing_list_no': 'HXCHIP-PL-2026-001',
                    'invoice_no': 'HXCHIP-INV-2026-001',
                    'packing_date': invoice_date,
                    'shipper': 'Shenzhen Huaxin Chip Electronics Co., Ltd.',
                    'consignee': 'Al Rashid Trading LLC',
                    'destination': 'Jebel Ali, Dubai, UAE',
                    'shipping_marks': 'HXCHIP2026SC001 / JEBEL ALI, DUBAI / C/NO.1-100',
                    'items': [
                        {
                            'carton_no': 'C/NO. 1-50',
                            'description': 'HX-WatchPro Smart Watch (Black)',
                            'qty_per_carton': '20 PCS',
                            'total_qty': '1000 PCS',
                            'net_weight': '500.00 KGS',
                            'gross_weight': '600.00 KGS',
                            'measurement': '50×40×35 CM × 50',
                        },
                        {
                            'carton_no': 'C/NO. 51-100',
                            'description': 'HX-WatchPro Smart Watch (Silver)',
                            'qty_per_carton': '20 PCS',
                            'total_qty': '1000 PCS',
                            'net_weight': '500.00 KGS',
                            'gross_weight': '600.00 KGS',
                            'measurement': '50×40×35 CM × 50',
                        },
                    ],
                    'total_cartons': '100',
                    'total_net_weight': '1,000.00 KGS',
                    'total_gross_weight': '1,200.00 KGS',
                    'total_measurement': '3.5 CBM',
                    'package_type': 'Carton',
                }, ensure_ascii=False, indent=2),
            },

            # 3. 海运提单
            {
                'template_code': 'bill_of_lading',
                'status': 'approved',
                'data': json.dumps({
                    'bl_no': 'CMDU5678234100',
                    'booking_no': 'CMA26MA01SZ001',
                    'shipper': 'Shenzhen Huaxin Chip Electronics Co., Ltd.\nSeg Plaza Tower A, 1208 Huaqiang North Rd\nFutian District, Shenzhen 518031, China',
                    'consignee': 'TO ORDER OF SHIPPER',
                    'notify_party': 'Al Rashid Trading LLC\nDubai Silicon Oasis, DDP Building A, Office 305\nDubai, UAE\nAttn: Mr. Ahmed Al Rashid\nTel: +971-4-3201234',
                    'vessel': 'CMA CGM MARCO POLO',
                    'voyage': '023W',
                    'port_of_loading': 'Shenzhen (Yantian), China',
                    'port_of_discharge': 'Jebel Ali, Dubai, UAE',
                    'etd': (now - timedelta(days=5)).strftime('%Y-%m-%d'),
                    'eta': (now + timedelta(days=9)).strftime('%Y-%m-%d'),
                    'container_no': 'BMOU3948201',
                    'container_type': "1×20'GP",
                    'seal_no': 'CM260601B',
                    'description': '2000 PCS Smart Watch\nHS Code: 910212\nGW: 1,200 KGS\n100 CARTONS',
                    'freight': 'FREIGHT COLLECT (FOB)',
                    'bl_issued_at': (now - timedelta(days=4)).strftime('%Y-%m-%d'),
                    'bl_originals': '3/3 ORIGINAL',
                    'on_board_date': (now - timedelta(days=4)).strftime('%Y-%m-%d'),
                }, ensure_ascii=False, indent=2),
            },

            # 4. 产地证
            {
                'template_code': 'certificate_of_origin',
                'status': 'approved',
                'data': json.dumps({
                    'certificate_no': 'GSP/CCPIT2026/001',
                    'certificate_type': 'FORM A (Generalized System of Preferences)',
                    'goods_consigned_from': 'Shenzhen Huaxin Chip Electronics Co., Ltd.\nSeg Plaza Tower A, 1208 Huaqiang North Rd\nFutian District, Shenzhen 518031, China',
                    'goods_consigned_to': 'Al Rashid Trading LLC\nDubai Silicon Oasis, DDP Building A, Office 305\nDubai, UAE',
                    'means_of_transport': 'BY VESSEL: CMA CGM MARCO POLO V.023W',
                    'port_of_loading': 'Shenzhen (Yantian), China',
                    'port_of_discharge': 'Jebel Ali, Dubai, UAE',
                    'item_details': [
                        {
                            'marks': 'HXCHIP2026SC001\nJEBEL ALI, DUBAI',
                            'description': 'Smart Watch Model HX-WatchPro',
                            'quantity': '2,000 PCS',
                            'origin_criterion': 'P (Wholly produced in China)',
                        }
                    ],
                    'issue_date': (now - timedelta(days=6)).strftime('%Y-%m-%d'),
                    'issuing_authority': 'China Council for the Promotion of International Trade (CCPIT)',
                    'certification': 'It is hereby certified that the goods described above originate in China',
                }, ensure_ascii=False, indent=2),
            },

            # 5. 报检单
            {
                'template_code': 'inspection_application',
                'status': 'approved',
                'data': json.dumps({
                    'application_no': 'IA20260528002',
                    'applicant': 'Shenzhen Huaxin Chip Electronics Co., Ltd.',
                    'inspector': 'Shenzhen Entry-Exit Inspection and Quarantine Bureau',
                    'product_name': '智能手表 HX-WatchPro',
                    'product_spec': '1.69寸AMOLED, 心率血氧, GPS, IP68防水',
                    'hs_code': '910212',
                    'quantity': '2,000 PCS',
                    'goods_value': 'USD 50,000.00',
                    'inspection_type': '法定检验',
                    'inspection_standard': 'GB/T 22780-2017',
                    'inspection_items': '外观检查、功能测试、电气安全、电磁兼容、防水等级',
                    'result': '合格',
                    'certificate_no': 'CIQ20260529002',
                    'application_date': (now - timedelta(days=8)).strftime('%Y-%m-%d'),
                    'inspection_date': (now - timedelta(days=7)).strftime('%Y-%m-%d'),
                    'pass_date': (now - timedelta(days=6)).strftime('%Y-%m-%d'),
                }, ensure_ascii=False, indent=2),
            },

            # 6. 检验证书
            {
                'template_code': 'inspection_certificate',
                'status': 'approved',
                'data': json.dumps({
                    'certificate_no': 'CIQ20260529002',
                    'applicant': 'Shenzhen Huaxin Chip Electronics Co., Ltd.',
                    'product_name': 'Smart Watch Model HX-WatchPro',
                    'hs_code': '910212',
                    'quantity': '2,000 PCS',
                    'contract_no': 'HXCHIP2026SC001',
                    'inspection_result': 'QUALITY AND QUANTITY FOUND TO BE IN CONFORMITY WITH THE CONTRACT STIPULATIONS',
                    'inspection_standard': 'GB/T 22780-2017',
                    'inspection_date': (now - timedelta(days=6)).strftime('%Y-%m-%d'),
                    'issue_date': (now - timedelta(days=5)).strftime('%Y-%m-%d'),
                    'inspector': 'Shenzhen Entry-Exit Inspection and Quarantine Bureau',
                    'remarks': 'Sample rate: AQL 1.0 Level II, All items passed',
                }, ensure_ascii=False, indent=2),
            },

            # 7. 出口报关单
            {
                'template_code': 'export_declaration',
                'status': 'approved',
                'data': json.dumps({
                    'declaration_no': 'CD20260601002',
                    'declaration_type': '出口报关',
                    'declarant': '深圳华芯电子科技有限公司',
                    'customs_office': '深圳海关（大鹏海关）',
                    'trade_mode': '一般贸易 (0110)',
                    'transport_mode': '海运 (2)',
                    'hs_code': '910212.00',
                    'goods_name': '智能手表 Smart Watch (Wrist-watch)',
                    'specification': 'HX-WatchPro',
                    'quantity': '2,000',
                    'unit': '只',
                    'unit_price': '25.00',
                    'total_value': 'USD 50,000.00',
                    'currency': 'USD',
                    'country_of_destination': '阿联酋 (AE)',
                    'port_of_loading': '深圳盐田 (CNSZX)',
                    'port_of_discharge': '杰贝阿里 (AEJEA)',
                    'container_no': 'BMOU3948201',
                    'gross_weight': '1,200 KGS',
                    'net_weight': '1,000 KGS',
                    'package_count': '100 纸箱',
                    'contract_no': 'HXCHIP2026SC001',
                    'supervision_code': '无',
                    'rebate_rate': '13%',
                    'declaration_date': (now - timedelta(days=5)).strftime('%Y-%m-%d'),
                    'clearance_date': (now - timedelta(days=5)).strftime('%Y-%m-%d'),
                }, ensure_ascii=False, indent=2),
            },

            # 8. 装船通知
            {
                'template_code': 'shipping_advice',
                'status': 'approved',
                'data': json.dumps({
                    'advice_no': 'HXCHIP-SA-2026-001',
                    'advice_date': (now - timedelta(days=4)).strftime('%Y-%m-%d'),
                    'from': 'Shenzhen Huaxin Chip Electronics Co., Ltd.',
                    'to': 'Al Rashid Trading LLC',
                    'contract_no': 'HXCHIP2026SC001',
                    'commodity': '2000 PCS Smart Watch (HX-WatchPro)',
                    'vessel': 'CMA CGM MARCO POLO V.023W',
                    'bl_no': 'CMDU5678234100',
                    'container_no': 'BMOU3948201',
                    'etd': (now - timedelta(days=5)).strftime('%Y-%m-%d'),
                    'eta': (now + timedelta(days=9)).strftime('%Y-%m-%d'),
                    'port_of_loading': 'Shenzhen (Yantian), China',
                    'port_of_discharge': 'Jebel Ali, Dubai, UAE',
                    'shipping_marks': 'HXCHIP2026SC001 / JEBEL ALI, DUBAI / C/NO.1-100',
                    'message': (
                        'We hereby inform you that the above mentioned goods have been shipped '
                        'on board the above vessel on the date shown. Please arrange for import '
                        'clearance and cargo reception accordingly.\n\n'
                        'As per our agreement, 70% balance payment (USD 35,000.00) is due upon '
                        'presentation of B/L copy. Please remit payment promptly.'
                    ),
                }, ensure_ascii=False, indent=2),
            },
        ]

        for doc_data in documents_data:
            template = DocumentTemplate.objects.filter(
                code=doc_data['template_code']
            ).first()
            if not template:
                self.stdout.write(self.style.WARNING(
                    f"  [SKIP] 模板不存在: {doc_data['template_code']}"))
                continue

            doc, created = Document.objects.get_or_create(
                template=template,
                transaction_id=transaction.id,
                defaults={
                    'status': doc_data['status'],
                    'data': doc_data['data'],
                    'created_by': sample_user,
                }
            )
            if not created and not doc.created_by:
                doc.created_by = sample_user
                doc.save(update_fields=['created_by'])
            tag = 'CREATE' if created else 'SKIP'
            self.stdout.write(f'  [{tag}] {template.name}')

    # ──────────────────────────────────────────────────────────────
    # 单证数据生成
    # ──────────────────────────────────────────────────────────────

    def _create_documents(self, now, contract, transaction, lc, shipment,
                          insurance, inspection, customs, companies,
                          sample_user):
        """创建全套单证记录"""

        invoice_date = (now - timedelta(days=5)).strftime('%Y-%m-%d')
        bl_date = (now - timedelta(days=4)).strftime('%Y-%m-%d')

        documents_data = [
            # 1. 商业发票
            {
                'template_code': 'commercial_invoice',
                'status': 'approved',
                'data': json.dumps({
                    'invoice_no': 'HX-INV-2026-00856',
                    'invoice_date': invoice_date,
                    'seller_name': 'Shenzhen Huaxin Electronics Tech Co., Ltd.',
                    'seller_address': 'Huaxin Building, 88 Keji Yuan South Rd, Nanshan, Shenzhen, China',
                    'buyer_name': 'Pacific Digital Trading LLC',
                    'buyer_address': '1200 Wilshire Blvd, Suite 500, Los Angeles, CA 90017, USA',
                    'contract_no': 'HX2026SC001',
                    'lc_no': 'BOCSZ/2026/LC00856',
                    'trade_term': 'CIF Los Angeles, Incoterms 2020',
                    'payment_term': 'L/C at sight',
                    'from_port': 'Shenzhen (Yantian), China',
                    'to_port': 'Los Angeles, USA',
                    'vessel': 'COSCO SHIPPING GALAXY V.025E',
                    'container_no': 'TGHU4729510',
                    'items': [
                        {
                            'marks': 'HX2026SC001\nLOS ANGELES\nC/NO.1-100\nG.W.:14.5KGS',
                            'description': 'Bluetooth Earphone Model HX-BT5Pro\nBT5.3, ANC, 40hrs battery, IPX5\nHS Code: 85183000',
                            'quantity': '5000',
                            'unit': 'PCS',
                            'unit_price': '12.50',
                            'amount': '62500.00',
                        }
                    ],
                    'total_amount': 'USD 62,500.00',
                    'packing': '100 cartons, 2 pallets',
                    'gross_weight': '1,450.00 KGS',
                    'net_weight': '1,200.00 KGS',
                    'total_packages': '100 CARTONS',
                }, ensure_ascii=False, indent=2),
            },

            # 2. 装箱单
            {
                'template_code': 'packing_list',
                'status': 'approved',
                'data': json.dumps({
                    'packing_list_no': 'HX-PL-2026-00856',
                    'invoice_no': 'HX-INV-2026-00856',
                    'packing_date': invoice_date,
                    'shipper': 'Shenzhen Huaxin Electronics Tech Co., Ltd.',
                    'consignee': 'Pacific Digital Trading LLC',
                    'destination': 'Los Angeles, USA',
                    'shipping_marks': 'HX2026SC001 / LOS ANGELES / C/NO.1-100',
                    'items': [
                        {
                            'carton_no': 'C/NO. 1-50',
                            'description': 'HX-BT5Pro Bluetooth Earphone (Black)',
                            'qty_per_carton': '50 PCS',
                            'total_qty': '2500 PCS',
                            'net_weight': '600.00 KGS',
                            'gross_weight': '725.00 KGS',
                            'measurement': '45×35×30 CM × 50',
                        },
                        {
                            'carton_no': 'C/NO. 51-100',
                            'description': 'HX-BT5Pro Bluetooth Earphone (White)',
                            'qty_per_carton': '50 PCS',
                            'total_qty': '2500 PCS',
                            'net_weight': '600.00 KGS',
                            'gross_weight': '725.00 KGS',
                            'measurement': '45×35×30 CM × 50',
                        },
                    ],
                    'total_cartons': '100',
                    'total_net_weight': '1,200.00 KGS',
                    'total_gross_weight': '1,450.00 KGS',
                    'total_measurement': '7.875 CBM',
                    'package_type': 'Carton + Pallet',
                }, ensure_ascii=False, indent=2),
            },

            # 3. 海运提单
            {
                'template_code': 'bill_of_lading',
                'status': 'approved',
                'data': json.dumps({
                    'bl_no': 'COSU6289510340',
                    'booking_no': 'COSCO26MA22HK003',
                    'shipper': 'Shenzhen Huaxin Electronics Tech Co., Ltd.\nHuaxin Building, 88 Keji Yuan South Rd\nNanshan District, Shenzhen 518057, China',
                    'consignee': 'TO ORDER OF SHIPPER',
                    'notify_party': 'Pacific Digital Trading LLC\n1200 Wilshire Blvd, Suite 500\nLos Angeles, CA 90017, USA\nAttn: Mr. John Smith\nTel: +1-213-555-0188',
                    'vessel': 'COSCO SHIPPING GALAXY',
                    'voyage': '025E',
                    'port_of_loading': 'Shenzhen (Yantian), China',
                    'port_of_discharge': 'Los Angeles, USA',
                    'etd': (now - timedelta(days=5)).strftime('%Y-%m-%d'),
                    'eta': (now + timedelta(days=13)).strftime('%Y-%m-%d'),
                    'container_no': 'TGHU4729510',
                    'container_type': "1×40'HC",
                    'seal_no': 'CS260522A',
                    'description': '5000 PCS Bluetooth Earphone\nHS Code: 85183000\nGW: 1,450 KGS\n100 CARTONS ON 2 PALLETS',
                    'freight': 'FREIGHT PREPAID',
                    'bl_issued_at': (now - timedelta(days=4)).strftime('%Y-%m-%d'),
                    'bl_originals': '3/3 ORIGINAL',
                    'on_board_date': (now - timedelta(days=4)).strftime('%Y-%m-%d'),
                }, ensure_ascii=False, indent=2),
            },

            # 4. 汇票
            {
                'template_code': 'bill_of_exchange',
                'status': 'approved',
                'data': json.dumps({
                    'draft_no': 'HX-DRAFT-2026-00856',
                    'draft_date': (now - timedelta(days=2)).strftime('%Y-%m-%d'),
                    'draft_amount': 'USD 62,500.00',
                    'amount_in_words': 'US DOLLARS SIXTY-TWO THOUSAND FIVE HUNDRED ONLY',
                    'tenor': 'AT SIGHT',
                    'drawer': 'Shenzhen Huaxin Electronics Tech Co., Ltd.',
                    'drawee': 'Wells Fargo Bank, N.A., Los Angeles Branch',
                    'payee': 'Bank of China, Shenzhen Branch',
                    'lc_no': 'BOCSZ/2026/LC00856',
                    'drawn_under': 'Irrevocable Letter of Credit No. BOCSZ/2026/LC00856\nDated 2026-04-30\nIssued by Wells Fargo Bank, N.A.',
                }, ensure_ascii=False, indent=2),
            },

            # 5. 信用证（单证副本）
            {
                'template_code': 'letter_of_credit',
                'status': 'approved',
                'data': json.dumps({
                    'lc_no': 'BOCSZ/2026/LC00856',
                    'lc_issue_date': '2026-04-30',
                    'lc_type': 'IRREVOCABLE, UNCONFIRMED',
                    'issuing_bank': 'Wells Fargo Bank, N.A., Los Angeles Branch',
                    'advising_bank': 'Bank of China, Shenzhen Branch',
                    'applicant': 'Pacific Digital Trading LLC\n1200 Wilshire Blvd, Suite 500\nLos Angeles, CA 90017, USA',
                    'beneficiary': 'Shenzhen Huaxin Electronics Tech Co., Ltd.\nHuaxin Building, 88 Keji Yuan South Rd\nNanshan District, Shenzhen 518057, China',
                    'amount': 'USD 62,500.00 (US DOLLARS SIXTY-TWO THOUSAND FIVE HUNDRED ONLY)',
                    'expiry_date': (now + timedelta(days=15)).strftime('%Y-%m-%d'),
                    'expiry_place': 'China',
                    'latest_shipment': (now - timedelta(days=3)).strftime('%Y-%m-%d'),
                    'port_of_loading': 'Shenzhen, China',
                    'port_of_discharge': 'Los Angeles, USA',
                    'partial_shipment': 'NOT ALLOWED',
                    'transshipment': 'NOT ALLOWED',
                    'trade_term': 'CIF Los Angeles, Incoterms 2020',
                    'documents_required': [
                        'Signed Commercial Invoice in 3 folds',
                        'Full set 3/3 clean on board B/L consigned to order of shipper, blank endorsed',
                        'Packing List in 3 folds',
                        'Insurance Policy/Certificate for 110% invoice value covering All Risks and War Risk',
                        'Certificate of Origin FORM A in 1 original + 1 copy',
                        'Inspection Certificate of Quality/Quantity issued by CCIC',
                        'Beneficiary Certificate that shipping advice has been sent within 24 hours after shipment',
                    ],
                    'period_for_presentation': 'Within 15 days after the date of shipment',
                }, ensure_ascii=False, indent=2),
            },

            # 6. 保险单
            {
                'template_code': 'insurance_policy',
                'status': 'approved',
                'data': json.dumps({
                    'policy_no': 'PICC2026SH05220001',
                    'insured': 'Shenzhen Huaxin Electronics Tech Co., Ltd.',
                    'insurer': 'PICC Property and Casualty Co., Ltd.',
                    'insured_amount': 'USD 68,750.00',
                    'insured_amount_in_words': 'US DOLLARS SIXTY-EIGHT THOUSAND SEVEN HUNDRED AND FIFTY ONLY',
                    'coverage': 'ALL RISKS AND WAR RISK',
                    'coverage_clause': 'As per Ocean Marine Cargo Clauses (1/1/1981) of CIC',
                    'cargo_description': '5000 PCS Bluetooth Earphone (HX-BT5Pro)',
                    'voyage_from': 'Shenzhen (Yantian), China',
                    'voyage_to': 'Los Angeles, USA',
                    'vessel': 'COSCO SHIPPING GALAXY V.025E',
                    'bl_no': 'COSU6289510340',
                    'container_no': 'TGHU4729510',
                    'premium': 'As arranged',
                    'issue_date': (now - timedelta(days=5)).strftime('%Y-%m-%d'),
                    'claim_settling_agent': 'PICC America LLC, New York',
                    'special_conditions': 'Covering warehouse to warehouse, including loading and unloading',
                }, ensure_ascii=False, indent=2),
            },

            # 7. 产地证
            {
                'template_code': 'certificate_of_origin',
                'status': 'approved',
                'data': json.dumps({
                    'certificate_no': 'GSP/CCPIT2026/00856',
                    'certificate_type': 'FORM A (Generalized System of Preferences)',
                    'goods_consigned_from': 'Shenzhen Huaxin Electronics Tech Co., Ltd.\nHuaxin Building, 88 Keji Yuan South Rd\nNanshan District, Shenzhen 518057, China',
                    'goods_consigned_to': 'Pacific Digital Trading LLC\n1200 Wilshire Blvd, Suite 500\nLos Angeles, CA 90017, USA',
                    'means_of_transport': 'BY VESSEL: COSCO SHIPPING GALAXY V.025E',
                    'port_of_loading': 'Shenzhen (Yantian), China',
                    'port_of_discharge': 'Los Angeles, USA',
                    'item_details': [
                        {
                            'marks': 'HX2026SC001\nLOS ANGELES',
                            'description': 'Bluetooth Earphone Model HX-BT5Pro',
                            'quantity': '5,000 PCS',
                            'origin_criterion': 'P (Wholly produced in China)',
                        }
                    ],
                    'issue_date': (now - timedelta(days=6)).strftime('%Y-%m-%d'),
                    'issuing_authority': 'China Council for the Promotion of International Trade (CCPIT)',
                    'certification': 'It is hereby certified that the goods described above originate in China',
                }, ensure_ascii=False, indent=2),
            },

            # 8. 报检单
            {
                'template_code': 'inspection_application',
                'status': 'approved',
                'data': json.dumps({
                    'application_no': 'IA20260518001',
                    'applicant': 'Shenzhen Huaxin Electronics Tech Co., Ltd.',
                    'inspector': 'Shenzhen Entry-Exit Inspection and Quarantine Bureau',
                    'product_name': '蓝牙耳机 HX-BT5Pro',
                    'product_spec': '蓝牙5.3, ANC主动降噪, 40小时续航, IPX5防水',
                    'hs_code': '85183000',
                    'quantity': '5,000 PCS',
                    'goods_value': 'USD 62,500.00',
                    'inspection_type': '法定检验',
                    'inspection_standard': 'GB/T 14217-2011',
                    'inspection_items': '外观检查、功能测试、电气安全、电磁兼容、防水等级',
                    'result': '合格',
                    'certificate_no': 'CIQ20260520001',
                    'application_date': (now - timedelta(days=9)).strftime('%Y-%m-%d'),
                    'inspection_date': (now - timedelta(days=8)).strftime('%Y-%m-%d'),
                    'pass_date': (now - timedelta(days=7)).strftime('%Y-%m-%d'),
                }, ensure_ascii=False, indent=2),
            },

            # 9. 检验证书
            {
                'template_code': 'inspection_certificate',
                'status': 'approved',
                'data': json.dumps({
                    'certificate_no': 'CIQ20260520001',
                    'applicant': 'Shenzhen Huaxin Electronics Tech Co., Ltd.',
                    'product_name': 'Bluetooth Earphone Model HX-BT5Pro',
                    'hs_code': '85183000',
                    'quantity': '5,000 PCS',
                    'contract_no': 'HX2026SC001',
                    'lc_no': 'BOCSZ/2026/LC00856',
                    'inspection_result': 'QUALITY AND QUANTITY FOUND TO BE IN CONFORMITY WITH THE CONTRACT STIPULATIONS',
                    'inspection_standard': 'GB/T 14217-2011',
                    'inspection_date': (now - timedelta(days=7)).strftime('%Y-%m-%d'),
                    'issue_date': (now - timedelta(days=6)).strftime('%Y-%m-%d'),
                    'inspector': 'Shenzhen Entry-Exit Inspection and Quarantine Bureau',
                    'remarks': 'Sample rate: AQL 1.0 Level II, All items passed',
                }, ensure_ascii=False, indent=2),
            },

            # 10. 出口报关单
            {
                'template_code': 'export_declaration',
                'status': 'approved',
                'data': json.dumps({
                    'declaration_no': 'CD20260522001',
                    'declaration_type': '出口报关',
                    'declarant': '深圳华信电子科技有限公司',
                    'customs_office': '深圳海关（大鹏海关）',
                    'trade_mode': '一般贸易 (0110)',
                    'transport_mode': '海运 (2)',
                    'hs_code': '85183000.90',
                    'goods_name': '蓝牙耳机 Bluetooth Earphone (Headphone)',
                    'specification': 'HX-BT5Pro',
                    'quantity': '5,000',
                    'unit': '台',
                    'unit_price': '12.50',
                    'total_value': 'USD 62,500.00',
                    'currency': 'USD',
                    'country_of_destination': '美国 (US)',
                    'port_of_loading': '深圳盐田 (CNSZX)',
                    'port_of_discharge': '洛杉矶 (USLAX)',
                    'container_no': 'TGHU4729510',
                    'gross_weight': '1,450 KGS',
                    'net_weight': '1,200 KGS',
                    'package_count': '100 纸箱',
                    'contract_no': 'HX2026SC001',
                    'supervision_code': '无',
                    'rebate_rate': '13%',
                    'declaration_date': (now - timedelta(days=5)).strftime('%Y-%m-%d'),
                    'clearance_date': (now - timedelta(days=5)).strftime('%Y-%m-%d'),
                }, ensure_ascii=False, indent=2),
            },

            # 11. 装船通知
            {
                'template_code': 'shipping_advice',
                'status': 'approved',
                'data': json.dumps({
                    'advice_no': 'HX-SA-2026-00856',
                    'advice_date': (now - timedelta(days=4)).strftime('%Y-%m-%d'),
                    'from': 'Shenzhen Huaxin Electronics Tech Co., Ltd.',
                    'to': 'Pacific Digital Trading LLC',
                    'contract_no': 'HX2026SC001',
                    'lc_no': 'BOCSZ/2026/LC00856',
                    'commodity': '5000 PCS Bluetooth Earphone (HX-BT5Pro)',
                    'vessel': 'COSCO SHIPPING GALAXY V.025E',
                    'bl_no': 'COSU6289510340',
                    'container_no': 'TGHU4729510',
                    'etd': (now - timedelta(days=5)).strftime('%Y-%m-%d'),
                    'eta': (now + timedelta(days=13)).strftime('%Y-%m-%d'),
                    'port_of_loading': 'Shenzhen (Yantian), China',
                    'port_of_discharge': 'Los Angeles, USA',
                    'shipping_marks': 'HX2026SC001 / LOS ANGELES / C/NO.1-100',
                    'message': (
                        'We hereby inform you that the above mentioned goods have been shipped '
                        'on board the above vessel on the date shown. Please arrange for import '
                        'clearance and cargo reception accordingly.'
                    ),
                }, ensure_ascii=False, indent=2),
            },

            # 12. 受益人证明
            {
                'template_code': 'beneficiary_certificate',
                'status': 'approved',
                'data': json.dumps({
                    'certificate_no': 'HX-BC-2026-00856',
                    'certificate_date': (now - timedelta(days=4)).strftime('%Y-%m-%d'),
                    'beneficiary': 'Shenzhen Huaxin Electronics Tech Co., Ltd.',
                    'lc_no': 'BOCSZ/2026/LC00856',
                    'declaration': (
                        'WE HEREBY CERTIFY THAT:\n'
                        '1. SHIPPING ADVICE HAS BEEN SENT TO THE APPLICANT BY FAX/EMAIL '
                        'WITHIN 24 HOURS AFTER SHIPMENT.\n'
                        '2. ONE SET OF NON-NEGOTIABLE DOCUMENTS HAS BEEN SENT TO THE APPLICANT '
                        'BY COURIER SERVICE.\n'
                        '3. ALL GOODS ARE IN CONFORMITY WITH THE CONTRACT NO. HX2026SC001.'
                    ),
                    'contract_no': 'HX2026SC001',
                }, ensure_ascii=False, indent=2),
            },
        ]

        for doc_data in documents_data:
            template = DocumentTemplate.objects.filter(
                code=doc_data['template_code']
            ).first()
            if not template:
                self.stdout.write(self.style.WARNING(
                    f"  [SKIP] 模板不存在: {doc_data['template_code']}"))
                continue

            doc, created = Document.objects.get_or_create(
                template=template,
                transaction_id=transaction.id,
                defaults={
                    'status': doc_data['status'],
                    'data': doc_data['data'],
                    'created_by': sample_user,
                }
            )
            if not created and not doc.created_by:
                doc.created_by = sample_user
                doc.save(update_fields=['created_by'])
            tag = 'CREATE' if created else 'SKIP'
            self.stdout.write(f'  [{tag}] {template.name}')
