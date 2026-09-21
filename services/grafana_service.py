"""
Grafana 接入服务（admin 控制台 SSO）

为「仅 Perseus 的监控栈」提供自动注入 Grafana 认证凭据的通道：
- 后端持有 Grafana 管理员密码（``PERSEUS_GRAFANA_ADMIN_PASSWORD``，部署时由 .env 注入），
- 调用 Grafana ``{subpath}/login``（JSON 体，Grafana 11 起登录端点位于子路径下；
  旧版 ``/api/login`` 在 11.4 已不存在）换取 ``grafana_session``，随后以同源 Cookie
  （``Path=/grafana``，经网关反代 /grafana 子路径）下发浏览器，免手动登录。
- 与监控栈容器探测（``services/monitoring_service.py``）解耦：凭据注入失败
  不意味着监控栈不可用，反之亦然。

与 Grafana 的 HTTP 会话仅发生在本服务内（app 容器 → grafana 容器，均在同一
compose 网络）；浏览器从不直接访问 Grafana，仅经网关 ``/grafana`` 子路径走后端
下发的会话 Cookie。

环境变量：
- ``PERSEUS_GRAFANA_URL``             Grafana 内网地址，默认 ``http://grafana:3000``
- ``PERSEUS_GRAFANA_ADMIN_PASSWORD``  Grafana admin 密码（部署时由 .env 注入；缺失时 SSO 关闭）
- ``PERSEUS_GRAFANA_SUBPATH``         网关反代子路径，默认 ``/grafana``
"""
import logging
import os
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

DEFAULT_GRAFANA_URL = "http://grafana:3000"
DEFAULT_SUBPATH = "/grafana"


class GrafanaError(Exception):
    """Grafana 登录 / 连接失败"""


def _grafana_url() -> str:
    return os.environ.get("PERSEUS_GRAFANA_URL", DEFAULT_GRAFANA_URL).strip().rstrip("/")


def _admin_password() -> str:
    return os.environ.get("PERSEUS_GRAFANA_ADMIN_PASSWORD", "").strip()


def _subpath() -> str:
    return os.environ.get("PERSEUS_GRAFANA_SUBPATH", DEFAULT_SUBPATH).strip()


def _extract_session_cookie(resp: httpx.Response) -> Optional[str]:
    """从登录响应提取 grafana_session（优先响应 Cookie 罐，回退原始 Set-Cookie 头）"""
    value = resp.cookies.get("grafana_session")
    if value:
        return value
    for raw in resp.headers.get_list("set-cookie"):
        if raw.lstrip().lower().startswith("grafana_session="):
            return raw.split("=", 1)[1].split(";", 1)[0].strip()
    return None


class GrafanaService:
    """Grafana 会话接入服务"""

    @property
    def entry_path(self) -> str:
        """网关反代入口路径（前端据此跳转）"""
        return _subpath() or DEFAULT_SUBPATH

    @property
    def configured(self) -> bool:
        """是否已注入 Grafana 凭据（未配置则 SSO 不可用）"""
        return bool(_admin_password() and _grafana_url())

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(base_url=_grafana_url(), timeout=5.0)

    async def login(self) -> str:
        """
        以管理员身份登录 Grafana，返回 ``grafana_session`` Cookie 值。

        Grafana 11 的登录端点为 ``{subpath}/login``（JSON 体 ``user``/``password``），
        成功时返回 200 并下发 ``grafana_session``。旧的 ``/api/login`` 在 11.4
        已不再注册（会被 notfound 处理返回 401）。

        Raises:
            GrafanaError: 连接失败 / 凭据错误 / 未配置凭据
        """
        if not self.configured:
            raise GrafanaError("未配置 GF Grafana 凭据 (PERSEUS_GRAFANA_ADMIN_PASSWORD)")
        payload = {"user": "admin", "password": _admin_password()}
        url = _grafana_url() or DEFAULT_GRAFANA_URL
        subpath = (_subpath() or DEFAULT_SUBPATH).rstrip("/")
        login_path = f"{subpath}/login" if subpath else "/login"
        async with httpx.AsyncClient(base_url=url, timeout=5.0) as client:
            try:
                resp = await client.post(login_path, json=payload)
            except httpx.HTTPError as exc:
                logger.warning("Grafana 连接失败: %s", exc)
                raise GrafanaError(f"无法连接 Grafana: {url}") from exc

        if resp.status_code not in (200, 302, 303, 307):
            logger.warning(
                "Grafana 登录被拒 (path=%s status=%s)", login_path, resp.status_code
            )
            raise GrafanaError(f"Grafana 登录凭据无效或已拒绝 (HTTP {resp.status_code})")

        session = _extract_session_cookie(resp)
        if not session:
            raise GrafanaError("Grafana 响应未包含 grafana_session Cookie")
        return session


_grafana_service: Optional[GrafanaService] = None


def get_grafana_service() -> GrafanaService:
    """获取全局 Grafana 服务实例"""
    global _grafana_service
    if _grafana_service is None:
        _grafana_service = GrafanaService()
    return _grafana_service