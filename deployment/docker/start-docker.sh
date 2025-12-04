#!/bin/bash
# AI Safety Lab - Docker 快速启动脚本
# 适用于Windows环境

echo "🚀 AI Safety Lab Docker 快速启动"
echo "=================================="

# 检查Docker是否运行
echo "检查Docker状态..."
if ! docker info >/dev/null 2>&1; then
    echo "❌ Docker未运行，请启动Docker Desktop"
    echo "💡 启动Docker Desktop后重新运行此脚本"
    exit 1
fi

echo "✅ Docker正在运行"

# 进入项目根目录
cd "$(dirname "$0")/../.."

# 构建镜像
echo "🔨 构建Docker镜像..."
docker build -f deployment/docker/Dockerfile.production -t ai-safety-lab:latest .

if [ $? -ne 0 ]; then
    echo "❌ 镜像构建失败"
    exit 1
fi

echo "✅ 镜像构建成功"

# 创建必要的目录
mkdir -p runs reports logs

# 停止已存在的容器
echo "🛑 停止旧容器..."
docker stop ai-safety-lab-container 2>/dev/null || true
docker rm ai-safety-lab-container 2>/dev/null || true

# 启动容器
echo "🚀 启动AI Safety Lab容器..."
docker run -d \
    --name ai-safety-lab-container \
    -p 8000:8000 \
    -p 8501:8501 \
    -v "$(pwd)/runs:/app/runs" \
    -v "$(pwd)/config:/app/config:ro" \
    -e AI_SAFETY_ENV=development \
    -e PYTHONPATH=/app \
    -e LOG_LEVEL=DEBUG \
    ai-safety-lab:latest \
    sh -c "
        echo 'Starting AI Safety Lab services...'
        # 启动后端服务（后台）
        python start_server.py &
        # 等待后端启动
        sleep 15
        # 启动前端服务
        streamlit run ui/app.py --server.port=8501 --server.address=0.0.0.0
    "

if [ $? -eq 0 ]; then
    echo "✅ 容器启动成功！"
    echo ""
    echo "📱 访问地址:"
    echo "- Web界面: http://localhost:8501"
    echo "- API文档: http://localhost:8000/docs"
    echo "- 健康检查: http://localhost:8000/api/health"
    echo ""
    echo "📋 管理命令:"
    echo "- 查看日志: docker logs -f ai-safety-lab-container"
    echo "- 停止服务: docker stop ai-safety-lab-container"
    echo "- 重启服务: docker restart ai-safety-lab-container"
    echo ""
    echo "⏳ 服务启动中，请等待30秒后访问..."
else
    echo "❌ 容器启动失败"
    exit 1
fi