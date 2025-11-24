"""
性能优化测试脚本
用于验证性能优化效果
"""
import time
import requests
import asyncio
from typing import Dict, List
import statistics

BASE_URL = "http://localhost:8000"

class PerformanceTester:
    """性能测试器"""
    
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.results = {}
    
    def test_api_response_time(self, endpoint: str, name: str, runs: int = 5) -> Dict:
        """
        测试API响应时间
        
        Args:
            endpoint: API端点
            name: 测试名称
            runs: 运行次数
            
        Returns:
            Dict: 测试结果
        """
        print(f"\n📊 测试 {name}...")
        times = []
        
        for i in range(runs):
            start = time.time()
            try:
                response = requests.get(f"{self.base_url}{endpoint}")
                elapsed = (time.time() - start) * 1000  # 转换为毫秒
                times.append(elapsed)
                status = "✅" if response.status_code == 200 else "❌"
                print(f"  运行 {i+1}/{runs}: {elapsed:.2f}ms {status}")
            except Exception as e:
                print(f"  运行 {i+1}/{runs}: 失败 - {e}")
        
        if times:
            result = {
                'name': name,
                'avg': statistics.mean(times),
                'min': min(times),
                'max': max(times),
                'median': statistics.median(times),
                'runs': len(times)
            }
            self.results[name] = result
            
            print(f"  平均: {result['avg']:.2f}ms")
            print(f"  最小: {result['min']:.2f}ms")
            print(f"  最大: {result['max']:.2f}ms")
            print(f"  中位: {result['median']:.2f}ms")
            
            return result
        return {}
    
    def test_batch_vs_individual(self):
        """对比批量API vs 单独API"""
        print("\n" + "="*60)
        print("🔬 批量API vs 单独API 性能对比")
        print("="*60)
        
        # 测试批量API
        print("\n【批量API】")
        batch_result = self.test_api_response_time('/api/history/all', 'Batch API', runs=10)
        
        # 测试单独API（6个请求）
        print("\n【单独API】")
        individual_endpoints = [
            ('/api/history/bm25/precision', 'BM25 Precision'),
            ('/api/history/bm25/recall', 'BM25 Recall'),
            ('/api/history/bm25/f1', 'BM25 F1'),
            ('/api/history/bm25/ndcg', 'BM25 NDCG'),
            ('/api/history/ragas/precision', 'Ragas Precision'),
            ('/api/history/ragas/recall', 'Ragas Recall'),
        ]
        
        individual_times = []
        for endpoint, name in individual_endpoints:
            result = self.test_api_response_time(endpoint, name, runs=3)
            if result:
                individual_times.append(result['avg'])
        
        # 计算总时间
        total_individual = sum(individual_times) if individual_times else 0
        
        print("\n" + "="*60)
        print("📈 性能对比结果")
        print("="*60)
        if batch_result and individual_times:
            print(f"  批量API耗时:   {batch_result['avg']:.2f}ms")
            print(f"  单独API总耗时: {total_individual:.2f}ms")
            improvement = ((total_individual - batch_result['avg']) / total_individual * 100)
            print(f"  性能提升:      {improvement:.1f}%")
            print(f"  请求数减少:    {len(individual_endpoints)}个 → 1个")
    
    def test_cache_effectiveness(self):
        """测试缓存有效性"""
        print("\n" + "="*60)
        print("🗄️  缓存有效性测试")
        print("="*60)
        
        endpoint = '/api/history/bm25/precision'
        
        # 第一次请求（缓存未命中）
        print("\n第一次请求（缓存未命中）:")
        start = time.time()
        response1 = requests.get(f"{self.base_url}{endpoint}")
        time1 = (time.time() - start) * 1000
        print(f"  耗时: {time1:.2f}ms")
        
        # 第二次请求（缓存命中）
        print("\n第二次请求（缓存命中）:")
        start = time.time()
        response2 = requests.get(f"{self.base_url}{endpoint}")
        time2 = (time.time() - start) * 1000
        print(f"  耗时: {time2:.2f}ms")
        
        # 计算性能提升
        if time1 > 0:
            improvement = ((time1 - time2) / time1 * 100)
            print(f"\n缓存命中后性能提升: {improvement:.1f}%")
            print(f"响应时间减少: {time1 - time2:.2f}ms")
    
    def test_cache_stats(self):
        """测试缓存统计"""
        print("\n" + "="*60)
        print("📊 缓存统计信息")
        print("="*60)
        
        try:
            response = requests.get(f"{self.base_url}/api/cache/stats")
            if response.status_code == 200:
                data = response.json()
                if data['success']:
                    stats = data['data']
                    
                    for cache_name, cache_stats in stats.items():
                        print(f"\n【{cache_name}】")
                        print(f"  缓存项数: {cache_stats['size']}")
                        print(f"  命中次数: {cache_stats['hit_count']}")
                        print(f"  未命中次数: {cache_stats['miss_count']}")
                        print(f"  总请求数: {cache_stats['total_requests']}")
                        print(f"  命中率: {cache_stats['hit_rate']}")
                        print(f"  TTL: {cache_stats['ttl']}秒")
        except Exception as e:
            print(f"  获取缓存统计失败: {e}")
    
    def generate_report(self):
        """生成测试报告"""
        print("\n" + "="*60)
        print("📋 性能测试报告")
        print("="*60)
        
        if self.results:
            print("\n所有测试结果:")
            for name, result in self.results.items():
                print(f"\n  {name}:")
                print(f"    平均响应时间: {result['avg']:.2f}ms")
                print(f"    最快响应: {result['min']:.2f}ms")
                print(f"    最慢响应: {result['max']:.2f}ms")
        
        print("\n" + "="*60)
        print("✅ 测试完成")
        print("="*60)

def main():
    """主测试函数"""
    print("="*60)
    print("🚀 RAG评估系统 - 性能优化测试")
    print("="*60)
    
    tester = PerformanceTester()
    
    # 测试1: 批量API vs 单独API
    tester.test_batch_vs_individual()
    
    # 测试2: 缓存有效性
    tester.test_cache_effectiveness()
    
    # 测试3: 缓存统计
    tester.test_cache_stats()
    
    # 生成报告
    tester.generate_report()
    
    print("\n💡 优化建议:")
    print("  1. 如果缓存命中率低于80%，考虑增加TTL")
    print("  2. 批量API应比单独API快70%以上")
    print("  3. 定期清理过期缓存以释放内存")
    print("  4. 数据更新后记得清除缓存")

if __name__ == "__main__":
    main()

