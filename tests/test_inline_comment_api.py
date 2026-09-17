"""
行内评论锚定 — API 集成测试
"""
import pytest


def _create_repo(test_client, auth_headers, name, is_public=True):
    create_resp = test_client.post("/api/v1/repositories", json={
        "name": name, "description": "test", "is_public": is_public,
    }, headers=auth_headers)
    assert create_resp.status_code == 200, create_resp.text
    return create_resp.json()["id"]


def _third_user_headers(db, username, test_user):
    from models.user import User
    from services.token_service import create_access_token

    user = User(
        username=username, email=f"{username}@example.com",
        password="hashed", full_name="Third User", is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user, {
        "Authorization": "Bearer " + create_access_token({
            "sub": str(user.id), "username": user.username, "is_admin": False,
        })
    }


def test_create_inline_comment_requires_auth(test_client):
    response = test_client.post(
        "/api/v1/repositories/00000000-0000-0000-0000-000000000001/discussions",
        json={"content": "hi", "file_path": "a.py"},
    )
    assert response.status_code in (401, 403)


def test_create_inline_comment_returns_201(test_client, auth_headers):
    repo_id = _create_repo(test_client, auth_headers, "disc-create")
    resp = test_client.post(
        f"/api/v1/repositories/{repo_id}/discussions",
        json={"content": "这段逻辑要改", "file_path": "src/app.py", "line_number": 12, "branch": "main"},
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["file_path"] == "src/app.py"
    assert data["line_number"] == 12
    assert data["branch"] == "main"
    assert data["resolved"] is False
    assert data["author_username"] == "testuser"


def test_create_inline_comment_missing_file_path_bad_request(test_client, auth_headers):
    repo_id = _create_repo(test_client, auth_headers, "disc-missing-path")
    resp = test_client.post(
        f"/api/v1/repositories/{repo_id}/discussions",
        json={"content": "没有文件路径"},
        headers=auth_headers,
    )
    assert resp.status_code == 422


def test_list_inline_comments_by_file(test_client, auth_headers):
    repo_id = _create_repo(test_client, auth_headers, "disc-list")
    test_client.post(
        f"/api/v1/repositories/{repo_id}/discussions",
        json={"content": "c1", "file_path": "src/a.py", "line_number": 1},
        headers=auth_headers,
    )
    test_client.post(
        f"/api/v1/repositories/{repo_id}/discussions",
        json={"content": "c2", "file_path": "src/b.py", "line_number": 2},
        headers=auth_headers,
    )

    resp = test_client.get(
        f"/api/v1/repositories/{repo_id}/discussions",
        params={"file_path": "src/a.py"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    comments = resp.json()
    assert len(comments) == 1
    assert comments[0]["content"] == "c1"


def test_reply_inline_comment(test_client, auth_headers):
    repo_id = _create_repo(test_client, auth_headers, "disc-reply")
    parent = test_client.post(
        f"/api/v1/repositories/{repo_id}/discussions",
        json={"content": "root", "file_path": "x.py"},
        headers=auth_headers,
    ).json()
    reply = test_client.post(
        f"/api/v1/repositories/{repo_id}/discussions",
        json={"content": "re: root", "file_path": "x.py", "parent_id": parent["id"]},
        headers=auth_headers,
    ).json()
    assert reply["parent_id"] == parent["id"]


def test_resolve_inline_comment(test_client, auth_headers):
    repo_id = _create_repo(test_client, auth_headers, "disc-resolve")
    comment = test_client.post(
        f"/api/v1/repositories/{repo_id}/discussions",
        json={"content": "fix me", "file_path": "x.py"},
        headers=auth_headers,
    ).json()
    resp = test_client.patch(
        f"/api/v1/repositories/{repo_id}/discussions/{comment['id']}",
        json={"resolved": True},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["resolved"] is True


def test_resolve_others_comment_forbidden(test_client, auth_headers, db, test_user):
    repo_id = _create_repo(test_client, auth_headers, "disc-resolve-forbidden")
    comment = test_client.post(
        f"/api/v1/repositories/{repo_id}/discussions",
        json={"content": "mine", "file_path": "x.py"},
        headers=auth_headers,
    ).json()
    _, other_headers = _third_user_headers(db, "disc_outsider", test_user)
    resp = test_client.patch(
        f"/api/v1/repositories/{repo_id}/discussions/{comment['id']}",
        json={"resolved": True},
        headers=other_headers,
    )
    assert resp.status_code in (400, 403)


def test_delete_inline_comment(test_client, auth_headers):
    repo_id = _create_repo(test_client, auth_headers, "disc-delete")
    comment = test_client.post(
        f"/api/v1/repositories/{repo_id}/discussions",
        json={"content": "remove me", "file_path": "x.py"},
        headers=auth_headers,
    ).json()
    resp = test_client.delete(
        f"/api/v1/repositories/{repo_id}/discussions/{comment['id']}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json() == {"success": True}

    listed = test_client.get(
        f"/api/v1/repositories/{repo_id}/discussions", headers=auth_headers,
    ).json()
    assert listed == []


def test_private_repo_non_member_forbidden(test_client, auth_headers, db, test_user):
    repo_id = _create_repo(test_client, auth_headers, "disc-private", is_public=False)
    _, other_headers = _third_user_headers(db, "disc_private_outsider", test_user)
    resp = test_client.post(
        f"/api/v1/repositories/{repo_id}/discussions",
        json={"content": "闯入私有仓库", "file_path": "x.py"},
        headers=other_headers,
    )
    assert resp.status_code == 400