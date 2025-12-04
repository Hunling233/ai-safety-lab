#!/bin/bash
# AI Safety Lab - 健康检查脚本
# 用途: 检查服务健康状态和性能指标

set -e

NAMESPACE="unicc-aisafety"
PROJECT_NAME="ai-safety-lab"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

# 检查Pod状态
check_pods() {
    log_info "检查Pod状态..."
    
    # 获取所有Pod状态
    PODS=$(kubectl get pods -n ${NAMESPACE} -o jsonpath='{.items[*].metadata.name}')
    
    for pod in $PODS; do
        STATUS=$(kubectl get pod $pod -n ${NAMESPACE} -o jsonpath='{.status.phase}')
        if [[ "$STATUS" == "Running" ]]; then
            log_success "Pod $pod: $STATUS"
        else
            log_error "Pod $pod: $STATUS"
            return 1
        fi
    done
}

# 检查服务可达性
check_services() {
    log_info "检查服务可达性..."
    
    # 检查后端服务
    BACKEND_IP=$(kubectl get service ai-safety-backend-service -n ${NAMESPACE} -o jsonpath='{.spec.clusterIP}')
    if kubectl run health-test --rm -i --restart=Never --image=curlimages/curl -- \
        curl -f -m 10 http://${BACKEND_IP}:8000/api/health; then
        log_success "后端服务可达"
    else
        log_error "后端服务不可达"
        return 1
    fi
    
    # 检查前端服务
    FRONTEND_IP=$(kubectl get service ai-safety-frontend-service -n ${NAMESPACE} -o jsonpath='{.spec.clusterIP}')
    if kubectl run frontend-test --rm -i --restart=Never --image=curlimages/curl -- \
        curl -f -m 10 http://${FRONTEND_IP}:8501; then
        log_success "前端服务可达"
    else
        log_error "前端服务不可达"
        return 1
    fi
}

# 检查资源使用情况
check_resources() {
    log_info "检查资源使用情况..."
    
    # CPU和内存使用情况
    kubectl top pods -n ${NAMESPACE} || log_warning "无法获取资源使用情况（需要metrics-server）"
    
    # 存储使用情况
    log_info "存储卷状态:"
    kubectl get pv,pvc -n ${NAMESPACE}
}

# 检查日志错误
check_logs() {
    log_info "检查最近的错误日志..."
    
    # 检查后端错误
    BACKEND_ERRORS=$(kubectl logs -n ${NAMESPACE} deployment/ai-safety-backend --tail=100 | grep -i error | wc -l)
    if [[ $BACKEND_ERRORS -gt 0 ]]; then
        log_warning "后端发现 $BACKEND_ERRORS 个错误"
        kubectl logs -n ${NAMESPACE} deployment/ai-safety-backend --tail=10 | grep -i error
    else
        log_success "后端无错误日志"
    fi
    
    # 检查前端错误
    FRONTEND_ERRORS=$(kubectl logs -n ${NAMESPACE} deployment/ai-safety-frontend --tail=100 | grep -i error | wc -l)
    if [[ $FRONTEND_ERRORS -gt 0 ]]; then
        log_warning "前端发现 $FRONTEND_ERRORS 个错误"
        kubectl logs -n ${NAMESPACE} deployment/ai-safety-frontend --tail=10 | grep -i error
    else
        log_success "前端无错误日志"
    fi
}

# 性能测试
performance_test() {
    log_info "执行性能测试..."
    
    BACKEND_IP=$(kubectl get service ai-safety-backend-service -n ${NAMESPACE} -o jsonpath='{.spec.clusterIP}')
    
    # API响应时间测试
    RESPONSE_TIME=$(kubectl run perf-test --rm -i --restart=Never --image=curlimages/curl -- \
        curl -w "%{time_total}" -s -o /dev/null http://${BACKEND_IP}:8000/api/health)
    
    if (( $(echo "$RESPONSE_TIME < 1.0" | bc -l) )); then
        log_success "API响应时间: ${RESPONSE_TIME}s (正常)"
    else
        log_warning "API响应时间: ${RESPONSE_TIME}s (较慢)"
    fi
}

# 生成健康报告
generate_report() {
    local timestamp=$(date "+%Y-%m-%d %H:%M:%S")
    local report_file="/tmp/aisafety-health-${timestamp//[: -]/}.txt"
    
    log_info "生成健康检查报告..."
    
    cat > $report_file << EOF
AI Safety Lab 健康检查报告
生成时间: $timestamp
命名空间: $NAMESPACE

==========================================
Pod 状态:
$(kubectl get pods -n ${NAMESPACE})

服务状态:
$(kubectl get services -n ${NAMESPACE})

资源使用:
$(kubectl top pods -n ${NAMESPACE} 2>/dev/null || echo "无法获取资源使用情况")

存储状态:
$(kubectl get pvc -n ${NAMESPACE})

最近错误 (后端):
$(kubectl logs -n ${NAMESPACE} deployment/ai-safety-backend --tail=20 | grep -i error | tail -5)

最近错误 (前端):
$(kubectl logs -n ${NAMESPACE} deployment/ai-safety-frontend --tail=20 | grep -i error | tail -5)

==========================================
EOF
    
    log_success "报告已保存到: $report_file"
    echo "报告内容:"
    cat $report_file
}

# 主函数
main() {
    log_info "开始AI Safety Lab健康检查"
    echo "=========================================="
    
    local failed=0
    
    check_pods || failed=1
    check_services || failed=1
    check_resources
    check_logs
    performance_test
    
    echo "=========================================="
    
    if [[ $failed -eq 0 ]]; then
        log_success "所有健康检查通过! ✅"
        generate_report
        exit 0
    else
        log_error "健康检查发现问题! ❌"
        generate_report
        exit 1
    fi
}

# 解析命令行参数
case "${1:-}" in
    "report")
        generate_report
        ;;
    *)
        main
        ;;
esac