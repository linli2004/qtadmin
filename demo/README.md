# M4 统计演示 — 财务部体验版

基于《QuantTide Finance Toolkit》统计 API 的前端演示，供财务部体验统计功能。

## 快速启动

保证当前在项目根目录 `quanttide-finance-toolkit/`。

### 第一步：填充演示数据

```bash
python3 demo/seed.py --reset
```

脚本会在 `demo/demo.db` 创建独立数据库（**不会碰** `packages/fastapi/data/quanttide_finance.db`）。

终端会打印数据摘要：

```
Created 52 SourceRecords
Created 52 NormalizedRecords + 52 RecordLinks
Created 44 classifications (33 accepted, 11 candidates)

=== Demo Data Summary ===
Total records: 52
Sum amount_cents: 7,405,348 (¥74,053.48)
Records with accepted classification: 35
Classification rate: 67%
```

### 第二步：启动后端

```bash
cd packages/fastapi
source .venv/bin/activate
DEMO_DB=../demo/demo.db uvicorn fastapi_quanttide_finance.app:app --reload
```

终端显示 `Uvicorn running on http://127.0.0.1:8000` 即启动成功。

> `DEMO_DB` 环境变量让后端读取独立 demo 数据库。不设此变量时使用默认的开发库路径。

### 第三步：打开演示页面

用浏览器打开 `demo/index.html`：

```bash
open demo/index.html        # macOS
xdg-open demo/index.html    # Linux
start demo/index.html       # Windows
```

## 功能说明

| 区域 | 内容 |
|------|------|
| 过滤栏 | 日期区间、部门、记录类型、流向、分类筛选，点"查询"刷新 |
| 汇总卡片 | 记录总数、金额合计、已分类数、平均金额 |
| 部门分布 | 柱状图展示各部门记录数 |
| 月度趋势 | 折线图展示金额和记录数的月度变化 |
| 明细表格 | 逐条查看原始记录，支持翻页 |

## 数据说明

演示数据为**随机生成的模拟数据**，包含：

- **时间范围**：2026 年 6 月 — 8 月
- **部门**：6 个部门（研发部、市场部、行政部、财务部、销售部、采购部）
- **分类**：办公用品、差旅、采购、工资、其他
- **约 2/3 的记录**已有已审核的分类
- **独立数据库**：`demo/demo.db`，与开发库隔离，`--reset` 只会删除 demo 库

## 停止 / 重置

| 操作 | 命令 |
|------|------|
| 停止后端 | 按 `Ctrl+C` |
| 重置数据 | `python3 demo/seed.py --reset`，然后重启 uvicorn |
| 彻底删除 | `rm demo/demo.db` |

## 常见问题

**页面提示"请求失败 — 请确认后端已启动"**

→ 确认 uvicorn 正在运行，访问 http://localhost:8000/health 应返回 `{"status":"ok"}`。
→ 如果忘记设 `DEMO_DB`，后端读的是空开发库，数据会显示 0。
