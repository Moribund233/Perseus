"""
Webhook API 集成测试

F-031: Webhook 触发与投递
F-032: HMAC-SHA256 签名验证
F-033: 事件负载标准格式
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from models.repository import Repository


def create_test_repo(db, owner_id: int, name: str = "test-repo") -> Repository:
    """创建测试仓库（同步操作，在 auth_headers fixture 的 db 会话中执行）"""
    repo = Repository(
        name=name,
        path=f"testuser/{name}",
        description="Test repository",
        is_public=True,
        owner_id=owner_id,
        default_branch="main"
    )
    db.add(repo)
    db.commit()
    db.refresh(repo)
    return repo


# =============================================================================
# F-031: Webhook CRUD API 测试
# =============================================================================

@pytest.mark.asyncio
async def test_create_webhook_endpoint(
    test_client: TestClient, auth_headers: dict, db
):
    """
    测试创建 WebHook API

    验证点：
    1. 有管理员权限的用户可以创建 WebHook
    2. 返回正确的 WebHook 信息
    """
    # 先创建测试仓库（auth_headers 中的用户是 owner_id=1）
    repo = create_test_repo(db, owner_id=1)

    response = test_client.post(
        f"/api/v1/repositories/{repo.id}/webhooks",
        json={
            "url": "https://example.com/webhook",
            "events": ["push", "pull_request.opened"],
            "secret": "my-secret-key",
            "content_type": "application/json",
            "is_active": True
        },
        headers=auth_headers
    )

    assert response.status_code == 201, f"应该返回 201, 实际返回 {response.status_code}"
    data = response.json()
    assert data["url"] == "https://example.com/webhook"
    assert data["events"] == ["push", "pull_request.opened"]
    assert data["is_active"] is True
    assert data["id"] is not None

    print("✓ test_create_webhook_endpoint 通过")


@pytest.mark.asyncio
async def test_list_webhooks_endpoint(
    test_client: TestClient, auth_headers: dict, db
):
    """
    测试列出 WebHook API

    验证点：
    1. 可以获取仓库的 WebHook 列表
    2. 返回分页结果
    """
    repo = create_test_repo(db, owner_id=1)

    # 先创建两个 WebHook
    for i in range(2):
        test_client.post(
            f"/api/v1/repositories/{repo.id}/webhooks",
            json={
                "url": f"https://example{i}.com/webhook",
                "events": ["push"],
            },
            headers=auth_headers
        )

    # 获取列表
    response = test_client.get(
        f"/api/v1/repositories/{repo.id}/webhooks",
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2

    print("✓ test_list_webhooks_endpoint 通过")


@pytest.mark.asyncio
async def test_get_webhook_endpoint(
    test_client: TestClient, auth_headers: dict, db
):
    """
    测试获取 WebHook 详情 API

    验证点：
    1. 可以获取单个 WebHook 详情
    2. 返回完整的 WebHook 信息
    """
    repo = create_test_repo(db, owner_id=1)

    # 创建 WebHook
    create_resp = test_client.post(
        f"/api/v1/repositories/{repo.id}/webhooks",
        json={
            "url": "https://example.com/webhook",
            "events": ["push"],
        },
        headers=auth_headers
    )
    webhook_id = create_resp.json()["id"]

    # 获取详情
    response = test_client.get(
        f"/api/v1/repositories/{repo.id}/webhooks/{webhook_id}",
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == webhook_id
    assert data["url"] == "https://example.com/webhook"

    print("✓ test_get_webhook_endpoint 通过")


@pytest.mark.asyncio
async def test_update_webhook_endpoint(
    test_client: TestClient, auth_headers: dict, db
):
    """
    测试更新 WebHook API

    验证点：
    1. 可以更新 WebHook 的 url 和 events
    """
    repo = create_test_repo(db, owner_id=1)

    create_resp = test_client.post(
        f"/api/v1/repositories/{repo.id}/webhooks",
        json={
            "url": "https://example.com/webhook",
            "events": ["push"],
        },
        headers=auth_headers
    )
    webhook_id = create_resp.json()["id"]

    # 更新
    response = test_client.patch(
        f"/api/v1/repositories/{repo.id}/webhooks/{webhook_id}",
        json={
            "url": "https://updated.com/webhook",
            "events": ["push", "pull_request.merged"],
        },
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["url"] == "https://updated.com/webhook"
    assert "pull_request.merged" in data["events"]

    print("✓ test_update_webhook_endpoint 通过")


@pytest.mark.asyncio
async def test_delete_webhook_endpoint(
    test_client: TestClient, auth_headers: dict, db
):
    """
    测试删除 WebHook API

    验证点：
    1. 可以删除 WebHook
    2. 删除后返回 204
    """
    repo = create_test_repo(db, owner_id=1)

    create_resp = test_client.post(
        f"/api/v1/repositories/{repo.id}/webhooks",
        json={
            "url": "https://example.com/webhook",
            "events": ["push"],
        },
        headers=auth_headers
    )
    webhook_id = create_resp.json()["id"]

    # 删除
    response = test_client.delete(
        f"/api/v1/repositories/{repo.id}/webhooks/{webhook_id}",
        headers=auth_headers
    )
    assert response.status_code == 204

    # 验证已删除
    get_resp = test_client.get(
        f"/api/v1/repositories/{repo.id}/webhooks/{webhook_id}",
        headers=auth_headers
    )
    assert get_resp.status_code == 404

    print("✓ test_delete_webhook_endpoint 通过")


# =============================================================================
# WebHook 权限测试
# =============================================================================

@pytest.mark.asyncio
async def test_create_webhook_unauthorized(test_client: TestClient, db):
    """
    测试未认证用户创建 WebHook

    验证点：
    1. 未认证用户应该收到 401 错误
    """
    repo = create_test_repo(db, owner_id=1)

    response = test_client.post(
        f"/api/v1/repositories/{repo.id}/webhooks",
        json={
            "url": "https://example.com/webhook",
            "events": ["push"],
        }
    )

    assert response.status_code == 401

    print("✓ test_create_webhook_unauthorized 通过")


@pytest.mark.asyncio
async def test_create_webhook_invalid_url(
    test_client: TestClient, auth_headers: dict, db
):
    """
    测试创建 WebHook 时使用无效 URL

    验证点：
    1. 无效 URL 应该返回 400 错误
    """
    repo = create_test_repo(db, owner_id=1)

    response = test_client.post(
        f"/api/v1/repositories/{repo.id}/webhooks",
        json={
            "url": "not-a-valid-url",
            "events": ["push"],
        },
        headers=auth_headers
    )

    assert response.status_code == 400

    print("✓ test_create_webhook_invalid_url 通过")


@pytest.mark.asyncio
async def test_create_webhook_empty_events(
    test_client: TestClient, auth_headers: dict, db
):
    """
    测试创建 WebHook 时未指定事件

    验证点：
    1. 空事件列表应该返回 400 错误
    """
    repo = create_test_repo(db, owner_id=1)

    response = test_client.post(
        f"/api/v1/repositories/{repo.id}/webhooks",
        json={
            "url": "https://example.com/webhook",
            "events": [],
        },
        headers=auth_headers
    )

    assert response.status_code == 422, f"Pydantic 验证返回 422, 实际返回 {response.status_code}"

    print("✓ test_create_webhook_empty_events 通过")


@pytest.mark.asyncio
async def test_delete_webhook_not_found(
    test_client: TestClient, auth_headers: dict, db
):
    """
    测试删除不存在的 WebHook

    验证点：
    1. 删除不存在的 WebHook 应该返回 404
    """
    repo = create_test_repo(db, owner_id=1)

    response = test_client.delete(
        f"/api/v1/repositories/{repo.id}/webhooks/99999",
        headers=auth_headers
    )
    assert response.status_code == 404

    print("✓ test_delete_webhook_not_found 通过")


# =============================================================================
# WebHook 测试端点
# =============================================================================

@pytest.mark.asyncio
async def test_webhook_test_endpoint(
    test_client: TestClient, auth_headers: dict, db
):
    """
    测试 WebHook 测试端点

    验证点：
    1. 测试端点返回投递结果
    """
    repo = create_test_repo(db, owner_id=1)

    create_resp = test_client.post(
        f"/api/v1/repositories/{repo.id}/webhooks",
        json={
            "url": "https://example.com/webhook",
            "events": ["push"],
        },
        headers=auth_headers
    )
    webhook_id = create_resp.json()["id"]

    # 测试 WebHook
    response = test_client.post(
        f"/api/v1/repositories/{repo.id}/webhooks/{webhook_id}/test",
        headers=auth_headers
    )

    # 测试请求可能成功或失败，但端点本身应该返回 200
    assert response.status_code == 200
    data = response.json()
    assert "success" in data
    assert "status_code" in data
    assert "duration_ms" in data

    print("✓ test_webhook_test_endpoint 通过")
