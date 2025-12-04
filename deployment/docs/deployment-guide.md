# AI Safety Lab - UNICC部署指南

## 📋 概述

本指南详细说明如何在UNICC AI沙盒环境中部署AI Safety Lab系统。

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────┐
│                 UNICC AI 沙盒                        │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌─────────────┐    ┌─────────────────────────────┐  │
│  │   Nginx     │    │        Kubernetes           │  │
│  │ LoadBalancer│    │        Cluster              │  │
│  │   :80,:443  │    │                             │  │
│  └─────┬───────┘    └─────────────────────────────┘  │
│        │                                             │
│  ┌─────▼─────────────────────────────────────────┐   │
│  │            AI Safety Lab Namespace           │   │
│  │                                              │   │
│  │  ┌─────────────┐  ┌─────────────────────────┐ │   │
│  │  │  Frontend   │  │       Backend           │ │   │
│  │  │ Streamlit   │  │      FastAPI            │ │   │
│  │  │   :8501     │  │        :8000            │ │   │
│  │  └─────────────┘  └─────────────────────────┘ │   │
│  │                                              │   │
│  │  ┌─────────────────────────────────────────┐ │   │
│  │  │           共享存储                       │ │   │
│  │  │    测试结果 + 配置 + 日志                │ │   │
│  │  └─────────────────────────────────────────┘ │   │
│  └──────────────────────────────────────────────┘   │
│                                                     │
│  ┌─────────────────────────────────────────────┐     │
│  │           监控和日志系统                     │     │
│  │   Prometheus + Grafana + Fluentd           │     │
│  └─────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────┘
```

## 🔧 环境要求

### 硬件要求
- **CPU**: 4 cores (推荐 8 cores)
- **内存**: 8GB RAM (推荐 16GB)
- **存储**: 100GB (推荐 200GB)
- **网络**: 1Gbps 内网连接

### 软件要求
- **Kubernetes**: v1.20+ 
- **Docker**: v20.10+
- **kubectl**: v1.20+
- **Helm**: v3.0+ (可选)

### UNICC特定要求
- UNICC SSO集成
- UNICC网络策略合规
- UNICC安全审计要求
- UNICC数据本地化政策

## 📦 部署前准备

### 1. 验证环境
```bash
# 检查Kubernetes集群连接
kubectl cluster-info

# 检查节点状态
kubectl get nodes

# 验证存储类
kubectl get storageclass

# 检查网络策略支持
kubectl get networkpolicies -A
```

### 2. 创建命名空间
```bash
kubectl create namespace unicc-aisafety
kubectl label namespace unicc-aisafety name=unicc-aisafety
```

### 3. 配置镜像仓库
```bash
# 登录UNICC内部镜像仓库
docker login unicc-registry.local

# 构建并推送镜像
cd ai-safety-lab
docker build -f deployment/docker/Dockerfile.production \
  -t unicc-registry.local/ai-safety-lab:latest .
docker push unicc-registry.local/ai-safety-lab:latest
```

## 🚀 部署步骤

### 方法一: 一键部署脚本
```bash
# 使用自动化脚本部署
cd deployment/scripts
chmod +x deploy.sh
./deploy.sh
```

### 方法二: 手动部署
```bash
# 1. 部署配置
kubectl apply -f deployment/kubernetes/configmap.yaml

# 2. 部署存储
kubectl apply -f deployment/kubernetes/configmap.yaml

# 3. 部署应用
kubectl apply -f deployment/kubernetes/deployment.yaml

# 4. 部署服务
kubectl apply -f deployment/kubernetes/service.yaml

# 5. 配置入口
kubectl apply -f deployment/kubernetes/ingress.yaml

# 6. 应用安全策略
kubectl apply -f deployment/config/security-policies.yaml
```

### 方法三: Docker Compose (开发/测试)
```bash
# 快速启动开发环境
cd deployment/docker
docker-compose -f docker-compose.dev.yml up -d
```

## 🔍 部署验证

### 1. 检查Pod状态
```bash
kubectl get pods -n unicc-aisafety
```

### 2. 检查服务状态
```bash
kubectl get services -n unicc-aisafety
```

### 3. 运行健康检查
```bash
cd deployment/scripts
./health-check.sh
```

### 4. 访问应用
- **Web界面**: https://aisafety.unicc.local
- **API文档**: https://aisafety.unicc.local/docs
- **监控面板**: https://monitoring.unicc.local/grafana

## 📊 监控配置

### Prometheus配置
```bash
# 部署Prometheus
kubectl apply -f deployment/monitoring/prometheus.yml

# 配置监控规则
kubectl apply -f deployment/config/security-policies.yaml
```

### Grafana仪表板
1. 导入仪表板配置: `deployment/monitoring/grafana-dashboard.json`
2. 配置数据源: Prometheus endpoint
3. 设置告警通知渠道

### 日志聚合
```bash
# 部署Fluentd
kubectl apply -f deployment/monitoring/fluentd.conf

# 配置日志转发到UNICC日志系统
```

## 🔐 安全配置

### 1. 网络策略
- 默认拒绝所有流量
- 仅允许必要的内部通信
- 限制外部访问端口

### 2. Pod安全策略
- 非root用户运行
- 只读根文件系统
- 禁用特权提升

### 3. RBAC配置
- 最小权限原则
- 服务账户隔离
- 细粒度访问控制

### 4. 数据加密
- 传输中加密 (TLS 1.3)
- 静态数据加密 (AES-256)
- 密钥轮换策略

## 🔧 配置管理

### 环境变量配置
编辑 `deployment/config/production.env`:
```bash
# 应用配置
AI_SAFETY_ENV=production
LOG_LEVEL=INFO

# UNICC特定配置
UNICC_ENVIRONMENT=sandbox
UNICC_SECURITY_LEVEL=high
```

### Kubernetes ConfigMap
```bash
kubectl edit configmap ai-safety-config -n unicc-aisafety
```

### 密钥管理
```bash
# 创建API密钥
kubectl create secret generic ai-safety-secrets \
  --from-literal=openai-api-key=sk-... \
  --from-literal=anthropic-api-key=sk-... \
  -n unicc-aisafety
```

## 📈 扩展配置

### 水平扩展
```bash
# 扩展后端副本
kubectl scale deployment ai-safety-backend --replicas=3 -n unicc-aisafety

# 扩展前端副本
kubectl scale deployment ai-safety-frontend --replicas=2 -n unicc-aisafety
```

### 资源调整
编辑 deployment.yaml 中的资源限制:
```yaml
resources:
  requests:
    memory: "1Gi"
    cpu: "500m"
  limits:
    memory: "2Gi"
    cpu: "1000m"
```

## 🔄 升级流程

### 滚动更新
```bash
# 更新镜像
kubectl set image deployment/ai-safety-backend \
  backend=unicc-registry.local/ai-safety-lab:v1.1.0 \
  -n unicc-aisafety

# 检查更新状态
kubectl rollout status deployment/ai-safety-backend -n unicc-aisafety
```

### 回滚操作
```bash
# 查看历史版本
kubectl rollout history deployment/ai-safety-backend -n unicc-aisafety

# 回滚到前一版本
kubectl rollout undo deployment/ai-safety-backend -n unicc-aisafety
```

## 🗄️ 备份和恢复

### 自动化备份
```bash
# 配置定时备份
kubectl create cronjob aisafety-backup \
  --image=unicc-registry.local/backup-tool:latest \
  --schedule="0 2 * * *" \
  -- /scripts/backup.sh

# 手动备份
cd deployment/scripts
./backup.sh
```

### 恢复流程
```bash
# 从备份恢复
./backup.sh restore /path/to/backup.tar.gz
```

## 🚨 故障排查

### 常见问题

#### Pod启动失败
```bash
# 查看Pod日志
kubectl logs -f deployment/ai-safety-backend -n unicc-aisafety

# 查看Pod事件
kubectl describe pod <pod-name> -n unicc-aisafety
```

#### 网络连接问题
```bash
# 测试服务连接
kubectl exec -it <pod-name> -n unicc-aisafety -- curl http://ai-safety-backend-service:8000/api/health
```

#### 存储问题
```bash
# 检查PVC状态
kubectl get pvc -n unicc-aisafety

# 检查存储类
kubectl describe storageclass
```

### 调试工具
```bash
# 进入Pod调试
kubectl exec -it <pod-name> -n unicc-aisafety -- /bin/bash

# 端口转发调试
kubectl port-forward service/ai-safety-backend-service 8000:8000 -n unicc-aisafety
```

## 📞 支持联系

- **技术支持**: aisafety-support@unicc.local
- **安全问题**: security@unicc.local
- **运维支持**: ops@unicc.local

## 📝 更新日志

### v1.0.0 (2024-12-03)
- 初始版本发布
- UNICC环境适配
- 完整监控集成

---

*本文档遵循UNICC技术文档规范和安全要求*