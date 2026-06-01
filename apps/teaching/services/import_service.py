"""批量导入学生服务"""
import openpyxl
from django.db import transaction
from django.utils import timezone
from django.contrib.auth import get_user_model
from apps.teaching.models import TeachingClass, StudentEnrollment, StudentProfile

User = get_user_model()


class ImportService:
    """批量导入学生服务"""

    REQUIRED_FIELDS = ['学号', '姓名']
    OPTIONAL_FIELDS = ['手机号', '邮箱', '行政班级', '年级', '初始角色']
    DEFAULT_ROLE = 'student'
    DEFAULT_PASSWORD = '123456'

    @staticmethod
    def parse_import_file(file):
        """解析 Excel 文件

        Args:
            file: 上传的文件对象

        Returns:
            list: 解析后的数据列表
        """
        try:
            workbook = openpyxl.load_workbook(file)
            sheet = workbook.active

            data = []
            headers = None

            for row_idx, row in enumerate(sheet.iter_rows(values_only=True), 1):
                if row_idx == 1:
                    headers = [str(cell) if cell is not None else '' for cell in row]
                    continue

                if not any(row):
                    continue

                row_data = {}
                for col_idx, value in enumerate(row):
                    if col_idx < len(headers) and value is not None:
                        row_data[headers[col_idx]] = str(value).strip()

                if row_data:
                    data.append(row_data)

            return data
        except Exception as e:
            raise ValueError(f'文件解析失败: {str(e)}')

    @staticmethod
    def validate_import_data(data):
        """验证导入数据

        Args:
            data: 解析后的数据列表

        Returns:
            list: 错误列表
        """
        errors = []

        for row_idx, row in enumerate(data, start=2):  # 从第2行开始
            missing_fields = []
            if not row.get('学号'):
                missing_fields.append('学号')
            if not row.get('姓名'):
                missing_fields.append('姓名')

            if missing_fields:
                errors.append({
                    'row': row_idx,
                    'error': f'必填字段缺失：{"、".join(missing_fields)}',
                    'student_id': row.get('学号', ''),
                })

        return errors

    @staticmethod
    def check_capacity(teaching_class, import_count):
        """检查班级容量

        Args:
            teaching_class: 教学班级对象
            import_count: 导入人数

        Returns:
            int: 可添加人数

        Raises:
            ValueError: 超出容量时抛出
        """
        current_count = StudentEnrollment.objects.filter(
            teaching_class=teaching_class,
            status='enrolled',
        ).count()

        available = teaching_class.capacity - current_count

        if import_count > available:
            raise ValueError(
                f'班级当前已有 {current_count} 人，容量 {teaching_class.capacity} 人，'
                f'仅可再添加 {available} 人。'
            )

        return available

    @staticmethod
    def _get_field(row, *names):
        """获取字段值，支持多个字段名"""
        for name in names:
            if name in row and row[name]:
                return row[name]
        return None

    @staticmethod
    def process_import_row(row, teaching_class):
        """处理单行导入数据

        Args:
            row: 行数据
            teaching_class: 教学班级对象

        Returns:
            StudentEnrollment: 创建或更新的选课记录

        Raises:
            ValueError: 数据验证失败时抛出
        """
        student_id = ImportService._get_field(row, '学号', 'student_id')
        username = ImportService._get_field(row, '姓名', 'username', 'name')
        phone = ImportService._get_field(row, '手机号', 'phone')
        email = ImportService._get_field(row, '邮箱', 'email')
        admin_class = ImportService._get_field(row, '行政班级', 'admin_class')
        grade = ImportService._get_field(row, '年级', 'grade')
        role = ImportService._get_field(row, '初始角色', 'role') or ImportService.DEFAULT_ROLE

        if not student_id or not username:
            raise ValueError('学号和姓名为必填项')

        # 查找或创建用户
        try:
            profile = StudentProfile.objects.select_related('user').get(
                student_id=student_id,
            )
            user = profile.user
            created = False
        except StudentProfile.DoesNotExist:
            # 创建新用户
            if not email:
                email = f'{student_id}@school.edu'

            # 检查邮箱是否已存在
            if User.objects.filter(email=email).exists():
                email = f'{student_id}@{timezone.now().timestamp()}@school.edu'

            user = User.objects.create_user(
                username=username,
                email=email,
                user_type='student',
                password=ImportService.DEFAULT_PASSWORD,
            )
            StudentProfile.objects.create(
                user=user,
                student_id=student_id,
                phone=phone or '',
                admin_class=admin_class or '',
                grade=grade or '',
            )
            created = True

        # 更新 Profile 信息
        if phone:
            user.student_profile.phone = phone
        if admin_class:
            user.student_profile.admin_class = admin_class
        if grade:
            user.student_profile.grade = grade
        user.student_profile.save()

        # 创建或更新选课记录
        enrollment, created_enrollment = StudentEnrollment.objects.get_or_create(
            teaching_class=teaching_class,
            student=user,
            defaults={
                'role': role,
                'status': 'enrolled',
            },
        )

        if not created_enrollment:
            if enrollment.status == 'dropped':
                enrollment.status = 'enrolled'
                enrollment.dropped_at = None
                enrollment.role = role
                enrollment.save()

        return enrollment

    @staticmethod
    @transaction.atomic
    def batch_import(file, teaching_class):
        """批量导入学生

        Args:
            file: 上传的文件对象
            teaching_class: 教学班级对象

        Returns:
            dict: 导入结果摘要，格式符合设计文档
        """
        # 解析文件
        try:
            data = ImportService.parse_import_file(file)
        except ValueError as e:
            return {
                'success': False,
                'error': '文件解析失败',
                'message': str(e),
            }

        # 验证数据
        validation_errors = ImportService.validate_import_data(data)
        if validation_errors:
            return {
                'success': False,
                'error': '数据验证失败',
                'errors': validation_errors,
            }

        # 检查容量
        try:
            ImportService.check_capacity(teaching_class, len(data))
        except ValueError as e:
            return {
                'success': False,
                'error': '超出班级容量',
                'message': str(e),
            }

        # 处理导入
        created_count = 0
        updated_count = 0
        failed_count = 0
        errors = []

        for row_idx, row in enumerate(data, start=2):
            try:
                enrollment = ImportService.process_import_row(row, teaching_class)

                # 判断是新增还是更新（简单判断：如果 enrollment 刚创建）
                if enrollment and enrollment.enrolled_at and \
                   (timezone.now() - enrollment.enrolled_at).total_seconds() < 5:
                    created_count += 1
                else:
                    updated_count += 1

            except Exception as e:
                failed_count += 1
                student_id = row.get('学号') or row.get('student_id', '')
                errors.append({
                    'row': row_idx,
                    'error': str(e),
                    'student_id': student_id,
                })

        return {
            'success': True,
            'summary': {
                'total': len(data),
                'created': created_count,
                'updated': updated_count,
                'failed': failed_count,
            },
            'errors': errors,
            'warnings': [],
        }
