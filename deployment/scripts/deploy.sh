#!/bin/bash
# AI Safety Lab - 一键部署脚本
# 用途: 在UNICC AI沙盒中部署AI Safety Lab

set -e

# 配置变量
PROJECT_NAME="ai-safety-lab"
NAMESPACE="unicc-aisafety"
DOCKER_REGISTRY="unicc-registry.local"
VERSION=${VERSION:-"latest"}

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查依赖
check_dependencies() {
    log_info "检查部署依赖..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker未安装或不在PATH中"
        exit 1
    fi
    
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl未安装或不在PATH中"
        exit 1
    fi
    
    # 检查Docker守护进程
    if ! docker info &> /dev/null; then
        log_error "Docker守护进程未运行"
        exit 1
    fi
    
    # 检查Kubernetes连接
    if ! kubectl cluster-info &> /dev/null; then
        log_error "无法连接到Kubernetes集群"
        exit 1
    fi
    
    log_success "所有依赖检查通过"
}

# 构建Docker镜像
build_image() {
    log_info "构建Docker镜像..."
    
    cd "$(dirname "$0")/../.."
    
    # 构建镜像
    docker build -f deployment/docker/Dockerfile.production \
        -t ${DOCKER_REGISTRY}/${PROJECT_NAME}:${VERSION} \
        -t ${DOCKER_REGISTRY}/${PROJECT_NAME}:latest \
        .
    
    log_success "Docker镜像构建完成"
}

# 推送镜像到注册表
push_image() {
    log_info "推送镜像到注册表..."
    
    # 登录到Docker注册表（如果需要）
    # docker login ${DOCKER_REGISTRY}
    
    docker push ${DOCKER_REGISTRY}/${PROJECT_NAME}:${VERSION}
    docker push ${DOCKER_REGISTRY}/${PROJECT_NAME}:latest
    
    log_success "镜像推送完成"
}

# 创建命名空间
create_namespace() {
    log_info "创建Kubernetes命名空间..."
    
    kubectl create namespace ${NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -
    
    # 添加标签
    kubectl label namespace ${NAMESPACE} \
        name=${NAMESPACE} \
        environment=production \
        project=${PROJECT_NAME} \
        --overwrite
    
    log_success "命名空间创建完成"
}

# 部署密钥
deploy_secrets() {
    log_info "部署应用密钥..."
    
    # 创建TLS密钥（示例）
    kubectl create secret tls ai-safety-tls \
        --cert=deployment/config/ssl/tls.crt \
        --key=deployment/config/ssl/tls.key \
        --namespace=${NAMESPACE} \
        --dry-run=client -o yaml | kubectl apply -f -
    
    # 创建应用密钥
    kubectl create secret generic ai-safety-secrets \
        --from-env-file=deployment/config/production.env \
        --namespace=${NAMESPACE} \
        --dry-run=client -o yaml | kubectl apply -f -
    
    log_success "密钥部署完成"
}

# 部署应用
deploy_application() {
    log_info "部署应用到Kubernetes..."
    
    # 更新镜像版本
    sed -i "s|unicc/ai-safety-lab:latest|${DOCKER_REGISTRY}/${PROJECT_NAME}:${VERSION}|g" \
        deployment/kubernetes/deployment.yaml
    
    # 应用Kubernetes配置
    kubectl apply -f deployment/kubernetes/configmap.yaml -n ${NAMESPACE}
    kubectl apply -f deployment/kubernetes/deployment.yaml -n ${NAMESPACE}
    kubectl apply -f deployment/kubernetes/service.yaml -n ${NAMESPACE}
    kubectl apply -f deployment/kubernetes/ingress.yaml -n ${NAMESPACE}
    
    log_success "应用部署完成"
}

# 等待部署完成
wait_for_deployment() {
    log_info "等待部署就绪..."
    
    # 等待后端部署
    kubectl rollout status deployment/ai-safety-backend -n ${NAMESPACE} --timeout=300s
    
    # 等待前端部署
    kubectl rollout status deployment/ai-safety-frontend -n ${NAMESPACE} --timeout=300s
    
    log_success "所有服务已就绪"
}

# 健康检查
health_check() {
    log_info "执行健康检查..."
    
    # 获取服务地址
    BACKEND_URL=$(kubectl get service ai-safety-backend-service -n ${NAMESPACE} -o jsonpath='{.spec.clusterIP}')
    
    # 检查后端健康状态
    if kubectl run health-check --rm -i --restart=Never --image=curlimages/curl -- \
        curl -f http://${BACKEND_URL}:8000/api/health; then
        log_success "后端服务健康检查通过"
    else
        log_error "后端服务健康检查失败"
        return 1
    fi
    
    log_success "健康检查完成"
}

# 显示部署信息
show_deployment_info() {
    log_info "部署信息:"
    
    echo "===========================================" 
    echo "AI Safety Lab 部署完成!"
    echo "==========================================="
    echo ""
    echo "命名空间: ${NAMESPACE}"
    echo "镜像版本: ${VERSION}"
    echo ""
    echo "服务状态:"
    kubectl get pods,services -n ${NAMESPACE}
    echo ""
    echo "访问地址:"
    echo "- 内部访问: http://ai-safety-frontend-service:8501"
    echo "- 外部访问: https://aisafety.unicc.local"
    echo ""
    echo "管理命令:"
    echo "- 查看日志: kubectl logs -f deployment/ai-safety-backend -n ${NAMESPACE}"
    echo "- 扩容服务: kubectl scale deployment ai-safety-backend --replicas=3 -n ${NAMESPACE}"
    echo "- 删除部署: kubectl delete namespace ${NAMESPACE}"
    echo "==========================================="
}

# 主函数
main() {
    log_info "开始部署 AI Safety Lab 到 UNICC AI 沙盒"
    
    check_dependencies
    build_image
    push_image
    create_namespace
    deploy_secrets
    deploy_application
    wait_for_deployment
    health_check
    show_deployment_info
    
    log_success "部署完成! 🎉"
}

# 清理函数
cleanup() {
    if [[ "${1:-}" == "clean" ]]; then
        log_warning "清理部署..."
        kubectl delete namespace ${NAMESPACE}
        log_success "清理完成"
        exit 0
    fi
}

# 解析命令行参数
case "${1:-}" in
    "clean")
        cleanup clean
        ;;
    *)
        main
        ;;
esac