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
    7. Issue相关API
    8. Pull Request相关API
    9. 仓库浏览器相关API
    10. Git HTTP相关API
    11. 带请求体的接口测试
"""

import requests
import sys
import json
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
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
    response_body: str = ""


class RemoteAPITester:
    """
    远程API测试器
    
    测试工作站服务器的所有API端点，检测重定向和CORS问题。
    
    Attributes:
        base_url: API基础URL
        test_results: 测试结果列表
        session: HTTP会话对象
        auth_token: 认证令牌
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
        self.auth_token: Optional[str] = None
        self.test_user_id: Optional[int] = None
        self.test_repo_id: Optional[int] = None
        
    def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        **kwargs
    ) -> Tuple[int, dict, str, bool, str]:
        """
        发送HTTP请求
        
        Args:
            method: HTTP方法 (GET, POST, PUT, DELETE)
            endpoint: API端点路径
            **kwargs: 额外的请求参数
            
        Returns:
            Tuple[int, dict, str, bool, str]: (状态码, 响应头, 响应体, 是否有重定向, 重定向URL)
        """
        url = f"{self.base_url}{endpoint}"
        
        # 添加认证头
        if self.auth_token and 'headers' not in kwargs:
            kwargs['headers'] = {}
        if self.auth_token and kwargs.get('headers') is not None:
            kwargs['headers']['Authorization'] = f"Bearer {self.auth_token}"
        
        try:
            response = self.session.request(method, url, timeout=10, **kwargs)
            
            # 检查是否有重定向 (3xx状态码)
            has_redirect = 300 <= response.status_code < 400
            redirect_url = response.headers.get('Location', '') if has_redirect else ''
            
            return (
                response.status_code,
                dict(response.headers),
                response.text[:1000] if response.text else "",
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
        redirect_url: str = "",
        response_body: str = ""
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
            response_body: 响应体
        """
        self.test_results.append(TestResult(
            name=name,
            status=status,
            status_code=status_code,
            error_message=error_message,
            has_redirect=has_redirect,
            redirect_url=redirect_url,
            response_body=response_body
        ))
    
    def _test_endpoint(self, method: str, endpoint: str, description: str, 
                       valid_codes=None, json_data=None, params=None):
        """
        通用端点测试方法
        
        Args:
            method: HTTP方法
            endpoint: API端点
            description: 测试描述
            valid_codes: 有效的状态码列表，默认为[200, 401, 403, 404]
            json_data: JSON请求体
            params: URL查询参数
        """
        if valid_codes is None:
            valid_codes = [200, 201, 401, 403, 404]
        
        kwargs = {}
        if json_data:
            kwargs['json'] = json_data
        if params:
            kwargs['params'] = params
            
        status_code, headers, body, has_redirect, redirect_url = self._make_request(
            method, endpoint, **kwargs
        )
        
        if has_redirect:
            self._record_result(
                f"{description} {endpoint}",
                TestStatus.FAIL,
                status_code,
                f"检测到重定向到: {redirect_url}",
                True,
                redirect_url,
                body
            )
            print(f"  ❌ {description} - 检测到307重定向到: {redirect_url}")
        elif status_code in valid_codes:
            self._record_result(f"{description} {endpoint}", TestStatus.PASS, status_code, response_body=body)
            print(f"  ✅ {description} - 状态码: {status_code}")
        else:
            error_msg = f"意外的状态码: {status_code}"
            if body:
                try:
                    error_detail = json.loads(body)
                    if 'detail' in error_detail:
                        error_msg += f", 详情: {error_detail['detail']}"
                except:
                    pass
            self._record_result(
                f"{description} {endpoint}",
                TestStatus.FAIL,
                status_code,
                error_msg,
                response_body=body
            )
            print(f"  ❌ {description} - {error_msg}")
    
    def test_health_check(self):
        """测试健康检查端点"""
        print("\n[测试] 健康检查端点 /health")
        self._test_endpoint("GET", "/health", "健康检查", [200])
    
    def test_user_apis(self):
        """测试用户相关API"""
        print("\n[测试] 用户相关API")
        
        endpoints = [
            ("GET", "/api/users", "获取用户列表（无斜杠）"),
            ("GET", "/api/users/", "获取用户列表（有斜杠）"),
            ("GET", "/api/users/1", "获取指定用户"),
        ]
        
        for method, endpoint, description in endpoints:
            self._test_endpoint(method, endpoint, description)
    
    def test_user_apis_with_body(self):
        """测试带请求体的用户API"""
        print("\n[测试] 用户相关API (带请求体)")
        
        # 测试创建用户
        self._test_endpoint(
            "POST", "/api/users/", "创建用户",
            json_data={
                "username": "testuser_api",
                "email": "test_api@example.com",
                "password": "Test123456!"
            }
        )
        
        # 测试更新用户
        self._test_endpoint(
            "PUT", "/api/users/1", "更新用户",
            json_data={
                "username": "updated_user",
                "email": "updated@example.com"
            }
        )
        
        # 测试用户登录
        self._test_endpoint(
            "POST", "/api/users/login", "用户登录",
            json_data={
                "username": "admin",
                "password": "admin123"
            }
        )
    
    def test_repository_apis(self):
        """测试仓库相关API"""
        print("\n[测试] 仓库相关API")

        endpoints = [
            ("GET", "/api/repositories", "获取仓库列表（无斜杠）"),
            ("GET", "/api/repositories/", "获取仓库列表（有斜杠）"),
            ("GET", "/api/repositories/public", "获取公开仓库"),
            ("GET", "/api/repositories/user/1", "获取用户仓库"),
            ("GET", "/api/repositories/1", "获取指定仓库"),
            ("DELETE", "/api/repositories/1", "删除仓库"),
        ]

        for method, endpoint, description in endpoints:
            self._test_endpoint(method, endpoint, description)
    
    def test_repository_apis_with_body(self):
        """测试带请求体的仓库API"""
        print("\n[测试] 仓库相关API (带请求体)")
        
        # 测试创建仓库 - 需要owner_id字段
        self._test_endpoint(
            "POST", "/api/repositories/", "创建仓库",
            json_data={
                "name": "test-repo-api",
                "path": "/tmp/test-repo-api",
                "description": "Test repository created via API",
                "is_public": True,
                "owner_id": 1
            }
        )
        
        # 测试更新仓库
        self._test_endpoint(
            "PUT", "/api/repositories/1", "更新仓库",
            json_data={
                "name": "updated-repo",
                "description": "Updated description"
            }
        )
        
        # 测试检查仓库访问权限 - 需要user_id查询参数
        self._test_endpoint(
            "GET", "/api/repositories/1/access", "检查仓库访问权限",
            params={"user_id": 1, "permission": "read"}
        )

    def test_branch_apis(self):
        """测试分支相关API"""
        print("\n[测试] 分支相关API")
        
        endpoints = [
            ("GET", "/api/repositories/1/branches", "获取分支列表（无斜杠）"),
            ("GET", "/api/repositories/1/branches/", "获取分支列表（有斜杠）"),
            ("GET", "/api/repositories/1/branches/default", "获取默认分支"),
            ("GET", "/api/repositories/1/branches/main", "获取指定分支"),
            ("DELETE", "/api/repositories/1/branches/feature", "删除分支"),
            ("PUT", "/api/repositories/1/branches/main/default", "设置默认分支"),
            ("PUT", "/api/repositories/1/branches/main/protect", "保护分支"),
            ("PUT", "/api/repositories/1/branches/main/unprotect", "取消保护分支"),
            ("GET", "/api/repositories/1/branches/main/protection", "获取分支保护状态"),
        ]
        
        for method, endpoint, description in endpoints:
            self._test_endpoint(method, endpoint, description)
    
    def test_branch_apis_with_body(self):
        """测试带请求体的分支API"""
        print("\n[测试] 分支相关API (带请求体)")
        
        # 测试创建分支
        self._test_endpoint(
            "POST", "/api/repositories/1/branches", "创建分支",
            json_data={
                "name": "feature/test-branch",
                "base_branch": "main"
            }
        )
        
        # 测试更新分支
        self._test_endpoint(
            "PUT", "/api/repositories/1/branches/main", "更新分支",
            json_data={
                "description": "Updated branch description"
            }
        )
    
    def test_commit_apis(self):
        """测试提交相关API"""
        print("\n[测试] 提交相关API")
        
        endpoints = [
            ("GET", "/api/repositories/1/commits", "获取提交列表（无斜杠）"),
            ("GET", "/api/repositories/1/commits/", "获取提交列表（有斜杠）"),
            ("GET", "/api/repositories/1/commits/history", "获取提交历史"),
            ("GET", "/api/repositories/1/commits/count", "统计提交数量"),
            ("GET", "/api/repositories/1/commits/latest", "获取最新提交"),
            ("GET", "/api/repositories/1/commits/abc123", "获取指定提交"),
            ("GET", "/api/repositories/1/branches/main/commits", "获取分支提交"),
            ("GET", "/api/repositories/1/branches/main/commits/count", "统计分支提交数量"),
        ]
        
        for method, endpoint, description in endpoints:
            self._test_endpoint(method, endpoint, description)
    
    def test_commit_apis_with_params(self):
        """测试带查询参数的提交API"""
        print("\n[测试] 提交相关API (带查询参数)")
        
        # 测试搜索提交
        self._test_endpoint(
            "GET", "/api/repositories/1/commits/search", "搜索提交",
            params={"query": "initial commit"}
        )
        
        # 测试按作者获取提交 - 需要author_email参数
        self._test_endpoint(
            "GET", "/api/repositories/1/commits/author", "按作者获取提交",
            params={"author_email": "admin@example.com"}
        )
    
    def test_commit_apis_with_body(self):
        """测试带请求体的提交API"""
        print("\n[测试] 提交相关API (带请求体)")
        
        # 测试创建提交 - 需要hash字段
        self._test_endpoint(
            "POST", "/api/repositories/1/commits", "创建提交",
            json_data={
                "hash": "abc123def456",
                "message": "Test commit via API",
                "files": [
                    {"path": "test.txt", "content": "Test content"}
                ],
                "branch": "main"
            }
        )
    
    def test_member_apis(self):
        """测试仓库成员相关API"""
        print("\n[测试] 仓库成员相关API")
        
        endpoints = [
            ("GET", "/api/repositories/1/members", "获取成员列表（无斜杠）"),
            ("GET", "/api/repositories/1/members/", "获取成员列表（有斜杠）"),
            ("GET", "/api/repositories/1/members/1", "获取指定成员"),
            ("DELETE", "/api/repositories/1/members/1", "删除成员"),
            ("PUT", "/api/repositories/1/members/1/activate", "激活成员"),
            ("PUT", "/api/repositories/1/members/1/deactivate", "停用成员"),
        ]
        
        for method, endpoint, description in endpoints:
            self._test_endpoint(method, endpoint, description)
    
    def test_member_apis_with_body(self):
        """测试带请求体的成员API"""
        print("\n[测试] 仓库成员相关API (带请求体)")
        
        # 测试添加成员 - 使用正确的角色值: owner, admin, developer, readonly
        self._test_endpoint(
            "POST", "/api/repositories/1/members", "添加成员",
            json_data={
                "user_id": 2,
                "role": "developer"
            }
        )
        
        # 测试更新成员 - 使用正确的角色值
        self._test_endpoint(
            "PUT", "/api/repositories/1/members/1", "更新成员",
            json_data={
                "role": "admin"
            }
        )
        
        # 测试更新成员角色 - 使用正确的角色值
        self._test_endpoint(
            "PUT", "/api/repositories/1/members/1/role", "更新成员角色",
            json_data={
                "role": "developer"
            }
        )
        
        # 测试获取成员权限 - 需要permission查询参数
        self._test_endpoint(
            "GET", "/api/repositories/1/members/1/permission", "获取成员权限",
            params={"permission": "push"}
        )
    
    def test_issue_apis(self):
        """测试Issue相关API"""
        print("\n[测试] Issue相关API")
        
        endpoints = [
            ("GET", "/api/repositories/1/issues", "获取Issue列表"),
            ("GET", "/api/repositories/1/issues/1", "获取指定Issue"),
            ("GET", "/api/repositories/1/issues/1/comments", "获取Issue评论"),
            ("GET", "/api/repositories/1/labels", "获取标签列表"),
            ("DELETE", "/api/repositories/1/labels/1", "删除标签"),
        ]
        
        for method, endpoint, description in endpoints:
            self._test_endpoint(method, endpoint, description)
    
    def test_issue_apis_with_body(self):
        """测试带请求体的Issue API"""
        print("\n[测试] Issue相关API (带请求体)")
        
        # 测试创建Issue
        self._test_endpoint(
            "POST", "/api/repositories/1/issues", "创建Issue",
            json_data={
                "title": "Test Issue from API",
                "description": "This is a test issue created via API",
                "priority": "high"
            }
        )
        
        # 测试更新Issue
        self._test_endpoint(
            "PATCH", "/api/repositories/1/issues/1", "更新Issue",
            json_data={
                "title": "Updated Issue Title",
                "status": "in_progress"
            }
        )
        
        # 测试关闭Issue
        self._test_endpoint(
            "POST", "/api/repositories/1/issues/1/close", "关闭Issue",
            json_data={}
        )
        
        # 测试重新打开Issue
        self._test_endpoint(
            "POST", "/api/repositories/1/issues/1/reopen", "重新打开Issue",
            json_data={}
        )
        
        # 测试创建Issue评论
        self._test_endpoint(
            "POST", "/api/repositories/1/issues/1/comments", "创建Issue评论",
            json_data={
                "content": "This is a test comment"
            }
        )
        
        # 测试创建标签
        self._test_endpoint(
            "POST", "/api/repositories/1/labels", "创建标签",
            json_data={
                "name": "bug",
                "color": "#ff0000",
                "description": "Bug label"
            }
        )
        
        # 测试更新标签
        self._test_endpoint(
            "PATCH", "/api/repositories/1/labels/1", "更新标签",
            json_data={
                "name": "feature",
                "color": "#00ff00"
            }
        )
    
    def test_pull_request_apis(self):
        """测试Pull Request相关API"""
        print("\n[测试] Pull Request相关API")
        
        endpoints = [
            ("GET", "/api/repositories/1/pull-requests", "获取PR列表"),
            ("GET", "/api/repositories/1/pull-requests/1", "获取指定PR"),
            ("GET", "/api/repositories/1/pull-requests/1/comments", "获取PR评论"),
        ]
        
        for method, endpoint, description in endpoints:
            self._test_endpoint(method, endpoint, description)
    
    def test_pull_request_apis_with_body(self):
        """测试带请求体的Pull Request API"""
        print("\n[测试] Pull Request相关API (带请求体)")
        
        # 测试创建PR
        self._test_endpoint(
            "POST", "/api/repositories/1/pull-requests", "创建PR",
            json_data={
                "title": "Test PR from API",
                "description": "This is a test PR",
                "source_branch": "feature/test",
                "target_branch": "main"
            }
        )
        
        # 测试更新PR
        self._test_endpoint(
            "PATCH", "/api/repositories/1/pull-requests/1", "更新PR",
            json_data={
                "title": "Updated PR Title",
                "description": "Updated description"
            }
        )
        
        # 测试关闭PR
        self._test_endpoint(
            "POST", "/api/repositories/1/pull-requests/1/close", "关闭PR",
            json_data={}
        )
        
        # 测试合并PR
        self._test_endpoint(
            "POST", "/api/repositories/1/pull-requests/1/merge", "合并PR",
            json_data={
                "merge_method": "merge",
                "commit_message": "Merge pull request"
            }
        )
        
        # 测试创建PR评论
        self._test_endpoint(
            "POST", "/api/repositories/1/pull-requests/1/comments", "创建PR评论",
            json_data={
                "content": "This is a PR comment"
            }
        )
        
        # 测试创建PR审查
        self._test_endpoint(
            "POST", "/api/repositories/1/pull-requests/1/reviews", "创建PR审查",
            json_data={
                "status": "approved",
                "comment": "LGTM!"
            }
        )
    
    def test_repository_browser_apis(self):
        """测试仓库浏览器相关API"""
        print("\n[测试] 仓库浏览器相关API")
        
        endpoints = [
            ("GET", "/api/repositories/1/tree", "获取文件树"),
            ("GET", "/api/repositories/1/commits", "获取提交列表"),
        ]
        
        for method, endpoint, description in endpoints:
            self._test_endpoint(method, endpoint, description)
    
    def test_repository_browser_apis_with_params(self):
        """测试带查询参数的仓库浏览器API"""
        print("\n[测试] 仓库浏览器相关API (带查询参数)")
        
        # 测试获取指定路径文件树
        self._test_endpoint(
            "GET", "/api/repositories/1/tree", "获取指定路径文件树",
            params={"path": "src"}
        )
        
        # 测试获取文件内容
        self._test_endpoint(
            "GET", "/api/repositories/1/blob", "获取文件内容",
            params={"path": "README.md"}
        )
        
        # 测试获取指定文件内容
        self._test_endpoint(
            "GET", "/api/repositories/1/blob", "获取指定文件内容（带ref）",
            params={"path": "README.md", "ref": "main"}
        )
        
        # 测试获取diff
        self._test_endpoint(
            "GET", "/api/repositories/1/diff", "获取diff",
            params={
                "base": "main",
                "head": "feature/test"
            }
        )
    
    def test_git_http_apis(self):
        """测试Git HTTP相关API"""
        print("\n[测试] Git HTTP相关API")
        
        endpoints = [
            ("GET", "/git/test-repo/info/refs?service=git-upload-pack", "Git clone info/refs"),
            ("GET", "/git/test-repo/info/refs?service=git-receive-pack", "Git push info/refs"),
            ("POST", "/git/test-repo/git-upload-pack", "Git upload-pack"),
            ("POST", "/git/test-repo/git-receive-pack", "Git receive-pack"),
            ("GET", "/git/test-repo/HEAD", "获取HEAD"),
            ("GET", "/git/test-repo/objects/00/00000000000000000000000000000000000000", "获取对象"),
        ]
        
        for method, endpoint, description in endpoints:
            # Git HTTP接口可能返回200, 401, 403, 404
            self._test_endpoint(method, endpoint, description, [200, 401, 403, 404])
    
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
        
        # 基础测试
        self.test_health_check()
        self.test_user_apis()
        self.test_repository_apis()
        self.test_branch_apis()
        self.test_commit_apis()
        self.test_member_apis()
        self.test_issue_apis()
        self.test_pull_request_apis()
        self.test_repository_browser_apis()
        self.test_git_http_apis()
        self.test_cors_headers()
        
        # 带请求体的测试
        self.test_user_apis_with_body()
        self.test_repository_apis_with_body()
        self.test_branch_apis_with_body()
        self.test_commit_apis_with_params()
        self.test_commit_apis_with_body()
        self.test_member_apis_with_body()
        self.test_issue_apis_with_body()
        self.test_pull_request_apis_with_body()
        self.test_repository_browser_apis_with_params()
        
        return self.print_summary()
    
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
    # 支持命令行参数指定服务器地址
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://192.168.31.248:8080"
    tester = RemoteAPITester(base_url)
    exit_code = tester.run_all_tests()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
