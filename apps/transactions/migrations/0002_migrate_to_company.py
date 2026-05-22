# Generated migration for migrating User foreign keys to Company

from django.db import migrations, models
import django.db.models.deletion


def create_companies_for_users(apps, schema_editor):
    """为每个用户创建默认公司"""
    User = apps.get_model('users', 'User')
    Company = apps.get_model('roles', 'Company')

    for user in User.objects.all():
        code = f'USER_{user.id:04d}'
        Company.objects.get_or_create(
            code=code,
            defaults={
                'name': f'{user.username}的公司',
                'type': 'trading',
                'created_by_id': user.id
            }
        )


def migrate_user_to_company(apps, schema_editor):
    """将用户外键迁移到公司外键（使用新添加的临时字段）"""
    User = apps.get_model('users', 'User')
    Company = apps.get_model('roles', 'Company')
    Transaction = apps.get_model('transactions', 'Transaction')
    LetterOfCredit = apps.get_model('transactions', 'LetterOfCredit')

    # 迁移 Transaction 数据
    for transaction in Transaction.objects.all():
        # 旧的 buyer_id 是 user_id，将其映射到对应的公司
        old_buyer_id = transaction.buyer_id
        old_seller_id = transaction.seller_id

        buyer_company = Company.objects.filter(code=f'USER_{old_buyer_id:04d}').first()
        seller_company = Company.objects.filter(code=f'USER_{old_seller_id:04d}').first()

        # 将数据写入新的临时字段
        if buyer_company:
            transaction.buyer_company_id = buyer_company.id
        if seller_company:
            transaction.seller_company_id = seller_company.id

        transaction.save(update_fields=['buyer_company_id', 'seller_company_id'])

    # 迁移 LetterOfCredit 数据
    for lc in LetterOfCredit.objects.all():
        old_applicant_id = lc.applicant_id
        old_beneficiary_id = lc.beneficiary_id

        applicant_company = Company.objects.filter(code=f'USER_{old_applicant_id:04d}').first()
        beneficiary_company = Company.objects.filter(code=f'USER_{old_beneficiary_id:04d}').first()

        if applicant_company:
            lc.applicant_company_id = applicant_company.id
        if beneficiary_company:
            lc.beneficiary_company_id = beneficiary_company.id

        lc.save(update_fields=['applicant_company_id', 'beneficiary_company_id'])


def reverse_migrate(apps, schema_editor):
    """回滚操作（保留数据结构，但可能丢失关联）"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('roles', '0003_usercompanyrole'),
        ('transactions', '0001_initial'),
    ]

    operations = [
        # 步骤 1: 为所有用户创建公司
        migrations.RunPython(create_companies_for_users, reverse_code=migrations.RunPython.noop),
        # 步骤 2: 添加新的 Company 外键临时字段
        migrations.AddField(
            model_name='transaction',
            name='buyer_company',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='buying_transactions_temp', to='roles.company'),
        ),
        migrations.AddField(
            model_name='transaction',
            name='seller_company',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='selling_transactions_temp', to='roles.company'),
        ),
        migrations.AddField(
            model_name='letterofcredit',
            name='applicant_company',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='applied_letters_of_credit_temp', to='roles.company'),
        ),
        migrations.AddField(
            model_name='letterofcredit',
            name='beneficiary_company',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='beneficiary_letters_of_credit_temp', to='roles.company'),
        ),
        # 步骤 3: 数据迁移
        migrations.RunPython(migrate_user_to_company, reverse_code=reverse_migrate),
        # 步骤 4: 删除旧字段
        migrations.RemoveField(
            model_name='transaction',
            name='buyer',
        ),
        migrations.RemoveField(
            model_name='transaction',
            name='seller',
        ),
        migrations.RemoveField(
            model_name='letterofcredit',
            name='applicant',
        ),
        migrations.RemoveField(
            model_name='letterofcredit',
            name='beneficiary',
        ),
        # 步骤 5: 重命名新字段为原字段名
        migrations.RenameField(
            model_name='transaction',
            old_name='buyer_company',
            new_name='buyer',
        ),
        migrations.RenameField(
            model_name='transaction',
            old_name='seller_company',
            new_name='seller',
        ),
        migrations.RenameField(
            model_name='letterofcredit',
            old_name='applicant_company',
            new_name='applicant',
        ),
        migrations.RenameField(
            model_name='letterofcredit',
            old_name='beneficiary_company',
            new_name='beneficiary',
        ),
        # 步骤 6: 更新 related_name 和约束（Transaction 字段）
        migrations.AlterField(
            model_name='transaction',
            name='buyer',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='buying_transactions', to='roles.company'),
        ),
        migrations.AlterField(
            model_name='transaction',
            name='seller',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='selling_transactions', to='roles.company'),
        ),
        # 步骤 7: 更新 related_name 和约束（LetterOfCredit 字段）
        migrations.AlterField(
            model_name='letterofcredit',
            name='applicant',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='applied_letters_of_credit', to='roles.company'),
        ),
        migrations.AlterField(
            model_name='letterofcredit',
            name='beneficiary',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='beneficiary_letters_of_credit', to='roles.company'),
        ),
    ]
