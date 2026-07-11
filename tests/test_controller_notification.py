import pytest


def test_list_notifications_pagination(test_client, auth_headers):
    for i in range(5):
        test_client.post(
            "/api/v1/notifications",
            json={"type": "comment", "title": f"Msg {i}", "message": "msg"},
            headers=auth_headers,
        )
    response = test_client.get(
        "/api/v1/notifications?skip=2&limit=2", headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["notifications"]) == 2
    assert data["total"] == 5


def test_update_all_preference_fields(test_client, auth_headers):
    response = test_client.put(
        "/api/v1/notifications/preferences",
        json={
            "email_on_mention": False,
            "email_on_pr_review": False,
            "email_on_issue_comment": False,
            "email_on_pr_merge": False,
            "email_on_release": False,
            "in_app_on_mention": False,
            "in_app_on_pr_review": False,
            "in_app_on_issue_comment": False,
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email_on_mention"] is False
    assert data["in_app_on_mention"] is False
