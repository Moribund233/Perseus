"""
F-203 DM 私聊 — API 集成测试
"""
import pytest


def _create_peer_user(test_client, db, test_user, username="peeruser"):
    from models.user import User
    from services.token_service import create_access_token

    user = User(
        username=username,
        email=f"{username}@example.com",
        password="hashed",
        full_name="Peer User",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user, {
        "Authorization": "Bearer " + create_access_token({
            "sub": str(user.id), "username": user.username, "is_admin": False,
        })
    }


def test_create_dm_returns_201(test_client, auth_headers, db, test_user):
    peer, _ = _create_peer_user(test_client, db, test_user)
    response = test_client.post("/api/v1/dm", json={"peer_user_id": str(peer.id)}, headers=auth_headers)
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["room_type"] == "dm"
    assert data["is_active"] is True
    assert data["repository_id"] is None


def test_create_dm_requires_auth(test_client):
    response = test_client.post("/api/v1/dm", json={"peer_user_id": "00000000-0000-0000-0000-000000000001"})
    assert response.status_code in (401, 403)


def test_create_dm_idempotent(test_client, auth_headers, db, test_user):
    peer, peer_headers = _create_peer_user(test_client, db, test_user)
    first = test_client.post("/api/v1/dm", json={"peer_user_id": str(peer.id)}, headers=auth_headers).json()
    second = test_client.post("/api/v1/dm", json={"peer_user_id": str(test_user.id)}, headers=peer_headers).json()
    assert first["id"] == second["id"]


def test_list_dms_returns_conversations(test_client, auth_headers, db, test_user):
    peer, peer_headers = _create_peer_user(test_client, db, test_user)
    test_client.post("/api/v1/dm", json={"peer_user_id": str(peer.id)}, headers=auth_headers)

    response = test_client.get("/api/v1/dm", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["peer_user_id"] == str(peer.id)
    assert data[0]["peer_username"] == "peeruser"
    assert "unread_count" in data[0]


def test_list_dms_only_own(test_client, auth_headers, db, test_user):
    peer, peer_headers = _create_peer_user(test_client, db, test_user)
    test_client.post("/api/v1/dm", json={"peer_user_id": str(peer.id)}, headers=auth_headers)

    response = test_client.get("/api/v1/dm", headers=peer_headers)
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_dm_messages_endpoint_reusable(test_client, auth_headers, db, test_user):
    peer, _ = _create_peer_user(test_client, db, test_user)
    dm = test_client.post("/api/v1/dm", json={"peer_user_id": str(peer.id)}, headers=auth_headers).json()
    resp = test_client.get(f"/api/v1/rooms/{dm['id']}/messages", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["messages"] == []