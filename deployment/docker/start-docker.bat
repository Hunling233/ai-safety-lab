@echo off
REM AI Safety Lab - Windows Docker 启动脚本

echo 🚀 AI Safety Lab Docker 快速启动
echo ==================================

REM 检查Docker是否运行
echo 检查Docker状态...
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Docker未运行，请启动Docker Desktop
    echo 💡 启动Docker Desktop后重新运行此脚本
    pause
    exit /b 1
)

echo ✅ Docker正在运行

REM 进入项目根目录
cd /d "%~dp0..\.."

REM 构建镜像
echo 🔨 构建Docker镜像...
docker build -f deployment\docker\Dockerfile.production -t ai-safety-lab:latest .

if %errorlevel% neq 0 (
    echo ❌ 镜像构建失败
    pause
    exit /b 1
)

echo ✅ 镜像构建成功

REM 创建必要的目录
if not exist runs mkdir runs
if not exist reports mkdir reports
if not exist logs mkdir logs

REM 停止已存在的容器
echo 🛑 停止旧容器...
docker stop ai-safety-lab-container >nul 2>&1
docker rm ai-safety-lab-container >nul 2>&1

REM 启动容器
echo 🚀 启动AI Safety Lab容器...
docker run -d --name ai-safety-lab-container -p 8000:8000 -p 8501:8501 -v "%cd%\runs:/app/runs" -v "%cd%\config:/app/config:ro" -e AI_SAFETY_ENV=development -e PYTHONPATH=/app -e LOG_LEVEL=DEBUG ai-safety-lab:latest sh -c "echo 'Starting AI Safety Lab services...'; python start_server.py & sleep 15; streamlit run ui/app.py --server.port=8501 --server.address=0.0.0.0"

if %errorlevel% equ 0 (
    echo ✅ 容器启动成功！
    echo.
    echo 📱 访问地址:
    echo - Web界面: http://localhost:8501
    echo - API文档: http://localhost:8000/docs
    echo - 健康检查: http://localhost:8000/api/health
    echo.
    echo 📋 管理命令:
    echo - 查看日志: docker logs -f ai-safety-lab-container
    echo - 停止服务: docker stop ai-safety-lab-container
    echo - 重启服务: docker restart ai-safety-lab-container
    echo.
    echo ⏳ 服务启动中，请等待30秒后访问...
) else (
    echo ❌ 容器启动失败
    pause
    exit /b 1
)

pause