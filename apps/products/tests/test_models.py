import pytest
from apps.products.models import Product, Catalog
from apps.roles.models import Company
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
def test_create_product():
    product = Product.objects.create(
        code='ELEC001',
        name='电子产品 A',
        category='electronics',
        unit='PCS'
    )
    assert product.code == 'ELEC001'
    assert product.name == '电子产品 A'
    assert product.get_category_display() == '电子产品'


@pytest.mark.django_db
def test_catalog_with_company():
    user = User.objects.create_user(username='owner', email='owner@test.com', password='testpass')
    product = Product.objects.create(code='P001', name='蓝牙耳机', category='electronics', unit='PCS')
    company = Company.objects.create(name='测试公司', code='COMP_TEST01', created_by=user)
    catalog = Catalog.objects.create(
        product=product, company=company,
        sale_price=100.00, currency='USD'
    )
    assert catalog.company == company
    assert catalog.product == product


@pytest.mark.django_db
def test_catalog_unique_together():
    user = User.objects.create_user(username='owner2', email='owner2@test.com', password='testpass')
    product = Product.objects.create(code='P002', name='手机', category='electronics', unit='PCS')
    company = Company.objects.create(name='测试公司2', code='COMP_TEST02', created_by=user)
    Catalog.objects.create(product=product, company=company, sale_price=500.00)

    with pytest.raises(Exception):
        Catalog.objects.create(product=product, company=company, sale_price=600.00)
