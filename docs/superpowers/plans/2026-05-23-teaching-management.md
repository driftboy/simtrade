# 教学管理系统实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 实现 SimTrade 平台的教学管理系统，支持四级组织体系（学期→课程→班级→实验），包含实验编排、作业管理和成绩报告。

**架构：** 新建独立 App `apps/teaching/`，包含 8 个模型（Semester/Course/TeachingClass/StudentEnrollment/ExperimentTemplate/ExperimentGroup/Assignment/AssignmentSubmission），改造 `scoring.Experiment` 新增 teaching_class 外键，成绩报告通过 GradeReportService 实时聚合。

**技术栈：** Django 3.2, Django REST Framework, Python 3.8+, SQLite(开发)/PostgreSQL(生产)

---

## 文件结构

### 将要创建的文件

| 文件路径 | 职责 |
|---------|------|
| `apps/teaching/__init__.py` | App 初始化 |
| `apps/teaching/apps.py` | App 配置 |
| `apps/teaching/models.py` | 8 个教学管理模型 |
| `apps/teaching/services.py` | 6 个 Service 类 |
| `apps/teaching/serializers.py` | API 序列化器 |
| `apps/teaching/views.py` | ViewSets 视图 |
| `apps/teaching/urls.py` | API 路由 |
| `apps/teaching/admin.py` | 管理后台 |
| `apps/teaching/permissions.py` | 权限类 |
| `apps/teaching/tests/__init__.py` | 测试包 |
| `apps/teaching/tests/test_models.py` | 模型测试 |
| `apps/teaching/tests/test_services.py` | 服务测试 |
| `apps/teaching/tests/test_api.py` | API 测试 |

### 将要修改的文件

| 文件路径 | 修改内容 |
|---------|---------|
| `simtrade/settings.py` | 注册 `apps.teaching` |
| `simtrade/urls.py` | 包含 teaching URLs |
| `apps/scoring/models.py` | Experiment 新增 teaching_class/template/group_config 字段 |

---

## 阶段 1：组织层级

### 任务 1：创建 teaching App

**文件：**
- 创建：`apps/teaching/__init__.py`
- 创建：`apps/teaching/apps.py`
- 修改：`simtrade/settings.py`

- [ ] **步骤 1：创建目录和文件**

运行：
```bash
cd f:/vsworkspace/simtrade
mkdir -p apps/teaching/tests
touch apps/teaching/__init__.py
touch apps/teaching/apps.py
touch apps/teaching/models.py
touch apps/teaching/tests/__init__.py
```

- [ ] **步骤 2：编辑 apps.py**

编辑 `apps/teaching/apps.py`：

```python
from django.apps import AppConfig


class TeachingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.teaching'
    verbose_name = '教学管理'
```

- [ ] **步骤 3：注册 App**

编辑 `simtrade/settings.py`，在 `INSTALLED_APPS` 中添加 `'apps.teaching'`。

- [ ] **步骤 4：验证**

运行：`python manage.py check`
预期：无报错

- [ ] **步骤 5：Commit**

```bash
git add apps/teaching/ simtrade/settings.py
git commit -m "feat(teaching): scaffold teaching app"
```

---

### 任务 2：实现 Semester 模型

**文件：**
- 修改：`apps/teaching/models.py`
- 创建：`apps/teaching/tests/test_models.py`

- [ ] **步骤 1：编写 Semester 测试**

创建 `apps/teaching/tests/test_models.py`：

```python
import pytest
from datetime import date
from django.core.exceptions import ValidationError
from apps.teaching.models import Semester


@pytest.mark.django_db
def test_create_semester():
    semester = Semester.objects.create(
        name='2026 春季学期',
        code='2026-SPRING',
        start_date=date(2026, 2, 20),
        end_date=date(2026, 6, 30),
    )
    assert semester.name == '2026 春季学期'
    assert semester.code == '2026-SPRING'
    assert semester.status == 'upcoming'
    assert semester.is_active is False
    assert str(semester) == '2026 春季学期'


@pytest.mark.django_db
def test_semester_code_unique():
    Semester.objects.create(
        name='学期1', code='UNIQUE01',
        start_date=date(2026, 2, 1), end_date=date(2026, 6, 30),
    )
    with pytest.raises(Exception):
        Semester.objects.create(
            name='学期2', code='UNIQUE01',
            start_date=date(2026, 7, 1), end_date=date(2027, 1, 15),
        )


@pytest.mark.django_db
def test_semester_date_validation():
    semester = Semester(
        name='错误学期', code='BAD-DATES',
        start_date=date(2026, 7, 1), end_date=date(2026, 6, 30),
    )
    with pytest.raises(ValidationError):
        semester.clean()


@pytest.mark.django_db
def test_semester_active_uniqueness():
    Semester.objects.create(
        name='活跃学期', code='ACTIVE01',
        start_date=date(2026, 2, 1), end_date=date(2026, 6, 30),
        is_active=True,
    )
    semester2 = Semester(
        name='冲突学期', code='ACTIVE02',
        start_date=date(2026, 7, 1), end_date=date(2027, 1, 15),
        is_active=True,
    )
    with pytest.raises(ValidationError):
        semester2.clean()
```

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest apps/teaching/tests/test_models.py::test_create_semester -v`
预期：FAIL，Semester 不存在

- [ ] **步骤 3：实现 Semester 模型**

编辑 `apps/teaching/models.py`：

```python
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError


class Semester(models.Model):
    """学期"""

    class Status(models.TextChoices):
        UPCOMING = 'upcoming', '未开始'
        ACTIVE = 'active', '进行中'
        ENDED = 'ended', '已结束'

    name = models.CharField('学期名称', max_length=100)
    code = models.CharField('学期代码', max_length=20, unique=True)
    start_date = models.DateField('开始日期')
    end_date = models.DateField('结束日期')
    is_active = models.BooleanField('当前学期', default=False)
    status = models.CharField(
        '状态', max_length=20,
        choices=Status.choices, default=Status.UPCOMING,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True,
        related_name='created_semesters',
    )
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'semesters'
        verbose_name = '学期'
        verbose_name_plural = '学期'
        ordering = ['-start_date']

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        if self.start_date and self.end_date and self.start_date >= self.end_date:
            raise ValidationError('结束日期必须晚于开始日期')
        if self.is_active:
            active_count = Semester.objects.filter(
                is_active=True,
            ).exclude(pk=self.pk).count()
            if active_count > 0:
                raise ValidationError('只能有一个激活的学期')
```

- [ ] **步骤 4：生成迁移并运行测试**

运行：
```bash
python manage.py makemigrations teaching
python manage.py migrate teaching
pytest apps/teaching/tests/test_models.py -v
```
预期：全部 PASS

- [ ] **步骤 5：Commit**

```bash
git add apps/teaching/models.py apps/teaching/tests/test_models.py apps/teaching/migrations/
git commit -m "feat(teaching): add Semester model"
```

---

### 任务 3：实现 Course 模型

**文件：**
- 修改：`apps/teaching/models.py`
- 修改：`apps/teaching/tests/test_models.py`

- [ ] **步骤 1：编写 Course 测试**

在 `apps/teaching/tests/test_models.py` 中追加：

```python
from apps.teaching.models import Course


@pytest.mark.django_db
def test_create_course():
    semester = Semester.objects.create(
        name='2026 春', code='2026S',
        start_date=date(2026, 2, 1), end_date=date(2026, 6, 30),
    )
    course = Course.objects.create(
        semester=semester,
        name='国际贸易实务',
        code='INTL-301',
        description='外贸模拟课程',
    )
    assert course.name == '国际贸易实务'
    assert course.status == 'upcoming'
    assert str(course) == '2026 春 - 国际贸易实务'


@pytest.mark.django_db
def test_course_code_unique_per_semester():
    semester = Semester.objects.create(
        name='学期', code='SEM01',
        start_date=date(2026, 2, 1), end_date=date(2026, 6, 30),
    )
    Course.objects.create(semester=semester, name='课1', code='C01')
    with pytest.raises(Exception):
        Course.objects.create(semester=semester, name='课2', code='C01')


@pytest.mark.django_db
def test_course_weight_validation():
    semester = Semester.objects.create(
        name='学期', code='SEM02',
        start_date=date(2026, 2, 1), end_date=date(2026, 6, 30),
    )
    course = Course(
        semester=semester, name='权重课', code='W01',
        experiment_weight=0.50, assignment_weight=0.60,
    )
    with pytest.raises(ValidationError):
        course.clean()
```

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest apps/teaching/tests/test_models.py::test_create_course -v`
预期：FAIL，Course 不存在

- [ ] **步骤 3：实现 Course 模型**

在 `apps/teaching/models.py` 的 Semester 类后面追加：

```python
class Course(models.Model):
    """课程"""

    class Status(models.TextChoices):
        UPCOMING = 'upcoming', '未开始'
        ACTIVE = 'active', '进行中'
        ENDED = 'ended', '已结束'

    semester = models.ForeignKey(
        Semester, on_delete=models.PROTECT,
        related_name='courses',
    )
    name = models.CharField('课程名称', max_length=200)
    code = models.CharField('课程代码', max_length=20)
    teachers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='teaching_courses',
        verbose_name='授课教师',
        blank=True,
    )
    description = models.TextField('课程简介', blank=True)
    experiment_weight = models.DecimalField(
        '实验成绩权重', max_digits=5, decimal_places=2, default=0.60,
    )
    assignment_weight = models.DecimalField(
        '作业成绩权重', max_digits=5, decimal_places=2, default=0.40,
    )
    status = models.CharField(
        '状态', max_length=20,
        choices=Status.choices, default=Status.UPCOMING,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True,
        related_name='created_courses',
    )
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'courses'
        verbose_name = '课程'
        verbose_name_plural = '课程'
        ordering = ['-created_at']
        unique_together = [['semester', 'code']]

    def __str__(self):
        return f'{self.semester.name} - {self.name}'

    def clean(self):
        super().clean()
        if self.experiment_weight + self.assignment_weight != 1:
            raise ValidationError('实验权重与作业权重之和必须为 1')
```

- [ ] **步骤 4：生成迁移并运行测试**

运行：
```bash
python manage.py makemigrations teaching
python manage.py migrate teaching
pytest apps/teaching/tests/test_models.py -v
```
预期：全部 PASS

- [ ] **步骤 5：Commit**

```bash
git add apps/teaching/models.py apps/teaching/tests/test_models.py apps/teaching/migrations/
git commit -m "feat(teaching): add Course model with M2M teachers"
```

---

### 任务 4：实现 TeachingClass 模型

**文件：**
- 修改：`apps/teaching/models.py`
- 修改：`apps/teaching/tests/test_models.py`

- [ ] **步骤 1：编写 TeachingClass 测试**

在 `apps/teaching/tests/test_models.py` 中追加：

```python
from apps.teaching.models import TeachingClass


@pytest.mark.django_db
def test_create_teaching_class():
    semester = Semester.objects.create(
        name='学期', code='TSEM01',
        start_date=date(2026, 2, 1), end_date=date(2026, 6, 30),
    )
    course = Course.objects.create(semester=semester, name='课', code='TC01')
    cls = TeachingClass.objects.create(
        course=course, name='3 班', capacity=30,
    )
    assert cls.name == '3 班'
    assert cls.enrollment_code  # 自动生成
    assert len(cls.enrollment_code) == 8
    assert str(cls) == '学期 - 课 - 3 班'


@pytest.mark.django_db
def test_enrollment_code_unique():
    semester = Semester.objects.create(
        name='学期', code='TSEM02',
        start_date=date(2026, 2, 1), end_date=date(2026, 6, 30),
    )
    course = Course.objects.create(semester=semester, name='课', code='TC02')
    cls1 = TeachingClass.objects.create(course=course, name='班1')
    cls2 = TeachingClass.objects.create(course=course, name='班2')
    assert cls1.enrollment_code != cls2.enrollment_code
```

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest apps/teaching/tests/test_models.py::test_create_teaching_class -v`
预期：FAIL

- [ ] **步骤 3：实现 TeachingClass 模型**

在 `apps/teaching/models.py` 的 Course 类后面追加：

```python
import random
import string


class TeachingClass(models.Model):
    """教学班级"""

    class Status(models.TextChoices):
        UPCOMING = 'upcoming', '未开始'
        ACTIVE = 'active', '进行中'
        ENDED = 'ended', '已结束'

    course = models.ForeignKey(
        Course, on_delete=models.CASCADE,
        related_name='classes',
    )
    name = models.CharField('班级名称', max_length=100)
    capacity = models.IntegerField('最大人数', default=40)
    enrollment_code = models.CharField(
        '选课码', max_length=20, unique=True,
    )
    status = models.CharField(
        '状态', max_length=20,
        choices=Status.choices, default=Status.UPCOMING,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True,
        related_name='created_classes',
    )
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'teaching_classes'
        verbose_name = '教学班级'
        verbose_name_plural = '教学班级'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.course.name} - {self.name}'

    def save(self, *args, **kwargs):
        if not self.enrollment_code:
            self.enrollment_code = self._generate_enrollment_code()
        super().save(*args, **kwargs)

    @staticmethod
    def _generate_enrollment_code():
        while True:
            code = ''.join(
                random.choices(string.ascii_uppercase + string.digits, k=8)
            )
            if not TeachingClass.objects.filter(
                enrollment_code=code,
            ).exists():
                return code
```

注意：将 `import random` 和 `import string` 放在文件顶部，与 `from django.db import models` 等导入一起。

- [ ] **步骤 4：生成迁移并运行测试**

运行：
```bash
python manage.py makemigrations teaching
python manage.py migrate teaching
pytest apps/teaching/tests/test_models.py -v
```
预期：全部 PASS

- [ ] **步骤 5：Commit**

```bash
git add apps/teaching/models.py apps/teaching/tests/test_models.py apps/teaching/migrations/
git commit -m "feat(teaching): add TeachingClass model with auto enrollment code"
```

---

### 任务 5：实现 StudentEnrollment 模型

**文件：**
- 修改：`apps/teaching/models.py`
- 修改：`apps/teaching/tests/test_models.py`

- [ ] **步骤 1：编写 StudentEnrollment 测试**

在 `apps/teaching/tests/test_models.py` 中追加：

```python
from apps.users.models import User
from apps.teaching.models import StudentEnrollment


def _make_class():
    semester = Semester.objects.create(
        name='学期', code=f'SEM-{random.randint(10000,99999)}',
        start_date=date(2026, 2, 1), end_date=date(2026, 6, 30),
    )
    course = Course.objects.create(
        semester=semester, name='课',
        code=f'C-{random.randint(10000,99999)}',
    )
    return TeachingClass.objects.create(course=course, name='班')


@pytest.mark.django_db
def test_create_enrollment():
    student = User.objects.create_user(username='stu1', password='pass')
    cls = _make_class()
    enrollment = StudentEnrollment.objects.create(
        teaching_class=cls, student=student,
    )
    assert enrollment.status == 'enrolled'
    assert enrollment.role == 'student'
    assert str(enrollment) == f'stu1 - {cls.name}'


@pytest.mark.django_db
def test_enrollment_unique():
    student = User.objects.create_user(username='stu2', password='pass')
    cls = _make_class()
    StudentEnrollment.objects.create(teaching_class=cls, student=student)
    with pytest.raises(Exception):
        StudentEnrollment.objects.create(
            teaching_class=cls, student=student,
        )
```

注意：在文件顶部添加 `import random`。

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest apps/teaching/tests/test_models.py::test_create_enrollment -v`
预期：FAIL

- [ ] **步骤 3：实现 StudentEnrollment 模型**

在 `apps/teaching/models.py` 的 TeachingClass 类后面追加：

```python
class StudentEnrollment(models.Model):
    """学生选课记录"""

    class Role(models.TextChoices):
        STUDENT = 'student', '学生'
        ASSISTANT = 'assistant', '助教'
        MONITOR = 'monitor', '班长'

    class Status(models.TextChoices):
        ENROLLED = 'enrolled', '已选课'
        DROPPED = 'dropped', '已退课'

    teaching_class = models.ForeignKey(
        TeachingClass, on_delete=models.CASCADE,
        related_name='enrollments',
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='enrollments',
    )
    role = models.CharField(
        '角色', max_length=20,
        choices=Role.choices, default=Role.STUDENT,
    )
    status = models.CharField(
        '状态', max_length=20,
        choices=Status.choices, default=Status.ENROLLED,
    )
    enrolled_at = models.DateTimeField('选课时间', auto_now_add=True)
    dropped_at = models.DateTimeField('退课时间', null=True, blank=True)

    class Meta:
        db_table = 'student_enrollments'
        verbose_name = '学生选课'
        verbose_name_plural = '学生选课'
        ordering = ['-enrolled_at']
        unique_together = [['teaching_class', 'student']]

    def __str__(self):
        return f'{self.student.username} - {self.teaching_class.name}'
```

- [ ] **步骤 4：生成迁移并运行测试**

运行：
```bash
python manage.py makemigrations teaching
python manage.py migrate teaching
pytest apps/teaching/tests/test_models.py -v
```
预期：全部 PASS

- [ ] **步骤 5：Commit**

```bash
git add apps/teaching/models.py apps/teaching/tests/test_models.py apps/teaching/migrations/
git commit -m "feat(teaching): add StudentEnrollment model"
```

---

### 任务 6：改造 scoring.Experiment

**文件：**
- 修改：`apps/scoring/models.py`

- [ ] **步骤 1：在 Experiment 模型中新增字段**

编辑 `apps/scoring/models.py`，在 Experiment 类的字段区域（`updated_at` 之前）添加：

```python
    teaching_class = models.ForeignKey(
        'teaching.TeachingClass',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='experiments',
        verbose_name='所属班级',
    )
    template = models.ForeignKey(
        'teaching.ExperimentTemplate',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='experiments',
        verbose_name='来源模板',
    )
    group_config = models.JSONField(
        '分组配置', default=dict, blank=True,
    )
```

注意：`ExperimentTemplate` 模型将在任务 8 创建，此时迁移文件先生成但 ExperimentTemplate 表还不存在。应先完成任务 5 的迁移，然后创建任务 8 的 ExperimentTemplate 模型，最后再生成此任务的迁移。实际操作中，可将此任务移到任务 8 之后执行。

**调整：将此任务移到任务 9（ExperimentTemplate 创建之后）。**

- [ ] **步骤 2：生成迁移**

运行：
```bash
python manage.py makemigrations scoring
python manage.py migrate scoring
```
预期：迁移成功

- [ ] **步骤 3：验证现有测试**

运行：`pytest apps/scoring/tests/ -v`
预期：全部 PASS（新增字段允许 null，不影响现有功能）

- [ ] **步骤 4：Commit**

```bash
git add apps/scoring/models.py apps/scoring/migrations/
git commit -m "feat(scoring): add teaching_class, template, group_config to Experiment"
```

---

### 任务 7：实现组织层级服务层

**文件：**
- 创建：`apps/teaching/services.py`
- 创建：`apps/teaching/tests/test_services.py`

- [ ] **步骤 1：编写服务层测试**

创建 `apps/teaching/tests/test_services.py`：

```python
import pytest
from datetime import date
from django.core.exceptions import ValidationError
from apps.users.models import User
from apps.teaching.models import Semester, Course, TeachingClass, StudentEnrollment
from apps.teaching.services import (
    SemesterService, CourseService, TeachingClassService,
)


@pytest.fixture
def teacher():
    return User.objects.create_user(
        username='teacher1', password='pass', user_type='teacher',
    )


@pytest.fixture
def student():
    return User.objects.create_user(
        username='student1', password='pass', user_type='student',
    )


@pytest.fixture
def semester():
    return Semester.objects.create(
        name='2026 春', code='SVC-SEM01',
        start_date=date(2026, 2, 1), end_date=date(2026, 6, 30),
    )


@pytest.fixture
def course(semester, teacher):
    course = Course.objects.create(
        semester=semester, name='国际贸易', code='SVC-C01',
    )
    course.teachers.add(teacher)
    return course


@pytest.mark.django_db
def test_activate_semester(semester):
    result = SemesterService.activate_semester(semester.id)
    assert result.is_active is True
    semester.refresh_from_db()
    assert semester.is_active is True


@pytest.mark.django_db
def test_activate_semester_deactivates_others(semester):
    other = Semester.objects.create(
        name='其他学期', code='SVC-SEM02',
        start_date=date(2025, 9, 1), end_date=date(2026, 1, 15),
        is_active=True,
    )
    SemesterService.activate_semester(semester.id)
    other.refresh_from_db()
    assert other.is_active is False


@pytest.mark.django_db
def test_get_active_semester(semester):
    SemesterService.activate_semester(semester.id)
    result = SemesterService.get_active_semester()
    assert result == semester


@pytest.mark.django_db
def test_get_active_semester_none():
    result = SemesterService.get_active_semester()
    assert result is None


@pytest.mark.django_db
def test_create_course(semester, teacher):
    course = CourseService.create_course(
        user=teacher, semester_id=semester.id,
        name='新课程', code='NEW-C01',
        teacher_ids=[teacher.id],
    )
    assert course.name == '新课程'
    assert course.teachers.filter(id=teacher.id).exists()


@pytest.mark.django_db
def test_get_teacher_courses(teacher, course):
    courses = CourseService.get_teacher_courses(teacher)
    assert course in courses


@pytest.mark.django_db
def test_create_class(course, teacher):
    cls = TeachingClassService.create_class(
        user=teacher, course_id=course.id,
        name='1 班', capacity=35,
    )
    assert cls.course == course
    assert cls.enrollment_code
    assert cls.capacity == 35


@pytest.mark.django_db
def test_enroll_student(course, student):
    cls = TeachingClassService.create_class(
        user=course.teachers.first(),
        course_id=course.id, name='班',
    )
    enrollment = TeachingClassService.enroll_student(
        teaching_class_id=cls.id,
        student=student,
        enrollment_code=cls.enrollment_code,
    )
    assert enrollment.status == 'enrolled'
    assert enrollment.student == student


@pytest.mark.django_db
def test_enroll_wrong_code(course, student):
    cls = TeachingClassService.create_class(
        user=course.teachers.first(),
        course_id=course.id, name='班',
    )
    with pytest.raises(ValueError):
        TeachingClassService.enroll_student(
            teaching_class_id=cls.id,
            student=student,
            enrollment_code='WRONG',
        )


@pytest.mark.django_db
def test_drop_student(course, student):
    cls = TeachingClassService.create_class(
        user=course.teachers.first(),
        course_id=course.id, name='班',
    )
    enrollment = TeachingClassService.enroll_student(
        teaching_class_id=cls.id,
        student=student,
        enrollment_code=cls.enrollment_code,
    )
    TeachingClassService.drop_student(enrollment.id, student)
    enrollment.refresh_from_db()
    assert enrollment.status == 'dropped'
    assert enrollment.dropped_at is not None
```

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest apps/teaching/tests/test_services.py::test_activate_semester -v`
预期：FAIL

- [ ] **步骤 3：实现服务层**

创建 `apps/teaching/services.py`：

```python
from django.utils import timezone
from apps.teaching.models import Semester, Course, TeachingClass, StudentEnrollment


class SemesterService:

    @staticmethod
    def create_semester(user, name, code, start_date, end_date):
        return Semester.objects.create(
            name=name, code=code,
            start_date=start_date, end_date=end_date,
            created_by=user,
        )

    @staticmethod
    def activate_semester(semester_id):
        semester = Semester.objects.get(id=semester_id)
        Semester.objects.filter(is_active=True).update(is_active=False)
        semester.is_active = True
        semester.status = 'active'
        semester.save()
        return semester

    @staticmethod
    def get_active_semester():
        return Semester.objects.filter(is_active=True).first()


class CourseService:

    @staticmethod
    def create_course(user, semester_id, name, code, teacher_ids=None, **kwargs):
        course = Course.objects.create(
            semester_id=semester_id,
            name=name, code=code,
            created_by=user,
            **kwargs,
        )
        if teacher_ids:
            from apps.users.models import User
            teachers = User.objects.filter(id__in=teacher_ids)
            course.teachers.set(teachers)
        return course

    @staticmethod
    def get_teacher_courses(teacher):
        return Course.objects.filter(teachers=teacher)

    @staticmethod
    def get_student_courses(student):
        enrollment_ids = StudentEnrollment.objects.filter(
            student=student, status='enrolled',
        ).values_list('teaching_class__course_id', flat=True)
        return Course.objects.filter(id__in=enrollment_ids).distinct()


class TeachingClassService:

    @staticmethod
    def create_class(user, course_id, name, capacity=40):
        return TeachingClass.objects.create(
            course_id=course_id,
            name=name, capacity=capacity,
            created_by=user,
        )

    @staticmethod
    def enroll_student(teaching_class_id, student, enrollment_code=None):
        cls = TeachingClass.objects.get(id=teaching_class_id)

        if enrollment_code and cls.enrollment_code != enrollment_code:
            raise ValueError('选课码错误')

        current_count = StudentEnrollment.objects.filter(
            teaching_class=cls, status='enrolled',
        ).count()
        if current_count >= cls.capacity:
            raise ValueError('班级已满')

        enrollment, created = StudentEnrollment.objects.get_or_create(
            teaching_class=cls,
            student=student,
            defaults={'status': 'enrolled'},
        )
        if not created and enrollment.status == 'dropped':
            enrollment.status = 'enrolled'
            enrollment.dropped_at = None
            enrollment.save()
        elif not created:
            raise ValueError('已经选过该班级')

        return enrollment

    @staticmethod
    def drop_student(enrollment_id, user):
        enrollment = StudentEnrollment.objects.get(
            id=enrollment_id, student=user,
        )
        enrollment.status = 'dropped'
        enrollment.dropped_at = timezone.now()
        enrollment.save()
        return enrollment

    @staticmethod
    def get_class_students(teaching_class_id):
        return StudentEnrollment.objects.filter(
            teaching_class_id=teaching_class_id,
            status='enrolled',
        ).select_related('student')
```

- [ ] **步骤 4：运行测试**

运行：`pytest apps/teaching/tests/test_services.py -v`
预期：全部 PASS

- [ ] **步骤 5：Commit**

```bash
git add apps/teaching/services.py apps/teaching/tests/test_services.py
git commit -m "feat(teaching): add SemesterService, CourseService, TeachingClassService"
```

---

### 任务 8：实现序列化器

**文件：**
- 创建：`apps/teaching/serializers.py`

- [ ] **步骤 1：实现全部序列化器**

创建 `apps/teaching/serializers.py`：

```python
from rest_framework import serializers
from apps.teaching.models import (
    Semester, Course, TeachingClass, StudentEnrollment,
    ExperimentTemplate, ExperimentGroup,
    Assignment, AssignmentSubmission,
)


class SemesterSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(
        source='get_status_display', read_only=True,
    )

    class Meta:
        model = Semester
        fields = [
            'id', 'name', 'code', 'start_date', 'end_date',
            'is_active', 'status', 'status_display',
            'created_by', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by']


class CourseSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(
        source='get_status_display', read_only=True,
    )
    semester_name = serializers.CharField(
        source='semester.name', read_only=True,
    )
    teacher_names = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = [
            'id', 'semester', 'semester_name', 'name', 'code',
            'teachers', 'teacher_names', 'description',
            'experiment_weight', 'assignment_weight',
            'status', 'status_display',
            'created_by', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by']

    def get_teacher_names(self, obj):
        return list(
            obj.teachers.values_list('username', flat=True),
        )


class TeachingClassSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(
        source='get_status_display', read_only=True,
    )
    course_name = serializers.CharField(
        source='course.name', read_only=True,
    )
    student_count = serializers.SerializerMethodField()

    class Meta:
        model = TeachingClass
        fields = [
            'id', 'course', 'course_name', 'name', 'capacity',
            'enrollment_code', 'status', 'status_display',
            'student_count',
            'created_by', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'enrollment_code', 'created_at',
            'updated_at', 'created_by',
        ]

    def get_student_count(self, obj):
        return obj.enrollments.filter(status='enrolled').count()


class StudentEnrollmentSerializer(serializers.ModelSerializer):
    student_username = serializers.CharField(
        source='student.username', read_only=True,
    )
    status_display = serializers.CharField(
        source='get_status_display', read_only=True,
    )
    role_display = serializers.CharField(
        source='get_role_display', read_only=True,
    )

    class Meta:
        model = StudentEnrollment
        fields = [
            'id', 'teaching_class', 'student', 'student_username',
            'role', 'role_display', 'status', 'status_display',
            'enrolled_at', 'dropped_at',
        ]
        read_only_fields = ['id', 'enrolled_at', 'dropped_at']


class EnrollRequestSerializer(serializers.Serializer):
    enrollment_code = serializers.CharField(max_length=20)


class ExperimentTemplateSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(
        source='created_by.username', read_only=True,
    )

    class Meta:
        model = ExperimentTemplate
        fields = [
            'id', 'name', 'description', 'config',
            'is_public', 'use_count', 'created_by',
            'created_by_name', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'use_count', 'created_at', 'updated_at',
            'created_by',
        ]


class ExperimentGroupSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(
        source='company.name', read_only=True,
    )

    class Meta:
        model = ExperimentGroup
        fields = [
            'id', 'experiment', 'company', 'company_name',
            'group_name',
        ]
        read_only_fields = ['id']


class AutoGroupSerializer(serializers.Serializer):
    group_size = serializers.IntegerField(
        min_value=2, max_value=10, default=5,
    )


class AssignmentSerializer(serializers.ModelSerializer):
    assignment_type_display = serializers.CharField(
        source='get_assignment_type_display', read_only=True,
    )
    class_name = serializers.CharField(
        source='teaching_class.name', read_only=True,
    )
    submission_count = serializers.SerializerMethodField()

    class Meta:
        model = Assignment
        fields = [
            'id', 'teaching_class', 'class_name',
            'title', 'description', 'assignment_type',
            'assignment_type_display', 'max_score',
            'due_date', 'allow_late', 'submission_count',
            'created_by', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'created_by',
        ]

    def get_submission_count(self, obj):
        return obj.submissions.filter(
            status__in=['submitted', 'graded'],
        ).count()


class AssignmentSubmissionSerializer(serializers.ModelSerializer):
    student_username = serializers.CharField(
        source='student.username', read_only=True,
    )
    assignment_title = serializers.CharField(
        source='assignment.title', read_only=True,
    )
    status_display = serializers.CharField(
        source='get_status_display', read_only=True,
    )

    class Meta:
        model = AssignmentSubmission
        fields = [
            'id', 'assignment', 'assignment_title',
            'student', 'student_username',
            'content', 'attachment',
            'score', 'feedback',
            'status', 'status_display',
            'submitted_at', 'graded_at', 'graded_by',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'student', 'submitted_at', 'graded_at',
            'graded_by', 'created_at', 'updated_at',
        ]


class GradeSerializer(serializers.Serializer):
    score = serializers.DecimalField(
        max_digits=6, decimal_places=2, min_value=0,
    )
    feedback = serializers.CharField(
        required=False, allow_blank=True, max_length=1000,
    )
```

- [ ] **步骤 2：Commit**

```bash
git add apps/teaching/serializers.py
git commit -m "feat(teaching): add all serializers"
```

---

### 任务 9：实现权限类

**文件：**
- 创建：`apps/teaching/permissions.py`

- [ ] **步骤 1：实现权限类**

创建 `apps/teaching/permissions.py`：

```python
from rest_framework.permissions import BasePermission


class IsTeacherOrAdmin(BasePermission):
    """教师或管理员权限"""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.user_type in ('teacher', 'admin')


class IsTeacherOfClass(BasePermission):
    """班级授课教师权限"""

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.user_type == 'admin':
            return True
        if request.user.user_type != 'teacher':
            return False
        if hasattr(obj, 'course'):
            return obj.course.teachers.filter(
                id=request.user.id,
            ).exists()
        if hasattr(obj, 'teaching_class'):
            return obj.teaching_class.course.teachers.filter(
                id=request.user.id,
            ).exists()
        return False


class IsEnrolledStudent(BasePermission):
    """已选课学生权限"""

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.user_type in ('teacher', 'admin'):
            return True
        from apps.teaching.models import StudentEnrollment
        if hasattr(obj, 'teaching_class'):
            return StudentEnrollment.objects.filter(
                teaching_class=obj.teaching_class,
                student=request.user,
                status='enrolled',
            ).exists()
        return False
```

- [ ] **步骤 2：Commit**

```bash
git add apps/teaching/permissions.py
git commit -m "feat(teaching): add permission classes"
```

---

### 任务 10：实现 API 视图和路由

**文件：**
- 创建：`apps/teaching/views.py`
- 创建：`apps/teaching/urls.py`
- 修改：`simtrade/urls.py`

- [ ] **步骤 1：实现视图**

创建 `apps/teaching/views.py`：

```python
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from apps.teaching.models import (
    Semester, Course, TeachingClass, StudentEnrollment,
    ExperimentTemplate, ExperimentGroup,
    Assignment, AssignmentSubmission,
)
from apps.teaching.serializers import (
    SemesterSerializer, CourseSerializer,
    TeachingClassSerializer, StudentEnrollmentSerializer,
    EnrollRequestSerializer,
    ExperimentTemplateSerializer, ExperimentGroupSerializer,
    AutoGroupSerializer,
    AssignmentSerializer, AssignmentSubmissionSerializer,
    GradeSerializer,
)
from apps.teaching.services import (
    SemesterService, CourseService, TeachingClassService,
)
from apps.teaching.permissions import IsTeacherOrAdmin


class SemesterViewSet(viewsets.ModelViewSet):
    queryset = Semester.objects.all()
    serializer_class = SemesterSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.user.user_type == 'student':
            return qs.filter(status__in=['active', 'ended'])
        return qs

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        if not IsTeacherOrAdmin().has_permission(request, self):
            return Response(
                {'code': 2001, 'message': '无权限操作'},
                status=status.HTTP_403_FORBIDDEN,
            )
        semester = SemesterService.activate_semester(pk)
        return Response({
            'code': 0,
            'message': '学期已激活',
            'data': SemesterSerializer(semester).data,
        })


class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.select_related('semester')
    serializer_class = CourseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.user_type == 'student':
            return CourseService.get_student_courses(user)
        if user.user_type == 'teacher':
            return CourseService.get_teacher_courses(user)
        return qs

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class TeachingClassViewSet(viewsets.ModelViewSet):
    queryset = TeachingClass.objects.select_related(
        'course', 'course__semester',
    )
    serializer_class = TeachingClassSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        course_id = self.request.query_params.get('course_id')
        if course_id:
            qs = qs.filter(course_id=course_id)
        return qs

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'])
    def enroll(self, request, pk=None):
        serializer = EnrollRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'code': 3002, 'message': '参数错误',
                 'errors': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            enrollment = TeachingClassService.enroll_student(
                teaching_class_id=pk,
                student=request.user,
                enrollment_code=serializer.validated_data['enrollment_code'],
            )
            return Response({
                'code': 0,
                'message': '选课成功',
                'data': StudentEnrollmentSerializer(enrollment).data,
            })
        except ValueError as e:
            return Response(
                {'code': 5005, 'message': str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=True, methods=['get'])
    def enrollments(self, request, pk=None):
        if not IsTeacherOrAdmin().has_permission(request, self):
            return Response(
                {'code': 2001, 'message': '无权限操作'},
                status=status.HTTP_403_FORBIDDEN,
            )
        enrollments = TeachingClassService.get_class_students(pk)
        return Response({
            'code': 0,
            'message': 'success',
            'data': StudentEnrollmentSerializer(enrollments, many=True).data,
        })

    @action(detail=True, methods=['post'])
    def drop(self, request, pk=None):
        enrollment = StudentEnrollment.objects.filter(
            teaching_class_id=pk,
            student=request.user,
            status='enrolled',
        ).first()
        if not enrollment:
            return Response(
                {'code': 4001, 'message': '未选该班级'},
                status=status.HTTP_404_NOT_FOUND,
            )
        TeachingClassService.drop_student(enrollment.id, request.user)
        return Response({'code': 0, 'message': '退课成功'})


class ExperimentTemplateViewSet(viewsets.ModelViewSet):
    queryset = ExperimentTemplate.objects.all()
    serializer_class = ExperimentTemplateSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.user_type == 'admin':
            return qs
        return qs.filter(
            is_public=True,
        ) | qs.filter(created_by=user)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class ExperimentGroupViewSet(viewsets.ModelViewSet):
    queryset = ExperimentGroup.objects.select_related('company')
    serializer_class = ExperimentGroupSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        experiment_id = self.request.query_params.get('experiment_id')
        if experiment_id:
            qs = qs.filter(experiment_id=experiment_id)
        return qs

    @action(detail=False, methods=['post'])
    def auto_group(self, request):
        if not IsTeacherOrAdmin().has_permission(request, self):
            return Response(
                {'code': 2001, 'message': '无权限操作'},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = AutoGroupSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'code': 3002, 'message': '参数错误',
                 'errors': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        experiment_id = request.query_params.get('experiment_id')
        if not experiment_id:
            return Response(
                {'code': 3002, 'message': '需要 experiment_id 参数'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        from apps.teaching.services import ExperimentOrchestrationService
        try:
            groups = ExperimentOrchestrationService.auto_group(
                int(experiment_id),
                group_size=serializer.validated_data['group_size'],
            )
            return Response({
                'code': 0,
                'message': f'已自动分组 {len(groups)} 组',
                'data': ExperimentGroupSerializer(groups, many=True).data,
            })
        except Exception as e:
            return Response(
                {'code': 5005, 'message': str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class AssignmentViewSet(viewsets.ModelViewSet):
    queryset = Assignment.objects.select_related('teaching_class')
    serializer_class = AssignmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        class_id = self.request.query_params.get('class_id')
        if class_id:
            qs = qs.filter(teaching_class_id=class_id)
        return qs

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        assignment = self.get_object()
        submission, created = AssignmentSubmission.objects.get_or_create(
            assignment=assignment,
            student=request.user,
            defaults={'status': 'not_submitted'},
        )
        submission.content = request.data.get('content', '')
        if 'attachment' in request.FILES:
            submission.attachment = request.FILES['attachment']
        submission.status = 'submitted'
        submission.submitted_at = timezone.now()
        submission.save()
        return Response({
            'code': 0,
            'message': '提交成功',
            'data': AssignmentSubmissionSerializer(submission).data,
        })

    @action(detail=True, methods=['get'])
    def submissions(self, request, pk=None):
        if not IsTeacherOrAdmin().has_permission(request, self):
            return Response(
                {'code': 2001, 'message': '无权限操作'},
                status=status.HTTP_403_FORBIDDEN,
            )
        assignment = self.get_object()
        submissions = assignment.submissions.select_related('student')
        return Response({
            'code': 0,
            'message': 'success',
            'data': AssignmentSubmissionSerializer(
                submissions, many=True,
            ).data,
        })


class SubmissionViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['post'], url_path='(?P<submission_id>[^/.]+)/grade')
    def grade(self, request, submission_id=None):
        if not IsTeacherOrAdmin().has_permission(request, self):
            return Response(
                {'code': 2001, 'message': '无权限操作'},
                status=status.HTTP_403_FORBIDDEN,
            )
        submission = AssignmentSubmission.objects.get(id=submission_id)
        serializer = GradeSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'code': 3002, 'message': '参数错误',
                 'errors': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        submission.score = serializer.validated_data['score']
        submission.feedback = serializer.validated_data.get('feedback', '')
        submission.status = 'graded'
        submission.graded_by = request.user
        from django.utils import timezone as tz
        submission.graded_at = tz.now()
        submission.save()
        return Response({
            'code': 0,
            'message': '评分成功',
            'data': AssignmentSubmissionSerializer(submission).data,
        })


class ReportViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'], url_path='class/(?P<class_id>[^/.]+)/my')
    def my_report(self, request, class_id=None):
        from apps.teaching.services import GradeReportService
        report = GradeReportService.get_student_report(
            request.user, int(class_id),
        )
        return Response({
            'code': 0,
            'message': 'success',
            'data': report,
        })

    @action(detail=False, methods=['get'], url_path='class/(?P<class_id>[^/.]+)')
    def class_report(self, request, class_id=None):
        if not IsTeacherOrAdmin().has_permission(request, self):
            return Response(
                {'code': 2001, 'message': '无权限操作'},
                status=status.HTTP_403_FORBIDDEN,
            )
        from apps.teaching.services import GradeReportService
        report = GradeReportService.get_class_report(int(class_id))
        return Response({
            'code': 0,
            'message': 'success',
            'data': report,
        })

    @action(detail=False, methods=['get'], url_path='course/(?P<course_id>[^/.]+)')
    def course_report(self, request, course_id=None):
        if not IsTeacherOrAdmin().has_permission(request, self):
            return Response(
                {'code': 2001, 'message': '无权限操作'},
                status=status.HTTP_403_FORBIDDEN,
            )
        from apps.teaching.services import GradeReportService
        report = GradeReportService.get_course_report(int(course_id))
        return Response({
            'code': 0,
            'message': 'success',
            'data': report,
        })
```

注意：在文件顶部添加 `from django.utils import timezone`。

- [ ] **步骤 2：配置路由**

创建 `apps/teaching/urls.py`：

```python
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.teaching.views import (
    SemesterViewSet, CourseViewSet,
    TeachingClassViewSet, ExperimentTemplateViewSet,
    ExperimentGroupViewSet, AssignmentViewSet,
    SubmissionViewSet, ReportViewSet,
)

router = DefaultRouter()
router.register(r'semesters', SemesterViewSet, basename='semester')
router.register(r'courses', CourseViewSet, basename='course')
router.register(r'classes', TeachingClassViewSet, basename='teachingclass')
router.register(
    r'experiment-templates', ExperimentTemplateViewSet,
    basename='experimenttemplate',
)
router.register(r'experiment-groups', ExperimentGroupViewSet, basename='experimentgroup')
router.register(r'assignments', AssignmentViewSet, basename='assignment')
router.register(r'submissions', SubmissionViewSet, basename='submission')
router.register(r'reports', ReportViewSet, basename='report')

urlpatterns = [
    path('api/v1/teaching/', include(router.urls)),
]
```

- [ ] **步骤 3：注册到主 urls.py**

编辑 `simtrade/urls.py`，在 urlpatterns 中添加：
```python
path('', include('apps.teaching.urls')),
```

- [ ] **步骤 4：验证**

运行：`python manage.py check`
预期：无报错

- [ ] **步骤 5：Commit**

```bash
git add apps/teaching/views.py apps/teaching/urls.py simtrade/urls.py
git commit -m "feat(teaching): add API views and URL routing"
```

---

### 任务 11：配置 Admin

**文件：**
- 创建：`apps/teaching/admin.py`

- [ ] **步骤 1：实现 Admin 配置**

创建 `apps/teaching/admin.py`：

```python
from django.contrib import admin
from apps.teaching.models import (
    Semester, Course, TeachingClass, StudentEnrollment,
    ExperimentTemplate, ExperimentGroup,
    Assignment, AssignmentSubmission,
)


class CourseTeacherInline(admin.TabularInline):
    model = Course.teachers.through
    extra = 1


@admin.register(Semester)
class SemesterAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'code', 'start_date', 'end_date',
        'is_active', 'status',
    ]
    list_filter = ['is_active', 'status']
    search_fields = ['name', 'code']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'code', 'semester', 'status',
        'experiment_weight', 'assignment_weight',
    ]
    list_filter = ['status', 'semester']
    search_fields = ['name', 'code']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [CourseTeacherInline]


@admin.register(TeachingClass)
class TeachingClassAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'course', 'capacity',
        'enrollment_code', 'status',
    ]
    list_filter = ['status', 'course']
    search_fields = ['name', 'enrollment_code']
    readonly_fields = ['enrollment_code', 'created_at', 'updated_at']


@admin.register(StudentEnrollment)
class StudentEnrollmentAdmin(admin.ModelAdmin):
    list_display = [
        'student', 'teaching_class', 'role', 'status', 'enrolled_at',
    ]
    list_filter = ['status', 'role']
    search_fields = ['student__username', 'teaching_class__name']
    readonly_fields = ['enrolled_at']


@admin.register(ExperimentTemplate)
class ExperimentTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_public', 'use_count', 'created_by']
    list_filter = ['is_public']
    search_fields = ['name']
    readonly_fields = ['use_count', 'created_at', 'updated_at']


@admin.register(ExperimentGroup)
class ExperimentGroupAdmin(admin.ModelAdmin):
    list_display = ['group_name', 'experiment', 'company']
    search_fields = ['group_name']


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'teaching_class', 'assignment_type',
        'max_score', 'due_date',
    ]
    list_filter = ['assignment_type', 'teaching_class']
    search_fields = ['title']


@admin.register(AssignmentSubmission)
class AssignmentSubmissionAdmin(admin.ModelAdmin):
    list_display = [
        'assignment', 'student', 'status',
        'score', 'submitted_at',
    ]
    list_filter = ['status']
    search_fields = ['student__username', 'assignment__title']
    readonly_fields = ['submitted_at', 'graded_at']
```

- [ ] **步骤 2：Commit**

```bash
git add apps/teaching/admin.py
git commit -m "feat(teaching): configure admin interface"
```

---

## 阶段 2：实验编排

### 任务 12：实现 ExperimentTemplate 和 ExperimentGroup 模型

**文件：**
- 修改：`apps/teaching/models.py`
- 修改：`apps/teaching/tests/test_models.py`

- [ ] **步骤 1：编写 ExperimentTemplate 测试**

在 `apps/teaching/tests/test_models.py` 中追加：

```python
from apps.teaching.models import ExperimentTemplate, ExperimentGroup


@pytest.mark.django_db
def test_create_experiment_template():
    user = User.objects.create_user(username='tpl_creator', password='pass')
    tpl = ExperimentTemplate.objects.create(
        name='CIF 出口完整流程',
        description='模拟 CIF 术语下的完整出口贸易流程',
        config={'roles_per_group': 5, 'trade_term': 'CIF'},
        is_public=True,
        created_by=user,
    )
    assert tpl.name == 'CIF 出口完整流程'
    assert tpl.use_count == 0
    assert str(tpl) == 'CIF 出口完整流程'
```

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest apps/teaching/tests/test_models.py::test_create_experiment_template -v`
预期：FAIL

- [ ] **步骤 3：实现 ExperimentTemplate 模型**

在 `apps/teaching/models.py` 的 StudentEnrollment 类后面追加：

```python
class ExperimentTemplate(models.Model):
    """实验模板"""

    name = models.CharField('模板名称', max_length=200)
    description = models.TextField('模板描述', blank=True)
    config = models.JSONField('预设配置', default=dict)
    is_public = models.BooleanField('是否公开', default=False)
    use_count = models.IntegerField('使用次数', default=0)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True,
        related_name='created_experiment_templates',
    )
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'experiment_templates'
        verbose_name = '实验模板'
        verbose_name_plural = '实验模板'
        ordering = ['-use_count', '-created_at']

    def __str__(self):
        return self.name
```

- [ ] **步骤 4：生成迁移并运行测试**

运行：
```bash
python manage.py makemigrations teaching
python manage.py migrate teaching
pytest apps/teaching/tests/test_models.py::test_create_experiment_template -v
```
预期：PASS

- [ ] **步骤 5：编写 ExperimentGroup 测试**

在 `apps/teaching/tests/test_models.py` 中追加：

```python
@pytest.mark.django_db
def test_create_experiment_group():
    from apps.roles.models import Company
    from apps.scoring.models import Experiment
    company = Company.objects.create(
        name='实验组公司', code='EXP-GRP01',
    )
    experiment = Experiment.objects.create(
        name='测试实验',
        start_date='2026-03-01 00:00:00',
    )
    group = ExperimentGroup.objects.create(
        experiment=experiment,
        company=company,
        group_name='A 组',
    )
    assert group.group_name == 'A 组'
    assert str(group) == '测试实验 - A 组'
```

- [ ] **步骤 6：实现 ExperimentGroup 模型**

在 `apps/teaching/models.py` 的 ExperimentTemplate 类后面追加：

```python
class ExperimentGroup(models.Model):
    """实验分组"""

    experiment = models.ForeignKey(
        'scoring.Experiment',
        on_delete=models.CASCADE,
        related_name='groups',
    )
    company = models.OneToOneField(
        'roles.Company',
        on_delete=models.CASCADE,
        related_name='experiment_group',
    )
    group_name = models.CharField('组名', max_length=100)

    class Meta:
        db_table = 'experiment_groups'
        verbose_name = '实验分组'
        verbose_name_plural = '实验分组'
        ordering = ['group_name']

    def __str__(self):
        return f'{self.experiment.name} - {self.group_name}'
```

- [ ] **步骤 7：生成迁移并运行测试**

运行：
```bash
python manage.py makemigrations teaching
python manage.py migrate teaching
pytest apps/teaching/tests/test_models.py -v
```
预期：全部 PASS

- [ ] **步骤 8：执行任务 6（改造 scoring.Experiment）**

现在 ExperimentTemplate 已存在，可安全地在 `apps/scoring/models.py` 的 Experiment 类中添加：

```python
    teaching_class = models.ForeignKey(
        'teaching.TeachingClass',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='experiments',
        verbose_name='所属班级',
    )
    template = models.ForeignKey(
        'teaching.ExperimentTemplate',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='experiments',
        verbose_name='来源模板',
    )
    group_config = models.JSONField(
        '分组配置', default=dict, blank=True,
    )
```

运行：
```bash
python manage.py makemigrations scoring
python manage.py migrate scoring
pytest apps/scoring/tests/ -v
```
预期：全部 PASS

- [ ] **步骤 9：Commit**

```bash
git add apps/teaching/models.py apps/teaching/tests/test_models.py apps/teaching/migrations/ apps/scoring/models.py apps/scoring/migrations/
git commit -m "feat(teaching): add ExperimentTemplate and ExperimentGroup, modify scoring.Experiment"
```

---

### 任务 13：实现 ExperimentOrchestrationService

**文件：**
- 修改：`apps/teaching/services.py`
- 修改：`apps/teaching/tests/test_services.py`

- [ ] **步骤 1：编写实验编排测试**

在 `apps/teaching/tests/test_services.py` 中追加：

```python
from apps.teaching.services import ExperimentOrchestrationService
from apps.roles.models import Company


def _make_class_with_students(student_count=6):
    semester = Semester.objects.create(
        name='学期', code=f'EXP-SEM-{random.randint(10000,99999)}',
        start_date=date(2026, 2, 1), end_date=date(2026, 6, 30),
    )
    course = Course.objects.create(
        semester=semester, name='课',
        code=f'EXP-C-{random.randint(10000,99999)}',
    )
    cls = TeachingClass.objects.create(course=course, name='实验班')
    students = []
    for i in range(student_count):
        s = User.objects.create_user(
            username=f'expstu{i}_{random.randint(1000,9999)}',
            password='pass', user_type='student',
        )
        StudentEnrollment.objects.create(teaching_class=cls, student=s)
        students.append(s)
    return cls, students


@pytest.mark.django_db
def test_auto_group():
    cls, students = _make_class_with_students(6)
    from apps.scoring.models import Experiment
    experiment = Experiment.objects.create(
        name='分组测试',
        start_date='2026-03-01 00:00:00',
        teaching_class=cls,
    )
    groups = ExperimentOrchestrationService.auto_group(
        experiment.id, group_size=3,
    )
    assert len(groups) == 2
    for g in groups:
        assert g.company is not None
        assert g.group_name


@pytest.mark.django_db
def test_batch_assign_roles():
    cls, students = _make_class_with_students(5)
    from apps.scoring.models import Experiment
    from apps.roles.models import TradeRole
    experiment = Experiment.objects.create(
        name='角色测试',
        start_date='2026-03-01 00:00:00',
        teaching_class=cls,
    )
    groups = ExperimentOrchestrationService.auto_group(
        experiment.id, group_size=5,
    )
    assignments = ExperimentOrchestrationService.batch_assign_roles(
        experiment.id,
    )
    assert len(assignments) == 5
    role_codes = set(a.role.code for a in assignments)
    assert len(role_codes) == 5
```

注意：在文件顶部添加 `import random`。

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest apps/teaching/tests/test_services.py::test_auto_group -v`
预期：FAIL

- [ ] **步骤 3：实现 ExperimentOrchestrationService**

在 `apps/teaching/services.py` 的 TeachingClassService 类后面追加：

```python
from apps.roles.models import Company, TradeRole, UserCompanyRole
from apps.scoring.models import Experiment
from apps.teaching.models import ExperimentGroup, ExperimentTemplate


class ExperimentOrchestrationService:

    @staticmethod
    def create_from_template(template_id, teaching_class_id, user, **overrides):
        template = ExperimentTemplate.objects.get(id=template_id)
        config = {**template.config, **overrides}
        experiment = Experiment.objects.create(
            name=overrides.get('name', template.name),
            description=template.description,
            teaching_class_id=teaching_class_id,
            template=template,
            group_config=config,
            created_by=user,
            start_date=overrides.get(
                'start_date',
                timezone.now().isoformat(),
            ),
        )
        template.use_count += 1
        template.save()
        return experiment

    @staticmethod
    def auto_group(experiment_id, group_size=5):
        experiment = Experiment.objects.get(id=experiment_id)
        enrollments = StudentEnrollment.objects.filter(
            teaching_class=experiment.teaching_class,
            status='enrolled',
        ).select_related('student')

        students = list(enrollments)
        group_names = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        groups = []

        for i in range(0, len(students), group_size):
            chunk = students[i:i + group_size]
            group_letter = group_names[i // group_size]
            company = Company.objects.create(
                name=f'{experiment.name} - {group_letter}组',
                code=f'EXP{experiment.id:04d}-{group_letter}',
            )
            group = ExperimentGroup.objects.create(
                experiment=experiment,
                company=company,
                group_name=f'{group_letter} 组',
            )
            groups.append(group)

        return groups

    @staticmethod
    def batch_assign_roles(experiment_id):
        experiment = Experiment.objects.get(id=experiment_id)
        groups = ExperimentGroup.objects.filter(
            experiment=experiment,
        ).select_related('company')

        all_roles = list(
            TradeRole.objects.filter(is_enabled=True).order_by('sort_order'),
        )
        assignments = []

        for group in groups:
            enrollments = StudentEnrollment.objects.filter(
                teaching_class=experiment.teaching_class,
                status='enrolled',
            ).select_related('student')

            for idx, enrollment in enumerate(enrollments):
                if idx >= len(all_roles):
                    break
                role = all_roles[idx]
                assignment = UserCompanyRole.objects.create(
                    user=enrollment.student,
                    company=group.company,
                    role=role,
                    status='active',
                    is_active=(idx == 0),
                )
                assignments.append(assignment)

        return assignments

    @staticmethod
    def get_experiment_groups(experiment_id):
        return ExperimentGroup.objects.filter(
            experiment_id=experiment_id,
        ).select_related('company')
```

- [ ] **步骤 4：运行测试**

运行：`pytest apps/teaching/tests/test_services.py -v`
预期：全部 PASS

- [ ] **步骤 5：Commit**

```bash
git add apps/teaching/services.py apps/teaching/tests/test_services.py
git commit -m "feat(teaching): add ExperimentOrchestrationService with auto-group"
```

---

## 阶段 3：作业/任务

### 任务 14：实现 Assignment 和 AssignmentSubmission 模型

**文件：**
- 修改：`apps/teaching/models.py`
- 修改：`apps/teaching/tests/test_models.py`

- [ ] **步骤 1：编写作业模型测试**

在 `apps/teaching/tests/test_models.py` 中追加：

```python
from apps.teaching.models import Assignment, AssignmentSubmission


def _make_assignment():
    semester = Semester.objects.create(
        name='学期', code=f'ASM-SEM-{random.randint(10000,99999)}',
        start_date=date(2026, 2, 1), end_date=date(2026, 6, 30),
    )
    course = Course.objects.create(
        semester=semester, name='课',
        code=f'ASM-C-{random.randint(10000,99999)}',
    )
    cls = TeachingClass.objects.create(course=course, name='作业班')
    return Assignment.objects.create(
        teaching_class=cls,
        title='第一次作业',
        description='完成案例分析',
        assignment_type='homework',
        max_score=100,
        due_date=date(2026, 4, 1),
    )


@pytest.mark.django_db
def test_create_assignment():
    assignment = _make_assignment()
    assert assignment.title == '第一次作业'
    assert assignment.assignment_type == 'homework'
    assert assignment.allow_late is False
    assert str(assignment).endswith('- 第一次作业')


@pytest.mark.django_db
def test_create_submission():
    assignment = _make_assignment()
    student = User.objects.create_user(
        username='substu', password='pass',
    )
    submission = AssignmentSubmission.objects.create(
        assignment=assignment,
        student=student,
        content='我的作业内容',
    )
    assert submission.status == 'not_submitted'
    assert submission.score is None


@pytest.mark.django_db
def test_submission_unique():
    assignment = _make_assignment()
    student = User.objects.create_user(
        username='substu2', password='pass',
    )
    AssignmentSubmission.objects.create(
        assignment=assignment, student=student,
    )
    with pytest.raises(Exception):
        AssignmentSubmission.objects.create(
            assignment=assignment, student=student,
        )
```

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest apps/teaching/tests/test_models.py::test_create_assignment -v`
预期：FAIL

- [ ] **步骤 3：实现 Assignment 模型**

在 `apps/teaching/models.py` 的 ExperimentGroup 类后面追加：

```python
class Assignment(models.Model):
    """作业/任务"""

    class AssignmentType(models.TextChoices):
        HOMEWORK = 'homework', '作业'
        QUIZ = 'quiz', '测验'
        REPORT = 'report', '报告'

    teaching_class = models.ForeignKey(
        TeachingClass, on_delete=models.CASCADE,
        related_name='assignments',
    )
    title = models.CharField('标题', max_length=200)
    description = models.TextField('要求说明', blank=True)
    assignment_type = models.CharField(
        '类型', max_length=20,
        choices=AssignmentType.choices,
        default=AssignmentType.HOMEWORK,
    )
    max_score = models.DecimalField(
        '满分', max_digits=6, decimal_places=2, default=100,
    )
    due_date = models.DateTimeField('截止时间')
    allow_late = models.BooleanField('允许迟交', default=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True,
        related_name='created_assignments',
    )
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'assignments'
        verbose_name = '作业'
        verbose_name_plural = '作业'
        ordering = ['-due_date']

    def __str__(self):
        return f'{self.teaching_class.name} - {self.title}'
```

- [ ] **步骤 4：实现 AssignmentSubmission 模型**

在 Assignment 类后面追加：

```python
class AssignmentSubmission(models.Model):
    """学生作业提交"""

    class Status(models.TextChoices):
        NOT_SUBMITTED = 'not_submitted', '未提交'
        SUBMITTED = 'submitted', '已提交'
        GRADED = 'graded', '已评分'
        LATE = 'late', '迟交'

    assignment = models.ForeignKey(
        Assignment, on_delete=models.CASCADE,
        related_name='submissions',
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='assignment_submissions',
    )
    content = models.TextField('文字提交', blank=True)
    attachment = models.FileField(
        '附件', upload_to='assignment_submissions/', blank=True,
    )
    score = models.DecimalField(
        '得分', max_digits=6, decimal_places=2,
        null=True, blank=True,
    )
    feedback = models.TextField('教师反馈', blank=True)
    status = models.CharField(
        '状态', max_length=20,
        choices=Status.choices, default=Status.NOT_SUBMITTED,
    )
    submitted_at = models.DateTimeField('提交时间', null=True, blank=True)
    graded_at = models.DateTimeField('评分时间', null=True, blank=True)
    graded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name='graded_submissions',
    )
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'assignment_submissions'
        verbose_name = '作业提交'
        verbose_name_plural = '作业提交'
        ordering = ['-submitted_at']
        unique_together = [['assignment', 'student']]

    def __str__(self):
        return f'{self.student.username} - {self.assignment.title}'
```

- [ ] **步骤 5：生成迁移并运行测试**

运行：
```bash
python manage.py makemigrations teaching
python manage.py migrate teaching
pytest apps/teaching/tests/test_models.py -v
```
预期：全部 PASS

- [ ] **步骤 6：Commit**

```bash
git add apps/teaching/models.py apps/teaching/tests/test_models.py apps/teaching/migrations/
git commit -m "feat(teaching): add Assignment and AssignmentSubmission models"
```

---

### 任务 15：实现 AssignmentService

**文件：**
- 修改：`apps/teaching/services.py`
- 修改：`apps/teaching/tests/test_services.py`

- [ ] **步骤 1：编写 AssignmentService 测试**

在 `apps/teaching/tests/test_services.py` 中追加：

```python
from apps.teaching.services import AssignmentService
from apps.teaching.models import Assignment


@pytest.mark.django_db
def test_create_assignment(teacher):
    semester = Semester.objects.create(
        name='学期', code=f'ASSEM-{random.randint(10000,99999)}',
        start_date=date(2026, 2, 1), end_date=date(2026, 6, 30),
    )
    course = Course.objects.create(
        semester=semester, name='课',
        code=f'ASC-{random.randint(10000,99999)}',
    )
    cls = TeachingClass.objects.create(course=course, name='班')
    assignment = AssignmentService.create_assignment(
        user=teacher, teaching_class_id=cls.id,
        title='作业1', max_score=100,
        due_date='2026-04-01T23:59:59Z',
    )
    assert assignment.title == '作业1'
    assert assignment.created_by == teacher


@pytest.mark.django_db
def test_submit_assignment(student):
    semester = Semester.objects.create(
        name='学期', code=f'ASSEM2-{random.randint(10000,99999)}',
        start_date=date(2026, 2, 1), end_date=date(2026, 6, 30),
    )
    course = Course.objects.create(
        semester=semester, name='课',
        code=f'ASC2-{random.randint(10000,99999)}',
    )
    cls = TeachingClass.objects.create(course=course, name='班')
    assignment = Assignment.objects.create(
        teaching_class=cls, title='作业',
        max_score=100, due_date='2026-04-01T23:59:59Z',
    )
    submission = AssignmentService.submit(
        assignment_id=assignment.id,
        student=student,
        content='我的答案',
    )
    assert submission.status == 'submitted'
    assert submission.content == '我的答案'
    assert submission.submitted_at is not None


@pytest.mark.django_db
def test_grade_submission(teacher, student):
    semester = Semester.objects.create(
        name='学期', code=f'ASSEM3-{random.randint(10000,99999)}',
        start_date=date(2026, 2, 1), end_date=date(2026, 6, 30),
    )
    course = Course.objects.create(
        semester=semester, name='课',
        code=f'ASC3-{random.randint(10000,99999)}',
    )
    cls = TeachingClass.objects.create(course=course, name='班')
    assignment = Assignment.objects.create(
        teaching_class=cls, title='作业',
        max_score=100, due_date='2026-04-01T23:59:59Z',
    )
    submission = AssignmentService.submit(
        assignment_id=assignment.id,
        student=student, content='答案',
    )
    graded = AssignmentService.grade(
        submission_id=submission.id,
        teacher=teacher,
        score=85.5,
        feedback='做得不错',
    )
    assert graded.score == 85.5
    assert graded.status == 'graded'
    assert graded.graded_by == teacher
    assert graded.feedback == '做得不错'
```

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest apps/teaching/tests/test_services.py::test_create_assignment -v`
预期：FAIL

- [ ] **步骤 3：实现 AssignmentService**

在 `apps/teaching/services.py` 的 ExperimentOrchestrationService 类后面追加：

```python
from apps.teaching.models import Assignment, AssignmentSubmission


class AssignmentService:

    @staticmethod
    def create_assignment(user, teaching_class_id, **kwargs):
        return Assignment.objects.create(
            teaching_class_id=teaching_class_id,
            created_by=user,
            **kwargs,
        )

    @staticmethod
    def submit(assignment_id, student, content='', attachment=None):
        submission, _ = AssignmentSubmission.objects.get_or_create(
            assignment_id=assignment_id,
            student=student,
            defaults={'status': 'not_submitted'},
        )
        submission.content = content
        if attachment:
            submission.attachment = attachment
        submission.status = 'submitted'
        submission.submitted_at = timezone.now()
        submission.save()
        return submission

    @staticmethod
    def grade(submission_id, teacher, score, feedback=''):
        submission = AssignmentSubmission.objects.get(id=submission_id)
        submission.score = score
        submission.feedback = feedback
        submission.status = 'graded'
        submission.graded_by = teacher
        submission.graded_at = timezone.now()
        submission.save()
        return submission
```

注意：确保 `from apps.teaching.models import Assignment, AssignmentSubmission` 不与文件顶部的其他导入冲突。实际操作中，将所有 teaching model 的导入合并到文件顶部。

- [ ] **步骤 4：运行测试**

运行：`pytest apps/teaching/tests/test_services.py -v`
预期：全部 PASS

- [ ] **步骤 5：Commit**

```bash
git add apps/teaching/services.py apps/teaching/tests/test_services.py
git commit -m "feat(teaching): add AssignmentService"
```

---

## 阶段 4：成绩报告

### 任务 16：实现 GradeReportService

**文件：**
- 修改：`apps/teaching/services.py`
- 创建：`apps/teaching/tests/test_report.py`

- [ ] **步骤 1：编写报告测试**

创建 `apps/teaching/tests/test_report.py`：

```python
import pytest
import random
from datetime import date
from django.db.models import Avg, Max, Min
from apps.users.models import User
from apps.teaching.models import (
    Semester, Course, TeachingClass, StudentEnrollment,
    Assignment, AssignmentSubmission,
)
from apps.scoring.models import Experiment, ScoreSheet, ScoringMetric, MetricScore
from apps.teaching.services import (
    GradeReportService, AssignmentService,
)


def _setup_class_with_data():
    semester = Semester.objects.create(
        name='学期', code=f'RPT-SEM-{random.randint(10000,99999)}',
        start_date=date(2026, 2, 1), end_date=date(2026, 6, 30),
    )
    course = Course.objects.create(
        semester=semester, name='报告课',
        code=f'RPT-C-{random.randint(10000,99999)}',
    )
    cls = TeachingClass.objects.create(course=course, name='报告班')

    students = []
    for i in range(3):
        s = User.objects.create_user(
            username=f'rptstu{i}_{random.randint(1000,9999)}',
            password='pass', user_type='student',
        )
        StudentEnrollment.objects.create(teaching_class=cls, student=s)
        students.append(s)

    teacher = User.objects.create_user(
        username=f'rpttchr_{random.randint(1000,9999)}',
        password='pass', user_type='teacher',
    )
    return cls, students, teacher


@pytest.mark.django_db
def test_student_report():
    cls, students, teacher = _setup_class_with_data()
    student = students[0]

    experiment = Experiment.objects.create(
        name='测试实验',
        start_date='2026-03-01 00:00:00',
        teaching_class=cls,
    )
    sheet = ScoreSheet.objects.create(
        experiment=experiment,
        user=student,
        auto_score=80.0,
        final_score=80.0,
        status='finalized',
    )

    assignment = Assignment.objects.create(
        teaching_class=cls, title='作业',
        max_score=100, due_date='2026-04-01T23:59:59Z',
    )
    AssignmentService.submit(
        assignment_id=assignment.id, student=student, content='答',
    )
    AssignmentService.grade(
        submission_id=assignment.submissions.first().id,
        teacher=teacher, score=90.0,
    )

    report = GradeReportService.get_student_report(student, cls.id)
    assert 'experiment_score' in report
    assert 'assignment_score' in report
    assert 'total_score' in report
    assert report['experiment_score'] == 80.0
    assert report['assignment_score'] == 90.0


@pytest.mark.django_db
def test_class_report():
    cls, students, teacher = _setup_class_with_data()

    assignment = Assignment.objects.create(
        teaching_class=cls, title='作业',
        max_score=100, due_date='2026-04-01T23:59:59Z',
    )
    for i, student in enumerate(students):
        AssignmentService.submit(
            assignment_id=assignment.id,
            student=student, content=f'答案{i}',
        )
        AssignmentService.grade(
            submission_id=assignment.submissions.first().id,
            teacher=teacher, score=70.0 + i * 10,
        )

    report = GradeReportService.get_class_report(cls.id)
    assert 'avg_score' in report
    assert 'max_score' in report
    assert 'min_score' in report
    assert 'student_count' in report
    assert report['student_count'] == 3


@pytest.mark.django_db
def test_course_report():
    cls, students, teacher = _setup_class_with_data()

    report = GradeReportService.get_course_report(cls.course.id)
    assert 'class_reports' in report
    assert len(report['class_reports']) >= 1
```

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest apps/teaching/tests/test_report.py::test_student_report -v`
预期：FAIL

- [ ] **步骤 3：实现 GradeReportService**

在 `apps/teaching/services.py` 的 AssignmentService 类后面追加：

```python
from django.db.models import Avg, Max, Min, Q


class GradeReportService:

    @staticmethod
    def get_student_report(student, teaching_class_id):
        teaching_class = TeachingClass.objects.select_related(
            'course',
        ).get(id=teaching_class_id)
        course = teaching_class.course

        # 实验成绩
        experiment_ids = Experiment.objects.filter(
            teaching_class=teaching_class,
        ).values_list('id', flat=True)
        score_sheets = ScoreSheet.objects.filter(
            experiment_id__in=experiment_ids,
            user=student,
            status='finalized',
        )
        experiment_score = (
            score_sheets.aggregate(avg=Avg('final_score'))['avg'] or 0
        )

        # 作业成绩
        assignment_ids = Assignment.objects.filter(
            teaching_class=teaching_class,
        ).values_list('id', flat=True)
        submissions = AssignmentSubmission.objects.filter(
            assignment_id__in=assignment_ids,
            student=student,
            status='graded',
        )
        assignment_score = (
            submissions.aggregate(avg=Avg('score'))['avg'] or 0
        )

        # 加权总分
        total_score = (
            experiment_score * float(course.experiment_weight)
            + assignment_score * float(course.assignment_weight)
        )

        return {
            'student_id': student.id,
            'student_username': student.username,
            'teaching_class_id': teaching_class_id,
            'experiment_score': round(experiment_score, 2),
            'assignment_score': round(assignment_score, 2),
            'total_score': round(total_score, 2),
            'experiment_weight': float(course.experiment_weight),
            'assignment_weight': float(course.assignment_weight),
            'experiment_count': score_sheets.count(),
            'assignment_count': submissions.count(),
        }

    @staticmethod
    def get_class_report(teaching_class_id):
        teaching_class = TeachingClass.objects.select_related(
            'course',
        ).get(id=teaching_class_id)
        enrollments = StudentEnrollment.objects.filter(
            teaching_class=teaching_class,
            status='enrolled',
        ).select_related('student')

        scores = []
        for enrollment in enrollments:
            report = GradeReportService.get_student_report(
                enrollment.student, teaching_class_id,
            )
            scores.append(report)

        if not scores:
            return {
                'teaching_class_id': teaching_class_id,
                'student_count': 0,
                'avg_score': 0,
                'max_score': 0,
                'min_score': 0,
                'students': [],
            }

        total_scores = [s['total_score'] for s in scores]

        return {
            'teaching_class_id': teaching_class_id,
            'student_count': len(scores),
            'avg_score': round(sum(total_scores) / len(total_scores), 2),
            'max_score': round(max(total_scores), 2),
            'min_score': round(min(total_scores), 2),
            'students': scores,
        }

    @staticmethod
    def get_course_report(course_id):
        course = Course.objects.get(id=course_id)
        classes = TeachingClass.objects.filter(course=course)

        class_reports = []
        for cls in classes:
            report = GradeReportService.get_class_report(cls.id)
            class_reports.append(report)

        return {
            'course_id': course_id,
            'course_name': course.name,
            'class_count': len(class_reports),
            'class_reports': class_reports,
        }
```

注意：将 `from django.db.models import Avg, Max, Min, Q` 合并到文件顶部导入。

- [ ] **步骤 4：运行测试**

运行：`pytest apps/teaching/tests/test_report.py -v`
预期：全部 PASS

- [ ] **步骤 5：Commit**

```bash
git add apps/teaching/services.py apps/teaching/tests/test_report.py
git commit -m "feat(teaching): add GradeReportService with real-time aggregation"
```

---

## 阶段 5：集成验证

### 任务 17：API 集成测试

**文件：**
- 创建：`apps/teaching/tests/test_api.py`

- [ ] **步骤 1：编写 API 测试**

创建 `apps/teaching/tests/test_api.py`：

```python
import pytest
from datetime import date
from rest_framework.test import APIClient
from apps.users.models import User
from apps.teaching.models import Semester, Course, TeachingClass


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def teacher():
    return User.objects.create_user(
        username='api_teacher', password='pass', user_type='teacher',
    )


@pytest.fixture
def student():
    return User.objects.create_user(
        username='api_student', password='pass', user_type='student',
    )


@pytest.fixture
def setup_data(teacher):
    semester = Semester.objects.create(
        name='API 学期', code='API-SEM',
        start_date=date(2026, 2, 1), end_date=date(2026, 6, 30),
    )
    course = Course.objects.create(
        semester=semester, name='API 课', code='API-C',
    )
    course.teachers.add(teacher)
    cls = TeachingClass.objects.create(
        course=course, name='API 班',
    )
    return {'semester': semester, 'course': course, 'class': cls}


@pytest.mark.django_db
def test_semester_crud(api_client, teacher):
    api_client.force_authenticate(user=teacher)
    # Create
    resp = api_client.post('/api/v1/teaching/semesters/', {
        'name': '新学期', 'code': 'API-NEW-SEM',
        'start_date': '2026-09-01', 'end_date': '2027-01-15',
    })
    assert resp.status_code == 201
    semester_id = resp.data['id']
    # List
    resp = api_client.get('/api/v1/teaching/semesters/')
    assert resp.status_code == 200
    # Activate
    resp = api_client.post(
        f'/api/v1/teaching/semesters/{semester_id}/activate/',
    )
    assert resp.status_code == 200


@pytest.mark.django_db
def test_student_enroll(api_client, student, setup_data):
    cls = setup_data['class']
    api_client.force_authenticate(user=student)
    resp = api_client.post(
        f'/api/v1/teaching/classes/{cls.id}/enroll/',
        {'enrollment_code': cls.enrollment_code},
    )
    assert resp.status_code == 200
    assert resp.data['code'] == 0


@pytest.mark.django_db
def test_student_enroll_wrong_code(api_client, student, setup_data):
    cls = setup_data['class']
    api_client.force_authenticate(user=student)
    resp = api_client.post(
        f'/api/v1/teaching/classes/{cls.id}/enroll/',
        {'enrollment_code': 'WRONG'},
    )
    assert resp.status_code == 400


@pytest.mark.django_db
def test_assignment_flow(api_client, teacher, student, setup_data):
    cls = setup_data['class']
    # Teacher creates assignment
    api_client.force_authenticate(user=teacher)
    resp = api_client.post('/api/v1/teaching/assignments/', {
        'teaching_class': cls.id,
        'title': 'API 测试作业',
        'max_score': 100,
        'due_date': '2026-04-01T23:59:59Z',
    })
    assert resp.status_code == 201
    assignment_id = resp.data['id']

    # Student submits
    api_client.force_authenticate(user=student)
    resp = api_client.post(
        f'/api/v1/teaching/assignments/{assignment_id}/submit/',
        {'content': '我的答案'},
    )
    assert resp.status_code == 200

    # Teacher grades
    submission_id = resp.data['data']['id']
    api_client.force_authenticate(user=teacher)
    resp = api_client.post(
        f'/api/v1/teaching/submissions/{submission_id}/grade/',
        {'score': 95.0, 'feedback': '很好'},
    )
    assert resp.status_code == 200
    assert resp.data['data']['score'] == '95.00'
```

- [ ] **步骤 2：运行 API 测试**

运行：`pytest apps/teaching/tests/test_api.py -v`
预期：全部 PASS

- [ ] **步骤 3：Commit**

```bash
git add apps/teaching/tests/test_api.py
git commit -m "test(teaching): add API integration tests"
```

---

### 任务 18：最终验证

- [ ] **步骤 1：运行全部教学模块测试**

运行：`pytest apps/teaching/tests/ -v`
预期：全部 PASS

- [ ] **步骤 2：运行全部项目测试**

运行：`pytest apps/ -v`
预期：全部 PASS

- [ ] **步骤 3：Django 系统检查**

运行：`python manage.py check`
预期：无报错

- [ ] **步骤 4：验证迁移完整性**

运行：`python manage.py migrate --run-syncdb`
预期：无报错

---

## 自检清单

### 规格覆盖度

| 规格章节 | 对应任务 |
|---------|---------|
| Semester 模型 | 任务 2 |
| Course 模型（M2M teachers） | 任务 3 |
| TeachingClass 模型（自动选课码） | 任务 4 |
| StudentEnrollment 模型 | 任务 5 |
| scoring.Experiment 改造 | 任务 12（步骤 8） |
| 组织层级服务层 | 任务 7 |
| 序列化器 | 任务 8 |
| 权限类 | 任务 9 |
| API 视图和路由 | 任务 10 |
| Admin 配置 | 任务 11 |
| ExperimentTemplate 模型 | 任务 12 |
| ExperimentGroup 模型 | 任务 12 |
| ExperimentOrchestrationService | 任务 13 |
| Assignment 模型 | 任务 14 |
| AssignmentSubmission 模型 | 任务 14 |
| AssignmentService | 任务 15 |
| GradeReportService | 任务 16 |
| API 集成测试 | 任务 17 |
| 最终验证 | 任务 18 |

### 占位符检查

- 无 "TBD"、"TODO" 等占位符
- 所有代码步骤包含完整代码
- 所有命令有明确的预期输出

### 类型一致性

- 模型字段名在各处一致
- 服务方法签名一致
- API 响应格式统一 `{code, message, data}`

---

## 完成标志

- [ ] 4 级组织体系可创建、管理
- [ ] 学生可通过选课码加入班级
- [ ] 实验可自动分组、批量分配角色
- [ ] 教师可布置作业、学生可提交、教师可评分
- [ ] 成绩报告实时聚合可查
- [ ] 所有测试通过
- [ ] Admin 界面正常工作
- [ ] API 端点可正常调用
