"""
F-201 房间/频道管理 — API 集成测试
"""
import pytest


def test_get_room_returns_200(test_client, auth_headers):
    create_resp = test_client.post("/api/v1/repositories", json={
        "name": "room-test-repo", "description": "test", "is_public": True,
    }, headers=auth_headers)
    repo_id = create_resp.json()["id"]
    response = test_client.get(f"/api/v1/repositories/{repo_id}/room", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["repository_id"] == repo_id


def test_get_room_unauthorized(test_client):
    response = test_client.get("/api/v1/repositories/1/room")
    assert response.status_code in (401, 403)


def test_get_room_members(test_client, auth_headers):
    create_resp = test_client.post("/api/v1/repositories", json={
        "name": "room-members-test", "description": "test", "is_public": True,
    }, headers=auth_headers)
    repo_id = create_resp.json()["id"]
    room_resp = test_client.get(f"/api/v1/repositories/{repo_id}/room", headers=auth_headers)
    room_id = room_resp.json()["id"]
    response = test_client.get(f"/api/v1/rooms/{room_id}/members", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


def test_delete_room_by_owner(test_client, auth_headers, admin_headers):
    create_resp = test_client.post("/api/v1/repositories", json={
        "name": "room-delete-test", "description": "test", "is_public": True,
    }, headers=auth_headers)
    repo_id = create_resp.json()["id"]
    room_resp = test_client.get(f"/api/v1/repositories/{repo_id}/room", headers=auth_headers)
    room_id = room_resp.json()["id"]
    response = test_client.delete(f"/api/v1/rooms/{room_id}", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data.get("success") is True
