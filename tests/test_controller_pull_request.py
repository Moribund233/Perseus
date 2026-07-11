# tests/test_controller_pull_request.py
import pytest


def _create_repo(test_client, auth_headers, name="pr-test-repo"):
    resp = test_client.post("/api/v1/repositories", json={
        "name": name, "description": "PR test", "is_public": True,
    }, headers=auth_headers)
    return resp.json()["id"]


def test_create_pull_request(test_client, auth_headers):
    repo_id = _create_repo(test_client, auth_headers)
    response = test_client.post(f"/api/v1/repositories/{repo_id}/pull-requests", json={
        "title": "Test PR",
        "description": "A test pull request",
        "source_branch": "feature",
        "target_branch": "main",
    }, headers=auth_headers)
    assert response.status_code in (201, 200)
    data = response.json()
    assert data["title"] == "Test PR"


def test_list_pull_requests(test_client, auth_headers):
    repo_id = _create_repo(test_client, auth_headers, "pr-list-repo")
    response = test_client.get(f"/api/v1/repositories/{repo_id}/pull-requests", headers=auth_headers)
    assert response.status_code == 200


def test_get_pull_request(test_client, auth_headers):
    repo_id = _create_repo(test_client, auth_headers, "pr-get-repo")
    create_resp = test_client.post(f"/api/v1/repositories/{repo_id}/pull-requests", json={
        "title": "Get PR", "description": "test", "source_branch": "a", "target_branch": "main",
    }, headers=auth_headers)
    pr_number = create_resp.json()["pr_number"]
    response = test_client.get(
        f"/api/v1/repositories/{repo_id}/pull-requests/{pr_number}", headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["title"] == "Get PR"


def test_create_draft_pr(test_client, auth_headers):
    repo_id = _create_repo(test_client, auth_headers, "pr-draft-repo")
    response = test_client.post(f"/api/v1/repositories/{repo_id}/pull-requests", json={
        "title": "Draft PR", "description": "draft", "source_branch": "b", "target_branch": "main",
    }, headers=auth_headers)
    assert response.status_code in (201, 200)
    assert response.json().get("is_draft") is False
