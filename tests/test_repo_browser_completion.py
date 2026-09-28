"""
Git 浏览器能力补齐（Blame / Commit Graph / Compare）HTTP 集成测试

覆盖 repository_browser_controller.py 新增端点：
- GET /{repo_id}/blame: 行级追溯
- GET /{repo_id}/graph: 提交图（拓扑序 + 引用标签）
- GET /{repo_id}/compare: 跨引用对比
"""
import pygit2
from fastapi.testclient import TestClient

from utils.git_utils import init_bare_repo, get_repository_storage_path


# ============ 辅助函数 ============

def create_repo(db, name: str):
    """创建数据库记录 + 物理 bare 仓库"""
    from tests.test_helpers import create_test_repo

    repo = create_test_repo(db, name=name, path=f"testuser/{name}")
    repo.default_branch = "master"
    db.commit()
    db.refresh(repo)

    physical_path = get_repository_storage_path(repo.path)
    init_bare_repo(physical_path)
    return repo, physical_path


def create_commit(physical_path: str, ref: str, parents: list,
                  filename: str, content: bytes, message: str):
    """在指定引用上创建一条提交（继承父提交树 + 插入文件）"""
    repo = pygit2.Repository(physical_path)
    existing_tree_id = repo[parents[0]].tree_id if parents else None
    builder = repo.TreeBuilder(existing_tree_id) if existing_tree_id else repo.TreeBuilder()
    blob_id = repo.create_blob(content)
    builder.insert(filename, blob_id, pygit2.GIT_FILEMODE_BLOB)
    tree_id = builder.write()
    signature = pygit2.Signature("Test User", "test@example.com")
    return repo.create_commit(ref, signature, signature, message, tree_id, parents)


# ============ Blame 端点测试 ============

class TestBlameEndpoint:
    """GET /{repo_id}/blame"""

    def test_blame_hunks_cover_all_lines(self, test_client: TestClient, db):
        repo, physical_path = create_repo(db, "blame-basic")
        c1 = create_commit(physical_path, "refs/heads/master", [], "a.txt", b"line1\nline2\n", "first")
        create_commit(physical_path, "refs/heads/master", [c1], "a.txt", b"line1\nline2\nline3\n", "add line3")

        response = test_client.get(f"/api/v1/repositories/{repo.id}/blame", params={"path": "a.txt"})
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["path"] == "a.txt"
        assert sum(h["lines_in_hunk"] for h in data["hunks"]) == 3
        # 前两行来自第一条提交
        assert data["hunks"][0]["commit"]["sha"] == str(c1)
        assert data["hunks"][0]["final_start_line_number"] == 1

    def test_blame_no_auth(self, test_client: TestClient, db):
        repo, physical_path = create_repo(db, "blame-noauth")
        create_commit(physical_path, "refs/heads/master", [], "a.txt", b"x\n", "init")

        response = test_client.get(f"/api/v1/repositories/{repo.id}/blame", params={"path": "a.txt"})
        assert response.status_code != 401

    def test_blame_missing_path_param(self, test_client: TestClient, db):
        repo, physical_path = create_repo(db, "blame-nopath")
        create_commit(physical_path, "refs/heads/master", [], "a.txt", b"x\n", "init")

        response = test_client.get(f"/api/v1/repositories/{repo.id}/blame")
        assert response.status_code == 422

    def test_blame_file_not_found(self, test_client: TestClient, db):
        repo, physical_path = create_repo(db, "blame-nofile")
        create_commit(physical_path, "refs/heads/master", [], "a.txt", b"x\n", "init")

        response = test_client.get(f"/api/v1/repositories/{repo.id}/blame", params={"path": "nope.txt"})
        assert response.status_code == 404

    def test_blame_empty_repo(self, test_client: TestClient, db):
        repo, physical_path = create_repo(db, "blame-empty")

        response = test_client.get(f"/api/v1/repositories/{repo.id}/blame", params={"path": "a.txt"})
        assert response.status_code == 200
        assert response.json()["is_empty"] is True

    def test_blame_repo_not_found(self, test_client: TestClient):
        response = test_client.get(
            "/api/v1/repositories/00000000-0000-0000-0000-000000000000/blame",
            params={"path": "a.txt"},
        )
        assert response.status_code == 404


# ============ Commit Graph 端点测试 ============

class TestGraphEndpoint:
    """GET /{repo_id}/graph"""

    def test_graph_nodes_and_labels(self, test_client: TestClient, db):
        repo, physical_path = create_repo(db, "graph-basic")
        c1 = create_commit(physical_path, "refs/heads/master", [], "a.txt", b"1", "first")
        c2 = create_commit(physical_path, "refs/heads/master", [c1], "a.txt", b"2", "second")

        git_repo = pygit2.Repository(physical_path)
        git_repo.references.create("refs/heads/feature", c1)
        git_repo.references.create("refs/tags/v1.0", c1)

        response = test_client.get(f"/api/v1/repositories/{repo.id}/graph")
        assert response.status_code == 200, response.text
        data = response.json()
        shas = [c["sha"] for c in data["commits"]]
        assert str(c2) in shas and str(c1) in shas

        c1_node = next(c for c in data["commits"] if c["sha"] == str(c1))
        assert "feature" in c1_node["labels"]
        assert any(label.startswith("tag:") for label in c1_node["labels"])

        c2_node = next(c for c in data["commits"] if c["sha"] == str(c2))
        assert "HEAD" in c2_node["labels"]
        assert c2_node["parents"] == [str(c1)]

    def test_graph_limit(self, test_client: TestClient, db):
        repo, physical_path = create_repo(db, "graph-limit")
        parent = []
        for i in range(5):
            parent = [create_commit(physical_path, "refs/heads/master", parent, f"f{i}.txt", b"x", f"c{i}")]

        response = test_client.get(f"/api/v1/repositories/{repo.id}/graph", params={"limit": 2})
        assert response.status_code == 200
        assert len(response.json()["commits"]) == 2

    def test_graph_empty_repo(self, test_client: TestClient, db):
        repo, physical_path = create_repo(db, "graph-empty")

        response = test_client.get(f"/api/v1/repositories/{repo.id}/graph")
        assert response.status_code == 200
        assert response.json()["is_empty"] is True

    def test_graph_bad_ref(self, test_client: TestClient, db):
        repo, physical_path = create_repo(db, "graph-badref")
        create_commit(physical_path, "refs/heads/master", [], "a.txt", b"x", "init")

        response = test_client.get(f"/api/v1/repositories/{repo.id}/graph", params={"ref": "nope"})
        assert response.status_code == 404

    def test_graph_repo_not_found(self, test_client: TestClient):
        response = test_client.get("/api/v1/repositories/00000000-0000-0000-0000-000000000000/graph")
        assert response.status_code == 404


# ============ Compare 端点测试 ============

class TestCompareEndpoint:
    """GET /{repo_id}/compare"""

    def test_compare_ahead_and_files(self, test_client: TestClient, db):
        repo, physical_path = create_repo(db, "compare-basic")
        c1 = create_commit(physical_path, "refs/heads/master", [], "a.txt", b"one\n", "first")
        create_commit(physical_path, "refs/heads/master", [c1], "a.txt", b"one\ntwo\n", "second")
        c3 = create_commit(physical_path, "refs/heads/feature", [c1], "feature.txt", b"feat\n", "feature")

        response = test_client.get(
            f"/api/v1/repositories/{repo.id}/compare",
            params={"base": "master", "head": "feature"},
        )
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["ahead_by"] == 1
        assert [c["sha"] for c in data["commits"]] == [str(c3)]
        assert data["merge_base"] == str(c1)
        assert "feature.txt" in {f["new_path"] for f in data["files"]}
        assert data["stats"]["files_changed"] >= 1

    def test_compare_missing_params(self, test_client: TestClient, db):
        repo, physical_path = create_repo(db, "compare-noparams")
        create_commit(physical_path, "refs/heads/master", [], "a.txt", b"x", "init")

        response = test_client.get(f"/api/v1/repositories/{repo.id}/compare", params={"base": "master"})
        assert response.status_code == 422

    def test_compare_bad_ref(self, test_client: TestClient, db):
        repo, physical_path = create_repo(db, "compare-badref")
        create_commit(physical_path, "refs/heads/master", [], "a.txt", b"x", "init")

        response = test_client.get(
            f"/api/v1/repositories/{repo.id}/compare",
            params={"base": "master", "head": "nope"},
        )
        assert response.status_code == 404

    def test_compare_repo_not_found(self, test_client: TestClient):
        response = test_client.get(
            "/api/v1/repositories/00000000-0000-0000-0000-000000000000/compare",
            params={"base": "master", "head": "feature"},
        )
        assert response.status_code == 404
