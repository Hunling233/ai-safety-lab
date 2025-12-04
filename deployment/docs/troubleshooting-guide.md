# AI Safety Lab - 故障排查指南

## 🚨 快速故障定位

### 故障分类矩阵

| 症状类型 | 可能原因 | 优先级 | 预估修复时间 |
|---------|---------|-------|------------|
| 服务完全不可用 | 基础设施故障 | P0 | 15-30分钟 |
| 接口响应超时 | 性能问题 | P1 | 30-60分钟 |
| 部分功能异常 | 应用逻辑错误 | P2 | 2-4小时 |
| 配置问题 | 配置错误 | P3 | 1-2小时 |

### 5分钟快速诊断流程
```bash
#!/bin/bash
echo "=== AI Safety Lab 快速诊断 ==="
echo "$(date): 开始故障诊断"

# 1. 检查基础设施
echo "1. 检查Kubernetes集群状态"
kubectl get nodes --no-headers | grep -v "Ready" && echo "❌ 节点异常" || echo "✅ 节点正常"

# 2. 检查应用状态
echo "2. 检查应用Pod状态"
kubectl get pods -n unicc-aisafety --no-headers | grep -v "Running\|Completed" && echo "❌ Pod异常" || echo "✅ Pod正常"

# 3. 检查服务可达性
echo "3. 检查服务可达性"
kubectl run diagnostic-test --rm -i --restart=Never --image=curlimages/curl -- \
  curl -f -m 5 http://ai-safety-backend-service.unicc-aisafety:8000/api/health \
  && echo "✅ 服务可达" || echo "❌ 服务不可达"

# 4. 检查资源使用
echo "4. 检查资源使用"
kubectl top nodes | awk 'NR>1 {if($3+0>80 || $5+0>80) print "❌ 资源紧张: " $1; else print "✅ 资源正常: " $1}'

echo "诊断完成: $(date)"
```

## 🔍 详细故障排查

### 1. 服务不可用问题

#### 1.1 Pod状态异常
```bash
# 查看Pod状态详情
kubectl get pods -n unicc-aisafety -o wide

# 查看Pod事件
kubectl describe pod <pod-name> -n unicc-aisafety

# 常见状态及处理方法
case "$POD_STATUS" in
    "Pending")
        echo "检查资源配额和调度约束"
        kubectl describe node
        kubectl get resourcequota -n unicc-aisafety
        ;;
    "ImagePullBackOff")
        echo "检查镜像地址和仓库访问权限"
        kubectl describe pod <pod-name> -n unicc-aisafety | grep -A5 "Events"
        ;;
    "CrashLoopBackOff")
        echo "检查应用日志和启动配置"
        kubectl logs <pod-name> -n unicc-aisafety --previous
        ;;
    "Error")
        echo "检查容器退出代码和错误信息"
        kubectl logs <pod-name> -n unicc-aisafety
        ;;
esac
```

#### 1.2 网络连接问题
```bash
# 网络连通性诊断
echo "=== 网络诊断 ==="

# 检查Service和Endpoints
kubectl get svc,ep -n unicc-aisafety

# 测试Pod间通信
kubectl exec -n unicc-aisafety <frontend-pod> -- \
  curl -v http://ai-safety-backend-service:8000/api/health

# 检查DNS解析
kubectl exec -n unicc-aisafety <pod-name> -- nslookup ai-safety-backend-service

# 检查网络策略
kubectl get networkpolicy -n unicc-aisafety -o yaml

# 端口连通性测试
kubectl exec -n unicc-aisafety <pod-name> -- nc -zv ai-safety-backend-service 8000
```

#### 1.3 负载均衡问题
```bash
# 检查Ingress状态
kubectl get ingress -n unicc-aisafety -o wide

# 检查负载均衡器日志
kubectl logs -n unicc-ingress-nginx deployment/nginx-ingress-controller

# 测试外部访问
curl -I https://aisafety.unicc.local/api/health

# 检查证书
echo | openssl s_client -connect aisafety.unicc.local:443 | openssl x509 -noout -dates
```

### 2. 性能问题排查

#### 2.1 高CPU使用率
```bash
# CPU使用分析
echo "=== CPU性能分析 ==="

# 查看Pod CPU使用情况
kubectl top pods -n unicc-aisafety

# 进入容器分析进程
kubectl exec -it <pod-name> -n unicc-aisafety -- top -n 1

# 查看系统负载
kubectl exec -it <pod-name> -n unicc-aisafety -- uptime

# 分析应用性能
kubectl exec -it <pod-name> -n unicc-aisafety -- ps aux --sort=-%cpu | head -10
```

#### 2.2 内存泄漏问题
```bash
# 内存使用分析
echo "=== 内存分析 ==="

# 查看内存使用趋势
kubectl top pods -n unicc-aisafety --sort-by=memory

# 内存详细信息
kubectl exec -it <pod-name> -n unicc-aisafety -- free -h

# 查看进程内存使用
kubectl exec -it <pod-name> -n unicc-aisafety -- ps aux --sort=-%mem | head -10

# Python应用内存调试
kubectl exec -it <pod-name> -n unicc-aisafety -- python -c "
import psutil
import os
process = psutil.Process(os.getpid())
print(f'Memory: {process.memory_info().rss / 1024 / 1024:.2f} MB')
print(f'Memory %: {process.memory_percent():.2f}%')
"
```

#### 2.3 响应时间优化
```bash
# 响应时间分析
echo "=== 响应时间分析 ==="

# API响应时间测试
kubectl run perf-test --rm -i --restart=Never --image=curlimages/curl -- \
  curl -w "@/dev/stdin" -s -o /dev/null http://ai-safety-backend-service:8000/api/health <<< "
time_namelookup:  %{time_namelookup}\n
time_connect:     %{time_connect}\n
time_appconnect:  %{time_appconnect}\n
time_pretransfer: %{time_pretransfer}\n
time_redirect:    %{time_redirect}\n
time_starttransfer: %{time_starttransfer}\n
time_total:       %{time_total}\n
"

# 应用层性能分析
kubectl logs <pod-name> -n unicc-aisafety | grep -i "response_time\|duration\|latency"
```

### 3. 存储问题排查

#### 3.1 磁盘空间不足
```bash
# 磁盘空间检查
echo "=== 存储空间分析 ==="

# 检查PVC使用情况
kubectl get pvc -n unicc-aisafety

# 查看容器内磁盘使用
kubectl exec -it <pod-name> -n unicc-aisafety -- df -h

# 找出大文件
kubectl exec -it <pod-name> -n unicc-aisafety -- du -h /app | sort -hr | head -20

# 清理临时文件
kubectl exec -it <pod-name> -n unicc-aisafety -- find /tmp -type f -mtime +7 -delete
kubectl exec -it <pod-name> -n unicc-aisafety -- find /app/logs -name "*.log" -mtime +30 -delete
```

#### 3.2 存储挂载问题
```bash
# 存储挂载诊断
echo "=== 存储挂载诊断 ==="

# 检查PV状态
kubectl get pv -o wide

# 检查存储类
kubectl get storageclass

# 验证挂载点
kubectl exec -it <pod-name> -n unicc-aisafety -- mount | grep -E '/app/(runs|logs)'

# 测试读写权限
kubectl exec -it <pod-name> -n unicc-aisafety -- touch /app/runs/test_write && \
  echo "✅ 存储可写" || echo "❌ 存储只读"
```

### 4. 应用层问题排查

#### 4.1 API错误分析
```bash
# API错误分析
echo "=== API错误分析 ==="

# 查看应用日志中的错误
kubectl logs <pod-name> -n unicc-aisafety | grep -i "error\|exception\|traceback" | tail -20

# 统计错误类型
kubectl logs <pod-name> -n unicc-aisafety | \
  grep -i error | \
  awk '{print $5}' | sort | uniq -c | sort -nr

# 检查依赖服务状态
kubectl exec -it <pod-name> -n unicc-aisafety -- python -c "
import requests
try:
    r = requests.get('https://api.openai.com', timeout=5)
    print('OpenAI API: ✅ 可达')
except Exception as e:
    print(f'OpenAI API: ❌ {e}')

try:
    r = requests.get('https://api.anthropic.com', timeout=5)
    print('Anthropic API: ✅ 可达')
except Exception as e:
    print(f'Anthropic API: ❌ {e}')
"
```

#### 4.2 数据完整性检查
```bash
# 数据完整性检查
echo "=== 数据完整性检查 ==="

# 检查测试结果文件
kubectl exec -it <pod-name> -n unicc-aisafety -- find /app/runs -name "*.json" | wc -l

# 验证配置文件
kubectl exec -it <pod-name> -n unicc-aisafety -- python -c "
import yaml
import json
try:
    with open('/app/config/run_hatespeech.yaml', 'r') as f:
        yaml.safe_load(f)
    print('配置文件: ✅ 有效')
except Exception as e:
    print(f'配置文件: ❌ {e}')
"

# 检查数据库连接（如果使用）
# kubectl exec -it <pod-name> -n unicc-aisafety -- python -c "
# import sqlite3
# conn = sqlite3.connect('/app/data/database.db')
# cursor = conn.cursor()
# cursor.execute('SELECT 1')
# print('数据库: ✅ 正常')
# conn.close()
# "
```

### 5. 安全问题排查

#### 5.1 认证授权问题
```bash
# 认证授权诊断
echo "=== 认证授权诊断 ==="

# 检查RBAC配置
kubectl get rolebinding,clusterrolebinding -n unicc-aisafety

# 验证服务账户权限
kubectl auth can-i --list --as=system:serviceaccount:unicc-aisafety:ai-safety-service-account -n unicc-aisafety

# 检查密钥配置
kubectl get secrets -n unicc-aisafety

# 测试API密钥
kubectl exec -it <pod-name> -n unicc-aisafety -- python -c "
import os
openai_key = os.environ.get('OPENAI_API_KEY')
print(f'OpenAI Key: {'✅ 配置' if openai_key else '❌ 未配置'}')
"
```

#### 5.2 网络安全检查
```bash
# 网络安全检查
echo "=== 网络安全检查 ==="

# 检查网络策略
kubectl get networkpolicy -n unicc-aisafety -o yaml

# 验证Pod安全上下文
kubectl get pods -n unicc-aisafety -o jsonpath='{.items[*].spec.securityContext}'

# 检查开放端口
kubectl exec -it <pod-name> -n unicc-aisafety -- netstat -tuln

# SSL证书检查
echo | openssl s_client -connect aisafety.unicc.local:443 2>/dev/null | openssl x509 -noout -text
```

## 🛠️ 故障修复常用命令

### 重启服务
```bash
# 重启特定Pod
kubectl delete pod <pod-name> -n unicc-aisafety

# 滚动重启Deployment
kubectl rollout restart deployment/ai-safety-backend -n unicc-aisafety

# 强制重建Pod
kubectl scale deployment ai-safety-backend --replicas=0 -n unicc-aisafety
kubectl scale deployment ai-safety-backend --replicas=2 -n unicc-aisafety
```

### 配置修复
```bash
# 更新ConfigMap
kubectl edit configmap ai-safety-config -n unicc-aisafety

# 更新Secret
kubectl create secret generic ai-safety-secrets \
  --from-literal=openai-api-key=new-key \
  --dry-run=client -o yaml | kubectl apply -f -

# 重新加载配置
kubectl rollout restart deployment/ai-safety-backend -n unicc-aisafety
```

### 临时修复
```bash
# 临时增加资源
kubectl patch deployment ai-safety-backend -n unicc-aisafety -p='
{
  "spec": {
    "template": {
      "spec": {
        "containers": [{
          "name": "backend",
          "resources": {
            "limits": {"memory": "4Gi", "cpu": "2000m"},
            "requests": {"memory": "1Gi", "cpu": "500m"}
          }
        }]
      }
    }
  }
}'

# 临时扩容
kubectl scale deployment ai-safety-backend --replicas=5 -n unicc-aisafety

# 临时禁用健康检查
kubectl patch deployment ai-safety-backend -n unicc-aisafety -p='
{
  "spec": {
    "template": {
      "spec": {
        "containers": [{
          "name": "backend",
          "livenessProbe": null,
          "readinessProbe": null
        }]
      }
    }
  }
}'
```

## 📊 故障处理报告模板

```
AI Safety Lab 故障处理报告

故障ID: INC-YYYY-XXXX
发生时间: YYYY-MM-DD HH:MM:SS
解决时间: YYYY-MM-DD HH:MM:SS
处理时长: X小时X分钟

=== 故障概述 ===
故障现象: [描述用户反馈的问题]
影响范围: [受影响的服务和用户]
严重级别: [P0/P1/P2/P3]

=== 根因分析 ===
直接原因: [导致故障的直接原因]
根本原因: [系统性问题分析]
触发因素: [引发故障的外部因素]

=== 解决过程 ===
1. 问题发现: [如何发现问题]
2. 应急处理: [临时解决方案]
3. 根本修复: [永久解决方案]
4. 验证测试: [修复效果验证]

=== 预防措施 ===
短期措施: [立即实施的改进]
长期措施: [系统性改进计划]
监控改进: [监控告警优化]
文档更新: [相关文档更新]

=== 经验总结 ===
处理亮点: [处理过程中的亮点]
改进建议: [流程改进建议]
技术债务: [需要解决的技术问题]

处理人员: [参与处理的人员]
审核人员: [报告审核人]
```

---

*遇到无法解决的问题，请联系技术支持团队：aisafety-support@unicc.local*