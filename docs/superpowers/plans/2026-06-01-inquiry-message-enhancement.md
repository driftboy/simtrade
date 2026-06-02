# 磋商消息增强实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 扩展 InquiryMessage 和 Transaction 模型，支持完整的国际贸易磋商流程（付款方式、交货日期、包装、质量标准、保险条款、商品名称和编码）

**架构：** 在现有 Transaction/InquiryMessage 模型基础上添加新字段；InquiryMessage 存储"报价提议"，Transaction 存储"当前共识"；接受磋商时同步字段；通过序列化器暴露给 API，前端表单和显示增强。

**技术栈：** Django, Django REST Framework, PostgreSQL, jQuery

---

### 任务 1：添加 PaymentTerm 枚举

**文件：**
- 修改：`apps/transactions/models.py:67-76`

- [ ] **步骤 1：添加 PaymentTerm 枚举类**

在 `InquiryMessage` 类之前添加：

```python
class PaymentTerm(models.TextChoices):
    """付款方式枚举"""
    LC = 'lc', '信用证 (L/C)'
    DP = 'dp', '付款交单 (D/P)'
    DA = 'da', '承兑交单 (D/A)'
    TT = 'tt', '电汇 (T/T)'
    TT_IN_ADVANCE = 'tt_advance', '前T/T (预付)'
    TT_AT_SIGHT = 'tt_sight', '后T/T (货到付款)'
    WESTERN_UNION = 'wu', '西联汇款'
    OTHER = 'other', '其他'
```

- [ ] **步骤 2：验证语法正确**

运行：`python manage.py check`
预期：无错误

- [ ] **步骤 3：Commit**

```bash
git add apps/transactions/models.py
git commit -m "feat: add PaymentTerm enum for negotiation"
```

---

### 任务 2：添加 InquiryMessage 新字段到模型

**文件：**
- 修改：`apps/transactions/models.py:95-100`

**注意：** 由于数据库中存在2条现有的 InquiryMessage 记录，无法在不提供默认值的情况下添加非空字段。采用**务实方案**：保持数据库字段可选（`blank=True, default=''`），但在序列化器层面通过验证器强制要求新消息必须提供 `offered_product_name`。这是生产环境中处理遗留数据的常见做法。

- [ ] **步骤 1：在 InquiryMessage 类中添加新字段**

在 `attachment = models.FileField(...)` 之后，`is_read` 之前添加：

```python
# 报价商品信息
offered_product_name = models.CharField('报价商品名称', max_length=200, blank=True, default='')
offered_product_code = models.CharField('报价商品编码', max_length=50, blank=True)

# 报价交易条款
offered_payment_term = models.CharField(
    '报价付款方式',
    max_length=20,
    choices=PaymentTerm.choices,
    blank=True
)
offered_delivery_date = models.DateField('报价交货日期', null=True, blank=True)
offered_packing = models.TextField('报价包装要求', blank=True)
offered_quality_standard = models.TextField('报价质量标准', blank=True)
offered_insurance = models.CharField('报价保险条款', max_length=200, blank=True)
```

- [ ] **步骤 2：验证语法正确**

运行：`python manage.py check`
预期：无错误

- [ ] **步骤 3：Commit**

```bash
git add apps/transactions/models.py
git commit -m "feat: add negotiation fields to InquiryMessage model"
```

---

### 任务 3：创建 InquiryMessage 迁移文件

**文件：**
- 创建：`apps/transactions/migrations/0014_add_inquiry_message_fields.py`

- [ ] **步骤 1：生成迁移文件**

运行：`python manage.py makemigrations transactions`
预期：生成 `0014_*.py` 迁移文件，包含新字段

- [ ] **步骤 2：检查迁移文件内容**

确认迁移文件包含：
- `offered_product_name` (CharField, max_length=200, not blank)
- `offered_product_code` (CharField, max_length=50, blank=True)
- `offered_payment_term` (CharField, max_length=20, choices=PaymentTerm.choices, blank=True)
- `offered_delivery_date` (DateField, null=True, blank=True)
- `offered_packing` (TextField, blank=True)
- `offered_quality_standard` (TextField, blank=True)
- `offered_insurance` (CharField, max_length=200, blank=True)

- [ ] **步骤 3：应用迁移**

运行：`python manage.py migrate transactions`
预期：显示 "Applying transactions.0014..."

- [ ] **步骤 4：Commit**

```bash
git add apps/transactions/migrations/0014_*.py
git add apps/transactions/migrations/
git commit -m "feat: create migration for InquiryMessage negotiation fields"
```

---

### 任务 4：添加 Transaction 新字段到模型

**文件：**
- 修改：`apps/transactions/models.py:44-47`

- [ ] **步骤 1：在 Transaction 类中添加新字段**

在 `notes = models.TextField(...)` 之后，`created_by` 之前添加：

```python
# 当前共识商品信息（快照）
product_name = models.CharField('商品名称', max_length=200, blank=True)

# 当前共识交易条款
payment_term = models.CharField(
    '付款方式',
    max_length=20,
    choices=PaymentTerm.choices,
    blank=True
)
delivery_date = models.DateField('交货日期', null=True, blank=True)
packing = models.TextField('包装要求', blank=True)
insurance = models.CharField('保险条款', max_length=200, blank=True)
```

- [ ] **步骤 2：验证语法正确**

运行：`python manage.py check`
预期：无错误

- [ ] **步骤 3：Commit**

```bash
git add apps/transactions/models.py
git commit -m "feat: add consensus fields to Transaction model"
```

---

### 任务 5：创建 Transaction 迁移文件

**文件：**
- 创建：`apps/transactions/migrations/0015_add_transaction_fields.py`

- [ ] **步骤 1：生成迁移文件**

运行：`python manage.py makemigrations transactions`
预期：生成 `0015_*.py` 迁移文件

- [ ] **步骤 2：检查迁移文件内容**

确认迁移文件包含：
- `product_name` (CharField, max_length=200, blank=True)
- `payment_term` (CharField, max_length=20, choices=PaymentTerm.choices, blank=True)
- `delivery_date` (DateField, null=True, blank=True)
- `packing` (TextField, blank=True)
- `insurance` (CharField, max_length=200, blank=True)

- [ ] **步骤 3：应用迁移**

运行：`python manage.py migrate transactions`
预期：显示 "Applying transactions.0015..."

- [ ] **步骤 4：Commit**

```bash
git add apps/transactions/migrations/0015_*.py
git add apps/transactions/migrations/
git commit -m "feat: create migration for Transaction consensus fields"
```

---

### 任务 6：更新 TransactionSerializer

**文件：**
- 修改：`apps/transactions/serializers.py:13-46`

- [ ] **步骤 1：添加新字段到 TransactionSerializer**

在 `seller_company_code` 行之后，`product` 行之前添加：

```python
product_name = serializers.CharField(source='product.name', read_only=True)
```

在 `currency` 行之后，`port_of_loading` 之前添加：

```python
payment_term = serializers.CharField(allow_blank=True, required=False)
payment_term_display = serializers.CharField(source='get_payment_term_display', read_only=True)
delivery_date = serializers.DateField(allow_null=True, required=False)
packing = serializers.CharField(allow_blank=True, required=False)
insurance = serializers.CharField(allow_blank=True, max_length=200, required=False)
```

- [ ] **步骤 2：更新 Meta.fields**

在 `fields` 列表中添加新字段：

```python
fields = ['id', 'buyer', 'buyer_name', 'buyer_company_name', 'buyer_company_code',
          'seller', 'seller_name', 'seller_company_name', 'seller_company_code',
          'product', 'product_name', 'product_code',
          'status', 'status_display', 'quantity',
          'unit_price', 'currency', 'trade_term', 'port_of_loading',
          'port_of_discharge',
          'payment_term', 'payment_term_display', 'delivery_date', 'packing', 'insurance',
          'notes', 'created_at', 'updated_at']
```

- [ ] **步骤 3：验证 API 返回新字段**

运行：`python manage.py runserver`，访问 `/api/v1/transactions/`，确认返回包含新字段
预期：返回的 JSON 包含 `product_name`, `payment_term`, `payment_term_display`, `delivery_date`, `packing`, `insurance`

- [ ] **步骤 4：Commit**

```bash
git add apps/transactions/serializers.py
git commit -m "feat: add negotiation fields to TransactionSerializer"
```

---

### 任务 7：更新 InquiryMessageSerializer

**文件：**
- 修改：`apps/transactions/serializers.py:49-62`

- [ ] **步骤 1：添加新字段到 InquiryMessageSerializer**

在 `sender_role` 行之后，`message_type` 之前添加：

```python
# 报价商品信息 - offered_product_name 对新消息必填，但数据库允许空白以兼容现有记录
offered_product_name = serializers.CharField(max_length=200, required=False, allow_blank=True)
offered_product_code = serializers.CharField(max_length=50, required=False, allow_blank=True)
# 报价交易条款 - 均为可选
offered_payment_term = serializers.CharField(max_length=20, required=False, allow_blank=True)
offered_payment_term_display = serializers.CharField(source='get_offered_payment_term_display', read_only=True)
offered_delivery_date = serializers.DateField(required=False, allow_null=True)
offered_packing = serializers.CharField(required=False, allow_blank=True)
offered_quality_standard = serializers.CharField(required=False, allow_blank=True)
offered_insurance = serializers.CharField(max_length=200, required=False, allow_blank=True)
```

**注意：** `offered_product_name` 设置为 `required=False` 是为了兼容现有数据库记录（该字段在数据库中为可选）。实际必填验证在 `validate()` 方法中实现，仅对新创建的消息强制要求。

- [ ] **步骤 1.5：添加验证方法**

添加 `validate` 方法以确保新消息必须包含 `offered_product_name`：

```python
def validate(self, attrs):
    """验证：新消息必须包含 offered_product_name（排除历史遗留记录）"""
    # 对于新创建的消息（没有pk），要求 offered_product_name
    if not self.instance and not attrs.get('offered_product_name'):
        raise serializers.ValidationError({
            'offered_product_name': '此字段为新消息必填项。'
        })
    return attrs
```

- [ ] **步骤 2：更新 Meta.fields**

在 `fields` 列表中添加新字段：

```python
fields = ['id', 'transaction', 'sender', 'sender_username', 'sender_role',
          'offered_product_name', 'offered_product_code',
          'offered_payment_term', 'offered_payment_term_display',
          'offered_delivery_date', 'offered_packing', 'offered_quality_standard', 'offered_insurance',
          'message_type', 'message_type_display', 'content',
          'offered_quantity', 'offered_price', 'offered_trade_term',
          'attachment', 'is_read', 'created_at']
```

- [ ] **步骤 3：验证 API 返回新字段**

访问 `/api/v1/transactions/<id>/messages/`，确认返回包含新字段
预期：返回的 JSON 包含 `offered_product_name`, `offered_payment_term_display` 等

- [ ] **步骤 4：Commit**

```bash
git add apps/transactions/serializers.py
git commit -m "feat: add negotiation fields to InquiryMessageSerializer"
```

---

### 任务 8：添加同步逻辑到 views.py

**文件：**
- 修改：`apps/transactions/views.py`
- 测试：`apps/transactions/tests/test_api.py`

- [ ] **步骤 1：编写失败的测试**

在 `test_api.py` 中添加：

```python
def test_accept_negotiation_syncs_to_transaction(self):
    """测试接受磋商时同步条款到 Transaction"""
    transaction = Transaction.objects.create(
        buyer=self.buyer_company,
        product=self.product
    )
    message_data = {
        'transaction': transaction.id,
        'message_type': 'accept',
        'content': '接受报价',
        'offered_product_name': '测试产品',
        'offered_payment_term': 'lc',
        'offered_delivery_date': '2024-12-31',
        'offered_packing': '纸箱包装',
        'offered_insurance': 'CIF条款加成110%'
    }
    response = self.client.post(
        f'/api/v1/transactions/{transaction.id}/send_message/',
        data=json.dumps(message_data),
        content_type='application/json'
    )
    self.assertEqual(response.status_code, 201)

    # 验证 Transaction 已更新
    transaction.refresh_from_db()
    self.assertEqual(transaction.product_name, '测试产品')
    self.assertEqual(transaction.payment_term, 'lc')
    self.assertEqual(str(transaction.delivery_date), '2024-12-31')
    self.assertEqual(transaction.packing, '纸箱包装')
    self.assertEqual(transaction.insurance, 'CIF条款加成110%')
```

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest apps/transactions/tests/test_api.py::TestTransactionAPI::test_accept_negotiation_syncs_to_transaction -v`
预期：FAIL - 字段未同步

- [ ] **步骤 3：实现同步逻辑**

在 `apps/transactions/views.py` 中找到 `send_message` 视图函数，在保存消息为 `accept` 类型后添加同步逻辑：

```python
# 如果是接受消息，同步共识条款到 Transaction
if message_data.get('message_type') == 'accept':
    transaction = get_object_or_404(Transaction, pk=transaction_id)
    if serializer.validated_data.get('offered_product_name'):
        transaction.product_name = serializer.validated_data['offered_product_name']
    if serializer.validated_data.get('offered_payment_term'):
        transaction.payment_term = serializer.validated_data['offered_payment_term']
    if serializer.validated_data.get('offered_delivery_date'):
        transaction.delivery_date = serializer.validated_data['offered_delivery_date']
    if serializer.validated_data.get('offered_packing'):
        transaction.packing = serializer.validated_data['offered_packing']
    if serializer.validated_data.get('offered_insurance'):
        transaction.insurance = serializer.validated_data['offered_insurance']
    transaction.save()
```

- [ ] **步骤 4：运行测试验证通过**

运行：`pytest apps/transactions/tests/test_api.py::TestTransactionAPI::test_accept_negotiation_syncs_to_transaction -v`
预期：PASS

- [ ] **步骤 5：Commit**

```bash
git add apps/transactions/views.py apps/transactions/tests/test_api.py
git commit -m "feat: add sync logic for accepted negotiation terms"
```

---

### 任务 9：更新前端表单

**文件：**
- 修改：`templates/transactions/detail.html:26-34`

- [ ] **步骤 1：在消息表单中添加新字段输入**

在现有的 textarea 和按钮之间添加：

```html
<div class="form-group" style="margin-top: 10px;">
    <label>商品名称</label>
    <input type="text" id="offerProductName" class="form-control" placeholder="商品名称" required>
</div>
<div class="row" style="margin-top: 10px;">
    <div class="col-md-6">
        <label>付款方式</label>
        <select id="offerPaymentTerm" class="form-control">
            <option value="">请选择</option>
            <option value="lc">信用证 (L/C)</option>
            <option value="dp">付款交单 (D/P)</option>
            <option value="da">承兑交单 (D/A)</option>
            <option value="tt">电汇 (T/T)</option>
            <option value="tt_advance">前T/T (预付)</option>
            <option value="tt_sight">后T/T (货到付款)</option>
            <option value="wu">西联汇款</option>
            <option value="other">其他</option>
        </select>
    </div>
    <div class="col-md-6">
        <label>交货日期</label>
        <input type="date" id="offerDeliveryDate" class="form-control">
    </div>
</div>
<div class="row" style="margin-top: 10px;">
    <div class="col-md-6">
        <label>包装要求</label>
        <input type="text" id="offerPacking" class="form-control" placeholder="如：纸箱包装">
    </div>
    <div class="col-md-6">
        <label>保险条款</label>
        <input type="text" id="offerInsurance" class="form-control" placeholder="如：由买方办理">
    </div>
</div>
```

- [ ] **步骤 2：验证表单显示正确**

刷新交易详情页面，确认新字段正确显示

- [ ] **步骤 3：Commit**

```bash
git add templates/transactions/detail.html
git commit -m "feat: add negotiation input fields to message form"
```

---

### 任务 10：更新 sendMessage 函数携带新字段

**文件：**
- 修改：`templates/transactions/detail.html:114-143`

- [ ] **步骤 1：更新 sendMessage 函数收集新字段**

修改 `sendMessage` 函数的 data 对象：

```javascript
var data = {
    message_type: messageType,
    content: content || '接受报价',
    offered_product_name: $('#offerProductName').val() || window.currentProductName || '未指定',
    offered_product_code: window.currentProductCode || '',
    offered_payment_term: $('#offerPaymentTerm').val() || null,
    offered_delivery_date: $('#offerDeliveryDate').val() || null,
    offered_packing: $('#offerPacking').val() || null,
    offered_insurance: $('#offerInsurance').val() || null
};
```

- [ ] **步骤 2：验证数据正确发送**

打开浏览器开发者工具 Network 标签，发送消息，确认请求包含新字段

- [ ] **步骤 3：Commit**

```bash
git add templates/transactions/detail.html
git commit -m "feat: include negotiation fields in sendMessage"
```

---

### 任务 11：更新消息显示展示新字段

**文件：**
- 修改：`templates/transactions/detail.html:89-104`

- [ ] **步骤 1：在消息渲染中添加新字段显示**

在消息气泡的 HTML 中添加：

```javascript
response.data.forEach(function(msg) {
    var bubbleClass = msg.sender_role === 'buyer' ? 'bubble-right' : 'bubble-left';
    var typeLabel = msg.message_type_display;
    html += `
        <div class="message-bubble ${bubbleClass}">
            <strong>${msg.sender_username}</strong> <span class="label label-default">${typeLabel}</span>
            <p>${msg.content}</p>
            ${msg.offered_product_name ? '<p><strong>商品:</strong> ' + msg.offered_product_name + '</p>' : ''}
            ${msg.offered_payment_term_display ? '<p><strong>付款方式:</strong> ' + msg.offered_payment_term_display + '</p>' : ''}
            ${msg.offered_delivery_date ? '<p><strong>交货日期:</strong> ' + msg.offered_delivery_date + '</p>' : ''}
            ${msg.offered_packing ? '<p><strong>包装要求:</strong> ' + msg.offered_packing + '</p>' : ''}
            ${msg.offered_quality_standard ? '<p><strong>质量标准:</strong> ' + msg.offered_quality_standard + '</p>' : ''}
            ${msg.offered_insurance ? '<p><strong>保险条款:</strong> ' + msg.offered_insurance + '</p>' : ''}
            ${msg.offered_price ? '<p><strong>报价: $' + msg.offered_price + '</strong></p>' : ''}
            ${msg.offered_quantity ? '<p><strong>数量: ' + msg.offered_quantity + '</strong></p>' : ''}
            <div class="message-time">${msg.created_at}</div>
        </div>
    `;
});
```

- [ ] **步骤 2：验证消息正确显示**

发送包含新字段的消息，确认消息气泡正确显示

- [ ] **步骤 3：Commit**

```bash
git add templates/transactions/detail.html
git commit -m "feat: display negotiation fields in message bubbles"
```

---

### 任务 12：更新交易详情显示共识条款

**文件：**
- 修改：`templates/transactions/detail.html:60-70`

- [ ] **步骤 1：在交易详情面板中添加共识条款显示**

在现有的买方/卖方信息之后添加：

```javascript
<div class="col-md-6">
    <p><strong>付款方式:</strong> ${tx.payment_term_display || '未协商'}</p>
    <p><strong>交货日期:</strong> ${tx.delivery_date || '未协商'}</p>
    <p><strong>包装要求:</strong> ${tx.packing || '未协商'}</p>
    <p><strong>保险条款:</strong> ${tx.insurance || '未协商'}</p>
</div>
```

- [ ] **步骤 2：验证交易详情正确显示**

刷新交易详情页面，确认共识条款正确显示

- [ ] **步骤 3：Commit**

```bash
git add templates/transactions/detail.html
git commit -m "feat: display consensus terms in transaction detail"
```

---

### 任务 13：添加模型测试

**文件：**
- 修改：`apps/transactions/tests/test_models.py`

- [ ] **步骤 1：添加新字段测试**

在 `test_models.py` 中添加：

```python
def test_inquiry_message_negotiation_fields(self):
    """测试 InquiryMessage 新字段"""
    message = InquiryMessage.objects.create(
        transaction=self.transaction,
        sender=self.user,
        sender_role='buyer',
        message_type='offer',
        offered_product_name='测试产品',
        offered_product_code='TEST001',
        offered_payment_term='lc',
        offered_delivery_date='2024-12-31',
        offered_packing='纸箱包装',
        offered_quality_standard='ISO9001',
        offered_insurance='CIF条款'
    )
    self.assertEqual(message.offered_product_name, '测试产品')
    self.assertEqual(message.offered_product_code, 'TEST001')
    self.assertEqual(message.offered_payment_term, 'lc')
    self.assertEqual(str(message.offered_delivery_date), '2024-12-31')
    self.assertEqual(message.offered_packing, '纸箱包装')

def test_transaction_consensus_fields(self):
    """测试 Transaction 新字段"""
    transaction = Transaction.objects.create(
        buyer=self.buyer_company,
        product=self.product,
        product_name='快照产品',
        payment_term='tt',
        delivery_date='2024-12-31',
        packing='木箱包装',
        insurance='由买方办理'
    )
    self.assertEqual(transaction.product_name, '快照产品')
    self.assertEqual(transaction.payment_term, 'tt')

def test_payment_term_choices(self):
    """测试付款方式枚举"""
    self.assertEqual(Transaction.PaymentTerm.LC, 'lc')
    self.assertEqual(Transaction.PaymentTerm.TT, 'tt')
```

- [ ] **步骤 2：运行测试**

运行：`pytest apps/transactions/tests/test_models.py -v -k negotiation`
预期：全部 PASS

- [ ] **步骤 3：Commit**

```bash
git add apps/transactions/tests/test_models.py
git commit -m "test: add tests for negotiation fields"
```

---

### 任务 14：添加序列化器测试

**文件：**
- 修改：`apps/transactions/tests/test_serializers.py`

- [ ] **步骤 1：添加序列化器测试**

```python
def test_transaction_serializer_includes_negotiation_fields(self):
    """测试 TransactionSerializer 包含新字段"""
    transaction = Transaction.objects.create(
        buyer=self.buyer_company,
        product=self.product,
        product_name='测试产品',
        payment_term='lc'
    )
    serializer = TransactionSerializer(transaction)
    data = serializer.data
    self.assertIn('product_name', data)
    self.assertIn('payment_term', data)
    self.assertIn('payment_term_display', data)
    self.assertEqual(data['payment_term_display'], '信用证 (L/C)')

def test_inquiry_message_serializer_includes_negotiation_fields(self):
    """测试 InquiryMessageSerializer 包含新字段"""
    message = InquiryMessage.objects.create(
        transaction=self.transaction,
        sender=self.user,
        sender_role='buyer',
        message_type='offer',
        offered_product_name='测试产品',
        offered_payment_term='tt'
    )
    serializer = InquiryMessageSerializer(message)
    data = serializer.data
    self.assertIn('offered_product_name', data)
    self.assertIn('offered_payment_term_display', data)
    self.assertEqual(data['offered_payment_term_display'], '电汇 (T/T)')
```

- [ ] **步骤 2：运行测试**

运行：`pytest apps/transactions/tests/test_serializers.py -v -k negotiation`
预期：全部 PASS

- [ ] **步骤 3：Commit**

```bash
git add apps/transactions/tests/test_serializers.py
git commit -m "test: add serializer tests for negotiation fields"
```

---

### 任务 15：端到端测试

**文件：**
- 修改：手动测试

- [ ] **步骤 1：完整流程测试**

1. 创建一个新交易
2. 发送包含新字段的发盘消息（填写商品名称、付款方式、交货日期等）
3. 接受报价
4. 验证 Transaction 的共识字段已更新
5. 刷新页面，验证交易详情显示共识条款
6. 验证消息列表正确显示所有字段

- [ ] **步骤 2：验证可选字段为空时的处理**

发送只包含必填字段（商品名称）的消息，确认不会报错

- [ ] **步骤 3：验证枚举字段**

测试各种付款方式，确认显示正确

- [ ] **步骤 4：最终 Commit**

```bash
git add .
git commit -m "feat: complete inquiry message enhancement with e2e validation"
```

---

## 完成检查清单

- [ ] 所有数据库迁移已应用
- [ ] 所有测试通过
- [ ] API 返回新字段
- [ ] 前端表单可以提交新字段
- [ ] 消息显示新字段
- [ ] 交易详情显示共识条款
- [ ] 接受磋商时同步逻辑正确
