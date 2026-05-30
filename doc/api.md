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

统计层不应只提供写死的 `by_department`、`by_expense_type`。

更合理的做法是按"维度 + 指标 + 过滤条件"组织查询：

- **维度**：`department`、`person`、`counterparty`、`record_type`、`taxonomy/category`
- **指标**：`count`、`amount_cents`
- **过滤**：时间区间、来源渠道、状态、分类体系、分类值

### 示例响应

```json
{
  "summary": {
    "record_count": 42,
    "amount_cents": 3845000,      /* 单位分 = ¥38,450.00 */
    "classified_count": 39
  },
  "query": {
    "dimension": "department",
    "metrics": ["count", "amount_cents"],
    "filters": {
      "from": "2026-06-01",
      "to": "2026-06-30",
      "taxonomy": "expense_type"
    }
  },
  "rows": [
    {
      "key": "研发部",
      "count": 15,
      "amount_cents": 1200000    /* 单位分 = ¥12,000.00 */
    },
    {
      "key": "市场部",
      "count": 10,
      "amount_cents": 850000     /* 单位分 = ¥8,500.00 */
    }
  ]
}
```

### 统计原则

- 统计基于 `NormalizedRecord`，**未分类记录也可进入汇总和趋势**
- 分类统计叠加 `ClassificationResult` 作为可选过滤维度
- 不直接基于 `SourceRecord` 做业务口径统计
- 默认只统计 `is_active = true` 且 `review_status = accepted` 的分类结果
