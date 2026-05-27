"""
从 hsbianma.com 爬取 HS 编码数据并入库。

用法:
    python manage.py sync_hs_codes                          # 全部章节
    python manage.py sync_hs_codes --chapter 84,85          # 指定章节
    python manage.py sync_hs_codes --chapter 84 --dry-run   # 仅预览
    python manage.py sync_hs_codes --filter-expired         # 跳过过期编码
"""
import re
import time
import urllib.request

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.products.models import HSCode

BASE_URL = 'https://www.hsbianma.com'
PAGE_SIZE = 20
REQUEST_DELAY = 1.5


def fetch_page(chapter, page):
    """抓取指定章节的某一页，返回 (rows, has_more)"""
    if page == 1:
        url = f'{BASE_URL}/search?keywords={chapter}'
    else:
        url = f'{BASE_URL}/Search/{page}?keywords={chapter}'

    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        html = resp.read().decode('utf-8')

    rows = []
    row_pattern = re.compile(
        r'<tr class="result-grid">\s*'
        r'<td>(.*?)</td>\s*'      # 编码
        r'<td>(.*?)</td>\s*'      # 名称
        r'<td class="tcenter">(.*?)</td>\s*'  # 单位
        r'<td class="tcenter">(.*?)</td>\s*'  # 退税率
        r'<td class="tcenter">(.*?)</td>\s*'  # 监管条件
        r'<td class="tcenter">(.*?)</td>\s*'  # 检验检疫
        r'<td class="tcenter">.*?</td>\s*'    # 详情链接
        r'</tr>',
        re.DOTALL,
    )

    for m in row_pattern.finditer(html):
        raw_code = _strip_tags(m.group(1))
        is_expired = '[过期]' in m.group(1)
        code = re.sub(r'[^\d]', '', raw_code)

        if not code or len(code) < 6:
            continue

        rows.append({
            'code': code,
            'name': _strip_tags(m.group(2)).strip(),
            'unit': _strip_tags(m.group(3)).strip(),
            'rebate_rate': _strip_tags(m.group(4)).strip(),
            'supervision': _strip_tags(m.group(5)).strip(),
            'inspection': _strip_tags(m.group(6)).strip(),
            'is_expired': is_expired,
        })

    has_more = len(rows) >= PAGE_SIZE
    return rows, has_more


def fetch_chapter(chapter):
    """抓取一个章节的所有页面"""
    all_rows = []
    page = 1

    while True:
        rows, has_more = fetch_page(chapter, page)
        all_rows.extend(rows)
        if not has_more:
            break
        page += 1
        time.sleep(REQUEST_DELAY)

    return all_rows


def fetch_detail(code):
    """抓取编码详情页，返回税率信息字典"""
    url = f'{BASE_URL}/Code/{code}.html'
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            html = resp.read().decode('utf-8')
    except Exception:
        return {}

    rates = {}
    # 税率字段映射
    tax_fields = {
        '出口税率': 'export_rate',
        '出口退税税率': 'rebate_rate',
        '出口暂定税率': 'export_provisional',
        '增值税率': 'vat_rate',
        '最惠国税率': 'mfn_rate',
        '进口暂定税率': 'import_provisional',
        '进口普通税率': 'import_general',
        '消费税率': 'consumption_rate',
    }
    for label, field in tax_fields.items():
        m = re.search(
            rf'<td[^>]*>\s*{re.escape(label)}\s*</td>\s*<td[^>]*>(.*?)</td>',
            html, re.DOTALL,
        )
        if m:
            rates[field] = _strip_tags(m.group(1))
    return rates


def _strip_tags(text):
    return re.sub(r'<[^>]+>', '', text).strip()


CHAPTER_NAMES = {
    '01': '活动物', '02': '肉及食用杂碎', '03': '鱼等', '04': '乳品等',
    '05': '其他动物产品', '06': '活树等', '07': '食用蔬菜', '08': '食用水果',
    '09': '咖啡、茶等', '10': '谷物', '11': '制粉工业产品', '12': '含油子仁等',
    '13': '虫胶等', '14': '编结用植物材料', '15': '动植物油脂', '16': '肉鱼制品',
    '17': '糖及糖食', '18': '可可制品', '19': '谷物制品', '20': '蔬菜水果制品',
    '21': '杂项食品', '22': '饮料、酒', '23': '食品工业残渣', '24': '烟草',
    '25': '盐等', '26': '矿砂', '27': '矿物燃料', '28': '无机化学品',
    '29': '有机化合物', '30': '药品', '31': '肥料', '32': '鞣料染料',
    '33': '精油化妆品', '34': '肥皂洗涤剂', '35': '蛋白类物质', '36': '炸药',
    '37': '照相用品', '38': '杂项化学产品', '39': '塑料及其制品',
    '40': '橡胶及其制品', '41': '生皮皮革', '42': '皮革制品',
    '43': '毛皮制品', '44': '木及木制品', '45': '软木制品',
    '46': '稻草编结品', '47': '木浆', '48': '纸及纸板',
    '49': '印刷品', '50': '蚕丝', '51': '羊毛', '52': '棉花',
    '53': '其他植物纺织纤维', '54': '化学纤维长丝', '55': '化学纤维短纤',
    '56': '絮胎毡呢', '57': '地毯', '58': '特种机织物',
    '59': '浸渍纺织物', '60': '针织物', '61': '针织服装',
    '62': '非针织服装', '63': '其他纺织品', '64': '鞋靴',
    '65': '帽类', '66': '雨伞', '67': '羽毛制品',
    '68': '石料制品', '69': '陶瓷产品', '70': '玻璃及其制品',
    '71': '珠宝贵金属', '72': '钢铁', '73': '钢铁制品',
    '74': '铜及其制品', '75': '镍及其制品', '76': '铝及其制品',
    '78': '铅及其制品', '79': '锌及其制品', '80': '锡及其制品',
    '81': '其他贱金属', '82': '贱金属工具', '83': '贱金属杂项',
    '84': '核反应堆、锅炉、机器', '85': '电机、电气设备',
    '86': '铁道车辆', '87': '车辆', '88': '航空器',
    '89': '船舶', '90': '光学精密仪器', '91': '钟表',
    '92': '乐器', '93': '武器弹药', '94': '家具灯具',
    '95': '玩具运动品', '96': '杂项制品', '97': '艺术品收藏品',
    '98': '特殊交易品',
}


class Command(BaseCommand):
    help = '从 hsbianma.com 爬取 HS 编码数据'

    def add_arguments(self, parser):
        parser.add_argument(
            '--chapter',
            type=str,
            default=None,
            help='指定章节，逗号分隔（如 84,85）。不指定则爬取全部 01-98 章',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='仅显示获取到的数据，不写入数据库',
        )
        parser.add_argument(
            '--filter-expired',
            action='store_true',
            help='跳过已过期的编码',
        )
        parser.add_argument(
            '--with-tax',
            action='store_true',
            help='抓取每个编码的详情页以获取税率信息（速度较慢）',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        filter_expired = options['filter_expired']
        with_tax = options['with_tax']
        chapter_arg = options.get('chapter')

        if chapter_arg:
            chapters = [c.strip() for c in chapter_arg.split(',')]
        else:
            chapters = [f'{i:02d}' for i in range(1, 99)]

        total_created = 0
        total_updated = 0
        total_skipped = 0

        for chapter in chapters:
            ch_name = CHAPTER_NAMES.get(chapter, '')
            self.stdout.write(f'\n第 {chapter} 章 - {ch_name}')

            try:
                rows = fetch_chapter(chapter)
            except Exception as e:
                self.stderr.write(self.style.ERROR(f'  抓取失败: {e}'))
                continue

            self.stdout.write(f'  获取到 {len(rows)} 条记录')

            if filter_expired:
                before = len(rows)
                rows = [r for r in rows if not r['is_expired']]
                skipped = before - len(rows)
                if skipped:
                    self.stdout.write(f'  过滤过期编码 {skipped} 条')

            if not rows:
                self.stdout.write(self.style.WARNING('  无有效数据'))
                continue

            if dry_run:
                for row in rows[:5]:
                    expired_tag = ' [过期]' if row['is_expired'] else ''
                    self.stdout.write(
                        f"  {row['code']}  {row['name']}{expired_tag}"
                    )
                if len(rows) > 5:
                    self.stdout.write(f'  ... 还有 {len(rows) - 5} 条')
                continue

            created = 0
            updated = 0
            skipped = 0

            with transaction.atomic():
                for row in rows:
                    code = row['code']
                    if not code:
                        skipped += 1
                        continue

                    defaults = {
                        'name': row['name'],
                        'unit': row['unit'],
                        'rebate_rate': row['rebate_rate'],
                        'supervision': row['supervision'],
                        'inspection': row['inspection'],
                        'chapter': chapter,
                        'is_expired': row['is_expired'],
                    }

                    if with_tax:
                        tax = fetch_detail(code)
                        defaults.update(tax)
                        time.sleep(0.8)

                    _, is_new = HSCode.objects.update_or_create(
                        code=code,
                        defaults=defaults,
                    )
                    if is_new:
                        created += 1
                    else:
                        updated += 1

            self.stdout.write(self.style.SUCCESS(
                f'  新增 {created}，更新 {updated}'
            ))
            total_created += created
            total_updated += updated
            total_skipped += skipped

            time.sleep(REQUEST_DELAY)

        if not dry_run:
            self.stdout.write(self.style.SUCCESS(
                f'\n同步完成: 新增 {total_created}，更新 {total_updated}，跳过 {total_skipped}'
            ))
