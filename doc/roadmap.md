# 开发计划

## Dart 包同步策略

**短期内策略已确定**：在 FastAPI 主干模型稳定前，Dart 包保持凭证层模型，并完成数据类型迁移。后续再决定是否扩展为共享 DTO。

具体行动项：

- `id` 从 `String` 改为 `int`
- `amount` 从 `double` 改为 `int`
- 金额单位统一为"分"
- `JournalEntry` 可选新增 `normalizedRecordId`

---

## 开发步骤

1. 新建 `packages/fastapi/` 目录骨架和 `database.py`
2. 实现 `SourceRecord`、`NormalizedRecord`、`RecordLink`、`ClassificationResult`
3. 实现标准化服务 `services/normalization.py`（Normalizer 接口 + 注册 + 首批实现）
4. 实现分类服务 `services/classification.py`（含 V1 硬编码 Taxonomy 校验）
5. 实现统计服务 `services/statistics.py`
6. 提供原始记录、标准化、分类、统计四类核心路由
7. 最后再补凭证生成 `services/posting.py`
8. 同步更新 Dart 包的数据类型和可选关联字段

---

## 待处理事项

| 优先级 | 事项 | 说明 |
|---|---|---|
| 🟡 高 | 脱敏粒度细化 | V1 使用统一 `[AMOUNT]`；下一步尽快支持 `[AMOUNT:SMALL]` / `[AMOUNT:LARGE]`，保留量级信息辅助 AI 分类 |
| 🟡 中 | 置信度阈值校准流程 | 上线后基于实际数据分布的校准 SOP |
| 🟢 低 | 速率限制与成本控制 | 外部 API 每分钟/每小时最大调用次数、超时时间、降级策略 |
| 🟢 低 | 附件存储设计 | `evidence_refs` 指向的对象存储方案 |
| 🟢 低 | 导入格式规范 | CSV/银行流水等常见格式的导入模板 |
| 🟢 低 | 审计日志保留策略 | 外部 API 调用日志的留存时间与清理机制 |
