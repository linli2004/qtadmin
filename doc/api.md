# API 与统计设计

## API 设计

### 原始记录

| 端点 | 方法 | 功能 |
|---|---|---|
| `/source-records` | GET | 原始记录列表，支持来源、状态、时间筛选 |
| `/source-records` | POST | 创建原始记录 |
| `/source-records/{id}` | GET | 原始记录详情 |
| `/source-records/{id}` | PATCH | 更新原始记录 |
| `/source-records/{id}/reparse` | POST | 重新解析原始内容 |

### 标准化记录

| 端点 | 方法 | 功能 |
|---|---|---|
| `/normalized-records` | GET | 标准化记录列表 |
| `/normalized-records` | POST | 手工创建标准化记录 |
| `/normalized-records/{id}` | GET | 标准化记录详情 |
| `/normalized-records/{id}` | PATCH | 修正标准字段 |
| `/normalized-records/{id}/links` | POST | 关联或重关联原始记录 |
| `/normalized-records/{id}/normalize` | POST | 重跑标准化 |

### 分类结果

| 端点 | 方法 | 功能 |
|---|---|---|
| `/normalized-records/{id}/classifications` | GET | 查询该记录的分类结果 |
| `/normalized-records/{id}/classifications` | POST | 新增分类结果 |
| `/classifications/{id}` | PATCH | 审核、激活、废弃分类结果 |
| `/classifications/rebuild` | POST | 批量重跑分类 |

### 统计

| 端点 | 方法 | 功能 |
|---|---|---|
| `/statistics/summary` | GET | 汇总统计 |
| `/statistics/breakdown` | GET | 按维度分组统计 |
| `/statistics/trend` | GET | 时间趋势统计 |
| `/statistics/drilldown` | GET | 查看满足条件的明细记录 |

### 可选凭证

| 端点 | 方法 | 功能 |
|---|---|---|
| `/postings/generate` | POST | 基于标准化记录生成凭证 |
| `/entries/{id}` | GET | 凭证详情 |
| `/journals/{id}/entries` | GET | 日记账下凭证列表 |

---

## 统计设计

### 统计原则

- 统计基于 `NormalizedRecord`，**未分类记录也可进入汇总和趋势**
- 分类统计叠加 `ClassificationResult` 作为可选过滤维度
- 不直接基于 `SourceRecord` 做业务口径统计
- 默认只统计 `is_active = true` 且 `review_status = accepted` 的分类结果
- `normalization_status = draft` 不排除——标准化是内部状态，不影响财务事实
- 货币处理：`amount_cents` 的聚合（SUM）仅在单一币种下有意义，未传 `currency` 时默认 `CNY`；`currency=*` 表示不限币种（此时不返回 `amount_cents`）
- `normalization_status` 不过滤，`draft` 状态的记录也参与统计

### 端点

#### `GET /statistics/summary` — 汇总统计

Query 参数（全部可选，不传代表全量）：

| 参数 | 类型 | 说明 |
|:-----|:-----|:------|
| `from_date` / `to_date` | `date?` | 业务日期区间 |
| `department` / `person` / `counterparty` | `str?` | 精确匹配 |
| `record_type` | `str?` | 枚举校验 |
| `direction` | `str?` | 枚举校验 |
| `currency` | `str?` | 默认 `CNY`，`*` 不限 |
| `source_channel` | `str?` | ⚠️ 待数据模型确定后追加（`NormalizedRecord` 无此字段） |
| `normalization_status` | `str?` | 枚举校验 |
| `taxonomy` + `category` | `str?` | 必须成对，缺一 422 |

#### `GET /statistics/breakdown` — 按维度分组

额外参数：

| 参数 | 类型 | 必填 | 说明 |
|:-----|:-----|:----:|:------|
| `dimension` | `str` | 是 | `department` / `person` / `counterparty` / `record_type` / `direction` / `currency` |

`dimension` 非法值 → 422。空值分组保留（`key=null` 不丢弃）。排序按 `count` 降序。

#### `GET /statistics/trend` — 时间趋势

额外参数：

| 参数 | 类型 | 必填 | 默认 | 说明 |
|:-----|:-----|:----:|:----:|:------|
| `granularity` | `str` | 否 | `day` | `day` / `week` / `month` |

`granularity` 非法值 → 422。不填充零值区间。排序按日期升序。

#### `GET /statistics/drilldown` — 明细穿透

额外参数：

| 参数 | 类型 | 必填 | 默认 | 说明 |
|:-----|:-----|:----:|:----:|:------|
| `skip` | `int` | 否 | 0 | 偏移量 |
| `limit` | `int` | 否 | 50 | 上限 200，超限 422 |

复用 `NormalizedRecordResponse` 作为行类型。排序按 `business_date` 降序。

### 完整过滤参数清单

| 参数 | summary | breakdown | trend | drilldown |
|:-----|:-------:|:---------:|:-----:|:---------:|
| `from_date` / `to_date` | ✅ | ✅ | ✅ | ✅ |
| `department` / `person` / `counterparty` | ✅ | ✅ | ✅ | ✅ |
| `record_type` / `direction` | ✅ | ✅ | ✅ | ✅ |
| `currency` | ✅ | ✅ | ✅ | ✅ |
| `source_channel` | ⚠️ | ⚠️ | ⚠️ | ⚠️ |
| `normalization_status` | ✅ | ✅ | ✅ | ✅ |
| `taxonomy` + `category` | ✅ | ✅ | ✅ | ✅ |

### 错误处理

| 场景 | 响应 |
|:-----|:------|
| 无数据 | Summary 全 0；其余 items/rows 为 [] |
| `dimension` / `granularity` 非法 | 422 + 合法值列表 |
| `record_type` / `direction` / `normalization_status` 非法 | 422（field_validator） |
| `taxonomy` 无 `category`（反之亦然） | 422 |
| `limit > 200` | 422 |
| `currency` 非法 | 422 |
| `from_date > to_date` | 422 |
| 维度字段全为 null | 保留 `key=null` 分组，不丢弃 |
