# 班级管理功能设计文档

**创建日期**: 2026-05-30
**状态**: 设计阶段
**优先级**: 高

## 1. 功能概述

为教师提供班级管理功能，通过班级实现学生管理。支持单个新增和批量导入学生。

## 2. 用户角色和权限

| 角色 | 权限 |
|-----|------|
| 教师 | 管理自己任课班级的学生 |
| 学生 | 查看自己所在的班级 |

**权限验证**: 只有班级的任课教师 (`course.teachers`) 可以管理该班级。

## 3. 数据模型

### 3.1 新增 StudentProfile 模型

```python
class StudentProfile(models.Model):
    """学生扩展信息"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    student_id = models.CharField('学号', max_length=50, unique=True)
    admin_class = models.CharField('行政班级', max_length=100, blank=True)
    grade = models.CharField('年级', max_length=20, blank=True)
    phone = models.CharField('手机号', max_length=20, blank=True)
    enrollment_year = models.IntegerField('入学年份', null=True, blank=True)

    class Meta:
        db_table = 'student_profiles'
```

### 3.2 现有模型关系

```
Semester (学期)
  └── Course (课程，teachers=ManyToMany)
      └── TeachingClass (教学班级，capacity=人数上限)
          └── StudentEnrollment (选课记录，status/dropped)
              └── User (学生)
                  └── StudentProfile (学生扩展信息)
```

## 4. 功能设计

### 4.1 学生列表展示

**显示字段**:
- 学号 (student_id)
- 姓名 (username)
- 角色 (role: student/assistant/monitor)
- 状态 (status: enrolled/dropped)
- 选课时间 (enrolled_at)

**筛选功能**:
- 按角色筛选
- 按状态筛选

**排序功能**:
- 按学号升序/降序
- 按选课时间排序

### 4.2 单个新增学生

**组合方式流程**:

1. 教师点击"添加学生"按钮
2. 弹出对话框，显示搜索框
3. 教师输入学号或姓名进行搜索
4. **情况A - 找到现有学生**:
   - 显示学生列表
   - 教师选择学生 → 确认 → 创建选课记录
5. **情况B - 未找到学生**:
   - 显示"创建新学生"表单
   - 填写：学号、姓名、手机号、邮箱、行政班级、年级
   - 确认 → 创建用户和Profile → 创建选课记录

**默认值**:
- 密码: `123456`
- 邮箱: 如无提供，使用 `{学号}@school.edu`
- 角色: `student`

### 4.3 批量导入学生

**导入文件格式** (Excel/CSV):

| 必选字段 | 说明 |
|---------|------|
| 学号 | 唯一标识 |
| 姓名 | 真实姓名 |

| 可选字段 | 说明 |
|---------|------|
| 手机号 | 联系方式 |
| 邮箱 | 初始邮箱 |
| 行政班级 | 如"计算机1班" |
| 年级 | 如"2024级" |
| 初始角色 | student/assistant/monitor |

**导入流程**:

```
1. 教师点击"批量导入"
2. 显示导入弹窗，包含"下载模板"链接
3. 教师上传 Excel/CSV 文件
4. 系统解析文件并验证
5. 显示导入预览：
   - 预览即将导入的学生列表
   - 标记：新增用户 / 现有用户
6. 教师确认后开始导入
7. 逐行处理：
   ├── 学号存在 → 更新Profile → 创建选课记录
   ├── 学号不存在 → 创建用户 + Profile → 创建选课记录
   └── 记录成功/失败
8. 检查容量限制：
   ├── 未超出 → 全部成功
   └── 超出 → 停止导入，提示剩余可添加人数
9. 显示导入结果：
   - 成功数量
   - 失败列表（行号 + 错误原因）
```

**错误处理**:

| 错误类型 | 处理方式 |
|---------|---------|
| 文件格式错误 | 拒绝导入，提示正确格式 |
| 必填字段缺失 | 记录失败，在失败列表中显示 |
| 学号重复 | 记录失败，提示"学号已存在" |
| 超出班级容量 | 停止导入，提示剩余可添加人数 |

**容量检查逻辑**:
```python
current_count = teaching_class.enrollments.filter(status='enrolled').count()
available = teaching_class.capacity - current_count
if len(import_data) > available:
    return error(f"超出容量，仅可再添加 {available} 人")
```

### 4.4 修改学生角色

**单个修改**:
- 表格中直接使用角色下拉框
- 修改后自动保存

**批量修改**:
- 选中多个学生
- 点击"批量修改角色"
- 选择新角色 → 确认 → 批量更新

### 4.5 移除学生

**软删除机制**:
- 不删除 `StudentEnrollment` 记录
- 设置 `status = 'dropped'`
- 记录 `dropped_at = now()`
- 历史数据保留

**操作流程**:
1. 点击"移除"按钮
2. 确认对话框："确定移除学生 {姓名}？"
3. 确认 → 执行软删除
4. 刷新列表（从"已选课"筛选中消失）

### 4.6 导出功能

**导出内容**:
- 班级信息（课程名称、班级名称、选课码）
- 学生列表（学号、姓名、角色、状态、选课时间）

**导出格式**:
- Excel 文件 (.xlsx)
- UTF-8 编码，支持中文

### 4.7 导入模板下载

**模板内容**:
- 包含字段说明表头
- 包含 2 行示例数据
- 放置在 `templates/teaching/import_template.xlsx`

## 5. API 设计

### 5.1 班级管理 API

| 方法 | 路径 | 说明 |
|-----|------|------|
| GET | `/api/v1/teaching/classes/` | 获取教师的班级列表 |
| GET | `/api/v1/teaching/classes/{id}/` | 获取班级详情 |
| GET | `/api/v1/teaching/classes/{id}/students/` | 获取班级学生列表 |
| POST | `/api/v1/teaching/classes/{id}/students/` | 添加单个学生 |
| DELETE | `/api/v1/teaching/classes/{id}/students/{student_id}/` | 移除学生（软删除） |
| PATCH | `/api/v1/teaching/classes/{id}/students/{student_id}/` | 修改学生角色 |
| POST | `/api/v1/teaching/classes/{id}/import/` | 批量导入学生 |
| PATCH | `/api/v1/teaching/classes/{id}/students/batch/` | 批量修改角色 |

### 5.2 用户相关 API

| 方法 | 路径 | 说明 |
|-----|------|------|
| GET | `/api/v1/users/search/?q={query}` | 搜索用户（按学号/姓名） |
| POST | `/api/v1/users/batch-create/` | 批量创建用户 |
| GET | `/api/v1/teaching/import-template/` | 下载导入模板 |

### 5.3 API 响应格式

**学生列表响应**:
```json
{
  "count": 30,
  "results": [
    {
      "id": 1,
      "student_id": "2024001",
      "username": "张三",
      "role": "student",
      "status": "enrolled",
      "enrolled_at": "2026-05-01T10:00:00Z"
    }
  ]
}
```

**批量导入响应**:
```json
{
  "success": true,
  "summary": {
    "total": 25,
    "created": 20,
    "updated": 3,
    "failed": 2
  },
  "errors": [
    {
      "row": 5,
      "error": "学号已存在",
      "student_id": "2024005"
    },
    {
      "row": 12,
      "error": "必填字段缺失：姓名",
      "student_id": "2024012"
    }
  ],
  "warnings": []
}
```

**容量超出响应**:
```json
{
  "success": false,
  "error": "超出班级容量",
  "message": "班级当前已有 38 人，容量 40 人，仅可再添加 2 人。请减少导入数量或联系管理员调整容量。"
}
```

## 6. 前端页面设计

### 6.1 页面结构

**班级列表页** (`/teaching/classes/`):
```
┌─────────────────────────────────────────────────────┐
│  教学管理 > 班级管理                                │
├─────────────────────────────────────────────────────┤
│  [搜索班级]                                          │
│                                                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │
│  │ 2024春-国贸  │  │ 2024春-国贸  │  │ 2024春-物流  │ │
│  │ 1班          │  │ 2班          │  │ 1班          │ │
│  │ 选课码:ABC123 │  │ 选课码:DEF456 │  │ 选课码:GHI789 │ │
│  │ 35/40人      │  │ 28/40人      │  │ 32/40人      │ │
│  └─────────────┘  └─────────────┘  └─────────────┘ │
└─────────────────────────────────────────────────────┘
```

**班级详情页** (`/teaching/classes/{id}/`):
```
┌─────────────────────────────────────────────────────┐
│  教学管理 > 班级管理 > 2024春-国贸1班                │
├─────────────────────────────────────────────────────┤
│  班级信息：选课码: ABC123 | 已选: 35/40人           │
│                                                      │
│  [筛选: 角色▼] [筛选: 状态▼]                         │
│  [添加学生] [批量导入] [导出] [批量修改角色]          │
│                                                      │
│  ┌───┬────────┬──────┬────────┬────────┬────────┐│
│  │选择│ 学号   │ 姓名  │ 角色   │ 状态   │ 操作   ││
│  ├───┼────────┼──────┼────────┼────────┼────────┤│
│  │☐ │2024001 │ 张三  │ 学生   │ 已选课 │ 移除   ││
│  │☐ │2024002 │ 李四  │ 班长   │ 已选课 │ 移除   ││
│  │☐ │2024003 │ 王五  │ 助教   │ 已退课 │ -      ││
│  └───┴────────┴──────┴────────┴────────┴────────┘│
└─────────────────────────────────────────────────────┘
```

### 6.2 批量导入弹窗

```
┌─────────────────────────────────────────────┐
│  批量导入学生                    [×]        │
├─────────────────────────────────────────────┤
│  [下载导入模板]                              │
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │  拖拽文件到此处                      │   │
│  │  或点击选择文件                      │   │
│  └─────────────────────────────────────┘   │
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │  导入预览                            │   │
│  ├─────────────────────────────────────┤   │
│  │  学号    姓名   状态    备注         │   │
│  │  2024001 张三   新增    -           │   │
│  │  2024002 李四   现有    更新信息    │   │
│  └─────────────────────────────────────┘   │
│                                             │
│  [取消]  [确认导入]                         │
└─────────────────────────────────────────────┘
```

### 6.3 导入结果展示

```
┌─────────────────────────────────────────────┐
│  导入完成                        [×]        │
├─────────────────────────────────────────────┤
│  成功: 23 人  |  失败: 2 人                 │
│                                             │
│  失败列表：                                 │
│  • 第5行: 学号 2024005 已存在               │
│  • 第12行: 必填字段缺失：姓名               │
│                                             │
│  [关闭]                                     │
└─────────────────────────────────────────────┘
```

## 7. 实现要点

### 7.1 新增 StudentProfile 模型

**位置**: `apps/teaching/models.py`

需要创建数据库迁移。

### 7.2 批量导入逻辑

**位置**: `apps/teaching/services.py` 或新建 `apps/teaching/services/import_service.py`

**关键函数**:
- `parse_import_file(file)` - 解析 Excel/CSV
- `validate_import_data(data)` - 验证数据
- `process_import_row(row, teaching_class)` - 处理单行数据
- `check_capacity(teaching_class, count)` - 检查容量

### 7.3 权限验证

**位置**: `apps/teaching/permissions.py`

```python
def is_class_teacher(user, teaching_class):
    return teaching_class.course.teachers.filter(id=user.id).exists()
```

### 7.4 导入模板文件

**位置**: `templates/teaching/import_template.xlsx`

包含字段说明和示例数据。

### 7.5 信号处理

当用户被创建时，自动创建 StudentProfile：

```python
@receiver(post_save, sender=User)
def create_student_profile(sender, instance, created, **kwargs):
    if created and instance.user_type == 'student':
        StudentProfile.objects.create(user=instance)
```

## 8. 测试要点

- 单个新增学生（现有用户）
- 单个新增学生（创建新用户）
- 批量导入（全新增）
- 批量导入（混合新增和现有）
- 批量导入（容量超出）
- 批量导入（格式错误）
- 修改角色（单个和批量）
- 移除学生（软删除验证）
- 权限验证（非任课教师访问）
- 导出功能
- 导入预览

## 9. 后续扩展

- 支持学生自助选课（通过选课码）
- 支持班级间学生转移
- 支持批量修改学生其他属性
- 学生考勤记录
- 成绩录入和统计
