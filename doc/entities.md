# 核心实体

## 类型约定

- 所有 `id` 使用 `int`
- 所有金额使用 `int`，单位为"分"
- 所有时间使用 ISO 8601 可序列化格式
- 原始内容尽量保留在 `raw_payload`、`raw_text`、`evidence_refs` 中，不在入库前做不可逆裁剪

## SourceRecord（原始记录）

主干第一层。不是"单据模型"，而是各种输入记录的统一容器。

| 字段 | 类型 | 说明 |
|---|---|---|
| id | `int` PK | 自增主键 |
| source_type | `str` | `image` / `chat` / `form` / `csv_row` / `bank_tx` / `api` / `manual` / `other` |
| source_channel | `str` | `wechat` / `email` / `upload` / `import` / `api` 等 |
| external_id | `str?` | 上游系统主键 |
| raw_payload | `json` | 原始结构化载荷 |
| raw_text | `str` | OCR 或文本抽取结果 |
| evidence_refs | `json` | 附件、截图、文件、对象存储引用 |
| occurred_at | `datetime?` | 原始记录发生时间 |
| ingestion_status | `str` | `pending` / `parsed` / `reviewed` / `failed` |
| created_at | `datetime` | |
| updated_at | `datetime` | |

**职责**：忠实保存原始记录。不要求费用类型、部门、人员在录入时就完全确定。任何后续标准化或分类都应能回溯到此记录。

## NormalizedRecord（标准化记录）

主干第二层。统计分析使用的事实层，不等同于凭证。

| 字段 | 类型 | 说明 |
|---|---|---|
| id | `int` PK | 自增主键 |
| primary_source_id | `int?` FK → source_record | 主要来源记录（快捷路径，可选） |
| record_type | `str` | `expense` / `income` / `transfer` / `reimbursement` / `other` |
| business_date | `date` | 业务日期 |
| amount_cents | `int` | 金额，**单位分**（如 `120000` = ¥1,200.00） |
| currency | `str` | 默认 `CNY` |
| direction | `str` | `outflow` / `inflow` |
| department | `str?` | 部门 |
| person | `str?` | 人员 |
| counterparty | `str?` | 对手方 / 商户 / 收款方 |
| description | `str` | 标准化后的统一描述 |
| normalization_status | `str` | `draft` / `normalized` / `reviewed` / `merged` |
| created_at | `datetime` | |
| updated_at | `datetime` | |

**职责**：统计口径的基础表，保存尽量确定的事实字段。**不负责表达"办公用品""差旅费"这类可变分类**——那是 `ClassificationResult` 的职责。

`primary_source_id` 是针对"一源对应一标准化"的常见场景提供的快捷路径，无需经过 `RecordLink` 即可直接追溯。复杂场景（拆分/合并）仍通过 `RecordLink` 处理。

## RecordLink（原始记录与标准化记录关联）

支持"一条记录拆成多条""多条记录归并成一条"。

| 字段 | 类型 | 说明 |
|---|---|---|
| id | `int` PK | 自增主键 |
| source_record_id | `int` FK → source_record | 原始记录 |
| normalized_record_id | `int` FK → normalized_record | 标准化记录 |
| relation_type | `str` | `primary` / `supplementary` / `split` / `merged` |
| created_at | `datetime` | |

**职责**：避免把模型锁死在"一源单据对应一张凭证"的假设里，支持重跑标准化逻辑时重新关联。

**时序注意**：RecordLink 是关联表，必须等 SourceRecord 和 NormalizedRecord 两端都持久化后才能创建。

## ClassificationResult（分类结果）

主干第三层。分类是对标准化记录的解释，不是原始事实本身。

| 字段 | 类型 | 说明 |
|---|---|---|
| id | `int` PK | 自增主键 |
| normalized_record_id | `int` FK → normalized_record | 被分类的标准化记录 |
| taxonomy | `str` | 分类体系，例如 `expense_type` / `business_tag` |
| category | `str` | 分类值，例如 `办公用品` |
| tags | `json` | 扩展标签 |
| classifier_kind | `str` | `ai` / `rule` / `manual` |
| confidence | `float?` | 置信度 |
| model_version | `str?` | 模型或规则版本 |
| review_status | `str` | `candidate` / `accepted` / `rejected` |
| is_active | `bool` | 当前是否生效 |
| created_at | `datetime` | |
| updated_at | `datetime` | |

说明：

- 同一条 `NormalizedRecord` 可以有多条分类结果
- 可以同时保留 AI 分类、规则分类和人工修订记录
- 统计默认读取 `is_active = true` 且 `review_status = accepted` 的结果

## Journal / JournalEntry / JournalEntryLine（可选下游）

凭证层保留，但不再是主干第一优先级。只在需要对接会计系统、生成凭证、做借贷分录时启用。

| 实体 | 调整说明 |
|---|---|
| Journal | 日记账，保留原有字段 |
| JournalEntry | 可选新增 `normalized_record_id` |
| JournalEntryLine | 金额继续使用分 |
