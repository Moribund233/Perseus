"""
服务端压力测试脚本

用于测试服务端在高并发情况下的性能表现
"""

import asyncio
import httpx
import time
import statistics
import argparse
from typing import List, Dict, Any


class StressTest:
    """
    压力测试类
    
    测试服务端 API 在高并发下的响应性能
    """
    
    def __init__(self, base_url: str = "http://127.0.0.1:8000", token: str = None):
        """
        初始化压力测试
        
        Args:
            base_url: 服务端基础URL
            token: 认证令牌（可选）
        """
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.results: List[Dict[str, Any]] = []
        
    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers
    
    async def _make_request(
        self, 
        client: httpx.AsyncClient, 
        endpoint: str, 
        method: str = "GET",
        data: Dict = None
    ) -> Dict[str, Any]:
        """
        发送单个请求
        
        Args:
            client: httpx异步客户端
            endpoint: API端点
            method: HTTP方法
            data: 请求数据
            
        Returns:
            请求结果字典
        """
        url = f"{self.base_url}{endpoint}"
        start_time = time.time()
        
        try:
            if method == "GET":
                response = await client.get(url, headers=self._get_headers())
            elif method == "POST":
                response = await client.post(
                    url, 
                    headers=self._get_headers(),
                    json=data
                )
            else:
                return {
                    "endpoint": endpoint,
                    "method": method,
                    "status": 0,
                    "elapsed": 0,
                    "success": False,
                    "error": "不支持的HTTP方法"
                }
                
            elapsed = time.time() - start_time
            return {
                "endpoint": endpoint,
                "method": method,
                "status": response.status_code,
                "elapsed": elapsed,
                "success": 200 <= response.status_code < 300,
                "error": None
            }
        except Exception as e:
            elapsed = time.time() - start_time
            return {
                "endpoint": endpoint,
                "method": method,
                "status": 0,
                "elapsed": elapsed,
                "success": False,
                "error": str(e)
            }
    
    async def run_concurrent_requests(
        self, 
        endpoint: str, 
        method: str = "GET",
        data: Dict = None,
        concurrent: int = 100,
        total: int = 1000
    ) -> Dict[str, Any]:
        """
        运行并发请求测试
        
        Args:
            endpoint: API端点
            method: HTTP方法
            data: 请求数据
            concurrent: 并发数
            total: 总请求数
            
        Returns:
            测试结果统计
        """
        print(f"\n开始测试: {method} {endpoint}")
        print(f"并发数: {concurrent}, 总请求数: {total}")
        
        # 创建连接池
        limits = httpx.Limits(max_connections=concurrent, max_keepalive_connections=concurrent)
        timeout = httpx.Timeout(30.0)
        
        async with httpx.AsyncClient(limits=limits, timeout=timeout) as client:
            tasks = []
            for i in range(total):
                task = self._make_request(client, endpoint, method, data)
                tasks.append(task)
                
                # 控制并发数
                if len(tasks) >= concurrent:
                    results = await asyncio.gather(*tasks)
                    self.results.extend(results)
                    tasks = []
            
            # 处理剩余任务
            if tasks:
                results = await asyncio.gather(*tasks)
                self.results.extend(results)
        
        return self._calculate_stats(endpoint)
    
    def _calculate_stats(self, endpoint: str) -> Dict[str, Any]:
        """
        计算统计信息
        
        Args:
            endpoint: API端点
            
        Returns:
            统计结果
        """
        endpoint_results = [r for r in self.results if r["endpoint"] == endpoint]
        
        if not endpoint_results:
            return {}
        
        successful = [r for r in endpoint_results if r["success"]]
        failed = [r for r in endpoint_results if not r["success"]]
        
        if successful:
            latencies = [r["elapsed"] for r in successful]
            avg_latency = statistics.mean(latencies)
            min_latency = min(latencies)
            max_latency = max(latencies)
            p50 = statistics.median(latencies)
            p95 = sorted(latencies)[int(len(latencies) * 0.95)] if len(latencies) > 1 else latencies[0]
            p99 = sorted(latencies)[int(len(latencies) * 0.99)] if len(latencies) > 1 else latencies[0]
        else:
            avg_latency = min_latency = max_latency = p50 = p95 = p99 = 0
        
        total_time = sum(r["elapsed"] for r in endpoint_results)
        
        stats = {
            "endpoint": endpoint,
            "total_requests": len(endpoint_results),
            "successful": len(successful),
            "failed": len(failed),
            "success_rate": len(successful) / len(endpoint_results) * 100,
            "avg_latency_ms": avg_latency * 1000,
            "min_latency_ms": min_latency * 1000,
            "max_latency_ms": max_latency * 1000,
            "p50_latency_ms": p50 * 1000,
            "p95_latency_ms": p95 * 1000,
            "p99_latency_ms": p99 * 1000,
            "total_time_s": total_time,
            "requests_per_second": len(endpoint_results) / total_time if total_time > 0 else 0
        }
        
        return stats
    
    def print_stats(self, stats: Dict[str, Any]):
        """打印统计结果"""
        print(f"\n{'='*60}")
        print(f"测试结果: {stats['endpoint']}")
        print(f"{'='*60}")
        print(f"总请求数: {stats['total_requests']}")
        print(f"成功请求: {stats['successful']}")
        print(f"失败请求: {stats['failed']}")
        print(f"成功率: {stats['success_rate']:.2f}%")
        print(f"\n延迟统计 (ms):")
        print(f"  平均: {stats['avg_latency_ms']:.2f}")
        print(f"  最小: {stats['min_latency_ms']:.2f}")
        print(f"  最大: {stats['max_latency_ms']:.2f}")
        print(f"  P50:  {stats['p50_latency_ms']:.2f}")
        print(f"  P95:  {stats['p95_latency_ms']:.2f}")
        print(f"  P99:  {stats['p99_latency_ms']:.2f}")
        print(f"\n吞吐量:")
        print(f"  总耗时: {stats['total_time_s']:.2f}s")
        print(f"  QPS: {stats['requests_per_second']:.2f}")
        print(f"{'='*60}\n")


async def run_extreme_test(base_url: str):
    """
    极限压力测试 - 高并发场景
    
    Args:
        base_url: 服务端基础URL
    """
    print("\n" + "="*60)
    print("极限压力测试 - 高并发场景")
    print("="*60)
    
    # 配置1: 超高并发
    CONCURRENT_USERS = 200
    TOTAL_REQUESTS = 2000
    
    print(f"\n配置: 并发数={CONCURRENT_USERS}, 总请求数={TOTAL_REQUESTS}")
    
    tester = StressTest(base_url=base_url)
    
    # 测试1: 根路由
    stats = await tester.run_concurrent_requests(
        endpoint="/",
        method="GET",
        concurrent=CONCURRENT_USERS,
        total=TOTAL_REQUESTS
    )
    tester.print_stats(stats)
    
    # 测试2: 健康检查端点
    tester.results = []
    stats = await tester.run_concurrent_requests(
        endpoint="/health",
        method="GET",
        concurrent=CONCURRENT_USERS,
        total=TOTAL_REQUESTS
    )
    tester.print_stats(stats)


async def run_sustained_test(base_url: str, duration_seconds: int = 30):
    """
    持续压力测试 - 长时间保持高负载
    
    Args:
        base_url: 服务端基础URL
        duration_seconds: 测试持续时间（秒）
    """
    print("\n" + "="*60)
    print(f"持续压力测试 - {duration_seconds}秒高负载")
    print("="*60)
    
    CONCURRENT_USERS = 100
    
    print(f"\n配置: 并发数={CONCURRENT_USERS}, 持续时间={duration_seconds}秒")
    
    tester = StressTest(base_url=base_url)
    
    limits = httpx.Limits(max_connections=CONCURRENT_USERS, max_keepalive_connections=CONCURRENT_USERS)
    timeout = httpx.Timeout(30.0)
    
    start_time = time.time()
    request_count = 0
    success_count = 0
    error_count = 0
    latencies = []
    
    async with httpx.AsyncClient(limits=limits, timeout=timeout) as client:
        while time.time() - start_time < duration_seconds:
            tasks = []
            for _ in range(CONCURRENT_USERS):
                task = tester._make_request(client, "/health", "GET")
                tasks.append(task)
            
            results = await asyncio.gather(*tasks)
            
            for r in results:
                request_count += 1
                if r["success"]:
                    success_count += 1
                    latencies.append(r["elapsed"])
                else:
                    error_count += 1
    
    elapsed_total = time.time() - start_time
    
    print(f"\n{'='*60}")
    print(f"持续压力测试结果")
    print(f"{'='*60}")
    print(f"持续时间: {elapsed_total:.2f}秒")
    print(f"总请求数: {request_count}")
    print(f"成功请求: {success_count}")
    print(f"失败请求: {error_count}")
    print(f"成功率: {(success_count/request_count*100):.2f}%")
    
    if latencies:
        avg_latency = statistics.mean(latencies)
        print(f"\n延迟统计 (ms):")
        print(f"  平均: {avg_latency*1000:.2f}")
        print(f"  最小: {min(latencies)*1000:.2f}")
        print(f"  最大: {max(latencies)*1000:.2f}")
    
    print(f"\n吞吐量:")
    print(f"  QPS: {request_count/elapsed_total:.2f}")
    print(f"{'='*60}\n")


async def main():
    """
    主函数
    运行压力测试
    """
    parser = argparse.ArgumentParser(description="Perseus 服务端压力测试")
    parser.add_argument("--mode", choices=["normal", "extreme", "sustained"], 
                        default="normal", help="测试模式")
    parser.add_argument("--url", default="http://127.0.0.1:8000", help="服务端地址")
    parser.add_argument("--duration", type=int, default=30, help="持续测试时间（秒）")
    
    args = parser.parse_args()
    
    print("="*60)
    print("Perseus 服务端压力测试")
    print("="*60)
    print(f"目标地址: {args.url}")
    print(f"测试模式: {args.mode}")
    
    if args.mode == "extreme":
        await run_extreme_test(args.url)
    elif args.mode == "sustained":
        await run_sustained_test(args.url, args.duration)
    else:
        # 普通测试
        CONCURRENT_USERS = 50
        TOTAL_REQUESTS = 500
        
        print(f"并发数: {CONCURRENT_USERS}")
        print(f"总请求数: {TOTAL_REQUESTS}")
        
        tester = StressTest(base_url=args.url)
        
        # 测试1: 根路由
        stats = await tester.run_concurrent_requests(
            endpoint="/",
            method="GET",
            concurrent=CONCURRENT_USERS,
            total=TOTAL_REQUESTS
        )
        tester.print_stats(stats)
        
        # 测试2: 健康检查端点
        tester.results = []
        stats = await tester.run_concurrent_requests(
            endpoint="/health",
            method="GET",
            concurrent=CONCURRENT_USERS,
            total=TOTAL_REQUESTS
        )
        tester.print_stats(stats)
        
        # 测试3: 应用状态端点
        tester.results = []
        stats = await tester.run_concurrent_requests(
            endpoint="/api/app/status",
            method="GET",
            concurrent=CONCURRENT_USERS,
            total=TOTAL_REQUESTS
        )
        tester.print_stats(stats)
    
    print("\n压力测试完成!")


if __name__ == "__main__":
    asyncio.run(main())
