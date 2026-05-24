import pytest
from django.contrib.auth import get_user_model
from apps.products.models import Product, Catalog
from apps.products.services import ProductService, CatalogService
from apps.roles.models import Company

User = get_user_model()


@pytest.fixture
def setup_data(db):
    user = User.objects.create_user(username='testuser', email='testuser@test.com', password='testpass')
    company = Company.objects.create(name='测试贸易公司', code='COMP_SVC01', created_by=user)
    p1 = Product.objects.create(code='E001', name='蓝牙耳机', category='electronics', unit='PCS')
    p2 = Product.objects.create(code='T001', name='纯棉T恤', category='textiles', unit='PCS')
    return {'user': user, 'company': company, 'p1': p1, 'p2': p2}


def test_search_products_by_keyword(setup_data):
    results = ProductService.search_products(keyword='蓝牙')
    assert len(results) == 1
    assert results[0].name == '蓝牙耳机'


def test_search_products_by_category(setup_data):
    results = ProductService.search_products(category='electronics')
    assert len(results) == 1


def test_get_catalog_for_company(setup_data):
    Catalog.objects.create(product=setup_data['p1'], company=setup_data['company'], sale_price=50.00)
    results = CatalogService.get_catalog_for_company(setup_data['company'].id)
    assert len(results) == 1


def test_add_to_catalog(setup_data):
    catalog = CatalogService.add_to_catalog(
        company_id=setup_data['company'].id,
        product_id=setup_data['p1'].id,
        sale_price=99.99,
        currency='USD'
    )
    assert catalog.sale_price == 99.99
    assert catalog.company == setup_data['company']


def test_remove_from_catalog(setup_data):
    catalog = CatalogService.add_to_catalog(
        company_id=setup_data['company'].id,
        product_id=setup_data['p1'].id,
        sale_price=50.00
    )
    assert CatalogService.remove_from_catalog(catalog.id, setup_data['user']) is True
    assert not Catalog.objects.filter(id=catalog.id).exists()
