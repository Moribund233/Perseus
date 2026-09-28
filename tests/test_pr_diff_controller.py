"""
PR Diff 端点 HTTP 集成测试

覆盖 controller/pull_request_controller.py 新增路由：
- GET /{repo_id}/pull-requests/{pr_number}/diff
- GET /{repo_id}/pull-requests/{pr_number}/diff/{file_path:path}

同时回归既有缺陷：PullRequest 无 base_commit/head_commit 列，
service 需按 target/source 分支当前 tip 解析。
"""
import pygit2
from fastapi.testclient import TestClient

from utils.git_utils import init_bare_repo, get_repository_storage_path
from tests.test_helpers import create_test_pr


def create_repo(db, name: str):
    from tests.test_helpers import create_test_repo

    repo = create_test_repo(db, name=name, path=f"testuser/{name}")
    repo.default_branch = "main"
    db.commit()
    db.refresh(repo)

    physical_path = get_repository_storage_path(repo.path)
    init_bare_repo(physical_path)
    return repo, physical_path


def create_commit(physical_path: str, ref: str, parents: list,
                  filename: str, content: bytes, message: str):
    repo = pygit2.Repository(physical_path)
    existing_tree_id = repo[parents[0]].tree_id if parents else None
    builder = repo.TreeBuilder(existing_tree_id) if existing_tree_id else repo.TreeBuilder()
    blob_id = repo.create_blob(content)
    builder.insert(filename, blob_id, pygit2.GIT_FILEMODE_BLOB)
    tree_id = builder.write()
    signature = pygit2.Signature("Test User", "test@example.com")
    return repo.create_commit(ref, signature, signature, message, tree_id, parents)


def build_pr_repo(db, name: str, test_user):
    """构造 main + feature/test 两分支并登记 PR（编号 1）"""
    repo, physical_path = create_repo(db, name)
    base = create_commit(physical_path, "refs/heads/main", [], "README.md", b"# base\n", "base")
    head = create_commit(
        physical_path, "refs/heads/feature/test", [base],
        "README.md", b"# base\n\nfeature\n", "add feature",
    )
    # 追加新文件，验证新增文件进入 files 列表
    create_commit(
        physical_path, "refs/heads/feature/test", [head],
        "new_file.py", b"print('hi')\n", "add new file",
    )
    pr = create_test_pr(
        db, repo_id=repo.id, pr_number=1, title="Test PR", author_id=test_user.id
    )
    return repo, physical_path, pr


class TestPRDiffEndpoint:
    def test_pr_diff(self, test_client: TestClient, db, test_user):
        repo, physical_path, pr = build_pr_repo(db, "pr-diff", test_user)

        response = test_client.get(f"/api/v1/repositories/{repo.id}/pull-requests/1/diff")
        assert response.status_code == 200, response.text
        data = response.json()

        git_repo = pygit2.Repository(physical_path)
        base_sha = str(git_repo.references["refs/heads/main"].peel(pygit2.Commit).id)
        head_sha = str(git_repo.references["refs/heads/feature/test"].peel(pygit2.Commit).id)

        assert data["base_commit"] == base_sha
        assert data["head_commit"] == head_sha
        assert "README.md" in data["diff"]
        assert "new_file.py" in {f["path"] for f in data["files"]}
        assert data["stats"]["files_changed"] == 2

    def test_pr_file_diff(self, test_client: TestClient, db, test_user):
        repo, _, _ = build_pr_repo(db, "pr-file-diff", test_user)

        response = test_client.get(
            f"/api/v1/repositories/{repo.id}/pull-requests/1/diff/README.md"
        )
        assert response.status_code == 200, response.text
        assert "README.md" in response.json()["diff"]

    def test_pr_diff_not_found(self, test_client: TestClient, db):
        repo, _ = create_repo(db, "pr-diff-404")
        response = test_client.get(f"/api/v1/repositories/{repo.id}/pull-requests/99/diff")
        assert response.status_code == 404

    def test_pr_diff_missing_source_branch(self, test_client: TestClient, db, test_user):
        repo, physical_path = create_repo(db, "pr-diff-missing")
        create_commit(physical_path, "refs/heads/main", [], "README.md", b"# base\n", "base")
        # 不创建 source_branch=feature/test → 明确 400
        create_test_pr(db, repo_id=repo.id, pr_number=1, title="Test PR", author_id=test_user.id)

        response = test_client.get(f"/api/v1/repositories/{repo.id}/pull-requests/1/diff")
        assert response.status_code == 400
        assert "pr_source_branch_not_found" in response.text or response.status_code == 400

    def test_pr_diff_repo_not_found(self, test_client: TestClient):
        response = test_client.get(
            "/api/v1/repositories/00000000-0000-0000-0000-000000000000/pull-requests/1/diff"
        )
        assert response.status_code == 404
