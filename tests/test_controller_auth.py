import pytest


def test_register_success(test_client):
    response = test_client.post("/api/v1/users", json={
        "username": "newuser",
        "email": "new@example.com",
        "password": "StrongPass123!",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "newuser"
    assert "id" in data


def test_register_duplicate_username(test_client):
    test_client.post("/api/v1/users", json={
        "username": "dupuser",
        "email": "dup@example.com",
        "password": "StrongPass123!",
    })
    response = test_client.post("/api/v1/users", json={
        "username": "dupuser",
        "email": "dup2@example.com",
        "password": "StrongPass123!",
    })
    assert response.status_code in (400, 409, 422)


def test_login_success(test_client):
    test_client.post("/api/v1/users", json={
        "username": "loginuser",
        "email": "login@example.com",
        "password": "StrongPass123!",
    })
    response = test_client.post("/api/v1/auth/login", json={
        "username": "loginuser",
        "password": "StrongPass123!",
    })
    assert response.status_code == 200
    data = response.json()
    assert "token" in data
    assert data["username"] == "loginuser"


def test_login_wrong_password(test_client):
    test_client.post("/api/v1/users", json={
        "username": "wrongpw",
        "email": "wrongpw@example.com",
        "password": "StrongPass123!",
    })
    response = test_client.post("/api/v1/auth/login", json={
        "username": "wrongpw",
        "password": "WrongPassword!",
    })
    assert response.status_code in (401, 400)


def test_login_nonexistent_user(test_client):
    response = test_client.post("/api/v1/auth/login", json={
        "username": "nouser",
        "password": "StrongPass123!",
    })
    assert response.status_code in (401, 400)


def test_get_current_user(test_client, auth_headers):
    response = test_client.get("/api/v1/users/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "username" in data
    assert "email" in data


def test_get_current_user_no_token(test_client):
    response = test_client.get("/api/v1/users/me")
    assert response.status_code == 401
