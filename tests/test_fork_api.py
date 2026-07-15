"""
Fork API 集成测试

验证 Fork 控制器层的所有端点
"""
import pytest
from fastapi.testclient import TestClient

from models.repository import Repository
from utils.git_utils import init_bare_repo, get_repository_storage_path
from tests.test_helpers import create_test_repo as _create_test_repo


def create_test_repo(db, name: str = "source-repo") -> Repository:
    """创建测试仓库（含物理 Git 仓库初始化）"""
    repo = _create_test_repo(db, name=name)
    physical_path = get_repository_storage_path(repo.path)
    init_bare_repo(physical_path)
    return repo


# =============================================================================
# Fork 创建
# =============================================================================

def test_fork_repository_with_custom_name(test_client: TestClient, auth_headers: dict, db):
    """测试使用自定义名称 Fork 仓库"""
    repo = create_test_repo(db, name="src-repo-1")

    response = test_client.post(
        f"/api/v1/repositories/{repo.id}/forks",
        json={"name": "my-fork", "description": "My fork"},
        headers=auth_headers
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "my-fork"
    assert data["description"] == "My fork"
    assert data["is_fork"] is True
    assert data["forked_from_id"] == str(repo.id)


def test_fork_repository_requires_auth(test_client: TestClient, db):
    """测试未认证用户不能 Fork 仓库"""
    repo = create_test_repo(db, name="src-repo-2")

    response = test_client.post(
        f"/api/v1/repositories/{repo.id}/forks",
        json={}
    )

    assert response.status_code == 401


def test_fork_repository_not_found(test_client: TestClient, auth_headers: dict):
    """测试 Fork 不存在的仓库返回 404"""
    response = test_client.post(
        "/api/v1/repositories/00000000-0000-0000-0000-000000000000/forks",
        json={"name": "fork-1"},
        headers=auth_headers
    )

    assert response.status_code == 404


def test_fork_duplicate_forbidden(test_client: TestClient, auth_headers: dict, db):
    """测试重复 Fork 同一仓库返回错误"""
    repo = create_test_repo(db, name="src-repo-3")

    # 第一次 Fork 成功
    response1 = test_client.post(
        f"/api/v1/repositories/{repo.id}/forks",
        json={"name": "my-fork-1"},
        headers=auth_headers
    )
    assert response1.status_code == 201

    # 第二次 Fork 失败
    response2 = test_client.post(
        f"/api/v1/repositories/{repo.id}/forks",
        json={"name": "my-fork-2"},
        headers=auth_headers
    )
    assert response2.status_code == 400


# =============================================================================
# Fork 列表
# =============================================================================

def test_list_repository_forks(test_client: TestClient, auth_headers: dict, db):
    """测试获取仓库的 Fork 列表"""
    repo = create_test_repo(db, name="src-repo-4")

    # Fork 一次
    test_client.post(
        f"/api/v1/repositories/{repo.id}/forks",
        json={"name": "fork-of-4"},
        headers=auth_headers
    )

    # 获取 Fork 列表
    response = test_client.get(
        f"/api/v1/repositories/{repo.id}/forks",
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1


def test_list_forks_empty(test_client: TestClient, auth_headers: dict, db):
    """测试没有 Fork 时返回空列表"""
    repo = create_test_repo(db, name="src-repo-5")

    response = test_client.get(
        f"/api/v1/repositories/{repo.id}/forks",
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["items"] == []


# =============================================================================
# Fork 源仓库追溯
# =============================================================================

def test_get_fork_source(test_client: TestClient, auth_headers: dict, db):
    """测试获取 Fork 的源仓库"""
    source_repo = create_test_repo(db, name="original-repo")

    # Fork 仓库
    fork_resp = test_client.post(
        f"/api/v1/repositories/{source_repo.id}/forks",
        json={"name": "fork-of-original"},
        headers=auth_headers
    )
    fork_id = fork_resp.json()["id"]

    # 获取源仓库
    response = test_client.get(
        f"/api/v1/repositories/{fork_id}/forks/source",
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data is not None
    assert data["id"] == str(source_repo.id)
    assert data["name"] == "original-repo"


def test_get_fork_source_not_fork(test_client: TestClient, auth_headers: dict, db):
    """测试非 Fork 仓库的源仓库返回 None"""
    repo = create_test_repo(db, name="src-repo-6")

    response = test_client.get(
        f"/api/v1/repositories/{repo.id}/forks/source",
        headers=auth_headers
    )

    assert response.status_code == 200
    assert response.json() is None
