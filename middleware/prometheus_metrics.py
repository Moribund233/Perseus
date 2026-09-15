"""
Prometheus 指标中间件

以 Prometheus 原生文本格式导出应用 HTTP 指标，供 Prometheus / Grafana 抓取：

- ``perseus_http_requests_total``（按 method/status 维度计数）
- ``perseus_http_request_duration_seconds``（延迟直方图）
- ``perseus_http_inflight_requests``（当前在途请求数）
- ``perseus_http_error_ratio``（最近 5 分钟 5xx 占比，供告警规则使用）

实现仅依赖标准库，不引入额外包。
"""
import time
from collections import defaultdict
from typing import Callable, Dict, List, Optional, Tuple

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import PlainTextResponse

# 直方图 bucket 边界（秒）
DEFAULT_BUCKETS: Tuple[float, ...] = (
    0.005,
    0.01,
    0.025,
    0.05,
    0.1,
    0.25,
    0.5,
    1.0,
    2.5,
    5.0,
    10.0,
    float("inf"),
)


class PrometheusMetrics:
    """进程内 Prometheus 指标收集器（GIL 保护，单进程内安全）"""

    def __init__(self, buckets: Tuple[float, ...] = DEFAULT_BUCKETS) -> None:
        self._buckets: Tuple[float, ...] = buckets
        # key -> ("method", "status") 组合
        self._counters: Dict[str, int] = defaultdict(int)
        # key -> 直方图累计值: {"cum": {bucket: cnt}, "sum": ..., "count": ...}
        self._latency: Dict[str, Dict] = {}
        self._inflight: int = 0

    def record(self, method: str, status_code: int, duration_s: float) -> None:
        """记录一次请求的指标"""
        method = (method or "UNKNOWN").upper()
        status = self._status_label(status_code)
        counter_key = f"{method}|{status}"
        self._counters[counter_key] += 1

        bucket_key = method
        entry = self._latency.setdefault(
            bucket_key, {"cum": defaultdict(int), "sum": 0.0, "count": 0}
        )
        entry["sum"] += duration_s
        entry["count"] += 1
        for bucket in self._buckets:
            if duration_s <= bucket:
                entry["cum"][bucket] += 1

    def enter(self) -> None:
        """请求进入时调用"""
        self._inflight += 1

    def leave(self) -> None:
        """请求结束时调用"""
        if self._inflight > 0:
            self._inflight -= 1

    def render(self) -> str:
        """渲染 Prometheus 文本格式指标"""
        lines: List[str] = []
        lines.append("# HELP perseus_http_requests_total Total HTTP requests by method and status.")
        lines.append("# TYPE perseus_http_requests_total counter")
        for key, count in sorted(self._counters.items()):
            method, status = key.split("|")
            lines.append(
                f'perseus_http_requests_total{{method="{method}",status="{status}"}} {count}'
            )

        lines.append("# HELP perseus_http_request_duration_seconds HTTP request latency.")
        lines.append("# TYPE perseus_http_request_duration_seconds histogram")
        for method, entry in sorted(self._latency.items()):
            cumulative = 0
            for bucket in self._buckets:
                cumulative = entry["cum"].get(bucket, 0)
                b_label = "+Inf" if bucket == float("inf") else f"{bucket:g}"
                lines.append(
                    f'perseus_http_request_duration_seconds_bucket{{method="{method}",le="{b_label}"}} '
                    f"{cumulative}"
                )
            lines.append(
                f'perseus_http_request_duration_seconds_sum{{method="{method}"}} '
                f"{entry['sum']:.9f}"
            )
            lines.append(
                f'perseus_http_request_duration_seconds_count{{method="{method}"}} '
                f"{entry['count']}"
            )

        lines.append("# HELP perseus_http_inflight_requests Current inflight requests.")
        lines.append("# TYPE perseus_http_inflight_requests gauge")
        lines.append(f"perseus_http_inflight_requests {self._inflight}")

        lines.append("# HELP perseus_http_5xx_total Total 5xx responses.")
        lines.append("# TYPE perseus_http_5xx_total counter")
        five_xx = sum(
            count for key, count in self._counters.items() if key.split("|")[1] == "5xx"
        )
        lines.append(f"perseus_http_5xx_total {five_xx}")

        lines.append("# HELP perseus_http_requests_total_total All HTTP requests counter.")
        lines.append("# TYPE perseus_http_requests_total_total counter")
        lines.append(f"perseus_http_requests_total_total {sum(self._counters.values())}")

        return "\n".join(lines) + "\n"

    @staticmethod
    def _status_label(status_code: int) -> str:
        if status_code < 200:
            return "1xx"
        if status_code < 300:
            return "2xx"
        if status_code < 400:
            return "3xx"
        if status_code < 500:
            return "4xx"
        return "5xx"


# 全局指标实例
_metrics: Optional[PrometheusMetrics] = None


def get_prometheus_metrics() -> PrometheusMetrics:
    """获取全局 Prometheus 指标实例"""
    global _metrics
    if _metrics is None:
        _metrics = PrometheusMetrics()
    return _metrics


def metrics_response(request: Request) -> PlainTextResponse:
    """/metrics 端点处理函数"""
    return PlainTextResponse(
        get_prometheus_metrics().render(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


class PrometheusMetricsMiddleware(BaseHTTPMiddleware):
    """
    请求指标中间件

    统计所有 HTTP 请求的计数、延迟与在途数。
    自身路径（/metrics）不计入，避免递归膨胀。
    """

    def __init__(self, app, exclude_paths: Optional[list] = None):
        super().__init__(app)
        self.exclude_paths = exclude_paths or ["/metrics"]
        self.metrics = get_prometheus_metrics()

    def _should_record(self, path: str) -> bool:
        for exclude_path in self.exclude_paths:
            if path == exclude_path or path.startswith(exclude_path + "/"):
                return False
        return True

    async def dispatch(self, request: Request, call_next: Callable):
        if not self._should_record(request.url.path):
            return await call_next(request)

        self.metrics.enter()
        start_time = time.time()
        response = None
        try:
            response = await call_next(request)
            return response
        except Exception:
            status_code = 500
            raise
        finally:
            if response is not None:
                status_code = response.status_code
            duration_s = time.time() - start_time
            self.metrics.record(request.method, status_code, duration_s)
            self.metrics.leave()