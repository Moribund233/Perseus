import pytest


def test_create_repository(test_client, auth_headers):
    response = test_client.post("/api/v1/repositories", json={
        "name": "test-repo",
        "description": "A test repository",
        "is_public": True,
    }, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "test-repo"
    assert data["is_public"] is True


def test_create_repository_duplicate(test_client, auth_headers):
    test_client.post("/api/v1/repositories", json={
        "name": "dup-repo",
        "description": "First",
        "is_public": True,
    }, headers=auth_headers)
    response = test_client.post("/api/v1/repositories", json={
        "name": "dup-repo",
        "description": "Second",
        "is_public": True,
    }, headers=auth_headers)
    assert response.status_code in (400, 409)


def test_list_repositories(test_client, auth_headers):
    test_client.post("/api/v1/repositories", json={
        "name": "list-repo",
        "description": "List test",
        "is_public": True,
    }, headers=auth_headers)
    response = test_client.get("/api/v1/repositories", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data or "repositories" in data or isinstance(data, list)


def test_get_repository(test_client, auth_headers):
    create_resp = test_client.post("/api/v1/repositories", json={
        "name": "get-repo",
        "description": "Get test",
        "is_public": True,
    }, headers=auth_headers)
    repo_id = create_resp.json()["id"]
    response = test_client.get(f"/api/v1/repositories/{repo_id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["name"] == "get-repo"


def test_get_repository_not_found(test_client, auth_headers):
    response = test_client.get("/api/v1/repositories/00000000-0000-0000-0000-000000000000", headers=auth_headers)
    assert response.status_code == 404


def test_update_repository(test_client, auth_headers):
    create_resp = test_client.post("/api/v1/repositories", json={
        "name": "update-repo",
        "description": "Original",
        "is_public": True,
    }, headers=auth_headers)
    repo_id = create_resp.json()["id"]
    response = test_client.put(f"/api/v1/repositories/{repo_id}", json={
        "description": "Updated description",
    }, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["description"] == "Updated description"


def test_delete_repository(test_client, auth_headers):
    create_resp = test_client.post("/api/v1/repositories", json={
        "name": "delete-repo",
        "description": "To delete",
        "is_public": True,
    }, headers=auth_headers)
    repo_id = create_resp.json()["id"]
    response = test_client.delete(f"/api/v1/repositories/{repo_id}", headers=auth_headers)
    assert response.status_code in (200, 204)


def test_list_repositories_pagination(test_client, auth_headers):
    response = test_client.get("/api/v1/repositories?page=1&limit=5", headers=auth_headers)
    assert response.status_code == 200


def test_list_repositories_search(test_client, auth_headers):
    test_client.post("/api/v1/repositories", json={
        "name": "searchable-repo",
        "description": "Contains unique term",
        "is_public": True,
    }, headers=auth_headers)
    response = test_client.get("/api/v1/repositories?q=searchable", headers=auth_headers)
    assert response.status_code == 200


def test_list_repositories_sort(test_client, auth_headers):
    response = test_client.get("/api/v1/repositories?sort=name", headers=auth_headers)
    assert response.status_code == 200
