"""
SSH Key 控制器异步测试

F-020: SSH 认证集成测试
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_add_ssh_key_endpoint(test_client: TestClient, auth_headers: dict, async_db: AsyncSession):
    """
    测试添加 SSH Key API 端点

    验证点：
    1. 认证用户可以添加 SSH Key
    2. 返回正确的 key 信息
    """
    public_key = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC0 test@example.com"

    response = test_client.post(
        "/api/v1/keys",
        json={
            "name": "My Laptop",
            "public_key": public_key
        },
        headers=auth_headers
    )

    assert response.status_code == 201, f"应该返回 201, 实际返回 {response.status_code}"
    data = response.json()
    assert data["name"] == "My Laptop"
    assert data["public_key"] == public_key
    assert data["fingerprint"] is not None
    assert data["id"] is not None

    print("✓ test_add_ssh_key_endpoint 通过")


@pytest.mark.asyncio
async def test_add_ssh_key_unauthorized(test_client: TestClient):
    """
    测试未认证用户添加 SSH Key

    验证点：
    1. 未认证用户应该收到 401 错误
    """
    response = test_client.post(
        "/api/v1/keys",
        json={
            "name": "My Laptop",
            "public_key": "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC0 test@example.com"
        }
    )

    assert response.status_code == 401, f"应该返回 401, 实际返回 {response.status_code}"

    print("✓ test_add_ssh_key_unauthorized 通过")


@pytest.mark.asyncio
async def test_add_ssh_key_invalid_format(test_client: TestClient, auth_headers: dict):
    """
    测试添加格式无效的 SSH Key

    验证点：
    1. 无效的 key 格式应该返回 400 错误
    """
    response = test_client.post(
        "/api/v1/keys",
        json={
            "name": "Invalid Key",
            "public_key": "not-a-valid-key"
        },
        headers=auth_headers
    )

    assert response.status_code == 400, f"应该返回 400, 实际返回 {response.status_code}"

    print("✓ test_add_ssh_key_invalid_format 通过")


@pytest.mark.asyncio
async def test_list_ssh_keys_endpoint(test_client: TestClient, auth_headers: dict, async_db: AsyncSession):
    """
    测试列出 SSH Keys API 端点

    验证点：
    1. 可以获取用户的 SSH Key 列表
    2. 返回列表包含所有 key
    """
    # 先添加两个 key
    test_client.post(
        "/api/v1/keys",
        json={
            "name": "Key 1",
            "public_key": "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQE1 key1@test.com"
        },
        headers=auth_headers
    )
    test_client.post(
        "/api/v1/keys",
        json={
            "name": "Key 2",
            "public_key": "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQE2 key2@test.com"
        },
        headers=auth_headers
    )

    # 获取列表
    response = test_client.get("/api/v1/keys", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2
    key_names = [k["name"] for k in data]
    assert "Key 1" in key_names
    assert "Key 2" in key_names

    print("✓ test_list_ssh_keys_endpoint 通过")


@pytest.mark.asyncio
async def test_delete_ssh_key_endpoint(test_client: TestClient, auth_headers: dict, async_db: AsyncSession):
    """
    测试删除 SSH Key API 端点

    验证点：
    1. 可以删除自己的 SSH Key
    2. 删除后返回 204
    """
    # 先添加 key
    response = test_client.post(
        "/api/v1/keys",
        json={
            "name": "Key to Delete",
            "public_key": "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQD3 delete@test.com"
        },
        headers=auth_headers
    )
    key_id = response.json()["id"]

    # 删除 key
    response = test_client.delete(f"/api/v1/keys/{key_id}", headers=auth_headers)
    assert response.status_code == 204

    # 验证已删除
    response = test_client.get("/api/v1/keys", headers=auth_headers)
    data = response.json()
    assert len(data) == 0

    print("✓ test_delete_ssh_key_endpoint 通过")


@pytest.mark.asyncio
async def test_delete_ssh_key_not_found(test_client: TestClient, auth_headers: dict):
    """
    测试删除不存在的 SSH Key

    验证点：
    1. 删除不存在的 key 应该返回 404
    """
    response = test_client.delete("/api/v1/keys/00000000-0000-0000-0000-000000000000", headers=auth_headers)
    assert response.status_code == 404

    print("✓ test_delete_ssh_key_not_found 通过")
