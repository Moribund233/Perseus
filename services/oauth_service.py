import json
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
from utils.redis_client import get_redis, key as redis_key

logger = logging.getLogger(__name__)

STATE_TTL = 600  # 10 minutes


class OAuthStateStore:
    """
    OAuth state 临时存储。

    Redis 可用时以共享键存储（``perseus:oauth:state:<state>``，带 TTL），
    使多 worker / 多副本下签发与回调校验一致；Redis 不可用时回退进程内
    内存并**显式告警**（不再静默，见规划 D2）。内存副本始终写入，作为
    同 worker 的本地兜底。
    """

    def __init__(self, ttl: int = STATE_TTL):
        self._ttl = ttl
        self._states: dict[str, dict] = {}
        self._warned = False

    def _warn_fallback(self) -> None:
        if not self._warned:
            self._warned = True
            logger.warning(
                "OAuth state 存储回退进程内内存（Redis 不可用）；多 worker 下登录可能失败"
            )

    @staticmethod
    def _validate(raw: str, provider: str) -> bool:
        try:
            data = json.loads(raw)
        except (ValueError, TypeError):
            return False
        if not isinstance(data, dict) or data.get("provider") != provider:
            return False
        created_at = data.get("created_at")
        if not isinstance(created_at, (int, float)):
            return False
        return (time.time() - created_at) <= STATE_TTL

    async def generate(self, provider: str) -> str:
        state = secrets.token_urlsafe(32)
        payload = {"provider": provider, "created_at": time.time()}
        # 内存兜底（同 worker 场景 / Redis 抖动）
        self._states[state] = payload
        client = await get_redis()
        if client is not None:
            try:
                await client.setex(
                    redis_key("oauth", "state", state),
                    self._ttl,
                    json.dumps(payload),
                )
                return state
            except Exception as exc:  # noqa: BLE001 — 写失败即降级
                logger.warning("OAuth state 写入 Redis 失败，回退内存: %s", exc)
        self._warn_fallback()
        return state

    async def consume(self, state: str, provider: str) -> bool:
        client = await get_redis()
        if client is not None:
            try:
                raw = await client.getdel(redis_key("oauth", "state", state))
            except Exception as exc:  # noqa: BLE001
                logger.warning("OAuth state 读取 Redis 失败，回退内存: %s", exc)
                raw = None
            if raw is not None:
                return self._validate(raw, provider)
        return self._consume_memory(state, provider)

    def _consume_memory(self, state: str, provider: str) -> bool:
        data = self._states.pop(state, None)
        if data is None or data.get("provider") != provider:
            return False
        return (time.time() - data["created_at"]) <= STATE_TTL


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

    async def initiate_login(self, provider_name: str) -> dict:
        provider = self._get_provider(provider_name)
        state = await _state_store.generate(provider_name)
        auth_url = provider.get_authorization_url(state=state)
        return {"authorization_url": auth_url, "state": state}

    async def handle_callback(
        self,
        db: AsyncSession,
        provider_name: str,
        code: str,
        state: str,
    ) -> dict:
        if not await _state_store.consume(state, provider_name):
            raise AuthenticationException("Invalid or expired OAuth state", error_code="oauth_invalid_state")

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
            if user is None:
                raise AuthenticationException("Linked OAuth account has no matching user", error_code="oauth_no_matching_user")
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
            raise NotFoundException(detail=f"Linked {provider} account not found", error_code="oauth_account_not_found")
        await db.delete(account)
        await db.commit()
