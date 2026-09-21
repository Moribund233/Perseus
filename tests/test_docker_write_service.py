"""窄写 Docker 控制服务（docker-write-proxy）单元测试"""
import httpx
import pytest
import respx

import services.docker_write_service as svc
from services.docker_write_service import DockerControlError


@pytest.fixture(autouse=True)
def clear_singleton():
    svc._control_service = None
    yield
    svc._control_service = None


class TestSetRunning:
    @pytest.mark.asyncio
    async def test_start_success(self, monkeypatch):
        monkeypatch.setattr(svc, "_write_host", lambda: "http://write-proxy:2376")
        client = httpx.AsyncClient(base_url="http://write-proxy:2376")
        with respx.mock:
            respx.post("http://write-proxy:2376/containers/abcdef123456/start").mock(
                return_value=httpx.Response(204)
            )
            await svc.DockerControlService().set_running(
                "abcdef123456", True, client=client
            )
        await client.aclose()

    @pytest.mark.asyncio
    async def test_stop_304_idempotent(self, monkeypatch):
        monkeypatch.setattr(svc, "_write_host", lambda: "http://write-proxy:2376")
        client = httpx.AsyncClient(base_url="http://write-proxy:2376")
        with respx.mock:
            respx.post("http://write-proxy:2376/containers/abcdef123456/stop").mock(
                return_value=httpx.Response(304)
            )
            await svc.DockerControlService().set_running(
                "abcdef123456", False, client=client
            )
        await client.aclose()

    @pytest.mark.asyncio
    async def test_proxy_403_raises(self, monkeypatch):
        monkeypatch.setattr(svc, "_write_host", lambda: "http://write-proxy:2376")
        client = httpx.AsyncClient(base_url="http://write-proxy:2376")
        with respx.mock:
            respx.post("http://write-proxy:2376/containers/abcdef123456/start").mock(
                return_value=httpx.Response(403)
            )
            with pytest.raises(DockerControlError, match="拒绝"):
                await svc.DockerControlService().set_running(
                    "abcdef123456", True, client=client
                )
        await client.aclose()

    @pytest.mark.asyncio
    async def test_404_raises(self, monkeypatch):
        monkeypatch.setattr(svc, "_write_host", lambda: "http://write-proxy:2376")
        client = httpx.AsyncClient(base_url="http://write-proxy:2376")
        with respx.mock:
            respx.post("http://write-proxy:2376/containers/abcdef123456/start").mock(
                return_value=httpx.Response(404)
            )
            with pytest.raises(DockerControlError, match="容器不存在"):
                await svc.DockerControlService().set_running(
                    "abcdef123456", True, client=client
                )
        await client.aclose()

    @pytest.mark.asyncio
    async def test_connection_error_raises(self, monkeypatch):
        client = httpx.AsyncClient(base_url="http://write-proxy:2376")
        with respx.mock:
            respx.post("http://write-proxy:2376/containers/abcdef123456/start").mock(
                side_effect=httpx.ConnectError("connection refused")
            )
            with pytest.raises(DockerControlError, match="连接"):
                await svc.DockerControlService().set_running(
                    "abcdef123456", True, client=client
                )
        await client.aclose()