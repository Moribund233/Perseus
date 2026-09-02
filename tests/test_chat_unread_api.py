"""
批次 D — 聊天未读数 — API 集成测试
"""
import pytest


def _create_room(test_client, auth_headers, name):
    create_resp = test_client.post("/api/v1/repositories", json={
        "name": name, "description": "test", "is_public": True,
    }, headers=auth_headers)
    assert create_resp.status_code == 200, create_resp.text
    repo_id = create_resp.json()["id"]
    room_resp = test_client.get(f"/api/v1/repositories/{repo_id}/room", headers=auth_headers)
    room_id = room_resp.json()["id"]
    return repo_id, room_id


def test_get_unread_counts_returns_200_and_list(test_client, auth_headers):
    _, room_id = _create_room(test_client, auth_headers, "unread-list-test")
    response = test_client.get("/api/v1/rooms/unread", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    entry = next(r for r in data if r["room_id"] == room_id)
    assert entry["unread_count"] == 0


def test_get_unread_counts_requires_auth(test_client):
    response = test_client.get("/api/v1/rooms/unread")
    assert response.status_code in (401, 403)


def test_mark_read_returns_200(test_client, auth_headers):
    _, room_id = _create_room(test_client, auth_headers, "mark-read-test")
    response = test_client.post(f"/api/v1/rooms/{room_id}/read", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == {"success": True}


def test_mark_read_requires_auth(test_client, auth_headers):
    _, room_id = _create_room(test_client, auth_headers, "mark-read-auth")
    response = test_client.post(f"/api/v1/rooms/{room_id}/read")
    assert response.status_code in (401, 403)


def test_mark_read_private_repo_non_member_forbidden(test_client, db, test_user, auth_headers):
    from models.user import User
    from services.token_service import create_access_token

    other = User(
        username="otheruser", email="other@example.com",
        password="hashed", full_name="Other User", is_active=True,
    )
    db.add(other)
    db.commit()
    db.refresh(other)

    other_headers = {
        "Authorization": "Bearer " + create_access_token({
            "sub": str(other.id), "username": other.username, "is_admin": False,
        })
    }

    # test_user 创建私有仓库
    create_resp = test_client.post("/api/v1/repositories", json={
        "name": "priv-unread", "description": "test", "is_public": False,
    }, headers=auth_headers)
    repo_id = create_resp.json()["id"]
    room_resp = test_client.get(f"/api/v1/repositories/{repo_id}/room", headers=auth_headers)
    room_id = room_resp.json()["id"]

    response = test_client.post(f"/api/v1/rooms/{room_id}/read", headers=other_headers)
    assert response.status_code in (400, 403)


def test_add_reaction_requires_auth(test_client):
    response = test_client.post("/api/v1/rooms/00000000-0000-0000-0000-000000000001/messages/00000000-0000-0000-0000-000000000002/reactions", json={"emoji": "👍"})
    assert response.status_code in (401, 403)