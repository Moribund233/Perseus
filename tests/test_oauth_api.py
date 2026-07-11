import os
import pytest
import respx

from core.config import reset_module_config_manager


GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"


@pytest.fixture(autouse=True)
def _setup_oauth_config(monkeypatch):
    monkeypatch.setenv("PERSEUS_OAUTH_GITHUB_CLIENT_ID", "test_client_id")
    monkeypatch.setenv("PERSEUS_OAUTH_GITHUB_CLIENT_SECRET", "test_secret")
    monkeypatch.setenv("PERSEUS_OAUTH_GITHUB_REDIRECT_URI", "http://localhost:5173/auth/github/callback")
    reset_module_config_manager()


@pytest.fixture
def oauth_client(test_client):
    return test_client


class TestOAuthLoginEndpoint:
    """GET /api/v1/auth/{provider}/login 应返回跳转 URL"""

    def test_login_returns_authorization_url(self, oauth_client):
        resp = oauth_client.get("/api/v1/auth/github/login")
        assert resp.status_code == 200
        data = resp.json()
        assert "authorization_url" in data
        assert "state" in data
        assert data["authorization_url"].startswith("https://github.com/login/oauth/authorize")

    def test_login_unknown_provider_returns_400(self, oauth_client):
        resp = oauth_client.get("/api/v1/auth/unknown/login")
        assert resp.status_code == 400


class TestOAuthCallbackEndpoint:
    """GET /api/v1/auth/{provider}/callback 应处理 code 并返回令牌"""

    def test_callback_creates_user_and_returns_tokens(self, oauth_client):
        init_resp = oauth_client.get("/api/v1/auth/github/login")
        state = init_resp.json()["state"]

        with respx.mock:
            respx.post(GITHUB_TOKEN_URL).respond(
                status_code=200,
                json={"access_token": "gho_test", "token_type": "bearer", "scope": ""},
            )
            respx.get("https://api.github.com/user").respond(
                status_code=200,
                json={"id": 77777, "login": "api_oauth_user", "email": "api_oauth@github.com", "name": ""},
            )

            resp = oauth_client.get(
                f"/api/v1/auth/github/callback?code=test_code&state={state}"
            )

        assert resp.status_code == 200
        data = resp.json()
        assert "token" in data
        assert "refresh_token" in data
        assert data["username"] == "api_oauth_user"
        assert data["email"] == "api_oauth@github.com"

    def test_callback_with_invalid_state_returns_401(self, oauth_client):
        resp = oauth_client.get(
            "/api/v1/auth/github/callback?code=test_code&state=invalid_state"
        )
        assert resp.status_code == 401


class TestOAuthAccountManagement:
    """用户 OAuth 账号关联管理"""

    def test_list_linked_accounts_empty(self, oauth_client, auth_headers):
        resp = oauth_client.get("/api/v1/users/me/oauth", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_linked_accounts_requires_auth(self, oauth_client):
        resp = oauth_client.get("/api/v1/users/me/oauth")
        assert resp.status_code == 401

    def test_unlink_account_requires_auth(self, oauth_client):
        resp = oauth_client.delete("/api/v1/users/me/oauth/github")
        assert resp.status_code == 401

    def test_unlink_nonexistent_account_returns_404(self, oauth_client, auth_headers):
        resp = oauth_client.delete(
            "/api/v1/users/me/oauth/github", headers=auth_headers
        )
        assert resp.status_code == 404
