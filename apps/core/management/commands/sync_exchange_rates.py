"""
从商务部商品价格网同步汇率数据到数据库。

API: https://price.mofcom.gov.cn/datamofcom/front/ExchFinancialDyna/searchlist/query
返回格式: X 单位外币 = 1 美元
"""
import ssl
import urllib.request
import json
from datetime import date

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.core.models import Currency, ExchangeRate

# 商务部货币名 -> ISO 4217 映射（常见货币）
CURRENCY_MAP = {
    ('中国', '人民币元'): ('CNY', '¥'),
    ('香港', '港元'): ('HKD', 'HK$'),
    ('台湾(地区)', '新台币'): ('TWD', 'NT$'),
    ('澳门', '澳门元'): ('MOP', 'MOP$'),
    ('日本', '日元'): ('JPY', '¥'),
    ('韩国', '圆'): ('KRW', '₩'),
    ('朝鲜', '圆'): ('KPW', '₩'),
    ('新加坡', '新加坡元'): ('SGD', 'S$'),
    ('澳大利亚', '澳大利亚元'): ('AUD', 'A$'),
    ('新西兰', '新西兰元'): ('NZD', 'NZ$'),
    ('加拿大', '加拿大元'): ('CAD', 'C$'),
    ('英国', '英镑'): ('GBP', '£'),
    ('美国', '美元'): ('USD', '$'),
    ('德国', '欧元'): ('EUR', '€'),
    ('法国', '欧元'): ('EUR', '€'),
    ('意大利', '欧元'): ('EUR', '€'),
    ('西班牙', '欧元'): ('EUR', '€'),
    ('荷兰', '欧元'): ('EUR', '€'),
    ('比利时', '欧元'): ('EUR', '€'),
    ('奥地利', '欧元'): ('EUR', '€'),
    ('芬兰', '欧元'): ('EUR', '€'),
    ('葡萄牙', '欧元'): ('EUR', '€'),
    ('爱尔兰共和国', '欧元'): ('EUR', '€'),
    ('希腊', '欧元'): ('EUR', '€'),
    ('瑞典', '瑞典克朗'): ('SEK', 'kr'),
    ('丹麦', '丹麦克朗'): ('DKK', 'kr'),
    ('挪威', '挪威克朗'): ('NOK', 'kr'),
    ('瑞士', '瑞士法郎'): ('CHF', 'CHF'),
    ('俄罗斯', '卢布'): ('RUB', '₽'),
    ('印度', '印度卢比'): ('INR', '₹'),
    ('泰国', '铢'): ('THB', '฿'),
    ('马来西亚', '马来西亚林吉特'): ('MYR', 'RM'),
    ('印度尼西亚', '印尼盾'): ('IDR', 'Rp'),
    ('菲律宾', '比索'): ('PHP', '₱'),
    ('越南', '盾'): ('VND', '₫'),
    ('巴西', '雷亚尔'): ('BRL', 'R$'),
    ('墨西哥', '墨西哥比索'): ('MXN', 'Mex$'),
    ('阿根廷', '比索'): ('ARS', 'ARS$'),
    ('土耳其', '土耳其里拉'): ('TRY', '₺'),
    ('沙特阿拉伯', '里亚尔'): ('SAR', '﷼'),
    ('阿拉伯联合酋长国', '阿联酋迪拉姆'): ('AED', 'د.إ'),
    ('南非', '兰特'): ('ZAR', 'R'),
    ('埃及', '埃镑'): ('EGP', 'E£'),
    ('以色列', '谢克尔'): ('ILS', '₪'),
    ('波兰', '兹罗提'): ('PLN', 'zł'),
    ('捷克共和国', '克朗'): ('CZK', 'Kč'),
    ('匈牙利', '福林'): ('HUF', 'Ft'),
    ('乌克兰', '格里夫纳'): ('UAH', '₴'),
    ('罗马尼亚', '列伊'): ('RON', 'lei'),
    ('文莱', '文莱元'): ('BND', 'B$'),
    ('巴基斯坦', '巴基斯坦卢比'): ('PKR', '₨'),
    ('孟加拉国', '塔卡'): ('BDT', '৳'),
    ('斯里兰卡', '卢比'): ('LKR', 'Rs'),
    ('哈萨克斯坦', '坚戈'): ('KZT', '₸'),
    ('卡塔尔', '卡特尔里亚尔'): ('QAR', '﷼'),
    ('科威特', '科威特第纳尔'): ('KWD', 'د.ك'),
    ('巴林', '第纳尔'): ('BHD', 'BD'),
    ('阿曼', '里亚尔'): ('OMR', '﷼'),
    ('约旦', '约旦第纳尔'): ('JOD', 'JD'),
    ('柬埔寨', '瑞尔'): ('KHR', '៛'),
    ('缅甸', '缅元'): ('MMK', 'K'),
    ('老挝', '新基普'): ('LAK', '₭'),
    ('蒙古', '图格里克'): ('MNT', '₮'),
    ('尼泊尔', '尼泊尔卢比'): ('NPR', '₨'),
    ('伊朗', '里亚尔'): ('IRR', '﷼'),
    ('伊拉克', '伊拉克第纳尔'): ('IQD', 'ع.د'),
    ('叙利亚', '叙利亚镑'): ('SYP', 'S£'),
    ('黎巴嫩', '黎巴嫩镑'): ('LBP', 'ل.ل'),
    ('肯尼亚', '肯尼亚先令'): ('KES', 'KSh'),
    ('坦桑尼亚', '先令'): ('TZS', 'TSh'),
    ('乌干达', '新先令'): ('UGX', 'USh'),
    ('尼日利亚', '奈拉'): ('NGN', '₦'),
    ('加纳', '塞地'): ('GHS', 'GH₵'),
    ('摩洛哥', '迪拉姆'): ('MAD', 'MAD'),
    ('突尼斯', '第纳尔'): ('TND', 'د.ت'),
    ('阿尔及利亚', '第纳尔'): ('DZD', 'د.ج'),
    ('苏丹', '苏丹镑'): ('SDG', 'ج.س.'),
    ('哥伦比亚', '哥伦比亚比索'): ('COP', 'COL$'),
    ('秘鲁', '新索尔'): ('PEN', 'S/.'),
    ('智利', '智利比索'): ('CLP', 'CLP$'),
    ('委内瑞拉', '博利瓦'): ('VEF', 'Bs.'),
    ('古巴', '古巴比索'): ('CUP', '$MN'),
    ('冰岛', '冰岛克朗'): ('ISK', 'kr'),
    ('克罗地亚', '库纳'): ('HRK', 'kn'),
    ('保加利亚', '列弗'): ('BGN', 'лв'),
    ('塞尔维亚和黑山', '新第纳尔'): ('RSD', 'дин.'),
    ('格鲁吉亚', '拉里'): ('GEL', '₾'),
    ('亚美尼亚', '德拉姆'): ('AMD', '֏'),
    ('阿塞拜疆', '与那特'): ('AZN', '₼'),
    ('斐济', '斐济元'): ('FJD', 'FJ$'),
    ('巴布亚新几内亚', '基那'): ('PGK', 'K'),
    # 美元使用国（MOFCOM 没有美国条目，美元在这些国家名下）
    ('厄瓜多尔', '美元'): ('USD', '$'),
    ('关岛', '美元'): ('USD', '$'),
    ('波多黎各', '美元'): ('USD', '$'),
}


API_URL = 'https://price.mofcom.gov.cn/datamofcom/front/ExchFinancialDyna/searchlist/query'


def _ssl_ctx():
    ctx = ssl.create_default_context()
    ctx.set_ciphers('DEFAULT@SECLEVEL=1')
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def fetch_rates(page_size=200):
    """从商务部 API 获取最新一页汇率数据"""
    params = f'country_namc=&currency_namc=&pageNumber=1&pageSize={page_size}'
    url = f'{API_URL}?{params}'
    req = urllib.request.Request(url, method='POST', headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Content-Type': 'application/x-www-form-urlencoded',
    })
    with urllib.request.urlopen(req, context=_ssl_ctx(), timeout=20) as resp:
        raw = resp.read().decode('utf-8')
    return json.loads(raw)


class Command(BaseCommand):
    help = '从商务部同步最新汇率数据到数据库'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='只显示获取到的数据，不写入数据库',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        self.stdout.write('正在从商务部获取最新汇率数据...')
        try:
            data = fetch_rates()
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'获取数据失败: {e}'))
            return

        rows = data.get('rows', [])
        if not rows:
            self.stderr.write(self.style.WARNING('未获取到汇率数据'))
            return

        rate_date_str = f'{rows[0]["yyyy"]}-{rows[0]["mm"]}-{rows[0]["dd"]}'
        rate_date = date.fromisoformat(rate_date_str)
        self.stdout.write(f'数据日期: {rate_date}，共 {len(rows)} 条汇率')

        # 找到人民币兑美元汇率（用于计算兑人民币汇率）
        cny_rate_to_usd = None
        for row in rows:
            if row['country_namc'] == '中国' and row['currency_namc'] == '人民币元':
                cny_rate_to_usd = float(row['exchange'])
                break

        if dry_run:
            for row in rows:
                key = (row['country_namc'], row['currency_namc'])
                iso_info = CURRENCY_MAP.get(key)
                iso = iso_info[0] if iso_info else '-'
                rate_cny = ''
                if cny_rate_to_usd:
                    try:
                        r = float(row['exchange'])
                        rate_cny = f'{cny_rate_to_usd / r:.4f}'
                    except (ValueError, ZeroDivisionError):
                        pass
                self.stdout.write(
                    f'  {iso:5s} | {row["country_namc"]:15s} | {row["currency_namc"]:12s} | '
                    f'1 USD = {row["exchange"]:>12s} | 1 {row["currency_namc"]} = {rate_cny} CNY'
                )
            return

        created_rates = 0
        skipped_rates = 0
        created_currencies = 0

        with transaction.atomic():
            # 去重：同种货币只保留第一个匹配到的代表国家
            seen = set()
            for row in rows:
                country = row['country_namc'].strip()
                currency_name = row['currency_namc'].strip()

                if currency_name in seen:
                    continue
                seen.add(currency_name)

                try:
                    rate_to_usd = float(row['exchange'])
                except (ValueError, TypeError):
                    continue

                # 计算 1 外币 = X 人民币
                rate_to_cny = None
                if cny_rate_to_usd and rate_to_usd:
                    rate_to_cny = round(cny_rate_to_usd / rate_to_usd, 6)

                # 映射到 ISO 4217（先尝试精确匹配，再尝试只匹配货币名）
                key = (country, currency_name)
                iso_info = CURRENCY_MAP.get(key)
                if not iso_info:
                    # 遍历映射表找同货币名的
                    for (_, cu), v in CURRENCY_MAP.items():
                        if cu == currency_name and v[0] not in seen:
                            iso_info = v
                            break
                currency_obj = None

                if iso_info:
                    iso_code, symbol = iso_info
                    currency_obj, cur_created = Currency.objects.update_or_create(
                        code=iso_code,
                        defaults={
                            'name': currency_name,
                            'name_en': iso_code,
                            'symbol': symbol,
                            'is_active': True,
                        },
                    )
                    if cur_created:
                        created_currencies += 1

                # 创建/更新汇率记录
                _, rate_created = ExchangeRate.objects.update_or_create(
                    currency_name=currency_name,
                    rate_date=rate_date,
                    defaults={
                        'country_name': country,
                        'currency': currency_obj,
                        'rate_to_usd': rate_to_usd,
                        'rate_to_cny': rate_to_cny,
                        'source': 'mofcom',
                    },
                )
                if rate_created:
                    created_rates += 1
                else:
                    skipped_rates += 1

        self.stdout.write(self.style.SUCCESS(
            f'同步完成: 新增 {created_rates} 条汇率，跳过 {skipped_rates} 条（已存在），'
            f'新增 {created_currencies} 种货币'
        ))
