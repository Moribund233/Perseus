"""
GrafanaService SSO 登录测试。

锁定 Grafana 11 的登录契约：端点位于 ``{subpath}/login``（而非已废弃的
``/api/login``），请求体为 JSON ``{"user","password"}``，成功时从
``grafana_session`` Cookie 取值。此前的 ``/api/login`` 在 11.4 未注册，
会导致管理台「打开 Grafana」恒报 401。
"""
import httpx
import pytest

from services import grafana_service
from services.grafana_service import GrafanaError, GrafanaService


class _FakeAsyncClient:
    """记录请求并返回预置响应的 httpx.AsyncClient 替身"""

    response: httpx.Response = None  # type: ignore[assignment]
    calls: list = []

    def __init__(self, *args, **kwargs):
        self.base_url = kwargs.get("base_url") or (args[0] if args else None)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def post(self, path, **kwargs):
        _FakeAsyncClient.calls.append({"path": path, "json": kwargs.get("json")})
        return _FakeAsyncClient.response


@pytest.fixture
def grafana_env(monkeypatch):
    monkeypatch.setenv("PERSEUS_GRAFANA_URL", "http://grafana:3000")
    monkeypatch.setenv("PERSEUS_GRAFANA_ADMIN_PASSWORD", "s3cret")
    monkeypatch.setenv("PERSEUS_GRAFANA_SUBPATH", "/grafana")
    _FakeAsyncClient.calls = []
    _FakeAsyncClient.response = httpx.Response(
        200,
        headers={"set-cookie": "grafana_session=abc123; Path=/grafana/; HttpOnly"},
        request=httpx.Request("POST", "http://grafana:3000/grafana/login"),
    )
    monkeypatch.setattr(grafana_service.httpx, "AsyncClient", _FakeAsyncClient)


async def test_login_uses_subpath_endpoint_with_json(grafana_env):
    session = await GrafanaService().login()

    assert session == "abc123"
    assert len(_FakeAsyncClient.calls) == 1
    assert _FakeAsyncClient.calls[0]["path"] == "/grafana/login"
    assert _FakeAsyncClient.calls[0]["json"] == {
        "user": "admin",
        "password": "s3cret",
    }


async def test_login_honors_custom_subpath(grafana_env, monkeypatch):
    monkeypatch.setenv("PERSEUS_GRAFANA_SUBPATH", "/mon/")

    await GrafanaService().login()

    assert _FakeAsyncClient.calls[0]["path"] == "/mon/login"


async def test_login_raises_on_rejected_credentials(grafana_env):
    _FakeAsyncClient.response = httpx.Response(401, json={"message": "Unauthorized"})

    with pytest.raises(GrafanaError, match="HTTP 401"):
        await GrafanaService().login()


async def test_login_raises_when_not_configured(monkeypatch):
    monkeypatch.delenv("PERSEUS_GRAFANA_ADMIN_PASSWORD", raising=False)

    with pytest.raises(GrafanaError, match="未配置"):
        await GrafanaService().login()


async def test_login_raises_without_session_cookie(grafana_env):
    _FakeAsyncClient.response = httpx.Response(
        200,
        json={"message": "Logged in"},
        request=httpx.Request("POST", "http://grafana:3000/grafana/login"),
    )

    with pytest.raises(GrafanaError, match="grafana_session"):
        await GrafanaService().login()