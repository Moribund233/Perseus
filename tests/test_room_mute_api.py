"""
批次 G — 会话静音 — API 集成测试
"""


def _create_room(test_client, auth_headers, name, is_public=True):
    create_resp = test_client.post("/api/v1/repositories", json={
        "name": name, "description": "test", "is_public": is_public,
    }, headers=auth_headers)
    assert create_resp.status_code == 200, create_resp.text
    repo_id = create_resp.json()["id"]
    room_resp = test_client.get(f"/api/v1/repositories/{repo_id}/room", headers=auth_headers)
    room_id = room_resp.json()["id"]
    return repo_id, room_id


def test_set_mute_requires_auth(test_client):
    response = test_client.post("/api/v1/rooms/00000000-0000-0000-0000-000000000001/members/me",
                                json={"muted": True})
    assert response.status_code in (401, 403)


def test_mute_room_success(test_client, auth_headers):
    _, room_id = _create_room(test_client, auth_headers, "mute-room")
    response = test_client.post(f"/api/v1/rooms/{room_id}/members/me",
                                json={"muted": True}, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["room_id"] == room_id
    assert data["is_muted"] is True

    # 取消静音
    response = test_client.post(f"/api/v1/rooms/{room_id}/members/me",
                                json={"muted": False}, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["is_muted"] is False


def test_mute_private_repo_non_member_forbidden(test_client, db, auth_headers):
    from models.user import User
    from services.token_service import create_access_token

    other = User(
        username="muteother", email="muteother@example.com",
        password="hashed", full_name="Mute Other", is_active=True,
    )
    db.add(other)
    db.commit()
    db.refresh(other)

    other_headers = {
        "Authorization": "Bearer " + create_access_token({
            "sub": str(other.id), "username": other.username, "is_admin": False,
        })
    }

    _, room_id = _create_room(test_client, auth_headers, "priv-mute", is_public=False)
    response = test_client.post(f"/api/v1/rooms/{room_id}/members/me",
                                json={"muted": True}, headers=other_headers)
    assert response.status_code in (400, 403, 404)


def test_mute_room_not_found(test_client, auth_headers):
    response = test_client.post("/api/v1/rooms/00000000-0000-0000-0000-000000000001/members/me",
                                json={"muted": True}, headers=auth_headers)
    assert response.status_code == 404


def test_muted_room_unread_zero_via_api(test_client, auth_headers):
    _, room_id = _create_room(test_client, auth_headers, "mute-unread")
    # 静音后 /rooms/unread 中该房间 unread_count 保持 0
    response = test_client.post(f"/api/v1/rooms/{room_id}/members/me",
                                json={"muted": True}, headers=auth_headers)
    assert response.status_code == 200

    unread_resp = test_client.get("/api/v1/rooms/unread", headers=auth_headers)
    assert unread_resp.status_code == 200
    entry = next((r for r in unread_resp.json() if r["room_id"] == room_id), None)
    assert entry is not None
    assert entry["unread_count"] == 0