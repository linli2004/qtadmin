# 核心实体

> 本文档是字段默认值、约束规则、截断策略的唯一规范来源。

## 类型约定

- 所有 `id` 使用 `int`
- 所有金额使用 `int`，单位为"分"
- 所有时间使用 ISO 8601 可序列化格式
- **不可逆裁剪禁令**：`raw_payload`、`raw_text`、`evidence_refs` 中的原始内容必须在入库前完整保留，不做截断、哈希、脱敏等不可逆变换。所有数据变换（截断、脱敏）必须发生在离站时（发往外部 AI 前），而非入库前

## 约束分层策略

| 约束类型 | 实施层 | 说明 |
|---------|--------|------|
| **必填、类型、数值范围（如 `amount_cents ≥ 0`）、`raw_text` 超限拒绝、`description` 超限截断** | Pydantic Schema（`field_validator`） | API 入口第一道关，快速反馈 |
| **枚举值域** | Pydantic `Literal` + ORM 列注释 `doc` | ORM 层不设 `Enum` 类型以保持方言兼容，增加新值无需迁移 |
| **外键、唯一性、非空** | 数据库层（Alembic 迁移） | 数据完整性的最后防线 |

**写路径约束**：所有数据写入必须经过 Pydantic Schema 校验。内部服务层和 API 层统一使用 Schema 序列化后写入，禁止直接实例化 ORM 模型并传入原始字典绕过校验。此约束通过代码评审强制执行，M1 不引入自动化检测。

## 枚举值域速查

| 字段 | 所属实体 | 合法值 |
|:-----|:---------|:-------|
| `source_type` | SourceRecord | `image` / `chat` / `form` / `csv_row` / `bank_tx` / `api` / `manual` / `other` |
| `ingestion_status` | SourceRecord | `pending` / `parsed` / `reviewed` / `failed` |
| `record_type` | NormalizedRecord | `expense` / `income` / `transfer` / `reimbursement` / `other` |
| `direction` | NormalizedRecord | `outflow` / `inflow` |
| `normalization_status` | NormalizedRecord | `draft` / `normalized` / `reviewed` / `merged` |
| `relation_type` | RecordLink | `primary` / `supplementary` / `split` / `merged` |
| `taxonomy` | ClassificationResult | `expense_type` |
| `classifier_kind` | ClassificationResult | `ai` / `rule` / `manual` |
| `review_status` | ClassificationResult | `candidate` / `accepted` / `rejected` |
| `line_type` | JournalEntryLine | `debit` / `credit` |

---

## SourceRecord（原始记录）

主干第一层。不是"单据模型"，而是各种输入记录的统一容器。

| 字段 | 类型 | 默认值 | 约束 | 说明 |
|:-----|:-----|:------:|:-----|:-----|
| id | `int` PK | 自增 | — | 自增主键 |
| source_type | `str` | — | `Literal` | 见枚举值域表 |
| source_channel | `str?` | `null` | — | `wechat` / `email` / `upload` / `import` / `api` 等，非枚举约束 |
| external_id | `str?` | `null` | — | 上游系统主键 |
| raw_payload | `json` | `null` | — | 原始结构化载荷 |
| raw_text | `str` | `''` | 最大 65535 字符，超限拒绝 | OCR 或文本抽取结果。**超限规则**：Schema `field_validator` 中超过 65535 时抛出 `ValidationError`，返回 422。不截断、不静默丢弃。拒绝原因和原始内容尺寸通过错误消息返回调用方。数据库类型使用 TEXT |
| evidence_refs | `json` | `null` | — | 附件、截图、文件、对象存储引用 |
| occurred_at | `datetime?` | `null` | — | 原始记录发生时间 |
| ingestion_status | `str` | `pending` | `Literal` | 见枚举值域表 |
| created_at | `datetime` | `func.now()` | — | |
| updated_at | `datetime` | `func.now()` | `onupdate` | |

**职责**：忠实保存原始记录。不要求费用类型、部门、人员在录入时就完全确定。任何后续标准化或分类都应能回溯到此记录。

---

## NormalizedRecord（标准化记录）

主干第二层。统计分析使用的事实层，不等同于凭证。

| 字段 | 类型 | 默认值 | 约束 | 说明 |
|:-----|:-----|:------:|:-----|:-----|
| id | `int` PK | 自增 | — | 自增主键 |
| primary_source_id | `int?` FK | `null` | — | 主要来源记录快捷路径（可选），复杂场景走 RecordLink |
| record_type | `str` | — | `Literal` | 见枚举值域表 |
| business_date | `date` | — | — | 业务日期 |
| amount_cents | `int` | `0` | **必须 ≥ 0**（`ge=0`） | 金额单位分。金额本身不允许负数，流向由 `direction` 表达。Schema 层 `Field(ge=0)`，ORM 列注释注明，数据库层暂不添加 `CHECK` 约束 |
| currency | `str` | `CNY` | — | |
| direction | `str` | — | `Literal` | `outflow` / `inflow` |
| department | `str?` | `null` | — | 部门 |
| person | `str?` | `null` | — | 人员 |
| counterparty | `str?` | `null` | — | 对手方 / 商户 / 收款方 |
| description | `str` | `''` | 最大 1000 字符，超限截断 | 标准化后的统一描述。此为衍生字段而非原始内容，可截断。Schema `field_validator` 中超过 1000 时截断到 1000，记录警告日志 |
| normalization_status | `str` | `draft` | `Literal` | 见枚举值域表 |
| created_at | `datetime` | `func.now()` | — | |
| updated_at | `datetime` | `func.now()` | `onupdate` | |

**职责**：统计口径的基础表，保存尽量确定的事实字段。**不负责表达"办公用品""差旅费"这类可变分类**——那是 `ClassificationResult` 的职责。

---

## RecordLink（原始记录与标准化记录关联）

支持"一条记录拆成多条""多条记录归并成一条"。

| 字段 | 类型 | 默认值 | 约束 | 说明 |
|:-----|:-----|:------:|:-----|:-----|
| id | `int` PK | 自增 | — | 自增主键 |
| source_record_id | `int` FK | — | `NOT NULL` | → source_record |
| normalized_record_id | `int` FK | — | `NOT NULL` | → normalized_record |
| relation_type | `str` | `primary` | `Literal` | 见枚举值域表 |
| created_at | `datetime` | `func.now()` | — | |

**时序注意**：RecordLink 是关联表，必须等 SourceRecord 和 NormalizedRecord 两端都持久化后才能创建。

---

## ClassificationResult（分类结果）

主干第三层。分类是对标准化记录的解释，不是原始事实本身。

| 字段 | 类型 | 默认值 | 约束 | 说明 |
|:-----|:-----|:------:|:-----|:-----|
| id | `int` PK | 自增 | — | 自增主键 |
| normalized_record_id | `int` FK | — | `NOT NULL` | → normalized_record |
| taxonomy | `str` | `expense_type` | `Literal` | 见枚举值域表 |
| category | `str` | — | — | 分类值，V1 由硬编码 Taxonomy 校验 |
| tags | `json` | `null` | — | 扩展标签 |
| classifier_kind | `str` | — | `Literal` | 见枚举值域表 |
| confidence | `float?` | `null` | — | 置信度 |
| model_version | `str?` | `null` | — | 模型或规则版本 |
| review_status | `str` | `candidate` | `Literal` | 见枚举值域表 |
| is_active | `bool` | `true` | — | 当前是否生效 |
| created_at | `datetime` | `func.now()` | — | |
| updated_at | `datetime` | `func.now()` | `onupdate` | |

说明：

- 同一条 `NormalizedRecord` 可以有多条分类结果
- 可以同时保留 AI 分类、规则分类和人工修订记录
- 统计默认读取 `is_active = true` 且 `review_status = accepted` 的结果

---

## Journal / JournalEntry / JournalEntryLine（可选下游）

凭证层保留，但不再是主干第一优先级。只在需要对接会计系统、生成凭证、做借贷分录时启用。

| 实体 | 调整说明 |
|------|---------|
| Journal | 日记账，保留原有字段 |
| JournalEntry | 可选新增 `normalized_record_id` |
| JournalEntryLine | 金额继续使用分 |

---

## 测试数据库策略

M0/M1 阶段统一使用**文件型 SQLite + Alembic 迁移验收**。

```python
# conftest.py — 基础夹具
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from alembic.config import Config
from alembic import command

TEST_DB_PATH = "sqlite:///./data/test.db"

@pytest.fixture(scope="session")
def engine():
    eng = create_engine(TEST_DB_PATH, connect_args={"check_same_thread": False})
    # 通过 Alembic 迁移建表，而非 metadata.create_all
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")
    yield eng
    eng.dispose()


@pytest.fixture
def session(engine):
    SessionLocal = sessionmaker(bind=engine)
    sess = SessionLocal()
    try:
        yield sess
    finally:
        sess.rollback()
        sess.close()
```

**不使用的方案**：
- **`:memory:` + `StaticPool`** — 连接关闭后 schema 丢失，FK 约束测试不可靠
- **PostgreSQL 方言** — M1 不做方言差异测试
