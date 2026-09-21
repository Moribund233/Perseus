"""
概览时序接口测试

覆盖：
- 延迟直方图桶标签与分位数估算（middleware/request_stats）
- record_request 写入 2xx/3xx/4xx/5xx 分布与直方图，get_history 读取
- 时序聚合服务 get_timeseries 的降采样与结构（Redis 不可用走内存回退）
- 端点门控（匿名 401 / 非管理员 403 / 管理员 200）与参数校验
"""
import pytest

from types import SimpleNamespace

from middleware.request_stats import (
    RequestStats,
    _bucket_label,
    _redis_minute,
    percentile_from_hist,
)


# ---------------- 直方图工具 ----------------

def test_bucket_label_boundaries():
    assert _bucket_label(1) == "10"
    assert _bucket_label(10) == "10"
    assert _bucket_label(10.1) == "25"
    assert _bucket_label(6000) == "inf"


def test_percentile_from_hist():
    assert percentile_from_hist({}) == 0.0
    # 95 分位落在 100ms 桶（10 个样本中第 10 个 >= 9.5）
    hist = {"10": 5, "50": 3, "100": 2}
    assert percentile_from_hist(hist, 0.95) == 100.0
    # inf 桶回退到上一有限上界（5000ms 为最大有限桶）
    assert percentile_from_hist({"10": 1, "inf": 9}, 0.95) == 5000.0


# ---------------- 请求桶写入与读取（内存回退） ----------------

async def test_record_request_tracks_status_and_hist():
    stats = RequestStats(window_minutes=5)
    await stats.record_request(8.0, True, 200)
    await stats.record_request(40.0, True, 301)
    await stats.record_request(120.0, False, 500)

    cur = stats._current
    assert cur["count"] == 3
    assert cur["ok"] == 2
    assert cur["fail"] == 1
    assert cur["s2xx"] == 1
    assert cur["s3xx"] == 1
    assert cur["s5xx"] == 1
    assert cur["hist"] == {"10": 1, "50": 1, "200": 1}


async def test_get_history_memory_excludes_current_minute():
    stats = RequestStats(window_minutes=5)
    now = _redis_minute()
    # 直接注入已归档分钟桶（当前未走完分钟不进入历史）
    from middleware.request_stats import _fresh_bucket

    old = _fresh_bucket(now - 1)
    old.update(count=4, ok=3, fail=1, lat_sum=40.0, s2xx=3, s4xx=1)
    old["hist"] = {"10": 2, "50": 2}
    stats._minutes.append(old)

    history = await stats.get_history(5)
    assert (now - 1) in history
    assert now not in history
    assert history[now - 1]["count"] == 4
    assert history[now - 1]["s4xx"] == 1


# ---------------- Redis 路径解析 ----------------

class _FakePipe:
    def __init__(self, mget_results, hgetall_results):
        self._mget = list(mget_results)
        self._hgetall = list(hgetall_results)
        self._ops = []

    def mget(self, *keys):
        self._ops.append(("mget", keys))

    def hgetall(self, key):
        self._ops.append(("hgetall", key))

    async def execute(self):
        out = []
        mi = hi = 0
        for op, _ in self._ops:
            if op == "mget":
                out.append(self._mget[mi])
                mi += 1
            else:
                out.append(self._hgetall[hi])
                hi += 1
        return out


class _FakeBackend:
    def __init__(self, mget_results, hgetall_results):
        self._mget = mget_results
        self._hgetall = hgetall_results

    def pipeline(self):
        return _FakePipe(self._mget, self._hgetall)


async def test_get_history_redis_parses_fields():
    # 4 个完整分钟：第 1 个有数据，其余为空
    mget_results = [
        ["4", "3", "1", "16.25", "3", "0", "0", "1"],
        [None, None, None, None, None, None, None, None],
        [None, None, None, None, None, None, None, None],
        [None, None, None, None, None, None, None, None],
    ]
    hgetall_results = [{"10": "3", "100": "1"}, {}, {}, {}]

    stats = RequestStats(window_minutes=5)
    stats._redis_probed = True
    stats._redis = _FakeBackend(mget_results, hgetall_results)

    history = await stats.get_history(5)
    assert len(history) == 4
    first = history[min(history)]
    assert first["count"] == 4
    assert first["ok"] == 3
    assert first["fail"] == 1
    assert first["lat_sum"] == 16.25
    assert first["s5xx"] == 1
    assert first["hist"] == {"10": 3, "100": 1}


# ---------------- 聚合服务 ----------------

async def test_get_timeseries_shape_and_downsample(monkeypatch):
    from services import metrics_service

    now = metrics_service._now_minute()

    class FakeReq:
        async def get_history(self, minutes):
            return {
                m: {
                    "minute": m,
                    "count": 6,
                    "ok": 5,
                    "fail": 1,
                    "lat_sum": 60.0,
                    "s2xx": 5,
                    "s3xx": 0,
                    "s4xx": 1,
                    "s5xx": 0,
                    "hist": {"10": 6},
                }
                for m in range(now - minutes, now)
            }

    class FakeProc:
        async def get_samples(self, minutes):
            return {m: {"mem_mb": 100.0, "cpu_pct": 2.0} for m in range(now - minutes, now)}

    async def fake_redis():
        return None

    monkeypatch.setattr(metrics_service, "get_request_stats", lambda: FakeReq())
    monkeypatch.setattr(metrics_service, "get_process_metrics", lambda: FakeProc())
    monkeypatch.setattr(metrics_service, "get_redis", fake_redis)

    out = await metrics_service.get_timeseries("1h")
    assert out["range"] == "1h"
    assert out["step"] == 60
    assert out["source"] == "memory"
    assert len(out["points"]) == 60

    point = out["points"][0]
    assert point["rpm"] == 6.0
    assert point["err_rate"] == pytest.approx(16.67, abs=0.01)
    assert point["avg_ms"] == 10.0
    assert point["p95_ms"] == 10.0
    assert point["mem_mb"] == 100.0
    assert point["cpu_pct"] == 2.0
    assert point["s2xx"] == 5


# ---------------- 进程采样器 ----------------

def test_process_sampler_reuses_psutil_instance(monkeypatch):
    """psutil.Process 必须复用实例，否则 cpu_percent(interval=None) 恒为 0"""
    import psutil

    from services import process_metrics

    created = []

    class FakeProc:
        def __init__(self, pid):
            created.append(pid)

        def cpu_percent(self, interval=None):
            return 12.5

        def memory_info(self):
            return SimpleNamespace(rss=128 * 1024 * 1024)

    monkeypatch.setattr(psutil, "Process", FakeProc)

    pm = process_metrics.ProcessMetrics()
    first = pm._read_process()
    second = pm._read_process()

    assert first["cpu_pct"] == 12.5
    assert first["mem_mb"] == 128.0
    assert second["cpu_pct"] == 12.5
    assert len(created) == 1  # 仅创建一次，保证 CPU 基线连续


# ---------------- 端点门控 ----------------

class TestMetricsTimeseriesEndpoint:
    def test_requires_auth(self, test_client):
        assert test_client.get("/api/app/metrics/timeseries").status_code == 401

    def test_requires_admin(self, test_client, auth_headers):
        r = test_client.get("/api/app/metrics/timeseries", headers=auth_headers)
        assert r.status_code == 403

    def test_admin_ok(self, test_client, admin_headers):
        r = test_client.get(
            "/api/app/metrics/timeseries",
            params={"range": "1h"},
            headers=admin_headers,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["range"] == "1h"
        assert body["step"] > 0
        assert body["source"] in ("redis", "memory")
        assert isinstance(body["points"], list)
        if body["points"]:
            assert set(body["points"][0]) >= {
                "t", "rpm", "err_rate", "avg_ms", "p95_ms",
                "mem_mb", "cpu_pct", "s2xx", "s3xx", "s4xx", "s5xx",
            }

    def test_invalid_range_rejected(self, test_client, admin_headers):
        r = test_client.get(
            "/api/app/metrics/timeseries",
            params={"range": "7d"},
            headers=admin_headers,
        )
        assert r.status_code == 422
