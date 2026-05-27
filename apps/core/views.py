from django.db import models as db_models
from rest_framework import status
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.models import (
    Currency, ExchangeRate,
    TradeMode, TransportMode, PackageType, UnitOfMeasure,
    CustomsDistrict, LevyMode, CustomsDoc, DomesticRegion,
)
from apps.core.management.commands.sync_exchange_rates import fetch_rates
from apps.products.models import HSCode
from apps.products.management.commands.sync_hs_codes import fetch_chapter, fetch_detail, CHAPTER_NAMES


class ExchangeRateListView(APIView):
    """获取最新汇率列表"""
    permission_classes = [IsAdminUser]

    def get(self, request):
        latest = ExchangeRate.objects.order_by('-rate_date').first()
        if not latest:
            return Response({'code': 0, 'data': [], 'rate_date': None})

        rates = ExchangeRate.objects.filter(rate_date=latest.rate_date).select_related('currency')
        data = []
        for r in rates:
            data.append({
                'id': r.id,
                'country_name': r.country_name,
                'currency_name': r.currency_name,
                'currency_code': r.currency.code if r.currency else None,
                'rate_to_usd': str(r.rate_to_usd),
                'rate_to_cny': str(r.rate_to_cny) if r.rate_to_cny else None,
                'rate_date': str(r.rate_date),
            })
        return Response({
            'code': 0,
            'data': data,
            'rate_date': str(latest.rate_date),
            'total': len(data),
        })


class ExchangeRateSyncView(APIView):
    """从商务部同步汇率"""
    permission_classes = [IsAdminUser]

    def post(self, request):
        from django.db import transaction
        from apps.core.management.commands.sync_exchange_rates import CURRENCY_MAP

        try:
            raw = fetch_rates()
        except Exception as e:
            return Response(
                {'code': 1, 'message': f'获取数据失败: {e}'},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        rows = raw.get('rows', [])
        if not rows:
            return Response(
                {'code': 1, 'message': '未获取到汇率数据'},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        from datetime import date
        from decimal import Decimal

        rate_date_str = f'{rows[0]["yyyy"]}-{rows[0]["mm"]}-{rows[0]["dd"]}'
        rate_date = date.fromisoformat(rate_date_str)

        cny_rate_to_usd = None
        for row in rows:
            if row['country_namc'] == '中国' and row['currency_namc'] == '人民币元':
                cny_rate_to_usd = float(row['exchange'])
                break

        created_rates = 0
        updated_rates = 0
        created_currencies = 0

        with transaction.atomic():
            # 去重：同种货币只保留代表国家
            seen = set()
            for row in rows:
                country = row['country_namc'].strip()
                currency_name = row['currency_namc'].strip()

                if currency_name in seen:
                    continue
                seen.add(currency_name)

                try:
                    rate_to_usd = Decimal(row['exchange'])
                except (ValueError, TypeError):
                    continue

                rate_to_cny = None
                if cny_rate_to_usd and rate_to_usd:
                    rate_to_cny = round(Decimal(str(cny_rate_to_usd)) / rate_to_usd, 6)

                # 映射到 ISO 4217
                key = (country, currency_name)
                iso_info = CURRENCY_MAP.get(key)
                if not iso_info:
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
                    updated_rates += 1

        return Response({
            'code': 0,
            'message': f'同步完成: 新增 {created_rates} 条，更新 {updated_rates} 条，新增 {created_currencies} 种货币',
            'data': {
                'rate_date': str(rate_date),
                'created_rates': created_rates,
                'updated_rates': updated_rates,
                'created_currencies': created_currencies,
            },
        })


class CustomsParamsStatsView(APIView):
    """海关参数代码表统计"""
    permission_classes = [IsAdminUser]

    TABLES = [
        ('trade_modes', TradeMode, '监管方式'),
        ('transport_modes', TransportMode, '运输方式'),
        ('package_types', PackageType, '包装种类'),
        ('units_of_measure', UnitOfMeasure, '计量单位'),
        ('customs_districts', CustomsDistrict, '关区代码'),
        ('levy_modes', LevyMode, '征减免税方式'),
        ('customs_docs', CustomsDoc, '监管证件'),
        ('domestic_regions', DomesticRegion, '国内地区'),
    ]

    def get(self, request):
        data = []
        for key, model, label in self.TABLES:
            data.append({
                'key': key,
                'label': label,
                'count': model.objects.count(),
                'active_count': model.objects.filter(is_active=True).count(),
            })
        return Response({'code': 0, 'data': data})


class CustomsParamsDetailView(APIView):
    """海关参数代码表明细"""
    permission_classes = [IsAdminUser]

    TABLE_MAP = {
        'trade_modes': (TradeMode, ['code', 'name']),
        'transport_modes': (TransportMode, ['code', 'name']),
        'package_types': (PackageType, ['code', 'name']),
        'units_of_measure': (UnitOfMeasure, ['code', 'name', 'conv_ratio', 'conv_code']),
        'customs_districts': (CustomsDistrict, ['code', 'name']),
        'levy_modes': (LevyMode, ['code', 'name']),
        'customs_docs': (CustomsDoc, ['code', 'name']),
        'domestic_regions': (DomesticRegion, ['code', 'name']),
    }

    def get(self, request):
        key = request.query_params.get('table', '')
        if key not in self.TABLE_MAP:
            return Response(
                {'code': 1, 'message': f'未知参数表: {key}'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        model, fields = self.TABLE_MAP[key]
        qs = model.objects.all().order_by('code')
        search = request.query_params.get('search', '').strip()
        if search:
            qs = qs.filter(name__icontains=search) | qs.filter(code__icontains=search)
        rows = []
        for obj in qs[:500]:
            row = {f: getattr(obj, f, '') for f in fields}
            row['is_active'] = getattr(obj, 'is_active', True)
            rows.append(row)
        return Response({'code': 0, 'data': rows, 'total': qs.count()})


class HSCodeStatsView(APIView):
    """HS 编码统计"""
    permission_classes = [IsAdminUser]

    def get(self, request):
        total = HSCode.objects.count()
        active = HSCode.objects.filter(is_expired=False).count()
        chapters = (
            HSCode.objects.values('chapter')
            .annotate(count=db_models.Count('code'))
            .order_by('chapter')
        )
        chapter_data = [
            {'chapter': c['chapter'], 'name': CHAPTER_NAMES.get(c['chapter'], ''), 'count': c['count']}
            for c in chapters
        ]
        return Response({
            'code': 0,
            'data': {
                'total': total,
                'active': active,
                'chapters': chapter_data,
            },
        })


class HSCodeSyncView(APIView):
    """按章节同步 HS 编码"""
    permission_classes = [IsAdminUser]

    def post(self, request):
        chapters = request.data.get('chapters', [])
        filter_expired = request.data.get('filter_expired', True)
        with_tax = request.data.get('with_tax', False)

        if not chapters:
            return Response(
                {'code': 1, 'message': '请选择要同步的章节'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        import time
        total_created = 0
        total_updated = 0
        errors = []

        for chapter in chapters:
            ch_name = CHAPTER_NAMES.get(chapter, '')
            try:
                rows = fetch_chapter(chapter)
            except Exception as e:
                errors.append(f'第{chapter}章({ch_name}): {e}')
                continue

            if filter_expired:
                rows = [r for r in rows if not r['is_expired']]

            created = 0
            updated = 0
            for row in rows:
                if not row['code']:
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
                    tax = fetch_detail(row['code'])
                    defaults.update(tax)
                    time.sleep(0.8)
                _, is_new = HSCode.objects.update_or_create(
                    code=row['code'],
                    defaults=defaults,
                )
                if is_new:
                    created += 1
                else:
                    updated += 1

            total_created += created
            total_updated += updated

        message = f'同步完成: 新增 {total_created}，更新 {total_updated}'
        if errors:
            message += f'，失败 {len(errors)} 章'

        return Response({
            'code': 0 if not errors else 2,
            'message': message,
            'data': {
                'created': total_created,
                'updated': total_updated,
                'errors': errors,
            },
        })


class HSCodeListView(APIView):
    """HS 编码明细列表（分页）"""
    permission_classes = [IsAdminUser]

    def get(self, request):
        qs = HSCode.objects.all().order_by('code')
        chapter = request.query_params.get('chapter', '').strip()
        if chapter:
            qs = qs.filter(chapter=chapter)
        search = request.query_params.get('search', '').strip()
        if search:
            qs = qs.filter(name__icontains=search) | qs.filter(code__icontains=search)
        total = qs.count()
        try:
            page = max(1, int(request.query_params.get('page', 1)))
        except (ValueError, TypeError):
            page = 1
        try:
            page_size = max(1, min(100, int(request.query_params.get('page_size', 5))))
        except (ValueError, TypeError):
            page_size = 5
        offset = (page - 1) * page_size
        rows = []
        for obj in qs[offset:offset + page_size]:
            rows.append({
                'code': obj.code,
                'name': obj.name,
                'unit': obj.unit,
                'rebate_rate': obj.rebate_rate,
                'supervision': obj.supervision,
                'inspection': obj.inspection,
                'chapter': obj.chapter,
                'is_expired': obj.is_expired,
                'export_rate': obj.export_rate,
                'export_provisional': obj.export_provisional,
                'vat_rate': obj.vat_rate,
                'mfn_rate': obj.mfn_rate,
                'import_provisional': obj.import_provisional,
                'import_general': obj.import_general,
                'consumption_rate': obj.consumption_rate,
            })
        return Response({
            'code': 0,
            'data': rows,
            'total': total,
            'page': page,
            'page_size': page_size,
            'total_pages': max(1, (total + page_size - 1) // page_size),
        })
