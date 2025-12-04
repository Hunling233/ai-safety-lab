#!/usr/bin/env python3
"""
AI Safety Lab - 本地测试脚本
测试所有核心功能和LangChain集成
"""

import sys
import requests
import time
import json
from pathlib import Path

# 配置
BACKEND_URL = "http://localhost:8000"
FRONTEND_URL = "http://localhost:8501"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    ENDC = '\033[0m'

def log_info(msg):
    print(f"{Colors.BLUE}[INFO]{Colors.ENDC} {msg}")

def log_success(msg):
    print(f"{Colors.GREEN}[SUCCESS]{Colors.ENDC} {msg}")

def log_error(msg):
    print(f"{Colors.RED}[ERROR]{Colors.ENDC} {msg}")

def log_warning(msg):
    print(f"{Colors.YELLOW}[WARNING]{Colors.ENDC} {msg}")

def test_backend_health():
    """测试后端服务健康状态"""
    log_info("测试后端服务健康状态...")
    try:
        response = requests.get(f"{BACKEND_URL}/api/health", timeout=10)
        if response.status_code == 200:
            log_success("后端服务正常运行")
            return True
        else:
            log_error(f"后端服务异常，状态码: {response.status_code}")
            return False
    except Exception as e:
        log_error(f"后端服务连接失败: {e}")
        return False

def test_frontend_health():
    """测试前端服务健康状态"""
    log_info("测试前端服务健康状态...")
    try:
        response = requests.get(FRONTEND_URL, timeout=10)
        if response.status_code == 200:
            log_success("前端服务正常运行")
            return True
        else:
            log_error(f"前端服务异常，状态码: {response.status_code}")
            return False
    except Exception as e:
        log_error(f"前端服务连接失败: {e}")
        return False

def test_langchain_adapter():
    """测试LangChain适配器"""
    log_info("测试LangChain适配器...")
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from adapters.langchain_adapter import LangChainAdapter, create_langchain_adapter
        
        # 测试适配器创建函数
        test_config = {
            "type": "simple_llm",
            "model": "openai",
            "api_key": "test-key",
            "temperature": 0.7
        }
        
        adapter = create_langchain_adapter(test_config)
        log_success("LangChain适配器创建成功")
        return True
    except Exception as e:
        log_error(f"LangChain适配器测试失败: {e}")
        return False

def test_api_endpoints():
    """测试API端点"""
    log_info("测试API端点...")
    
    endpoints = [
        "/api/health",
        "/api/agents",
        "/docs",
    ]
    
    success_count = 0
    for endpoint in endpoints:
        try:
            response = requests.get(f"{BACKEND_URL}{endpoint}", timeout=5)
            if response.status_code == 200:
                log_success(f"✅ {endpoint}")
                success_count += 1
            else:
                log_error(f"❌ {endpoint} - 状态码: {response.status_code}")
        except Exception as e:
            log_error(f"❌ {endpoint} - 错误: {e}")
    
    if success_count == len(endpoints):
        log_success("所有API端点测试通过")
        return True
    else:
        log_warning(f"API端点测试: {success_count}/{len(endpoints)} 通过")
        return False

def test_simple_ai_test():
    """测试简单的AI安全测试"""
    log_info("执行简单的AI安全测试...")
    
    test_payload = {
        "agent": "mock",
        "testSuite": "ethics",
        "prompt": "Hello, this is a test message"
    }
    
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/run",
            json=test_payload,
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            log_success("AI安全测试执行成功")
            log_info(f"测试结果: {result.get('score', 'N/A')}")
            return True
        else:
            log_error(f"AI安全测试失败，状态码: {response.status_code}")
            return False
    except Exception as e:
        log_error(f"AI安全测试执行失败: {e}")
        return False

def test_configuration_files():
    """测试配置文件完整性"""
    log_info("检查配置文件完整性...")
    
    config_files = [
        "config/run_hatespeech.yaml",
        "config/run_shixuanlin.yaml", 
        "config/run_verimedia.yaml",
        "pyproject.toml",
        "requirements.txt"
    ]
    
    missing_files = []
    for config_file in config_files:
        if not Path(config_file).exists():
            missing_files.append(config_file)
    
    if not missing_files:
        log_success("所有配置文件完整")
        return True
    else:
        log_warning(f"缺少配置文件: {missing_files}")
        return False

def test_deployment_readiness():
    """测试部署就绪性"""
    log_info("检查部署就绪性...")
    
    deployment_files = [
        "deployment/docker/Dockerfile.production",
        "deployment/docker/docker-compose.yml",
        "deployment/kubernetes/deployment.yaml",
        "deployment/scripts/deploy.sh"
    ]
    
    missing_files = []
    for deploy_file in deployment_files:
        if not Path(deploy_file).exists():
            missing_files.append(deploy_file)
    
    if not missing_files:
        log_success("部署文件完整，可以进行部署")
        return True
    else:
        log_error(f"缺少部署文件: {missing_files}")
        return False

def run_comprehensive_test():
    """运行综合测试"""
    print(f"\n{Colors.BLUE}{'='*50}{Colors.ENDC}")
    print(f"{Colors.BLUE}AI Safety Lab 综合测试开始{Colors.ENDC}")
    print(f"{Colors.BLUE}{'='*50}{Colors.ENDC}\n")
    
    test_results = []
    
    # 运行所有测试
    tests = [
        ("配置文件检查", test_configuration_files),
        ("LangChain适配器", test_langchain_adapter),
        ("后端服务", test_backend_health),
        ("前端服务", test_frontend_health),
        ("API端点", test_api_endpoints),
        ("AI安全测试", test_simple_ai_test),
        ("部署就绪性", test_deployment_readiness)
    ]
    
    for test_name, test_func in tests:
        print(f"\n🧪 正在执行: {test_name}")
        result = test_func()
        test_results.append((test_name, result))
        time.sleep(1)  # 避免请求过快
    
    # 生成测试报告
    print(f"\n{Colors.BLUE}{'='*50}{Colors.ENDC}")
    print(f"{Colors.BLUE}测试结果总结{Colors.ENDC}")
    print(f"{Colors.BLUE}{'='*50}{Colors.ENDC}")
    
    passed = 0
    failed = 0
    
    for test_name, result in test_results:
        status = "✅ PASS" if result else "❌ FAIL"
        color = Colors.GREEN if result else Colors.RED
        print(f"{color}{status}{Colors.ENDC} {test_name}")
        
        if result:
            passed += 1
        else:
            failed += 1
    
    total = passed + failed
    success_rate = (passed / total * 100) if total > 0 else 0
    
    print(f"\n📊 测试统计:")
    print(f"总测试数: {total}")
    print(f"通过: {Colors.GREEN}{passed}{Colors.ENDC}")
    print(f"失败: {Colors.RED}{failed}{Colors.ENDC}")
    print(f"成功率: {Colors.YELLOW}{success_rate:.1f}%{Colors.ENDC}")
    
    if success_rate >= 80:
        print(f"\n🎉 {Colors.GREEN}系统状态良好，可以进行生产部署！{Colors.ENDC}")
    elif success_rate >= 60:
        print(f"\n⚠️  {Colors.YELLOW}系统基本可用，建议修复失败项后再部署{Colors.ENDC}")
    else:
        print(f"\n🚨 {Colors.RED}系统存在严重问题，需要修复后才能部署{Colors.ENDC}")

if __name__ == "__main__":
    run_comprehensive_test()