"""
远程API接口测试脚本

用于测试工作站服务器(192.168.31.248:8080)的所有API端点，
验证是否存在307重定向或CORS问题。

使用方法:
    python tests/test_remote_api.py

测试内容:
    1. 健康检查端点
    2. 用户相关API
    3. 仓库相关API
    4. 分支相关API
    5. 提交相关API
    6. 仓库成员相关API
"""

import requests
import sys
from typing import Dict, List, Tuple
from dataclasses import dataclass
from enum import Enum


class TestStatus(Enum):
    """测试状态枚举"""
    PASS = "通过"
    FAIL = "失败"
    SKIP = "跳过"


@dataclass
class TestResult:
    """测试结果数据类"""
    name: str
    status: TestStatus
    status_code: int = 0
    response_time: float = 0.0
    error_message: str = ""
    has_redirect: bool = False
    redirect_url: str = ""


class RemoteAPITester:
    """
    远程API测试器
    
    测试工作站服务器的所有API端点，检测重定向和CORS问题。
    
    Attributes:
        base_url: API基础URL
        test_results: 测试结果列表
        session: HTTP会话对象
    """
    
    def __init__(self, base_url: str = "http://192.168.31.248:8080"):
        """
        初始化测试器
        
        Args:
            base_url: API基础URL，默认为工作站地址
        """
        self.base_url = base_url.rstrip('/')
        self.test_results: List[TestResult] = []
        self.session = requests.Session()
        # 禁止自动跟随重定向，以便检测307重定向
        self.session.allow_redirects = False
        
    def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        **kwargs
    ) -> Tuple[int, dict, str, bool]:
        """
        发送HTTP请求
        
        Args:
            method: HTTP方法 (GET, POST, PUT, DELETE)
            endpoint: API端点路径
            **kwargs: 额外的请求参数
            
        Returns:
            Tuple[int, dict, str, bool]: (状态码, 响应头, 响应体, 是否有重定向)
        """
        url = f"{self.base_url}{endpoint}"
        try:
            response = self.session.request(method, url, timeout=10, **kwargs)
            
            # 检查是否有重定向 (3xx状态码)
            has_redirect = 300 <= response.status_code < 400
            redirect_url = response.headers.get('Location', '') if has_redirect else ''
            
            return (
                response.status_code,
                dict(response.headers),
                response.text[:500] if response.text else "",
                has_redirect,
                redirect_url
            )
        except requests.exceptions.Timeout:
            return 0, {}, "请求超时", False, ""
        except requests.exceptions.ConnectionError:
            return 0, {}, "连接错误", False, ""
        except Exception as e:
            return 0, {}, str(e), False, ""
    
    def _record_result(
        self, 
        name: str, 
        status: TestStatus, 
        status_code: int = 0,
        error_message: str = "",
        has_redirect: bool = False,
        redirect_url: str = ""
    ):
        """
        记录测试结果
        
        Args:
            name: 测试名称
            status: 测试状态
            status_code: HTTP状态码
            error_message: 错误信息
            has_redirect: 是否有重定向
            redirect_url: 重定向URL
        """
        self.test_results.append(TestResult(
            name=name,
            status=status,
            status_code=status_code,
            error_message=error_message,
            has_redirect=has_redirect,
            redirect_url=redirect_url
        ))
    
    def test_health_check(self):
        """测试健康检查端点"""
        print("\n[测试] 健康检查端点 /health")
        
        status_code, headers, body, has_redirect, redirect_url = self._make_request("GET", "/health")
        
        if has_redirect:
            self._record_result(
                "健康检查 /health",
                TestStatus.FAIL,
                status_code,
                f"检测到重定向到: {redirect_url}",
                True,
                redirect_url
            )
            print(f"  ❌ 失败 - 检测到307重定向到: {redirect_url}")
        elif status_code == 200:
            self._record_result("健康检查 /health", TestStatus.PASS, status_code)
            print(f"  ✅ 通过 - 状态码: {status_code}")
        else:
            self._record_result(
                "健康检查 /health",
                TestStatus.FAIL,
                status_code,
                f"意外的状态码: {status_code}"
            )
            print(f"  ❌ 失败 - 状态码: {status_code}")
    
    def test_user_apis(self):
        """测试用户相关API"""
        print("\n[测试] 用户相关API")
        
        # 测试获取用户列表（不带斜杠）
        endpoints = [
            ("GET", "/api/users", "获取用户列表（无斜杠）"),
            ("GET", "/api/users/", "获取用户列表（有斜杠）"),
        ]
        
        for method, endpoint, description in endpoints:
            status_code, headers, body, has_redirect, redirect_url = self._make_request(method, endpoint)
            
            if has_redirect:
                self._record_result(
                    f"{description} {endpoint}",
                    TestStatus.FAIL,
                    status_code,
                    f"检测到重定向到: {redirect_url}",
                    True,
                    redirect_url
                )
                print(f"  ❌ {description} - 检测到307重定向到: {redirect_url}")
            elif status_code in [200, 401, 403]:
                # 200表示成功，401/403表示需要认证（也是正常的）
                self._record_result(f"{description} {endpoint}", TestStatus.PASS, status_code)
                print(f"  ✅ {description} - 状态码: {status_code}")
            else:
                self._record_result(
                    f"{description} {endpoint}",
                    TestStatus.FAIL,
                    status_code,
                    f"意外的状态码: {status_code}"
                )
                print(f"  ❌ {description} - 状态码: {status_code}")
    
    def test_repository_apis(self):
        """测试仓库相关API"""
        print("\n[测试] 仓库相关API")
        
        endpoints = [
            ("GET", "/api/repositories", "获取仓库列表（无斜杠）"),
            ("GET", "/api/repositories/", "获取仓库列表（有斜杠）"),
            ("GET", "/api/repositories/public", "获取公开仓库"),
        ]
        
        for method, endpoint, description in endpoints:
            status_code, headers, body, has_redirect, redirect_url = self._make_request(method, endpoint)
            
            if has_redirect:
                self._record_result(
                    f"{description} {endpoint}",
                    TestStatus.FAIL,
                    status_code,
                    f"检测到重定向到: {redirect_url}",
                    True,
                    redirect_url
                )
                print(f"  ❌ {description} - 检测到307重定向到: {redirect_url}")
            elif status_code in [200, 401, 403]:
                self._record_result(f"{description} {endpoint}", TestStatus.PASS, status_code)
                print(f"  ✅ {description} - 状态码: {status_code}")
            else:
                self._record_result(
                    f"{description} {endpoint}",
                    TestStatus.FAIL,
                    status_code,
                    f"意外的状态码: {status_code}"
                )
                print(f"  ❌ {description} - 状态码: {status_code}")
    
    def test_branch_apis(self):
        """测试分支相关API"""
        print("\n[测试] 分支相关API")
        
        # 使用repo_id=1进行测试（假设存在）
        endpoints = [
            ("GET", "/api/repositories/1/branches", "获取分支列表（无斜杠）"),
            ("GET", "/api/repositories/1/branches/", "获取分支列表（有斜杠）"),
        ]
        
        for method, endpoint, description in endpoints:
            status_code, headers, body, has_redirect, redirect_url = self._make_request(method, endpoint)
            
            if has_redirect:
                self._record_result(
                    f"{description} {endpoint}",
                    TestStatus.FAIL,
                    status_code,
                    f"检测到重定向到: {redirect_url}",
                    True,
                    redirect_url
                )
                print(f"  ❌ {description} - 检测到307重定向到: {redirect_url}")
            elif status_code in [200, 401, 403, 404]:
                # 404表示仓库不存在，也是正常的
                self._record_result(f"{description} {endpoint}", TestStatus.PASS, status_code)
                print(f"  ✅ {description} - 状态码: {status_code}")
            else:
                self._record_result(
                    f"{description} {endpoint}",
                    TestStatus.FAIL,
                    status_code,
                    f"意外的状态码: {status_code}"
                )
                print(f"  ❌ {description} - 状态码: {status_code}")
    
    def test_commit_apis(self):
        """测试提交相关API"""
        print("\n[测试] 提交相关API")
        
        endpoints = [
            ("GET", "/api/repositories/1/commits", "获取提交列表（无斜杠）"),
            ("GET", "/api/repositories/1/commits/", "获取提交列表（有斜杠）"),
            ("GET", "/api/repositories/1/commits/count", "统计提交数量"),
        ]
        
        for method, endpoint, description in endpoints:
            status_code, headers, body, has_redirect, redirect_url = self._make_request(method, endpoint)
            
            if has_redirect:
                self._record_result(
                    f"{description} {endpoint}",
                    TestStatus.FAIL,
                    status_code,
                    f"检测到重定向到: {redirect_url}",
                    True,
                    redirect_url
                )
                print(f"  ❌ {description} - 检测到307重定向到: {redirect_url}")
            elif status_code in [200, 401, 403, 404]:
                self._record_result(f"{description} {endpoint}", TestStatus.PASS, status_code)
                print(f"  ✅ {description} - 状态码: {status_code}")
            else:
                self._record_result(
                    f"{description} {endpoint}",
                    TestStatus.FAIL,
                    status_code,
                    f"意外的状态码: {status_code}"
                )
                print(f"  ❌ {description} - 状态码: {status_code}")
    
    def test_member_apis(self):
        """测试仓库成员相关API"""
        print("\n[测试] 仓库成员相关API")
        
        endpoints = [
            ("GET", "/api/repositories/1/members", "获取成员列表（无斜杠）"),
            ("GET", "/api/repositories/1/members/", "获取成员列表（有斜杠）"),
        ]
        
        for method, endpoint, description in endpoints:
            status_code, headers, body, has_redirect, redirect_url = self._make_request(method, endpoint)
            
            if has_redirect:
                self._record_result(
                    f"{description} {endpoint}",
                    TestStatus.FAIL,
                    status_code,
                    f"检测到重定向到: {redirect_url}",
                    True,
                    redirect_url
                )
                print(f"  ❌ {description} - 检测到307重定向到: {redirect_url}")
            elif status_code in [200, 401, 403, 404]:
                self._record_result(f"{description} {endpoint}", TestStatus.PASS, status_code)
                print(f"  ✅ {description} - 状态码: {status_code}")
            else:
                self._record_result(
                    f"{description} {endpoint}",
                    TestStatus.FAIL,
                    status_code,
                    f"意外的状态码: {status_code}"
                )
                print(f"  ❌ {description} - 状态码: {status_code}")
    
    def test_cors_headers(self):
        """测试CORS响应头"""
        print("\n[测试] CORS响应头")
        
        # 发送OPTIONS预检请求
        headers = {
            'Origin': 'http://localhost:5173',
            'Access-Control-Request-Method': 'GET',
            'Access-Control-Request-Headers': 'Content-Type, Authorization'
        }
        
        status_code, response_headers, body, has_redirect, redirect_url = self._make_request(
            "OPTIONS", "/api/repositories", headers=headers
        )
        
        cors_headers = [
            'Access-Control-Allow-Origin',
            'Access-Control-Allow-Methods',
            'Access-Control-Allow-Headers'
        ]
        
        missing_headers = [h for h in cors_headers if h not in response_headers]
        
        if missing_headers:
            self._record_result(
                "CORS预检请求",
                TestStatus.FAIL,
                status_code,
                f"缺少CORS响应头: {', '.join(missing_headers)}"
            )
            print(f"  ❌ CORS预检请求 - 缺少响应头: {', '.join(missing_headers)}")
        else:
            self._record_result("CORS预检请求", TestStatus.PASS, status_code)
            print(f"  ✅ CORS预检请求 - 所有响应头正常")
    
    def run_all_tests(self):
        """运行所有测试"""
        print("=" * 60)
        print("开始测试远程API接口")
        print(f"目标服务器: {self.base_url}")
        print("=" * 60)
        
        self.test_health_check()
        self.test_user_apis()
        self.test_repository_apis()
        self.test_branch_apis()
        self.test_commit_apis()
        self.test_member_apis()
        self.test_cors_headers()
        
        self.print_summary()
    
    def print_summary(self):
        """打印测试摘要"""
        print("\n" + "=" * 60)
        print("测试摘要")
        print("=" * 60)
        
        total = len(self.test_results)
        passed = sum(1 for r in self.test_results if r.status == TestStatus.PASS)
        failed = sum(1 for r in self.test_results if r.status == TestStatus.FAIL)
        redirect_issues = sum(1 for r in self.test_results if r.has_redirect)
        
        print(f"总测试数: {total}")
        print(f"通过: {passed}")
        print(f"失败: {failed}")
        print(f"重定向问题: {redirect_issues}")
        
        if redirect_issues > 0:
            print("\n⚠️  发现重定向问题（可能导致CORS错误）:")
            for result in self.test_results:
                if result.has_redirect:
                    print(f"  - {result.name}")
                    print(f"    重定向到: {result.redirect_url}")
        
        if failed > 0:
            print("\n❌ 失败的测试:")
            for result in self.test_results:
                if result.status == TestStatus.FAIL:
                    print(f"  - {result.name}")
                    print(f"    状态码: {result.status_code}")
                    print(f"    错误: {result.error_message}")
        
        print("\n" + "=" * 60)
        
        # 返回退出码
        return 0 if failed == 0 else 1


def main():
    """主函数"""
    tester = RemoteAPITester()
    exit_code = tester.run_all_tests()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
