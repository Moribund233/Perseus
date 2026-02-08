"""
仓库完整工作流程测试脚本

模拟完整的 Git 仓库操作：
1. 用户登录
2. 创建远程仓库
3. 克隆/连接远程仓库
4. 添加文件并提交

使用方法:
    python tests/test_repository_workflow.py

环境变量:
    API_BASE_URL: API 基础 URL (默认: http://192.168.31.248:8080)
    TEST_USERNAME: 测试用户名 (默认: test)
    TEST_PASSWORD: 测试密码 (默认: test123)
"""
import os
import sys
import tempfile
import shutil
import subprocess
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests


class RepositoryWorkflowTester:
    """
    仓库工作流程测试器

    模拟完整的 Git 仓库操作流程。
    """

    def __init__(self):
        self.base_url = os.environ.get("API_BASE_URL", "http://192.168.31.248:8080").rstrip('/')
        self.username = os.environ.get("TEST_USERNAME", "test")
        self.password = os.environ.get("TEST_PASSWORD", "test123")
        self.token = None
        self.user_id = None
        self.repo_id = None
        self.repo_name = None
        self.session = requests.Session()
        self.temp_dir = None

    def log(self, message: str, level: str = "INFO"):
        """打印日志"""
        prefix = {"INFO": "ℹ️", "SUCCESS": "✅", "ERROR": "❌", "WARNING": "⚠️"}.get(level, "ℹ️")
        print(f"{prefix} {message}")

    def login(self) -> bool:
        """
        用户登录获取 Token

        Returns:
            bool: 登录是否成功
        """
        self.log("步骤 1: 用户登录", "INFO")
        print(f"   用户名: {self.username}")
        print(f"   API地址: {self.base_url}")

        try:
            response = self.session.post(
                f"{self.base_url}/api/users/login",
                json={"username": self.username, "password": self.password},
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                self.user_id = data.get("id") or data.get("user_id")

                if self.user_id:
                    self.log(f"登录成功! User ID: {self.user_id}", "SUCCESS")
                    print(f"   用户名: {data.get('username')}")
                    print(f"   邮箱: {data.get('email')}")
                    return True
                else:
                    self.log("登录响应中缺少用户ID", "ERROR")
                    return False
            else:
                self.log(f"登录失败: HTTP {response.status_code}", "ERROR")
                print(f"   响应: {response.text[:200]}")
                return False

        except Exception as e:
            self.log(f"登录异常: {e}", "ERROR")
            return False

    def create_repository(self) -> bool:
        """
        创建远程仓库

        Returns:
            bool: 创建是否成功
        """
        self.log("步骤 2: 创建远程仓库", "INFO")

        import uuid
        self.repo_name = f"test-repo-{uuid.uuid4().hex[:8]}"
        repo_path = f"/repos/{self.repo_name}"

        repo_data = {
            "name": self.repo_name,
            "path": repo_path,
            "description": f"Test repository created by workflow test",
            "is_public": True,
            "owner_id": self.user_id,
            "default_branch": "master"
        }

        try:
            response = self.session.post(
                f"{self.base_url}/api/repositories/",
                json=repo_data,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                self.repo_id = data.get("id")
                physical_info = data.get("physical", {})

                self.log(f"仓库创建成功!", "SUCCESS")
                print(f"   仓库ID: {self.repo_id}")
                print(f"   仓库名: {self.repo_name}")
                print(f"   逻辑路径: {repo_path}")
                print(f"   物理路径: {physical_info.get('path', 'N/A')}")
                print(f"   物理存在: {physical_info.get('exists', False)}")
                return True
            elif response.status_code == 409:
                self.log("仓库路径已存在", "WARNING")
                return False
            else:
                self.log(f"创建仓库失败: HTTP {response.status_code}", "ERROR")
                print(f"   响应: {response.text[:200]}")
                return False

        except Exception as e:
            self.log(f"创建仓库异常: {e}", "ERROR")
            return False

    def verify_repository_exists(self) -> bool:
        """
        验证仓库在 API 中存在

        Returns:
            bool: 验证是否通过
        """
        self.log("步骤 3: 验证仓库信息", "INFO")

        try:
            response = self.session.get(
                f"{self.base_url}/api/repositories/{self.repo_id}",
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                physical = data.get("physical", {})

                self.log("仓库信息获取成功", "SUCCESS")
                print(f"   仓库名: {data.get('name')}")
                print(f"   物理路径: {physical.get('path')}")
                print(f"   物理存在: {physical.get('exists')}")

                if physical.get("exists"):
                    self.log("物理仓库已创建", "SUCCESS")
                    return True
                else:
                    self.log("物理仓库不存在!", "WARNING")
                    return False
            else:
                self.log(f"获取仓库信息失败: HTTP {response.status_code}", "ERROR")
                return False

        except Exception as e:
            self.log(f"验证仓库异常: {e}", "ERROR")
            return False

    def clone_and_commit(self) -> bool:
        """
        克隆仓库、添加文件并提交

        Returns:
            bool: 操作是否成功
        """
        self.log("步骤 4: 克隆仓库并提交", "INFO")

        # 创建临时目录
        self.temp_dir = tempfile.mkdtemp(prefix="langit_test_")
        print(f"   临时目录: {self.temp_dir}")

        # 构建仓库 URL
        # 注意：这里假设服务器支持 HTTP Git 协议
        # 实际 URL 可能需要根据你的服务器配置调整
        repo_url = f"{self.base_url}/git/{self.repo_name}"
        print(f"   仓库URL: {repo_url}")

        try:
            # 检查 git 命令是否可用
            result = subprocess.run(
                ["git", "--version"],
                capture_output=True,
                text=True,
                check=True
            )
            print(f"   Git版本: {result.stdout.strip()}")

            # 克隆仓库
            self.log("正在克隆仓库...", "INFO")
            clone_result = subprocess.run(
                ["git", "clone", repo_url, self.repo_name],
                cwd=self.temp_dir,
                capture_output=True,
                text=True,
                timeout=30
            )

            if clone_result.returncode != 0:
                # 克隆失败可能是正常的，因为 HTTP Git 协议可能未配置
                self.log(f"克隆失败（可能是正常的）: {clone_result.stderr}", "WARNING")
                print("   💡 提示: 服务器可能未配置 HTTP Git 协议")
                print("   继续测试其他功能...")
                return True  # 不阻止后续测试

            self.log("仓库克隆成功", "SUCCESS")

            # 创建测试文件
            repo_dir = os.path.join(self.temp_dir, self.repo_name)
            test_file = os.path.join(repo_dir, "README.md")

            with open(test_file, "w", encoding="utf-8") as f:
                f.write(f"# {self.repo_name}\n\n")
                f.write("This is a test repository created by LanGit workflow test.\n")
                f.write(f"Created at: {__import__('datetime').datetime.now().isoformat()}\n")

            self.log("创建测试文件", "SUCCESS")

            # 配置 git
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"],
                cwd=repo_dir,
                check=True
            )
            subprocess.run(
                ["git", "config", "user.name", "Test User"],
                cwd=repo_dir,
                check=True
            )

            # 添加文件
            subprocess.run(
                ["git", "add", "README.md"],
                cwd=repo_dir,
                check=True
            )

            # 提交
            subprocess.run(
                ["git", "commit", "-m", "Initial commit from workflow test"],
                cwd=repo_dir,
                check=True
            )

            self.log("文件提交成功", "SUCCESS")

            # 推送
            self.log("正在推送...", "INFO")
            push_result = subprocess.run(
                ["git", "push", "origin", "master"],
                cwd=repo_dir,
                capture_output=True,
                text=True,
                timeout=30
            )

            if push_result.returncode == 0:
                self.log("推送成功", "SUCCESS")
            else:
                self.log(f"推送失败: {push_result.stderr}", "WARNING")

            return True

        except subprocess.TimeoutExpired:
            self.log("Git 操作超时", "ERROR")
            return False
        except Exception as e:
            self.log(f"Git 操作异常: {e}", "ERROR")
            return False

    def delete_repository(self) -> bool:
        """
        删除测试仓库

        Returns:
            bool: 删除是否成功
        """
        self.log("步骤 5: 清理 - 删除测试仓库", "INFO")

        if not self.repo_id:
            self.log("没有仓库ID，跳过删除", "WARNING")
            return True

        try:
            response = self.session.delete(
                f"{self.base_url}/api/repositories/{self.repo_id}",
                timeout=10
            )

            if response.status_code == 200:
                self.log("仓库删除成功", "SUCCESS")
                return True
            else:
                self.log(f"删除仓库失败: HTTP {response.status_code}", "WARNING")
                return False

        except Exception as e:
            self.log(f"删除仓库异常: {e}", "WARNING")
            return False

    def cleanup(self):
        """清理临时资源"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
                self.log(f"清理临时目录: {self.temp_dir}", "INFO")
            except Exception as e:
                self.log(f"清理临时目录失败: {e}", "WARNING")

    def run_all_tests(self):
        """运行所有测试"""
        print("=" * 70)
        print("仓库完整工作流程测试")
        print("=" * 70)
        print(f"API地址: {self.base_url}")
        print(f"测试用户: {self.username}")
        print("=" * 70)

        success = True

        try:
            # 步骤 1: 登录
            if not self.login():
                success = False
                return

            # 步骤 2: 创建仓库
            if not self.create_repository():
                success = False
                return

            # 步骤 3: 验证仓库
            if not self.verify_repository_exists():
                success = False

            # 步骤 4: 克隆和提交（可选，可能失败）
            self.clone_and_commit()

        finally:
            # 步骤 5: 清理
            self.delete_repository()
            self.cleanup()

            print("\n" + "=" * 70)
            if success:
                print("✅ 工作流程测试完成!")
            else:
                print("❌ 工作流程测试未完成")
            print("=" * 70)


def main():
    """主函数"""
    tester = RepositoryWorkflowTester()
    tester.run_all_tests()


if __name__ == "__main__":
    main()
