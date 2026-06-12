# 人力资源模块 — 零基础使用教程

本教程教你从零开始搭建一套招聘管道管理系统：接收简历邮件 → AI 自动分类 → 人工确认 → 进入招聘看板追踪。

## 目录

1. [系统概览](#1-系统概览)
2. [环境准备](#2-环境准备)
3. [启动 Provider（数据后端）](#3-启动-provider数据后端)
4. [安装 CLI 命令行工具](#4-安装-cli-命令行工具)
5. [连接飞书邮箱](#5-连接飞书邮箱)
6. [配置 AI 智能分类](#6-配置-ai-智能分类)
7. [完整使用教程](#7-完整使用教程)
8. [打包项目](#8-打包项目)
9. [常见问题](#9-常见问题)

---

## 1. 系统概览

整个系统由 3 个部分组成：

```
飞书邮箱 ──→ CLI（拉取邮件+分类）──→ Provider API（数据+AI）──→ 看板页面
                  ↑                          │
                  └───── 定时轮询发件箱 ──────┘
```

| 组件 | 作用 | 端口 |
|------|------|------|
| **Provider** | 数据后端，存数据库、提供 API、AI 分类 | 8080 |
| **CLI** | 命令行工具，拉取飞书邮件、推送分类结果 | — |
| **看板页面** | Web 界面，管理候选人管道 | 8000 |

---

## 2. 环境准备

### 2.1 安装 Python 3.10+

```bash
python3 --version
```

如果低于 3.10，请到 [python.org](https://python.org) 下载安装。

### 2.2 安装 Node.js（飞书集成需要）

```bash
node --version
npm --version
```

如果未安装，到 [nodejs.org](https://nodejs.org) 下载 LTS 版本。

### 2.3 获取项目代码

```bash
# 克隆项目（如果还没有）
git clone <项目仓库地址> qtadmin
cd qtadmin
```

> 如果已有项目代码，直接进入项目目录即可。

### 2.4 目录结构

```
qtadmin/
├── src/provider/          # Provider API（数据后端）
├── src/cli/               # CLI 命令行工具
├── examples/human/        # Demo 演示（带 Web 页面）
├── docs/user-guide/       # 本文档
└── manifests/             # systemd 服务配置（生产用）
```

---

## 3. 启动 Provider（数据后端）

Provider 是所有数据的总源头，必须第一个启动。

### 3.1 创建虚拟环境并安装

```bash
cd src/provider

# 创建虚拟环境（仅首次）
python3 -m venv .venv

# 安装依赖
.venv/bin/pip install -e .
```

### 3.2 启动服务

```bash
.venv/bin/uvicorn app.__main__:app --host 0.0.0.0 --port 8080
```

看到以下输出即成功：

```
INFO:     Started server process [12345]
INFO:     Uvicorn running on http://0.0.0.0:8080
```

首次启动会自动创建 `hr.db` 数据库文件并写入 40 条示例数据。

### 3.3 验证

```bash
# 新开一个终端，检查服务是否正常
curl http://127.0.0.1:8080/health
# 返回 {"status":"ok"} 即正常

# 查看管道数据
curl http://127.0.0.1:8080/pipeline
```

> Provider 启动后不要关闭终端，后续所有操作都在新终端中进行。

---

## 4. 安装 CLI 命令行工具

### 4.1 创建虚拟环境并安装

```bash
# 新开一个终端
cd qtadmin/src/cli

# 创建虚拟环境
python3 -m venv .venv

# 安装
.venv/bin/pip install -e .
```

### 4.2 验证安装

```bash
.venv/bin/qtadmin --help
```

看到帮助信息即安装成功。

### 4.3 配置 Provider 地址

告诉 CLI 你的 Provider 运行在哪里：

```bash
.venv/bin/qtadmin human config set-provider http://127.0.0.1:8080

# 查看配置
.venv/bin/qtadmin human config show
```

输出应类似：

```
当前配置：
  provider_url: http://127.0.0.1:8080
  lark_path: lark-cli
```

---

## 5. 连接飞书邮箱

连接飞书邮箱后，系统可以自动拉取招聘邮箱中的简历邮件。

### 5.1 安装 lark-cli

```bash
# 全局安装飞书命令行工具
npm install -g @larksuite/cli

# 验证安装
lark-cli --version
```

### 5.2 登录飞书

```bash
lark login
```

浏览器会自动打开飞书登录页面，扫码登录即可。

> 如果浏览器没有自动打开，复制终端显示的链接手动打开。

### 5.3 验证登录

```bash
# 查看邮箱列表，确认你能访问目标邮箱
lark-cli mail user_mailboxes profile --params '{"user_mailbox_id":"你的邮箱@example.com"}'
```

### 5.4 配置 CLI 使用 lark-cli

```bash
.venv/bin/qtadmin human config set-lark-path $(which lark-cli)
```

### 5.5 测试邮件拉取

```bash
# 列出收件箱最近 5 封邮件
.venv/bin/qtadmin human list -n 5
```

如果能列出邮件，说明飞书集成成功。

---

## 6. 配置 AI 智能分类

AI 分类器可以自动判断一封邮件是简历、笔试、面试还是 Offer，并提取候选人姓名。

### 6.1 准备工作

你需要一个 **OpenAI 兼容的 API 密钥**。支持：
- OpenAI：`sk-...`（需科学上网）
- 国内替代：DeepSeek、智谱、通义千问等（无需科学上网）

### 6.2 通过 API 配置（推荐）

```bash
# 启用 AI 并设置密钥（以 DeepSeek 为例）
curl -X PATCH http://127.0.0.1:8080/ai/config \
  -H "Content-Type: application/json" \
  -d '{
    "enabled": true,
    "provider": "openai",
    "base_url": "https://api.deepseek.com/v1",
    "api_key": "sk-你的密钥",
    "model": "deepseek-chat"
  }'
```

国内常用 AI 服务：

| 服务商 | base_url | model |
|--------|----------|-------|
| DeepSeek | `https://api.deepseek.com/v1` | `deepseek-chat` |
| 智谱 | `https://open.bigmodel.cn/api/paas/v4` | `glm-4-flash` |
| 通义千问 | `https://dashscope.aliyuncs.com/compatible-mode/v1` | `qwen-turbo` |
| OpenAI | `https://api.openai.com/v1` | `gpt-4o-mini` |

### 6.3 测试 AI 配置

```bash
curl -X POST http://127.0.0.1:8080/ai/test
```

返回 `{"status":"ok","message":"连接成功"}` 即配置正确。

### 6.4 在 Web 页面配置

打开 http://127.0.0.1:8000/ → 点击右侧 **⚙️ AI 配置** → 填入：
1. 勾选"启用 AI 分类"
2. 填入 API 地址（如 `https://api.deepseek.com/v1`）
3. 填入 API 密钥
4. 填入模型名（如 `deepseek-chat`）
5. 点击保存

---

## 7. 完整使用教程

### 7.1 启动看板页面

```bash
# 新开一个终端
cd qtadmin

# 启动 Demo（使用 Provider 的虚拟环境）
QTADMIN_MAILBOX=你的邮箱@example.com \
  PYTHONPATH=src/provider \
  src/provider/.venv/bin/python examples/human/demo.py
```

> 设置 `QTADMIN_MAILBOX` 后，系统会自动轮询该邮箱。

打开浏览器访问 **http://127.0.0.1:8000/**。

### 7.2 每日工作流程

#### 步骤 1：拉取邮件并分类

```bash
# 查看收件箱有哪些邮件
.venv/bin/qtadmin human list -n 20

# 预览某封邮件的分类结果
.venv/bin/qtadmin human classify <邮件ID>
```

#### 步骤 2：推送到确认队列

```bash
# 推送所有未处理邮件到待确认队列
.venv/bin/qtadmin human ingest
```

#### 步骤 3：在 Web 页面确认

打开 http://127.0.0.1:8000/ → 点击 **待确认队列**：
- 查看邮件内容、附件、AI 分类结果
- 点击 **确认入队** → 候选人自动进入管道
- 点击 **忽略** → 丢弃该邮件

#### 步骤 4：管理招聘管道

管道看板将候选人按 8 个阶段排列：

```
新进 → 已联系 → 已发卷 → 已收卷 → 评卷中 → 面试 → 发Offer → 关闭
```

操作：
- **拖拽** 候选人卡片到下一阶段
- **点击候选人** 查看详情、时间线、消息记录
- **查看附件** — PDF 直接预览，Word 文档自动转 PDF 在线预览

#### 步骤 5：查看队列状态

```bash
# 查看待确认队列统计
.venv/bin/qtadmin human status
```

### 7.3 自动轮询模式

系统支持两种自动模式：

**邮件拉取轮询**（在 Provider 或 Demo 中）：
- 设置 `QTADMIN_MAILBOX` 环境变量后自动启用
- 每 5 分钟检查一次新邮件
- 新邮件自动推送至 `/ingest` 端点

**发件箱轮询**（邮件发送守护进程）：
```bash
# 启动邮件发送循环（每 30 秒检查一次）
.venv/bin/qtadmin human send-loop -i 30
```

---

## 8. 打包项目

### 8.1 打包 CLI 工具

```bash
cd src/cli

# 构建可分发的 wheel 包
.venv/bin/pip install build
.venv/bin/python -m build

# 生成的包在 dist/ 目录
ls dist/
# qtadmin_cli-0.0.1-py3-none-any.whl

# 安装到其他环境
pip install dist/qtadmin_cli-0.0.1-py3-none-any.whl
```

### 8.2 打包 Provider

```bash
cd src/provider

# 安装 build 工具
.venv/bin/pip install build
.venv/bin/python -m build

# 查看生成的包
ls dist/
# qtadmin_provider-0.1.0-py3-none-any.whl
```

### 8.3 打包完整项目（含依赖）

创建一个 requirements.txt 包含所有依赖：

```bash
cd src/provider
.venv/bin/pip freeze > requirements.txt

# 这样部署时只需：
# python3 -m venv .venv
# .venv/bin/pip install -r requirements.txt
# .venv/bin/pip install dist/qtadmin_provider-0.1.0-py3-none-any.whl
```

### 8.4 配置开机自启（生产环境）

```bash
# 复制服务配置
cp manifests/qtadmin-provider.service ~/.config/systemd/user/
cp manifests/qtadmin-mail-sender.service ~/.config/systemd/user/

# 重新加载 systemd
systemctl --user daemon-reload

# 启动服务
systemctl --user start qtadmin-provider
systemctl --user start qtadmin-mail-sender

# 设置开机自启
systemctl --user enable qtadmin-provider
systemctl --user enable qtadmin-mail-sender
```

---

## 9. 常见问题

### Q：端口被占用怎么办？

```bash
# 查看谁在用端口
ss -tlnp | grep 8080

# 杀掉进程
kill -9 <PID>
```

### Q：lark-cli 找不到命令？

确保 Node.js 全局 bin 目录在 PATH 中：

```bash
# 查看 npm 全局安装路径
npm config get prefix
# 例如输出 /home/你的用户名/.npm-global

# 将 bin 目录加入 PATH
export PATH=$PATH:/home/你的用户名/.npm-global/bin

# 永久生效（加到 ~/.bashrc）
echo 'export PATH=$PATH:/home/你的用户名/.npm-global/bin' >> ~/.bashrc
```

### Q：数据库被锁定？

```bash
# 删除数据库后重启 Provider（数据会重新初始化）
rm src/provider/hr.db
```

### Q：AI 分类没生效？

1. 确认 Provider 正在运行
2. 调用 `GET /ai/config` 检查 `enabled` 是否为 `true`
3. 调用 `POST /ai/test` 测试连接
4. 检查 API 密钥是否正确

### Q：如何重置所有数据？

```bash
# 停止 Provider
# 删除数据库
rm src/provider/hr.db
# 重启 Provider（自动重新生成种子数据）
```

### Q：飞书邮件收不到？

1. 确认 `lark login` 已成功登录
2. 确认邮箱地址正确：`lark-cli mail user_mailboxes profile --params '{"user_mailbox_id":"你的邮箱"}'`
3. 确认收件箱中有邮件：`lark-cli mail +triage --format json --max 5 --mailbox 你的邮箱`
4. 检查 Provider 是否设置了 `QTADMIN_MAILBOX` 环境变量
