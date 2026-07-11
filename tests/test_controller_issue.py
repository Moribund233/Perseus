import pytest


def _create_repo(test_client, auth_headers, name="issue-test-repo"):
    resp = test_client.post("/api/v1/repositories", json={
        "name": name, "description": "Issue test", "is_public": True,
    }, headers=auth_headers)
    return resp.json()["id"]


def test_create_issue(test_client, auth_headers):
    repo_id = _create_repo(test_client, auth_headers)
    response = test_client.post(f"/api/v1/repositories/{repo_id}/issues", json={
        "title": "Test Issue",
        "description": "A test issue",
    }, headers=auth_headers)
    assert response.status_code in (201, 200)
    assert response.json()["title"] == "Test Issue"


def test_list_issues(test_client, auth_headers):
    repo_id = _create_repo(test_client, auth_headers, "issue-list-repo")
    response = test_client.get(f"/api/v1/repositories/{repo_id}/issues", headers=auth_headers)
    assert response.status_code == 200


def test_get_issue(test_client, auth_headers):
    repo_id = _create_repo(test_client, auth_headers, "issue-get-repo")
    create_resp = test_client.post(f"/api/v1/repositories/{repo_id}/issues", json={
        "title": "Get Issue", "description": "test",
    }, headers=auth_headers)
    issue_number = create_resp.json()["issue_number"]
    response = test_client.get(
        f"/api/v1/repositories/{repo_id}/issues/{issue_number}", headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["title"] == "Get Issue"


def test_close_issue(test_client, auth_headers):
    repo_id = _create_repo(test_client, auth_headers, "issue-close-repo")
    create_resp = test_client.post(f"/api/v1/repositories/{repo_id}/issues", json={
        "title": "Close me", "description": "test",
    }, headers=auth_headers)
    issue_number = create_resp.json()["issue_number"]
    response = test_client.post(
        f"/api/v1/repositories/{repo_id}/issues/{issue_number}/close",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "closed"


def test_filter_issues_by_status(test_client, auth_headers):
    repo_id = _create_repo(test_client, auth_headers, "issue-filter-repo")
    test_client.post(f"/api/v1/repositories/{repo_id}/issues", json={
        "title": "Open Issue", "description": "open",
    }, headers=auth_headers)
    response = test_client.get(
        f"/api/v1/repositories/{repo_id}/issues?status=open", headers=auth_headers
    )
    assert response.status_code == 200
