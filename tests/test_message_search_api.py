"""
消息检索 — API 集成测试
"""


def _create_room(test_client, auth_headers, name):
    create_resp = test_client.post("/api/v1/repositories", json={
        "name": name, "description": "test", "is_public": True,
    }, headers=auth_headers)
    assert create_resp.status_code == 200, create_resp.text
    repo_id = create_resp.json()["id"]
    room_resp = test_client.get(f"/api/v1/repositories/{repo_id}/room", headers=auth_headers)
    return repo_id, room_resp.json()["id"]


def _seed_message(db, room_id, sender_id, content):
    import uuid
    from models.chat_message import ChatMessage
    db.add(ChatMessage(
        room_id=uuid.UUID(str(room_id)),
        sender_id=uuid.UUID(str(sender_id)),
        content=content,
    ))
    db.commit()


def test_messages_search_requires_auth(test_client):
    response = test_client.get("/api/v1/messages/search", params={"q": "hi"})
    assert response.status_code in (401, 403)


def test_messages_search_empty_query_bad_request(test_client, auth_headers):
    response = test_client.get("/api/v1/messages/search", params={"q": "   "}, headers=auth_headers)
    assert response.status_code == 400


def test_room_messages_search_by_q(test_client, auth_headers, db, test_user):
    from models.user import User
    from services.token_service import create_access_token

    _, room_id = _create_room(test_client, auth_headers, "msg-search-room")

    peer = User(
        username="msgpeer", email="msgpeer@example.com",
        password="hashed", full_name="Msg Peer", is_active=True,
    )
    db.add(peer)
    db.commit()
    db.refresh(peer)
    peer_headers = {
        "Authorization": "Bearer " + create_access_token({
            "sub": str(peer.id), "username": peer.username, "is_admin": False,
        })
    }

    _seed_message(db, room_id, test_user.id, "hello machine")
    _seed_message(db, room_id, test_user.id, "unrelated filler")

    resp = test_client.get(
        f"/api/v1/rooms/{room_id}/messages", params={"q": "hello"}, headers=peer_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["messages"]) == 1
    assert data["messages"][0]["content"] == "hello machine"


def test_messages_search_no_match(test_client, auth_headers, db, test_user):
    _, room_id = _create_room(test_client, auth_headers, "msg-search-nomatch")
    _seed_message(db, room_id, test_user.id, "alpha beta gamma")

    resp = test_client.get("/api/v1/messages/search", params={"q": "zeta"}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["messages"] == []


def test_messages_search_returns_matches(test_client, auth_headers, db, test_user):
    _, room_id = _create_room(test_client, auth_headers, "msg-search-global")
    _seed_message(db, room_id, test_user.id, "alpha beta gamma")

    resp = test_client.get("/api/v1/messages/search", params={"q": "beta"}, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data["messages"], list)
    assert len(data["messages"]) == 1
    assert data["messages"][0]["room_id"] == room_id
    assert "room_name" in data["messages"][0]
    assert data["messages"][0]["content"] == "alpha beta gamma"