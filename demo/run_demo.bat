@echo off
REM 量潮财务工具 — 演示启动脚本 (Windows)
chcp 65001 >nul

set "SCRIPT_DIR=%~dp0"
set "FASTAPI_DIR=%SCRIPT_DIR%..\packages\fastapi"
set "DEMO_DB_PATH=%SCRIPT_DIR%demo.db"

echo === 量潮财务工具 — 演示 ===

REM 1. 准备后端环境
cd /d "%FASTAPI_DIR%"
if not exist ".venv" (
    echo [1/4] 创建虚拟环境...
    python -m venv .venv
)
call .venv\Scripts\activate.bat

echo [2/4] 安装依赖...
pip install -e ".[dev]" -q

REM 2. 初始化演示数据
echo [3/4] 初始化演示数据...
python "%SCRIPT_DIR%seed.py" --reset

REM 3. 启动服务（设置 DEMO_DB 让服务器读取 demo 独立数据库）
echo [4/4] 启动 API 服务...
set "DEMO_DB=%DEMO_DB_PATH%"
start "quanttide-demo" /B uvicorn fastapi_quanttide_finance.app:app --host 0.0.0.0 --port 8000

REM 等待服务就绪
echo 等待服务启动...
timeout /t 5 /nobreak >nul

echo.
echo === 启动成功 ===
echo API 服务: http://localhost:8000
echo 演示页面: %SCRIPT_DIR%index.html
echo.
start "" "%SCRIPT_DIR%index.html"
pause
