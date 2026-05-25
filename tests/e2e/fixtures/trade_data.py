"""tests/e2e/fixtures/trade_data.py — 测试贸易数据"""

from apps.products.models import Product


def create_test_product(factory_user):
    """创建测试产品，返回 Product 实例"""
    ucr = factory_user.usercompanyrole_set.filter(status='active').first()
    company = ucr.company
    product = Product.objects.create(
        name='测试商品-电子元器件',
        name_en='Test Electronic Components',
        hs_code='8542390000',
        category='electronics',
        description='用于 E2E 测试的标准商品',
        unit='piece',
        unit_price=100.00,
        currency='USD',
        company=company,
        min_order_quantity=10,
        stock_quantity=10000,
    )
    return product
