# 🚀 AI Safety Lab - UNICC部署包

## 📦 部署包概述

本部署包包含了在UNICC AI沙盒环境中部署AI Safety Lab所需的所有配置、脚本和文档。

## 📁 目录结构

```
deployment/
├── docker/                      # Docker配置
│   ├── Dockerfile.production     # 生产环境镜像
│   ├── docker-compose.yml       # 生产环境编排
│   ├── docker-compose.dev.yml   # 开发环境编排
│   └── nginx.conf               # Nginx反向代理配置
├── kubernetes/                   # Kubernetes配置
│   ├── deployment.yaml          # 应用部署配置
│   ├── service.yaml             # 服务配置
│   ├── configmap.yaml           # 配置映射
│   └── ingress.yaml             # 入口和网络策略
├── scripts/                     # 自动化脚本
│   ├── deploy.sh               # 一键部署脚本
│   ├── health-check.sh         # 健康检查脚本
│   └── backup.sh               # 备份脚本
├── config/                      # 环境配置
│   ├── production.env          # 生产环境变量
│   ├── unicc-sandbox.yaml      # UNICC特定配置
│   └── security-policies.yaml   # 安全策略
├── monitoring/                   # 监控配置
│   ├── prometheus.yml          # Prometheus配置
│   ├── alertmanager.yml        # 告警管理配置
│   ├── fluentd.conf           # 日志收集配置
│   └── grafana-dashboard.json  # Grafana仪表板
└── docs/                        # 部署文档
    ├── deployment-guide.md      # 部署指南
    ├── operations-manual.md     # 运维手册
    └── troubleshooting-guide.md # 故障排查指南
```

## 🚀 快速开始

### 前置要求
- Kubernetes 1.20+
- Docker 20.10+
- kubectl配置完成
- UNICC环境访问权限

### 一键部署
```bash
cd deployment/scripts
chmod +x deploy.sh
./deploy.sh
```

### 验证部署
```bash
./health-check.sh
```

## 📚 文档导航

### 🏗️ 部署相关
- **[部署指南](docs/deployment-guide.md)** - 完整的部署步骤和配置说明
- **[Docker配置说明](docker/)** - 容器化配置详解
- **[Kubernetes配置说明](kubernetes/)** - K8s资源配置详解

### 🔧 运维相关
- **[运维操作手册](docs/operations-manual.md)** - 日常运维操作和维护流程
- **[故障排查指南](docs/troubleshooting-guide.md)** - 常见问题诊断和解决方案
- **[自动化脚本说明](scripts/)** - 运维脚本使用指南

### 📊 监控相关
- **[监控配置说明](monitoring/)** - Prometheus、Grafana和日志监控配置
- **[告警策略配置](config/security-policies.yaml)** - 告警规则和通知配置

### 🔐 安全相关
- **[安全策略配置](config/security-policies.yaml)** - 网络策略、RBAC和Pod安全策略
- **[UNICC合规配置](config/unicc-sandbox.yaml)** - UNICC特定的安全和合规要求

## ⚡ 部署方式对比

| 部署方式 | 适用场景 | 优势 | 劣势 |
|---------|---------|------|------|
| **一键脚本** | 生产环境首次部署 | 自动化程度高，错误处理完善 | 灵活性较低 |
| **手动K8s** | 定制化部署 | 完全可控，灵活配置 | 需要K8s经验 |
| **Docker Compose** | 开发测试 | 简单快速，易于调试 | 不适合生产环境 |

## 🔧 配置定制

### 环境变量配置
编辑 `config/production.env` 调整应用配置：
```bash
# 核心配置
AI_SAFETY_ENV=production
LOG_LEVEL=INFO
MAX_WORKERS=4

# UNICC特定配置  
UNICC_ENVIRONMENT=sandbox
UNICC_SECURITY_LEVEL=high
```

### 资源配置调整
编辑 `kubernetes/deployment.yaml` 调整资源限制：
```yaml
resources:
  requests:
    memory: "512Mi"
    cpu: "250m"
  limits:
    memory: "2Gi"
    cpu: "1000m"
```

### 监控配置定制
编辑 `monitoring/prometheus.yml` 调整监控指标收集。

## 📊 系统架构

```
                    ┌─────────────────────┐
                    │    UNICC用户        │
                    └──────────┬──────────┘
                               │ HTTPS
                    ┌─────────────────────┐
                    │   Nginx Ingress     │
                    │   负载均衡器         │
                    └──────────┬──────────┘
                               │
                    ┌─────────────────────┐
                    │  AI Safety Lab UI   │
                    │    (Streamlit)      │
                    └──────────┬──────────┘
                               │ HTTP API
                    ┌─────────────────────┐
                    │ AI Safety Lab API   │
                    │    (FastAPI)        │
                    └──────────┬──────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
    ┌─────────────────┐ ┌─────────────┐ ┌─────────────┐
    │   测试数据      │ │   配置文件   │ │    日志      │
    │  (PVC存储)     │ │ (ConfigMap) │ │  (PVC存储)   │
    └─────────────────┘ └─────────────┘ └─────────────┘
```

## 🔍 健康检查

系统提供多层次健康检查：

- **基础设施层**: Kubernetes节点和集群状态
- **应用层**: Pod状态、服务可达性
- **业务层**: API功能、测试套件执行
- **数据层**: 存储挂载、数据完整性

### 手动健康检查
```bash
# 快速检查
kubectl get pods,svc -n unicc-aisafety

# 详细检查
cd deployment/scripts
./health-check.sh

# 性能检查
kubectl top pods -n unicc-aisafety
```

## 📈 扩容指南

### 水平扩容
```bash
# 扩展后端服务
kubectl scale deployment ai-safety-backend --replicas=5 -n unicc-aisafety

# 扩展前端服务
kubectl scale deployment ai-safety-frontend --replicas=3 -n unicc-aisafety
```

### 垂直扩容
```bash
# 增加资源配额
kubectl patch deployment ai-safety-backend -n unicc-aisafety -p='
{
  "spec": {
    "template": {
      "spec": {
        "containers": [{
          "name": "backend",
          "resources": {
            "requests": {"memory": "1Gi", "cpu": "500m"},
            "limits": {"memory": "4Gi", "cpu": "2000m"}
          }
        }]
      }
    }
  }
}'
```

## 🔒 安全特性

- **零信任网络**: 默认拒绝所有网络流量
- **最小权限原则**: 细粒度RBAC权限控制
- **数据加密**: 传输和静态数据全加密
- **审计日志**: 完整的操作审计轨迹
- **安全扫描**: 定期安全漏洞扫描
- **合规认证**: 符合UNICC安全标准

## 📞 技术支持

### 联系方式
- **技术支持**: aisafety-support@unicc.local
- **安全问题**: security@unicc.local
- **运维支持**: ops@unicc.local

### 支持等级
- **P0 (紧急)**: 系统完全不可用 - 15分钟响应
- **P1 (高优先级)**: 核心功能异常 - 1小时响应
- **P2 (中优先级)**: 部分功能问题 - 4小时响应
- **P3 (低优先级)**: 功能改进请求 - 24小时响应

## 📝 版本历史

### v1.0.0 (2024-12-03)
- ✅ 初始版本发布
- ✅ UNICC环境完整适配
- ✅ 全套部署和运维工具
- ✅ 完整监控和告警系统
- ✅ 安全合规配置
- ✅ 详细文档和故障排查指南

## 🤝 贡献指南

1. 遵循UNICC开发规范
2. 所有配置变更需经过安全审查
3. 更新相关文档
4. 通过完整测试验证

---

**🎯 目标**: 为UNICC提供企业级、安全、可靠的AI安全测试平台  
**🛡️ 承诺**: 7×24小时可用性 > 99.9%  
**🔐 保证**: 符合所有UNICC安全和合规要求