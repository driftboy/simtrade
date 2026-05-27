# 单证管理三级权限 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 给 Document 增加 `teaching_class` FK，实现 admin/teacher/student 三级文档可见性。

**架构：** Document 新增 `teaching_class` 外键指向 TeachingClass。`get_queryset()` 按 user_type 分流：admin 查全部、teacher 按班级课程关联过滤、student 查自己创建的。`create()` 自动从学生选课记录填入 `teaching_class`。

**技术栈：** Django ORM, Django REST Framework, pytest/django.test

---

## 文件结构

| 文件 | 职责 |
|------|------|
| `apps/documents/models.py:156` | 新增 `teaching_class` FK 字段 |
| `apps/documents/migrations/0005_document_teaching_class.py` | 自动生成的 migration |
| `apps/documents/views.py:30-43` | `get_queryset()` 三级权限 |
| `apps/documents/views.py:65-105` | `create()` 自动填入 `teaching_class` |
| `apps/documents/serializers.py:42-57` | 序列化器增加 `teaching_class` 字段 |
| `apps/documents/tests/test_api.py` | 新增权限测试用例 |

---

### 任务 1：Model — 新增 teaching_class 字段

**文件：**
- 修改：`apps/documents/models.py:156`（在 `reviewed_by` 字段后）
- 创建：`apps/documents/migrations/0005_*.py`（自动生成）

- [ ] **步骤 1：编写失败测试**

在 `apps/documents/tests/test_models.py` 末尾添加：

```python
class DocumentTeachingClassTest(TestCase):
    def test_document_can_link_teaching_class(self):
        from apps.documents.models import Document, DocumentTemplate
        doc = Document.objects.create(
            template=DocumentTemplate.objects.create(
                code='test_tc', name='测试', content='<p></p>'
            ),
            data='{}',
        )
        # teaching_class 应该是可空的
        self.assertIsNone(doc.teaching_class)
```

运行：`python manage.py test apps.documents.tests.test_models.DocumentTeachingClassTest -v 2`
预期：PASS（字段还没加，但 `assertIsNone` 对不存在的属性会报 `AttributeError`）

- [ ] **步骤 2：在 Document 模型中添加字段**

在 `apps/documents/models.py` 的 `reviewed_by` 字段（第 163 行）之后添加：

```python
    teaching_class = models.ForeignKey(
        'teaching.TeachingClass',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='documents',
        verbose_name='所属班级',
    )
```

- [ ] **步骤 3：生成并执行 migration**

```bash
python manage.py makemigrations documents --name document_teaching_class
python manage.py migrate
```

预期：`apps/documents/migrations/0005_document_teaching_class.py` 生成成功，migrate 无报错。

- [ ] **步骤 4：运行测试确认通过**

```bash
python manage.py test apps.documents.tests.test_models.DocumentTeachingClassTest -v 2
```
预期：PASS

- [ ] **步骤 5：Commit**

```bash
git add apps/documents/models.py apps/documents/migrations/0005_document_teaching_class.py apps/documents/tests/test_models.py
git commit -m "feat(documents): add teaching_class FK to Document model"
```

---

### 任务 2：序列化器 — 暴露 teaching_class 字段

**文件：**
- 修改：`apps/documents/serializers.py:42-57`

- [ ] **步骤 1：修改 DocumentSerializer**

在 `apps/documents/serializers.py` 的 `DocumentSerializer` 中，`fields` 列表增加 `'teaching_class'`：

```python
fields = ['id', 'template', 'template_name', 'template_code',
          'status', 'status_display', 'data', 'teaching_class',
          'created_by', 'reviewed_by',
          'auto_validation_result', 'manual_review_status',
          'manual_review_comment', 'submitted_at', 'reviewed_at',
          'created_at', 'updated_at', 'validations']
```

注意：`teaching_class` 是 FK，DRF 默认序列化为 ID，不需要额外添加 SerializerMethodField。

- [ ] **步骤 2：运行已有测试确认不破坏**

```bash
python manage.py test apps.documents.tests.test_serializers -v 2
```
预期：全部 PASS

- [ ] **步骤 3：Commit**

```bash
git add apps/documents/serializers.py
git commit -m "feat(documents): expose teaching_class in DocumentSerializer"
```

---

### 任务 3：View — get_queryset 三级权限

**文件：**
- 修改：`apps/documents/views.py:30-43`

- [ ] **步骤 1：编写失败测试**

在 `apps/documents/tests/test_api.py` 末尾添加：

```python
class DocumentVisibilityTest(TestCase):
    """测试单证三级可见性"""

    def setUp(self):
        from apps.teaching.models import Semester, Course, TeachingClass, StudentEnrollment
        from apps.documents.models import Document, DocumentTemplate

        self.client = APIClient()

        # 创建模板
        self.template = DocumentTemplate.objects.create(
            code='vis_test', name='可见性测试', content='<p></p>'
        )

        # 创建 admin 用户
        self.admin = User.objects.create_user(
            username='admin1', email='admin1@test.com',
            password='pass', user_type='admin', is_staff=True,
        )

        # 创建 teacher 用户 + 课程 + 班级
        self.teacher = User.objects.create_user(
            username='teacher1', email='teacher1@test.com',
            password='pass', user_type='teacher',
        )
        semester = Semester.objects.create(
            name='2026春', code='2026SP',
            start_date='2026-02-01', end_date='2026-06-30',
        )
        self.course = Course.objects.create(
            semester=semester, name='国际贸易实务', code='IR101',
        )
        self.course.teachers.add(self.teacher)
        self.tc = TeachingClass.objects.create(
            course=self.course, name='A班', enrollment_code='AAAA1111',
        )

        # 创建 student 用户并选课
        self.student = User.objects.create_user(
            username='student1', email='student1@test.com',
            password='pass', user_type='student',
        )
        StudentEnrollment.objects.create(
            teaching_class=self.tc, student=self.student,
        )

        # 创建另一个不在班级的学生
        self.other_student = User.objects.create_user(
            username='student2', email='student2@test.com',
            password='pass', user_type='student',
        )

        # 创建 3 份单证
        # student1 的课堂单证
        self.doc_in_class = Document.objects.create(
            template=self.template, created_by=self.student,
            teaching_class=self.tc, data='{}',
        )
        # student1 的无班级单证
        self.doc_no_class = Document.objects.create(
            template=self.template, created_by=self.student,
            data='{}',
        )
        # student2 的单证（不在班级里）
        self.doc_other = Document.objects.create(
            template=self.template, created_by=self.other_student,
            data='{}',
        )

    def test_admin_sees_all(self):
        """admin 可以看到所有单证"""
        self.client.force_authenticate(user=self.admin)
        resp = self.client.get('/api/v1/documents/documents/')
        ids = [d['id'] for d in resp.json()['data']]
        self.assertIn(self.doc_in_class.id, ids)
        self.assertIn(self.doc_no_class.id, ids)
        self.assertIn(self.doc_other.id, ids)

    def test_teacher_sees_class_docs_only(self):
        """teacher 只能看到自己班级的单证"""
        self.client.force_authenticate(user=self.teacher)
        resp = self.client.get('/api/v1/documents/documents/')
        ids = [d['id'] for d in resp.json()['data']]
        self.assertIn(self.doc_in_class.id, ids)
        self.assertNotIn(self.doc_no_class.id, ids)
        self.assertNotIn(self.doc_other.id, ids)

    def test_student_sees_own_docs_only(self):
        """student 只能看到自己的单证"""
        self.client.force_authenticate(user=self.student)
        resp = self.client.get('/api/v1/documents/documents/')
        ids = [d['id'] for d in resp.json()['data']]
        self.assertIn(self.doc_in_class.id, ids)
        self.assertIn(self.doc_no_class.id, ids)
        self.assertNotIn(self.doc_other.id, ids)

    def test_filter_by_transaction_id(self):
        """所有角色都可以用 transaction_id 过滤"""
        self.client.force_authenticate(user=self.admin)
        resp = self.client.get('/api/v1/documents/documents/?transaction_id=99999')
        self.assertEqual(len(resp.json()['data']), 0)

    def test_filter_by_teaching_class_id(self):
        """teacher 可以按班级 ID 过滤"""
        self.client.force_authenticate(user=self.teacher)
        resp = self.client.get(f'/api/v1/documents/documents/?teaching_class_id={self.tc.id}')
        ids = [d['id'] for d in resp.json()['data']]
        self.assertIn(self.doc_in_class.id, ids)
        self.assertEqual(len(ids), 1)
```

运行：`python manage.py test apps.documents.tests.test_api.DocumentVisibilityTest -v 2`
预期：FAIL（当前 get_queryset 不按三级权限过滤）

- [ ] **步骤 2：实现 get_queryset 三级权限**

替换 `apps/documents/views.py` 的 `get_queryset` 方法（第 30-43 行）：

```python
    def get_queryset(self):
        user = self.request.user
        transaction_id = self.request.query_params.get('transaction_id')
        teaching_class_id = self.request.query_params.get('teaching_class_id')

        if user.user_type == 'admin':
            queryset = Document.objects.all()
        elif user.user_type == 'teacher':
            queryset = Document.objects.filter(
                teaching_class__course__teachers=user
            )
        else:
            queryset = Document.objects.filter(created_by=user)

        if transaction_id:
            queryset = queryset.filter(transaction_id=transaction_id)
        if teaching_class_id:
            queryset = queryset.filter(teaching_class_id=teaching_class_id)

        return queryset.select_related(
            'template', 'created_by', 'reviewed_by', 'teaching_class'
        )
```

- [ ] **步骤 3：运行测试确认通过**

```bash
python manage.py test apps.documents.tests.test_api.DocumentVisibilityTest -v 2
```
预期：全部 PASS

- [ ] **步骤 4：运行全部 documents 测试确认不破坏**

```bash
python manage.py test apps.documents -v 2
```
预期：全部 PASS

- [ ] **步骤 5：Commit**

```bash
git add apps/documents/views.py apps/documents/tests/test_api.py
git commit -m "feat(documents): implement 3-level document visibility (admin/teacher/student)"
```

---

### 任务 4：View — create() 自动填入 teaching_class

**文件：**
- 修改：`apps/documents/views.py:65-105`

- [ ] **步骤 1：编写失败测试**

在 `apps/documents/tests/test_api.py` 的 `DocumentVisibilityTest` 类中追加：

```python
    def test_student_create_auto_fills_teaching_class(self):
        """学生创建单证时自动填入 teaching_class"""
        from apps.teaching.models import StudentEnrollment
        self.client.force_authenticate(user=self.student)
        resp = self.client.post('/api/v1/documents/documents/', {
            'template': self.template.id,
            'data': {'invoice_no': 'AUTO001'},
        }, format='json')
        self.assertEqual(resp.status_code, 200)
        doc_id = resp.json()['data']['id']
        doc = Document.objects.get(id=doc_id)
        self.assertEqual(doc.teaching_class, self.tc)

    def test_student_without_enrollment_creates_without_class(self):
        """没有选课的学生创建单证时 teaching_class 为 None"""
        self.client.force_authenticate(user=self.other_student)
        resp = self.client.post('/api/v1/documents/documents/', {
            'template': self.template.id,
            'data': {},
        }, format='json')
        self.assertEqual(resp.status_code, 200)
        doc_id = resp.json()['data']['id']
        doc = Document.objects.get(id=doc_id)
        self.assertIsNone(doc.teaching_class)
```

运行：`python manage.py test apps.documents.tests.test_api.DocumentVisibilityTest.test_student_create_auto_fills_teaching_class apps.documents.tests.test_api.DocumentVisibilityTest.test_student_without_enrollment_creates_without_class -v 2`
预期：FAIL（当前 create 不设置 teaching_class）

- [ ] **步骤 2：修改 create() 方法**

在 `apps/documents/views.py` 的 `create()` 方法中，在 `Document.objects.create(...)` 调用前添加自动填入逻辑。在文件顶部 import 区域添加：

```python
from apps.teaching.models import StudentEnrollment
```

修改 `create()` 方法中的 `Document.objects.create(...)` 部分（原第 94-98 行），替换为：

```python
        # 自动填入 teaching_class（学生）
        teaching_class = None
        if user.user_type == 'student':
            enrollment = StudentEnrollment.objects.filter(
                student=user,
                status='enrolled',
            ).select_related('teaching_class').first()
            if enrollment:
                teaching_class = enrollment.teaching_class

        document = Document.objects.create(
            template=template,
            created_by=user,
            teaching_class=teaching_class,
            data=json.dumps(merged_data, ensure_ascii=False)
        )
```

- [ ] **步骤 3：运行测试确认通过**

```bash
python manage.py test apps.documents.tests.test_api.DocumentVisibilityTest -v 2
```
预期：全部 PASS

- [ ] **步骤 4：运行全部 documents 测试**

```bash
python manage.py test apps.documents -v 2
```
预期：全部 PASS

- [ ] **步骤 5：Commit**

```bash
git add apps/documents/views.py apps/documents/tests/test_api.py
git commit -m "feat(documents): auto-fill teaching_class on student document creation"
```

---

## 验证

完成所有任务后，执行以下端到端验证：

1. `python manage.py migrate` — 确认 migration 无问题
2. `python manage.py test apps.documents -v 2` — 全部测试通过
3. `python manage.py init_sample_trade` — 样本数据命令无报错，样本单证 `teaching_class=None`
4. 用 admin 账号访问 `/api/v1/documents/documents/` 确认返回所有单证
5. 用 teacher 账号访问确认只返回自己班级的单证
6. 用 student 账号访问确认只返回自己的单证
