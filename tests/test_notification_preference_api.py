import pytest


def test_get_preferences(test_client, auth_headers):
    response = test_client.get("/api/v1/notifications/preferences", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "email_on_mention" in data
    assert data["email_on_mention"] is True


def test_update_preferences(test_client, auth_headers):
    response = test_client.put(
        "/api/v1/notifications/preferences",
        json={"email_on_mention": False, "email_on_pr_review": False},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email_on_mention"] is False
    assert data["email_on_pr_review"] is False
    assert data["email_on_issue_comment"] is True  # unchanged


def test_update_preferences_invalid_field(test_client, auth_headers):
    response = test_client.put(
        "/api/v1/notifications/preferences",
        json={"invalid_field": True},
        headers=auth_headers,
    )
    assert response.status_code == 200  # ignores unknown fields
