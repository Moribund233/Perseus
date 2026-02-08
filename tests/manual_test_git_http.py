"""
Git HTTP 协议手动测试脚本

用于手动测试 Git Smart HTTP 协议的完整工作流程
包括：
1. 创建用户和仓库
2. 使用 git clone 克隆仓库
3. 使用 git push 推送代码
4. 使用 git pull 拉取代码

使用方法:
1. 启动服务器: python langit_cli.py server start
2. 运行测试: python tests/manual_test_git_http.py
"""
import os
import sys
import tempfile
import shutil
import subprocess
import base64
import json
import time

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx


# 测试配置
BASE_URL = "http://127.0.0.1:8000"
TEST_USERNAME = "gittestuser"
TEST_PASSWORD = "testpass123"
TEST_EMAIL = "gittest@example.com"
TEST_REPO_NAME = "test-git-repo"


def create_user():
    """创建测试用户"""
    print("=" * 60)
    print("步骤 1: 创建测试用户")
    print("=" * 60)

    url = f"{BASE_URL}/api/users/"
    data = {
        "username": TEST_USERNAME,
        "password": TEST_PASSWORD,
        "email": TEST_EMAIL,
        "full_name": "Git Test User",
        "is_active": True,
        "is_admin": False
    }

    try:
        response = httpx.post(url, json=data, timeout=10.0)
        if response.status_code == 200:
            print(f"✅ 用户创建成功: {TEST_USERNAME}")
            return response.json()
        elif response.status_code == 409:
            print(f"⚠️ 用户已存在: {TEST_USERNAME}")
            # 尝试登录获取用户信息
            return login_user()
        else:
            print(f"❌ 用户创建失败: {response.status_code}")
            print(f"   响应: {response.text}")
            return None
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return None


def login_user():
    """用户登录"""
    url = f"{BASE_URL}/api/users/login"
    data = {
        "username": TEST_USERNAME,
        "password": TEST_PASSWORD
    }

    try:
        response = httpx.post(url, json=data, timeout=10.0)
        if response.status_code == 200:
            print(f"✅ 用户登录成功: {TEST_USERNAME}")
            return response.json()
        else:
            print(f"❌ 登录失败: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return None


def create_repository(user_id):
    """创建测试仓库"""
    print("\n" + "=" * 60)
    print("步骤 2: 创建测试仓库")
    print("=" * 60)

    url = f"{BASE_URL}/api/repositories/"
    data = {
        "name": TEST_REPO_NAME,
        "description": "Test repository for Git HTTP",
        "is_public": True,
        "owner_id": user_id,
        "path": f"{TEST_USERNAME}/{TEST_REPO_NAME}"
    }

    try:
        response = httpx.post(url, json=data, timeout=10.0)
        if response.status_code == 200:
            print(f"✅ 仓库创建成功: {TEST_REPO_NAME}")
            return response.json()
        elif response.status_code == 409:
            print(f"⚠️ 仓库已存在: {TEST_REPO_NAME}")
            # 获取仓库信息
            return get_repository()
        else:
            print(f"❌ 仓库创建失败: {response.status_code}")
            print(f"   响应: {response.text}")
            return None
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return None


def get_repository():
    """获取仓库信息"""
    url = f"{BASE_URL}/api/repositories/"

    try:
        response = httpx.get(url, timeout=10.0)
        if response.status_code == 200:
            repos = response.json()
            for repo in repos:
                if repo.get("name") == TEST_REPO_NAME:
                    return repo
        return None
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return None


def test_git_refs_discovery():
    """测试 Git 引用发现"""
    print("\n" + "=" * 60)
    print("步骤 3: 测试 Git 引用发现")
    print("=" * 60)

    url = f"{BASE_URL}/git/{TEST_USERNAME}/{TEST_REPO_NAME}/info/refs?service=git-upload-pack"

    try:
        response = httpx.get(url, timeout=10.0)
        if response.status_code == 200:
            print(f"✅ 引用发现成功")
            print(f"   Content-Type: {response.headers.get('content-type')}")
            # 解析响应内容
            content = response.content
            if b"# service=git-upload-pack" in content:
                print(f"   服务声明: git-upload-pack")
            return True
        else:
            print(f"❌ 引用发现失败: {response.status_code}")
            print(f"   响应: {response.text}")
            return False
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return False


def test_git_clone():
    """测试 Git Clone"""
    print("\n" + "=" * 60)
    print("步骤 4: 测试 Git Clone")
    print("=" * 60)

    # 创建临时目录
    temp_dir = tempfile.mkdtemp(prefix="git_test_")
    clone_dir = os.path.join(temp_dir, "cloned_repo")

    # 构建仓库 URL（带认证信息）
    encoded_credentials = base64.b64encode(f"{TEST_USERNAME}:{TEST_PASSWORD}".encode()).decode()
    repo_url = f"{BASE_URL}/git/{TEST_USERNAME}/{TEST_REPO_NAME}"

    print(f"   临时目录: {temp_dir}")
    print(f"   仓库 URL: {repo_url}")

    try:
        # 使用 git clone
        env = os.environ.copy()
        env["GIT_TERMINAL_PROMPT"] = "0"  # 禁用交互式提示

        cmd = [
            "git", "clone",
            "-c", f"http.extraHeader=Authorization: Basic {encoded_credentials}",
            repo_url,
            clone_dir
        ]

        print(f"   执行命令: git clone ...")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30.0
        )

        if result.returncode == 0:
            print(f"✅ Git Clone 成功")
            print(f"   克隆目录: {clone_dir}")

            # 检查是否是有效的 git 仓库
            if os.path.exists(os.path.join(clone_dir, ".git")):
                print(f"   验证: 是有效的 Git 仓库")
                return temp_dir, clone_dir
            else:
                print(f"❌ 验证失败: 不是有效的 Git 仓库")
                return None, None
        else:
            print(f"❌ Git Clone 失败")
            print(f"   错误: {result.stderr}")
            return None, None

    except subprocess.TimeoutExpired:
        print(f"❌ Git Clone 超时")
        return None, None
    except Exception as e:
        print(f"❌ Git Clone 异常: {e}")
        return None, None


def test_git_push(clone_dir):
    """测试 Git Push"""
    print("\n" + "=" * 60)
    print("步骤 5: 测试 Git Push")
    print("=" * 60)

    if not clone_dir or not os.path.exists(clone_dir):
        print(f"❌ 克隆目录不存在")
        return False

    try:
        # 配置 git 用户信息
        subprocess.run(["git", "config", "user.email", TEST_EMAIL], cwd=clone_dir, check=True)
        subprocess.run(["git", "config", "user.name", TEST_USERNAME], cwd=clone_dir, check=True)

        # 创建一个测试文件
        test_file = os.path.join(clone_dir, "README.md")
        with open(test_file, "w") as f:
            f.write("# Test Repository\n\nThis is a test file.\n")

        print(f"   创建测试文件: README.md")

        # 添加文件到暂存区
        result = subprocess.run(
            ["git", "add", "README.md"],
            cwd=clone_dir,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            print(f"❌ Git Add 失败: {result.stderr}")
            return False

        print(f"   执行: git add README.md")

        # 提交更改
        result = subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=clone_dir,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            print(f"❌ Git Commit 失败: {result.stderr}")
            return False

        print(f"   执行: git commit -m 'Initial commit'")

        # 推送更改
        encoded_credentials = base64.b64encode(f"{TEST_USERNAME}:{TEST_PASSWORD}".encode()).decode()

        result = subprocess.run(
            [
                "git", "push",
                "-c", f"http.extraHeader=Authorization: Basic {encoded_credentials}",
                "origin", "master"
            ],
            cwd=clone_dir,
            capture_output=True,
            text=True,
            timeout=30.0
        )

        if result.returncode == 0:
            print(f"✅ Git Push 成功")
            return True
        else:
            print(f"❌ Git Push 失败")
            print(f"   错误: {result.stderr}")
            return False

    except Exception as e:
        print(f"❌ Git Push 异常: {e}")
        return False


def test_git_pull(clone_dir):
    """测试 Git Pull"""
    print("\n" + "=" * 60)
    print("步骤 6: 测试 Git Pull")
    print("=" * 60)

    if not clone_dir or not os.path.exists(clone_dir):
        print(f"❌ 克隆目录不存在")
        return False

    try:
        encoded_credentials = base64.b64encode(f"{TEST_USERNAME}:{TEST_PASSWORD}".encode()).decode()

        result = subprocess.run(
            [
                "git", "pull",
                "-c", f"http.extraHeader=Authorization: Basic {encoded_credentials}",
                "origin", "master"
            ],
            cwd=clone_dir,
            capture_output=True,
            text=True,
            timeout=30.0
        )

        if result.returncode == 0:
            print(f"✅ Git Pull 成功")
            return True
        else:
            print(f"❌ Git Pull 失败")
            print(f"   错误: {result.stderr}")
            return False

    except Exception as e:
        print(f"❌ Git Pull 异常: {e}")
        return False


def cleanup(temp_dir):
    """清理临时文件"""
    print("\n" + "=" * 60)
    print("清理临时文件")
    print("=" * 60)

    if temp_dir and os.path.exists(temp_dir):
        try:
            shutil.rmtree(temp_dir)
            print(f"✅ 已清理临时目录: {temp_dir}")
        except Exception as e:
            print(f"⚠️ 清理失败: {e}")


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("Git HTTP 协议手动测试")
    print("=" * 60)
    print(f"服务器地址: {BASE_URL}")
    print(f"测试用户: {TEST_USERNAME}")
    print(f"测试仓库: {TEST_REPO_NAME}")
    print("=" * 60)

    temp_dir = None
    clone_dir = None

    try:
        # 步骤 1: 创建用户
        user = create_user()
        if not user:
            print("\n❌ 测试中止: 无法创建用户")
            return

        # 步骤 2: 创建仓库
        repo = create_repository(user.get("id"))
        if not repo:
            print("\n❌ 测试中止: 无法创建仓库")
            return

        # 步骤 3: 测试引用发现
        if not test_git_refs_discovery():
            print("\n⚠️ 引用发现测试失败，继续其他测试...")

        # 步骤 4: 测试 Git Clone
        temp_dir, clone_dir = test_git_clone()
        if not clone_dir:
            print("\n❌ 测试中止: Git Clone 失败")
            return

        # 步骤 5: 测试 Git Push
        if not test_git_push(clone_dir):
            print("\n⚠️ Git Push 测试失败，继续其他测试...")

        # 步骤 6: 测试 Git Pull
        if not test_git_pull(clone_dir):
            print("\n⚠️ Git Pull 测试失败")

        print("\n" + "=" * 60)
        print("✅ 所有测试完成!")
        print("=" * 60)

    except KeyboardInterrupt:
        print("\n\n⚠️ 测试被用户中断")

    finally:
        cleanup(temp_dir)


if __name__ == "__main__":
    # 检查服务器是否运行
    print("检查服务器状态...")
    try:
        response = httpx.get(f"{BASE_URL}/health", timeout=5.0)
        if response.status_code == 200:
            print(f"✅ 服务器运行正常")
            main()
        else:
            print(f"❌ 服务器返回异常状态码: {response.status_code}")
            print(f"请确保服务器已启动: python langit_cli.py server start")
    except Exception as e:
        print(f"❌ 无法连接到服务器: {e}")
        print(f"请确保服务器已启动: python langit_cli.py server start")
        print(f"服务器地址: {BASE_URL}")
