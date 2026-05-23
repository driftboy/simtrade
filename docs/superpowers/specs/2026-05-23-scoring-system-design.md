# SimTrade 评分系统设计

## 概述

为 SimTrade 国际贸易模拟系统设计评分模块，采用**混合模式**：系统自动计算客观指标分数，教师在此基础上通过评语 + 加减分进行调整，加权汇总为最终分数。

评分粒度为**角色实例**（一个学生在一个实验中扮演的某个角色），不同角色适用的指标和权重不同。

## 数据模型

### ScoringMetric — 评分指标注册表

| 字段 | 类型 | 说明 |
|------|------|------|
| name | CharField(unique) | 指标标识符（如 `document_accuracy`）|
| display_name | CharField | 显示名称（如 "单证准确率"）|
| dimension | CharField(choices) | 所属维度：FINANCIAL / ACCURACY / EFFICIENCY / NEGOTIATION |
| applicable_roles | M2M → TradeRole | 适用的角色列表 |
| weight | DecimalField | 默认权重（0-100）|
| calculation_method | CharField | 计算方法标识符，用于查找对应的 Calculator |
| config | JSONField | 计算配置（如基准值、阈值），如 `{"benchmark_minutes": 30, "max_minutes": 60}` |
| is_active | BooleanField | 是否启用 |

### ScoreSheet — 评分表

一次实验 + 一个学生 + 一个角色实例 = 一张评分表。

| 字段 | 类型 | 说明 |
|------|------|------|
| experiment | FK → Experiment | 所属实验 |
| user | FK → User | 学生 |
| user_company_role | FK → UserCompanyRole | 角色实例 |
| status | CharField(choices) | DRAFT / AUTO_SCORED / TEACHER_REVIEWED / FINALIZED |
| auto_score | DecimalField | 自动计算总分 |
| teacher_adjustment | DecimalField | 教师加减分（受 max_adjustment 限制）|
| final_score | DecimalField | 最终分数 = auto_score + teacher_adjustment |
| teacher_comment | TextField | 教师评语 |
| reviewed_by | FK → User | 审核教师 |
| reviewed_at | DateTimeField | 审核时间 |

### MetricScore — 指标得分明细

| 字段 | 类型 | 说明 |
|------|------|------|
| score_sheet | FK → ScoreSheet | 所属评分表 |
| metric | FK → ScoringMetric | 评分指标 |
| raw_value | DecimalField | 原始值（如 0.95 表示 95%）|
| score | DecimalField | 标准化得分（0-100）|
| details | JSONField | 计算细节（如哪些单证出错、耗时明细）|

### ExperimentScoringConfig — 实验级权重配置

覆盖默认权重，教师可为不同实验定制评分规则。

| 字段 | 类型 | 说明 |
|------|------|------|
| experiment | FK → Experiment | 所属实验 |
| metric | FK → ScoringMetric | 指标 |
| custom_weight | DecimalField | 自定义权重 |
| max_adjustment | DecimalField | 教师加减分上限（默认 ±20）|

## 自动计算指标

### 指标总表（10 个）

#### 财务表现 (FINANCIAL) — 仅出口商/进口商

| 指标 | calculation_method | 数据来源 | 计算逻辑 |
|------|-------------------|---------|---------|
| profit_margin | 利润率 | Transaction 金额 + 各项费用 | (收入 - 成本) / 收入 × 100 |
| cost_control | 成本控制 | Shipment/Insurance/Customs 费用 | 与行业基准成本对比，偏差 ≤5% = 100，每增加 5% 扣 10 分，≥50% = 0 |

#### 业务准确度 (ACCURACY)

| 指标 | calculation_method | 适用角色 | 计算逻辑 |
|------|-------------------|---------|---------|
| document_accuracy | 单证准确率 | 出口商, 进口商 | 1 - (错误次数 / 提交总数) × 100 |
| first_pass_rate | 首次通过率 | Bank, Customs, Inspection, Forex, Tax | 首次成功数 / 总操作数 × 100 |

#### 操作效率 (EFFICIENCY)

| 指标 | calculation_method | 适用角色 | 计算逻辑 |
|------|-------------------|---------|---------|
| trade_cycle_time | 交易周期 | 出口商, 进口商 | 时间标准化到 0-100（分钟基准）|
| document_turnaround | 单证处理速度 | 出口商, 进口商 | 平均处理时长标准化 |
| response_time | 响应速度 | 出口商, 进口商 | 平均响应时长标准化 |
| processing_speed | 处理速度 | 辅助角色（Factory/Shipping 等）| 接任务到完成的时间标准化 |
| completion_rate | 完成率 | Factory, Shipping 等 | 成功完成数 / 分配总数 × 100 |

#### 谈判能力 (NEGOTIATION) — 仅出口商/进口商

| 指标 | calculation_method | 数据来源 | 计算逻辑 |
|------|-------------------|---------|---------|
| negotiation_efficiency | 谈判效率 | InquiryMessage + Contract | 综合评估轮次和最终成交价偏差 |

### 角色到指标映射

| 角色 | 指标 |
|------|------|
| 出口商 | profit_margin, cost_control, document_accuracy, trade_cycle_time, document_turnaround, response_time, negotiation_efficiency |
| 进口商 | 同出口商 |
| 工厂 | processing_speed（接单→发货）, completion_rate |
| 银行 | processing_speed（开证→付款）, first_pass_rate |
| 海关 | processing_speed（申报→放行）, first_pass_rate |
| 货运 | processing_speed（订舱→到达）, completion_rate |
| 保险 | processing_speed（投保→出单）, first_pass_rate |
| 商检 | processing_speed（申请→出证）, first_pass_rate |
| 外汇 | processing_speed（申请→结汇）, first_pass_rate |
| 税务 | processing_speed（申请→退税）, first_pass_rate |

### 标准化规则

所有 score 统一到 0-100：

- **比率型**（准确率、通过率、完成率）：直接 × 100
- **时间型**（processing_speed, response_time, trade_cycle_time, document_turnaround）：
  - 低于基准 = 100 分
  - 基准到 2 倍基准 = 线性递减到 0
  - 超过 2 倍基准 = 0 分
  - 基准值存储在 ScoringMetric.config 中，单位统一为分钟
- **金额型**（profit_margin）：利润率 ≥ 20% = 100，0% = 0，中间线性；负利润 = 0
- **偏差型**（cost_control）：偏差 ≤ 5% = 100，每增加 5% 扣 10 分，≥ 50% = 0

## 计算服务架构

### ScoringService — 评分总调度

- `calculate_experiment_scores(experiment_id)` — 触发整个实验的自动评分
- `calculate_role_score(user_company_role, experiment)` — 计算单个角色实例的评分
- `recalculate(score_sheet_id)` — 重新计算某张评分表

### MetricCalculator — 指标计算器（策略模式）

基类接口：`calculate(user_company_role, experiment) → (raw_value, score, details)`

每个计算方法一个实现类，通过 `calculation_method` 字符串注册/查找：

- `ProfitMarginCalculator`
- `CostControlCalculator`
- `DocumentAccuracyCalculator`
- `FirstPassRateCalculator`
- `TradeCycleTimeCalculator`
- `DocumentTurnaroundCalculator`
- `ResponseTimeCalculator`
- `ProcessingSpeedCalculator`
- `CompletionRateCalculator`
- `NegotiationEfficiencyCalculator`

### ScoreAggregator — 汇总加权

- 读取实验级（ExperimentScoringConfig）或默认（ScoringMetric.weight）权重
- 无数据的指标权重归零，剩余权重等比重分配
- 各 MetricScore × 权重 → 加权求和 → auto_score

## API 端点

| 端点 | 方法 | 权限 | 说明 |
|------|------|------|------|
| `/api/v1/scoring/metrics/` | GET | 全部 | 列出所有评分指标 |
| `/api/v1/scoring/sheets/` | GET | 学生看自己，教师看全部 | 评分表列表（支持按实验/学生筛选）|
| `/api/v1/scoring/sheets/{id}/` | GET | 学生看自己，教师看全部 | 评分表详情（含指标明细）|
| `/api/v1/scoring/sheets/{id}/review/` | POST | 教师 | 教师审核（加减分 + 评语）|
| `/api/v1/scoring/sheets/{id}/recalculate/` | POST | 教师 | 重新计算自动分 |
| `/api/v1/scoring/experiments/{id}/calculate/` | POST | 教师 | 触发整实验评分 |
| `/api/v1/scoring/configs/` | GET/PUT | 教师 | 实验级权重配置 |

## 边界情况处理

| 场景 | 处理方式 |
|------|---------|
| 学生未参与任何交易 | 自动分 0，教师可手动给分 |
| 对方取消交易 | 已完成环节仍参与评分 |
| 自己取消交易 | completion_rate 受影响，已完成部分仍参与评分 |
| 指标无数据 | 该指标权重归零，剩余权重等比重分配 |
| 重新计算（已有审核） | 保留 teacher_adjustment 和 comment，更新 auto_score 和 final_score |
| 教师加减分超限 | 限制在 ±max_adjustment 范围内，默认 ±20 |
| 同公司多名学生 | 共享指标（profit_margin 等）同分，个人操作指标（response_time 等）按各自数据计算 |
| 信用证不适用（T/T 交易） | 银行角色的 first_pass_rate 跳过，权重重分配 |
| 实验中途退出角色 | 按实际参与的交易数据评分 |
| 仅计算 COMPLETED 状态交易 | CANCELLED 交易按取消责任分类处理 |

## 测试策略

- 每个指标计算器独立单元测试：正常、无数据、极端值
- ScoreAggregator 测试：权重配置、零权重重分配
- ScoringService 集成测试：模拟完整交易流程 → 触发评分 → 验证分数
- API 测试：权限校验、教师审核流程、重新计算
- 边界情况专项测试：取消交易、同公司多人、教师加减分超限
