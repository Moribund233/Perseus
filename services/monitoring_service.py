"""
监控栈（Prometheus / Grafana）探测与控制服务

- ``get_monitoring``：复用编排服务经只读 docker-socket-proxy 的容器清单，
  判定监控栈是否在运行，并为 admin 控制台提供 Grafana 入口的可用性；
  探测失败一律降级 ``available=false``（与编排组件一致），不向调用方抛 5xx。
- ``set_enabled``：经窄写代理（docker-write-proxy）启停监控栈容器，实现
  admin 控制台的「监控开关」；仅当容器已创建（监控栈曾部署过）可操作，
  从未部署过时抛 ``MonitoringControlError``（需先在部署机拉起 compose）。

探测来源：监控栈容器与业务层同属一个 compose project（``com.docker.compose.project``，
一键部署在仓库根目录先后拉起两套 compose），故 ``perseus-prometheus`` /
``perseus-grafana`` 天然落在编排服务的标签过滤范围内。

Grafana 入口可用性（``ready``）口径：
- 监控栈可探测时：Grafana 容器运行中 **且** 已注入凭据（后端有能力下发会话 Cookie）；
- 仍在保留 docker 探测（``available=false``）时：无从确认容器状态，一律视为未就绪，
  避免出现可点击却 502 的空洞入口。

环境变量：
- ``PERSEUS_MONITORING_ACTION_DELAY`` 启停后重新探测的等待秒数，默认 1.5
"""
import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from services.docker_write_service import get_docker_control_service
from services.grafana_service import get_grafana_service
from services.orchestration_service import get_orchestration_service

logger = logging.getLogger(__name__)

MONITORING_SERVICES = ("grafana", "prometheus")


class MonitoringControlError(Exception):
    """监控栈启停失败（编排不可用 / 控制接口异常）"""


class MonitoringNotDeployedError(MonitoringControlError):
    """监控栈容器从未创建，无法经代理启停（需先在部署机拉起一次 compose）"""


def _action_delay() -> float:
    try:
        return float(os.environ.get("PERSEUS_MONITORING_ACTION_DELAY", "1.5"))
    except (TypeError, ValueError):
        return 1.5


class MonitoringService:
    """监控栈状态探测与控制服务"""

    async def get_monitoring(
        self, client: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        探测 Prometheus / Grafana 容器状态。

        Args:
            client: 可选 httpx.AsyncClient（注入编排服务的 Docker 请求，测试用）

        Returns:
            Dict[str, Any]: 含 available / reason / generated_at 与
            grafana / prometheus 两个服务状态节。
        """
        generated_at = datetime.now(timezone.utc).isoformat()
        grafana = self._service_state(running=False)
        prometheus = self._service_state(running=False)

        orch = get_orchestration_service()
        try:
            data = await orch.get_components(client=client)
        except Exception as exc:  # noqa: BLE001 — 任何失败都降级，不 5xx
            logger.warning("获取监控栈状态失败: %s", exc)
            return self._payload(
                available=False,
                reason=str(exc) or exc.__class__.__name__,
                generated_at=generated_at,
            )

        if not data.get("available"):
            return self._payload(
                available=False,
                reason=data.get("reason"),
                generated_at=generated_at,
            )

        comps = {c.get("service"): c for c in data.get("components", [])}
        grafana_c = comps.get("grafana")
        prometheus_c = comps.get("prometheus")

        configured = get_grafana_service().configured
        grafana_running = bool(grafana_c and grafana_c.get("running"))
        prom_running = bool(prometheus_c and prometheus_c.get("running"))

        return self._payload(
            available=True,
            reason=None,
            generated_at=generated_at,
            grafana=self._service_state(
                running=grafana_running,
                configured=configured,
                ready=grafana_running and configured,
                entry=get_grafana_service().entry_path,
                container_id=grafana_c.get("container_id") if grafana_c else None,
            ),
            prometheus=self._service_state(
                running=prom_running,
                container_id=prometheus_c.get("container_id") if prometheus_c else None,
            ),
        )

    async def set_enabled(
        self, enabled: bool, client: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        启/停监控栈（Prometheus + Grafana 一起）。

        容器必须已创建（曾通过 ``docker compose -f docker-compose.monitoring.yml
        up -d`` 部署过一次，之后可被一键部署遗漏而处于停止态）。从未部署过时
        抛 ``MonitoringControlError`` 提示先在部署机拉起一次。

        Args:
            enabled: True=启动，False=停止
            client: 可选 httpx.AsyncClient（测试注入用）

        Returns:
            Dict[str, Any]: 启停后重新探测的完整监控状态。

        Raises:
            MonitoringControlError: 编排不可用 / 监控栈未部署 / 控制接口失败
        """
        orch = get_orchestration_service()
        try:
            data = await orch.get_components(client=client)
        except Exception as exc:  # noqa: BLE001
            raise MonitoringControlError(
                f"编排不可用，无法操作监控栈: {exc}"
            ) from exc

        if not data.get("available"):
            raise MonitoringControlError(
                f"编排不可用，无法操作监控栈: {data.get('reason') or 'docker 不可达'}"
            )

        comps = {c.get("service"): c for c in data.get("components", [])}
        targets = {}
        for service in MONITORING_SERVICES:
            comp = comps.get(service)
            cid = (comp or {}).get("container_id")
            running = bool(comp and comp.get("running"))
            if not cid:
                raise MonitoringNotDeployedError(
                    f"监控栈（{service}）未部署，请先在部署机执行: "
                    "docker compose -f docker-compose.monitoring.yml up -d"
                )
            targets[service] = (cid, running)

        if enabled:
            # 幂等：已在运行的服务跳过
            to_do = [
                cid for cid, running in targets.values() if not running
            ]
        else:
            to_do = [cid for cid, running in targets.values() if running]

        control = get_docker_control_service()
        for cid in to_do:
            try:
                await control.set_running(cid, running=enabled, client=client)
            except Exception as exc:  # noqa: BLE001 — 映射为业务错误，由上层转 5xx
                raise MonitoringControlError(
                    f"操作监控栈容器 {cid[:12]} 失败: {exc}"
                ) from exc

        await asyncio.sleep(_action_delay())
        return await self.get_monitoring(client=client)

    @staticmethod
    def _service_state(
        running: bool,
        configured: bool = False,
        ready: bool = False,
        entry: str = "",
        container_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        return {
            "running": running,
            "configured": configured,
            "ready": ready,
            "entry": entry,
            "container_id": container_id,
        }

    def _payload(
        self,
        available: bool,
        reason: Optional[str],
        generated_at: str,
        grafana: Optional[Dict[str, Any]] = None,
        prometheus: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return {
            "available": available,
            "reason": reason,
            "generated_at": generated_at,
            "grafana": grafana
            or self._service_state(
                running=False, configured=get_grafana_service().configured
            ),
            "prometheus": prometheus or self._service_state(running=False),
        }


_monitoring_service: Optional[MonitoringService] = None


def get_monitoring_service() -> MonitoringService:
    """获取全局监控栈探测与控制服务实例"""
    global _monitoring_service
    if _monitoring_service is None:
        _monitoring_service = MonitoringService()
    return _monitoring_service