# 架构设计

## 设计目标

本项目的核心目标不是"先做凭证，再做统计"，而是：

1. 把各种形态的财务相关记录标准化进系统
2. 把标准化结果整理分类
3. 基于标准化字段和分类结果做统计分析

因此主干应该是**数据标准化 + 数据分类 + 数据统计**，而不是会计分录模型。

会计凭证层保留，但降级为可选下游能力。

## 核心流程

```text
原始输入
  图片 / 聊天 / 表单 / CSV / 银行流水 / API / 人工录入
    ↓
SourceRecord
  保留原始证据、原始文本、来源信息、导入状态
    │
    │  ┌─ RecordLink（关联表，两端记录存在后创建）
    │  │
    ↓  ↓
NormalizedRecord
  抽取并统一成标准字段，作为统计基线
    │
    ├──→ Statistics（基于标准字段汇总、分组、趋势、钻取）
    │        ↑
    └──→ ClassificationResult（AI/规则/人工分类，作为叠加维度，可选）

可选下游
NormalizedRecord
    ↓
Journal（日记账）→ JournalEntry（凭证）→ JournalEntryLine（分录行）
```

## 包结构

```text
packages/
├── dart/                   ← 已有，当前主要是凭证层 freezed 模型
│   └── lib/src/models/
│       ├── journal.dart
│       └── journal_entry.dart
│
├── fastapi/                ← 新建，承担主干服务
│   ├── pyproject.toml
│   ├── src/
│   │   └── fastapi_quanttide_finance/
│   │       ├── __init__.py
│   │       ├── database.py
│   │       ├── models/
│   │       │   ├── __init__.py
│   │       │   ├── source_record.py
│   │       │   ├── normalized_record.py
│   │       │   ├── classification_result.py
│   │       │   ├── record_link.py
│   │       │   ├── journal.py
│   │       │   └── journal_entry.py
│   │       ├── schemas/
│   │       │   ├── __init__.py
│   │       │   ├── source_record.py
│   │       │   ├── normalized_record.py
│   │       │   ├── classification_result.py
│   │       │   ├── statistics.py
│   │       │   └── journal_entry.py
│   │       ├── services/
│   │       │   ├── __init__.py
│   │       │   ├── normalization.py
│   │       │   ├── classification.py
│   │       │   ├── statistics.py
│   │       │   └── posting.py
│   │       └── routers/
│   │           ├── __init__.py
│   │           ├── source_records.py
│   │           ├── normalized_records.py
│   │           ├── classifications.py
│   │           ├── statistics.py
│   │           └── postings.py
│   ├── tests/
│   │   └── test_api.py
│   └── examples/
│       └── provider/
│           ├── pyproject.toml
│           └── app.py
```

## 分层架构

```text
┌──────────────┐  Routers（HTTP 端点）
│   Routers    │
├──────────────┤  Services（标准化、分类、统计、凭证生成）
│  Services    │
├──────────────┤  Schemas（Pydantic 请求/响应模型）
│   Schemas    │
├──────────────┤  Models（SQLAlchemy ORM）
│   Models     │
└──────────────┘
```

## 实体关系

```text
SourceRecord
    └── RecordLink ──→ NormalizedRecord ──→ ClassificationResult
         (快捷: primary_source_id)    │
                                     └── JournalEntry ──→ JournalEntryLine
```

关系说明：

- 一条 `SourceRecord` 可以参与多条 `NormalizedRecord`
- 一条 `NormalizedRecord` 也可以由多条 `SourceRecord` 合并而来
- 一条 `NormalizedRecord` 可以拥有多条分类结果
- 一条 `NormalizedRecord` 可以不生成任何凭证
