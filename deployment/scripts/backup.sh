#!/bin/bash
# AI Safety Lab - 备份脚本
# 用途: 备份测试数据、配置和日志

set -e

NAMESPACE="unicc-aisafety"
BACKUP_DIR="/backup/aisafety"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

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

# 创建备份目录
create_backup_dir() {
    log_info "创建备份目录..."
    
    mkdir -p ${BACKUP_DIR}/${DATE}
    
    log_success "备份目录创建完成: ${BACKUP_DIR}/${DATE}"
}

# 备份Kubernetes配置
backup_k8s_config() {
    log_info "备份Kubernetes配置..."
    
    local config_dir="${BACKUP_DIR}/${DATE}/k8s-config"
    mkdir -p $config_dir
    
    # 备份所有Kubernetes资源
    kubectl get all -n ${NAMESPACE} -o yaml > $config_dir/all-resources.yaml
    kubectl get configmap -n ${NAMESPACE} -o yaml > $config_dir/configmaps.yaml
    kubectl get secrets -n ${NAMESPACE} -o yaml > $config_dir/secrets.yaml
    kubectl get pvc -n ${NAMESPACE} -o yaml > $config_dir/pvcs.yaml
    kubectl get ingress -n ${NAMESPACE} -o yaml > $config_dir/ingress.yaml
    
    log_success "Kubernetes配置备份完成"
}

# 备份应用数据
backup_app_data() {
    log_info "备份应用数据..."
    
    local data_dir="${BACKUP_DIR}/${DATE}/app-data"
    mkdir -p $data_dir
    
    # 获取运行中的Pod
    local pod_name=$(kubectl get pods -n ${NAMESPACE} -l app=ai-safety-backend --output=jsonpath='{.items[0].metadata.name}')
    
    if [[ -n "$pod_name" ]]; then
        # 备份测试结果
        kubectl exec -n ${NAMESPACE} $pod_name -- tar czf - /app/runs > $data_dir/runs.tar.gz
        
        # 备份日志
        kubectl exec -n ${NAMESPACE} $pod_name -- tar czf - /app/logs > $data_dir/logs.tar.gz
        
        # 备份配置文件
        kubectl exec -n ${NAMESPACE} $pod_name -- tar czf - /app/config > $data_dir/config.tar.gz
        
        log_success "应用数据备份完成"
    else
        log_error "未找到运行中的后端Pod"
        return 1
    fi
}

# 备份数据库（如果有）
backup_database() {
    log_info "检查数据库备份需求..."
    
    # 这里可以添加数据库备份逻辑
    # 目前AI Safety Lab使用文件存储，无需数据库备份
    
    log_info "无数据库需要备份"
}

# 创建备份元数据
create_backup_metadata() {
    log_info "创建备份元数据..."
    
    local metadata_file="${BACKUP_DIR}/${DATE}/backup-metadata.json"
    
    cat > $metadata_file << EOF
{
    "timestamp": "$(date -Iseconds)",
    "namespace": "${NAMESPACE}",
    "kubernetes_version": "$(kubectl version --short --client)",
    "backup_components": [
        "k8s-config",
        "app-data",
        "logs"
    ],
    "pods_backed_up": $(kubectl get pods -n ${NAMESPACE} -o json | jq '.items | length'),
    "backup_size": "$(du -sh ${BACKUP_DIR}/${DATE} | cut -f1)"
}
EOF
    
    log_success "备份元数据创建完成"
}

# 压缩备份
compress_backup() {
    log_info "压缩备份文件..."
    
    cd ${BACKUP_DIR}
    tar czf "aisafety-backup-${DATE}.tar.gz" ${DATE}/
    
    # 删除未压缩的目录
    rm -rf ${DATE}/
    
    log_success "备份压缩完成: aisafety-backup-${DATE}.tar.gz"
}

# 清理旧备份
cleanup_old_backups() {
    log_info "清理超过 ${RETENTION_DAYS} 天的旧备份..."
    
    find ${BACKUP_DIR} -name "aisafety-backup-*.tar.gz" -mtime +${RETENTION_DAYS} -delete
    
    local remaining_backups=$(find ${BACKUP_DIR} -name "aisafety-backup-*.tar.gz" | wc -l)
    log_success "备份清理完成，剩余 ${remaining_backups} 个备份文件"
}

# 验证备份
verify_backup() {
    log_info "验证备份完整性..."
    
    local backup_file="${BACKUP_DIR}/aisafety-backup-${DATE}.tar.gz"
    
    if tar -tzf $backup_file > /dev/null 2>&1; then
        log_success "备份文件验证通过"
    else
        log_error "备份文件验证失败"
        return 1
    fi
    
    # 显示备份信息
    log_info "备份信息:"
    echo "文件: $backup_file"
    echo "大小: $(du -sh $backup_file | cut -f1)"
    echo "内容:"
    tar -tzf $backup_file | head -20
}

# 还原备份
restore_backup() {
    local backup_file=$1
    
    if [[ -z "$backup_file" || ! -f "$backup_file" ]]; then
        log_error "请指定有效的备份文件"
        return 1
    fi
    
    log_warning "开始还原备份: $backup_file"
    log_warning "这将覆盖现有配置！按 Ctrl+C 取消，或等待 10 秒继续..."
    sleep 10
    
    # 解压备份
    local restore_dir="/tmp/aisafety-restore-$$"
    mkdir -p $restore_dir
    tar -xzf $backup_file -C $restore_dir
    
    # 还原Kubernetes配置
    local config_dir=$(find $restore_dir -name "k8s-config" | head -1)
    if [[ -n "$config_dir" ]]; then
        kubectl apply -f $config_dir/configmaps.yaml
        kubectl apply -f $config_dir/secrets.yaml
        kubectl apply -f $config_dir/pvcs.yaml
        kubectl apply -f $config_dir/all-resources.yaml
        kubectl apply -f $config_dir/ingress.yaml
    fi
    
    # 清理临时目录
    rm -rf $restore_dir
    
    log_success "备份还原完成"
}

# 显示备份列表
list_backups() {
    log_info "可用备份列表:"
    
    if [[ -d "${BACKUP_DIR}" ]]; then
        find ${BACKUP_DIR} -name "aisafety-backup-*.tar.gz" -printf "%T@ %Tc %s %p\n" | sort -n | \
        while read timestamp date size file; do
            echo "$(basename $file) - $date ($(numfmt --to=iec $size))"
        done
    else
        log_warning "备份目录不存在"
    fi
}

# 主函数
main() {
    log_info "开始AI Safety Lab备份"
    
    create_backup_dir
    backup_k8s_config
    backup_app_data
    backup_database
    create_backup_metadata
    compress_backup
    cleanup_old_backups
    verify_backup
    
    log_success "备份完成! 🎉"
    
    # 显示备份统计
    local backup_count=$(find ${BACKUP_DIR} -name "aisafety-backup-*.tar.gz" | wc -l)
    log_info "当前共有 ${backup_count} 个备份文件"
}

# 解析命令行参数
case "${1:-}" in
    "restore")
        restore_backup "$2"
        ;;
    "list")
        list_backups
        ;;
    *)
        main
        ;;
esac