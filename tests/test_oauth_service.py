import pytest
import respx
from sqlalchemy import select


GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"


class TestOAuthServiceInitiateLogin:
    """OAuthService.initiate_login() 应生成 state 并返回跳转 URL"""

    @pytest.mark.asyncio
    async def test_initiate_login_returns_authorization_url(self):
        from services.oauth_service import OAuthService
        from core.config import Config

        config = Config()
        config.oauth.github_client_id = "test_client_id"
        config.oauth.github_client_secret = "test_secret"
        config.oauth.github_redirect_uri = "http://localhost:5173/auth/github/callback"

        service = OAuthService(config)
        result = service.initiate_login("github")

        assert "authorization_url" in result
        assert "state" in result
        assert result["authorization_url"].startswith("https://github.com/login/oauth/authorize")
        assert "client_id=test_client_id" in result["authorization_url"]
        assert len(result["state"]) > 8

    def test_initiate_login_unknown_provider_raises(self):
        from services.oauth_service import OAuthService
        from core.config import Config

        config = Config()
        service = OAuthService(config)

        with pytest.raises(ValueError, match="Unsupported OAuth provider"):
            service.initiate_login("unknown")


class TestOAuthServiceHandleCallback:
    """OAuthService.handle_callback() 应用 code 交换令牌并创建/绑定用户"""

    @pytest.mark.asyncio
    async def test_handle_callback_creates_user_and_returns_tokens(self, async_db):
        from services.oauth_service import OAuthService
        from core.config import Config
        from models.user import User

        config = Config()
        config.oauth.github_client_id = "test_client_id"
        config.oauth.github_client_secret = "test_secret"
        config.oauth.github_redirect_uri = "http://localhost:5173/auth/github/callback"

        service = OAuthService(config)
        init_result = service.initiate_login("github")
        state = init_result["state"]

        with respx.mock:
            respx.post(GITHUB_TOKEN_URL).respond(
                status_code=200,
                json={"access_token": "gho_test_token", "token_type": "bearer", "scope": "user"},
            )
            respx.get("https://api.github.com/user").respond(
                status_code=200,
                json={
                    "id": "00000000-0000-0000-0000-000000000000",
                    "login": "oauth_user",
                    "email": "oauth@github.com",
                    "name": "OAuth User",
                },
            )

            result = await service.handle_callback(async_db, "github", "test_code", state)

        assert "token" in result
        assert "refresh_token" in result
        assert result["username"] == "oauth_user"
        assert result["email"] == "oauth@github.com"

        user = await async_db.get(User, result["id"])
        assert user is not None
        assert user.email == "oauth@github.com"

    @pytest.mark.asyncio
    async def test_handle_callback_links_existing_user_by_email(self, async_db, async_test_user):
        from services.oauth_service import OAuthService
        from core.config import Config
        from models.user_oauth import UserOAuthAccount

        async_test_user.email = "existing@github.com"
        await async_db.flush()

        config = Config()
        config.oauth.github_client_id = "id"
        config.oauth.github_client_secret = "secret"
        config.oauth.github_redirect_uri = "http://localhost/callback"

        service = OAuthService(config)
        init_result = service.initiate_login("github")
        state = init_result["state"]

        with respx.mock:
            respx.post(GITHUB_TOKEN_URL).respond(
                status_code=200, json={"access_token": "t", "token_type": "bearer", "scope": ""},
            )
            respx.get("https://api.github.com/user").respond(
                status_code=200,
                json={"id": 88888, "login": "existing_user", "email": "existing@github.com", "name": ""},
            )

            result = await service.handle_callback(async_db, "github", "code", state)

        assert result["id"] == async_test_user.id
        stmt = select(UserOAuthAccount).where(UserOAuthAccount.user_id == async_test_user.id)
        oauth_account = await async_db.execute(stmt)
        account = oauth_account.scalar_one()
        assert account.provider == "github"
        assert account.provider_user_id == "88888"


class TestOAuthServiceLinkAccount:
    """OAuthService 账号关联管理"""

    @pytest.mark.asyncio
    async def test_list_linked_accounts(self, async_db, async_test_user):
        from services.oauth_service import OAuthService
        from core.config import Config
        from models.user_oauth import UserOAuthAccount

        account = UserOAuthAccount(
            user_id=async_test_user.id, provider="github",
            provider_user_id="g_1", provider_username="gh_user",
        )
        async_db.add(account)
        await async_db.flush()

        config = Config()
        service = OAuthService(config)
        result = await service.list_linked_accounts(async_db, async_test_user.id)

        assert len(result) == 1
        assert result[0]["provider"] == "github"
        assert result[0]["provider_username"] == "gh_user"
        assert "access_token" not in result[0]

    @pytest.mark.asyncio
    async def test_unlink_account_success(self, async_db, async_test_user):
        from services.oauth_service import OAuthService
        from core.config import Config
        from models.user_oauth import UserOAuthAccount

        account = UserOAuthAccount(
            user_id=async_test_user.id, provider="github",
            provider_user_id="g_2", provider_username="gh_user2",
        )
        async_db.add(account)
        await async_db.flush()

        config = Config()
        service = OAuthService(config)
        await service.unlink_account(async_db, async_test_user.id, "github")

        stmt = select(UserOAuthAccount).where(
            UserOAuthAccount.user_id == async_test_user.id,
            UserOAuthAccount.provider == "github",
        )
        result = await async_db.execute(stmt)
        assert result.scalar_one_or_none() is None

    @pytest.mark.asyncio
    async def test_unlink_account_not_found_raises(self, async_db, async_test_user):
        from services.oauth_service import OAuthService
        from core.config import Config
        from core.exception import NotFoundException

        config = Config()
        service = OAuthService(config)

        with pytest.raises(NotFoundException):
            await service.unlink_account(async_db, async_test_user.id, "gitlab")
