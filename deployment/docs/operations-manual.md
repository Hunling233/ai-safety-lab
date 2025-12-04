# AI Safety Lab - 运维操作手册

## 📋 日常运维清单

### 🌅 每日检查 (自动化)
- [ ] 系统健康状态检查
- [ ] 资源使用率监控
- [ ] 错误日志审查
- [ ] 备份任务验证
- [ ] 安全告警处理

### 📅 每周维护
- [ ] 性能指标分析
- [ ] 存储空间清理
- [ ] 安全补丁更新
- [ ] 备份恢复测试
- [ ] 用户访问审计

### 📊 每月报告
- [ ] 系统可用性统计
- [ ] 性能趋势分析
- [ ] 安全事件总结
- [ ] 容量规划评估
- [ ] 成本优化建议

## 🔧 运维脚本

### 系统状态检查
```bash
#!/bin/bash
# 系统状态快速检查脚本

echo "=== AI Safety Lab 系统状态 ==="
echo "时间: $(date)"
echo

# 检查Pod状态
echo "📦 Pod状态:"
kubectl get pods -n unicc-aisafety -o wide

echo
# 检查服务状态
echo "🌐 服务状态:"
kubectl get services -n unicc-aisafety

echo
# 检查资源使用
echo "💾 资源使用:"
kubectl top pods -n unicc-aisafety || echo "Metrics server不可用"

echo
# 检查存储
echo "💿 存储状态:"
kubectl get pvc -n unicc-aisafety

echo
# 检查最近的错误
echo "🚨 最近错误:"
kubectl logs --since=1h -l app=ai-safety-backend -n unicc-aisafety | grep -i error | tail -5
```

### 性能监控
```bash
#!/bin/bash
# 性能监控脚本

NAMESPACE="unicc-aisafety"
BACKEND_POD=$(kubectl get pods -n $NAMESPACE -l app=ai-safety-backend -o jsonpath='{.items[0].metadata.name}')

echo "=== 性能指标收集 ==="
echo

# CPU和内存使用
echo "🖥️ 资源使用情况:"
kubectl exec -n $NAMESPACE $BACKEND_POD -- top -n 1 -b | head -20

echo
# 磁盘使用
echo "💾 磁盘使用情况:"
kubectl exec -n $NAMESPACE $BACKEND_POD -- df -h

echo
# 网络连接
echo "🌐 网络连接状态:"
kubectl exec -n $NAMESPACE $BACKEND_POD -- netstat -tuln | head -10

echo
# API响应时间测试
echo "⚡ API响应时间:"
for i in {1..5}; do
    kubectl exec -n $NAMESPACE $BACKEND_POD -- \
        curl -w "@curl-format.txt" -s -o /dev/null \
        http://localhost:8000/api/health
    sleep 1
done
```

### 日志收集
```bash
#!/bin/bash
# 日志收集和分析脚本

NAMESPACE="unicc-aisafety"
DATE=$(date +%Y%m%d_%H%M%S)
LOG_DIR="/tmp/aisafety-logs-$DATE"

mkdir -p $LOG_DIR

echo "📊 收集AI Safety Lab日志..."

# 收集Pod日志
echo "收集Pod日志..."
for pod in $(kubectl get pods -n $NAMESPACE -o name); do
    pod_name=$(basename $pod)
    kubectl logs --previous $pod -n $NAMESPACE > "$LOG_DIR/${pod_name}-previous.log" 2>/dev/null
    kubectl logs $pod -n $NAMESPACE > "$LOG_DIR/${pod_name}-current.log"
done

# 收集事件
echo "收集事件日志..."
kubectl get events -n $NAMESPACE > "$LOG_DIR/events.log"

# 收集配置信息
echo "收集配置信息..."
kubectl get all -n $NAMESPACE -o yaml > "$LOG_DIR/resources.yaml"

# 生成摘要
echo "生成日志摘要..."
cat > "$LOG_DIR/summary.txt" << EOF
AI Safety Lab 日志收集摘要
收集时间: $(date)
命名空间: $NAMESPACE

文件列表:
$(ls -la $LOG_DIR)

最近错误统计:
$(grep -r "ERROR" $LOG_DIR/*.log | wc -l) 个错误
$(grep -r "WARN" $LOG_DIR/*.log | wc -l) 个警告

存储使用:
$(du -sh $LOG_DIR)
EOF

echo "日志收集完成: $LOG_DIR"
echo "压缩日志文件..."
tar -czf "/tmp/aisafety-logs-$DATE.tar.gz" -C /tmp "aisafety-logs-$DATE"
echo "压缩文件: /tmp/aisafety-logs-$DATE.tar.gz"
```

## 🚨 告警响应流程

### 严重告警 (Critical)
1. **立即响应** (5分钟内)
   - 确认告警真实性
   - 评估业务影响
   - 启动应急响应

2. **快速修复** (15分钟内)
   - 实施临时解决方案
   - 通知相关干系人
   - 记录处理过程

3. **根因分析** (1小时内)
   - 深入分析根本原因
   - 制定永久解决方案
   - 更新运维文档

### 警告告警 (Warning)
1. **及时响应** (30分钟内)
   - 分析告警原因
   - 评估潜在影响
   - 制定处理计划

2. **计划修复** (4小时内)
   - 在维护窗口期修复
   - 验证修复效果
   - 更新监控阈值

### 信息告警 (Info)
1. **定期检查** (24小时内)
   - 记录告警信息
   - 趋势分析
   - 预防性维护

## 🔄 变更管理

### 变更类型
- **紧急变更**: 安全漏洞修复
- **标准变更**: 版本升级
- **常规变更**: 配置调整

### 变更流程
1. **变更申请**
   - 填写变更申请单
   - 风险评估分析
   - 回滚计划制定

2. **变更审批**
   - 技术负责人审批
   - 安全团队审批
   - 业务负责人确认

3. **变更实施**
   - 在维护窗口执行
   - 实时监控系统
   - 验证变更结果

4. **变更验证**
   - 功能测试验证
   - 性能指标检查
   - 用户反馈收集

### 维护窗口
- **标准维护窗口**: 每周日 02:00-06:00
- **紧急维护窗口**: 随时（需要审批）
- **计划停机时间**: 最大4小时/月

## 🔐 安全运维

### 安全检查清单
- [ ] 访问日志审计
- [ ] 异常登录检测
- [ ] 权限变更审查
- [ ] 安全补丁状态
- [ ] 网络流量分析
- [ ] 数据完整性验证

### 安全事件响应
1. **事件识别**
   - 自动检测告警
   - 人工发现报告
   - 第三方通知

2. **事件分类**
   - **P0**: 数据泄露/系统入侵
   - **P1**: 服务不可用
   - **P2**: 性能严重降级
   - **P3**: 功能异常

3. **响应流程**
   ```bash
   # 安全事件响应脚本
   #!/bin/bash
   INCIDENT_ID=$1
   SEVERITY=$2
   
   echo "安全事件响应 - ID: $INCIDENT_ID, 级别: $SEVERITY"
   
   # 隔离受影响的服务
   if [ "$SEVERITY" = "P0" ]; then
       kubectl scale deployment ai-safety-backend --replicas=0 -n unicc-aisafety
       echo "服务已紧急停止"
   fi
   
   # 收集证据
   ./collect-logs.sh $INCIDENT_ID
   
   # 通知安全团队
   curl -X POST "https://security.unicc.local/api/incidents" \
        -d "{\"id\":\"$INCIDENT_ID\",\"severity\":\"$SEVERITY\"}"
   ```

## 📊 容量规划

### 资源监控指标
- **CPU使用率**: 目标 <70%
- **内存使用率**: 目标 <80%
- **磁盘使用率**: 目标 <75%
- **网络带宽**: 目标 <60%

### 扩容触发条件
```yaml
# 自动扩容配置
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: ai-safety-backend-hpa
  namespace: unicc-aisafety
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: ai-safety-backend
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

### 容量规划报告模板
```
AI Safety Lab 容量规划报告

报告期间: [开始日期] - [结束日期]

当前资源使用:
- CPU平均使用率: XX%
- 内存平均使用率: XX%
- 存储使用量: XXGB
- 网络流量: XX Mbps

峰值负载:
- 最高CPU使用率: XX% (时间点)
- 最高内存使用率: XX% (时间点)
- 最大并发用户数: XXX

增长趋势:
- 用户数增长: XX%/月
- 数据量增长: XXGB/月
- 请求量增长: XX%/月

扩容建议:
1. 建议在[时间]前增加[资源]
2. 预计需要额外[数量][资源类型]
3. 预算影响: $XXXX/月
```

## 🔧 故障排查手册

### 常见故障及解决方案

#### 1. Pod无法启动
**症状**: Pod状态为Pending/CrashLoopBackOff
```bash
# 诊断步骤
kubectl describe pod <pod-name> -n unicc-aisafety
kubectl logs <pod-name> -n unicc-aisafety

# 可能原因及解决方案
# 1. 资源不足
kubectl top nodes
kubectl describe nodes

# 2. 镜像拉取失败
kubectl get events -n unicc-aisafety | grep Failed

# 3. 配置错误
kubectl get configmap -n unicc-aisafety -o yaml
```

#### 2. 服务无法访问
**症状**: API请求超时或拒绝连接
```bash
# 诊断步骤
kubectl get services -n unicc-aisafety
kubectl get endpoints -n unicc-aisafety

# 网络连通性测试
kubectl run test-pod --rm -i --restart=Never --image=curlimages/curl -- \
    curl -v http://ai-safety-backend-service:8000/api/health

# 检查网络策略
kubectl get networkpolicies -n unicc-aisafety
```

#### 3. 性能问题
**症状**: 响应时间长，CPU/内存使用率高
```bash
# 性能分析
kubectl top pods -n unicc-aisafety
kubectl exec -it <pod-name> -n unicc-aisafety -- htop

# 应用层分析
kubectl logs <pod-name> -n unicc-aisafety | grep -i "slow\|timeout\|error"
```

#### 4. 存储问题
**症状**: PVC无法挂载或磁盘空间不足
```bash
# 存储诊断
kubectl get pv,pvc -n unicc-aisafety
kubectl describe pvc <pvc-name> -n unicc-aisafety

# 清理存储空间
kubectl exec -it <pod-name> -n unicc-aisafety -- df -h
kubectl exec -it <pod-name> -n unicc-aisafety -- find /app/runs -type f -mtime +30 -delete
```

## 📋 检查清单模板

### 部署后检查清单
- [ ] 所有Pod状态为Running
- [ ] 服务端点正常响应
- [ ] 健康检查通过
- [ ] 监控指标正常
- [ ] 日志输出正常
- [ ] 安全策略生效
- [ ] 备份任务配置
- [ ] 告警规则测试

### 升级后检查清单
- [ ] 版本号确认
- [ ] 数据库迁移完成
- [ ] 配置文件更新
- [ ] 功能回归测试
- [ ] 性能基准对比
- [ ] 用户接受测试
- [ ] 回滚方案验证

### 应急响应检查清单
- [ ] 问题影响范围确认
- [ ] 临时解决方案实施
- [ ] 用户通知发送
- [ ] 日志和证据保存
- [ ] 根因分析开始
- [ ] 永久修复计划制定
- [ ] 事后总结报告

---

*本手册遵循UNICC运维标准和最佳实践*