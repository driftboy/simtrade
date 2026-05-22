from django.core.management.base import BaseCommand
from apps.roles.models import TradeRole


class Command(BaseCommand):
    help = '初始化 10 种贸易角色数据'

    def handle(self, *args, **options):
        """创建或更新 10 种贸易角色"""

        # 定义 10 种角色数据
        roles_data = [
            {
                'code': TradeRole.RoleType.EXPORTER,
                'name': '出口商',
                'description': '销售货物到国外，负责制作单证、安排运输、办理报关等出口业务。',
                'sort_order': 1,
            },
            {
                'code': TradeRole.RoleType.IMPORTER,
                'name': '进口商',
                'description': '从国外购买货物，负责开立信用证、办理进口报关、支付货款等进口业务。',
                'sort_order': 2,
            },
            {
                'code': TradeRole.RoleType.FACTORY,
                'name': '工厂',
                'description': '生产/供应商品，接收出口商订单，安排生产、备货、发货，开具增值税发票。',
                'sort_order': 3,
            },
            {
                'code': TradeRole.RoleType.BANK,
                'name': '银行',
                'description': '处理信用证开立、通知、议付、付款等银行业务，提供结算服务。',
                'sort_order': 4,
            },
            {
                'code': TradeRole.RoleType.CUSTOMS,
                'name': '海关',
                'description': '审核报关单据，征收关税，查验货物，办理放行手续。',
                'sort_order': 5,
            },
            {
                'code': TradeRole.RoleType.SHIPPING,
                'name': '货运公司',
                'description': '提供订舱、运输服务，签发提单，安排货物装运和运输。',
                'sort_order': 6,
            },
            {
                'code': TradeRole.RoleType.INSURANCE,
                'name': '保险公司',
                'description': '提供货物运输保险服务，审核投保单，签发保险单，处理理赔。',
                'sort_order': 7,
            },
            {
                'code': TradeRole.RoleType.INSPECTION,
                'name': '商检机构',
                'description': '对出口商品进行检验检疫，签发检验证书、产地证等。',
                'sort_order': 8,
            },
            {
                'code': TradeRole.RoleType.FOREX,
                'name': '外汇局',
                'description': '管理出口收汇核销，审核外汇收支，办理核销手续。',
                'sort_order': 9,
            },
            {
                'code': TradeRole.RoleType.TAX,
                'name': '税务局',
                'description': '审核出口退税申请，办理退税手续，管理退税资金。',
                'sort_order': 10,
            },
        ]

        created_count = 0
        updated_count = 0

        for role_data in roles_data:
            code = role_data['code']
            role, created = TradeRole.objects.get_or_create(
                code=code,
                defaults={
                    'name': role_data['name'],
                    'description': role_data['description'],
                    'sort_order': role_data['sort_order'],
                    'is_enabled': True,
                    'is_system': True,
                }
            )

            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'  [CREATE] {role.name} ({code})')
                )
            else:
                # 更新现有角色（保持 is_enabled 和 is_system 不变）
                role.name = role_data['name']
                role.description = role_data['description']
                role.sort_order = role_data['sort_order']
                role.save()
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'  [UPDATE] {role.name} ({code})')
                )

        # 输出汇总
        self.stdout.write('\n--- 汇总 ---')
        self.stdout.write(f'  新建角色: {created_count}')
        self.stdout.write(f'  更新角色: {updated_count}')
        self.stdout.write(f'  总计角色: {created_count + updated_count}')

        if created_count + updated_count == 10:
            self.stdout.write(
                self.style.SUCCESS('\n初始化完成！全部 10 种贸易角色已就绪。')
            )
        else:
            self.stdout.write(
                self.style.ERROR('\n警告：角色数量不正确，预期 10 个！')
            )
