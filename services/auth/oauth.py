import urllib.parse
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

import httpx


@dataclass
class OAuthUserInfo:
    provider_user_id: str
    username: str
    email: str = ""
    full_name: str = ""


@dataclass
class OAuthTokenResponse:
    access_token: str
    token_type: str = "bearer"
    scope: str = ""
    refresh_token: Optional[str] = None
    expires_in: Optional[int] = None


class OAuthProvider(ABC):
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri

    @abstractmethod
    def get_authorization_url(self, state: str) -> str:
        ...

    @abstractmethod
    async def exchange_code(self, code: str) -> OAuthTokenResponse:
        ...

    @abstractmethod
    async def get_user_info(self, access_token: str) -> OAuthUserInfo:
        ...


GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USERINFO_URL = "https://api.github.com/user"


class GitHubProvider(OAuthProvider):
    def get_authorization_url(self, state: str) -> str:
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "state": state,
            "response_type": "code",
        }
        return f"{GITHUB_AUTHORIZE_URL}?{urllib.parse.urlencode(params)}"

    async def exchange_code(self, code: str) -> OAuthTokenResponse:
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "redirect_uri": self.redirect_uri,
        }
        headers = {"Accept": "application/json"}
        async with httpx.AsyncClient() as client:
            resp = await client.post(GITHUB_TOKEN_URL, data=data, headers=headers)
            resp.raise_for_status()
            body = resp.json()
        return OAuthTokenResponse(**body)

    async def get_user_info(self, access_token: str) -> OAuthUserInfo:
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }
        async with httpx.AsyncClient() as client:
            resp = await client.get(GITHUB_USERINFO_URL, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        return OAuthUserInfo(
            provider_user_id=str(data["id"]),
            username=data["login"],
            email=data.get("email", ""),
            full_name=data.get("name", ""),
        )


GITLAB_AUTHORIZE_URL = "https://gitlab.com/oauth/authorize"
GITLAB_TOKEN_URL = "https://gitlab.com/oauth/token"
GITLAB_USERINFO_URL = "https://gitlab.com/api/v4/user"


class GitLabProvider(OAuthProvider):
    def get_authorization_url(self, state: str) -> str:
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "state": state,
            "response_type": "code",
            "scope": "read_user email",
        }
        return f"{GITLAB_AUTHORIZE_URL}?{urllib.parse.urlencode(params)}"

    async def exchange_code(self, code: str) -> OAuthTokenResponse:
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": self.redirect_uri,
        }
        headers = {"Accept": "application/json"}
        async with httpx.AsyncClient() as client:
            resp = await client.post(GITLAB_TOKEN_URL, data=data, headers=headers)
            resp.raise_for_status()
            body = resp.json()
        return OAuthTokenResponse(**body)

    async def get_user_info(self, access_token: str) -> OAuthUserInfo:
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }
        async with httpx.AsyncClient() as client:
            resp = await client.get(GITLAB_USERINFO_URL, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        return OAuthUserInfo(
            provider_user_id=str(data["id"]),
            username=data["username"],
            email=data.get("email", ""),
            full_name=data.get("name", ""),
        )
