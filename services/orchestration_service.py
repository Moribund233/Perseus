"""
编排组件状态服务

通过只读 Docker socket 代理（docker-socket-proxy）查询 compose 各容器状态，
供管理员在 admin 控制台可视化 Perseus 各组件的健康度。

设计要点：
- 只使用只读 Docker Engine API：``GET /containers/json``、``GET /containers/{id}/json``
- daemon / 代理不可用时优雅降级为 ``available=false``，不抛 5xx
- 优先用 compose 标签 ``com.docker.compose.project`` 定位本项目容器；
  无法确定项目时回退到容器名前缀过滤（默认 ``perseus-``）

环境变量：
- ``PERSEUS_DOCKER_HOST``        Docker 端点，默认 ``http://docker-socket-proxy:2375``
- ``PERSEUS_COMPOSE_PROJECT``    显式指定 compose 项目名（默认自动探测）
- ``PERSEUS_CONTAINER_PREFIX``   项目无法探测时的容器名前缀，默认 ``perseus-``
- ``PERSEUS_ORCHESTRATION_TIMEOUT`` 请求超时秒数，默认 5
"""
import asyncio
import json
import logging
import os
import socket
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

DEFAULT_DOCKER_HOST = "http://docker-socket-proxy:2375"
DEFAULT_CONTAINER_PREFIX = "perseus-"

# 组件展示顺序（compose service 名；prometheus/grafana 仅在启用监控栈时出现）
COMPONENT_ORDER = [
    "gateway",
    "app",
    "collab",
    "git-cgi",
    "sshd",
    "postgres",
    "redis",
    "init",
    "prometheus",
    "grafana",
]

COMPONENT_LABELS = {
    "gateway": "网关 (OpenResty)",
    "app": "后端 (FastAPI)",
    "collab": "协作网关 (Hocuspocus)",
    "git-cgi": "Git HTTP (git-http-backend)",
    "sshd": "SSH (Git over SSH)",
    "postgres": "PostgreSQL",
    "redis": "Redis",
    "init": "数据库初始化任务",
    "prometheus": "Prometheus (监控)",
    "grafana": "Grafana (监控)",
}


def _docker_host() -> str:
    return os.environ.get("PERSEUS_DOCKER_HOST", DEFAULT_DOCKER_HOST).strip()


def _configured_project() -> Optional[str]:
    value = os.environ.get("PERSEUS_COMPOSE_PROJECT", "").strip()
    return value or None


def _container_prefix() -> str:
    return os.environ.get("PERSEUS_CONTAINER_PREFIX", DEFAULT_CONTAINER_PREFIX).strip()


def _timeout() -> float:
    try:
        return float(os.environ.get("PERSEUS_ORCHESTRATION_TIMEOUT", "5"))
    except (TypeError, ValueError):
        return 5.0


def _empty_result(reason: Optional[str]) -> Dict[str, Any]:
    return {
        "available": False,
        "runtime": "docker",
        "project": None,
        "reason": reason,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "components": [],
        "summary": {
            "total": 0,
            "running": 0,
            "stopped": 0,
            "healthy": 0,
            "unhealthy": 0,
            "starting": 0,
        },
    }


class OrchestrationService:
    """编排组件状态服务（只读）"""

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(base_url=_docker_host(), timeout=_timeout())

    async def get_components(
        self, client: Optional[httpx.AsyncClient] = None
    ) -> Dict[str, Any]:
        """
        获取本项目各组件状态。

        Args:
            client: 可选的 httpx.AsyncClient（测试注入用）

        Returns:
            Dict[str, Any]: 组件状态与汇总；daemon 不可用时 available=false
        """
        owns_client = client is None
        client = client or self._client()
        try:
            project = _configured_project() or await self._detect_project(client)
            containers = await self._list_containers(client, project)
            components = await self._build_components(client, containers)
            return {
                "available": True,
                "runtime": "docker",
                "project": project,
                "reason": None,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "components": components,
                "summary": self._summarize(components),
            }
        except Exception as exc:  # noqa: BLE001 — 任何失败都降级，不 5xx
            logger.warning("获取编排组件状态失败: %s", exc)
            return _empty_result(str(exc) or exc.__class__.__name__)
        finally:
            if owns_client:
                await client.aclose()

    async def _detect_project(
        self, client: httpx.AsyncClient
    ) -> Optional[str]:
        """通过检查自身容器标签探测 compose 项目名"""
        hostname = socket.gethostname()
        try:
            resp = await client.get(f"/containers/{hostname}/json")
            if resp.status_code == 200:
                labels = (resp.json().get("Config") or {}).get("Labels") or {}
                return labels.get("com.docker.compose.project")
        except httpx.HTTPError:
            pass
        return None

    async def _list_containers(
        self, client: httpx.AsyncClient, project: Optional[str]
    ) -> List[Dict[str, Any]]:
        if project:
            filters: Dict[str, Any] = {
                "label": [f"com.docker.compose.project={project}"]
            }
        else:
            filters = {"name": [_container_prefix()]}
        resp = await client.get(
            "/containers/json",
            params={"all": 1, "filters": json.dumps(filters)},
        )
        resp.raise_for_status()
        return resp.json()

    async def _build_components(
        self, client: httpx.AsyncClient, containers: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        async def inspect(
            container: Dict[str, Any]
        ) -> tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
            cid = container.get("Id")
            if not cid:
                return container, None
            try:
                resp = await client.get(f"/containers/{cid}/json")
                if resp.status_code == 200:
                    return container, resp.json()
            except httpx.HTTPError:
                pass
            return container, None

        pairs = await asyncio.gather(*(inspect(c) for c in containers))
        components = [self._to_component(c, d) for c, d in pairs]
        order = {name: i for i, name in enumerate(COMPONENT_ORDER)}
        components.sort(key=lambda x: order.get(x["service"], len(COMPONENT_ORDER)))
        return components

    def _to_component(
        self,
        container: Dict[str, Any],
        detail: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        labels = container.get("Labels") or {}
        names = container.get("Names") or []
        name = (names[0].lstrip("/") if names else container.get("Id", "")[:12])
        service = labels.get("com.docker.compose.service") or name

        state = container.get("State") or "unknown"
        health: Optional[str] = None
        started_at: Optional[str] = None
        restart_count: Optional[int] = None
        exit_code: Optional[int] = None

        if detail:
            state_obj = detail.get("State") or {}
            state = state_obj.get("Status", state)
            health_obj = state_obj.get("Health") or {}
            health = health_obj.get("Status")
            started_at = state_obj.get("StartedAt")
            restart_count = detail.get("RestartCount")
            exit_code = state_obj.get("ExitCode")

        uptime_seconds: Optional[int] = None
        if state == "running" and started_at:
            try:
                started = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
                uptime_seconds = max(
                    0, int((datetime.now(timezone.utc) - started).total_seconds())
                )
            except (ValueError, TypeError):
                uptime_seconds = None

        return {
            "service": service,
            "name": name,
            "label": COMPONENT_LABELS.get(service, service),
            "container_id": container.get("Id"),
            "state": state,
            "health": health,
            "running": state == "running",
            "image": container.get("Image"),
            "started_at": started_at,
            "uptime_seconds": uptime_seconds,
            "restart_count": restart_count,
            "exit_code": exit_code,
            "status_text": container.get("Status"),
        }

    def _summarize(self, components: List[Dict[str, Any]]) -> Dict[str, int]:
        return {
            "total": len(components),
            "running": sum(1 for c in components if c["running"]),
            "stopped": sum(1 for c in components if not c["running"]),
            "healthy": sum(1 for c in components if c["health"] == "healthy"),
            "unhealthy": sum(1 for c in components if c["health"] == "unhealthy"),
            "starting": sum(1 for c in components if c["health"] == "starting"),
        }


_orchestration_service: Optional[OrchestrationService] = None


def get_orchestration_service() -> OrchestrationService:
    """获取全局编排状态服务实例"""
    global _orchestration_service
    if _orchestration_service is None:
        _orchestration_service = OrchestrationService()
    return _orchestration_service
