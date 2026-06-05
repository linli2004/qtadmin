# 人力资源职能

## 概述

处理招聘邮箱中的简历邮件：自动分类 → 待确认队列 → HR 确认后进入招聘看板。

### 架构

```
飞书邮箱 → lark-cli → qtadmin human ingest → 服务端 API → 待确认队列 → 看板
                                  ↑                              ↓
                              分类器                        HR 确认/调整
```

- **CLI 端** (`qtadmin human`)：连接飞书邮箱读取邮件，自动分类后推送到服务端
- **服务端** (`qtadmin-api`)：管理待确认队列、招聘看板（8 阶段状态机）、人才库
- **客户端** (`src/studio/`)：管理后台 Web 界面（开发中）

### 招聘流程（8 阶段）

```
新进 → 已联系 → 已发卷 → 已收卷 → 评卷中 → 面试 → 发Offer → 关闭
```

所有阶段均可直接关闭。评卷中阶段可回退到已发卷。

## 前置要求

- Python >= 3.10
- （生产模式）飞书开放平台账号 + lark-cli：`npm install -g @larksuite/cli`

## 安装

### 1. 启动服务端

```bash
cd src/provider

# 创建虚拟环境（如未创建）
python3 -m venv .venv

# 安装
.venv/bin/pip install -e .

# 启动（默认 http://127.0.0.1:8000）
.venv/bin/python -m app
```

首次启动会自动创建 SQLite 数据库并写入演示数据（42 条候选记录 + 10 条待确认队列记录）。

### 2. 安装 CLI

```bash
cd src/cli

# 创建虚拟环境
python3 -m venv .venv

# 安装
.venv/bin/pip install -e .

# 配置服务端地址
.venv/bin/qtadmin human config set-provider http://127.0.0.1:8000
```

### 3.（可选）配置飞书

```bash
# 安装 lark-cli
npm install -g @larksuite/cli

# 登录飞书
lark login

# 配置 lark-cli 路径
qtadmin human config set-lark-path /path/to/lark-cli
```

## 快速开始（演示模式）

服务端启动后自带演示数据，无需连接飞书即可体验：

1. 查看当前演示候选人管道：`curl http://127.0.0.1:8000/pipeline`
2. 查看待确认队列：`curl http://127.0.0.1:8000/queue`
3. 通过 CLI 查看队列状态：`qtadmin human status`

## 命令参考

### 配置管理

```bash
# 设置服务端地址
qtadmin human config set-provider http://127.0.0.1:8000

# 设置 lark-cli 路径
qtadmin human config set-lark-path /usr/local/bin/lark-cli

# 查看当前配置
qtadmin human config show
```

配置存储在 `~/.config/qtadmin/human.json`。

### 邮件处理

```bash
# 查看收件箱邮件（最近 10 封）
qtadmin human list -n 10

# 预览单封邮件分类
qtadmin human classify <邮件ID>

# 预览推送内容（不实际推送）
qtadmin human ingest --dry-run

# 推送到服务端待确认队列
qtadmin human ingest

# 查看队列状态
qtadmin human status
```

### API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |
| GET | `/pipeline` | 招聘看板（按阶段分组） |
| GET | `/queue` | 待确认队列列表 |
| PATCH | `/queue/{id}/confirm` | 确认入队（创建候选人+申请） |
| PATCH | `/queue/{id}/ignore` | 忽略入队 |
| GET | `/queue/stats` | 队列统计 |
| POST | `/ingest` | 推送分类结果到队列 |
| GET | `/recruitments` | 招聘批次列表 |
| POST | `/recruitments` | 创建招聘批次 |
| GET | `/recruitments/{id}/talents` | 批次下的候选人列表 |
| POST | `/recruitments/{id}/talents` | 添加候选人 |
| POST | `/recruitments/{id}/talents/{id}/transition` | 候选人状态转换 |
| GET | `/recruitments/{id}/headcount` | Offer 统计（总数/已接受） |
| GET | `/pool` | 人才库列表 |
| POST | `/applications/{id}/pool` | 入池（关闭申请进人才库） |
| POST | `/applications/{id}/unpool` | 出池（创建新申请） |
| GET | `/candidates` | 候选人列表 |

## 开发

```bash
# 运行测试
cd src/provider && .venv/bin/pip install -e '.[dev]' && .venv/bin/pytest tests/human/ -v

# 查看 API 文档
# 启动服务端后访问 http://127.0.0.1:8000/docs
```

## 排错

| 问题 | 原因 | 解决 |
|------|------|------|
| `qtadmin: command not found` | CLI 未安装或未激活虚拟环境 | 运行 `cd src/cli && .venv/bin/pip install -e .` |
| 连接服务端失败 | 服务端未启动或地址配置错误 | 确认服务端运行中，检查 `config show` |
| `lark-cli` 命令不存在 | 未安装或路径配置错误 | `npm install -g @larksuite/cli` |
| 管道数据为空 | 数据库无数据 | 删除 `hr.db` 重新启动服务端会自动 seed |
