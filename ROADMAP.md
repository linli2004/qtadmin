# QuantTide Finance Toolkit — 路线图

---

## 探索阶段：财务数据标准化主干验证

> 来源：数据架构设计文档（2026-05-30）
> 首选方向：`SourceRecord → NormalizedRecord → Statistics` 主干链路

说明：

- `RecordLink` 是 `SourceRecord` 与 `NormalizedRecord` 之间的关联层，不是线性处理节点；两端记录存在后再创建。
- `ClassificationResult` 是叠加维度，不是事实层；分类结果只存于 `ClassificationResult`，不回写 `NormalizedRecord`。
- 统计主干基于 `NormalizedRecord`，未分类记录也可以进入汇总、趋势和明细查询。
- 当前 `packages/dart` 仍是下游凭证层模型；探索阶段主资源投入 `packages/fastapi` 主干。

### 里程碑

| 里程碑 | 目标日期 | 关键交付物 | 通过标准 |
|:-------|:--------:|:-----------|:---------|
| M1: 核心模型就绪 | 第 14 天 | `SourceRecord`、`NormalizedRecord`、`RecordLink`、`ClassificationResult` 四个 ORM 模型 + Pydantic Schema + 数据库建表 | 模型可通过 Alembic 迁移创建，Pydantic 校验通过 |
| M2: 标准化服务可用 | 第 28 天 | `Normalizer` 接口 + 注册机制 + `CsvRowNormalizer` + `ManualNormalizer` 首批实现 | 单条 CSV 记录导入 → 标准化记录生成 → API 可查询 |
| M3: 分类服务可用 | 第 35 天 | V1 硬编码 Taxonomy + 分类 API + 审核状态流转（`candidate → accepted/rejected`） | 标准化记录可通过 API 添加分类，审核流程走通 |
| M4: 统计主干可用 | 第 42 天 | 汇总 / 分组 / 趋势 / 钻取四类统计 API | 至少支持按 `department` 和 `record_type` 两种维度分组统计 |
| M5: 数据安全落地 | 第 49 天 | 脱敏器 + 外部 API 审计日志 + Taxonomy 输出校验 | 脱敏规则覆盖全部敏感类型，非法分类标签被拦截 |
| M6: Dart 包同步升级 | 第 56 天 | Dart 模型 `id` 改为 `int`，`amount` 改为 `int`（分），`JournalEntry` 新增 `normalizedRecordId` | 现有测试通过，序列化行为不变 |

### 模型验证里程碑

- **标准化效果验证**（M2+7 天）：用至少 3 种不同来源（CSV、手工、银行流水样例）导入数据，统计标准化成功率。通过标准：规则驱动的标准化成功率 ≥ 95%，人工标准化无字段缺失。
- **分类准确度基线**（M3+14 天）：用至少 50 条已人工分类的记录，对比规则 / AI 分类输出，计算准确率。通过标准：V1 硬编码规则分类准确率 ≥ 80%。
- **统计口径验证**（M4+7 天）：人工核对统计 API 输出与原始数据，验证金额汇总、记录计数无误。

### 实施边界

- 所有 `id` 使用 `int`。
- 所有金额使用 `int`，单位为“分”。
- 原始内容保留在 `raw_payload`、`raw_text`、`evidence_refs` 中，不在入库前做不可逆裁剪。
- `NormalizeInput` 在 M2 阶段预留 `existing_normalized_id` 字段，实现延后。即接口支持传入但不强制使用，方便后续支持"追加到已有标准化记录"场景。
- 统计层不做写死的 `by_department`、`by_expense_type` 端点，统一走“维度 + 指标 + 过滤条件”。
- 输入超限后的处理策略必须显式实现为“截断或拒绝”，由应用层决定。

### 高风险变量数据获取计划

| 变量 | 当前状态 | 获取计划 | 预计获取时间 |
|:-----|:--------:|:---------|:-----------:|
| 标准化规则覆盖率 | 未知（CSV / 手工先行） | 每新增一种 `source_type` 记录覆盖比例与失败原因 | M2 起持续跟踪 |
| AI 分类置信度分布 | 未知 | 上线 AI 分类后采集置信度直方图，并按 taxonomy 分层观察 | M3 + AI 分类器接入后 |
| 人工审核工作量 | 未知 | 统计 `candidate → accepted/rejected` 的平均延迟与积压量 | M3 起持续跟踪 |
| 外部 API 调用成本 | 未知 | 审计日志记录每次调用耗时、请求量与费用 | 首次接入外部 AI 起跟踪 |
| 未分类记录占比 | 未知 | 监控进入统计但缺少 `accepted` 分类结果的记录比例 | M4 起持续跟踪 |

### 暂缓项

- 脱敏粒度细化：V1 统一使用 `[AMOUNT]`，后续再细化到 `[AMOUNT:SMALL]` / `[AMOUNT:LARGE]`。
- 置信度阈值校准 SOP。
- 速率限制与成本控制。
- 附件对象存储方案。
- CSV / 银行流水导入模板。
- 审计日志保留与清理策略。

---

*以上为数据架构设计（2026-05-30）输出的探索阶段。后续阶段将在此路线图中逐步追加。*
