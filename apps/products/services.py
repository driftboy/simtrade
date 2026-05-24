from apps.products.models import Product, Catalog
from apps.roles.models import Company


class ProductService:
    @staticmethod
    def search_products(keyword='', category=''):
        qs = Product.objects.filter(is_active=True)
        if keyword:
            qs = qs.filter(name__icontains=keyword)
        if category:
            qs = qs.filter(category=category)
        return qs


class CatalogService:
    @staticmethod
    def get_catalog_for_company(company_id):
        return Catalog.objects.filter(company_id=company_id, is_available=True).select_related('product')

    @staticmethod
    def add_to_catalog(company_id, product_id, sale_price, **kwargs):
        company = Company.objects.get(id=company_id)
        product = Product.objects.get(id=product_id)
        return Catalog.objects.create(
            company=company, product=product,
            sale_price=sale_price, **kwargs
        )

    @staticmethod
    def remove_from_catalog(catalog_id, user):
        catalog = Catalog.objects.get(id=catalog_id)
        catalog.delete()
        return True
