"""
Prometheus 指标中间件测试（F-053 监控集成）

覆盖：
- PrometheusMetrics 记录/渲染（计数、直方图、在途、5xx 汇总）
- 状态分类（1xx~5xx）
- /metrics 端点导出（经 app 全链路）
- exclude_paths 排除逻辑
"""
import pytest
import time

from middleware.prometheus_metrics import (
    PrometheusMetrics,
    PrometheusMetricsMiddleware,
    get_prometheus_metrics,
    metrics_response,
)


def _reset_metrics_instance():
    import middleware.prometheus_metrics as pm
    pm._metrics = None
    return get_prometheus_metrics()


class TestPrometheusMetrics:
    @pytest.fixture(autouse=True)
    def _fresh(self):
        _reset_metrics_instance()
        yield
        _reset_metrics_instance()

    def test_record_and_counts(self):
        m = get_prometheus_metrics()
        m.record("get", 200, 0.05)
        m.record("GET", 200, 0.01)
        m.record("GET", 404, 0.02)
        m.record("GET", 500, 0.03)
        text = m.render()
        assert 'perseus_http_requests_total{method="GET",status="2xx"} 2' in text
        assert 'perseus_http_requests_total{method="GET",status="4xx"} 1' in text
        assert 'perseus_http_requests_total{method="GET",status="5xx"} 1' in text
        assert "perseus_http_5xx_total 1" in text
        assert "perseus_http_requests_total_total 4" in text

    def test_latency_histogram_monotonic(self):
        m = get_prometheus_metrics()
        m.record("GET", 200, 0.003)
        m.record("GET", 200, 0.02)
        m.record("GET", 200, 1.5)
        text = m.render()
        counts = []
        for bucket in ("0.005", "0.01", "0.025", "0.05", "0.1",
                       "0.25", "0.5", "1", "2.5", "5", "10", "+Inf"):
            marker = f'perseus_http_request_duration_seconds_bucket{{method="GET",le="{bucket}"}} '
            value = int([l.split()[-1] for l in text.splitlines()
                         if l.startswith(marker)][0])
            counts.append(value)
        assert counts == sorted(counts)
        assert counts[-1] == 3
        assert '_sum' in text and '_count' in text
        assert 'perseus_http_request_duration_seconds_count{method="GET"} 3' in text

    def test_inflight_gauge(self):
        m = get_prometheus_metrics()
        m.enter()
        m.enter()
        assert "perseus_http_inflight_requests 2" in m.render()
        m.leave()
        assert "perseus_http_inflight_requests 1" in m.render()
        m.leave()
        m.leave()  # 不出现负值
        assert "perseus_http_inflight_requests 0" in m.render()

    def test_status_label_classification(self):
        assert PrometheusMetrics._status_label(99) == "1xx"
        assert PrometheusMetrics._status_label(200) == "2xx"
        assert PrometheusMetrics._status_label(304) == "3xx"
        assert PrometheusMetrics._status_label(422) == "4xx"
        assert PrometheusMetrics._status_label(503) == "5xx"

    def test_render_includes_help_type_headers(self):
        m = get_prometheus_metrics()
        text = m.render()
        assert "# TYPE perseus_http_requests_total counter" in text
        assert "# TYPE perseus_http_request_duration_seconds histogram" in text
        assert "# TYPE perseus_http_inflight_requests gauge" in text


class TestMetricsEndpoint:
    @pytest.fixture(autouse=True)
    def _fresh(self):
        _reset_metrics_instance()
        yield
        _reset_metrics_instance()

    def test_metrics_endpoint_via_app(self, test_client):
        test_client.get("/health")
        test_client.get("/health")
        r = test_client.get("/metrics")
        assert r.status_code == 200
        assert "text/plain" in r.headers.get("content-type", "")
        text = r.text
        assert 'perseus_http_requests_total{method="GET",status="200"} ' not in text
        # 端点应自排除，避免 /metrics 递归计入自身
        assert 'method="GET",status="2xx"' in text
        assert "perseus_http_requests_total_total" in text

    def test_metrics_not_self_recorded(self, test_client):
        r = test_client.get("/metrics")
        assert r.status_code == 200
        # 仅请求 /metrics 时自身不应出现在计数中
        assert 'method="GET",status="2xx"' not in r.text

    def test_metrics_response_direct(self):
        r = metrics_response(None)
        assert r.status_code == 200
        assert "perseus_http_requests_total" in r.body.decode()


class TestMiddlewareUnit:
    @pytest.fixture(autouse=True)
    def _fresh(self):
        _reset_metrics_instance()
        yield
        _reset_metrics_instance()

    def test_should_record_excludes(self):
        mw = PrometheusMetricsMiddleware.__new__(PrometheusMetricsMiddleware)
        mw.exclude_paths = ["/metrics", "/health"]
        assert not mw._should_record("/metrics")
        assert not mw._should_record("/health")
        assert not mw._should_record("/metrics/extra")
        assert mw._should_record("/api/v1/users")

    def test_dispatch_records(self):
        from starlette.requests import Request
        from starlette.responses import PlainTextResponse
        mw = PrometheusMetricsMiddleware.__new__(PrometheusMetricsMiddleware)
        mw.exclude_paths = ["/metrics"]
        mw.metrics = get_prometheus_metrics()

        async def call_next(request):
            return PlainTextResponse("ok")

        import asyncio
        req = Request({"type": "http", "method": "GET",
                       "path": "/api/v1/test", "headers": []})
        res = asyncio.run(mw.dispatch(req, call_next))
        assert res.status_code == 200
        assert mw.metrics._inflight == 0
        text = mw.metrics.render()
        assert 'perseus_http_requests_total{method="GET",status="2xx"} 1' in text

    def test_dispatch_excluded_path_not_recorded(self):
        from starlette.requests import Request
        from starlette.responses import PlainTextResponse
        mw = PrometheusMetricsMiddleware.__new__(PrometheusMetricsMiddleware)
        mw.exclude_paths = ["/metrics"]
        mw.metrics = get_prometheus_metrics()

        async def call_next(request):
            return PlainTextResponse("ok")

        import asyncio
        req = Request({"type": "http", "method": "GET",
                       "path": "/metrics", "headers": []})
        asyncio.run(mw.dispatch(req, call_next))
        assert "perseus_http_requests_total_total 0" in mw.metrics.render()