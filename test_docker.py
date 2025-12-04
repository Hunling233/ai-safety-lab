#!/usr/bin/env python3
"""
AI Safety Lab - Docker环境测试脚本
测试Docker容器化部署
"""

import subprocess
import time
import requests
import sys
from pathlib import Path

def run_command(cmd, shell=True):
    """执行命令并返回结果"""
    try:
        result = subprocess.run(cmd, shell=shell, capture_output=True, text=True, timeout=60)
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "命令执行超时"

def test_docker_build():
    """测试Docker镜像构建"""
    print("🔨 测试Docker镜像构建...")
    
    cmd = "docker build -f deployment/docker/Dockerfile.production -t ai-safety-lab:test ."
    success, stdout, stderr = run_command(cmd)
    
    if success:
        print("✅ Docker镜像构建成功")
        return True
    else:
        print(f"❌ Docker镜像构建失败: {stderr}")
        return False

def test_docker_compose():
    """测试Docker Compose部署"""
    print("🐳 测试Docker Compose部署...")
    
    # 启动服务
    cmd = "docker-compose -f deployment/docker/docker-compose.dev.yml up -d"
    success, stdout, stderr = run_command(cmd)
    
    if not success:
        print(f"❌ Docker Compose启动失败: {stderr}")
        return False
    
    print("⏳ 等待服务启动...")
    time.sleep(30)  # 等待服务完全启动
    
    # 测试服务可达性
    try:
        response = requests.get("http://localhost:8000/api/health", timeout=10)
        if response.status_code == 200:
            print("✅ Docker Compose部署成功，服务可达")
            success = True
        else:
            print(f"❌ 服务不可达，状态码: {response.status_code}")
            success = False
    except Exception as e:
        print(f"❌ 服务连接失败: {e}")
        success = False
    
    # 清理
    print("🧹 清理Docker Compose环境...")
    run_command("docker-compose -f deployment/docker/docker-compose.dev.yml down")
    
    return success

def main():
    print("🚀 开始Docker环境测试")
    
    # 检查Docker是否可用
    success, _, _ = run_command("docker --version")
    if not success:
        print("❌ Docker未安装或不可用")
        return False
    
    success, _, _ = run_command("docker-compose --version")
    if not success:
        print("❌ Docker Compose未安装或不可用")
        return False
    
    # 运行测试
    tests = [
        ("Docker镜像构建", test_docker_build),
        ("Docker Compose部署", test_docker_compose)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n🧪 执行测试: {test_name}")
        result = test_func()
        results.append((test_name, result))
    
    # 输出结果
    print("\n" + "="*50)
    print("Docker测试结果:")
    print("="*50)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print(f"\n通过率: {passed}/{total} ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 所有Docker测试通过！")
    else:
        print("⚠️  部分测试失败，请检查Docker配置")

if __name__ == "__main__":
    main()