from decimal import Decimal
from django.core.management.base import BaseCommand
from apps.scoring.models import ScoringMetric
from apps.roles.models import TradeRole


class Command(BaseCommand):
    help = '初始化评分指标数据'

    def handle(self, *args, **options):
        roles = {r.code: r for r in TradeRole.objects.all()}

        metrics_data = [
            # 财务表现
            {
                'name': 'profit_margin',
                'display_name': '利润率',
                'dimension': 'financial',
                'calculation_method': 'profit_margin',
                'weight': Decimal('20'),
                'config': {'threshold_high': 20, 'threshold_low': 0},
                'roles': ['exporter', 'importer'],
            },
            {
                'name': 'cost_control',
                'display_name': '成本控制',
                'dimension': 'financial',
                'calculation_method': 'cost_control',
                'weight': Decimal('15'),
                'config': {'benchmark_deviation_pct': 5},
                'roles': ['exporter', 'importer'],
            },
            # 业务准确度
            {
                'name': 'document_accuracy',
                'display_name': '单证准确率',
                'dimension': 'accuracy',
                'calculation_method': 'document_accuracy',
                'weight': Decimal('15'),
                'config': {},
                'roles': ['exporter', 'importer'],
            },
            {
                'name': 'first_pass_rate',
                'display_name': '首次通过率',
                'dimension': 'accuracy',
                'calculation_method': 'first_pass_rate',
                'weight': Decimal('30'),
                'config': {},
                'roles': ['bank', 'customs', 'inspection', 'forex', 'tax'],
            },
            # 操作效率
            {
                'name': 'trade_cycle_time',
                'display_name': '交易周期',
                'dimension': 'efficiency',
                'calculation_method': 'trade_cycle_time',
                'weight': Decimal('15'),
                'config': {'benchmark_minutes': 1440, 'max_minutes': 2880},
                'roles': ['exporter', 'importer'],
            },
            {
                'name': 'document_turnaround',
                'display_name': '单证处理速度',
                'dimension': 'efficiency',
                'calculation_method': 'document_turnaround',
                'weight': Decimal('10'),
                'config': {'benchmark_minutes': 60, 'max_minutes': 120},
                'roles': ['exporter', 'importer'],
            },
            {
                'name': 'response_time',
                'display_name': '响应速度',
                'dimension': 'efficiency',
                'calculation_method': 'response_time',
                'weight': Decimal('10'),
                'config': {'benchmark_minutes': 30, 'max_minutes': 60},
                'roles': ['exporter', 'importer'],
            },
            {
                'name': 'processing_speed',
                'display_name': '处理速度',
                'dimension': 'efficiency',
                'calculation_method': 'processing_speed',
                'weight': Decimal('40'),
                'config': {'benchmark_minutes': 120, 'max_minutes': 240},
                'roles': ['factory', 'bank', 'customs', 'shipping', 'insurance', 'inspection', 'forex', 'tax'],
            },
            {
                'name': 'completion_rate',
                'display_name': '完成率',
                'dimension': 'efficiency',
                'calculation_method': 'completion_rate',
                'weight': Decimal('30'),
                'config': {},
                'roles': ['factory', 'shipping'],
            },
            # 谈判能力
            {
                'name': 'negotiation_efficiency',
                'display_name': '谈判效率',
                'dimension': 'negotiation',
                'calculation_method': 'negotiation_efficiency',
                'weight': Decimal('15'),
                'config': {'max_rounds': 5},
                'roles': ['exporter', 'importer'],
            },
        ]

        created_count = 0
        updated_count = 0
        for data in metrics_data:
            role_codes = data.pop('roles')
            metric, created = ScoringMetric.objects.update_or_create(
                name=data['name'],
                defaults=data,
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'[CREATE] {metric.display_name}'))
            else:
                updated_count += 1
                self.stdout.write(self.style.WARNING(f'[UPDATE] {metric.display_name}'))

            applicable_roles = [roles[c] for c in role_codes if c in roles]
            metric.applicable_roles.set(applicable_roles)

        self.stdout.write(
            self.style.SUCCESS(
                f'\n完成: 新建 {created_count} 个, 更新 {updated_count} 个指标'
            )
        )
