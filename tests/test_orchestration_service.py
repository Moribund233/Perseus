"""
编排组件状态服务测试

用 httpx.MockTransport 模拟只读 Docker Engine API，覆盖：
- 正常获取组件状态（健康/重启次数/退出码/运行时长/排序）
- daemon 不可用时优雅降级 available=false
- compose 项目名自动探测
- 探测失败时回退到容器名前缀过滤
"""
import json
from datetime import datetime, timedelta, timezone

import httpx
import pytest

from services import orchestration_service as orch


def _client(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url="http://docker",
        transport=httpx.MockTransport(handler),
    )


def _container(cid, name, service, state, status):
    return {
        "Id": cid,
        "Names": [f"/{name}"],
        "Image": f"{name}:latest",
        "State": state,
        "Status": status,
        "Labels": {
            "com.docker.compose.service": service,
            "com.docker.compose.project": "perseus",
        },
    }


@pytest.mark.asyncio
async def test_get_components_success(monkeypatch):
    monkeypatch.setenv("PERSEUS_COMPOSE_PROJECT", "perseus")
    started = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/containers/json":
            return httpx.Response(200, json=[
                _container("appid", "perseus-app", "app", "running", "Up 1 hour (healthy)"),
                _container("redisid", "perseus-redis", "redis", "exited", "Exited (0) 5 min ago"),
            ])
        if path == "/containers/appid/json":
            return httpx.Response(200, json={
                "RestartCount": 0,
                "State": {"Status": "running", "Health": {"Status": "healthy"},
                          "StartedAt": started, "ExitCode": 0},
            })
        if path == "/containers/redisid/json":
            return httpx.Response(200, json={
                "RestartCount": 2,
                "State": {"Status": "exited", "StartedAt": started, "ExitCode": 0},
            })
        return httpx.Response(404)

    async with _client(handler) as client:
        result = await orch.get_orchestration_service().get_components(client=client)

    assert result["available"] is True
    assert result["project"] == "perseus"
    services = [c["service"] for c in result["components"]]
    assert services == ["app", "redis"]  # 按 COMPONENT_ORDER 排序

    app = result["components"][0]
    assert app["health"] == "healthy"
    assert app["running"] is True
    assert app["uptime_seconds"] and app["uptime_seconds"] >= 3500
    assert app["restart_count"] == 0
    assert app["label"] == "后端 (FastAPI)"

    redis = result["components"][1]
    assert redis["running"] is False
    assert redis["restart_count"] == 2
    assert redis["exit_code"] == 0

    assert result["summary"] == {
        "total": 2, "running": 1, "stopped": 1,
        "healthy": 1, "unhealthy": 0, "starting": 0,
    }


@pytest.mark.asyncio
async def test_get_components_unavailable(monkeypatch):
    monkeypatch.setenv("PERSEUS_COMPOSE_PROJECT", "perseus")

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("cannot connect to docker proxy")

    async with _client(handler) as client:
        result = await orch.get_orchestration_service().get_components(client=client)

    assert result["available"] is False
    assert result["components"] == []
    assert result["reason"]
    assert result["summary"]["total"] == 0


@pytest.mark.asyncio
async def test_detect_project_from_self_labels(monkeypatch):
    monkeypatch.delenv("PERSEUS_COMPOSE_PROJECT", raising=False)
    monkeypatch.setattr(orch.socket, "gethostname", lambda: "self123")

    seen_filters = {}

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/containers/self123/json":
            return httpx.Response(200, json={
                "Config": {"Labels": {"com.docker.compose.project": "perseus"}}
            })
        if path == "/containers/json":
            seen_filters.update(json.loads(request.url.params["filters"]))
            return httpx.Response(200, json=[
                _container("appid", "perseus-app", "app", "running", "Up")
            ])
        if path == "/containers/appid/json":
            return httpx.Response(200, json={
                "RestartCount": 0,
                "State": {"Status": "running", "StartedAt": None, "ExitCode": 0},
            })
        return httpx.Response(404)

    async with _client(handler) as client:
        result = await orch.get_orchestration_service().get_components(client=client)

    assert result["available"] is True
    assert result["project"] == "perseus"
    assert seen_filters.get("label") == ["com.docker.compose.project=perseus"]


@pytest.mark.asyncio
async def test_project_detect_failure_falls_back_to_name_prefix(monkeypatch):
    monkeypatch.delenv("PERSEUS_COMPOSE_PROJECT", raising=False)
    monkeypatch.setattr(orch.socket, "gethostname", lambda: "self123")

    seen_filters = {}

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/containers/self123/json":
            return httpx.Response(404)
        if path == "/containers/json":
            seen_filters.update(json.loads(request.url.params["filters"]))
            return httpx.Response(200, json=[])
        return httpx.Response(404)

    async with _client(handler) as client:
        result = await orch.get_orchestration_service().get_components(client=client)

    assert result["available"] is True
    assert result["project"] is None
    assert result["components"] == []
    assert seen_filters.get("name") == ["perseus-"]
