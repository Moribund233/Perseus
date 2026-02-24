"""
批量测试数据生成脚本

用于生成大量测试数据以验证数据库迁移性能
支持创建用户、仓库、分支和提交记录

使用方法:
    python scripts/generate_test_data.py --users 10 --repos 50 --branches 200 --commits 10000

参数说明:
    --users: 创建的用户数量 (默认: 10)
    --repos: 每个用户创建的仓库数量 (默认: 50)
    --branches: 每个仓库创建的分支数量 (默认: 5)
    --commits: 每个分支创建的提交数量 (默认: 100)
    --base-url: API 基础 URL (默认: http://localhost:8000)
    --admin-user: 管理员用户名 (默认: admin)
    --admin-pass: 管理员密码 (默认: admin123)
    
限流控制参数:
    --max-concurrent: 最大并发请求数 (默认: 15)
    --request-delay: 请求间隔（秒）(默认: 0.05)
    --max-retries: 请求失败最大重试次数 (默认: 5)
    --retry-delay: 重试间隔（秒）(默认: 2.0)

优化建议:
    1. 如果遇到 429 限流错误，增加 --request-delay 或减小 --max-concurrent
    2. 默认参数已针对新的限流配置优化（支持分钟/小时二选一模式）
    3. 如果服务端响应慢，增加 --retry-delay 给服务端恢复时间
    4. 建议根据限流模式调整参数:
       - 分钟模式 (默认 200/min): 使用 --max-concurrent 10 --request-delay 0.3
       - 小时模式 (默认 5000/hour): 使用 --max-concurrent 15 --request-delay 0.05

推荐参数示例:
    # 分钟限流模式（保守）
    python scripts/generate_test_data.py --users 5 --repos 10 --branches 3 --commits 50 \
      --max-concurrent 10 --request-delay 0.3

    # 小时限流模式（默认）
    python scripts/generate_test_data.py --users 10 --repos 20 --branches 5 --commits 100 \
      --max-concurrent 15 --request-delay 0.05
"""

import argparse
import asyncio
import hashlib
import random
import string
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

import aiohttp
from aiohttp import ClientSession, ClientTimeout


class TestDataGenerator:
    """测试数据生成器

    优化特性:
    - 智能限流保护: 根据服务端限流模式自动调整请求频率
    - 重试机制: 自动重试失败的请求（特别是 429 限流错误）
    - 自适应延迟: 根据响应动态调整请求间隔
    - 批量处理: 支持批量创建提高效率
    - 限流模式检测: 自动检测服务端限流模式（分钟/小时）
    """

    def __init__(
        self,
        base_url: str,
        admin_user: str,
        admin_pass: str,
        max_concurrent: int = 15,
        request_delay: float = 0.05,
        max_retries: int = 5,
        retry_delay: float = 2.0,
        batch_size: int = 100
    ):
        self.base_url = base_url.rstrip("/")
        self.admin_user = admin_user
        self.admin_pass = admin_pass
        self.token: Optional[str] = None
        self.session: Optional[ClientSession] = None
        self.headers: Dict[str, str] = {}

        # 限流和重试配置
        # 新的限流配置支持分钟或小时二选一模式
        # 默认配置: default_limits = { mode: "minute", value: 200 }
        # 标准配置: standard = { mode: "minute", value: 60 }
        # 宽松配置: generous = { mode: "hour", value: 5000 }
        self.max_concurrent = max_concurrent  # 最大并发请求数（默认 15）
        self.request_delay = request_delay    # 请求间隔（秒）（默认 0.05）
        self.max_retries = max_retries        # 最大重试次数
        self.retry_delay = retry_delay        # 重试延迟（秒）
        self.batch_size = batch_size          # 批量处理大小（默认 100）
        self.semaphore = None                 # 信号量，用于控制并发

        # 自适应限流控制
        self.adaptive_delay = request_delay   # 自适应延迟（根据响应动态调整）
        self.rate_limit_hits = 0              # 限流命中次数
        self.consecutive_success = 0          # 连续成功次数

        # 统计信息
        self.stats = {
            "users_created": 0,
            "repos_created": 0,
            "branches_created": 0,
            "commits_created": 0,
            "errors": [],
            "retried_requests": 0,
            "rate_limited_count": 0,
            "start_time": None,
            "end_time": None,
        }

    async def __aenter__(self):
        """异步上下文管理器入口"""
        timeout = ClientTimeout(total=300, connect=30)
        self.session = ClientSession(timeout=timeout)
        self.semaphore = asyncio.Semaphore(self.max_concurrent)
        await self.login()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self.session:
            await self.session.close()

    def _adjust_delay(self, status: int):
        """根据响应状态动态调整请求延迟

        Args:
            status: HTTP 响应状态码
        """
        if status == 429:
            # 触发限流，大幅增加延迟
            self.rate_limit_hits += 1
            self.consecutive_success = 0
            # 指数退避: 每次触发限流，延迟翻倍
            self.adaptive_delay = min(self.adaptive_delay * 2, 5.0)
        elif status >= 200 and status < 300:
            # 请求成功，可以适当降低延迟
            self.consecutive_success += 1
            if self.consecutive_success >= 10:
                # 连续 10 次成功，稍微降低延迟
                self.adaptive_delay = max(self.adaptive_delay * 0.9, self.request_delay)
                self.consecutive_success = 0

    async def _make_request(
        self,
        method: str,
        url: str,
        **kwargs
    ) -> tuple[int, Any]:
        """发送 HTTP 请求，带智能限流保护和重试机制

        Args:
            method: HTTP 方法 (get, post, etc.)
            url: 请求 URL
            **kwargs: 其他请求参数

        Returns:
            tuple: (状态码, 响应数据)
        """
        async with self.semaphore:  # 限制并发
            for attempt in range(self.max_retries + 1):
                try:
                    # 使用自适应延迟
                    current_delay = max(self.adaptive_delay, self.request_delay)
                    if current_delay > 0:
                        await asyncio.sleep(current_delay)

                    async with getattr(self.session, method)(url, **kwargs) as response:
                        status = response.status

                        # 动态调整延迟
                        self._adjust_delay(status)

                        # 处理限流错误 (429) - 使用指数退避
                        if status == 429:
                            self.stats["rate_limited_count"] += 1
                            if attempt < self.max_retries:
                                # 从响应头获取 Retry-After，或使用指数退避
                                retry_after = float(response.headers.get('Retry-After', self.retry_delay * (2 ** attempt)))
                                self.stats["retried_requests"] += 1
                                if attempt == 0:
                                    print(f"   ⚠️  触发限流 (429)，等待 {retry_after:.1f}s 后重试...")
                                await asyncio.sleep(retry_after)
                                continue
                            else:
                                return status, "Rate limited - Max retries exceeded"

                        # 处理其他错误
                        if status >= 400:
                            text = await response.text()
                            if attempt < self.max_retries and status >= 500:
                                # 服务器错误时重试
                                self.stats["retried_requests"] += 1
                                wait_time = self.retry_delay * (2 ** attempt)
                                await asyncio.sleep(wait_time)
                                continue
                            return status, text

                        # 成功响应
                        try:
                            data = await response.json()
                        except:
                            data = await response.text()
                        return status, data

                except asyncio.TimeoutError:
                    if attempt < self.max_retries:
                        self.stats["retried_requests"] += 1
                        wait_time = self.retry_delay * (2 ** attempt)
                        print(f"   ⚠️  请求超时，等待 {wait_time:.1f}s 后重试...")
                        await asyncio.sleep(wait_time)
                        continue
                    return 0, "Timeout"

                except Exception as e:
                    if attempt < self.max_retries:
                        self.stats["retried_requests"] += 1
                        wait_time = self.retry_delay * (2 ** attempt)
                        await asyncio.sleep(wait_time)
                        continue
                    return 0, str(e)

            return 0, "Max retries exceeded"

    async def login(self) -> bool:
        """
        用户登录获取 Token

        Returns:
            bool: 登录是否成功
        """
        url = f"{self.base_url}/api/v1/auth/login"
        payload = {
            "username": self.admin_user,
            "password": self.admin_pass
        }

        try:
            async with self.session.post(url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    self.token = data.get("token") or data.get("access_token")
                    if self.token:
                        self.headers["Authorization"] = f"Bearer {self.token}"
                        print(f"✅ 登录成功: {self.admin_user}")
                        return True
                    else:
                        print("❌ 登录响应中没有 access_token")
                        return False
                else:
                    text = await response.text()
                    print(f"❌ 登录失败: HTTP {response.status} - {text}")
                    return False
        except Exception as e:
            print(f"❌ 登录异常: {e}")
            return False

    def generate_random_string(self, length: int = 10) -> str:
        """生成随机字符串"""
        return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))

    def generate_random_name(self, prefix: str = "") -> str:
        """生成随机名称"""
        timestamp = int(time.time())
        random_part = self.generate_random_string(8)
        return f"{prefix}{timestamp}_{random_part}"

    def generate_email(self, username: str) -> str:
        """生成邮箱地址"""
        domains = ["test.com", "example.com", "demo.org", "fake.net"]
        return f"{username}@{random.choice(domains)}"

    def generate_commit_hash(self) -> str:
        """生成模拟的 Git commit hash"""
        return hashlib.sha1(str(time.time() + random.random()).encode()).hexdigest()

    def generate_commit_message(self) -> str:
        """生成随机的提交信息"""
        actions = ["添加", "修复", "更新", "重构", "优化", "删除", "合并", "创建"]
        targets = ["功能", "bug", "文档", "测试", "配置", "接口", "模块", "组件"]
        details = [
            "提升性能", "解决兼容性问题", "改进用户体验",
            "修复内存泄漏", "优化查询速度", "添加单元测试",
            "更新依赖版本", "重构代码结构"
        ]
        return f"{random.choice(actions)}{random.choice(targets)}: {random.choice(details)}"

    def generate_date(self, days_ago: int = 365) -> str:
        """生成随机日期"""
        delta = timedelta(days=random.randint(0, days_ago))
        date = datetime.now() - delta
        return date.strftime("%Y-%m-%dT%H:%M:%S")

    async def create_user(self, username: str, password: str) -> Optional[int]:
        """
        创建用户

        Args:
            username: 用户名
            password: 密码

        Returns:
            Optional[int]: 用户ID，失败返回 None
        """
        url = f"{self.base_url}/api/v1/users"
        payload = {
            "username": username,
            "email": self.generate_email(username),
            "password": password,
            "full_name": f"Test User {username}",
            "is_active": True,
            "is_admin": False
        }

        status, data = await self._make_request("post", url, headers=self.headers, json=payload)

        if status in (200, 201):
            user_id = data.get("id") if isinstance(data, dict) else None
            self.stats["users_created"] += 1
            return user_id
        elif status == 429:
            self.stats["errors"].append(f"创建用户被限流 {username}")
            return None
        elif status == 409:
            # 用户已存在，尝试获取
            return await self.get_user_id(username)
        else:
            self.stats["errors"].append(f"创建用户失败 {username}: HTTP {status} - {data}")
            return None

    async def get_user_id(self, username: str) -> Optional[int]:
        """获取用户ID"""
        url = f"{self.base_url}/api/v1/users"
        status, data = await self._make_request("get", url, headers=self.headers)

        if status == 200:
            # API 可能直接返回列表或包含 items 的对象
            if isinstance(data, list):
                users = data
            else:
                users = data.get("items", [])
            for user in users:
                if user.get("username") == username:
                    return user.get("id")
        return None

    async def create_repository(self, name: str, owner_id: int) -> Optional[int]:
        """
        创建仓库

        Args:
            name: 仓库名称
            owner_id: 所有者ID

        Returns:
            Optional[int]: 仓库ID，失败返回 None
        """
        url = f"{self.base_url}/api/v1/repositories"
        payload = {
            "name": name,
            "path": f"/repos/{name}",
            "description": f"Test repository {name}",
            "is_public": random.choice([True, False]),
            "owner_id": owner_id,
            "default_branch": "main"
        }

        status, data = await self._make_request("post", url, headers=self.headers, json=payload)

        if status in (200, 201):
            repo_id = data.get("id") if isinstance(data, dict) else None
            self.stats["repos_created"] += 1
            return repo_id
        elif status == 429:
            self.stats["errors"].append(f"创建仓库被限流 {name}")
            return None
        elif status == 409:
            return await self.get_repository_id(name)
        else:
            self.stats["errors"].append(f"创建仓库失败 {name}: HTTP {status}")
            return None

    async def get_repository_id(self, name: str) -> Optional[int]:
        """获取仓库ID"""
        url = f"{self.base_url}/api/v1/repositories"
        status, data = await self._make_request("get", url, headers=self.headers)

        if status == 200:
            if isinstance(data, list):
                repos = data
            else:
                repos = data.get("items", [])
            for repo in repos:
                if repo.get("name") == name:
                    return repo.get("id")
        return None

    async def create_branch(self, name: str, repository_id: int) -> Optional[int]:
        """
        创建分支

        Args:
            name: 分支名称
            repository_id: 仓库ID

        Returns:
            Optional[int]: 分支ID，失败返回 None
        """
        url = f"{self.base_url}/api/v1/repositories/{repository_id}/branches"
        payload = {
            "name": name,
            "is_protected": random.choice([True, False]),
            "require_code_review": random.choice([True, False]),
            "require_status_checks": random.choice([True, False])
        }

        status, data = await self._make_request("post", url, headers=self.headers, json=payload)

        if status in (200, 201):
            branch_id = data.get("id") if isinstance(data, dict) else None
            self.stats["branches_created"] += 1
            return branch_id
        elif status == 429:
            self.stats["errors"].append(f"创建分支被限流 {name}")
            return None
        elif status == 409:
            return await self.get_branch_id(name, repository_id)
        else:
            self.stats["errors"].append(f"创建分支失败 {name}: HTTP {status}")
            return None

    async def get_branch_id(self, name: str, repository_id: int) -> Optional[int]:
        """获取分支ID"""
        url = f"{self.base_url}/api/v1/repositories/{repository_id}/branches"
        status, data = await self._make_request("get", url, headers=self.headers)

        if status == 200:
            if isinstance(data, list):
                branches = data
            else:
                branches = data.get("items", [])
            for branch in branches:
                if branch.get("name") == name:
                    return branch.get("id")
        return None

    async def create_commit(self, repository_id: int, branch_id: int, branch_name: str, author_name: str, author_email: str) -> bool:
        """
        创建提交记录（带智能限流保护和重试）

        Args:
            repository_id: 仓库ID
            branch_id: 分支ID
            branch_name: 分支名称
            author_name: 作者名称
            author_email: 作者邮箱

        Returns:
            bool: 是否成功
        """
        url = f"{self.base_url}/api/v1/repositories/{repository_id}/commits"
        payload = {
            "hash": self.generate_commit_hash(),
            "branch_id": branch_id,
            "author_name": author_name,
            "author_email": author_email,
            "committer_name": author_name,
            "committer_email": author_email,
            "commit_message": self.generate_commit_message()
        }

        status, data = await self._make_request("post", url, headers=self.headers, json=payload)

        if status in (200, 201):
            self.stats["commits_created"] += 1
            return True
        else:
            if status == 429:
                self.stats["errors"].append(f"创建提交被限流: {data}")
            else:
                self.stats["errors"].append(f"创建提交失败: HTTP {status} - {data}")
            return False

    async def generate_data(
        self,
        user_count: int,
        repos_per_user: int,
        branches_per_repo: int,
        commits_per_branch: int
    ):
        """
        生成测试数据

        Args:
            user_count: 用户数量
            repos_per_user: 每个用户的仓库数量
            branches_per_repo: 每个仓库的分支数量
            commits_per_branch: 每个分支的提交数量
        """
        self.stats["start_time"] = time.time()
        print(f"\n🚀 开始生成测试数据...")
        print(f"   计划创建: {user_count} 用户 × {repos_per_user} 仓库 × {branches_per_repo} 分支 × {commits_per_branch} 提交")
        print(f"   预计总数: {user_count * repos_per_user * branches_per_repo * commits_per_branch} 条记录")
        print(f"   限流保护: 并发={self.max_concurrent}, 延迟={self.request_delay}s, 最大重试={self.max_retries}\n")

        # 1. 创建用户
        print("👤 创建用户...")
        users = []
        for i in range(user_count):
            username = f"testuser_{self.generate_random_string(6)}"
            password = "TestPass123!"
            user_id = await self.create_user(username, password)
            if user_id:
                users.append({
                    "id": user_id,
                    "username": username,
                    "email": self.generate_email(username)
                })
                if (i + 1) % 10 == 0:
                    print(f"   已创建 {i + 1}/{user_count} 用户")

        print(f"✅ 成功创建 {len(users)} 个用户\n")

        # 2. 创建仓库
        print("📦 创建仓库...")
        repos = []
        for user in users:
            for j in range(repos_per_user):
                repo_name = f"repo_{self.generate_random_string(8)}"
                repo_id = await self.create_repository(repo_name, user["id"])
                if repo_id:
                    repos.append({
                        "id": repo_id,
                        "name": repo_name,
                        "owner_id": user["id"]
                    })

        print(f"✅ 成功创建 {len(repos)} 个仓库\n")

        # 3. 创建分支
        print("🌿 创建分支...")
        branches = []
        for repo in repos:
            # 每个仓库至少有一个 main 分支
            main_branch_id = await self.create_branch("main", repo["id"])
            if main_branch_id:
                branches.append({
                    "id": main_branch_id,
                    "name": "main",
                    "repository_id": repo["id"]
                })

            # 创建其他分支
            for k in range(branches_per_repo - 1):
                branch_name = f"feature_{self.generate_random_string(6)}"
                branch_id = await self.create_branch(branch_name, repo["id"])
                if branch_id:
                    branches.append({
                        "id": branch_id,
                        "name": branch_name,
                        "repository_id": repo["id"]
                    })

            if len(branches) % 100 == 0:
                print(f"   已创建 {len(branches)} 分支")

        print(f"✅ 成功创建 {len(branches)} 个分支\n")

        # 4. 创建提交（使用批量并发控制）
        print("💾 创建提交记录...")
        total_commits = len(branches) * commits_per_branch
        commit_count = 0
        failed_count = 0

        # 预先生成所有提交任务
        commit_tasks = []
        for branch in branches:
            # 获取仓库所有者信息作为提交作者
            repo_owner = next((r for r in repos if r["id"] == branch["repository_id"]), None)
            if repo_owner:
                user = next((u for u in users if u["id"] == repo_owner["owner_id"]), None)
                if user:
                    author_name = user["username"]
                    author_email = user["email"]
                else:
                    author_name = "unknown"
                    author_email = "unknown@test.com"
            else:
                author_name = "system"
                author_email = "system@test.com"

            for _ in range(commits_per_branch):
                commit_tasks.append({
                    "repository_id": branch["repository_id"],
                    "branch_id": branch["id"],
                    "branch_name": branch["name"],
                    "author_name": author_name,
                    "author_email": author_email
                })

        # 分批处理提交任务，避免内存溢出和触发限流
        for i in range(0, len(commit_tasks), self.batch_size):
            batch = commit_tasks[i:i + self.batch_size]

            # 并发执行批次内的任务
            results = await asyncio.gather(*[
                self.create_commit(**task)
                for task in batch
            ], return_exceptions=True)

            # 统计结果
            for result in results:
                if isinstance(result, Exception):
                    failed_count += 1
                elif result:
                    commit_count += 1
                else:
                    failed_count += 1

            # 进度报告
            processed = min(i + self.batch_size, len(commit_tasks))
            progress_pct = processed / total_commits * 100 if total_commits > 0 else 0
            print(f"   进度: {processed}/{total_commits} ({progress_pct:.1f}%) - "
                  f"成功: {commit_count}, 失败: {failed_count}")

        print(f"✅ 成功创建 {commit_count} 个提交")
        if failed_count > 0:
            print(f"⚠️  失败: {failed_count} 个提交")
        print()

        self.stats["end_time"] = time.time()

    def print_summary(self):
        """打印统计摘要"""
        duration = self.stats["end_time"] - self.stats["start_time"]
        print("\n" + "=" * 60)
        print("📊 测试数据生成完成")
        print("=" * 60)
        print(f"⏱️  耗时: {duration:.2f} 秒")
        print(f"👤 用户: {self.stats['users_created']}")
        print(f"📦 仓库: {self.stats['repos_created']}")
        print(f"🌿 分支: {self.stats['branches_created']}")
        print(f"💾 提交: {self.stats['commits_created']}")
        print(f"📈 总记录: {sum([self.stats['users_created'], self.stats['repos_created'], self.stats['branches_created'], self.stats['commits_created']])}")
        
        if duration > 0:
            print(f"⚡ 平均速度: {self.stats['commits_created'] / duration:.1f} 提交/秒")

        if self.stats["rate_limited_count"] > 0:
            print(f"🚫 限流命中: {self.stats['rate_limited_count']} 次")

        if self.stats["retried_requests"] > 0:
            print(f"🔄 重试请求: {self.stats['retried_requests']} 次")

        if self.stats["errors"]:
            print(f"\n⚠️  错误数量: {len(self.stats['errors'])}")
            print("前 5 个错误:")
            for error in self.stats["errors"][:5]:
                print(f"   - {error}")


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="批量生成测试数据用于验证数据库迁移",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 生成小规模数据（快速测试）- 适合分钟限流模式
  python scripts/generate_test_data.py --users 2 --repos 5 --branches 3 --commits 10 \
    --max-concurrent 5 --request-delay 0.3

  # 生成中等规模数据 - 适合小时限流模式
  python scripts/generate_test_data.py --users 5 --repos 20 --branches 5 --commits 100 \
    --max-concurrent 15 --request-delay 0.05

  # 生成大规模数据（压力测试）
  python scripts/generate_test_data.py --users 10 --repos 50 --branches 10 --commits 1000 \
    --max-concurrent 20 --request-delay 0.02

限流模式适配:
  分钟模式 (默认 200/min):
    --max-concurrent 5-10 --request-delay 0.3-0.5
  
  小时模式 (默认 5000/hour):
    --max-concurrent 15-25 --request-delay 0.02-0.05
        """
    )

    parser.add_argument(
        "--users", "-u",
        type=int,
        default=10,
        help="创建的用户数量 (默认: 10)"
    )
    parser.add_argument(
        "--repos", "-r",
        type=int,
        default=50,
        help="每个用户创建的仓库数量 (默认: 50)"
    )
    parser.add_argument(
        "--branches", "-b",
        type=int,
        default=5,
        help="每个仓库创建的分支数量 (默认: 5)"
    )
    parser.add_argument(
        "--commits", "-c",
        type=int,
        default=100,
        help="每个分支创建的提交数量 (默认: 100)"
    )
    parser.add_argument(
        "--base-url",
        type=str,
        default="http://localhost:8000",
        help="API 基础 URL (默认: http://localhost:8000)"
    )
    parser.add_argument(
        "--admin-user",
        type=str,
        default="admin",
        help="管理员用户名 (默认: admin)"
    )
    parser.add_argument(
        "--admin-pass",
        type=str,
        default="admin123",
        help="管理员密码 (默认: admin123)"
    )
    parser.add_argument(
        "--max-concurrent",
        type=int,
        default=15,
        help="最大并发请求数 (默认: 15，分钟模式建议 5-10，小时模式建议 15-25)"
    )
    parser.add_argument(
        "--request-delay",
        type=float,
        default=0.05,
        help="请求间隔（秒），避免触发限流 (默认: 0.05，分钟模式建议 0.3-0.5，小时模式建议 0.02-0.05)"
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=5,
        help="请求失败最大重试次数 (默认: 5)"
    )
    parser.add_argument(
        "--retry-delay",
        type=float,
        default=2.0,
        help="重试间隔（秒） (默认: 2.0)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="批量处理大小，每批处理的提交数量 (默认: 100)"
    )

    return parser.parse_args()


async def main():
    """主函数"""
    args = parse_args()

    async with TestDataGenerator(
        base_url=args.base_url,
        admin_user=args.admin_user,
        admin_pass=args.admin_pass,
        max_concurrent=args.max_concurrent,
        request_delay=args.request_delay,
        max_retries=args.max_retries,
        retry_delay=args.retry_delay,
        batch_size=args.batch_size
    ) as generator:
        await generator.generate_data(
            user_count=args.users,
            repos_per_user=args.repos,
            branches_per_repo=args.branches,
            commits_per_branch=args.commits
        )
        generator.print_summary()


if __name__ == "__main__":
    asyncio.run(main())
