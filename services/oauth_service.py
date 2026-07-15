import logging
import secrets
import time
import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import Config
from core.exception import AuthenticationException, ConflictException, NotFoundException
from models.user import User
from models.user_oauth import UserOAuthAccount
from services.token_service import create_token_pair
from services.auth.oauth import GitHubProvider, GitLabProvider, OAuthProvider

logger = logging.getLogger(__name__)

STATE_TTL = 600  # 10 minutes


class OAuthStateStore:
    """OAuth state 临时存储（内存实现，生产环境应换 Redis）"""

    def __init__(self):
        self._states: dict[str, dict] = {}

    def generate(self, provider: str) -> str:
        state = secrets.token_urlsafe(32)
        self._states[state] = {
            "provider": provider,
            "created_at": time.time(),
        }
        return state

    def consume(self, state: str, provider: str) -> bool:
        data = self._states.pop(state, None)
        if data is None:
            return False
        if data["provider"] != provider:
            return False
        if time.time() - data["created_at"] > STATE_TTL:
            return False
        return True


_state_store = OAuthStateStore()


class OAuthService:
    def __init__(self, config: Config):
        self.config = config

    def _get_provider(self, provider_name: str) -> OAuthProvider:
        oauth_config = self.config.oauth
        if provider_name == "github":
            if not oauth_config.github_client_id:
                raise ValueError(f"GitHub OAuth client_id not configured")
            return GitHubProvider(
                client_id=oauth_config.github_client_id,
                client_secret=oauth_config.github_client_secret,
                redirect_uri=oauth_config.github_redirect_uri,
            )
        elif provider_name == "gitlab":
            if not oauth_config.gitlab_client_id:
                raise ValueError(f"GitLab OAuth client_id not configured")
            return GitLabProvider(
                client_id=oauth_config.gitlab_client_id,
                client_secret=oauth_config.gitlab_client_secret,
                redirect_uri=oauth_config.gitlab_redirect_uri,
            )
        raise ValueError(f"Unsupported OAuth provider: {provider_name}")

    def initiate_login(self, provider_name: str) -> dict:
        provider = self._get_provider(provider_name)
        state = _state_store.generate(provider_name)
        auth_url = provider.get_authorization_url(state=state)
        return {"authorization_url": auth_url, "state": state}

    async def handle_callback(
        self,
        db: AsyncSession,
        provider_name: str,
        code: str,
        state: str,
    ) -> dict:
        if not _state_store.consume(state, provider_name):
            raise AuthenticationException("Invalid or expired OAuth state")

        provider = self._get_provider(provider_name)
        token_resp = await provider.exchange_code(code)
        user_info = await provider.get_user_info(token_resp.access_token)

        existing = await db.execute(
            select(UserOAuthAccount).where(
                UserOAuthAccount.provider == provider_name,
                UserOAuthAccount.provider_user_id == user_info.provider_user_id,
            )
        )
        account = existing.scalar_one_or_none()

        if account:
            user = await db.get(User, account.user_id)
            account.access_token = token_resp.access_token
            if token_resp.refresh_token:
                account.refresh_token = token_resp.refresh_token
        else:
            existing_user = None
            if user_info.email:
                user_result = await db.execute(
                    select(User).where(User.email == user_info.email)
                )
                existing_user = user_result.scalar_one_or_none()

            if existing_user:
                user = existing_user
            else:
                user = User(
                    username=user_info.username,
                    email=user_info.email or f"{user_info.provider_user_id}@{provider_name}.oauth",
                    password=secrets.token_urlsafe(32),
                    full_name=user_info.full_name or None,
                    is_active=True,
                )
                db.add(user)
                await db.flush()

            account = UserOAuthAccount(
                user_id=user.id,
                provider=provider_name,
                provider_user_id=user_info.provider_user_id,
                provider_username=user_info.username,
                access_token=token_resp.access_token,
                refresh_token=token_resp.refresh_token,
            )
            db.add(account)

        await db.commit()
        await db.refresh(user)

        tokens = create_token_pair(user, extra_claims={"oauth_provider": provider_name})
        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "is_admin": user.is_admin,
            "token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"],
        }

    async def list_linked_accounts(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
    ) -> list[dict]:
        result = await db.execute(
            select(UserOAuthAccount).where(UserOAuthAccount.user_id == user_id)
        )
        accounts = result.scalars().all()
        return [
            {
                "provider": a.provider,
                "provider_username": a.provider_username,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in accounts
        ]

    async def unlink_account(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        provider: str,
    ) -> None:
        result = await db.execute(
            select(UserOAuthAccount).where(
                UserOAuthAccount.user_id == user_id,
                UserOAuthAccount.provider == provider,
            )
        )
        account = result.scalar_one_or_none()
        if account is None:
            raise NotFoundException(detail=f"Linked {provider} account not found")
        await db.delete(account)
        await db.commit()
