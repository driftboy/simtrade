"""tests/e2e/fixtures/users.py — 创建 10 个角色的测试用户和公司"""

from apps.users.models import User
from apps.roles.models import Company, TradeRole, UserCompanyRole
from apps.core.models import Country


ROLE_COMPANY_NAMES = {
    'importer': '测试进口公司',
    'exporter': '测试出口公司',
    'factory': '测试工厂',
    'bank': '测试银行',
    'shipping': '测试货运公司',
    'insurance': '测试保险公司',
    'inspection': '测试商检机构',
    'customs': '测试海关',
    'forex': '测试外汇局',
    'tax': '测试税务局',
}


def create_test_users():
    """创建 10 个角色用户和对应公司（幂等，用 get_or_create）"""
    china, _ = Country.objects.get_or_create(
        code='CN',
        defaults={'name': '中国', 'name_en': 'China'},
    )
    users = {}
    for role_code, company_name in ROLE_COMPANY_NAMES.items():
        company, _ = Company.objects.get_or_create(
            code=f'TEST_{role_code.upper()}',
            defaults={
                'name': company_name,
                'name_en': f'Test {role_code.title()} Co.',
                'type': 'trade',
                'country': china,
            },
        )
        trade_role = TradeRole.objects.get(code=role_code)
        user, _ = User.objects.get_or_create(
            username=f'e2e_{role_code}',
            defaults={
                'password': 'testpass123',
                'email': f'{role_code}@e2e.test',
                'user_type': 'student',
            },
        )
        user.set_password('testpass123')
        user.save()
        UserCompanyRole.objects.get_or_create(
            user=user,
            company=company,
            role=trade_role,
            defaults={
                'status': 'approved',
                'is_active': True,
            },
        )
        users[role_code] = user
    return users


def get_or_create_test_users():
    return create_test_users()
