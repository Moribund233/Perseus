"""
仓库API测试类

使用认证后的客户端进行测试
"""
import pytest
from fastapi.testclient import TestClient


class TestRepositoryAPI:
    """
    仓库API测试类
    """

    def test_get_repositories_with_auth(self, test_client, auth_headers):
        """
        测试获取所有仓库（已认证）
        """
        response = test_client.get("/api/repositories/", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_repositories_without_auth(self, test_client):
        """
        测试获取所有仓库（未认证）- 应该返回403
        """
        response = test_client.get("/api/repositories/")
        assert response.status_code == 403

    def test_get_public_repositories(self, test_client):
        """
        测试获取所有公开仓库（不需要认证）
        """
        response = test_client.get("/api/repositories/public")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_repository_by_id_with_auth(self, test_client, auth_headers):
        """
        测试根据ID获取仓库（已认证）
        """
        response = test_client.get("/api/repositories/1", headers=auth_headers)
        # 如果仓库不存在，应该返回404
        if response.status_code == 404:
            assert "error" in response.json()
            assert "message" in response.json()["error"]
            assert "Repository not found" in response.json()["error"]["message"]
        else:
            # 如果仓库存在，应该返回200和仓库信息
            assert response.status_code == 200
            assert "id" in response.json()

    def test_get_repository_by_id_without_auth(self, test_client):
        """
        测试根据ID获取仓库（未认证）- 应该返回403
        """
        response = test_client.get("/api/repositories/1")
        assert response.status_code == 403

    def test_create_repository_with_auth(self, test_client, auth_headers):
        """
        测试创建新仓库（已认证）
        """
        repo_data = {
            "name": "test-repo",
            "path": "/repos/test-repo",
            "description": "Test repository",
            "is_public": True,
            "default_branch": "master"
        }

        response = test_client.post("/api/repositories/", json=repo_data, headers=auth_headers)

        # 检查响应状态码
        assert response.status_code == 200 or response.status_code == 409

        if response.status_code == 409:
            # 如果仓库路径已存在，应该返回409和错误信息
            assert "error" in response.json()
            assert "message" in response.json()["error"]
            assert "already exists" in response.json()["error"]["message"]
        else:
            # 如果仓库创建成功，应该返回200和仓库信息
            assert response.status_code == 200
            assert "id" in response.json()
            assert response.json()["name"] == repo_data["name"]
            assert response.json()["path"] == repo_data["path"]
            assert response.json()["is_public"] == repo_data["is_public"]
            assert response.json()["default_branch"] == repo_data["default_branch"]

    def test_create_repository_without_auth(self, test_client):
        """
        测试创建新仓库（未认证）- 应该返回403
        """
        repo_data = {
            "name": "test-repo",
            "path": "/repos/test-repo",
            "description": "Test repository",
            "is_public": True,
            "default_branch": "master"
        }

        response = test_client.post("/api/repositories/", json=repo_data)
        assert response.status_code == 403

    def test_update_repository_with_auth(self, test_client, auth_headers):
        """
        测试更新仓库信息（已认证）
        """
        # 首先创建测试仓库
        repo_data = {
            "name": "test-update-repo",
            "path": "/repos/test-update-repo",
            "description": "Test repository for update",
            "is_public": True,
            "default_branch": "master"
        }

        create_response = test_client.post("/api/repositories/", json=repo_data, headers=auth_headers)
        if create_response.status_code == 409:
            # 如果仓库已存在，跳过此测试
            pytest.skip("Repository already exists")

        assert create_response.status_code == 200
        repo_id = create_response.json()["id"]

        # 更新仓库信息
        update_data = {
            "description": "Updated test repository",
            "is_public": False
        }

        update_response = test_client.put(f"/api/repositories/{repo_id}", json=update_data, headers=auth_headers)

        # 检查响应状态码
        assert update_response.status_code == 200
        assert update_response.json()["id"] == repo_id
        assert update_response.json()["description"] == update_data["description"]
        assert update_response.json()["is_public"] == update_data["is_public"]

    def test_update_repository_without_auth(self, test_client):
        """
        测试更新仓库信息（未认证）- 应该返回403
        """
        update_data = {
            "description": "Updated test repository",
            "is_public": False
        }

        update_response = test_client.put("/api/repositories/1", json=update_data)
        assert update_response.status_code == 403

    def test_delete_repository_with_auth(self, test_client, auth_headers):
        """
        测试删除仓库（已认证）
        """
        # 首先创建测试仓库
        repo_data = {
            "name": "test-delete-repo",
            "path": "/repos/test-delete-repo",
            "description": "Test repository for deletion",
            "is_public": True,
            "default_branch": "master"
        }

        create_response = test_client.post("/api/repositories/", json=repo_data, headers=auth_headers)
        if create_response.status_code == 409:
            # 如果仓库已存在，跳过此测试
            pytest.skip("Repository already exists")

        assert create_response.status_code == 200
        repo_id = create_response.json()["id"]

        # 删除仓库
        delete_response = test_client.delete(f"/api/repositories/{repo_id}", headers=auth_headers)

        # 检查响应状态码
        assert delete_response.status_code == 200
        assert "message" in delete_response.json()
        assert "deleted successfully" in delete_response.json()["message"]

        # 验证仓库已被删除
        get_response = test_client.get(f"/api/repositories/{repo_id}", headers=auth_headers)
        assert get_response.status_code == 404

    def test_delete_repository_without_auth(self, test_client):
        """
        测试删除仓库（未认证）- 应该返回403
        """
        delete_response = test_client.delete("/api/repositories/1")
        assert delete_response.status_code == 403

    def test_check_repository_access_with_auth(self, test_client, auth_headers):
        """
        测试检查仓库访问权限（已认证）
        """
        # 首先创建测试仓库
        repo_data = {
            "name": "test-access-repo",
            "path": "/repos/test-access-repo",
            "description": "Test repository for access check",
            "is_public": True,
            "default_branch": "master"
        }

        repo_response = test_client.post("/api/repositories/", json=repo_data, headers=auth_headers)
        if repo_response.status_code == 409:
            # 如果仓库已存在，跳过此测试
            pytest.skip("Repository already exists")

        assert repo_response.status_code == 200
        repo_id = repo_response.json()["id"]
        user_id = repo_response.json()["owner_id"]

        response = test_client.get(f"/api/repositories/{repo_id}/access?user_id={user_id}", headers=auth_headers)
        # 检查响应状态码
        assert response.status_code == 200
        assert "has_access" in response.json()
        assert isinstance(response.json()["has_access"], bool)

    def test_check_repository_access_without_auth(self, test_client):
        """
        测试检查仓库访问权限（未认证）- 应该返回403
        """
        response = test_client.get("/api/repositories/1/access?user_id=1")
        assert response.status_code == 403
