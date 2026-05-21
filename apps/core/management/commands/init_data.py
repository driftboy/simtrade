"""
Django management command to initialize system reference data.

This command loads:
1. Core reference data (countries, ports, currencies)
2. Default roles (STUDENT, TEACHER, ADMIN)
3. Default permissions for the RBAC system
4. Role-permission assignments
"""
from django.core.management.base import BaseCommand
from apps.users.models import Role, Permission, RolePermission
from apps.core.models import Country, Port, Currency


class Command(BaseCommand):
    help = 'Initialize system reference data and default RBAC setup'

    def handle(self, *args, **options):
        """Execute the initialization command."""
        self.stdout.write(self.style.SUCCESS('Starting system data initialization...'))

        # Step 1: Load core reference data
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write('Step 1: Loading core reference data')
        self.stdout.write('=' * 60)

        # Countries data
        countries_data = [
            ('CN', '中国', 'China', '86'),
            ('US', '美国', 'United States', '1'),
            ('JP', '日本', 'Japan', '81'),
            ('GB', '英国', 'United Kingdom', '44'),
            ('DE', '德国', 'Germany', '49'),
            ('FR', '法国', 'France', '33'),
            ('KR', '韩国', 'South Korea', '82'),
            ('SG', '新加坡', 'Singapore', '65'),
            ('AU', '澳大利亚', 'Australia', '61'),
        ]

        for code, name, name_en, phone_code in countries_data:
            country, created = Country.objects.get_or_create(
                code=code,
                defaults={
                    'name': name,
                    'name_en': name_en,
                    'phone_code': phone_code,
                    'is_active': True
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'  [OK] Created country: {name}'))

        # Ports data
        ports_data = [
            ('CNSHA', '上海港', 'Shanghai', 'CN'),
            ('CNNGB', '宁波港', 'Ningbo', 'CN'),
            ('CNSZX', '深圳港', 'Shenzhen', 'CN'),
            ('CNQDG', '青岛港', 'Qingdao', 'CN'),
            ('CNTAO', '天津港', 'Tianjin', 'CN'),
            ('CNXMN', '厦门港', 'Xiamen', 'CN'),
            ('USLAX', '洛杉矶港', 'Los Angeles', 'US'),
            ('USNYC', '纽约港', 'New York', 'US'),
            ('JPTYO', '东京港', 'Tokyo', 'JP'),
            ('JPOSA', '大阪港', 'Osaka', 'JP'),
            ('GBSOU', '南安普顿港', 'Southampton', 'GB'),
            ('DEHAM', '汉堡港', 'Hamburg', 'DE'),
            ('FRMLE', '勒阿弗尔港', 'Le Havre', 'FR'),
            ('KRPUS', '釜山港', 'Busan', 'KR'),
            ('SGSIN', '新加坡港', 'Singapore', 'SG'),
            ('AUSYD', '悉尼港', 'Sydney', 'AU'),
        ]

        for code, name, name_en, country_code in ports_data:
            try:
                country = Country.objects.get(pk=country_code)
                port, created = Port.objects.get_or_create(
                    code=code,
                    defaults={
                        'name': name,
                        'name_en': name_en,
                        'country': country,
                        'is_active': True
                    }
                )
                if created:
                    self.stdout.write(self.style.SUCCESS(f'  [OK] Created port: {name}'))
            except Country.DoesNotExist:
                self.stdout.write(self.style.WARNING(f'  [WARN] Country {country_code} not found for port {name}'))

        # Currencies data
        currencies_data = [
            ('CNY', '人民币', 'Chinese Yuan', '¥'),
            ('USD', '美元', 'US Dollar', '$'),
            ('EUR', '欧元', 'Euro', '€'),
            ('GBP', '英镑', 'British Pound', '£'),
            ('JPY', '日元', 'Japanese Yen', '¥'),
            ('KRW', '韩元', 'Korean Won', '₩'),
            ('SGD', '新加坡元', 'Singapore Dollar', 'S$'),
            ('AUD', '澳元', 'Australian Dollar', 'A$'),
            ('HKD', '港币', 'Hong Kong Dollar', 'HK$'),
        ]

        for code, name, name_en, symbol in currencies_data:
            currency, created = Currency.objects.get_or_create(
                code=code,
                defaults={
                    'name': name,
                    'name_en': name_en,
                    'symbol': symbol,
                    'is_active': True
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'  [OK] Created currency: {name}'))

        # Step 2: Create default roles
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write('Step 2: Creating default roles')
        self.stdout.write('=' * 60)

        roles_data = [
            ('STUDENT', '学生', '可以创建自己的交易和单证'),
            ('TEACHER', '教师', '可以管理班级的课程和学生'),
            ('ADMIN', '管理员', '拥有所有权限'),
        ]

        for code, name, desc in roles_data:
            role, created = Role.objects.get_or_create(
                code=code,
                defaults={'name': name, 'description': desc}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'  [OK] Created role: {name}'))
            else:
                self.stdout.write(self.style.NOTICE(f'  [SKIP] Role already exists: {name}'))

        # Step 3: Create default permissions
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write('Step 3: Creating default permissions')
        self.stdout.write('=' * 60)

        permissions_data = [
            # Transaction permissions
            ('transaction', 'create', 'self'),
            ('transaction', 'read', 'self'),
            ('transaction', 'update', 'self'),
            ('transaction', 'delete', 'self'),
            # Document permissions
            ('document', 'create', 'self'),
            ('document', 'read', 'self'),
            ('document', 'update', 'self'),
            ('document', 'delete', 'self'),
            ('document', 'approve', 'class'),
            # Course permissions
            ('course', 'create', 'all'),
            ('course', 'read', 'all'),
            ('course', 'update', 'all'),
            ('course', 'delete', 'all'),
            # Score permissions
            ('score', 'read', 'all'),
            ('score', 'update', 'all'),
            # User permissions
            ('user', 'read', 'class'),
            # System config permissions
            ('system_config', 'read', 'all'),
        ]

        for resource, action, scope in permissions_data:
            perm, created = Permission.objects.get_or_create(
                resource=resource,
                action=action,
                scope=scope
            )
            if created:
                self.stdout.write(self.style.SUCCESS(
                    f'  [OK] Created permission: {resource}.{action}.{scope}'
                ))

        # Step 4: Assign permissions to roles
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write('Step 4: Assigning permissions to roles')
        self.stdout.write('=' * 60)

        student_role = Role.objects.get(code='STUDENT')
        teacher_role = Role.objects.get(code='TEACHER')
        admin_role = Role.objects.get(code='ADMIN')

        # Student permissions
        student_permissions = [
            ('transaction', 'create', 'self'),
            ('transaction', 'read', 'self'),
            ('transaction', 'update', 'self'),
            ('document', 'create', 'self'),
            ('document', 'read', 'self'),
            ('document', 'update', 'self'),
            ('course', 'read', 'all'),
        ]

        for resource, action, scope in student_permissions:
            try:
                perm = Permission.objects.get(resource=resource, action=action, scope=scope)
                RolePermission.objects.get_or_create(role=student_role, permission=perm)
            except Permission.DoesNotExist:
                pass

        self.stdout.write(self.style.SUCCESS('  [OK] Student permissions assigned'))

        # Teacher permissions
        teacher_permissions = [
            ('transaction', 'read', 'class'),
            ('transaction', 'update', 'class'),
            ('document', 'approve', 'class'),
            ('course', 'create', 'all'),
            ('course', 'read', 'all'),
            ('course', 'update', 'all'),
            ('score', 'read', 'all'),
            ('score', 'update', 'all'),
            ('user', 'read', 'class'),
        ]

        for resource, action, scope in teacher_permissions:
            try:
                perm = Permission.objects.get(resource=resource, action=action, scope=scope)
                RolePermission.objects.get_or_create(role=teacher_role, permission=perm)
            except Permission.DoesNotExist:
                pass

        self.stdout.write(self.style.SUCCESS('  [OK] Teacher permissions assigned'))

        # Admin permissions (all permissions)
        all_permissions = Permission.objects.all()
        for perm in all_permissions:
            RolePermission.objects.get_or_create(role=admin_role, permission=perm)

        self.stdout.write(self.style.SUCCESS('  [OK] Admin permissions assigned'))

        # Summary
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('System data initialization completed[WARN]'))
        self.stdout.write('=' * 60)
        self.stdout.write(f'  Countries: {Country.objects.count()}')
        self.stdout.write(f'  Ports: {Port.objects.count()}')
        self.stdout.write(f'  Currencies: {Currency.objects.count()}')
        self.stdout.write(f'  Roles: {Role.objects.count()}')
        self.stdout.write(f'  Permissions: {Permission.objects.count()}')
        self.stdout.write(f'  Role-Permission mappings: {RolePermission.objects.count()}')
