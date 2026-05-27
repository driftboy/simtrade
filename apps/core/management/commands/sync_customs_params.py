"""
从海关总署在线查询平台同步海关参数代码表到数据库。

API: https://www.chinaport.gov.cn/api/getSwapi?tableName=<name>
当API不可用时，使用内嵌备份数据或网页抓取。
"""
import json
import re
import ssl
import urllib.request

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.core.models import (
    CustomsDoc,
    CustomsDistrict,
    DomesticRegion,
    LevyMode,
    PackageType,
    TradeMode,
    TransportMode,
    UnitOfMeasure,
)

API_BASE = 'https://www.chinaport.gov.cn/api/getSwapi'

# 表名 -> (Model, field_mapping)
TABLE_CONFIG = {
    'cusTrade': {
        'model': TradeMode,
        'fields': {
            'code': 'codeValue',
            'name': 'codeName',
            'full_name': 'fullTrade',
        },
    },
    'cusTrans': {
        'model': TransportMode,
        'fields': {
            'code': 'codeValue',
            'name': 'codeName',
        },
    },
    'cusWrap': {
        'model': PackageType,
        'fields': {
            'code': 'codeValue',
            'name': 'codeName',
        },
    },
    'cusUnit': {
        'model': UnitOfMeasure,
        'fields': {
            'code': 'unitCode',
            'name': 'unitName',
            'conv_ratio': 'convRatio',
            'conv_code': 'convCode',
        },
    },
    'cusCustoms': {
        'model': CustomsDistrict,
        'fields': {
            'code': 'codeValue',
            'name': 'codeName',
        },
    },
    'cusLevyMode': {
        'model': LevyMode,
        'fields': {
            'code': 'codeValue',
            'name': 'codeName',
        },
    },
    'cusDoc': {
        'model': CustomsDoc,
        'fields': {
            'code': 'codeValue',
            'name': 'codeName',
        },
    },
    'cusDist': {
        'model': DomesticRegion,
        'fields': {
            'code': 'codeValue',
            'name': 'codeName',
        },
    },
}

# ---------------------------------------------------------------------------
# Fallback data (when chinaport API is rate-limited or unavailable)
# ---------------------------------------------------------------------------
FALLBACK_DATA = {
    'cusTrans': [
        {'codeValue': '0', 'codeName': '非保税区'},
        {'codeValue': '1', 'codeName': '监管仓库'},
        {'codeValue': '2', 'codeName': '水路运输'},
        {'codeValue': '3', 'codeName': '铁路运输'},
        {'codeValue': '4', 'codeName': '公路运输'},
        {'codeValue': '5', 'codeName': '航空运输'},
        {'codeValue': '6', 'codeName': '邮件运输'},
        {'codeValue': '7', 'codeName': '保税区'},
        {'codeValue': '8', 'codeName': '保税仓库'},
        {'codeValue': '9', 'codeName': '其他运输'},
    ],
    'cusWrap': [
        {'codeValue': '00', 'codeName': '散装'},
        {'codeValue': '01', 'codeName': '裸装'},
        {'codeValue': '11', 'codeName': '木箱'},
        {'codeValue': '12', 'codeName': '纸箱'},
        {'codeValue': '13', 'codeName': '桶装'},
        {'codeValue': '15', 'codeName': '托盘'},
        {'codeValue': '16', 'codeName': '散装'},
        {'codeValue': '17', 'codeName': '捆扎'},
        {'codeValue': '18', 'codeName': '其他'},
        {'codeValue': '22', 'codeName': '纸制或纤维板制盒/箱'},
        {'codeValue': '23', 'codeName': '木制或竹藤等植物性材料制盒/箱'},
        {'codeValue': '29', 'codeName': '其他材料制盒/箱'},
        {'codeValue': '32', 'codeName': '纸制或纤维板制桶'},
        {'codeValue': '33', 'codeName': '木制或竹藤等植物性材料制桶'},
        {'codeValue': '39', 'codeName': '其他材料制桶'},
        {'codeValue': '42', 'codeName': '纸制或纤维板制罐/听'},
        {'codeValue': '43', 'codeName': '木制或竹藤等植物性材料制罐/听'},
        {'codeValue': '49', 'codeName': '其他材料制罐/听'},
        {'codeValue': '52', 'codeName': '纸制或纤维板制卷/轴'},
        {'codeValue': '53', 'codeName': '木制或竹藤等植物性材料制卷/轴'},
        {'codeValue': '59', 'codeName': '其他材料制卷/轴'},
        {'codeValue': '62', 'codeName': '纸制或纤维板制捆/包'},
        {'codeValue': '63', 'codeName': '木制或竹藤等植物性材料制捆/包'},
        {'codeValue': '69', 'codeName': '其他材料制捆/包'},
        {'codeValue': '72', 'codeName': '纸制或纤维板制袋/包'},
        {'codeValue': '73', 'codeName': '木制或竹藤等植物性材料制袋/包'},
        {'codeValue': '79', 'codeName': '其他材料制袋/包'},
        {'codeValue': '81', 'codeName': '天然木质托'},
        {'codeValue': '87', 'codeName': '塑料托'},
        {'codeValue': '91', 'codeName': '其他材质托盘'},
        {'codeValue': '92', 'codeName': '纸制或纤维板制托盘'},
        {'codeValue': '93', 'codeName': '木制或竹藤等植物性材料制托盘'},
        {'codeValue': '99', 'codeName': '其他材料制托盘'},
    ],
    'cusLevyMode': [
        {'codeValue': '1', 'codeName': '照章征税'},
        {'codeValue': '2', 'codeName': '折半征税'},
        {'codeValue': '3', 'codeName': '全免'},
        {'codeValue': '4', 'codeName': '特案'},
        {'codeValue': '5', 'codeName': '随征免性'},
        {'codeValue': '6', 'codeName': '保证金'},
        {'codeValue': '7', 'codeName': '保函'},
        {'codeValue': '8', 'codeName': '折半补税'},
        {'codeValue': '9', 'codeName': '全额退税'},
    ],
    'cusDoc': [
        {'codeValue': '1', 'codeName': '进口许可证'},
        {'codeValue': '2', 'codeName': '汽车进口许可证'},
        {'codeValue': '3', 'codeName': '两用物项和技术出口许可证'},
        {'codeValue': '4', 'codeName': '出口许可证'},
        {'codeValue': '5', 'codeName': '定向出口商品许可证'},
        {'codeValue': '7', 'codeName': '重要工业品或外商或自动登记证明'},
        {'codeValue': '8', 'codeName': '禁止出口商品'},
        {'codeValue': 'A', 'codeName': '入境货物通关单'},
        {'codeValue': 'B', 'codeName': '出境货物通关单'},
        {'codeValue': 'D', 'codeName': '出/入境货物通关单(毛坯钻石用)'},
        {'codeValue': 'E', 'codeName': '濒危物种允许出口证明书'},
        {'codeValue': 'F', 'codeName': '濒危物种进出口允许证'},
        {'codeValue': 'G', 'codeName': '两用物项和技术出口许可证(定向)'},
        {'codeValue': 'I', 'codeName': '精神药物进(出)口准许证'},
        {'codeValue': 'J', 'codeName': '金产品出口证或人总行进口批件'},
        {'codeValue': 'L', 'codeName': '药品进出口准许证'},
        {'codeValue': 'M', 'codeName': '密码产品和设备进口许可证'},
        {'codeValue': 'N', 'codeName': '机电产品进口许可证'},
        {'codeValue': 'O', 'codeName': '自动进口许可证(机电产品)'},
        {'codeValue': 'P', 'codeName': '进口固体废物原料许可证'},
        {'codeValue': 'Q', 'codeName': '进口药品通关单'},
        {'codeValue': 'R', 'codeName': '进口兽药通关单'},
        {'codeValue': 'S', 'codeName': '进出口农药登记证明'},
        {'codeValue': 'T', 'codeName': '银行调运外币现钞进出境许可证'},
        {'codeValue': 'U', 'codeName': '合法捕捞产品通关证明'},
        {'codeValue': 'V', 'codeName': '有毒化学品进出口环境管理放行通知单'},
        {'codeValue': 'W', 'codeName': '麻醉药品准许证'},
        {'codeValue': 'X', 'codeName': '有毒化学品进出口环境管理登记证'},
        {'codeValue': 'Y', 'codeName': '优惠贸易协定原产地证明'},
        {'codeValue': 'e', 'codeName': '香港 Macao CEPA原产地证书'},
        {'codeValue': 'h', 'codeName': '香港 CEPA原产地证书'},
        {'codeValue': 'm', 'codeName': '银行调运人民币现钞进出境证明'},
        {'codeValue': 's', 'codeName': '适用ITA税率的商品用途认定证明'},
        {'codeValue': 'y', 'codeName': '原产地证书'},
    ],
}


def _ssl_ctx():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def fetch_table(table_name):
    """从海关总署 API 获取参数表数据"""
    url = f'{API_BASE}?tableName={table_name}'
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://online.customs.gov.cn/',
    })
    with urllib.request.urlopen(req, context=_ssl_ctx(), timeout=30) as resp:
        raw = json.loads(resp.read().decode('utf-8'))

    ret_data = raw.get('message', {}).get('retData')
    if isinstance(ret_data, str):
        return json.loads(ret_data)
    return ret_data or []


def scrape_cusdist():
    """从海关总署网站抓取国内地区代码表"""
    url = 'http://gdfs.customs.gov.cn/customs/302249/zfxxgk/2799825/302274/tjfwzn/2363253/index.html'
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        html = resp.read().decode('utf-8')

    entries = []
    pattern = re.compile(r'[一-鿿（）()A-Za-z\-－\d]+?\s*(\d{4,5}[A-Za-z]?)\s*')
    for m in re.finditer(r'>([^<]+?)(\d{4,5}[A-Za-z]?)<', html):
        name_raw = m.group(1).strip()
        code = m.group(2).strip()
        if name_raw and code and len(code) >= 4:
            name = re.sub(r'\s+', '', name_raw)
            if name:
                entries.append({'codeValue': code, 'codeName': name})

    # Deduplicate by code
    seen = set()
    result = []
    for e in entries:
        if e['codeValue'] not in seen:
            seen.add(e['codeValue'])
            result.append(e)
    return result


class Command(BaseCommand):
    help = '从海关总署同步参数代码表到数据库（API优先，自动回退到备份数据）'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='只显示获取到的数据，不写入数据库',
        )
        parser.add_argument(
            '--table',
            type=str,
            default=None,
            help='只同步指定的表（如 cusTrade, cusUnit 等）',
        )
        parser.add_argument(
            '--fallback-only',
            action='store_true',
            help='仅使用备份数据，不尝试API',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        table_filter = options.get('table')
        fallback_only = options.get('fallback_only')

        tables = TABLE_CONFIG
        if table_filter:
            if table_filter not in TABLE_CONFIG:
                self.stderr.write(self.style.ERROR(
                    f'未知表名: {table_filter}，可选: {", ".join(TABLE_CONFIG.keys())}'
                ))
                return
            tables = {table_filter: TABLE_CONFIG[table_filter]}

        total_created = 0
        total_updated = 0

        for table_name, config in tables.items():
            model = config['model']
            field_map = config['fields']
            model_name = model._meta.verbose_name

            self.stdout.write(f'\n正在获取 {model_name}（{table_name}）...')

            rows = None

            # 1. Try API (unless --fallback-only)
            if not fallback_only:
                try:
                    rows = fetch_table(table_name)
                    self.stdout.write(f'  API: 获取到 {len(rows)} 条记录')
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'  API 不可用: {e}'))

            # 2. Fallback: embedded data or web scrape
            if not rows:
                if table_name in FALLBACK_DATA:
                    rows = FALLBACK_DATA[table_name]
                    self.stdout.write(f'  备份数据: {len(rows)} 条记录')
                elif table_name == 'cusDist':
                    self.stdout.write('  尝试从海关网站抓取国内地区代码表...')
                    try:
                        rows = scrape_cusdist()
                        self.stdout.write(f'  网页抓取: 获取到 {len(rows)} 条记录')
                    except Exception as e:
                        self.stderr.write(self.style.ERROR(f'  抓取失败: {e}'))
                        continue
                else:
                    self.stdout.write(self.style.WARNING('  无可用数据源'))
                    continue

            if not rows:
                self.stdout.write(self.style.WARNING('  无数据'))
                continue

            if dry_run:
                for row in rows[:5]:
                    vals = {k: row.get(v, '') for k, v in field_map.items()}
                    self.stdout.write(f'  {vals}')
                if len(rows) > 5:
                    self.stdout.write(f'  ... 还有 {len(rows) - 5} 条')
                continue

            created = 0
            updated = 0

            with transaction.atomic():
                for row in rows:
                    code = row.get(field_map['code'], '').strip()
                    if not code:
                        continue

                    defaults = {'is_active': True}
                    for model_field, api_field in field_map.items():
                        if model_field == 'code':
                            continue
                        val = row.get(api_field, '')
                        if val is not None:
                            val = str(val).strip()
                        defaults[model_field] = val

                    if 'conv_ratio' in defaults:
                        try:
                            defaults['conv_ratio'] = float(defaults['conv_ratio']) if defaults['conv_ratio'] else 1
                        except (ValueError, TypeError):
                            defaults['conv_ratio'] = 1

                    _, is_new = model.objects.update_or_create(
                        code=code,
                        defaults=defaults,
                    )
                    if is_new:
                        created += 1
                    else:
                        updated += 1

            self.stdout.write(self.style.SUCCESS(
                f'  {model_name}: 新增 {created}，更新 {updated}'
            ))
            total_created += created
            total_updated += updated

        if not dry_run:
            self.stdout.write(self.style.SUCCESS(
                f'\n同步完成: 共新增 {total_created} 条，更新 {total_updated} 条'
            ))
