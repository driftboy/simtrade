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

        # ── 场景 3：CIF + L/C 纺织品出口欧盟 ──────────────────────
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write('场景 3：CIF + L/C（棉质女式针织外套出口德国）')
        self.stdout.write('=' * 60)
        result3 = self._create_scenario_textile_eu(now, companies, huaxin_user)

        # ── 场景 4：机械设备出口东南亚 ──────────────────────────────
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write('场景 4：机械设备出口东南亚（CIF + L/C）')
        self.stdout.write('=' * 60)
        result4 = self._create_scenario_machinery_sea(now, companies, huaxin_user)

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
        self.stdout.write('')
        self.stdout.write('  场景 3: CIF + L/C（棉质女式针织外套出口德国）')
        self.stdout.write(f'  交易: #{result3["transaction"].id}')
        self.stdout.write(f'  合同: {result3["contract"].contract_no}')
        self.stdout.write(f'  信用证: {result3["lc"].lc_no}')
        self.stdout.write(f'  采购订单: {result3["po"].order_no}')
        self.stdout.write(f'  货运: {result3["shipment"].shipment_no}')
        self.stdout.write(f'  保险: {result3["insurance"].policy_no}')
        self.stdout.write(f'  报检: {result3["inspection"].application_no}')
        self.stdout.write(f'  报关: {result3["customs"].declaration_no}')
        self.stdout.write(f'  外汇结算: {result3["forex"].settlement_no}')
        self.stdout.write(f'  退税: {result3["tax_refund"].application_no}')
        self.stdout.write('')
        self.stdout.write('  场景 4: CIF + L/C（数控车床出口泰国）')
        self.stdout.write(f'  交易: #{result4["transaction"].id}')
        self.stdout.write(f'  合同: {result4["contract"].contract_no}')
        self.stdout.write(f'  信用证: {result4["lc"].lc_no}')
        self.stdout.write(f'  采购订单: {result4["po"].order_no}')
        self.stdout.write(f'  货运: {result4["shipment"].shipment_no}')
        self.stdout.write(f'  保险: {result4["insurance"].policy_no}')
        self.stdout.write(f'  报检: {result4["inspection"].application_no}')
        self.stdout.write(f'  报关: {result4["customs"].declaration_no}')
        self.stdout.write(f'  外汇结算: {result4["forex"].settlement_no}')
        self.stdout.write(f'  退税: {result4["tax_refund"].application_no}')
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
    # 场景：CIF + L/C 纺织品出口德国（棉质女式针织外套）
    # ──────────────────────────────────────────────────────────────

    def _create_scenario_textile_eu(self, now, companies, sample_user):
        """CIF + L/C 场景：棉质女式针织外套出口德国（EUR 结算，FORM A 欧盟普惠制）"""

        # ── 新公司 ──────────────────────────────────────────
        self.stdout.write('\n[新增公司] 创建场景 3 公司...')

        exp03, created = self._create_company(
            'EXP03', '杭州丝绸之纺织品有限公司',
            'Hangzhou Silk Road Textiles Co., Ltd.',
            'CN', 'textiles',
            '杭州市萧山区市心北路188号丝绸之大厦',
            '+86-571-82801234', 'export@silkroad-textile.com')
        self.stdout.write(f'  [{"CREATE" if created else "SKIP"}] {exp03.name}')

        imp03, created = self._create_company(
            'IMP03', 'Fashion Europe GmbH',
            'Fashion Europe GmbH',
            'DE', 'trading',
            'Mönckebergstraße 7, 20095 Hamburg, Germany',
            '+49-40-3001234', 'purchasing@fashion-europe.de')
        self.stdout.write(f'  [{"CREATE" if created else "SKIP"}] {imp03.name}')

        # ── 商品 ──────────────────────────────────────────
        product = self._ensure_product(
            'T001', '棉质女式针织外套', "Women's Cotton Knitted Coat",
            'textiles', 'PCS', '6104',
            '60%棉 40%聚酯纤维, 针织, 女式, 外套, 多色可选')
        self.stdout.write(f'  [OK] 商品 {product.name}')

        # ── 交易 ──────────────────────────────────────────
        self.stdout.write('\n[2/10] 创建交易记录 (Textile EU CIF+L/C)...')

        transaction, created = Transaction.objects.get_or_create(
            pk=9003,
            defaults={
                'buyer': imp03,
                'seller': exp03,
                'product': product,
                'status': 'completed',
                'quantity': 10000,
                'unit_price': Decimal('8.50'),
                'currency': 'EUR',
                'trade_term': 'CIF',
                'port_of_loading': 'Shanghai',
                'port_of_discharge': 'Hamburg, Germany',
                'notes': '样本交易：棉质女式针织外套出口德国，CIF Hamburg，L/C at sight',
            }
        )
        tag = 'CREATE' if created else 'SKIP'
        self.stdout.write(f'  [{tag}] 交易 #{transaction.id}')

        # ── 合同 ──────────────────────────────────────────
        self.stdout.write('\n[3/10] 创建外销合同 (Textile EU CIF+L/C)...')

        delivery_date = (now - timedelta(days=3)).date()

        contract, created = Contract.objects.get_or_create(
            contract_no='SR2026SC001',
            defaults={
                'transaction': transaction,
                'status': 'effective',
                'trade_term': 'CIF',
                'payment_term': 'L/C at sight',
                'delivery_time': delivery_date,
                'port_of_loading': 'Shanghai',
                'port_of_discharge': 'Hamburg, Germany',
                'product_name': "棉质女式针织外套 Women's Cotton Knitted Coat",
                'product_spec': '60%棉 40%聚酯纤维, 针织, 女式, S/M/L/XL, 多色可选',
                'quantity': 10000,
                'unit': 'PCS',
                'unit_price': Decimal('8.50'),
                'total_amount': Decimal('85000.00'),
                'currency': 'EUR',
                'packing': '每件独立包装，50件/外箱，共200外箱',
                'shipping_marks': (
                    'SR2026SC001\n'
                    'HAMBURG\n'
                    'C/NO.: 1-200\n'
                    'G.W.: 18.0 KGS\n'
                    'N.W.: 15.0 KGS\n'
                    'MEAS: 60×45×50 CM'
                ),
                'remarks': (
                    '1. 装运期：不迟于2026年6月15日\n'
                    '2. 允许分批装运：不允许\n'
                    '3. 允许转船：不允许\n'
                    '4. 品质以中国商品检验局检验证书为准\n'
                    '5. 按 CIF Hamburg 成交，卖方负责投保一切险\n'
                    '6. 产地证要求 FORM A 欧盟普惠制'
                ),
                'seller_signed_at': now - timedelta(days=30),
                'buyer_signed_at': now - timedelta(days=29),
                'effective_at': now - timedelta(days=29),
            }
        )
        tag = 'CREATE' if created else 'SKIP'
        self.stdout.write(f'  [{tag}] 合同 {contract.contract_no}')

        # ── 信用证 ──────────────────────────────────────────
        self.stdout.write('\n[4/10] 创建信用证 (Textile EU)...')

        lc_issue_date = (now - timedelta(days=28)).date()
        lc_expiry_date = (now + timedelta(days=15)).date()
        latest_shipment = (now - timedelta(days=2)).date()

        lc, created = LetterOfCredit.objects.get_or_create(
            lc_no='COMMB/2026/LC00234',
            defaults={
                'contract': contract,
                'transaction': transaction,
                'status': 'negotiated',
                'issuing_bank': 'Commerzbank AG, Hamburg',
                'advising_bank': '中国银行杭州市分行',
                'applicant': imp03,
                'beneficiary': exp03,
                'amount': Decimal('85000.00'),
                'currency': 'EUR',
                'issue_date': lc_issue_date,
                'expiry_date': lc_expiry_date,
                'latest_shipment_date': latest_shipment,
                'port_of_loading': 'Shanghai, China',
                'port_of_discharge': 'Hamburg, Germany',
                'documents_required': [
                    'Signed Commercial Invoice in triplicate, currency EUR',
                    'Full set of 3/3 clean on board ocean Bills of Lading',
                    'Packing List in triplicate',
                    'Insurance Policy/Certificate for 110% of invoice value covering All Risks',
                    'Certificate of Origin FORM A (EU GSP)',
                    'Inspection Certificate issued by CCIC',
                    'Beneficiary Certificate certifying that shipping advice has been sent',
                ],
                'issued_at': now - timedelta(days=28),
                'advised_at': now - timedelta(days=27),
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

        # ── 采购订单 ──────────────────────────────────────
        self.stdout.write('\n[5/10] 创建采购订单 (Textile EU)...')

        po_delivery = (now - timedelta(days=8)).date()

        po, created = PurchaseOrder.objects.get_or_create(
            order_no='PO20260603003',
            defaults={
                'transaction': transaction,
                'buyer': exp03,
                'seller': companies['factory'],
                'product_name': '棉质女式针织外套',
                'product_code': 'T001',
                'quantity': Decimal('10000'),
                'unit': 'PCS',
                'unit_price': Decimal('45.00'),
                'currency': 'CNY',
                'total_amount': Decimal('450000.00'),
                'delivery_date': po_delivery,
                'delivery_address': '杭州市萧山区市心北路188号丝绸之大厦仓库',
                'status': 'completed',
                'notes': '棉质女式针织外套，60%棉40%聚酯纤维，尺码S-XL，4色各2500件',
                'shipped_at': now - timedelta(days=6),
                'invoiced_at': now - timedelta(days=5),
                'completed_at': now - timedelta(days=5),
            }
        )
        tag = 'CREATE' if created else 'SKIP'
        self.stdout.write(f'  [{tag}] 采购订单 {po.order_no}')

        # ── 货运 ──────────────────────────────────────────
        self.stdout.write('\n[6/10] 创建货运订单 (Textile EU)...')

        etd = (now - timedelta(days=3)).date()
        eta = etd + timedelta(days=28)

        shipment, created = Shipment.objects.get_or_create(
            shipment_no='SH20260605001',
            defaults={
                'contract': contract,
                'shipper': exp03,
                'carrier': companies['shipping'],
                'booking_no': 'MSC26MA05SH002',
                'bl_no': 'MSCU8234569200',
                'vessel_name': 'MSC GÜLSÜN V.012W',
                'port_of_loading': 'Shanghai (Waigaoqiao), China',
                'port_of_discharge': 'Hamburg, Germany',
                'etd': etd,
                'eta': eta,
                'container_no': 'MSKU7234891 / 40GP',
                'freight_amount': Decimal('4500.00'),
                'freight_currency': 'USD',
                'status': 'shipped',
                'notes': "CY to CY, 1x40'GP Container",
                'booked_at': now - timedelta(days=10),
                'loaded_at': now - timedelta(days=3),
                'shipped_at': now - timedelta(days=2),
            }
        )
        tag = 'CREATE' if created else 'SKIP'
        self.stdout.write(f'  [{tag}] 货运订单 {shipment.shipment_no}')

        # ── 保险 ──────────────────────────────────────────
        self.stdout.write('\n[7/10] 创建保险单 (Textile EU)...')

        insurance, created = InsurancePolicy.objects.get_or_create(
            policy_no='PICC2026SH06050001',
            defaults={
                'contract': contract,
                'shipment': shipment,
                'insured': exp03,
                'insurer': companies['insurance'],
                'cargo_description': (
                    '10000 PCS Cotton Knitted Coat as per Contract No. SR2026SC001 '
                    'Shipped per MSC GÜLSÜN V.012W '
                    'from Shanghai to Hamburg'
                ),
                'insured_amount': Decimal('93500.00'),  # EUR 85000 × 110%
                'premium': Decimal('561.00'),  # ~0.6%
                'premium_currency': 'CNY',
                'coverage_type': 'all_risk',
                'status': 'issued',
                'notes': 'Covering All Risks and War Risk as per CIC 1/1/1981',
                'underwritten_at': now - timedelta(days=4),
                'issued_at': now - timedelta(days=3),
            }
        )
        tag = 'CREATE' if created else 'SKIP'
        self.stdout.write(f'  [{tag}] 保险单 {insurance.policy_no}')

        # ── 报检 ──────────────────────────────────────────
        self.stdout.write('\n[8/10] 创建报检记录 (Textile EU)...')

        inspection, created = InspectionApplication.objects.get_or_create(
            application_no='IA20260601003',
            defaults={
                'shipment': shipment,
                'applicant': exp03,
                'inspector': companies['inspection'],
                'product_name': '棉质女式针织外套',
                'product_spec': '60%棉 40%聚酯纤维, 针织, 女式外套',
                'quantity': Decimal('10000'),
                'goods_value': Decimal('85000.00'),
                'inspection_type': 'legal',
                'fee': Decimal('1200.00'),
                'fee_currency': 'CNY',
                'certificate_no': 'CIQ20260603003',
                'origin_certificate_no': 'GSP/CCPIT2026/002',
                'status': 'certified',
                'notes': '依据 GB 18401-2010 国家纺织产品基本安全技术规范，外观/色牢度/甲醛/pH值检验合格',
                'inspecting_at': now - timedelta(days=5),
                'passed_at': now - timedelta(days=4),
                'certified_at': now - timedelta(days=3),
            }
        )
        tag = 'CREATE' if created else 'SKIP'
        self.stdout.write(f'  [{tag}] 报检记录 {inspection.application_no}')

        # ── 报关 ──────────────────────────────────────────
        self.stdout.write('\n[9/10] 创建报关单 (Textile EU)...')

        customs, created = CustomsDeclaration.objects.get_or_create(
            declaration_no='CD20260605003',
            defaults={
                'shipment': shipment,
                'declarant': exp03,
                'customs_office': companies['customs'],
                'hs_code': '6104',
                'goods_name': "Women's Cotton Knitted Coat",
                'quantity': Decimal('10000'),
                'unit_value': Decimal('8.50'),
                'total_value': Decimal('85000.00'),
                'currency': 'EUR',
                'duty_rate': Decimal('0'),
                'duty_amount': Decimal('0'),
                'vat_rate': Decimal('0.13'),
                'vat_amount': Decimal('0'),
                'status': 'cleared',
                'notes': '纺织品出口，退税率9%',
                'reviewed_at': now - timedelta(days=3),
                'assessed_at': now - timedelta(days=3),
                'cleared_at': now - timedelta(days=3),
            }
        )
        tag = 'CREATE' if created else 'SKIP'
        self.stdout.write(f'  [{tag}] 报关单 {customs.declaration_no}')

        # ── 外汇结算（单笔，EUR）──────────────────────────
        self.stdout.write('\n[10/10] 创建外汇结算与退税 (Textile EU)...')

        forex, created = ForexSettlement.objects.get_or_create(
            settlement_no='FX20260607003',
            defaults={
                'customs_declaration': customs,
                'applicant': exp03,
                'forex_bureau': companies['forex'],
                'foreign_currency': 'EUR',
                'foreign_amount': Decimal('85000.00'),
                'reference_rate': Decimal('7.8500'),
                'reference_cny_amount': Decimal('667250.00'),
                'settlement_rate': Decimal('7.8420'),
                'settlement_cny_amount': Decimal('666570.00'),
                'status': 'settled',
                'notes': 'EUR 收汇结汇，收汇金额与报关金额一致',
                'verified_at': now - timedelta(days=1),
                'settled_at': now,
            }
        )
        tag = 'CREATE' if created else 'SKIP'
        self.stdout.write(f'  [{tag}] 外汇结算 {forex.settlement_no}')

        # ── 退税（纺织品 9%）──────────────────────────────
        total_value_cny = Decimal('666570.00')  # EUR 等值 CNY

        tax_refund, created = TaxRefundApplication.objects.get_or_create(
            application_no='TR20260608003',
            defaults={
                'customs_declaration': customs,
                'applicant': exp03,
                'tax_bureau': companies['tax'],
                'hs_code': '6104',
                'total_value': total_value_cny,
                'refund_rate': Decimal('0.09'),
                'refund_amount': Decimal('53089.65'),  # 666570 × 9% / 1.13
                'refund_currency': 'CNY',
                'status': 'approved',
                'notes': '纺织品退税率9%，依据出口报关单及增值税发票核准',
                'reviewing_at': now - timedelta(days=1),
                'approved_at': now,
            }
        )
        tag = 'CREATE' if created else 'SKIP'
        self.stdout.write(f'  [{tag}] 退税申请 {tax_refund.application_no}')

        # ── 单证 ──────────────────────────────────────────
        self.stdout.write('\n[单证] 生成场景 3 单证记录...')

        self._create_textile_eu_documents(
            now, contract, transaction, lc, shipment,
            insurance, inspection, customs, companies,
            exp03, imp03, sample_user)

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

    def _create_textile_eu_documents(self, now, contract, transaction, lc,
                                      shipment, insurance, inspection, customs,
                                      companies, exp03, imp03, sample_user):
        """创建 CIF + L/C 纺织品出口欧盟场景的单证记录（11 种）"""

        invoice_date = (now - timedelta(days=3)).strftime('%Y-%m-%d')
        bl_date = (now - timedelta(days=2)).strftime('%Y-%m-%d')

        documents_data = [
            # 1. 商业发票
            {
                'template_code': 'commercial_invoice',
                'status': 'approved',
                'data': json.dumps({
                    'invoice_no': 'SR-INV-2026-001',
                    'invoice_date': invoice_date,
                    'seller_name': 'Hangzhou Silk Road Textiles Co., Ltd.',
                    'seller_address': 'Silk Road Building, 188 Shixin North Rd, Xiaoshan, Hangzhou, China',
                    'buyer_name': 'Fashion Europe GmbH',
                    'buyer_address': 'Mönckebergstraße 7, 20095 Hamburg, Germany',
                    'contract_no': 'SR2026SC001',
                    'lc_no': 'COMMB/2026/LC00234',
                    'trade_term': 'CIF Hamburg, Incoterms 2020',
                    'payment_term': 'L/C at sight',
                    'from_port': 'Shanghai (Waigaoqiao), China',
                    'to_port': 'Hamburg, Germany',
                    'vessel': 'MSC GÜLSÜN V.012W',
                    'container_no': 'MSKU7234891',
                    'items': [
                        {
                            'marks': 'SR2026SC001\nHAMBURG\nC/NO.1-200\nG.W.:18.0KGS',
                            'description': "Women's Cotton Knitted Coat\n60% Cotton 40% Polyester, Knitted, Sizes S/M/L/XL, Multi-color\nHS Code: 6104",
                            'quantity': '10000',
                            'unit': 'PCS',
                            'unit_price': '8.50',
                            'amount': '85000.00',
                        }
                    ],
                    'total_amount': 'EUR 85,000.00',
                    'packing': '200 cartons',
                    'gross_weight': '3,600.00 KGS',
                    'net_weight': '3,000.00 KGS',
                    'total_packages': '200 CARTONS',
                }, ensure_ascii=False, indent=2),
            },

            # 2. 装箱单
            {
                'template_code': 'packing_list',
                'status': 'approved',
                'data': json.dumps({
                    'packing_list_no': 'SR-PL-2026-001',
                    'invoice_no': 'SR-INV-2026-001',
                    'packing_date': invoice_date,
                    'shipper': 'Hangzhou Silk Road Textiles Co., Ltd.',
                    'consignee': 'Fashion Europe GmbH',
                    'destination': 'Hamburg, Germany',
                    'shipping_marks': 'SR2026SC001 / HAMBURG / C/NO.1-200',
                    'items': [
                        {
                            'carton_no': 'C/NO. 1-50',
                            'description': "Women's Cotton Knitted Coat (Size S, Multi-color)",
                            'qty_per_carton': '50 PCS',
                            'total_qty': '2500 PCS',
                            'net_weight': '750.00 KGS',
                            'gross_weight': '900.00 KGS',
                            'measurement': '60×45×50 CM × 50',
                        },
                        {
                            'carton_no': 'C/NO. 51-100',
                            'description': "Women's Cotton Knitted Coat (Size M, Multi-color)",
                            'qty_per_carton': '50 PCS',
                            'total_qty': '2500 PCS',
                            'net_weight': '750.00 KGS',
                            'gross_weight': '900.00 KGS',
                            'measurement': '60×45×50 CM × 50',
                        },
                        {
                            'carton_no': 'C/NO. 101-150',
                            'description': "Women's Cotton Knitted Coat (Size L, Multi-color)",
                            'qty_per_carton': '50 PCS',
                            'total_qty': '2500 PCS',
                            'net_weight': '750.00 KGS',
                            'gross_weight': '900.00 KGS',
                            'measurement': '60×45×50 CM × 50',
                        },
                        {
                            'carton_no': 'C/NO. 151-200',
                            'description': "Women's Cotton Knitted Coat (Size XL, Multi-color)",
                            'qty_per_carton': '50 PCS',
                            'total_qty': '2500 PCS',
                            'net_weight': '750.00 KGS',
                            'gross_weight': '900.00 KGS',
                            'measurement': '60×45×50 CM × 50',
                        },
                    ],
                    'total_cartons': '200',
                    'total_net_weight': '3,000.00 KGS',
                    'total_gross_weight': '3,600.00 KGS',
                    'total_measurement': '27.0 CBM',
                    'package_type': 'Carton',
                }, ensure_ascii=False, indent=2),
            },

            # 3. 海运提单
            {
                'template_code': 'bill_of_lading',
                'status': 'approved',
                'data': json.dumps({
                    'bl_no': 'MSCU8234569200',
                    'booking_no': 'MSC26MA05SH002',
                    'shipper': 'Hangzhou Silk Road Textiles Co., Ltd.\nSilk Road Building, 188 Shixin North Rd\nXiaoshan District, Hangzhou 311200, China',
                    'consignee': 'TO ORDER OF SHIPPER',
                    'notify_party': 'Fashion Europe GmbH\nMönckebergstraße 7\n20095 Hamburg, Germany\nAttn: Ms. Anna Müller\nTel: +49-40-3001234',
                    'vessel': 'MSC GÜLSÜN',
                    'voyage': '012W',
                    'port_of_loading': 'Shanghai (Waigaoqiao), China',
                    'port_of_discharge': 'Hamburg, Germany',
                    'etd': (now - timedelta(days=3)).strftime('%Y-%m-%d'),
                    'eta': (now + timedelta(days=25)).strftime('%Y-%m-%d'),
                    'container_no': 'MSKU7234891',
                    'container_type': "1×40'GP",
                    'seal_no': 'MS260605C',
                    'description': "10000 PCS Women's Cotton Knitted Coat\nHS Code: 6104\nGW: 3,600 KGS\n200 CARTONS",
                    'freight': 'FREIGHT PREPAID',
                    'bl_issued_at': (now - timedelta(days=2)).strftime('%Y-%m-%d'),
                    'bl_originals': '3/3 ORIGINAL',
                    'on_board_date': (now - timedelta(days=2)).strftime('%Y-%m-%d'),
                }, ensure_ascii=False, indent=2),
            },

            # 4. 汇票
            {
                'template_code': 'bill_of_exchange',
                'status': 'approved',
                'data': json.dumps({
                    'draft_no': 'SR-DRAFT-2026-001',
                    'draft_date': (now - timedelta(days=2)).strftime('%Y-%m-%d'),
                    'draft_amount': 'EUR 85,000.00',
                    'amount_in_words': 'EURO EIGHTY-FIVE THOUSAND ONLY',
                    'tenor': 'AT SIGHT',
                    'drawer': 'Hangzhou Silk Road Textiles Co., Ltd.',
                    'drawee': 'Commerzbank AG, Hamburg',
                    'payee': 'Bank of China, Hangzhou Branch',
                    'lc_no': 'COMMB/2026/LC00234',
                    'drawn_under': 'Irrevocable Letter of Credit No. COMMB/2026/LC00234\nDated 2026-04-29\nIssued by Commerzbank AG, Hamburg',
                }, ensure_ascii=False, indent=2),
            },

            # 5. 信用证（单证副本）
            {
                'template_code': 'letter_of_credit',
                'status': 'approved',
                'data': json.dumps({
                    'lc_no': 'COMMB/2026/LC00234',
                    'lc_issue_date': (now - timedelta(days=28)).strftime('%Y-%m-%d'),
                    'lc_type': 'IRREVOCABLE, UNCONFIRMED',
                    'issuing_bank': 'Commerzbank AG, Hamburg',
                    'advising_bank': 'Bank of China, Hangzhou Branch',
                    'applicant': 'Fashion Europe GmbH\nMönckebergstraße 7\n20095 Hamburg, Germany',
                    'beneficiary': 'Hangzhou Silk Road Textiles Co., Ltd.\nSilk Road Building, 188 Shixin North Rd\nXiaoshan District, Hangzhou 311200, China',
                    'amount': 'EUR 85,000.00 (EURO EIGHTY-FIVE THOUSAND ONLY)',
                    'expiry_date': (now + timedelta(days=15)).strftime('%Y-%m-%d'),
                    'expiry_place': 'China',
                    'latest_shipment': (now - timedelta(days=2)).strftime('%Y-%m-%d'),
                    'port_of_loading': 'Shanghai, China',
                    'port_of_discharge': 'Hamburg, Germany',
                    'partial_shipment': 'NOT ALLOWED',
                    'transshipment': 'NOT ALLOWED',
                    'trade_term': 'CIF Hamburg, Incoterms 2020',
                    'documents_required': [
                        'Signed Commercial Invoice in triplicate, currency EUR',
                        'Full set 3/3 clean on board B/L consigned to order of shipper, blank endorsed',
                        'Packing List in triplicate',
                        'Insurance Policy/Certificate for 110% invoice value covering All Risks',
                        'Certificate of Origin FORM A (EU GSP) in 1 original + 1 copy',
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
                    'policy_no': 'PICC2026SH06050001',
                    'insured': 'Hangzhou Silk Road Textiles Co., Ltd.',
                    'insurer': 'PICC Property and Casualty Co., Ltd.',
                    'insured_amount': 'EUR 93,500.00',
                    'insured_amount_in_words': 'EURO NINETY-THREE THOUSAND FIVE HUNDRED ONLY',
                    'coverage': 'ALL RISKS AND WAR RISK',
                    'coverage_clause': 'As per Ocean Marine Cargo Clauses (1/1/1981) of CIC',
                    'cargo_description': "10000 PCS Women's Cotton Knitted Coat (60% Cotton 40% Polyester)",
                    'voyage_from': 'Shanghai (Waigaoqiao), China',
                    'voyage_to': 'Hamburg, Germany',
                    'vessel': 'MSC GÜLSÜN V.012W',
                    'bl_no': 'MSCU8234569200',
                    'container_no': 'MSKU7234891',
                    'premium': 'CNY 561.00',
                    'issue_date': (now - timedelta(days=3)).strftime('%Y-%m-%d'),
                    'claim_settling_agent': 'PICC Europe GmbH, Hamburg',
                    'special_conditions': 'Covering warehouse to warehouse, including loading and unloading',
                }, ensure_ascii=False, indent=2),
            },

            # 7. 产地证 (FORM A 欧盟普惠制)
            {
                'template_code': 'certificate_of_origin',
                'status': 'approved',
                'data': json.dumps({
                    'certificate_no': 'GSP/CCPIT2026/002',
                    'certificate_type': 'FORM A (EU Generalized System of Preferences)',
                    'goods_consigned_from': 'Hangzhou Silk Road Textiles Co., Ltd.\nSilk Road Building, 188 Shixin North Rd\nXiaoshan District, Hangzhou 311200, China',
                    'goods_consigned_to': 'Fashion Europe GmbH\nMönckebergstraße 7\n20095 Hamburg, Germany',
                    'means_of_transport': 'BY VESSEL: MSC GÜLSÜN V.012W',
                    'port_of_loading': 'Shanghai (Waigaoqiao), China',
                    'port_of_discharge': 'Hamburg, Germany',
                    'item_details': [
                        {
                            'marks': 'SR2026SC001\nHAMBURG',
                            'description': "Women's Cotton Knitted Coat (60% Cotton 40% Polyester)",
                            'quantity': '10,000 PCS',
                            'origin_criterion': 'P (Wholly produced in China)',
                        }
                    ],
                    'issue_date': (now - timedelta(days=4)).strftime('%Y-%m-%d'),
                    'issuing_authority': 'China Council for the Promotion of International Trade (CCPIT)',
                    'certification': 'It is hereby certified that the goods described above originate in China. FORM A issued for EU GSP preferential tariff treatment.',
                }, ensure_ascii=False, indent=2),
            },

            # 8. 报检单
            {
                'template_code': 'inspection_application',
                'status': 'approved',
                'data': json.dumps({
                    'application_no': 'IA20260601003',
                    'applicant': 'Hangzhou Silk Road Textiles Co., Ltd.',
                    'inspector': 'Shenzhen Entry-Exit Inspection and Quarantine Bureau',
                    'product_name': '棉质女式针织外套',
                    'product_spec': '60%棉 40%聚酯纤维, 针织, 女式外套',
                    'hs_code': '6104',
                    'quantity': '10,000 PCS',
                    'goods_value': 'EUR 85,000.00',
                    'inspection_type': '法定检验',
                    'inspection_standard': 'GB 18401-2010',
                    'inspection_items': '外观检查、色牢度、甲醛含量、pH值、异味、可分解致癌芳香胺染料',
                    'result': '合格',
                    'certificate_no': 'CIQ20260603003',
                    'application_date': (now - timedelta(days=6)).strftime('%Y-%m-%d'),
                    'inspection_date': (now - timedelta(days=5)).strftime('%Y-%m-%d'),
                    'pass_date': (now - timedelta(days=4)).strftime('%Y-%m-%d'),
                }, ensure_ascii=False, indent=2),
            },

            # 9. 检验证书
            {
                'template_code': 'inspection_certificate',
                'status': 'approved',
                'data': json.dumps({
                    'certificate_no': 'CIQ20260603003',
                    'applicant': 'Hangzhou Silk Road Textiles Co., Ltd.',
                    'product_name': "Women's Cotton Knitted Coat",
                    'hs_code': '6104',
                    'quantity': '10,000 PCS',
                    'contract_no': 'SR2026SC001',
                    'lc_no': 'COMMB/2026/LC00234',
                    'inspection_result': 'QUALITY AND QUANTITY FOUND TO BE IN CONFORMITY WITH THE CONTRACT STIPULATIONS',
                    'inspection_standard': 'GB 18401-2010 (National General Safety Technical Code for Textile Products)',
                    'inspection_date': (now - timedelta(days=4)).strftime('%Y-%m-%d'),
                    'issue_date': (now - timedelta(days=3)).strftime('%Y-%m-%d'),
                    'inspector': 'Shenzhen Entry-Exit Inspection and Quarantine Bureau',
                    'remarks': 'Textile product category: Class B (direct skin contact). Color fastness, formaldehyde, pH value all within standards.',
                }, ensure_ascii=False, indent=2),
            },

            # 10. 出口报关单
            {
                'template_code': 'export_declaration',
                'status': 'approved',
                'data': json.dumps({
                    'declaration_no': 'CD20260605003',
                    'declaration_type': '出口报关',
                    'declarant': '杭州丝绸之纺织品有限公司',
                    'customs_office': '上海海关（浦江海关）',
                    'trade_mode': '一般贸易 (0110)',
                    'transport_mode': '海运 (2)',
                    'hs_code': '6104.42',
                    'goods_name': "Women's Cotton Knitted Coat",
                    'specification': '60%棉 40%聚酯纤维, 针织, 女式外套',
                    'quantity': '10,000',
                    'unit': '件',
                    'unit_price': '8.50',
                    'total_value': 'EUR 85,000.00',
                    'currency': 'EUR',
                    'country_of_destination': '德国 (DE)',
                    'port_of_loading': '上海外高桥 (CNSHA)',
                    'port_of_discharge': '汉堡 (DEHAM)',
                    'container_no': 'MSKU7234891',
                    'gross_weight': '3,600 KGS',
                    'net_weight': '3,000 KGS',
                    'package_count': '200 纸箱',
                    'contract_no': 'SR2026SC001',
                    'supervision_code': '无',
                    'rebate_rate': '9%',
                    'declaration_date': (now - timedelta(days=3)).strftime('%Y-%m-%d'),
                    'clearance_date': (now - timedelta(days=3)).strftime('%Y-%m-%d'),
                }, ensure_ascii=False, indent=2),
            },

            # 11. 装船通知
            {
                'template_code': 'shipping_advice',
                'status': 'approved',
                'data': json.dumps({
                    'advice_no': 'SR-SA-2026-001',
                    'advice_date': (now - timedelta(days=2)).strftime('%Y-%m-%d'),
                    'from': 'Hangzhou Silk Road Textiles Co., Ltd.',
                    'to': 'Fashion Europe GmbH',
                    'contract_no': 'SR2026SC001',
                    'lc_no': 'COMMB/2026/LC00234',
                    'commodity': "10000 PCS Women's Cotton Knitted Coat",
                    'vessel': 'MSC GÜLSÜN V.012W',
                    'bl_no': 'MSCU8234569200',
                    'container_no': 'MSKU7234891',
                    'etd': (now - timedelta(days=3)).strftime('%Y-%m-%d'),
                    'eta': (now + timedelta(days=25)).strftime('%Y-%m-%d'),
                    'port_of_loading': 'Shanghai (Waigaoqiao), China',
                    'port_of_discharge': 'Hamburg, Germany',
                    'shipping_marks': 'SR2026SC001 / HAMBURG / C/NO.1-200',
                    'message': (
                        'We hereby inform you that the above mentioned goods have been shipped '
                        'on board the above vessel on the date shown. Please arrange for import '
                        'clearance and cargo reception accordingly.\n\n'
                        'Full set of original documents will be presented to Commerzbank AG '
                        'for L/C negotiation.'
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
    # 场景：CIF + L/C 机械设备出口泰国（数控车床）
    # ──────────────────────────────────────────────────────────────

    def _create_scenario_machinery_sea(self, now, companies, sample_user):
        """CIF + L/C 场景：数控车床出口泰国（开顶柜，FORM E 产地证）"""

        # ── 新公司 ──────────────────────────────────────────
        self.stdout.write('\n[新增公司] 创建场景 4 公司...')

        exp04, created = self._create_company(
            'EXP04', '广州重工机械有限公司',
            'Guangzhou Heavy Machinery Co., Ltd.',
            'CN', 'machinery',
            '广州市黄埔区开发大道388号重工产业园',
            '+86-20-82201234', 'export@gz-heavy.com')
        self.stdout.write(f'  [{"CREATE" if created else "SKIP"}] {exp04.name}')

        imp04, created = self._create_company(
            'IMP04', 'Siam Industrial Co., Ltd.',
            'Siam Industrial Co., Ltd.',
            'TH', 'manufacturing',
            '888 Vibhavadi Rangsit Road, Chatuchak, Bangkok 10900',
            '+66-2-6101234', 'procurement@siam-industrial.co.th')
        self.stdout.write(f'  [{"CREATE" if created else "SKIP"}] {imp04.name}')

        # ── 商品 ──────────────────────────────────────────
        product = self._ensure_product(
            'M001', '数控车床 CNC Lathe', 'CNC Lathe GZ-CK6150',
            'machinery', 'SET', '845811',
            '最大加工直径500mm, 最大加工长度1000mm, 主轴转速50-3000rpm, 精度0.01mm')
        self.stdout.write(f'  [OK] 商品 {product.name}')

        # ── 交易 ──────────────────────────────────────────
        self.stdout.write('\n[2/10] 创建交易记录 (Machinery SEA CIF+L/C)...')

        transaction, created = Transaction.objects.get_or_create(
            pk=9004,
            defaults={
                'buyer': imp04,
                'seller': exp04,
                'product': product,
                'status': 'completed',
                'quantity': 3,
                'unit_price': Decimal('35000.00'),
                'currency': 'USD',
                'trade_term': 'CIF',
                'port_of_loading': 'Guangzhou',
                'port_of_discharge': 'Laem Chabang, Thailand',
                'notes': '样本交易：数控车床出口泰国，CIF Bangkok，L/C at sight',
            }
        )
        tag = 'CREATE' if created else 'SKIP'
        self.stdout.write(f'  [{tag}] 交易 #{transaction.id}')

        # ── 合同 ──────────────────────────────────────────
        self.stdout.write('\n[3/10] 创建外销合同 (Machinery SEA CIF+L/C)...')

        delivery_date = (now - timedelta(days=4)).date()

        contract, created = Contract.objects.get_or_create(
            contract_no='GZH2026SC001',
            defaults={
                'transaction': transaction,
                'status': 'effective',
                'trade_term': 'CIF',
                'payment_term': 'L/C at sight',
                'delivery_time': delivery_date,
                'port_of_loading': 'Guangzhou (Huangpu)',
                'port_of_discharge': 'Laem Chabang, Thailand',
                'product_name': '数控车床 CNC Lathe GZ-CK6150',
                'product_spec': '最大加工直径500mm, 最大加工长度1000mm, 主轴转速50-3000rpm, 精度0.01mm',
                'quantity': 3,
                'unit': 'SET',
                'unit_price': Decimal('35000.00'),
                'total_amount': Decimal('105000.00'),
                'currency': 'USD',
                'packing': '每台固定于开顶集装箱内，防锈处理，木质底座加固绑扎',
                'shipping_marks': (
                    'GZH2026SC001\n'
                    'LAEM CHABANG\n'
                    'C/NO.: 1-3\n'
                    'G.W.: 3500 KGS\n'
                    'N.W.: 3200 KGS\n'
                    'MEAS: 300×180×200 CM'
                ),
                'remarks': (
                    '1. 装运期：不迟于2026年6月15日\n'
                    '2. 允许分批装运：不允许\n'
                    '3. 允许转船：不允许\n'
                    '4. 品质以中国商品检验局检验证书为准\n'
                    '5. 按 CIF Laem Chabang 成交，卖方负责投保一切险\n'
                    '6. 卖方负责指导安装调试，质保期12个月\n'
                    '7. 产地证要求 FORM E（中国-东盟自贸区）'
                ),
                'seller_signed_at': now - timedelta(days=25),
                'buyer_signed_at': now - timedelta(days=24),
                'effective_at': now - timedelta(days=24),
            }
        )
        tag = 'CREATE' if created else 'SKIP'
        self.stdout.write(f'  [{tag}] 合同 {contract.contract_no}')

        # ── 信用证 ──────────────────────────────────────────
        self.stdout.write('\n[4/10] 创建信用证 (Machinery SEA)...')

        lc_issue_date = (now - timedelta(days=22)).date()
        lc_expiry_date = (now + timedelta(days=15)).date()
        latest_shipment = (now - timedelta(days=2)).date()

        lc, created = LetterOfCredit.objects.get_or_create(
            lc_no='BANGKOK/2026/LC00567',
            defaults={
                'contract': contract,
                'transaction': transaction,
                'status': 'negotiated',
                'issuing_bank': 'Bangkok Bank Public Company Limited',
                'advising_bank': '中国银行广州市分行',
                'applicant': imp04,
                'beneficiary': exp04,
                'amount': Decimal('105000.00'),
                'currency': 'USD',
                'issue_date': lc_issue_date,
                'expiry_date': lc_expiry_date,
                'latest_shipment_date': latest_shipment,
                'port_of_loading': 'Guangzhou, China',
                'port_of_discharge': 'Laem Chabang, Thailand',
                'documents_required': [
                    'Signed Commercial Invoice in triplicate',
                    'Full set of 3/3 clean on board ocean Bills of Lading',
                    'Packing List in triplicate',
                    'Insurance Policy/Certificate for 110% of invoice value covering All Risks',
                    'Certificate of Origin FORM E (ASEAN-China FTA)',
                    'Inspection Certificate issued by CCIC',
                    'Beneficiary Certificate certifying that shipping advice has been sent',
                ],
                'issued_at': now - timedelta(days=22),
                'advised_at': now - timedelta(days=21),
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

        # ── 采购订单 ──────────────────────────────────────
        self.stdout.write('\n[5/10] 创建采购订单 (Machinery SEA)...')

        po_delivery = (now - timedelta(days=8)).date()

        po, created = PurchaseOrder.objects.get_or_create(
            order_no='PO20260608004',
            defaults={
                'transaction': transaction,
                'buyer': exp04,
                'seller': companies['factory'],
                'product_name': '数控车床 GZ-CK6150',
                'product_code': 'M001',
                'quantity': Decimal('3'),
                'unit': 'SET',
                'unit_price': Decimal('180000.00'),
                'currency': 'CNY',
                'total_amount': Decimal('540000.00'),
                'delivery_date': po_delivery,
                'delivery_address': '广州市黄埔区开发大道388号重工产业园仓库',
                'status': 'completed',
                'notes': '数控车床GZ-CK6150，最大加工直径500mm，含安装调试服务',
                'shipped_at': now - timedelta(days=6),
                'invoiced_at': now - timedelta(days=5),
                'completed_at': now - timedelta(days=5),
            }
        )
        tag = 'CREATE' if created else 'SKIP'
        self.stdout.write(f'  [{tag}] 采购订单 {po.order_no}')

        # ── 货运 ──────────────────────────────────────────
        self.stdout.write('\n[6/10] 创建货运订单 (Machinery SEA)...')

        etd = (now - timedelta(days=4)).date()
        eta = etd + timedelta(days=7)

        shipment, created = Shipment.objects.get_or_create(
            shipment_no='SH20260608001',
            defaults={
                'contract': contract,
                'shipper': exp04,
                'carrier': companies['shipping'],
                'booking_no': 'EVER26MA08GZ001',
                'bl_no': 'EGLV492083700',
                'vessel_name': 'EVER GREEN V.036E',
                'port_of_loading': 'Guangzhou (Huangpu), China',
                'port_of_discharge': 'Laem Chabang, Thailand',
                'etd': etd,
                'eta': eta,
                'container_no': 'BMOU5234817 / 40OFR',
                'freight_amount': Decimal('5800.00'),
                'freight_currency': 'USD',
                'status': 'shipped',
                'notes': 'Open-top container, cargo lashed and secured, heavy-lift surcharge applied',
                'booked_at': now - timedelta(days=10),
                'loaded_at': now - timedelta(days=4),
                'shipped_at': now - timedelta(days=3),
            }
        )
        tag = 'CREATE' if created else 'SKIP'
        self.stdout.write(f'  [{tag}] 货运订单 {shipment.shipment_no}')

        # ── 保险 ──────────────────────────────────────────
        self.stdout.write('\n[7/10] 创建保险单 (Machinery SEA)...')

        insurance, created = InsurancePolicy.objects.get_or_create(
            policy_no='PICC2026GZ06080001',
            defaults={
                'contract': contract,
                'shipment': shipment,
                'insured': exp04,
                'insurer': companies['insurance'],
                'cargo_description': (
                    '3 SET CNC Lathe (GZ-CK6150) as per Contract No. GZH2026SC001 '
                    'Shipped per EVER GREEN V.036E '
                    'from Guangzhou to Laem Chabang'
                ),
                'insured_amount': Decimal('115500.00'),  # USD 105000 × 110%
                'premium': Decimal('693.00'),  # ~0.6%
                'premium_currency': 'CNY',
                'coverage_type': 'all_risk',
                'status': 'issued',
                'notes': 'Covering loading/unloading risks for heavy machinery',
                'underwritten_at': now - timedelta(days=5),
                'issued_at': now - timedelta(days=4),
            }
        )
        tag = 'CREATE' if created else 'SKIP'
        self.stdout.write(f'  [{tag}] 保险单 {insurance.policy_no}')

        # ── 报检 ──────────────────────────────────────────
        self.stdout.write('\n[8/10] 创建报检记录 (Machinery SEA)...')

        inspection, created = InspectionApplication.objects.get_or_create(
            application_no='IA20260604004',
            defaults={
                'shipment': shipment,
                'applicant': exp04,
                'inspector': companies['inspection'],
                'product_name': '数控车床 CNC Lathe GZ-CK6150',
                'product_spec': '最大加工直径500mm, 最大加工长度1000mm, 主轴转速50-3000rpm, 精度0.01mm',
                'quantity': Decimal('3'),
                'goods_value': Decimal('105000.00'),
                'inspection_type': 'legal',
                'fee': Decimal('2000.00'),
                'fee_currency': 'CNY',
                'certificate_no': 'CIQ20260606004',
                'origin_certificate_no': 'FORME/CCPIT2026/001',
                'status': 'certified',
                'notes': '机械设备法定检验，依据 GB/T 16462-2007 标准，精度/安全/性能检验合格',
                'inspecting_at': now - timedelta(days=5),
                'passed_at': now - timedelta(days=4),
                'certified_at': now - timedelta(days=3),
            }
        )
        tag = 'CREATE' if created else 'SKIP'
        self.stdout.write(f'  [{tag}] 报检记录 {inspection.application_no}')

        # ── 报关 ──────────────────────────────────────────
        self.stdout.write('\n[9/10] 创建报关单 (Machinery SEA)...')

        customs, created = CustomsDeclaration.objects.get_or_create(
            declaration_no='CD20260608004',
            defaults={
                'shipment': shipment,
                'declarant': exp04,
                'customs_office': companies['customs'],
                'hs_code': '845811',
                'goods_name': '数控车床 CNC Lathe',
                'quantity': Decimal('3'),
                'unit_value': Decimal('35000.00'),
                'total_value': Decimal('105000.00'),
                'currency': 'USD',
                'duty_rate': Decimal('0'),
                'duty_amount': Decimal('0'),
                'vat_rate': Decimal('0.13'),
                'vat_amount': Decimal('0'),
                'status': 'cleared',
                'notes': '机械设备出口，退税率13%',
                'reviewed_at': now - timedelta(days=4),
                'assessed_at': now - timedelta(days=4),
                'cleared_at': now - timedelta(days=4),
            }
        )
        tag = 'CREATE' if created else 'SKIP'
        self.stdout.write(f'  [{tag}] 报关单 {customs.declaration_no}')

        # ── 外汇结算 ──────────────────────────────────────
        self.stdout.write('\n[10/10] 创建外汇结算与退税 (Machinery SEA)...')

        forex, created = ForexSettlement.objects.get_or_create(
            settlement_no='FX20260610004',
            defaults={
                'customs_declaration': customs,
                'applicant': exp04,
                'forex_bureau': companies['forex'],
                'foreign_currency': 'USD',
                'foreign_amount': Decimal('105000.00'),
                'reference_rate': Decimal('7.2450'),
                'reference_cny_amount': Decimal('760725.00'),
                'settlement_rate': Decimal('7.2380'),
                'settlement_cny_amount': Decimal('759990.00'),
                'status': 'settled',
                'notes': 'USD 收汇结汇，收汇金额与报关金额一致',
                'verified_at': now - timedelta(days=1),
                'settled_at': now,
            }
        )
        tag = 'CREATE' if created else 'SKIP'
        self.stdout.write(f'  [{tag}] 外汇结算 {forex.settlement_no}')

        # ── 退税（机械设备 13%）──────────────────────────
        total_value_cny = Decimal('759990.00')

        tax_refund, created = TaxRefundApplication.objects.get_or_create(
            application_no='TR20260611004',
            defaults={
                'customs_declaration': customs,
                'applicant': exp04,
                'tax_bureau': companies['tax'],
                'hs_code': '845811',
                'total_value': total_value_cny,
                'refund_rate': Decimal('0.13'),
                'refund_amount': Decimal('87354.78'),  # 759990 × 13% / 1.13
                'refund_currency': 'CNY',
                'status': 'approved',
                'notes': '机械设备退税率13%，依据出口报关单及增值税发票核准',
                'reviewing_at': now - timedelta(days=1),
                'approved_at': now,
            }
        )
        tag = 'CREATE' if created else 'SKIP'
        self.stdout.write(f'  [{tag}] 退税申请 {tax_refund.application_no}')

        # ── 单证 ──────────────────────────────────────────
        self.stdout.write('\n[单证] 生成场景 4 单证记录...')

        self._create_machinery_sea_documents(
            now, contract, transaction, lc, shipment,
            insurance, inspection, customs, companies,
            exp04, imp04, sample_user)

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

    def _create_machinery_sea_documents(self, now, contract, transaction, lc,
                                         shipment, insurance, inspection, customs,
                                         companies, exp04, imp04, sample_user):
        """创建 CIF + L/C 机械设备出口东南亚场景的单证记录（11 种）"""

        invoice_date = (now - timedelta(days=4)).strftime('%Y-%m-%d')
        bl_date = (now - timedelta(days=3)).strftime('%Y-%m-%d')

        documents_data = [
            # 1. 商业发票
            {
                'template_code': 'commercial_invoice',
                'status': 'approved',
                'data': json.dumps({
                    'invoice_no': 'GZH-INV-2026-001',
                    'invoice_date': invoice_date,
                    'seller_name': 'Guangzhou Heavy Machinery Co., Ltd.',
                    'seller_address': 'Heavy Industry Park, 388 Kaifa Avenue, Huangpu District, Guangzhou, China',
                    'buyer_name': 'Siam Industrial Co., Ltd.',
                    'buyer_address': '888 Vibhavadi Rangsit Road, Chatuchak, Bangkok 10900, Thailand',
                    'contract_no': 'GZH2026SC001',
                    'lc_no': 'BANGKOK/2026/LC00567',
                    'trade_term': 'CIF Laem Chabang, Incoterms 2020',
                    'payment_term': 'L/C at sight',
                    'from_port': 'Guangzhou (Huangpu), China',
                    'to_port': 'Laem Chabang, Thailand',
                    'vessel': 'EVER GREEN V.036E',
                    'container_no': 'BMOU5234817',
                    'items': [
                        {
                            'marks': 'GZH2026SC001\nLAEM CHABANG\nC/NO.1-3\nG.W.:3500KGS',
                            'description': 'CNC Lathe Model GZ-CK6150\nMax turning dia. 500mm, Max turning length 1000mm\nSpindle speed 50-3000rpm, Precision 0.01mm\nHS Code: 845811',
                            'quantity': '3',
                            'unit': 'SET',
                            'unit_price': '35000.00',
                            'amount': '105000.00',
                        }
                    ],
                    'total_amount': 'USD 105,000.00',
                    'packing': '3 open-top containers, anti-rust treated, wooden base secured and lashed',
                    'gross_weight': '10,500.00 KGS',
                    'net_weight': '9,600.00 KGS',
                    'total_packages': '3 SETS',
                }, ensure_ascii=False, indent=2),
            },

            # 2. 装箱单
            {
                'template_code': 'packing_list',
                'status': 'approved',
                'data': json.dumps({
                    'packing_list_no': 'GZH-PL-2026-001',
                    'invoice_no': 'GZH-INV-2026-001',
                    'packing_date': invoice_date,
                    'shipper': 'Guangzhou Heavy Machinery Co., Ltd.',
                    'consignee': 'Siam Industrial Co., Ltd.',
                    'destination': 'Laem Chabang, Thailand',
                    'shipping_marks': 'GZH2026SC001 / LAEM CHABANG / C/NO.1-3',
                    'items': [
                        {
                            'carton_no': 'C/NO. 1',
                            'description': 'CNC Lathe GZ-CK6150 (Unit 1)',
                            'qty_per_carton': '1 SET',
                            'total_qty': '1 SET',
                            'net_weight': '3,200.00 KGS',
                            'gross_weight': '3,500.00 KGS',
                            'measurement': '300×180×200 CM',
                        },
                        {
                            'carton_no': 'C/NO. 2',
                            'description': 'CNC Lathe GZ-CK6150 (Unit 2)',
                            'qty_per_carton': '1 SET',
                            'total_qty': '1 SET',
                            'net_weight': '3,200.00 KGS',
                            'gross_weight': '3,500.00 KGS',
                            'measurement': '300×180×200 CM',
                        },
                        {
                            'carton_no': 'C/NO. 3',
                            'description': 'CNC Lathe GZ-CK6150 (Unit 3)',
                            'qty_per_carton': '1 SET',
                            'total_qty': '1 SET',
                            'net_weight': '3,200.00 KGS',
                            'gross_weight': '3,500.00 KGS',
                            'measurement': '300×180×200 CM',
                        },
                    ],
                    'total_cartons': '3',
                    'total_net_weight': '9,600.00 KGS',
                    'total_gross_weight': '10,500.00 KGS',
                    'total_measurement': '32.4 CBM',
                    'package_type': 'Open-top Container (40\'OFR)',
                }, ensure_ascii=False, indent=2),
            },

            # 3. 海运提单
            {
                'template_code': 'bill_of_lading',
                'status': 'approved',
                'data': json.dumps({
                    'bl_no': 'EGLV492083700',
                    'booking_no': 'EVER26MA08GZ001',
                    'shipper': 'Guangzhou Heavy Machinery Co., Ltd.\nHeavy Industry Park, 388 Kaifa Avenue\nHuangpu District, Guangzhou 510700, China',
                    'consignee': 'TO ORDER OF SHIPPER',
                    'notify_party': 'Siam Industrial Co., Ltd.\n888 Vibhavadi Rangsit Road, Chatuchak\nBangkok 10900, Thailand\nAttn: Mr. Somchai Rattanakosin\nTel: +66-2-6101234',
                    'vessel': 'EVER GREEN',
                    'voyage': '036E',
                    'port_of_loading': 'Guangzhou (Huangpu), China',
                    'port_of_discharge': 'Laem Chabang, Thailand',
                    'etd': (now - timedelta(days=4)).strftime('%Y-%m-%d'),
                    'eta': (now + timedelta(days=3)).strftime('%Y-%m-%d'),
                    'container_no': 'BMOU5234817',
                    'container_type': "1×40'OFR (Open-top)",
                    'seal_no': 'EV260608A',
                    'description': '3 SETS CNC Lathe GZ-CK6150\nHS Code: 845811\nGW: 10,500 KGS\nHEAVY-LIFT CARGO',
                    'freight': 'FREIGHT PREPAID',
                    'bl_issued_at': (now - timedelta(days=3)).strftime('%Y-%m-%d'),
                    'bl_originals': '3/3 ORIGINAL',
                    'on_board_date': (now - timedelta(days=3)).strftime('%Y-%m-%d'),
                }, ensure_ascii=False, indent=2),
            },

            # 4. 汇票
            {
                'template_code': 'bill_of_exchange',
                'status': 'approved',
                'data': json.dumps({
                    'draft_no': 'GZH-DRAFT-2026-001',
                    'draft_date': (now - timedelta(days=2)).strftime('%Y-%m-%d'),
                    'draft_amount': 'USD 105,000.00',
                    'amount_in_words': 'US DOLLARS ONE HUNDRED AND FIVE THOUSAND ONLY',
                    'tenor': 'AT SIGHT',
                    'drawer': 'Guangzhou Heavy Machinery Co., Ltd.',
                    'drawee': 'Bangkok Bank Public Company Limited',
                    'payee': 'Bank of China, Guangzhou Branch',
                    'lc_no': 'BANGKOK/2026/LC00567',
                    'drawn_under': 'Irrevocable Letter of Credit No. BANGKOK/2026/LC00567\nDated ' + (now - timedelta(days=22)).strftime('%Y-%m-%d') + '\nIssued by Bangkok Bank Public Company Limited',
                }, ensure_ascii=False, indent=2),
            },

            # 5. 信用证（单证副本）
            {
                'template_code': 'letter_of_credit',
                'status': 'approved',
                'data': json.dumps({
                    'lc_no': 'BANGKOK/2026/LC00567',
                    'lc_issue_date': (now - timedelta(days=22)).strftime('%Y-%m-%d'),
                    'lc_type': 'IRREVOCABLE, UNCONFIRMED',
                    'issuing_bank': 'Bangkok Bank Public Company Limited',
                    'advising_bank': 'Bank of China, Guangzhou Branch',
                    'applicant': 'Siam Industrial Co., Ltd.\n888 Vibhavadi Rangsit Road, Chatuchak\nBangkok 10900, Thailand',
                    'beneficiary': 'Guangzhou Heavy Machinery Co., Ltd.\nHeavy Industry Park, 388 Kaifa Avenue\nHuangpu District, Guangzhou 510700, China',
                    'amount': 'USD 105,000.00 (US DOLLARS ONE HUNDRED AND FIVE THOUSAND ONLY)',
                    'expiry_date': (now + timedelta(days=15)).strftime('%Y-%m-%d'),
                    'expiry_place': 'China',
                    'latest_shipment': (now - timedelta(days=2)).strftime('%Y-%m-%d'),
                    'port_of_loading': 'Guangzhou, China',
                    'port_of_discharge': 'Laem Chabang, Thailand',
                    'partial_shipment': 'NOT ALLOWED',
                    'transshipment': 'NOT ALLOWED',
                    'trade_term': 'CIF Laem Chabang, Incoterms 2020',
                    'documents_required': [
                        'Signed Commercial Invoice in 3 folds',
                        'Full set 3/3 clean on board B/L consigned to order of shipper, blank endorsed',
                        'Packing List in 3 folds',
                        'Insurance Policy/Certificate for 110% invoice value covering All Risks',
                        'Certificate of Origin FORM E (ASEAN-China FTA) in 1 original + 1 copy',
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
                    'policy_no': 'PICC2026GZ06080001',
                    'insured': 'Guangzhou Heavy Machinery Co., Ltd.',
                    'insurer': 'PICC Property and Casualty Co., Ltd.',
                    'insured_amount': 'USD 115,500.00',
                    'insured_amount_in_words': 'US DOLLARS ONE HUNDRED AND FIFTEEN THOUSAND FIVE HUNDRED ONLY',
                    'coverage': 'ALL RISKS',
                    'coverage_clause': 'As per Ocean Marine Cargo Clauses (1/1/1981) of CIC',
                    'cargo_description': '3 SETS CNC Lathe GZ-CK6150 (Heavy Machinery)',
                    'voyage_from': 'Guangzhou (Huangpu), China',
                    'voyage_to': 'Laem Chabang, Thailand',
                    'vessel': 'EVER GREEN V.036E',
                    'bl_no': 'EGLV492083700',
                    'container_no': 'BMOU5234817',
                    'premium': 'CNY 693.00',
                    'issue_date': (now - timedelta(days=4)).strftime('%Y-%m-%d'),
                    'claim_settling_agent': 'PICC Thailand Co., Ltd., Bangkok',
                    'special_conditions': 'Covering loading/unloading risks for heavy machinery, including warehouse to warehouse',
                }, ensure_ascii=False, indent=2),
            },

            # 7. 产地证 (FORM E 中国-东盟自贸区)
            {
                'template_code': 'certificate_of_origin',
                'status': 'approved',
                'data': json.dumps({
                    'certificate_no': 'FORME/CCPIT2026/001',
                    'certificate_type': 'FORM E (ASEAN-China Free Trade Area)',
                    'goods_consigned_from': 'Guangzhou Heavy Machinery Co., Ltd.\nHeavy Industry Park, 388 Kaifa Avenue\nHuangpu District, Guangzhou 510700, China',
                    'goods_consigned_to': 'Siam Industrial Co., Ltd.\n888 Vibhavadi Rangsit Road, Chatuchak\nBangkok 10900, Thailand',
                    'means_of_transport': 'BY VESSEL: EVER GREEN V.036E',
                    'port_of_loading': 'Guangzhou (Huangpu), China',
                    'port_of_discharge': 'Laem Chabang, Thailand',
                    'item_details': [
                        {
                            'marks': 'GZH2026SC001\nLAEM CHABANG',
                            'description': 'CNC Lathe Model GZ-CK6150\nHS Code: 845811',
                            'quantity': '3 SETS',
                            'origin_criterion': 'WO (Wholly Obtained)',
                            'hs_code': '845811.00',
                        }
                    ],
                    'issue_date': (now - timedelta(days=5)).strftime('%Y-%m-%d'),
                    'issuing_authority': 'China Council for the Promotion of International Trade (CCPIT)',
                    'certification': 'It is hereby certified that the goods described above originate in China. FORM E issued for ASEAN-China FTA preferential tariff treatment.',
                }, ensure_ascii=False, indent=2),
            },

            # 8. 报检单
            {
                'template_code': 'inspection_application',
                'status': 'approved',
                'data': json.dumps({
                    'application_no': 'IA20260604004',
                    'applicant': 'Guangzhou Heavy Machinery Co., Ltd.',
                    'inspector': 'Shenzhen Entry-Exit Inspection and Quarantine Bureau',
                    'product_name': '数控车床 CNC Lathe GZ-CK6150',
                    'product_spec': '最大加工直径500mm, 最大加工长度1000mm, 主轴转速50-3000rpm, 精度0.01mm',
                    'hs_code': '845811',
                    'quantity': '3 SETS',
                    'goods_value': 'USD 105,000.00',
                    'inspection_type': '法定检验',
                    'inspection_standard': 'GB/T 16462-2007',
                    'inspection_items': '精度检测、安全防护、电气安全、噪声等级、性能测试',
                    'result': '合格',
                    'certificate_no': 'CIQ20260606004',
                    'application_date': (now - timedelta(days=6)).strftime('%Y-%m-%d'),
                    'inspection_date': (now - timedelta(days=5)).strftime('%Y-%m-%d'),
                    'pass_date': (now - timedelta(days=4)).strftime('%Y-%m-%d'),
                }, ensure_ascii=False, indent=2),
            },

            # 9. 检验证书
            {
                'template_code': 'inspection_certificate',
                'status': 'approved',
                'data': json.dumps({
                    'certificate_no': 'CIQ20260606004',
                    'applicant': 'Guangzhou Heavy Machinery Co., Ltd.',
                    'product_name': 'CNC Lathe Model GZ-CK6150',
                    'hs_code': '845811',
                    'quantity': '3 SETS',
                    'contract_no': 'GZH2026SC001',
                    'lc_no': 'BANGKOK/2026/LC00567',
                    'inspection_result': 'QUALITY AND QUANTITY FOUND TO BE IN CONFORMITY WITH THE CONTRACT STIPULATIONS',
                    'inspection_standard': 'GB/T 16462-2007 (CNC Lathe - Testing of the Accuracy)',
                    'inspection_date': (now - timedelta(days=4)).strftime('%Y-%m-%d'),
                    'issue_date': (now - timedelta(days=3)).strftime('%Y-%m-%d'),
                    'inspector': 'Shenzhen Entry-Exit Inspection and Quarantine Bureau',
                    'remarks': 'All 3 units tested individually. Machining precision 0.01mm confirmed. Safety guards and emergency stops verified.',
                }, ensure_ascii=False, indent=2),
            },

            # 10. 出口报关单
            {
                'template_code': 'export_declaration',
                'status': 'approved',
                'data': json.dumps({
                    'declaration_no': 'CD20260608004',
                    'declaration_type': '出口报关',
                    'declarant': '广州重工机械有限公司',
                    'customs_office': '广州海关（黄埔海关）',
                    'trade_mode': '一般贸易 (0110)',
                    'transport_mode': '海运 (2)',
                    'hs_code': '845811.00',
                    'goods_name': '数控车床 CNC Lathe',
                    'specification': 'GZ-CK6150',
                    'quantity': '3',
                    'unit': '台',
                    'unit_price': '35,000.00',
                    'total_value': 'USD 105,000.00',
                    'currency': 'USD',
                    'country_of_destination': '泰国 (TH)',
                    'port_of_loading': '广州黄埔 (CNGGZ)',
                    'port_of_discharge': '林查班 (THLCH)',
                    'container_no': 'BMOU5234817',
                    'gross_weight': '10,500 KGS',
                    'net_weight': '9,600 KGS',
                    'package_count': '3 台（开顶集装箱）',
                    'contract_no': 'GZH2026SC001',
                    'supervision_code': '无',
                    'rebate_rate': '13%',
                    'declaration_date': (now - timedelta(days=4)).strftime('%Y-%m-%d'),
                    'clearance_date': (now - timedelta(days=4)).strftime('%Y-%m-%d'),
                }, ensure_ascii=False, indent=2),
            },

            # 11. 装船通知
            {
                'template_code': 'shipping_advice',
                'status': 'approved',
                'data': json.dumps({
                    'advice_no': 'GZH-SA-2026-001',
                    'advice_date': (now - timedelta(days=3)).strftime('%Y-%m-%d'),
                    'from': 'Guangzhou Heavy Machinery Co., Ltd.',
                    'to': 'Siam Industrial Co., Ltd.',
                    'contract_no': 'GZH2026SC001',
                    'lc_no': 'BANGKOK/2026/LC00567',
                    'commodity': '3 SETS CNC Lathe (GZ-CK6150)',
                    'vessel': 'EVER GREEN V.036E',
                    'bl_no': 'EGLV492083700',
                    'container_no': 'BMOU5234817',
                    'etd': (now - timedelta(days=4)).strftime('%Y-%m-%d'),
                    'eta': (now + timedelta(days=3)).strftime('%Y-%m-%d'),
                    'port_of_loading': 'Guangzhou (Huangpu), China',
                    'port_of_discharge': 'Laem Chabang, Thailand',
                    'shipping_marks': 'GZH2026SC001 / LAEM CHABANG / C/NO.1-3',
                    'message': (
                        'We hereby inform you that the above mentioned goods have been shipped '
                        'on board the above vessel on the date shown. Please arrange for import '
                        'clearance and cargo reception accordingly.\n\n'
                        'As per contract terms, we will send engineers for installation and '
                        'commissioning guidance upon your notification of readiness. '
                        'The warranty period is 12 months from the date of commissioning.\n\n'
                        'Full set of original documents will be presented to Bangkok Bank '
                        'for L/C negotiation.'
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
