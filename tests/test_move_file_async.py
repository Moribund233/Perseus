"""
文件重命名/移动端点测试

POST /api/v1/repositories/{repo_id}/contents/move
单次提交内完成 copy+delete（git 语义即 rename），保留文件内容与历史。
"""
import pytest
from fastapi.testclient import TestClient

from services.token_service import create_access_token
from tests.test_repo_browser_controller import create_repo_with_content, create_commit_in_repo


def _auth_headers(user) -> dict:
    token = create_access_token({
        "sub": str(user.id),
        "username": user.username,
        "is_admin": user.is_admin,
    })
    return {"Authorization": f"Bearer {token}"}


def _blob(test_client, repo_id, path: str):
    return test_client.get(
        f"/api/v1/repositories/{repo_id}/blob",
        params={"path": path, "ref": "master"},
    )


class TestMoveFileEndpoint:

    def test_move_file_in_repo(self, test_client: TestClient, db, test_user):
        """移动文件: 新路径可读且内容保留, 旧路径消失, 单次提交"""
        repo, physical_path = create_repo_with_content(db, "move-basic", owner_id=test_user.id)
        create_commit_in_repo(physical_path, "old.txt", b"hello move")

        response = test_client.post(
            f"/api/v1/repositories/{repo.id}/contents/move",
            json={"from_path": "old.txt", "to_path": "docs/new.txt"},
            headers=_auth_headers(test_user),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["from"] == "old.txt"
        assert data["to"] == "docs/new.txt"
        assert data["commit_id"]

        new_blob = _blob(test_client, repo.id, "docs/new.txt")
        assert new_blob.status_code == 200
        assert "hello move" in str(new_blob.json().get("content", ""))

        old_blob = _blob(test_client, repo.id, "old.txt")
        assert old_blob.status_code in (404, 422)

    def test_move_file_into_existing_directory(self, test_client: TestClient, db, test_user):
        """移动到已存在目录下应创建子路径条目"""
        repo, physical_path = create_repo_with_content(db, "move-into-dir", owner_id=test_user.id)
        create_commit_in_repo(physical_path, "src/main.py", b"def main(): pass")
        create_commit_in_repo(physical_path, "top.txt", b"top level")

        response = test_client.post(
            f"/api/v1/repositories/{repo.id}/contents/move",
            json={"from_path": "top.txt", "to_path": "src/top.txt"},
            headers=_auth_headers(test_user),
        )
        assert response.status_code == 200
        assert _blob(test_client, repo.id, "src/top.txt").status_code == 200
        assert _blob(test_client, repo.id, "src/main.py").status_code == 200

    def test_move_missing_source_404(self, test_client: TestClient, db, test_user):
        repo, physical_path = create_repo_with_content(db, "move-missing", owner_id=test_user.id)
        create_commit_in_repo(physical_path, "a.txt", b"a")

        response = test_client.post(
            f"/api/v1/repositories/{repo.id}/contents/move",
            json={"from_path": "nope.txt", "to_path": "b.txt"},
            headers=_auth_headers(test_user),
        )
        assert response.status_code == 404

    def test_move_destination_exists_409(self, test_client: TestClient, db, test_user):
        repo, physical_path = create_repo_with_content(db, "move-conflict", owner_id=test_user.id)
        create_commit_in_repo(physical_path, "a.txt", b"a")
        create_commit_in_repo(physical_path, "b.txt", b"b")

        response = test_client.post(
            f"/api/v1/repositories/{repo.id}/contents/move",
            json={"from_path": "a.txt", "to_path": "b.txt"},
            headers=_auth_headers(test_user),
        )
        assert response.status_code == 409

    def test_move_same_path_400(self, test_client: TestClient, db, test_user):
        repo, physical_path = create_repo_with_content(db, "move-same", owner_id=test_user.id)
        create_commit_in_repo(physical_path, "a.txt", b"a")

        response = test_client.post(
            f"/api/v1/repositories/{repo.id}/contents/move",
            json={"from_path": "a.txt", "to_path": "a.txt"},
            headers=_auth_headers(test_user),
        )
        assert response.status_code == 400

    def test_move_directory_rejected_400(self, test_client: TestClient, db, test_user):
        repo, physical_path = create_repo_with_content(db, "move-dir", owner_id=test_user.id)
        create_commit_in_repo(physical_path, "src/main.py", b"x=1")

        response = test_client.post(
            f"/api/v1/repositories/{repo.id}/contents/move",
            json={"from_path": "src", "to_path": "lib"},
            headers=_auth_headers(test_user),
        )
        assert response.status_code == 400

    def test_move_requires_auth_401(self, test_client: TestClient, db, test_user):
        repo, physical_path = create_repo_with_content(db, "move-auth", owner_id=test_user.id)
        create_commit_in_repo(physical_path, "a.txt", b"a")

        response = test_client.post(
            f"/api/v1/repositories/{repo.id}/contents/move",
            json={"from_path": "a.txt", "to_path": "b.txt"},
        )
        assert response.status_code == 401

    def test_move_repo_not_found_404(self, test_client: TestClient, test_user):
        response = test_client.post(
            "/api/v1/repositories/00000000-0000-0000-0000-000000000000/contents/move",
            json={"from_path": "a.txt", "to_path": "b.txt"},
            headers=_auth_headers(test_user),
        )
        assert response.status_code == 404
