# SimTrade 外贸模拟实训平台设计文档

**版本**: 1.0
**日期**: 2026-05-20
**作者**: Claude + 用户

---

## 1. 项目概述

### 1.1 项目定位

SimTrade 是一个面向高校国际贸易专业的模拟实训平台，参考世格软件 SIMTRADE 的产品理念，采用全 Web 架构，兼容主流浏览器。

### 1.2 核心目标

- 支持三种教学模式：学生单人学习、教师控制课堂、多角色协同
- 覆盖完整外贸业务流程：从市场调研到核销退税
- 模拟 10 种贸易角色，教师可灵活配置
- 提供 15 种外贸单证制作与审核
- 过程化评分系统，自动评估学生表现

### 1.3 技术栈

| 层级 | 技术选型 | 说明 |
|------|---------|------|
| 后端 | Django + Python | 全功能框架，内置管理后台 |
| 前端 | Bootstrap 3 + jQuery | 兼容 IE8+，支持 Win7 |
| 数据库 | PostgreSQL/MySQL | 关系型数据库 |
| 部署 | 公云服务器 / 学校内网 | 支持 100 人同时在线 |

---

## 2. 角色系统

### 2.1 角色列表 (10 种)

| 角色 | 英文代码 | 说明 | 可配置 |
|------|---------|------|--------|
| 出口商 | EXPORTER | 销售货物到国外 | 始终 |
| 进口商 | IMPORTER | 从国外购买货物 | 始终 |
| 工厂 | FACTORY | 生产/供应商品 | 始终 |
| 银行 | BANK | 信用证、结算业务 | 始终 |
| 海关 | CUSTOMS | 报关、征税、放行 | 可选 |
| 货运公司 | SHIPPING | 订舱、运输、提单 | 可选 |
| 保险公司 | INSURANCE | 承保、签发保单 | 可选 |
| 商检机构 | INSPECTION | 检验、签发证书 | 可选 |
| 外汇局 | FOREX | 核销管理 | 可选 |
| 税务局 | TAX | 退税审核 | 可选 |

### 2.2 角色配置策略

- **核心角色**（出口商/进口商/工厂/银行）：始终可由学生扮演
- **辅助角色**（海关/货运/保险等）：默认系统自动处理，教师可开启为学生角色
- **多角色扮演**：一个学生可分配多个角色

---

## 3. 数据模型

### 3.1 数据表清单 (28 表)

#### 用户与权限 (7 表)
- `User` - 用户基本信息
- `Role` - 角色类型定义
- `UserRole` - 用户角色分配
- `Permission` - 权限定义
- `RolePermission` - 角色权限关联
- `Class` - 班级信息
- `Company` - 公司信息（学生扮演的虚拟公司）

#### 交易与单证 (6 表)
- `Product` - 商品基础信息
- `Catalog` - 商品目录（公司商品）
- `Transaction` - 交易记录
- `Contract` - 外销合同
- `LetterOfCredit` - 信用证
- `Document` - 单证记录
- `DocumentTemplate` - 单证模板
- `DocumentDependency` - 单证依赖关系

#### 财务与生产 (4 表)
- `ProductionOrder` - 工厂生产订单
- `TransactionCost` - 交易费用
- `Payment` - 收付款记录

#### 教学管理 (4 表)
- `Course` - 课程/实习计划
- `ActivityLog` - 操作日志
- `ScoringRule` - 评分规则配置
- `Score` - 成绩记录

#### 系统配置 (5 表)
- `ExchangeRate` - 汇率
- `ShippingRate` - 运费率
- `InsuranceRate` - 保险费率
- `Country` - 国家信息
- `Port` - 港口信息

#### 消息与新闻 (2 表)
- `Message` - 消息通知
- `News` - 新闻公告

### 3.2 核心数据关系

```
# 用户与权限
User → UserRole → Role → Permission → RolePermission
User → Class
User → Company

# 交易流程
Company → Transaction → Contract
Contract → LetterOfCredit
Transaction → Document
Transaction → ProductionOrder
Transaction → TransactionCost → Payment

# 教学管理
Course → User → ActivityLog → Score
Course → ScoringRule
```

---

## 4. 状态机设计 (8 个)

### 4.1 Transaction (交易)

```
草稿 → 询盘中 → 还盘中 → 待签约 → 已签约 → 履约中 → 已完成
  ↓
已取消
```

### 4.2 Contract (合同)

```
草稿 → 待签字 → 双方已签字 → 已生效 → 履行完毕
  ↓
已取消
```

### 4.3 Document (单证)

```
草稿 → 待审核 → 已审核 → 已提交 → 已接收 → 已归档
  ↓
审核不通过 → 草稿(修改)
```

### 4.4 LetterOfCredit (信用证)

```
草稿 → 待开证 → 已开证 → 已通知 → 待议付 → 已议付 → 已付款
```

### 4.5 ProductionOrder (生产订单)

```
待确认 → 已确认 → 生产中 → 已完成 → 已发货
```

### 4.6 Payment (付款)

```
待支付 → 处理中 → 已支付 → 已收款
  ↓
已取消
```

### 4.7 Course (课程)

```
筹备中 → 报名中 → 进行中 → 已结束 → 已归档
```

### 4.8 Score (成绩)

```
计算中 → 待审核 → 已发布 → 已确认
```

### 4.9 状态联动规则

- `Contract.已生效` → 自动创建 `LetterOfCredit.草稿`
- `LetterOfCredit.已通知` → `Transaction.履约中`
- 所有单证归档 → `Transaction.已完成`
- `Course.已结束` → 触发成绩计算

---

## 5. 业务流程

### 5.1 完整出口流程 (11 步)

1. **市场调研** - 浏览商品、发布商品目录
2. **询盘/发盘** - 接收询盘、发送发盘、还盘磋商
3. **签订合同** - 起草合同、双方签字、合同生效
4. **备货** - 向工厂下单、工厂生产、发货
5. **信用证** - 进口商申请开证、出口商审核、修改
6. **租船订舱** - 联系货代、订舱确认、获取配舱回单
7. **报检报关** - 商检报检、海关报关、获取放行单
8. **投保** - 填写投保单、保险公司承保、获取保单
9. **装船出运** - 货物装船、获取提单
10. **制单结汇** - 制作全套单证、银行议付、收汇
11. **核销退税** - 外汇核销、税务退税

### 5.2 单证制作顺序

1. 商业发票（基础单据）
2. 装箱单（与发票同日）
3. 汇票
4. 投保单 → 保险单
5. 报检单 → 检验证书
6. 报关单
7. 提单
8. 受益人证明 / 装船通知

### 5.3 工厂角色流程

```
接收订单 → 确认订单 → 安排生产 → 生产完成 → 发货 → 开具发票
```

---

## 6. 单证系统

### 6.1 单证列表 (15 种)

| 序号 | 单证名称 | 英文 | 说明 |
|------|---------|------|------|
| 1 | 商业发票 | Commercial Invoice | 结算核心单据 |
| 2 | 装箱单 | Packing List | 货物详细描述 |
| 3 | 汇票 | Bill of Exchange | 收款凭证 |
| 4 | 外销合同 | Sales Contract | 交易合同 |
| 5 | 信用证 | Letter of Credit | 支付保障 |
| 6 | 海运提单 | Bill of Lading | 货权凭证 |
| 7 | 保险单 | Insurance Policy | 保险凭证 |
| 8 | 投保单 | Application Form | 投保申请 |
| 9 | 出口报关单 | Export Declaration | 海关申报 |
| 10 | 进口报关单 | Import Declaration | 海关申报 |
| 11 | 报检单 | Inspection Application | 商检申请 |
| 12 | 检验证书 | Inspection Certificate | 商检凭证 |
| 13 | 产地证 | Certificate of Origin | 原产地证明 |
| 14 | 受益人证明 | Beneficiary Certificate | 补充证明 |
| 15 | 装船通知 | Shipping Advice | 装运通知 |

### 6.2 单证模板系统

- 系统提供标准模板
- 教师可自定义模板
- 支持字段配置（必填/可选/校验规则）

### 6.3 单证自动校验

| 校验项 | 规则 | 扣分 |
|--------|------|------|
| 日期逻辑 | 发票日期 ≤ 提单日期 ≤ 保险日期 | 10分 |
| 金额一致 | 发票金额 = 汇票金额 = 保险金额×1.1 | 15分 |
| 数量一致 | 发票数量 = 装箱单数量 = 提单数量 | 10分 |
| 单证齐全 | L/C 要求的单证全部提交 | 每缺一种 20分 |

---

## 7. 评分系统

### 7.1 评分维度 (5 个)

| 维度 | 权重 | 说明 |
|------|------|------|
| 盈利能力 | 30% | 利润率、成本控制 |
| 单证准确 | 25% | 单证正确率 |
| 完成时效 | 20% | 按时完成 |
| 业务量 | 15% | 交易笔数 |
| 综合表现 | 10% | 操作规范 |

### 7.2 评分公式

```
总分 = 盈利能力×30% + 单证准确×25% + 完成时效×20% + 业务量×15% + 综合表现×10%
```

### 7.3 教师可配置参数

- 各维度权重
- 单证错误扣分
- 超时扣分标准
- 目标交易笔数
- 完成时限

### 7.4 排行榜

- 总分榜
- 利润榜
- 效率榜

---

## 8. 系统模块

### 8.1 模块划分 (8 个)

| 模块 | 功能 |
|------|------|
| 用户管理 | 注册/登录、角色分配、班级管理 |
| 角色模拟 | 角色切换、工作台、消息通知 |
| 交易管理 | 市场/商品浏览、询盘/发盘、合同、履约 |
| 单证中心 | 15种单证制作、审核、归档 |
| 财务结算 | 信用证、收付款、费用计算 |
| 评分系统 | 操作记录、自动评分、排行榜 |
| 教学管理 | 课程创建、进度监控、新闻发布、参数调整 |
| 系统配置 | 商品库、汇率/费率、国家/港口、日志 |

### 8.2 用户端界面

- **学生端**：角色工作台、交易管理、单证中心、我的成绩
- **教师端**：课程管理、学生管理、进度监控、成绩管理、新闻发布、参数配置
- **管理端**：系统配置、数据维护

---

## 9. 浏览器兼容性

### 9.1 支持的浏览器

| 浏览器 | 版本 |
|--------|------|
| Internet Explorer | IE8 - IE11 |
| Edge | 全版本 |
| Chrome | 全版本 |
| Firefox | 全版本 |
| 360浏览器 | 全版本 |
| 搜狗浏览器 | 全版本 |

### 9.2 兼容性策略

- Bootstrap 3 支持 IE8+
- jQuery 处理浏览器差异
- 服务端渲染，减少客户端兼容问题

---

## 10. 部署要求

### 10.1 服务器配置

- CPU: 4 核心及以上
- 内存: 8GB 及以上
- 硬盘: 100GB 及以上
- 带宽: 10Mbps 及以上

### 10.2 软件环境

- Python 3.8+
- Django 3.2+
- PostgreSQL 12+ / MySQL 8.0+
- Nginx / Apache

### 10.3 并发支持

- 支持 100 人同时在线
- 每秒请求处理能力: 50+ QPS

---

## 11. 附录

### 11.1 参考资料

- 世格软件 SIMTRADE: https://www.simtrade.net/
- 世格软件官网: https://www.desunsoft.com/

---

## 12. 权限系统设计 (RBAC)

### 12.1 权限模型

```
User → UserRole → Role → Permission
```

### 12.2 权限定义

权限由三部分组成：`资源.操作.作用域`

| 资源 | 操作 | 作用域 | 说明 |
|------|------|--------|------|
| transaction | create/read/update/delete/approve | self/class/all | 交易操作权限 |
| document | create/read/update/delete/approve | self/class/all | 单证操作权限 |
| course | create/read/update/delete | self/all | 课程管理权限 |
| user | create/read/update/delete | class/all | 用户管理权限 |
| score | read/update | class/all | 成绩管理权限 |
| system_config | read/update | all | 系统配置权限 |

### 12.3 预定义角色

| 角色 | 权限范围 | 说明 |
|------|---------|------|
| 学生 | transaction.*, document.* (self) | 只能操作自己的交易和单证 |
| 教师 | course.*, user.*, score.* (class), transaction.* (class) | 管理自己班级的课程、学生、成绩 |
| 管理员 | 所有权限 | 系统管理 |

### 12.4 权限检查

```python
# 权限检查装饰器
@require_permission('transaction.update', scope='self')
def update_transaction(request, transaction_id):
    # 检查用户是否有权限修改此交易
    pass

# 权限检查函数
def has_permission(user, resource, action, scope, obj=None):
    if scope == 'all':
        return user.is_superuser
    elif scope == 'class':
        return obj.course.teacher == user
    elif scope == 'self':
        return obj.owner == user
    return False
```

---

## 13. 单证模板字段配置

### 13.1 字段配置结构

```json
{
  "doc_type": "commercial_invoice",
  "doc_name": "商业发票",
  "version": "1.0",
  "template_content": "<html>...</html>",
  "fields": [
    {
      "name": "invoice_no",
      "label": "发票编号",
      "type": "text",
      "required": true,
      "readonly": false,
      "default_value": "",
      "validation": {
        "pattern": "^[A-Z0-9]{6,20}$",
        "message": "发票编号为6-20位大写字母和数字"
      },
      "help_text": "格式：INV+年份+流水号，如INV2026001"
    },
    {
      "name": "invoice_date",
      "label": "发票日期",
      "type": "date",
      "required": true,
      "readonly": false,
      "default_value": "{{today}}",
      "validation": {
        "min_date": "{{contract_date}}",
        "max_date": "{{shipment_date}}",
        "message": "发票日期应在合同日期之后，提单日期之前"
      }
    },
    {
      "name": "buyer_name",
      "label": "买方名称",
      "type": "text",
      "required": true,
      "readonly": true,
      "default_value": "{{transaction.buyer.name}}",
      "data_source": "transaction.buyer.name"
    },
    {
      "name": "seller_name",
      "label": "卖方名称",
      "type": "text",
      "required": true,
      "readonly": true,
      "default_value": "{{transaction.seller.name}}",
      "data_source": "transaction.seller.name"
    },
    {
      "name": "amount",
      "label": "发票金额",
      "type": "decimal",
      "required": true,
      "readonly": false,
      "default_value": "{{transaction.amount}}",
      "validation": {
        "min_value": 0.01,
        "precision": 2,
        "message": "金额必须大于0，保留两位小数"
      }
    },
    {
      "name": "quantity",
      "label": "数量",
      "type": "integer",
      "required": true,
      "readonly": false,
      "default_value": "{{transaction.quantity}}",
      "validation": {
        "min_value": 1,
        "message": "数量必须大于0"
      }
    },
    {
      "name": "remarks",
      "label": "备注",
      "type": "textarea",
      "required": false,
      "readonly": false,
      "default_value": "",
      "max_length": 500
    }
  ],
  "validation_rules": [
    {
      "rule": "invoice_date <= bl_date",
      "message": "发票日期不能晚于提单日期",
      "severity": "error"
    },
    {
      "rule": "amount == transaction.amount",
      "message": "发票金额必须与交易金额一致",
      "severity": "error"
    }
  ]
}
```

### 13.2 字段类型

| 类型 | 说明 | 示例 |
|------|------|------|
| text | 单行文本 | 发票编号 |
| textarea | 多行文本 | 备注 |
| number | 数字 | 数量 |
| decimal | 小数 | 金额 |
| date | 日期 | 发票日期 |
| select | 下拉选择 | 贸易术语 |
| radio | 单选 | 是否投保 |
| checkbox | 多选 | 港口列表 |

### 13.3 数据源变量

| 变量 | 说明 | 示例值 |
|------|------|--------|
| {{today}} | 当前日期 | 2026-05-20 |
| {{contract_date}} | 合同日期 | 2026-05-15 |
| {{shipment_date}} | 装运日期 | 2026-06-01 |
| {{transaction.buyer.name}} | 买方名称 | ABC Trading Co. |
| {{transaction.seller.name}} | 卖方名称 | XYZ Export Corp. |
| {{transaction.amount}} | 交易金额 | 10000.00 |
| {{transaction.quantity}} | 交易数量 | 1000 |
| {{user.company.name}} | 用户公司名称 | 学生A的公司 |
| {{course.name}} | 课程名称 | 2026春外贸实训 |

---

## 14. REST API 设计

### 14.1 API 规范

- 基础路径：`/api/v1/`
- 认证方式：Token (Bearer Token)
- 响应格式：JSON
- 错误码：统一格式

### 14.2 通用响应格式

**成功响应**
```json
{
  "code": 0,
  "message": "success",
  "data": {...}
}
```

**错误响应**
```json
{
  "code": 1001,
  "message": "用户不存在",
  "errors": [...]
}
```

### 14.3 API 列表

#### 用户认证

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/v1/auth/login | 用户登录 |
| POST | /api/v1/auth/logout | 用户登出 |
| GET | /api/v1/auth/me | 获取当前用户信息 |

#### 交易管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/v1/transactions | 获取交易列表 |
| POST | /api/v1/transactions | 创建交易 |
| GET | /api/v1/transactions/{id} | 获取交易详情 |
| PUT | /api/v1/transactions/{id} | 更新交易 |
| DELETE | /api/v1/transactions/{id} | 删除交易 |
| POST | /api/v1/transactions/{id}/cancel | 取消交易 |

#### 单证管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/v1/documents | 获取单证列表 |
| POST | /api/v1/documents | 创建单证 |
| GET | /api/v1/documents/{id} | 获取单证详情 |
| PUT | /api/v1/documents/{id} | 更新单证 |
| DELETE | /api/v1/documents/{id} | 删除单证 |
| POST | /api/v1/documents/{id}/submit | 提交单证 |
| POST | /api/v1/documents/{id}/approve | 审核单证 |

#### 课程管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/v1/courses | 获取课程列表 |
| POST | /api/v1/courses | 创建课程 |
| GET | /api/v1/courses/{id} | 获取课程详情 |
| PUT | /api/v1/courses/{id} | 更新课程 |
| DELETE | /api/v1/courses/{id} | 删除课程 |
| GET | /api/v1/courses/{id}/students | 获取课程学生 |
| GET | /api/v1/courses/{id}/scores | 获取课程成绩 |

#### 成绩管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/v1/scores/{id} | 获取成绩详情 |
| PUT | /api/v1/scores/{id} | 更新成绩 |
| POST | /api/v1/scores/calculate | 计算成绩 |
| POST | /api/v1/scores/publish | 发布成绩 |

### 14.4 分页规范

```
GET /api/v1/transactions?page=1&page_size=20

响应:
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [...],
    "total": 100,
    "page": 1,
    "page_size": 20,
    "pages": 5
  }
}
```

---

## 15. 数据字典

### 15.1 交易状态

```python
TRANSACTION_STATUS_CHOICES = [
    ('draft', '草稿'),
    ('inquiring', '询盘中'),
    ('negotiating', '还盘中'),
    ('pending_contract', '待签约'),
    ('contracted', '已签约'),
    ('in_progress', '履约中'),
    ('completed', '已完成'),
    ('cancelled', '已取消'),
]
```

### 15.2 合同状态

```python
CONTRACT_STATUS_CHOICES = [
    ('draft', '草稿'),
    ('pending_sign', '待签字'),
    ('signed', '双方已签字'),
    ('effective', '已生效'),
    ('fulfilled', '履行完毕'),
    ('cancelled', '已取消'),
]
```

### 15.3 单证状态

```python
DOCUMENT_STATUS_CHOICES = [
    ('draft', '草稿'),
    ('pending_review', '待审核'),
    ('approved', '已审核'),
    ('submitted', '已提交'),
    ('received', '已接收'),
    ('archived', '已归档'),
    ('rejected', '审核不通过'),
]
```

### 15.4 信用证状态

```python
LETTER_OF_CREDIT_STATUS_CHOICES = [
    ('draft', '草稿'),
    ('pending_issue', '待开证'),
    ('issued', '已开证'),
    ('advised', '已通知'),
    ('pending_negotiation', '待议付'),
    ('negotiated', '已议付'),
    ('paid', '已付款'),
]
```

### 15.5 生产订单状态

```python
PRODUCTION_ORDER_STATUS_CHOICES = [
    ('pending_confirm', '待确认'),
    ('confirmed', '已确认'),
    ('in_production', '生产中'),
    ('completed', '已完成'),
    ('shipped', '已发货'),
]
```

### 15.6 付款状态

```python
PAYMENT_STATUS_CHOICES = [
    ('pending', '待支付'),
    ('processing', '处理中'),
    ('paid', '已支付'),
    ('received', '已收款'),
    ('cancelled', '已取消'),
]
```

### 15.7 课程状态

```python
COURSE_STATUS_CHOICES = [
    ('preparing', '筹备中'),
    ('enrolling', '报名中'),
    ('active', '进行中'),
    ('ended', '已结束'),
    ('archived', '已归档'),
]
```

### 15.8 成绩状态

```python
SCORE_STATUS_CHOICES = [
    ('calculating', '计算中'),
    ('pending_review', '待审核'),
    ('published', '已发布'),
    ('confirmed', '已确认'),
]
```

### 15.9 角色类型

```python
ROLE_TYPE_CHOICES = [
    ('STUDENT', '学生'),
    ('TEACHER', '教师'),
    ('ADMIN', '管理员'),
]

TRADE_ROLE_CHOICES = [
    ('EXPORTER', '出口商'),
    ('IMPORTER', '进口商'),
    ('FACTORY', '工厂'),
    ('BANK', '银行'),
    ('CUSTOMS', '海关'),
    ('SHIPPING', '货运公司'),
    ('INSURANCE', '保险公司'),
    ('INSPECTION', '商检机构'),
    ('FOREX', '外汇局'),
    ('TAX', '税务局'),
]
```

### 15.10 单证类型

```python
DOCUMENT_TYPE_CHOICES = [
    ('commercial_invoice', '商业发票'),
    ('packing_list', '装箱单'),
    ('bill_of_exchange', '汇票'),
    ('sales_contract', '外销合同'),
    ('letter_of_credit', '信用证'),
    ('bill_of_lading', '海运提单'),
    ('insurance_policy', '保险单'),
    ('insurance_application', '投保单'),
    ('export_declaration', '出口报关单'),
    ('import_declaration', '进口报关单'),
    ('inspection_application', '报检单'),
    ('inspection_certificate', '检验证书'),
    ('certificate_of_origin', '产地证'),
    ('beneficiary_certificate', '受益人证明'),
    ('shipping_advice', '装船通知'),
]
```

### 15.11 贸易术语

```python
TRADE_TERM_CHOICES = [
    ('EXW', '工厂交货'),
    ('FOB', '装运港船上交货'),
    ('CFR', '成本加运费'),
    ('CIF', '成本加保险费加运费'),
    ('FCA', '货交承运人'),
    ('CPT', '运费付至'),
    ('CIP', '运费保险费付至'),
    ('DAF', '边境交货'),
    ('DES', '目的港船上交货'),
    ('DEQ', '目的港码头交货'),
    ('DDU', '未完税交货'),
    ('DDP', '完税后交货'),
]
```

### 15.12 付款方式

```python
PAYMENT_TERM_CHOICES = [
    ('L/C', '信用证'),
    ('D/P', '付款交单'),
    ('D/A', '承兑交单'),
    ('T/T', '电汇'),
    ('M/T', '信汇'),
    ('Western Union', '西联汇款'),
    ('Money Gram', '速汇金'),
]
```

### 15.13 运输方式

```python
SHIPPING_METHOD_CHOICES = [
    ('sea', '海运'),
    ('air', '空运'),
    ('land', '陆运'),
    ('rail', '铁路'),
    ('multimodal', '多式联运'),
]
```

### 15.14 用户类型

```python
USER_TYPE_CHOICES = [
    ('student', '学生'),
    ('teacher', '教师'),
    ('admin', '管理员'),
]
```

### 15.15 消息类型

```python
MESSAGE_TYPE_CHOICES = [
    ('system', '系统通知'),
    ('transaction', '交易消息'),
    ('document', '单证消息'),
    ('inquiry', '询盘'),
    ('news', '新闻'),
]
```

---

### 11.2 设计变更记录

| 版本 | 日期 | 变更内容 |
|------|------|---------|
| 1.0 | 2026-05-20 | 初始设计 |
| 1.1 | 2026-05-20 | 补充权限系统、单证字段配置、API设计、数据字典 |
