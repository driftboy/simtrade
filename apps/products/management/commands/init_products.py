from django.core.management.base import BaseCommand
from apps.products.models import Product


class Command(BaseCommand):
    help = '初始化商品种子数据'

    PRODUCTS_DATA = [
        {'code': 'E001', 'name': '蓝牙耳机', 'name_en': 'Bluetooth Earphone', 'category': 'electronics', 'unit': 'PCS', 'hs_code': '85183000', 'description': '无线蓝牙5.0耳机，降噪功能'},
        {'code': 'E002', 'name': '智能手机', 'name_en': 'Smartphone', 'category': 'electronics', 'unit': 'PCS', 'hs_code': '85171200', 'description': '6.5寸屏幕，128GB存储'},
        {'code': 'T001', 'name': '纯棉T恤', 'name_en': 'Cotton T-Shirt', 'category': 'textiles', 'unit': 'PCS', 'hs_code': '61091000', 'description': '100%纯棉，圆领短袖'},
        {'code': 'T002', 'name': '牛仔布', 'name_en': 'Denim Fabric', 'category': 'textiles', 'unit': 'METER', 'hs_code': '52094200', 'description': '靛蓝染色牛仔面料'},
        {'code': 'M001', 'name': '数控机床', 'name_en': 'CNC Machine', 'category': 'machinery', 'unit': 'SET', 'hs_code': '84581100', 'description': '三轴数控车床'},
        {'code': 'M002', 'name': '柴油发电机', 'name_en': 'Diesel Generator', 'category': 'machinery', 'unit': 'SET', 'hs_code': '85021100', 'description': '500KW柴油发电机组'},
        {'code': 'C001', 'name': '工业酒精', 'name_en': 'Industrial Alcohol', 'category': 'chemicals', 'unit': 'KG', 'hs_code': '22071000', 'description': '95%乙醇，工业级'},
        {'code': 'C002', 'name': '建筑涂料', 'name_en': 'Building Paint', 'category': 'chemicals', 'unit': 'BARREL', 'hs_code': '32091000', 'description': '水性内墙乳胶漆'},
        {'code': 'F001', 'name': '绿茶', 'name_en': 'Green Tea', 'category': 'food', 'unit': 'KG', 'hs_code': '09021000', 'description': '有机龙井绿茶'},
        {'code': 'F002', 'name': '午餐肉罐头', 'name_en': 'Canned Luncheon Meat', 'category': 'food', 'unit': 'CASE', 'hs_code': '16024900', 'description': '340g/罐，24罐/箱'},
    ]

    def handle(self, *args, **options):
        created_count = 0
        for data in self.PRODUCTS_DATA:
            product, created = Product.objects.get_or_create(
                code=data['code'], defaults=data
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'创建商品: {product.name}'))
            else:
                self.stdout.write(self.style.WARNING(f'商品已存在: {product.name}'))

        self.stdout.write(self.style.SUCCESS(f'\n完成！创建 {created_count} 个商品。'))
