"""
Git Tag 管理端点 HTTP 集成测试

覆盖 controller/tag_controller.py：
- GET    /{repo_id}/tags
- GET    /{repo_id}/tags/{tag_name}
- POST   /{repo_id}/tags
- DELETE /{repo_id}/tags/{tag_name}
"""
import pygit2
from fastapi.testclient import TestClient

from utils.git_utils import init_bare_repo, get_repository_storage_path


def create_repo_with_commit(db, name: str, with_commit: bool = True):
    """创建仓库记录 + 物理 bare 仓库（可选初始提交）"""
    from tests.test_helpers import create_test_repo

    repo = create_test_repo(db, name=name, path=f"testuser/{name}")
    repo.default_branch = "master"
    db.commit()
    db.refresh(repo)

    physical_path = get_repository_storage_path(repo.path)
    init_bare_repo(physical_path)

    commit_sha = None
    if with_commit:
        git_repo = pygit2.Repository(physical_path)
        signature = pygit2.Signature("Test User", "test@example.com")
        builder = git_repo.TreeBuilder()
        blob_id = git_repo.create_blob(b"hello\n")
        builder.insert("README.md", blob_id, pygit2.GIT_FILEMODE_BLOB)
        tree_id = builder.write()
        oid = git_repo.create_commit(
            "refs/heads/master", signature, signature, "initial", tree_id, []
        )
        commit_sha = str(oid)

    return repo, physical_path, commit_sha


class TestListTags:
    def test_list_empty(self, test_client: TestClient, db):
        repo, _, _ = create_repo_with_commit(db, "tags-empty")
        response = test_client.get(f"/api/v1/repositories/{repo.id}/tags")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_no_auth(self, test_client: TestClient, db):
        repo, _, _ = create_repo_with_commit(db, "tags-list-noauth")
        response = test_client.get(f"/api/v1/repositories/{repo.id}/tags")
        assert response.status_code != 401

    def test_list_repo_not_found(self, test_client: TestClient):
        response = test_client.get("/api/v1/repositories/00000000-0000-0000-0000-000000000000/tags")
        assert response.status_code == 404


class TestCreateTag:
    def test_create_annotated_and_persist(self, test_client: TestClient, db, auth_headers):
        repo, physical_path, sha = create_repo_with_commit(db, "tags-create")

        response = test_client.post(
            f"/api/v1/repositories/{repo.id}/tags",
            json={"name": "v1.0.0", "message": "first release"},
            headers=auth_headers,
        )
        assert response.status_code == 201, response.text
        assert response.json()["name"] == "v1.0.0"
        assert response.json()["commit_hash"] == sha

        git_repo = pygit2.Repository(physical_path)
        assert "refs/tags/v1.0.0" in git_repo.listall_references()

        listed = test_client.get(f"/api/v1/repositories/{repo.id}/tags").json()
        assert [t["name"] for t in listed] == ["v1.0.0"]

    def test_create_lightweight_defaults_to_head(self, test_client: TestClient, db, auth_headers):
        repo, physical_path, sha = create_repo_with_commit(db, "tags-light")
        response = test_client.post(
            f"/api/v1/repositories/{repo.id}/tags",
            json={"name": "v0.1.0"},
            headers=auth_headers,
        )
        assert response.status_code == 201, response.text
        assert response.json()["commit_hash"] == sha

    def test_create_pattern_filter(self, test_client: TestClient, db, auth_headers):
        repo, _, _ = create_repo_with_commit(db, "tags-pattern")
        for name in ("v1.0.0", "v2.0.0", "nightly"):
            test_client.post(
                f"/api/v1/repositories/{repo.id}/tags",
                json={"name": name},
                headers=auth_headers,
            )

        response = test_client.get(
            f"/api/v1/repositories/{repo.id}/tags", params={"pattern": "v1.*"}
        )
        assert response.status_code == 200
        assert [t["name"] for t in response.json()] == ["v1.0.0"]

    def test_create_requires_auth(self, test_client: TestClient, db):
        repo, _, _ = create_repo_with_commit(db, "tags-create-noauth")
        response = test_client.post(
            f"/api/v1/repositories/{repo.id}/tags", json={"name": "v1.0.0"}
        )
        assert response.status_code == 401

    def test_create_repo_not_found(self, test_client: TestClient, auth_headers):
        response = test_client.post(
            "/api/v1/repositories/00000000-0000-0000-0000-000000000000/tags",
            json={"name": "v1.0.0"},
            headers=auth_headers,
        )
        assert response.status_code == 404

    def test_create_no_commit(self, test_client: TestClient, db, auth_headers):
        repo, _, _ = create_repo_with_commit(db, "tags-nocommit", with_commit=False)
        response = test_client.post(
            f"/api/v1/repositories/{repo.id}/tags",
            json={"name": "v1.0.0"},
            headers=auth_headers,
        )
        assert response.status_code == 400


class TestGetTag:
    def test_get_existing(self, test_client: TestClient, db, auth_headers):
        repo, _, sha = create_repo_with_commit(db, "tags-get")
        test_client.post(
            f"/api/v1/repositories/{repo.id}/tags",
            json={"name": "v1.0.0", "message": "note"},
            headers=auth_headers,
        )

        response = test_client.get(f"/api/v1/repositories/{repo.id}/tags/v1.0.0")
        assert response.status_code == 200
        assert response.json()["commit_hash"] == sha

    def test_get_missing(self, test_client: TestClient, db):
        repo, _, _ = create_repo_with_commit(db, "tags-get-missing")
        response = test_client.get(f"/api/v1/repositories/{repo.id}/tags/nope")
        assert response.status_code == 404


class TestDeleteTag:
    def test_delete_removes_tag(self, test_client: TestClient, db, auth_headers):
        repo, physical_path, _ = create_repo_with_commit(db, "tags-delete")
        test_client.post(
            f"/api/v1/repositories/{repo.id}/tags",
            json={"name": "v1.0.0"},
            headers=auth_headers,
        )

        response = test_client.delete(
            f"/api/v1/repositories/{repo.id}/tags/v1.0.0", headers=auth_headers
        )
        assert response.status_code == 204

        git_repo = pygit2.Repository(physical_path)
        assert "refs/tags/v1.0.0" not in git_repo.listall_references()
        assert test_client.get(f"/api/v1/repositories/{repo.id}/tags/v1.0.0").status_code == 404

    def test_delete_requires_auth(self, test_client: TestClient, db):
        repo, _, _ = create_repo_with_commit(db, "tags-delete-noauth")
        response = test_client.delete(f"/api/v1/repositories/{repo.id}/tags/v1.0.0")
        assert response.status_code == 401
