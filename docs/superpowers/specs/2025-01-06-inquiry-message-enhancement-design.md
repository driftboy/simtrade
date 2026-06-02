# 磋商消息增强设计文档

**日期：** 2026-06-01
**状态：** 待审查

## 概述

扩展 `InquiryMessage` 和 `Transaction` 模型，支持完整的国际贸易磋商流程，新增 7 个核心磋商字段。

## 背景与问题

当前磋商消息只支持数量、单价、贸易术语的报价，缺少国际贸易中必需的关键条款：
- 付款方式
- 装运期/交货期
- 包装要求
- 质量标准
- 保险条款
- 商品名称和编码

## 数据模型变更

### 1. InquiryMessage 模型

新增 7 个字段，存储"报价提议"：

```python
# 报价商品信息
offered_product_name = models.CharField('报价商品名称', max_length=200)
offered_product_code = models.CharField('报价商品编码', max_length=50, blank=True)

# 报价交易条款
offered_payment_term = models.CharField('报价付款方式', max_length=20, blank=True)
offered_delivery_date = models.DateField('报价交货日期', null=True, blank=True)
offered_packing = models.TextField('报价包装要求', blank=True)
offered_quality_standard = models.TextField('报价质量标准', blank=True)
offered_insurance = models.CharField('报价保险条款', max_length=200, blank=True)
```

### 2. Transaction 模型

新增 5 个字段，存储"当前共识"：

```python
# 当前共识商品信息（快照）
product_name = models.CharField('商品名称', max_length=200, blank=True)

# 当前共识交易条款
payment_term = models.CharField('付款方式', max_length=20, blank=True)
delivery_date = models.DateField('交货日期', null=True, blank=True)
packing = models.TextField('包装要求', blank=True)
insurance = models.CharField('保险条款', max_length=200, blank=True)
```

### 3. PaymentTerm 枚举

定义付款方式选项：

```python
class PaymentTerm(models.TextChoices):
    LC = 'lc', '信用证 (L/C)'
    DP = 'dp', '付款交单 (D/P)'
    DA = 'da', '承兑交单 (D/A)'
    TT = 'tt', '电汇 (T/T)'
    TT_IN_ADVANCE = 'tt_advance', '前T/T (预付)'
    TT_AT_SIGHT = 'tt_sight', '后T/T (货到付款)'
    WESTERN_UNION = 'wu', '西联汇款'
    OTHER = 'other', '其他'
```

## 字段约束总结

| 字段 | InquiryMessage | Transaction | 约束 |
|------|----------------|-------------|------|
| product_name | offered_product_name | product_name | IM必填，T可选 |
| product_code | offered_product_code | - | IM可选 |
| payment_term | offered_payment_term | payment_term | 均可选，带枚举 |
| delivery_date | offered_delivery_date | delivery_date | 均可选，日期类型 |
| packing | offered_packing | packing | 均可选 |
| quality_standard | offered_quality_standard | - | IM可选 |
| insurance | offered_insurance | insurance | 均可选 |

## 序列化器变更

### TransactionSerializer

```python
# 新增字段
product_name = serializers.CharField(source='product.name', read_only=True)
payment_term_display = serializers.CharField(source='get_payment_term_display', read_only=True)
delivery_date = serializers.DateField(allow_null=True, required=False)
packing = serializers.CharField(allow_blank=True, required=False)
insurance = serializers.CharField(allow_blank=True, max_length=200, required=False)
```

### InquiryMessageSerializer

```python
# 新增字段
offered_product_name = serializers.CharField(max_length=200)
offered_product_code = serializers.CharField(allow_blank=True, max_length=50, required=False)
offered_payment_term = serializers.CharField(allow_blank=True, max_length=20, required=False)
offered_payment_term_display = serializers.CharField(source='get_offered_payment_term_display', read_only=True)
offered_delivery_date = serializers.DateField(allow_null=True, required=False)
offered_packing = serializers.CharField(allow_blank=True, required=False)
offered_quality_standard = serializers.CharField(allow_blank=True, required=False)
offered_insurance = serializers.CharField(allow_blank=True, max_length=200, required=False)
```

## 业务逻辑：同步机制

**同步时机：** 当用户发送 `message_type = 'accept'` 的消息时

**同步映射：**

| InquiryMessage | Transaction |
|----------------|-------------|
| offered_product_name | → product_name |
| offered_payment_term | → payment_term |
| offered_delivery_date | → delivery_date |
| offered_packing | → packing |
| offered_insurance | → insurance |

**实现位置：** `apps/transactions/services.py` 或 `apps/transactions/views.py`

## 前端界面变更

### 修改文件
- `templates/transactions/detail.html`
- `static/js/transaction-detail.js` (如果独立)

### 1. 磋商表单新增字段

添加付款方式选择、交货日期、包装等输入控件。

### 2. 消息显示增强

在消息气泡中显示新增的报价字段：
- 付款方式
- 交货日期
- 包装要求
- 质量标准
- 保险条款

### 3. 交易详情增强

在交易详情头部显示当前共识条款。

## 数据库迁移

需要创建迁移文件：
- `0014_add_negotiation_fields.py` - 添加 InquiryMessage 新字段
- `0015_add_transaction_consensus_fields.py` - 添加 Transaction 新字段

## 测试要点

1. **字段验证**
   - offered_product_name 必填验证
   - 付款方式枚举验证
   - 日期格式验证

2. **同步逻辑**
   - 接受磋商时字段正确同步到 Transaction
   - 可选字段为空时的处理

3. **前端显示**
   - 新字段正确显示在消息列表
   - 共识条款正确显示在交易详情
   - 表单提交正确携带新字段

## 实现文件清单

| 文件 | 变更类型 |
|------|----------|
| `apps/transactions/models.py` | 新增字段 |
| `apps/transactions/serializers.py` | 新增序列化字段 |
| `apps/transactions/services.py` 或 `views.py` | 新增同步逻辑 |
| `templates/transactions/detail.html` | 新增表单和显示 |
| `migrations/0014_*.py` | 数据库迁移 |
| `migrations/0015_*.py` | 数据库迁移 |

## 实施顺序

1. 创建数据库迁移文件
2. 更新模型定义
3. 更新序列化器
4. 实现同步逻辑
5. 更新前端界面
6. 测试验证
