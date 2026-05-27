# 样本贸易场景扩展 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 在 `init_sample_trade.py` 中新增 4 个样本贸易场景，覆盖 FOB+T/T、纺织品出口欧盟、机械设备出口东南亚、空运出口日本。

**架构：** 在现有 `Command` 类中新增 4 个场景方法（`_create_scenario_X`），由 `handle()` 统一调用。无需模型改造 — 现有模型已足够灵活：`Shipment.vessel_name` 已标注"船名/航班号"且 `blank=True`，`ForexSettlement` 已是 `ForeignKey` 支持多笔结汇，L/C 和 Insurance 只需不创建即可跳过。

**技术栈：** Django management command, Decimal, JSON

---

## 重要发现：无需模型改造

经代码审查，之前规格中的 3 项模型改造实际上**不需要**：

| 原评估问题 | 实际情况 |
|-----------|---------|
| Shipment 缺少空运字段 | `vessel_name` 已标注"船名/航班号"且 `blank=True`（`models.py:560`），`bl_no` 可存 AWB 号 |
| LetterOfCredit 需改为可选 | OneToOne 在 LC 侧（`models.py:287`），不创建即可，无需改模型 |
| ForexSettlement 需支持多笔 | 已是 `ForeignKey`（`models.py:847`），天然支持多条记录 |

## 文件影响

| 文件 | 操作 | 职责 |
|------|------|------|
| `apps/transactions/management/commands/init_sample_trade.py` | 修改 | 新增 4 个场景方法 + 重构 handle() |

---

### 任务 1：重构现有代码，提取公司创建辅助函数

**文件：**
- 修改：`apps/transactions/management/commands/init_sample_trade.py`

**目的：** 将现有 `companies_data` 列表和创建逻辑提取为 `_create_company()` 辅助方法，供 5 个场景共用。

- [ ] **步骤 1：添加 `_create_company` 辅助方法**

在 `Command` 类中添加静态方法（放在 `_create_documents` 之前）：

```python
@staticmethod
def _create_company(code, name, name_en, country_code, ctype, addr, phone, email):
    """创建或获取公司，返回 (company, created) 元组"""
    from apps.core.models import Country
    country = Country.objects.filter(code=country_code).first()
    company, created = Company.objects.get_or_create(
        code=code,
        defaults={
            'name': name, 'name_en': name_en,
            'country': country, 'type': ctype,
            'address': addr, 'phone': phone, 'email': email,
        }
    )
    return company, created
```

- [ ] **步骤 2：添加 `_ensure_country` 和 `_ensure_currency` 辅助方法**

```python
@staticmethod
def _ensure_country(code, name, phone_code=''):
    """确保国家存在"""
    country, created = Country.objects.get_or_create(
        code=code,
        defaults={'name': name, 'phone_code': phone_code}
    )
    return country

@staticmethod
def _ensure_currency(code, name, symbol=''):
    """确保货币存在"""
    currency, created = Currency.objects.get_or_create(
        code=code,
        defaults={'name': name, 'symbol': symbol}
    )
    return currency
```

- [ ] **步骤 3：添加 `_ensure_product` 辅助方法**

```python
@staticmethod
def _ensure_product(code, name, name_en, category, unit, hs_code, description=''):
    """确保商品存在"""
    product, created = Product.objects.get_or_create(
        code=code,
        defaults={
            'name': name, 'name_en': name_en,
            'category': category, 'unit': unit,
            'hs_code': hs_code, 'description': description,
        }
    )
    return product
```

- [ ] **步骤 4：重构 `handle()` 中现有公司创建逻辑，使用 `_create_company`**

将 `handle()` 中 `companies_data` 循环替换为调用 `_create_company`。保留现有行为不变，只是用新方法。

- [ ] **步骤 5：将现有场景代码提取到 `_create_scenario_cif_lc()` 方法中**

将 `handle()` 中步骤 2-11 的代码移入 `_create_scenario_cif_lc(self, now, companies, huaxin_user)` 方法。`handle()` 调用它。

- [ ] **步骤 6：运行命令验证无回归**

运行：`python manage.py init_sample_trade`
预期：输出与重构前一致，无报错

- [ ] **步骤 7：Commit**

```bash
git add apps/transactions/management/commands/init_sample_trade.py
git commit -m "refactor: extract helper methods from init_sample_trade"
```

---

### 任务 2：添加场景 1 — FOB + T/T（电子消费品出口中东）

**文件：**
- 修改：`apps/transactions/management/commands/init_sample_trade.py`

**关键差异**：无信用证、无保险、两笔分批结汇（30% 预付 + 70% 见提单副本）

- [ ] **步骤 1：在 `_create_scenario_cif_lc` 后添加 `_create_scenario_fob_tt` 方法**

该方法创建以下数据：

**公司和用户**（复用现有银行/海关/货运等角色公司）：
```python
exp02, _ = self._create_company(
    'EXP02', '深圳华芯电子科技有限公司',
    'Shenzhen Huaxin Chip Electronics Co., Ltd.',
    'CN', 'electronics',
    '深圳市福田区华强北路赛格广场A座1208',
    '+86-755-83001234', 'trade@huaxin-chip.com')
imp02, _ = self._create_company(
    'IMP02', 'Al Rashid Trading LLC',
    'Al Rashid Trading LLC',
    'AE', 'trading',
    'Dubai Silicon Oasis, DDP Building A, Office 305',
    '+971-4-3201234', 'import@alrashid-trading.ae')
```

**商品**：
```python
product = self._ensure_product(
    'E002', '智能手表 Smart Watch', 'Smart Watch HX-WatchPro',
    'electronics', 'PCS', '910212',
    '1.69寸AMOLED屏, 心率血氧, GPS, IP68防水, 7天续航')
```

**交易**（Transaction pk=9002）：
```python
transaction = Transaction(
    pk=9002,
    buyer=imp02, seller=exp02, product=product,
    status='completed',
    quantity=2000, unit_price=Decimal('25.00'),
    currency='USD', trade_term='FOB',
    port_of_loading='Shenzhen',
    port_of_discharge='Jebel Ali, Dubai',
    notes='样本交易：智能手表出口阿联酋，FOB Shenzhen，T/T 30%+70%')
```

**合同**（contract_no='HXCHIP2026SC001'）：
- payment_term: 'T/T (30% advance + 70% against B/L copy)'
- trade_term: 'FOB'
- total_amount: Decimal('50000.00')

**采购订单**：
- 2,000 只智能手表，向工厂采购价 CNY 128/只

**货运**（shipment_no='SH20260601001'）：
- 1×20'GP 集装箱
- 深圳（盐田）→ 杰贝阿里港
- vessel: 'CMA CGM MARCO POLO V.023W'

**无保险**（FOB 术语下卖方不负责保险，不创建 InsurancePolicy 记录）

**报检**：
- inspection_type: 'legal'
- 法定检验

**报关**：
- hs_code: '910212'
- total_value: Decimal('50000.00')

**外汇结算**（两笔）：
```python
# 第一笔：30% 预付
ForexSettlement(
    customs_declaration=customs,
    applicant=exp02,
    forex_bureau=companies['forex'],
    foreign_currency='USD',
    foreign_amount=Decimal('15000.00'),  # 30% of 50000
    reference_rate=Decimal('7.2450'),
    reference_cny_amount=Decimal('108675.00'),
    settlement_rate=Decimal('7.2380'),
    settlement_cny_amount=Decimal('108570.00'),
    status='settled',
    notes='T/T 预付 30%',
)
# 第二笔：70% 见提单副本
ForexSettlement(
    customs_declaration=customs,
    applicant=exp02,
    forex_bureau=companies['forex'],
    foreign_currency='USD',
    foreign_amount=Decimal('35000.00'),  # 70% of 50000
    reference_rate=Decimal('7.2450'),
    reference_cny_amount=Decimal('253575.00'),
    settlement_rate=Decimal('7.2380'),
    settlement_cny_amount=Decimal('253330.00'),
    status='settled',
    notes='T/T 尾款 70%，凭提单副本付款',
)
```

**退税**：
- refund_rate: Decimal('0.13')（电子产品 13%）

**单证**（8 种）：
1. commercial_invoice — 商业发票
2. packing_list — 装箱单
3. bill_of_lading — 海运提单
4. certificate_of_origin — 产地证 FORM A
5. inspection_application — 报检单
6. inspection_certificate — 检验证书
7. export_declaration — 出口报关单
8. shipping_advice — 装船通知

每种单证的 JSON data 字段需包含完整的单证信息（参考现有 `_create_documents` 中的格式），所有编号、日期、金额与本场景一致。

- [ ] **步骤 2：在 `handle()` 中调用 `_create_scenario_fob_tt`**

在 `_create_scenario_cif_lc` 调用后添加：
```python
self.stdout.write('\n' + '=' * 60)
self.stdout.write('场景 2：FOB + T/T（智能手表出口阿联酋）')
self.stdout.write('=' * 60)
self._create_scenario_fob_tt(now, companies, huaxin_user)
```

- [ ] **步骤 3：运行命令验证**

运行：`python manage.py init_sample_trade`
预期：输出包含"场景 2"数据，无报错

- [ ] **步骤 4：验证数据正确性**

```python
# 在 Django shell 中验证
from apps.transactions.models import Transaction, ForexSettlement
t = Transaction.objects.get(pk=9002)
assert t.trade_term == 'FOB'
assert not hasattr(t.contract, 'letter_of_credit') or not LetterOfCredit.objects.filter(contract=t.contract).exists()
assert ForexSettlement.objects.filter(customs_declaration__shipment__contract=t.contract).count() == 2
```

- [ ] **步骤 5：Commit**

```bash
git add apps/transactions/management/commands/init_sample_trade.py
git commit -m "feat: add FOB+T/T sample trade scenario (smartwatch to UAE)"
```

---

### 任务 3：添加场景 2 — 纺织品出口欧盟（CIF + L/C）

**文件：**
- 修改：`apps/transactions/management/commands/init_sample_trade.py`

**关键差异**：EUR 货币、纺织品退税率 9%、FORM A 欧盟普惠制产地证

- [ ] **步骤 1：在 `_create_scenario_fob_tt` 后添加 `_create_scenario_textile_eu` 方法**

**公司**：
```python
exp03, _ = self._create_company(
    'EXP03', '杭州丝绸之纺织品有限公司',
    'Hangzhou Silk Road Textiles Co., Ltd.',
    'CN', 'textiles',
    '杭州市萧山区市心北路188号丝绸之大厦',
    '+86-571-82801234', 'export@silkroad-textile.com')
imp03, _ = self._create_company(
    'IMP03', 'Fashion Europe GmbH',
    'Fashion Europe GmbH',
    'DE', 'trading',
    'Mönckebergstraße 7, 20095 Hamburg, Germany',
    '+49-40-3001234', 'purchasing@fashion-europe.de')
```

**确保 EUR 货币存在**：
```python
eur = self._ensure_currency('EUR', 'Euro', '€')
```

**商品**：
```python
product = self._ensure_product(
    'T001', '棉质女式针织外套', "Women's Cotton Knitted Coat",
    'textiles', 'PCS', '6104',
    '60%棉 40%聚酯纤维, 针织, 女式, 外套, 多色可选')
```

**交易**（pk=9003）：
- 10,000 件，CIF Hamburg EUR 8.50/件 = EUR 85,000

**合同**（contract_no='SR2026SC001'）：
- trade_term: 'CIF', payment_term: 'L/C at sight'
- currency: 'EUR'

**信用证**（lc_no='COMMB/2026/LC00234'）：
- issuing_bank: 'Commerzbank AG, Hamburg'
- advising_bank: '中国银行杭州市分行'
- currency: 'EUR', amount: Decimal('85000.00')

**采购订单**：
- 向纺织工厂采购，CNY 计价

**货运**（shipment_no='SH20260605001'）：
- 1×40'GP，上海 → 汉堡
- vessel: 'MSC GULSUN V.012W'
- eta: etd + timedelta(days=28)（上海到汉堡约 28 天）

**保险**：
- insured_amount: Decimal('93500.00')（EUR 85000 × 110%）
- premium: Decimal('561.00')（约 0.6%）
- coverage_type: 'all_risk'

**报检 + 检验证书**：
- 纺织品法定检验，符合 GB 18401-2010 国家纺织产品基本安全技术规范

**报关**：
- hs_code: '6104', 退税率 9%

**外汇结算**（单笔，EUR）：
- EUR 85,000，参考汇率 EUR/CNY 7.85

**退税**：
- refund_rate: Decimal('0.09')（纺织品 9%）

**单证**（11 种）：
1. commercial_invoice
2. packing_list
3. bill_of_lading
4. bill_of_exchange
5. letter_of_credit
6. insurance_policy
7. certificate_of_origin（FORM A，注明欧盟普惠制）
8. inspection_application
9. inspection_certificate
10. export_declaration
11. shipping_advice

- [ ] **步骤 2：在 `handle()` 中调用**

- [ ] **步骤 3：运行命令验证**

运行：`python manage.py init_sample_trade`
预期：输出包含"场景 3"数据，无报错

- [ ] **步骤 4：Commit**

```bash
git add apps/transactions/management/commands/init_sample_trade.py
git commit -m "feat: add textile EU sample trade scenario (CIF+L/C)"
```

---

### 任务 4：添加场景 3 — 机械设备出口东南亚（CIF + L/C）

**文件：**
- 修改：`apps/transactions/management/commands/init_sample_trade.py`

**关键差异**：特种集装箱（开顶柜）、FORM E 产地证（中国-东盟自贸区）、大件设备

- [ ] **步骤 1：在 `_create_scenario_textile_eu` 后添加 `_create_scenario_machinery_sea` 方法**

**公司**：
```python
exp04, _ = self._create_company(
    'EXP04', '广州重工机械有限公司',
    'Guangzhou Heavy Machinery Co., Ltd.',
    'CN', 'machinery',
    '广州市黄埔区开发大道388号重工产业园',
    '+86-20-82201234', 'export@gz-heavy.com')
imp04, _ = self._create_company(
    'IMP04', 'Siam Industrial Co., Ltd.',
    'Siam Industrial Co., Ltd.',
    'TH', 'manufacturing',
    '888 Vibhavadi Rangsit Road, Chatuchak, Bangkok 10900',
    '+66-2-6101234', 'procurement@siam-industrial.co.th')
```

**商品**：
```python
product = self._ensure_product(
    'M001', '数控车床 CNC Lathe', 'CNC Lathe GZ-CK6150',
    'machinery', 'SET', '845811',
    '最大加工直径500mm, 最大加工长度1000mm, 主轴转速50-3000rpm, 精度0.01mm')
```

**交易**（pk=9004）：
- 3 台，CIF Bangkok USD 35,000/台 = USD 105,000

**合同**（contract_no='GZH2026SC001'）：
- packing: '每台固定于开顶集装箱内，防锈处理，木质底座加固绑扎'
- remarks 含设备安装调试条款

**信用证**（lc_no='BANGKOK/2026/LC00567'）：
- issuing_bank: 'Bangkok Bank Public Company Limited'
- advising_bank: '中国银行广州市分行'

**货运**（shipment_no='SH20260608001'）：
- 1×40'OFR 开顶集装箱（`container_no: 'BMOU5234817 / 40OFR'`）
- notes: 'Open-top container, cargo lashed and secured, heavy-lift surcharge applied'
- 广州黄埔 → 林查班港（Laem Chabang）
- vessel: 'EVER GREEN V.036E'
- eta: etd + timedelta(days=7)（广州到林查班约 7 天）

**保险**：
- insured_amount: Decimal('115500.00')（USD 105000 × 110%）
- notes: 'Covering loading/unloading risks for heavy machinery'

**报检**：
- inspection_type: 'legal'（机械设备属于法定检验）
- product_spec 包含技术参数

**报关**：
- hs_code: '845811'
- 退税率 13%

**外汇结算**：USD 105,000

**退税**：refund_rate: Decimal('0.13')

**单证**（11 种）：
1. commercial_invoice
2. packing_list
3. bill_of_lading
4. bill_of_exchange
5. letter_of_credit
6. insurance_policy
7. certificate_of_origin（FORM E，注明中国-东盟自贸区）
8. inspection_application
9. inspection_certificate
10. export_declaration
11. shipping_advice

- [ ] **步骤 2：在 `handle()` 中调用**

- [ ] **步骤 3：运行命令验证**

- [ ] **步骤 4：Commit**

```bash
git add apps/transactions/management/commands/init_sample_trade.py
git commit -m "feat: add machinery SEA sample trade scenario (CIF+L/C, open-top container)"
```

---

### 任务 5：添加场景 4 — 空运出口日本（CIP + T/T）

**文件：**
- 修改：`apps/transactions/management/commands/init_sample_trade.py`

**关键差异**：空运（AWB 替代 B/L）、T/T 100% 预付、CIP 术语、无信用证/汇票、纸箱包装

- [ ] **步骤 1：在 `_create_scenario_machinery_sea` 后添加 `_create_scenario_air_freight` 方法**

**公司**：
```python
exp05, _ = self._create_company(
    'EXP05', '苏州精密仪器有限公司',
    'Suzhou Precision Instruments Co., Ltd.',
    'CN', 'electronics',
    '苏州市工业园区星湖街218号精密仪器产业园',
    '+86-512-62801234', 'export@sz-precision.com')
imp05, _ = self._create_company(
    'IMP05', 'Yamada Electronics 株式会社',
    'Yamada Electronics Co., Ltd.',
    'JP', 'electronics',
    '東京都千代田区丸の内1-8-3 丸の内ビルディング 15F',
    '+81-3-62001234', 'purchase@yamada-elec.co.jp')
```

**商品**（归入 electronics 分类）：
```python
product = self._ensure_product(
    'E003', '高精度传感器 High-Precision Sensor', 'High-Precision Sensor SP-X200',
    'electronics', 'PCS', '903149',
    '测量精度±0.01%, 工作温度-40~85℃, IP67防护, 输出信号4-20mA/RS485')
```

**交易**（pk=9005）：
- 500 个，CIP Tokyo USD 120.00/个 = USD 60,000
- trade_term: 'CIP'

**合同**（contract_no='SZPI2026SC001'）：
- payment_term: 'T/T 100% in advance'
- trade_term: 'CIP'
- packing: '每个传感器独立防静电包装，20个/纸箱，共25纸箱'

**无信用证**（T/T 付款，不创建 LetterOfCredit 和 BankOperation）

**货运**（shipment_no='SH20260610001'）：
```python
shipment = Shipment(
    contract=contract,
    shipper=exp05,
    carrier=companies['shipping'],  # 复用或创建航空公司
    bl_no='618-12345675',  # AWB 航空运单号格式
    vessel_name='CA929 / MU537',  # 航班号
    port_of_loading='Shanghai Pudong (PVG)',
    port_of_discharge='Tokyo Narita (NRT)',
    container_no='',  # 空运无集装箱
    freight_amount=Decimal('2800.00'),
    freight_currency='USD',
    notes='AIR FREIGHT, AWB: 618-12345675, 25 cartons on air pallet',
)
```

**保险**（CIP 术语下卖方负责保险）：
- insured_amount: Decimal('66000.00')（USD 60000 × 110%）
- coverage_type: 'all_risk'
- notes: 'Air cargo insurance, covering warehouse to warehouse including air transit'

**报检**：
- inspection_type: 'general'（精密仪器一般鉴定）

**报关**：
- hs_code: '903149'
- transport_mode 在 data 中注明"航空运输 (5)"

**外汇结算**（单笔 T/T 预付）：
- USD 60,000

**退税**：
- refund_rate: Decimal('0.13')（电子产品 13%）

**单证**（8 种）：
1. commercial_invoice
2. packing_list
3. bill_of_lading（data 中标注为航空运单 AWB，AWB 号存入 bl_no 字段）
4. insurance_policy
5. certificate_of_origin
6. inspection_application
7. inspection_certificate
8. export_declaration（data 中注明航空运输）

- [ ] **步骤 2：在 `handle()` 中调用**

- [ ] **步骤 3：运行命令验证**

- [ ] **步骤 4：Commit**

```bash
git add apps/transactions/management/commands/init_sample_trade.py
git commit -m "feat: add air freight sample trade scenario (CIP+T/T, AWB, to Japan)"
```

---

### 任务 6：更新 `handle()` 汇总输出

**文件：**
- 修改：`apps/transactions/management/commands/init_sample_trade.py`

- [ ] **步骤 1：更新最终汇总统计**

将 `handle()` 末尾的汇总更新为覆盖所有 5 个场景：

```python
self.stdout.write('\n' + '=' * 60)
self.stdout.write(self.style.SUCCESS('全部样本交易数据生成完毕！'))
self.stdout.write('=' * 60)
self.stdout.write(f'  公司: {Company.objects.count()} 家')
self.stdout.write(f'  交易: {Transaction.objects.count()} 笔')
self.stdout.write(f'  合同: {Contract.objects.count()} 份')
self.stdout.write(f'  单证记录: {Document.objects.count()} 份')
```

- [ ] **步骤 2：运行完整命令**

运行：`python manage.py init_sample_trade`
预期：5 个场景全部输出成功，无报错

- [ ] **步骤 3：验证数据完整性**

在 Django shell 中运行：
```python
from apps.transactions.models import *
from apps.documents.models import Document

# 验证 5 笔交易
assert Transaction.objects.count() == 5

# 验证场景 1（CIF+L/C）有信用证
t1 = Transaction.objects.get(pk=9001)
assert LetterOfCredit.objects.filter(transaction=t1).count() == 1

# 验证场景 2（FOB+T/T）无信用证、两笔结汇
t2 = Transaction.objects.get(pk=9002)
assert LetterOfCredit.objects.filter(contract__transaction=t2).count() == 0
assert ForexSettlement.objects.filter(customs_declaration__shipment__contract=t2.contract).count() == 2

# 验证场景 4（空运）AWB 格式
t5 = Transaction.objects.get(pk=9005)
s5 = Shipment.objects.get(contract=t5.contract)
assert '-' in s5.bl_no  # AWB 格式含连字符

# 验证单证总数 >= 8+11+11+8 = 38（加上场景1的12份 = 50）
assert Document.objects.count() >= 38

print('全部验证通过！')
```

- [ ] **步骤 4：Commit**

```bash
git add apps/transactions/management/commands/init_sample_trade.py
git commit -m "feat: update init_sample_trade summary output for 5 scenarios"
```

---

## 自检

**1. 规格覆盖度：**
- FOB+T/T 场景 → 任务 2 ✓
- 纺织品出口欧盟 → 任务 3 ✓
- 机械设备出口东南亚 → 任务 4 ✓
- 空运出口日本 → 任务 5 ✓
- 模型改造 → 已验证不需要 ✓
- 单证编号互不重复 → 各场景使用不同编号前缀 ✓
- 日期逻辑合理 → 各场景日期不重叠，使用 timedelta ✓
- 金额计算准确（CIF×110%）→ 任务 3/4/5 保险金额均按此计算 ✓

**2. 占位符扫描：** 无 TODO/待定/后续。所有代码步骤均含具体数据。

**3. 类型一致性：**
- `_create_company` 返回 `(company, created)` 与现有 `get_or_create` 模式一致
- 各场景 Transaction pk（9001-9005）不冲突
- contract_no 各场景前缀不同（HX2026SC / HXCHIP2026SC / SR2026SC / GZH2026SC / SZPI2026SC）
- shipment_no 使用不同日期前缀避免冲突
