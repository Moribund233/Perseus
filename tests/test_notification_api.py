import pytest
from httpx import AsyncClient
from models.notification import Notification


def test_get_notifications_empty(test_client, auth_headers):
    response = test_client.get("/api/v1/notifications", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "notifications" in data
    assert data["total"] == 0


def test_get_notifications_with_data(test_client, auth_headers):
    for i in range(3):
        test_client.post(
            "/api/v1/notifications",
            json={
                "type": "comment",
                "title": f"Comment {i}",
                "message": f"Message {i}",
            },
            headers=auth_headers,
        )
    response = test_client.get("/api/v1/notifications", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3


def test_get_unread_count(test_client, auth_headers):
    test_client.post(
        "/api/v1/notifications",
        json={"type": "comment", "title": "Unread", "message": "msg"},
        headers=auth_headers,
    )
    response = test_client.get(
        "/api/v1/notifications/unread-count", headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["count"] == 1


def test_mark_as_read(test_client, auth_headers):
    create_resp = test_client.post(
        "/api/v1/notifications",
        json={"type": "comment", "title": "Read", "message": "msg"},
        headers=auth_headers,
    )
    notif_id = create_resp.json()["id"]

    response = test_client.patch(
        f"/api/v1/notifications/{notif_id}/read", headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["is_read"] is True


def test_mark_as_read_not_found(test_client, auth_headers):
    response = test_client.patch(
        "/api/v1/notifications/99999/read", headers=auth_headers
    )
    assert response.status_code == 404


def test_mark_all_as_read(test_client, auth_headers):
    for i in range(2):
        test_client.post(
            "/api/v1/notifications",
            json={"type": "comment", "title": f"Unread {i}", "message": "msg"},
            headers=auth_headers,
        )
    response = test_client.post(
        "/api/v1/notifications/read-all", headers=auth_headers
    )
    assert response.status_code == 200


def test_delete_notification(test_client, auth_headers):
    create_resp = test_client.post(
        "/api/v1/notifications",
        json={"type": "comment", "title": "Delete", "message": "msg"},
        headers=auth_headers,
    )
    notif_id = create_resp.json()["id"]

    response = test_client.delete(
        f"/api/v1/notifications/{notif_id}", headers=auth_headers
    )
    assert response.status_code == 204


def test_delete_notification_not_found(test_client, auth_headers):
    response = test_client.delete(
        "/api/v1/notifications/99999", headers=auth_headers
    )
    assert response.status_code == 404


def test_create_notification(test_client, auth_headers):
    response = test_client.post(
        "/api/v1/notifications",
        json={
            "type": "pull_request",
            "title": "PR created",
            "message": "New PR",
            "repository_id": None,
            "target_type": None,
            "target_id": None,
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["type"] == "pull_request"
    assert data["title"] == "PR created"


def test_get_notifications_unread_only(test_client, auth_headers):
    test_client.post(
        "/api/v1/notifications",
        json={"type": "comment", "title": "Unread", "message": "msg"},
        headers=auth_headers,
    )
    read_resp = test_client.post(
        "/api/v1/notifications",
        json={"type": "comment", "title": "Read", "message": "msg"},
        headers=auth_headers,
    )
    test_client.patch(
        f"/api/v1/notifications/{read_resp.json()['id']}/read", headers=auth_headers
    )
    response = test_client.get(
        "/api/v1/notifications?unread_only=true", headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["notifications"][0]["title"] == "Unread"
