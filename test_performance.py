#!/usr/bin/env python3
"""
AI Safety Lab - 性能压力测试
测试系统在负载下的性能表现
"""

import asyncio
import aiohttp
import time
import statistics
from concurrent.futures import ThreadPoolExecutor
import threading
import json

class PerformanceTest:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.results = {
            'response_times': [],
            'success_count': 0,
            'error_count': 0,
            'errors': []
        }
        self.lock = threading.Lock()
    
    def add_result(self, response_time, success, error=None):
        """线程安全地添加测试结果"""
        with self.lock:
            if success:
                self.results['response_times'].append(response_time)
                self.results['success_count'] += 1
            else:
                self.results['error_count'] += 1
                if error:
                    self.results['errors'].append(str(error))
    
    async def test_endpoint(self, session, endpoint="/api/health"):
        """异步测试单个端点"""
        start_time = time.time()
        try:
            async with session.get(f"{self.base_url}{endpoint}") as response:
                response_time = time.time() - start_time
                success = response.status == 200
                self.add_result(response_time, success)
                return success
        except Exception as e:
            response_time = time.time() - start_time
            self.add_result(response_time, False, e)
            return False
    
    async def concurrent_test(self, concurrent_users=10, requests_per_user=10):
        """并发测试"""
        print(f"🚀 开始并发测试: {concurrent_users} 并发用户, 每用户 {requests_per_user} 请求")
        
        async with aiohttp.ClientSession() as session:
            tasks = []
            for _ in range(concurrent_users):
                for _ in range(requests_per_user):
                    task = asyncio.create_task(self.test_endpoint(session))
                    tasks.append(task)
            
            start_time = time.time()
            await asyncio.gather(*tasks)
            total_time = time.time() - start_time
            
            return total_time
    
    def test_api_security_endpoints(self):
        """测试AI安全相关的API端点"""
        print("🔒 测试AI安全API端点...")
        
        import requests
        
        endpoints = [
            "/api/health",
            "/api/agents", 
            "/docs",
        ]
        
        for endpoint in endpoints:
            try:
                start_time = time.time()
                response = requests.get(f"{self.base_url}{endpoint}", timeout=10)
                response_time = time.time() - start_time
                
                success = response.status_code == 200
                self.add_result(response_time, success)
                
                status = "✅" if success else "❌"
                print(f"  {status} {endpoint} - {response_time*1000:.0f}ms")
                
            except Exception as e:
                self.add_result(1.0, False, e)
                print(f"  ❌ {endpoint} - 错误: {e}")
    
    def generate_report(self, total_time):
        """生成性能测试报告"""
        if not self.results['response_times']:
            print("❌ 没有成功的请求数据")
            return
        
        response_times = self.results['response_times']
        total_requests = self.results['success_count'] + self.results['error_count']
        
        print("\n" + "="*60)
        print("🏁 性能测试报告")
        print("="*60)
        
        # 基本统计
        print(f"总请求数: {total_requests}")
        print(f"成功请求: {self.results['success_count']}")
        print(f"失败请求: {self.results['error_count']}")
        print(f"成功率: {self.results['success_count']/total_requests*100:.1f}%")
        print(f"总耗时: {total_time:.2f}秒")
        
        # 性能指标
        if response_times:
            print(f"\n📊 响应时间统计:")
            print(f"平均响应时间: {statistics.mean(response_times)*1000:.0f}ms")
            print(f"最小响应时间: {min(response_times)*1000:.0f}ms")
            print(f"最大响应时间: {max(response_times)*1000:.0f}ms")
            print(f"95%响应时间: {sorted(response_times)[int(len(response_times)*0.95)]*1000:.0f}ms")
            print(f"QPS (每秒请求数): {len(response_times)/total_time:.1f}")
        
        # 错误统计
        if self.results['errors']:
            print(f"\n❌ 错误统计:")
            error_counts = {}
            for error in self.results['errors']:
                error_counts[error] = error_counts.get(error, 0) + 1
            
            for error, count in error_counts.items():
                print(f"  {error}: {count}次")
        
        # 性能评估
        if response_times:
            avg_response = statistics.mean(response_times) * 1000
            qps = len(response_times) / total_time
            success_rate = self.results['success_count'] / total_requests * 100
            
            print(f"\n🎯 性能评估:")
            if avg_response < 100:
                print("✅ 响应时间: 优秀 (<100ms)")
            elif avg_response < 500:
                print("✅ 响应时间: 良好 (<500ms)")
            elif avg_response < 1000:
                print("⚠️  响应时间: 一般 (<1000ms)")
            else:
                print("❌ 响应时间: 需要优化 (>1000ms)")
            
            if qps > 100:
                print("✅ 吞吐量: 优秀 (>100 QPS)")
            elif qps > 50:
                print("✅ 吞吐量: 良好 (>50 QPS)")
            elif qps > 10:
                print("⚠️  吞吐量: 一般 (>10 QPS)")
            else:
                print("❌ 吞吐量: 需要优化 (<10 QPS)")
            
            if success_rate >= 99.5:
                print("✅ 可靠性: 优秀 (≥99.5%)")
            elif success_rate >= 99:
                print("✅ 可靠性: 良好 (≥99%)")
            elif success_rate >= 95:
                print("⚠️  可靠性: 一般 (≥95%)")
            else:
                print("❌ 可靠性: 需要改进 (<95%)")

async def main():
    print("🧪 AI Safety Lab 性能压力测试")
    print("="*50)
    
    # 检查服务是否可用
    import requests
    try:
        response = requests.get("http://localhost:8000/api/health", timeout=5)
        if response.status_code != 200:
            print("❌ 后端服务不可用，请先启动服务")
            return
    except Exception as e:
        print(f"❌ 无法连接到后端服务: {e}")
        print("请确保服务正在运行在 http://localhost:8000")
        return
    
    tester = PerformanceTest()
    
    # 测试API端点
    tester.test_api_security_endpoints()
    
    # 并发性能测试
    test_scenarios = [
        (5, 10),   # 轻负载
        (10, 20),  # 中负载
        (20, 10),  # 高并发
    ]
    
    for concurrent_users, requests_per_user in test_scenarios:
        print(f"\n🔄 测试场景: {concurrent_users}并发用户 x {requests_per_user}请求")
        
        scenario_tester = PerformanceTest()
        total_time = await scenario_tester.concurrent_test(concurrent_users, requests_per_user)
        
        print(f"完成时间: {total_time:.2f}秒")
        print(f"成功请求: {scenario_tester.results['success_count']}")
        print(f"失败请求: {scenario_tester.results['error_count']}")
        
        # 合并结果到主测试器
        tester.results['response_times'].extend(scenario_tester.results['response_times'])
        tester.results['success_count'] += scenario_tester.results['success_count']
        tester.results['error_count'] += scenario_tester.results['error_count']
        tester.results['errors'].extend(scenario_tester.results['errors'])
    
    # 生成最终报告
    total_test_time = sum([rt for rt in tester.results['response_times']])
    tester.generate_report(total_test_time)
    
    print(f"\n💡 建议:")
    print("- 如果响应时间过长，考虑增加资源或优化代码")
    print("- 如果错误率过高，检查服务配置和依赖")
    print("- 在生产环境中建议进行更大规模的压力测试")

if __name__ == "__main__":
    asyncio.run(main())