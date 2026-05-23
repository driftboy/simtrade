# 教学管理系统设计文档

**版本**: 1.0
**日期**: 2026-05-23
**状态**: 待审核

---

## 1. 概述

### 1.1 设计目标

实现 SimTrade 平台的教学管理功能，支持四级组织体系（学期→课程→班级→实验），包含实验编排、作业/任务管理和成绩报告三大核心模块。

### 1.2 核心决策

| 决策点 | 选择 | 理由 |
|--------|------|------|
| 架构模式 | 独立 App (`teaching/`) | 教学管理与评分、角色解耦，职责清晰 |
| 组织层级 | 四级：学期→课程→班级→实验 | 覆盖高校完整教学场景 |
| 教师关系 | Course.teachers M2M | 支持合班授课、双师教学 |
| 成绩报告 | 实时聚合查询 | 灵活，数据始终最新 |
| 命名规范 | TeachingClass + StudentEnrollment | 语义明确，避免与 Python class 混淆 |
| Experiment 改造 | 加 `teaching_class` FK | 复用现有模型，最小改动 |

### 1.3 实现分阶段

| 阶段 | 内容 |
|------|------|
| 阶段 1 | 组织层级（Semester/Course/TeachingClass/StudentEnrollment）+ Experiment 改造 |
| 阶段 2 | 实验编排（ExperimentTemplate/ExperimentGroup） |
| 阶段 3 | 作业/任务（Assignment/AssignmentSubmission） |
| 阶段 4 | 成绩报告（GradeReportService） |

---

## 2. 数据模型设计

### 2.1 模型关系图

```
Semester (学期)
  └── Course (课程) [teachers M2M]
        └── TeachingClass (班级) [course FK]
              ├── StudentEnrollment (学生选课) [teaching_class + student FK]
              │
              ├── Experiment (改造 scoring.Experiment, 加 teaching_class FK)
              │     └── ExperimentGroup (实验分组 ↔ roles.Company)
              │
              └── Assignment (作业/任务)
                    └── AssignmentSubmission (学生提交)
```

### 2.2 Semester 模型

```python
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
        choices=Status.choices, default=Status.UPCOMING
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True,
        related_name='created_semesters'
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
                is_active=True
            ).exclude(pk=self.pk).count()
            if active_count > 0:
                raise ValidationError('只能有一个激活的学期')
```

### 2.3 Course 模型

```python
class Course(models.Model):
    """课程"""

    class Status(models.TextChoices):
        UPCOMING = 'upcoming', '未开始'
        ACTIVE = 'active', '进行中'
        ENDED = 'ended', '已结束'

    semester = models.ForeignKey(
        Semester, on_delete=models.PROTECT,
        related_name='courses'
    )
    name = models.CharField('课程名称', max_length=200)
    code = models.CharField('课程代码', max_length=20)
    teachers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='teaching_courses',
        verbose_name='授课教师',
        limit_choices_to={'user_type': 'teacher'}
    )
    description = models.TextField('课程简介', blank=True)
    experiment_weight = models.DecimalField(
        '实验成绩权重', max_digits=5, decimal_places=2, default=0.60,
        help_text='实验成绩在总评中的占比，0.00-1.00'
    )
    assignment_weight = models.DecimalField(
        '作业成绩权重', max_digits=5, decimal_places=2, default=0.40,
        help_text='作业成绩在总评中的占比，0.00-1.00'
    )
    status = models.CharField(
        '状态', max_length=20,
        choices=Status.choices, default=Status.UPCOMING
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True,
        related_name='created_courses'
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

### 2.4 TeachingClass 模型

```python
class TeachingClass(models.Model):
    """教学班级"""

    class Status(models.TextChoices):
        UPCOMING = 'upcoming', '未开始'
        ACTIVE = 'active', '进行中'
        ENDED = 'ended', '已结束'

    course = models.ForeignKey(
        Course, on_delete=models.CASCADE,
        related_name='classes'
    )
    name = models.CharField('班级名称', max_length=100)
    capacity = models.IntegerField('最大人数', default=40)
    enrollment_code = models.CharField(
        '选课码', max_length=20, unique=True
    )
    status = models.CharField(
        '状态', max_length=20,
        choices=Status.choices, default=Status.UPCOMING
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True,
        related_name='created_classes'
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
        import random
        import string
        while True:
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            if not TeachingClass.objects.filter(enrollment_code=code).exists():
                return code
```

### 2.5 StudentEnrollment 模型

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
        related_name='enrollments'
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='enrollments'
    )
    role = models.CharField(
        '角色', max_length=20,
        choices=Role.choices, default=Role.STUDENT
    )
    status = models.CharField(
        '状态', max_length=20,
        choices=Status.choices, default=Status.ENROLLED
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

### 2.6 ExperimentTemplate 模型

```python
class ExperimentTemplate(models.Model):
    """实验模板 — 可复用的实验配置"""

    name = models.CharField('模板名称', max_length=200)
    description = models.TextField('模板描述', blank=True)
    config = models.JSONField('预设配置', default=dict, help_text=(
        '可包含：roles_per_group（每组角色数）、'
        'allowed_trade_terms（允许的贸易术语）、'
        'scoring_weights（评分权重覆盖）等'
    ))
    is_public = models.BooleanField('是否公开', default=False)
    use_count = models.IntegerField('使用次数', default=0)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True,
        related_name='created_experiment_templates'
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

### 2.7 ExperimentGroup 模型

```python
class ExperimentGroup(models.Model):
    """实验分组 — 对应 roles.Company"""

    experiment = models.ForeignKey(
        'scoring.Experiment',
        on_delete=models.CASCADE,
        related_name='groups'
    )
    company = models.OneToOneField(
        'roles.Company',
        on_delete=models.CASCADE,
        related_name='experiment_group'
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

### 2.8 Assignment 模型

```python
class Assignment(models.Model):
    """作业/任务"""

    class AssignmentType(models.TextChoices):
        HOMEWORK = 'homework', '作业'
        QUIZ = 'quiz', '测验'
        REPORT = 'report', '报告'

    teaching_class = models.ForeignKey(
        TeachingClass, on_delete=models.CASCADE,
        related_name='assignments'
    )
    title = models.CharField('标题', max_length=200)
    description = models.TextField('要求说明', blank=True)
    assignment_type = models.CharField(
        '类型', max_length=20,
        choices=AssignmentType.choices, default=AssignmentType.HOMEWORK
    )
    max_score = models.DecimalField('满分', max_digits=6, decimal_places=2, default=100)
    due_date = models.DateTimeField('截止时间')
    allow_late = models.BooleanField('允许迟交', default=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True,
        related_name='created_assignments'
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

### 2.9 AssignmentSubmission 模型

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
        related_name='submissions'
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='assignment_submissions'
    )
    content = models.TextField('文字提交', blank=True)
    attachment = models.FileField(
        '附件', upload_to='assignment_submissions/', blank=True
    )
    score = models.DecimalField('得分', max_digits=6, decimal_places=2, null=True, blank=True)
    feedback = models.TextField('教师反馈', blank=True)
    status = models.CharField(
        '状态', max_length=20,
        choices=Status.choices, default=Status.NOT_SUBMITTED
    )
    submitted_at = models.DateTimeField('提交时间', null=True, blank=True)
    graded_at = models.DateTimeField('评分时间', null=True, blank=True)
    graded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name='graded_submissions'
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

---

## 3. Experiment 模型改造

### 3.1 新增字段

在 `apps/scoring/models.py` 的 `Experiment` 模型上新增：

| 字段 | 类型 | 说明 |
|------|------|------|
| teaching_class | FK(TeachingClass, null=True) | 所属班级 |
| template | FK(ExperimentTemplate, null=True) | 来源模板 |
| group_config | JSONField(default=dict) | 分组配置 |

### 3.2 迁移策略

- `teaching_class` 允许 null=True（过渡期），旧实验保留为未归档
- 无需数据迁移脚本，旧实验 null 即表示"独立实验"
- 后续可选：移除 null=True 约束

---

## 4. 服务层设计

### 4.1 SemesterService

```python
class SemesterService:
    @staticmethod
    def create_semester(user, name, code, start_date, end_date):
        """创建学期"""

    @staticmethod
    def activate_semester(semester_id, user):
        """激活学期（自动停用其他学期）"""

    @staticmethod
    def get_active_semester():
        """获取当前激活学期"""
```

### 4.2 CourseService

```python
class CourseService:
    @staticmethod
    def create_course(user, semester_id, name, code, teacher_ids=None, **kwargs):
        """创建课程（可指定多个教师）"""

    @staticmethod
    def get_teacher_courses(teacher):
        """获取教师的所有课程"""

    @staticmethod
    def get_student_courses(student):
        """通过选课记录获取学生的课程"""
```

### 4.3 TeachingClassService

```python
class TeachingClassService:
    @staticmethod
    def create_class(user, course_id, name, capacity=40):
        """创建班级（自动生成选课码）"""

    @staticmethod
    def enroll_student(teaching_class_id, student, enrollment_code=None):
        """学生选课（通过选课码）"""

    @staticmethod
    def drop_student(enrollment_id, user):
        """退课"""

    @staticmethod
    def get_class_students(teaching_class_id):
        """获取班级学生列表"""
```

### 4.4 ExperimentOrchestrationService

```python
class ExperimentOrchestrationService:
    @staticmethod
    def create_from_template(template_id, teaching_class_id, user, **overrides):
        """从模板创建实验"""

    @staticmethod
    def auto_group(experiment_id, group_size=5):
        """自动分组（为未分组学生创建 Company 和 ExperimentGroup）"""

    @staticmethod
    def batch_assign_roles(experiment_id):
        """批量分配角色（为每组内学生分配不同贸易角色）"""

    @staticmethod
    def get_experiment_groups(experiment_id):
        """获取实验的所有分组"""
```

### 4.5 AssignmentService

```python
class AssignmentService:
    @staticmethod
    def create_assignment(user, teaching_class_id, **kwargs):
        """布置作业"""

    @staticmethod
    def submit(assignment_id, student, content='', attachment=None):
        """学生提交作业"""

    @staticmethod
    def grade(submission_id, teacher, score, feedback=''):
        """教师评分"""
```

### 4.6 GradeReportService

```python
class GradeReportService:
    @staticmethod
    def get_student_report(student, teaching_class_id):
        """学生个人报告
        聚合：实验成绩（ScoreSheet）+ 作业成绩（AssignmentSubmission）
        按课程权重加权计算总分
        返回: dict {experiment_score, assignment_score, total_score, details}
        """

    @staticmethod
    def get_class_report(teaching_class_id):
        """班级整体报告
        返回: dict {avg, max, min, distribution, rankings}
        """

    @staticmethod
    def get_course_report(course_id):
        """课程汇总：各班级成绩对比
        返回: dict {class_reports: [...], comparison: {...}}
        """
```

---

## 5. API 接口设计

### 5.1 学期管理

| 端点 | 方法 | 说明 | 权限 |
|------|------|------|------|
| `/api/v1/teaching/semesters/` | GET | 学期列表 | 登录 |
| `/api/v1/teaching/semesters/` | POST | 创建学期 | 教师/管理员 |
| `/api/v1/teaching/semesters/{id}/` | GET | 学期详情 | 登录 |
| `/api/v1/teaching/semesters/{id}/activate/` | POST | 激活学期 | 教师/管理员 |

### 5.2 课程管理

| 端点 | 方法 | 说明 | 权限 |
|------|------|------|------|
| `/api/v1/teaching/courses/` | GET | 课程列表（教师看自己，学生看已选） | 登录 |
| `/api/v1/teaching/courses/` | POST | 创建课程 | 教师/管理员 |
| `/api/v1/teaching/courses/{id}/` | GET/PUT | 课程详情/更新 | 教师/管理员 |

### 5.3 班级管理

| 端点 | 方法 | 说明 | 权限 |
|------|------|------|------|
| `/api/v1/teaching/classes/` | GET | 班级列表 | 登录 |
| `/api/v1/teaching/classes/` | POST | 创建班级 | 教师/管理员 |
| `/api/v1/teaching/classes/{id}/` | GET | 班级详情 | 登录 |
| `/api/v1/teaching/classes/{id}/enroll/` | POST | 学生选课（需选课码） | 学生 |
| `/api/v1/teaching/classes/{id}/enrollments/` | GET | 班级选课列表 | 教师 |
| `/api/v1/teaching/classes/{id}/drop/` | POST | 退课 | 学生 |

### 5.4 实验模板

| 端点 | 方法 | 说明 | 权限 |
|------|------|------|------|
| `/api/v1/teaching/experiment-templates/` | GET | 模板列表（含公开模板） | 教师 |
| `/api/v1/teaching/experiment-templates/` | POST | 创建模板 | 教师 |
| `/api/v1/teaching/experiment-templates/{id}/` | GET/PUT/DELETE | 模板详情/更新/删除 | 本人/管理员 |

### 5.5 实验编排

| 端点 | 方法 | 说明 | 权限 |
|------|------|------|------|
| `/api/v1/teaching/experiments/` | GET | 实验列表（按班级筛选） | 登录 |
| `/api/v1/teaching/experiments/{id}/groups/` | GET | 实验分组列表 | 登录 |
| `/api/v1/teaching/experiments/{id}/auto-group/` | POST | 自动分组 | 教师 |
| `/api/v1/teaching/experiments/{id}/assign-roles/` | POST | 批量分配角色 | 教师 |

### 5.6 作业管理

| 端点 | 方法 | 说明 | 权限 |
|------|------|------|------|
| `/api/v1/teaching/assignments/` | GET | 作业列表（按班级筛选） | 登录 |
| `/api/v1/teaching/assignments/` | POST | 布置作业 | 教师 |
| `/api/v1/teaching/assignments/{id}/` | GET | 作业详情 | 登录 |
| `/api/v1/teaching/assignments/{id}/submit/` | POST | 提交作业 | 学生 |
| `/api/v1/teaching/assignments/{id}/submissions/` | GET | 提交列表 | 教师 |
| `/api/v1/teaching/submissions/{id}/grade/` | POST | 评分 | 教师 |

### 5.7 成绩报告

| 端点 | 方法 | 说明 | 权限 |
|------|------|------|------|
| `/api/v1/teaching/classes/{id}/my-report/` | GET | 学生个人报告 | 本人 |
| `/api/v1/teaching/classes/{id}/report/` | GET | 班级整体报告 | 教师 |
| `/api/v1/teaching/courses/{id}/report/` | GET | 课程汇总报告 | 教师 |

### 5.8 响应格式

所有接口遵循项目统一格式：

```json
{
  "code": 0,
  "message": "success",
  "data": {}
}
```

---

## 6. 迁移策略

### 6.1 迁移步骤

```
阶段 1: 创建 teaching App + 组织层级模型
  ├── 创建 apps/teaching/ 目录结构
  ├── 实现 Semester, Course, TeachingClass, StudentEnrollment
  └── 改造 scoring.Experiment 新增 teaching_class FK

阶段 2: 实验编排
  ├── 实现 ExperimentTemplate 模型
  ├── 实现 ExperimentGroup 模型
  └── 实现 ExperimentOrchestrationService

阶段 3: 作业/任务
  ├── 实现 Assignment 模型
  ├── 实现 AssignmentSubmission 模型
  └── 实现 AssignmentService

阶段 4: 成绩报告
  ├── 实现 GradeReportService
  └── 实现报告 API 端点
```

### 6.2 scoring.Experiment 改造

- 新增字段均允许 null=True，无需数据迁移
- 旧 Experiment 的 teaching_class=null 表示"独立实验"
- 不影响现有 ScoreSheet、ExperimentScoringConfig 功能

---

## 7. 测试策略

### 7.1 单元测试

- `apps/teaching/tests/test_models.py` — 模型验证（唯一性、约束、clean 方法）
- `apps/teaching/tests/test_services.py` — 服务层逻辑
- `apps/teaching/tests/test_serializers.py` — 序列化器验证

### 7.2 API 测试

- `apps/teaching/tests/test_api.py` — 端点 CRUD + 权限验证
- `apps/teaching/tests/test_permissions.py` — 学生/教师/管理员权限隔离

### 7.3 集成测试

- 学生选课 → 被分配到实验 → 完成实验 → 查看报告（完整流程）
- 教师创建课程 → 布置作业 → 学生提交 → 教师评分 → 生成报告
- 自动分组 + 批量角色分配

### 7.4 迁移测试

- 验证 scoring.Experiment 新增字段不影响现有功能
- 旧实验（teaching_class=null）仍可正常使用

---

## 8. 前端集成（简要）

### 8.1 教师端

- 课程管理页面（学期/课程/班级 CRUD）
- 实验编排页面（模板选择、分组、角色分配）
- 作业管理页面（布置、批改）
- 成绩报告页面（班级统计、学生详情）

### 8.2 学生端

- 选课页面（输入选课码加入班级）
- 作业页面（查看、提交）
- 成绩页面（查看个人报告）

---

## 9. 后续扩展

- 教学资源管理（文件上传、PPT、文档）
- 考勤管理
- 教学评价（学生对课程/教师评价）
- 通知推送（作业截止提醒、实验开始通知）
- 数据导出（Excel 成绩单、学期报告）
