# 安全设计

## 数据脱敏与本地化

### 脱敏时机

脱敏在**数据离站前一刻**执行，不污染存储层。原始 `raw_text` 和 `description` 完整入库，仅在发往外部 AI 前做脱敏替换。

```text
原始 description
    │
    ├──→ 本地模型（Ollama）：不脱敏，数据不出域
    │
    └──→ 外部 AI API：先脱敏，再发送
                │
                └── 脱敏版不落库，用完即弃
```

### 脱敏规则

| 敏感类型 | 替换方式 |
|---|---|
| 数字金额 | `[AMOUNT]`（V1） |
| 18 位身份证号 | `[ID_CARD]` |
| 银行卡号 | `[BANK_CARD]` |
| 手机号 | `[PHONE]` |
| 不在通讯录白名单中的人名 | `[PERSON]` |

说明：

- 脱敏只做**类型标记替换**，不哈希、不加密、不保留原文片段
- 保留语义信息（"这里有一笔金额/一个人名"）供 AI 参考
- 精确值不需要发给 AI，因为 `NormalizedRecord` 已有结构化金额

### 外部 API 审计

记录每次外部调用的：

- 脱敏后的输入（不是原始输入）
- 输出结果、时间戳、模型版本、耗时

禁止记录原始 `description` 到审计日志。

---

## 分类结果安全

### 审核机制

| `review_status` | 含义 | 是否参与统计 |
|---|---|---|
| `candidate` | AI/规则建议，待审核 | 否 |
| `accepted` | 人工确认通过 | 是 |
| `rejected` | 人工驳回 | 否 |

### 置信度阈值

可配置参数：

```yaml
classification:
  confidence_threshold: 0.7    # 默认值，管理后台可调
  auto_review_below: true      # 低于阈值的自动标记 candidate
```

初期从 `0.7` 起步，观察一周后根据实际分布校准。不同分类体系可设不同阈值。

### 分类版本与回滚

- `model_version` 字段记录每次分类使用的模型/规则版本
- 批量重跑生成新版本，旧结果 `is_active = false`
- 统计默认读 `is_active = true` 且 `review_status = accepted` 的结果
- 提供版本对比 API，便于人工复核差异

### 分类回写闭环

AI 分类结果不覆盖 `NormalizedRecord`。两阶段：

1. AI 分类 → 写入 `ClassificationResult`，`review_status = candidate`
2. 人工审核确认 → `review_status = accepted`，此时结果生效

分类结果仅存储在 `ClassificationResult` 中，不回写 `NormalizedRecord`。

---

## 防注入与输入校验

### 输入限制

| 字段 | 最大长度 | 超限处理 |
|---|---|---|
| `raw_text` | 65535 字符 | 截断或拒绝，由应用层策略决定 |
| `description` | 1000 字符 | 截断或拒绝，由应用层策略决定 |

### Taxonomy 定义与校验

**V1 硬编码（services/classification.py）**：

```python
EXPENSE_TYPE_TAXONOMY = ["办公用品", "差旅", "采购", "工资", "其他"]

def validate_category(category: str) -> bool:
    return category in EXPENSE_TYPE_TAXONOMY
```

校验规则：AI 返回的 `category` 必须在列表中，否则标记 `review_status = rejected` + 异常标签 `unknown`，不参与统计。

**V2+ 演化**：

| 阶段 | Taxonomy 位置 | 说明 |
|---|---|---|
| V1 | 代码内硬编码 | 预定义基础列表 |
| V2 | 数据库表 + 管理后台 | 支持增删改，记录版本 |
| 远期 | 多 taxonomy 并存 | 不同部门/项目使用不同体系 |

Taxonomy 表结构（V2+）：

```text
taxonomies
├── id: int PK
├── name: str              # 分类体系名称
├── version: int
├── categories: json       # ["办公用品", "差旅", ...]
├── is_active: bool
└── created_at: datetime
```

校验规则：

- 分类时指定 `taxonomy` + `version`
- 后端检查 `category` 是否在该版本的 `categories` 列表中
- 非法值丢弃，或标记 `rejected` + 附加 `unknown`
- taxonomy 版本变更后触发存量 `candidate` 结果重新校验

### 沙箱测试

分类规则或模型上线前，用历史数据做批量测试。

报告格式：

1. 总体统计：总数 N，一致 M 条，不一致 K 条
2. 不一致列表：按置信度差额降序排列
3. 抽样建议：从高差额中抽取 10% 人工复核；错误率 > 5% 则扩大抽样
