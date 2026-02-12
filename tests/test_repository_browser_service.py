"""
仓库代码浏览服务层测试

测试范围:
1. 文件树浏览 - get_tree_entries
2. 文件内容查看 - get_blob_content
3. 提交历史 - get_commits
4. 代码对比 - get_diff
"""

import stat


def remove_readonly(func, path, excinfo):
    """Windows 下删除只读文件的回调函数"""
    os.chmod(path, stat.S_IWRITE)
    func(path)

import pytest
import os
import tempfile
import shutil
import stat
from datetime import datetime

import pygit2

from services.repository_browser_service import (
    get_tree_entries,
    get_blob_content,
    get_commits,
    get_diff
)
from exception import RepositoryBrowserException
from utils.git_utils import init_bare_repo, get_repository_storage_path


# ==================== Fixtures ====================

@pytest.fixture
def temp_repo_path():
    """创建临时仓库目录"""
    temp_dir = tempfile.mkdtemp()
    repo_path = os.path.join(temp_dir, "test_repo.git")
    yield repo_path
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def sample_bare_repo(temp_repo_path):
    """创建包含示例文件的 bare 仓库"""
    # 初始化 bare 仓库
    init_bare_repo(temp_repo_path)
    
    # 创建临时工作目录来添加文件
    work_dir = tempfile.mkdtemp()
    try:
        # Clone bare 仓库到工作目录
        repo = pygit2.clone_repository(temp_repo_path, work_dir, bare=False)
        
        # 创建一些文件
        os.makedirs(os.path.join(work_dir, "src", "components"), exist_ok=True)
        
        # 根目录文件
        with open(os.path.join(work_dir, "README.md"), "w") as f:
            f.write("# Test Repository\n")
        
        with open(os.path.join(work_dir, ".gitignore"), "w") as f:
            f.write("*.pyc\n__pycache__/\n")
        
        # src 目录文件
        with open(os.path.join(work_dir, "src", "app.py"), "w") as f:
            f.write("import os\n\ndef main():\n    pass\n")
        
        with open(os.path.join(work_dir, "src", "utils.py"), "w") as f:
            f.write("def helper():\n    return True\n")
        
        # components 目录文件
        with open(os.path.join(work_dir, "src", "components", "Button.vue"), "w") as f:
            f.write("<template>\n  <button>Click</button>\n</template>\n")
        
        # 提交文件
        signature = pygit2.Signature("Test User", "test@example.com", int(datetime.now().timestamp()), 0)
        
        # 添加所有文件
        index = repo.index
        index.add_all()
        index.write()
        
        # 创建提交
        tree = index.write_tree()
        repo.create_commit(
            "HEAD",
            signature,
            signature,
            "Initial commit",
            tree,
            []
        )
        
        # 推送回 bare 仓库
        remote = repo.remotes["origin"]
        remote.push(["refs/heads/master:refs/heads/master"])
        
        repo.free()
        
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)
    
    return temp_repo_path


# ==================== 文件树浏览测试 ====================

class TestGetTreeEntries:
    """测试获取文件树条目"""
    
    def test_get_root_tree(self, sample_bare_repo):
        """测试获取根目录文件树"""
        result = get_tree_entries(sample_bare_repo, ref="master", path="")
        
        assert result["path"] == ""
        assert result["ref"] == "master"
        assert "entries" in result
        assert isinstance(result["entries"], list)
        assert len(result["entries"]) == 3  # README.md, .gitignore, src/
        
        # 检查条目类型
        entry_names = {e["name"] for e in result["entries"]}
        assert "README.md" in entry_names
        assert ".gitignore" in entry_names
        assert "src" in entry_names
    
    def test_get_subdir_tree(self, sample_bare_repo):
        """测试获取子目录文件树"""
        result = get_tree_entries(sample_bare_repo, ref="master", path="src")
        
        assert result["path"] == "src"
        assert len(result["entries"]) == 3  # app.py, utils.py, components/
        
        entry_names = {e["name"] for e in result["entries"]}
        assert "app.py" in entry_names
        assert "utils.py" in entry_names
        assert "components" in entry_names
    
    def test_get_nested_subdir_tree(self, sample_bare_repo):
        """测试获取嵌套子目录文件树"""
        result = get_tree_entries(sample_bare_repo, ref="master", path="src/components")
        
        assert result["path"] == "src/components"
        assert len(result["entries"]) == 1
        assert result["entries"][0]["name"] == "Button.vue"
        assert result["entries"][0]["type"] == "blob"
    
    def test_get_tree_with_nonexistent_path(self, sample_bare_repo):
        """测试获取不存在的路径"""
        with pytest.raises(RepositoryBrowserException) as exc_info:
            get_tree_entries(sample_bare_repo, ref="master", path="nonexistent")

        assert "not found" in str(exc_info.value).lower()

    def test_get_tree_with_nonexistent_ref(self, sample_bare_repo):
        """测试获取不存在的分支"""
        with pytest.raises(RepositoryBrowserException) as exc_info:
            get_tree_entries(sample_bare_repo, ref="nonexistent-branch", path="")

        assert "not found" in str(exc_info.value).lower()

    def test_get_tree_with_invalid_repo(self):
        """测试无效的仓库路径"""
        with pytest.raises(RepositoryBrowserException):
            get_tree_entries("/invalid/path", ref="master", path="")
    
    def test_tree_entry_structure(self, sample_bare_repo):
        """测试文件树条目结构"""
        result = get_tree_entries(sample_bare_repo, ref="master", path="")
        
        for entry in result["entries"]:
            assert "name" in entry
            assert "type" in entry
            assert entry["type"] in ["tree", "blob"]
            assert "mode" in entry
            assert "sha" in entry
            
            if entry["type"] == "blob":
                assert "size" in entry
                assert isinstance(entry["size"], int)


# ==================== 文件内容查看测试 ====================

class TestGetBlobContent:
    """测试获取文件内容"""
    
    def test_get_text_file_content(self, sample_bare_repo):
        """测试获取文本文件内容"""
        result = get_blob_content(sample_bare_repo, ref="master", path="README.md")
        
        assert result["path"] == "README.md"
        assert result["ref"] == "master"
        assert "content" in result
        assert result["content"] == "# Test Repository\n"
        assert result["encoding"] == "utf-8"
        assert result["is_binary"] is False
        assert "size" in result
        assert "sha" in result
    
    def test_get_nested_file_content(self, sample_bare_repo):
        """测试获取嵌套目录中的文件内容"""
        result = get_blob_content(sample_bare_repo, ref="master", path="src/app.py")
        
        assert result["path"] == "src/app.py"
        assert "def main():" in result["content"]
        assert result["is_binary"] is False
    
    def test_get_nonexistent_file(self, sample_bare_repo):
        """测试获取不存在的文件"""
        with pytest.raises(RepositoryBrowserException) as exc_info:
            get_blob_content(sample_bare_repo, ref="master", path="nonexistent.py")

        assert "not found" in str(exc_info.value).lower()

    def test_get_directory_as_file(self, sample_bare_repo):
        """测试将目录作为文件获取"""
        with pytest.raises(RepositoryBrowserException) as exc_info:
            get_blob_content(sample_bare_repo, ref="master", path="src")

        assert "is a directory" in str(exc_info.value).lower() or "not a file" in str(exc_info.value).lower()


# ==================== 提交历史测试 ====================

class TestGetCommits:
    """测试获取提交历史"""
    
    def test_get_commits_basic(self, sample_bare_repo):
        """测试基本提交历史获取"""
        result = get_commits(sample_bare_repo, ref="master")
        
        assert "commits" in result
        assert isinstance(result["commits"], list)
        assert len(result["commits"]) >= 1
        
        # 检查提交结构
        commit = result["commits"][0]
        assert "sha" in commit
        assert "message" in commit
        assert "author" in commit
        assert "name" in commit["author"]
        assert "email" in commit["author"]
        assert "date" in commit
        assert "parents" in commit
    
    def test_get_commits_with_pagination(self, sample_bare_repo):
        """测试分页获取提交"""
        result = get_commits(sample_bare_repo, ref="master", page=1, per_page=10)
        
        assert "pagination" in result
        assert result["pagination"]["page"] == 1
        assert result["pagination"]["per_page"] == 10
    
    def test_get_commits_with_nonexistent_ref(self, sample_bare_repo):
        """测试获取不存在的分支提交"""
        with pytest.raises(RepositoryBrowserException):
            get_commits(sample_bare_repo, ref="nonexistent-branch")


# ==================== 代码对比测试 ====================

class TestGetDiff:
    """测试获取代码差异"""
    
    def test_get_diff_between_commits(self, sample_bare_repo):
        """测试获取两个提交之间的差异"""
        # 获取提交列表
        commits_result = get_commits(sample_bare_repo, ref="master")
        commits = commits_result["commits"]
        
        if len(commits) >= 1:
            # 只有一个提交时，对比与空树
            head = commits[0]["sha"]
            result = get_diff(sample_bare_repo, base=None, head=head)
            
            assert "files" in result
            assert isinstance(result["files"], list)
    
    def test_get_diff_with_nonexistent_commit(self, sample_bare_repo):
        """测试获取不存在的提交差异"""
        with pytest.raises(RepositoryBrowserException):
            get_diff(sample_bare_repo, base="invalid", head="also-invalid")
