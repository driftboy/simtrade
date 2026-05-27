# 单证样本数据使用指南

## 概述

项目提供了一套基于真实国际贸易惯例的样本单证数据，采用 **CIF + L/C** 出口场景，涵盖全部 10 个贸易环节及 12 份核心单证。数据来源参考了以下公开资源：

- [知乎专栏 — 外贸单证实用模板](https://zhuanlan.zhihu.com/p/706335591)
- [小满科技 — 5 大核心单据全攻略](https://www.xiaoman.cn/article/917.html)
- [trade.gov — Common Export Documents](https://www.trade.gov/common-export-documents)
- [IncoDocs — Commercial Invoice Template](https://incodocs.com/blog/commercial-invoice-template-shipping/)
- [DripCapital — Packing List in Shipping & Exports](https://www.dripcapital.com/en-us/resources/finance-guides/export-packing-list)

## 贸易场景

| 项目 | 内容 |
|------|------|
| 出口商 | 深圳华信电子科技有限公司 (Shenzhen Huaxin Electronics Tech Co., Ltd.) |
| 进口商 | Pacific Digital Trading LLC (洛杉矶) |
| 工厂 | 东莞光电制造厂 |
| 商品 | 蓝牙耳机 HX-BT5Pro (HS: 85183000) |
| 数量/金额 | 5,000 PCS × USD 12.50 = USD 62,500.00 |
| 贸易术语 | CIF Los Angeles, Incoterms 2020 |
| 付款方式 | L/C at sight（不可撤销信用证） |
| 装运港 | 深圳盐田 (CNSZX) |
| 目的港 | 洛杉矶 (USLAX) |
| 承运人 | 中远海运 COSCO SHIPPING GALAXY V.025E |

## 快速初始化

按以下顺序执行管理命令：

```bash
# 1. 基础参考数据（国家、港口、货币、用户角色）
python manage.py init_data

# 2. 商品库
python manage.py init_products

# 3. 10 种贸易角色
python manage.py init_trade_roles

# 4. 单证模板（15 种文档模板及字段定义）
python manage.py init_documents

# 5. 样本交易 + 全套单证数据
python manage.py init_sample_trade
```

所有命令均支持重复执行，已存在的数据会自动跳过。

## 生成的数据

### 10 家参与公司

| 公司代码 | 名称 | 角色 |
|----------|------|------|
| EXP01 | 深圳华信电子科技有限公司 | 出口商 |
| IMP01 | Pacific Digital Trading LLC | 进口商 |
| FAC01 | 东莞光电制造厂 | 工厂 |
| BNK01 | 中国银行深圳市分行 | 银行 |
| CUS01 | 深圳海关 | 海关 |
| SHP01 | 中远海运集装箱运输有限公司 | 货运公司 |
| INS01 | 中国人民财产保险股份有限公司 | 保险公司 |
| IQ01 | 深圳出入境检验检疫局 | 商检机构 |
| FX01 | 国家外汇管理局深圳分局 | 外汇局 |
| TAX01 | 深圳市国家税务局 | 税务局 |

### 10 个交易环节

| 阶段 | 记录 | 编号 | 状态 |
|------|------|------|------|
| 1. 交易 | Transaction #9001 | — | 履约中 |
| 2. 合同 | Contract | HX2026SC001 | 已生效 |
| 3. 信用证 | LetterOfCredit | BOCSZ/2026/LC00856 | 已议付 |
| 4. 采购 | PurchaseOrder | PO20260517001 | 已完成 |
| 5. 货运 | Shipment | SH20260522001 | 已签发提单 |
| 6. 保险 | InsurancePolicy | PICC2026SH05220001 | 已签发 |
| 7. 报检 | InspectionApplication | IA20260518001 | 已签发证书 |
| 8. 报关 | CustomsDeclaration | CD20260522001 | 已放行 |
| 9. 结汇 | ForexSettlement | FX20260525001 | 已结汇 |
| 10. 退税 | TaxRefundApplication | TR20260526001 | 已批准 |

### 12 份单证

所有单证遵循国际贸易 **"单证一致、单单一致"** 原则：发票号、合同号、信用证号、提单号在各份单证中保持一致。

| 单证 | 模板代码 | 关键字段 |
|------|----------|----------|
| 商业发票 | `commercial_invoice` | 发票号 HX-INV-2026-00856, 金额 USD 62,500.00 |
| 装箱单 | `packing_list` | 100 纸箱, 净重 1,200 KGS, 毛重 1,450 KGS |
| 海运提单 | `bill_of_lading` | 提单号 COSU6289510340, 3/3 正本 |
| 汇票 | `bill_of_exchange` | AT SIGHT, 收款人中国银行深圳分行 |
| 信用证 | `letter_of_credit` | 不可撤销, 7 项单据要求 |
| 保险单 | `insurance_policy` | 投保额 USD 68,750.00 (110%), 一切险+战争险 |
| 产地证 | `certificate_of_origin` | FORM A (GSP), CCPIT 签发 |
| 报检单 | `inspection_application` | GB/T 14217-2011, 法定检验 |
| 检验证书 | `inspection_certificate` | AQL 1.0 Level II 合格 |
| 出口报关单 | `export_declaration` | 一般贸易 0110, 退税率 13% |
| 装船通知 | `shipping_advice` | 装船后 24 小时内发送 |
| 受益人证明 | `beneficiary_certificate` | 证明已发送装船通知及单据副本 |

### 单证日期逻辑

按照国际贸易惯例，各单证日期遵循以下先后顺序：

```
合同签署 → L/C 开证 → 报检 → 检验合格 → 产地证 → 投保 → 发票/装箱单
→ 报关 → 装船(提单) → 装船通知/受益人证明 → 交单 → 汇票 → 议付 → 结汇 → 退税
```

## 数据访问

### 通过 Django Shell

```python
from apps.transactions.models import Transaction, Contract
from apps.documents.models import Document

# 查看样本交易
t = Transaction.objects.get(pk=9001)
print(f'{t.seller.name} -> {t.buyer.name}, {t.product.name} x{t.quantity}')

# 查看所有单证
for doc in Document.objects.filter(transaction_id=9001):
    print(f'{doc.template.name}: {doc.get_status_display()}')
```

### 通过 REST API

```
GET /api/v1/transactions/transactions/9001/
GET /api/v1/transactions/contracts/?transaction=9001
GET /api/v1/documents/documents/?transaction_id=9001
```

### 通过管理后台

访问 `/admin/` 可查看和编辑所有交易记录与单证数据。

## 数据来源与参考资料

| 资源 | 说明 |
|------|------|
| [知乎 — 外贸单证实用模板](https://zhuanlan.zhihu.com/p/706335591) | 全套外贸单证模板图片及填制说明 |
| [小满科技 — 5 大核心单据全攻略](https://www.xiaoman.cn/article/917.html) | 商业发票、装箱单、提单、CO、保险单操作要点 |
| [trade.gov — Common Export Documents](https://www.trade.gov/common-export-documents) | 美国商务部出口单证指南 |
| [IncoDocs — Commercial Invoice Template](https://incodocs.com/blog/commercial-invoice-template-shipping/) | 可下载的商业发票模板 |
| [DripCapital — Packing List Examples](https://www.dripcapital.com/en-us/resources/finance-guides/export-packing-list) | 装箱单实例详解 |
| [百运网 — 外贸单证的种类与使用](https://www.by56.com/news/31942.html) | 外贸流程中各类单证的制作顺序 |
| [DHL — 商业发票准备指南](https://www.dhl.com/discover/en-us/global-logistics-advice/essential-guides/how-to-prepare-a-commercial-invoice) | DHL 商业发票填制标准 |

## 扩展建议

如需增加更多样本场景，可在 `init_sample_trade.py` 中添加新的贸易案例，例如：

- **FOB + T/T 场景**：不同贸易术语和付款方式
- **纺织品出口欧盟**：不同商品类别、FORM A 产地证
- **机械设备出口东南亚**：大件货物、特种集装箱
- **空运场景**：航空运单 (AWB) 替代海运提单

每个场景需确保：单证编号互不重复、日期逻辑合理、金额计算准确（如保险金额 = CIF × 110%）。
