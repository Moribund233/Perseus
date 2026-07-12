"""
F-202 团队聊天 — API 集成测试
"""
import pytest


def test_get_messages_returns_200(test_client, auth_headers):
    create_resp = test_client.post("/api/v1/repositories", json={
        "name": "chat-test-repo", "description": "test", "is_public": True,
    }, headers=auth_headers)
    repo_id = create_resp.json()["id"]
    room_resp = test_client.get(f"/api/v1/repositories/{repo_id}/room", headers=auth_headers)
    room_id = room_resp.json()["id"]
    response = test_client.get(f"/api/v1/rooms/{room_id}/messages", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "messages" in data
    assert "has_more" in data
    assert "next_before" in data


def test_get_messages_unauthorized(test_client):
    response = test_client.get("/api/v1/rooms/1/messages")
    assert response.status_code in (401, 403)


def test_get_messages_pagination(test_client, auth_headers):
    create_resp = test_client.post("/api/v1/repositories", json={
        "name": "chat-pag-test", "description": "test", "is_public": True,
    }, headers=auth_headers)
    repo_id = create_resp.json()["id"]
    room_resp = test_client.get(f"/api/v1/repositories/{repo_id}/room", headers=auth_headers)
    room_id = room_resp.json()["id"]
    response = test_client.get(f"/api/v1/rooms/{room_id}/messages?limit=5", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["messages"], list)
