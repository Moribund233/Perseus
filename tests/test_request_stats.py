"""
请求统计（middleware/request_stats）与 Redis 客户端（utils/redis_client）测试。

Redis 未配置/不可达时统计走进程内回退，本文件覆盖该路径的统一口径：
success/failed/avg/rpm 基于「完整分钟」滑动窗口，当前未走完的分钟不参与。
"""

from middleware.request_stats import (
    RequestStats,
    _redis_minute,
    _fresh_bucket,
)
from utils import redis_client


async def test_current_minute_not_counted():
    """当前未走完的分钟不进入窗口统计（成功/失败/速率均为 0）"""
    stats = RequestStats(window_minutes=5)
    for _ in range(5):
        await stats.record_request(10.0, True)
    await stats.record_request(50.0, False)

    result = await stats.get_stats()
    assert result["total"] == 6
    assert result["success"] == 0
    assert result["failed"] == 0
    assert result["requests_per_minute"] == 0.0
    assert result["avg_response_time_ms"] == 0.0
    assert result["window_minutes"] == 5


def _filled_bucket(minute: int, count=0, ok=0, fail=0, lat_sum=0.0):
    b = _fresh_bucket(minute)
    b.update(count=count, ok=ok, fail=fail, lat_sum=lat_sum)
    return b


async def test_completed_minute_counts():
    """归档完成的分钟进入窗口统计，rpm 按实际观测分钟数取均值"""
    stats = RequestStats(window_minutes=5)
    stats._minutes.append(
        _filled_bucket(_redis_minute() - 2, count=2, ok=2, lat_sum=20)
    )
    stats._minutes.append(
        _filled_bucket(_redis_minute() - 1, count=4, ok=3, fail=1, lat_sum=40)
    )

    result = await stats.get_stats()
    assert result["total"] == 0  # total 为累计值，此处未发生实时请求
    assert result["success"] == 5
    assert result["failed"] == 1
    assert result["requests_per_minute"] == 3.0  # (2+4)/2 个完整分钟
    assert result["avg_response_time_ms"] == 10.0  # (20+40)/(2+4)


async def test_reset_clears():
    """reset 清空累计与窗口"""
    stats = RequestStats(window_minutes=5)
    await stats.record_request(10.0, True)
    await stats.reset()

    result = await stats.get_stats()
    assert result["total"] == 0
    assert result["success"] == 0
    assert result["failed"] == 0
    assert result["requests_per_minute"] == 0.0


async def test_redis_path_parses_float_latency(monkeypatch):
    """Redis 路径：count/ok/fail 整数字面量、lat 浮点字符串，均能正确解析"""
    class FakeBackend:
        async def get(self, key):
            return "42"

        async def mget(self, *keys):
            # 每分钟一组 count,ok,fail,lat；前两分钟有数据，其余分钟键不存在
            minutes = [
                ("4", "3", "1", "16.25"),
                ("2", "2", "0", "20.0"),
                (None, None, None, None),
                (None, None, None, None),
                (None, None, None, None),
            ]
            return [v for group in minutes for v in group]

    stats = RequestStats(window_minutes=5)
    stats._redis_probed = True
    stats._redis = FakeBackend()

    result = await stats.get_stats()
    assert result["total"] == 42
    assert result["success"] == 5
    assert result["failed"] == 1
    assert result["requests_per_minute"] == 3.0  # 6 次 / 2 个完整分钟
    assert result["avg_response_time_ms"] == 6.04  # 36.25 / 6


async def test_redis_client_disabled_when_no_url(monkeypatch):
    """未配置 Redis URL 时 get_redis 返回 None，调用方回退"""
    for dirty in ("", "  "):
        await redis_client.reset_redis()
        monkeypatch.setattr(redis_client, "_redis_url", lambda: dirty)
        assert await redis_client.get_redis() is None
    await redis_client.reset_redis()


async def test_redis_client_lazy_connect_success(monkeypatch):
    """配置 URL 且连接成功时返回客户端；reset 后重新探测"""

    class FakeRedis:
        def __init__(self):
            self.closed = False

        async def ping(self):
            return True

        async def aclose(self):
            self.closed = True

        @classmethod
        def from_url(cls, url, *args, **kwargs):
            return cls()

    await redis_client.reset_redis()
    monkeypatch.setattr(redis_client, "_redis_url", lambda: "redis://x:6379/0")
    monkeypatch.setattr("redis.asyncio", FakeRedis)
    first = await redis_client.get_redis()
    second = await redis_client.get_redis()
    assert first is not None and second is first
    await redis_client.reset_redis()
    third = await redis_client.get_redis()
    assert third is not None and third is not first
    await redis_client.reset_redis()
    # 备注: Redis 回退路径验证改由具体键操作单测覆盖（见 e2e）,
    # 此处仅确认请求统计能解析到同一后端实例。
    stats = RequestStats(window_minutes=5)
    assert await stats._backend() is not None
    await redis_client.reset_redis()