@echo off
REM AI Safety Lab - 本地开发启动脚本

echo 🚀 启动 AI Safety Lab 开发环境...
echo ================================

cd /d "%~dp0"

REM 激活虚拟环境
call .venv\Scripts\activate.bat

REM 启动后端服务（后台）
echo 📡 启动 FastAPI 后端服务...
start /b python -m uvicorn server.api:app --host 127.0.0.1 --port 8000 --reload

REM 等待后端启动
timeout /t 3 /nobreak > nul

REM 启动前端服务
echo 🌐 启动 Streamlit 前端界面...
streamlit run ui/app.py --server.port=8501 --server.address=127.0.0.1

pause