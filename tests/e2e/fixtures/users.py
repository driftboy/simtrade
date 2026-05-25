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
    """创建 10 个角色用户和对应公司，返回 {role_code: user} 字典"""
    china, _ = Country.objects.get_or_create(
        code='CN',
        defaults={'name': '中国', 'name_en': 'China'},
    )
    users = {}
    for role_code, company_name in ROLE_COMPANY_NAMES.items():
        company = Company.objects.create(
            name=company_name,
            name_en=f'Test {role_code.title()} Co.',
            code=f'TEST_{role_code.upper()}',
            type='trade',
            country=china,
        )
        trade_role = TradeRole.objects.get(role_type=role_code)
        user = User.objects.create_user(
            username=f'e2e_{role_code}',
            password='testpass123',
            email=f'{role_code}@e2e.test',
            user_type='student',
        )
        ucr = UserCompanyRole.objects.create(
            user=user,
            company=company,
            role=trade_role,
            status='approved',
        )
        ucr.activate()
        users[role_code] = user
    return users


def get_or_create_test_users():
    """获取或创建测试用户（幂等）"""
    existing = {}
    for role_code in ROLE_COMPANY_NAMES:
        try:
            user = User.objects.get(username=f'e2e_{role_code}')
            existing[role_code] = user
        except User.DoesNotExist:
            return create_test_users()
    if len(existing) == 10:
        return existing
    return create_test_users()
