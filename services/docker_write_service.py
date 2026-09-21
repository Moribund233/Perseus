"""
低权限 Docker 写操作服务

经窄写代理（docker-write-proxy）启停容器，供 admin 控制台开关可选服务栈
（如 Prometheus / Grafana）。本服务**只**暴露 start/stop/restart 三个动作，
路径、方法与项目归属双重校验都在代理层完成（见 docker/docker-write-proxy），
应用侧无法借它触碰 create/exec/pull 等 Docker 控制面接口。

设计要点：
- 每个动作都是 POST /containers/{id}/{action}；204=成功，304=目标态已满足，
  其余状态码（404 容器不存在 / 403 代理拒绝 / 5xx）统一抛 DockerControlError
- 与只读编排服务分离：读容器状态仍走 docker-socket-proxy（PERSEUS_DOCKER_HOST）
- 读端点超时复用 PERSEUS_ORCHESTRATION_TIMEOUT，保证与编排探测口径一致

环境变量：
- ``PERSEUS_DOCKER_WRITE_HOST``  窄写代理端点，默认 ``http://docker-write-proxy:2376``
- ``PERSEUS_ORCHESTRATION_TIMEOUT`` 请求超时秒数，默认 5
"""
import logging
import os
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

DEFAULT_DOCKER_WRITE_HOST = "http://docker-write-proxy:2376"

ACTION_START = "start"
ACTION_STOP = "stop"
ACTION_RESTART = "restart"


class DockerControlError(Exception):
    """容器控制失败（代理拒绝 / 拉取不到容器 / 依赖异常）"""


def _write_host() -> str:
    return os.environ.get(
        "PERSEUS_DOCKER_WRITE_HOST", DEFAULT_DOCKER_WRITE_HOST
    ).strip()


def _timeout() -> float:
    try:
        return float(os.environ.get("PERSEUS_ORCHESTRATION_TIMEOUT", "5"))
    except (TypeError, ValueError):
        return 5.0


class DockerControlService:
    """窄写 Docker 控制服务（仅启停容器）"""

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(base_url=_write_host(), timeout=_timeout())

    async def set_running(
        self,
        container_id: str,
        running: bool,
        client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        """
        启/停单个容器。

        Args:
            container_id: Docker 容器 ID（短 ID 亦可）
            running: True=启动容器，False=停止容器
            client: 可选的 httpx.AsyncClient（测试注入用）

        Raises:
            DockerControlError: 代理拒绝、请求失败或返回非预期状态码
        """
        action = ACTION_START if running else ACTION_STOP
        owns_client = client is None
        client = client or self._client()
        try:
            resp = await client.post(f"/containers/{container_id}/{action}")
        except httpx.HTTPError as exc:
            raise DockerControlError(
                f"无法连接窄写代理启停容器 {container_id[:12]}: {exc}"
            ) from exc
        finally:
            if owns_client:
                await client.aclose()

        if resp.status_code in (204, 304):
            return
        if resp.status_code == 403:
            raise DockerControlError(
                f"窄写代理拒绝操作（{action}）: 容器 {container_id[:12]} 不在允许范围"
            )
        if resp.status_code == 404:
            raise DockerControlError(
                f"容器不存在（{action}）: {container_id[:12]}"
            )
        raise DockerControlError(
            f"{action} 容器 {container_id[:12]} 失败 (HTTP {resp.status_code})"
        )


_control_service: Optional[DockerControlService] = None


def get_docker_control_service() -> DockerControlService:
    """获取全局窄写 Docker 控制服务实例"""
    global _control_service
    if _control_service is None:
        _control_service = DockerControlService()
    return _control_service