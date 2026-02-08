"""
Git 工具模块测试脚本

测试 git_utils.py 的功能
"""
import os
import sys
import tempfile
import shutil

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from client.utils.git_utils import (
    init_bare_repo,
    repo_exists,
    get_repo_info,
    get_repository_storage_path,
    ensure_repository_root,
    GitError
)


def test_init_bare_repo():
    """测试创建 bare 仓库"""
    print("\n=== 测试 init_bare_repo ===")

    # 创建临时目录
    temp_dir = tempfile.mkdtemp()
    repo_path = os.path.join(temp_dir, "test-repo.git")

    try:
        # 测试创建新仓库
        result = init_bare_repo(repo_path)
        assert result == True, "应该返回 True 表示新创建"
        assert os.path.exists(repo_path), "仓库目录应该存在"
        assert os.path.exists(os.path.join(repo_path, "HEAD")), "HEAD 文件应该存在"
        print(f"✅ 创建新仓库成功: {repo_path}")

        # 测试重复创建（应该返回 False）
        result = init_bare_repo(repo_path)
        assert result == False, "应该返回 False 表示已存在"
        print("✅ 重复创建检测正确")

    finally:
        # 清理
        shutil.rmtree(temp_dir)
        print(f"✅ 清理临时目录: {temp_dir}")


def test_repo_exists():
    """测试仓库存在检查"""
    print("\n=== 测试 repo_exists ===")

    temp_dir = tempfile.mkdtemp()
    repo_path = os.path.join(temp_dir, "test-repo.git")

    try:
        # 测试不存在的路径
        assert repo_exists(repo_path) == False, "不存在的路径应该返回 False"
        print("✅ 不存在的路径检测正确")

        # 创建仓库
        init_bare_repo(repo_path)

        # 测试存在的仓库
        assert repo_exists(repo_path) == True, "存在的仓库应该返回 True"
        print("✅ 存在的仓库检测正确")

    finally:
        shutil.rmtree(temp_dir)


def test_get_repo_info():
    """测试获取仓库信息"""
    print("\n=== 测试 get_repo_info ===")

    temp_dir = tempfile.mkdtemp()
    repo_path = os.path.join(temp_dir, "test-repo.git")

    try:
        # 创建仓库
        init_bare_repo(repo_path)

        # 获取信息
        info = get_repo_info(repo_path)

        assert "branches" in info, "应该包含 branches"
        assert "head_commit" in info, "应该包含 head_commit"
        assert "is_bare" in info, "应该包含 is_bare"
        assert info["is_bare"] == True, "应该是 bare 仓库"
        print(f"✅ 仓库信息: {info}")

    finally:
        shutil.rmtree(temp_dir)


def test_ensure_repository_root():
    """测试确保仓库根目录存在"""
    print("\n=== 测试 ensure_repository_root ===")

    temp_dir = tempfile.mkdtemp()
    repo_root = os.path.join(temp_dir, "repositories")

    try:
        # 确保目录不存在
        assert not os.path.exists(repo_root), "目录应该不存在"

        # 确保目录存在
        result = ensure_repository_root(repo_root)

        assert os.path.exists(repo_root), "目录应该被创建"
        assert result == os.path.abspath(repo_root), "应该返回绝对路径"
        print(f"✅ 仓库根目录创建成功: {result}")

    finally:
        shutil.rmtree(temp_dir)


def test_get_repository_storage_path():
    """测试获取仓库物理存储路径"""
    print("\n=== 测试 get_repository_storage_path ===")

    repo_root = "/data/repositories"
    repo_path = "/repos/test-project"

    result = get_repository_storage_path(repo_path, repo_root)
    # 使用 os.path.join 构建期望路径，兼容 Windows 和 Linux
    expected = os.path.join(repo_root, "repos", "test-project")

    assert result == expected, f"路径应该是 {expected}, 实际是 {result}"
    print(f"✅ 存储路径正确: {result}")


def main():
    """运行所有测试"""
    print("=" * 60)
    print("开始测试 Git 工具模块")
    print("=" * 60)

    try:
        test_init_bare_repo()
        test_repo_exists()
        test_get_repo_info()
        test_ensure_repository_root()
        test_get_repository_storage_path()

        print("\n" + "=" * 60)
        print("✅ 所有测试通过！")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
