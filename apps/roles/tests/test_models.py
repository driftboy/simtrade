import pytest
from apps.roles.models import Company
from apps.core.models import Country


@pytest.mark.django_db
def test_create_company():
    """测试创建公司"""
    country = Country.objects.first()
    company = Company.objects.create(
        name='测试外贸公司',
        name_en='Test Trading Co.',
        code='TEST001',
        type='进出口公司',
        country=country,
        address='上海市浦东新区',
        phone='021-12345678',
        email='test@example.com'
    )

    assert company.name == '测试外贸公司'
    assert company.code == 'TEST001'
    assert str(company) == '测试外贸公司'


@pytest.mark.django_db
def test_company_code_unique():
    """测试公司代码唯一性"""
    country = Country.objects.first()
    Company.objects.create(
        name='公司1',
        code='UNIQUE001',
        country=country
    )

    with pytest.raises(Exception):  # IntegrityError
        Company.objects.create(
            name='公司2',
            code='UNIQUE001',
            country=country
        )
