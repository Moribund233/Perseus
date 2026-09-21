"""
监控栈（Prometheus / Grafana）端点与服务测试

覆盖：
- /api/app/monitoring 门控（匿名 401 / 非管理员 403）与成功/降级路径
- /api/app/monitoring/grafana/sso 成功下发 grafana_session Cookie（Path=/grafana）、
  凭据或连接失败时 502
- services.monitoring_service 容器探测 → ready 判定（与凭据注入耦合）
- 编排组件已纳入 prometheus / grafana 标签（监控栈启用时出现在组件列表）
"""
import pytest

import controller.app_controller as app_ctl
import services.monitoring_service as mon_svc

from services.grafana_service import GrafanaError


# ---- 端点门控 ----


class TestMonitoringGating:
    def test_requires_auth(self, test_client):
        assert test_client.get("/api/app/monitoring").status_code == 401
        assert test_client.get("/api/app/monitoring/grafana/sso").status_code == 401

    def test_requires_admin(self, test_client, auth_headers):
        r = test_client.get("/api/app/monitoring", headers=auth_headers)
        assert r.status_code == 403
        r = test_client.get("/api/app/monitoring/grafana/sso", headers=auth_headers)
        assert r.status_code == 403


# ---- /api/app/monitoring ----


def _fake_state(**kwargs):
    defaults = {"running": False, "configured": False, "ready": False, "entry": ""}
    defaults.update(kwargs)
    return defaults


class TestMonitoringEndpoint:
    def test_admin_ok_with_running_stack(self, test_client, admin_headers, monkeypatch):
        class FakeMon:
            async def get_monitoring(self):
                return {
                    "available": True,
                    "reason": None,
                    "generated_at": "2026-09-18T00:00:00+00:00",
                    "grafana": _fake_state(
                        running=True, configured=True, ready=True, entry="/grafana"
                    ),
                    "prometheus": _fake_state(running=True),
                }

        monkeypatch.setattr(app_ctl, "get_monitoring_service", FakeMon)
        r = test_client.get("/api/app/monitoring", headers=admin_headers)
        assert r.status_code == 200
        body = r.json()
        assert body["available"] is True
        assert body["grafana"]["ready"] is True
        assert body["grafana"]["entry"] == "/grafana"
        assert body["prometheus"]["running"] is True

    def test_admin_ok_grafana_not_ready(self, test_client, admin_headers, monkeypatch):
        class FakeMon:
            async def get_monitoring(self):
                return {
                    "available": True,
                    "reason": None,
                    "generated_at": "2026-09-18T00:00:00+00:00",
                    "grafana": _fake_state(
                        running=True, configured=False, ready=False, entry="/grafana"
                    ),
                    "prometheus": _fake_state(running=True),
                }

        monkeypatch.setattr(app_ctl, "get_monitoring_service", FakeMon)
        r = test_client.get("/api/app/monitoring", headers=admin_headers)
        assert r.status_code == 200
        assert r.json()["grafana"]["ready"] is False

    def test_admin_ok_degraded(self, test_client, admin_headers, monkeypatch):
        class FakeMon:
            async def get_monitoring(self):
                return {
                    "available": False,
                    "reason": "docker proxy 不可用",
                    "generated_at": "2026-09-18T00:00:00+00:00",
                    "grafana": _fake_state(running=False, configured=True, ready=False),
                    "prometheus": _fake_state(running=False),
                }

        monkeypatch.setattr(app_ctl, "get_monitoring_service", FakeMon)
        r = test_client.get("/api/app/monitoring", headers=admin_headers)
        assert r.status_code == 200
        body = r.json()
        assert body["available"] is False
        assert body["grafana"]["ready"] is False


# ---- /api/app/monitoring/grafana/sso ----


class TestGrafanaSso:
    def test_success_sets_cookie(self, test_client, admin_headers, monkeypatch):
        class FakeGrf:
            entry_path = "/grafana"

            async def login(self):
                return "session-token-abc"

        monkeypatch.setattr(app_ctl, "get_grafana_service", lambda: FakeGrf())
        r = test_client.get("/api/app/monitoring/grafana/sso", headers=admin_headers)
        assert r.status_code == 200
        body = r.json()
        assert body["ok"] is True
        assert body["entry"] == "/grafana"
        cookie = r.headers.get("set-cookie", "")
        assert "grafana_session=session-token-abc" in cookie
        assert "Path=/grafana" in cookie

    def test_failure_returns_502(self, test_client, admin_headers, monkeypatch):
        class FakeGrf:
            entry_path = "/grafana"

            async def login(self):
                raise GrafanaError("Grafana 登录凭据无效")

        monkeypatch.setattr(app_ctl, "get_grafana_service", lambda: FakeGrf())
        r = test_client.get("/api/app/monitoring/grafana/sso", headers=admin_headers)
        assert r.status_code == 502
        assert "Grafana" in r.json()["detail"]


# ---- services.monitoring_service 判定逻辑 ----


class TestMonitoringServiceDetection:
    @pytest.fixture
    def fake_orch(self):
        class FakeOrch:
            def __init__(self, data):
                self._data = data

            async def get_components(self, client=None):
                return self._data

        return FakeOrch

    @staticmethod
    def _components(*services):
        return {
            "available": True,
            "generated_at": "2026-09-18T00:00:00+00:00",
            "components": [
                {"service": s, "running": True} for s in services
            ],
        }

    async def test_ready_requires_running_and_credentials(self, monkeypatch, fake_orch):
        monkeypatch.setenv("PERSEUS_GRAFANA_ADMIN_PASSWORD", "secret")
        monkeypatch.setattr(
            mon_svc, "get_orchestration_service",
            lambda: fake_orch(self._components("graph", "grafana", "prometheus")),
        )
        svc = mon_svc.get_monitoring_service()
        result = await svc.get_monitoring()
        assert result["available"] is True
        assert result["grafana"]["running"] is True
        assert result["grafana"]["configured"] is True
        assert result["grafana"]["ready"] is True
        assert result["prometheus"]["running"] is True

    async def test_not_ready_without_credentials(self, monkeypatch, fake_orch):
        monkeypatch.delenv("PERSEUS_GRAFANA_ADMIN_PASSWORD", raising=False)
        monkeypatch.setattr(
            mon_svc, "get_orchestration_service",
            lambda: fake_orch(self._components("grafana", "prometheus")),
        )
        result = await mon_svc.get_monitoring_service().get_monitoring()
        assert result["grafana"]["running"] is True
        assert result["grafana"]["configured"] is False
        assert result["grafana"]["ready"] is False

    async def test_degraded_when_orchestration_unavailable(
        self, monkeypatch, fake_orch
    ):
        data = {
            "available": False,
            "reason": "docker proxy 不可用",
            "generated_at": "2026-09-18T00:00:00+00:00",
            "components": [],
        }
        monkeypatch.setattr(
            mon_svc, "get_orchestration_service", lambda: fake_orch(data),
        )
        result = await mon_svc.get_monitoring_service().get_monitoring()
        assert result["available"] is False
        assert result["grafana"]["ready"] is False

    async def test_grafana_absent_means_not_ready(self, monkeypatch, fake_orch):
        monkeypatch.setenv("PERSEUS_GRAFANA_ADMIN_PASSWORD", "secret")
        monkeypatch.setattr(
            mon_svc, "get_orchestration_service",
            lambda: fake_orch(self._components("prometheus")),
        )
        result = await mon_svc.get_monitoring_service().get_monitoring()
        assert result["grafana"]["running"] is False
        assert result["grafana"]["ready"] is False


# ---- 编排组件标签纳入监控栈 ----


def test_orchestration_includes_monitoring_components():
    from services.orchestration_service import COMPONENT_LABELS, COMPONENT_ORDER

    assert "prometheus" in COMPONENT_ORDER
    assert "grafana" in COMPONENT_ORDER
    assert "Prometheus" in COMPONENT_LABELS["prometheus"]
    assert "Grafana" in COMPONENT_LABELS["grafana"]


# ---- /api/app/monitoring/enabled 开关 ----

GRAFANA_ID = "a" * 64
PROMETHEUS_ID = "b" * 64


class FakeControl:
    """经窄写代理控制容器：启停时翻转 FakeOrch 里的 running 位，便于重扫描断言"""

    def __init__(self, data):
        self._data = data
        self.calls = []

    async def set_running(self, container_id, running, client=None):
        self.calls.append((container_id, running))
        for c in self._data.get("components", []):
            if c.get("container_id") == container_id:
                c["running"] = running


class FakeToggleOrch:
    def __init__(self, components, available=True, reason=None):
        self._data = {
            "available": available,
            "reason": reason,
            "generated_at": "2026-09-18T00:00:00+00:00",
            "components": components,
        }
        self.control = FakeControl(self._data)

    async def get_components(self, client=None):
        return self._data

    def with_run_state(self):
        """返回当前 running 位（与真实 get_components 同步）"""
        return {c["service"]: c for c in self._data["components"]}


def _toggle_stack(running):
    return [
        {
            "service": "grafana",
            "container_id": GRAFANA_ID,
            "running": running,
        },
        {
            "service": "prometheus",
            "container_id": PROMETHEUS_ID,
            "running": running,
        },
    ]


class TestMonitoringToggle:
    def test_requires_auth(self, test_client):
        r = test_client.post(
            "/api/app/monitoring/enabled", json={"enabled": True}
        )
        assert r.status_code == 401

    def test_requires_admin(self, test_client, auth_headers):
        r = test_client.post(
            "/api/app/monitoring/enabled",
            json={"enabled": True},
            headers=auth_headers,
        )
        assert r.status_code == 403

    def test_enable_starts_containers(self, test_client, admin_headers, monkeypatch):
        orch = FakeToggleOrch(_toggle_stack(running=False))
        monkeypatch.setattr(mon_svc, "get_orchestration_service", lambda: orch)
        monkeypatch.setattr(mon_svc, "get_docker_control_service", lambda: orch.control)
        monkeypatch.setattr(mon_svc, "_action_delay", lambda: 0)

        r = test_client.post(
            "/api/app/monitoring/enabled", json={"enabled": True}, headers=admin_headers
        )
        assert r.status_code == 200
        body = r.json()
        assert body["grafana"]["running"] is True
        assert body["prometheus"]["running"] is True
        assert body["grafana"]["container_id"] == GRAFANA_ID

        started = sorted([cid for cid, run in orch.control.calls if run])
        assert started == sorted([GRAFANA_ID, PROMETHEUS_ID])

    def test_disable_stops_containers(self, test_client, admin_headers, monkeypatch):
        orch = FakeToggleOrch(_toggle_stack(running=True))
        monkeypatch.setattr(mon_svc, "get_orchestration_service", lambda: orch)
        monkeypatch.setattr(mon_svc, "get_docker_control_service", lambda: orch.control)
        monkeypatch.setattr(mon_svc, "_action_delay", lambda: 0)

        r = test_client.post(
            "/api/app/monitoring/enabled",
            json={"enabled": False},
            headers=admin_headers,
        )
        assert r.status_code == 200
        assert r.json()["grafana"]["running"] is False
        stopped = sorted([cid for cid, run in orch.control.calls if not run])
        assert stopped == sorted([GRAFANA_ID, PROMETHEUS_ID])

    def test_not_deployed_returns_409(self, test_client, admin_headers, monkeypatch):
        orchid = FakeToggleOrch(
            [{"service": "grafana", "container_id": None, "running": False}]
        )
        monkeypatch.setattr(mon_svc, "get_orchestration_service", lambda: orchid)
        monkeypatch.setattr(mon_svc, "_action_delay", lambda: 0)

        r = test_client.post(
            "/api/app/monitoring/enabled",
            json={"enabled": True},
            headers=admin_headers,
        )
        assert r.status_code == 409
        detail = r.json()["detail"]
        assert "unavailable" in detail or "未部署" in detail

    def test_orchestration_unavailable_returns_502(
        self, test_client, admin_headers, monkeypatch
    ):
        orchid = FakeToggleOrch([], available=False, reason="docker proxy 不可用")
        monkeypatch.setattr(mon_svc, "get_orchestration_service", lambda: orchid)

        r = test_client.post(
            "/api/app/monitoring/enabled",
            json={"enabled": True},
            headers=admin_headers,
        )
        assert r.status_code == 502

    async def test_control_failure_returns_502(
        self, test_client, admin_headers, monkeypatch
    ):
        orch = FakeToggleOrch(_toggle_stack(running=False))

        class FailingControl:
            async def set_running(self, container_id, running, client=None):
                raise Exception("proxy refused")  # noqa: TRY002

        monkeypatch.setattr(mon_svc, "get_orchestration_service", lambda: orch)
        monkeypatch.setattr(
            mon_svc, "get_docker_control_service", lambda: FailingControl()
        )

        r = test_client.post(
            "/api/app/monitoring/enabled",
            json={"enabled": True},
            headers=admin_headers,
        )
        assert r.status_code == 502