#!/bin/bash
# 量潮财务工具 — 演示启动脚本
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
FASTAPI_DIR="$PROJECT_DIR/packages/fastapi"
DEMO_DB_PATH="$SCRIPT_DIR/demo.db"

echo "=== 量潮财务工具 — 演示 ==="

# 1. 准备后端环境
cd "$FASTAPI_DIR"
if [ ! -d ".venv" ]; then
    echo "[1/4] 创建虚拟环境..."
    python3 -m venv .venv
fi
source .venv/bin/activate

echo "[2/4] 安装依赖..."
pip install -e ".[dev]" -q

# 2. 初始化演示数据（--reset 确保每次重新生成）
echo "[3/4] 初始化演示数据..."
python3 "$SCRIPT_DIR/seed.py" --reset

# 3. 启动服务（设置 DEMO_DB 让服务器读取 demo 独立数据库）
echo "[4/4] 启动 API 服务..."
echo ""
trap "kill $UVICORN_PID 2>/dev/null; echo ''; echo '服务已停止'; exit 0" INT TERM

DEMO_DB="$DEMO_DB_PATH" uvicorn fastapi_quanttide_finance.app:app --host 0.0.0.0 --port 8000 &
UVICORN_PID=$!

# 等待服务就绪
for _ in $(seq 1 15); do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "=== 启动成功 ==="
        echo "API 服务: http://localhost:8000"
        echo "演示页面: file://$SCRIPT_DIR/index.html"
        echo ""
        # 自动打开浏览器
        if command -v xdg-open &> /dev/null; then
            xdg-open "$SCRIPT_DIR/index.html"
        elif command -v open &> /dev/null; then
            open "$SCRIPT_DIR/index.html"
        fi
        echo "服务已启动，按 Ctrl+C 停止"
        wait $UVICORN_PID
        exit 0
    fi
    sleep 1
done

echo "启动失败，手动运行检查错误"
kill $UVICORN_PID 2>/dev/null
exit 1
