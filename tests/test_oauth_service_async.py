import pytest
import respx
import httpx
from urllib.parse import urlparse, parse_qs


GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITLAB_TOKEN_URL = "https://gitlab.com/oauth/token"
GITLAB_USERINFO_URL = "https://gitlab.com/api/v4/user"


class TestGitHubProviderAuthorizationUrl:
    """GitHubProvider.get_authorization_url() 应生成正确的跳转 URL"""

    def test_authorization_url_includes_required_params(self):
        from services.auth.oauth import GitHubProvider

        provider = GitHubProvider(
            client_id="test_client_id",
            client_secret="test_secret",
            redirect_uri="http://localhost:5173/auth/github/callback",
        )
        state = "test_state_value"
        url = provider.get_authorization_url(state=state)

        parsed = urlparse(url)
        params = parse_qs(parsed.query)

        assert parsed.scheme == "https"
        assert parsed.netloc == "github.com"
        assert parsed.path == "/login/oauth/authorize"
        assert params["client_id"] == ["test_client_id"]
        assert params["redirect_uri"] == ["http://localhost:5173/auth/github/callback"]
        assert params["state"] == ["test_state_value"]
        assert params["response_type"] == ["code"]


class TestGitHubProviderExchangeCode:
    """GitHubProvider.exchange_code() 应用 code 交换 access_token"""

    @pytest.mark.asyncio
    async def test_exchange_code_returns_access_token(self):
        from services.auth.oauth import GitHubProvider

        provider = GitHubProvider(
            client_id="test_client_id",
            client_secret="test_secret",
            redirect_uri="http://localhost:5173/auth/github/callback",
        )

        with respx.mock:
            route = respx.post(GITHUB_TOKEN_URL).respond(
                status_code=200,
                json={"access_token": "gho_test_token", "token_type": "bearer", "scope": "user,repo"},
            )

            result = await provider.exchange_code("test_code")

            assert result.access_token == "gho_test_token"
            assert result.token_type == "bearer"
            assert route.called


class TestGitHubProviderGetUserInfo:
    """GitHubProvider.get_user_info() 应用 access_token 获取用户信息"""

    @pytest.mark.asyncio
    async def test_get_user_info_returns_user_data(self):
        from services.auth.oauth import GitHubProvider

        provider = GitHubProvider(
            client_id="test_client_id",
            client_secret="test_secret",
            redirect_uri="http://localhost:5173/auth/github/callback",
        )

        with respx.mock:
            respx.get("https://api.github.com/user").respond(
                status_code=200,
                json={
                    "id": 12345,
                    "login": "testuser",
                    "email": "testuser@github.com",
                    "name": "Test User",
                },
            )

            user_info = await provider.get_user_info("gho_test_token")

            assert user_info.provider_user_id == "12345"
            assert user_info.username == "testuser"
            assert user_info.email == "testuser@github.com"


class TestOAuthProviderInterface:
    """所有 OAuthProvider 应遵循相同接口"""

    @pytest.mark.asyncio
    async def test_github_provider_implements_interface(self):
        from services.auth.oauth import GitHubProvider

        provider = GitHubProvider(
            client_id="id", client_secret="secret",
            redirect_uri="http://localhost/callback",
        )
        url = provider.get_authorization_url(state="x")
        assert isinstance(url, str)
        assert url.startswith("https://")

        with respx.mock:
            respx.post(GITHUB_TOKEN_URL).respond(status_code=200, json={"access_token": "t"})
            token = await provider.exchange_code("c")
            assert token.access_token == "t"

            respx.get("https://api.github.com/user").respond(
                status_code=200, json={"id": 1, "login": "u"},
            )
            info = await provider.get_user_info("t")
            assert info.username == "u"

    @pytest.mark.asyncio
    async def test_gitlab_provider_implements_interface(self):
        from services.auth.oauth import GitLabProvider

        provider = GitLabProvider(
            client_id="id", client_secret="secret",
            redirect_uri="http://localhost/callback",
        )
        url = provider.get_authorization_url(state="x")
        assert isinstance(url, str)
        assert url.startswith("https://")

        with respx.mock:
            respx.post(GITLAB_TOKEN_URL).respond(status_code=200, json={"access_token": "t"})
            token = await provider.exchange_code("c")
            assert token.access_token == "t"

            respx.get(GITLAB_USERINFO_URL).respond(
                status_code=200, json={"id": 1, "username": "u", "email": "u@gitlab.com", "name": "User"},
            )
            info = await provider.get_user_info("t")
            assert info.provider_user_id == "1"
            assert info.username == "u"
            assert info.email == "u@gitlab.com"


class TestGitHubProviderErrors:
    """异常场景测试"""

    @pytest.mark.asyncio
    async def test_exchange_code_raises_on_invalid_code(self):
        from services.auth.oauth import GitHubProvider

        provider = GitHubProvider(
            client_id="id", client_secret="secret",
            redirect_uri="http://localhost/callback",
        )

        with respx.mock:
            respx.post(GITHUB_TOKEN_URL).respond(status_code=401, json={"error": "bad_verification_code"})

            with pytest.raises(httpx.HTTPStatusError):
                await provider.exchange_code("invalid_code")

    @pytest.mark.asyncio
    async def test_get_user_info_raises_on_invalid_token(self):
        from services.auth.oauth import GitHubProvider

        provider = GitHubProvider(
            client_id="id", client_secret="secret",
            redirect_uri="http://localhost/callback",
        )

        with respx.mock:
            respx.get("https://api.github.com/user").respond(status_code=401)

            with pytest.raises(httpx.HTTPStatusError):
                await provider.get_user_info("invalid_token")
