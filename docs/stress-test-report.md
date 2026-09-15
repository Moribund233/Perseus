# Perseus 服务端压力测试报告（F-052）

- 测试时间: 2026-09-15
- 测试环境: Docker dev compose `perseus-backend-dev` 容器内直连 `http://127.0.0.1:8000`（绕过宿主机网络转发）
- 测试工具: `tests/stress_test.py`（httpx 异步并发）
- 基线: 单发 `GET /health` ≈ 2ms，`GET /api/app/status` ≈ 4ms

## 测试模式与参数

| 模式 | 并发数 | 每端点请求数 | 端点 |
|------|-------|-------------|------|
| normal | 50 | 500 | `/`、`/health`、`/api/app/status` |
| extreme | 200 | 2000 | `/`、`/health` |

## Normal 模式（并发 50 × 500）

| 端点 | 成功率 | 平均延迟 | P50 | P95 | P99 | 墙钟耗时 | 真实 QPS |
|------|-------|---------|-----|-----|-----|---------|---------|
| `/` | 100% | 102.26 ms | 99.28 | 161.48 | 172.62 | 1.81 s | 275.7 |
| `/health` | 100% | 92.70 ms | 86.46 | 153.37 | 162.75 | 1.65 s | 303.2 |
| `/api/app/status` | 100% | 145.00 ms | 135.39 | 282.39 | 287.03 | 2.34 s | 214.1 |

## Extreme 模式（并发 200 × 2000）

| 端点 | 成功率 | 平均延迟 | P50 | P95 | P99 | 墙钟耗时 | 真实 QPS |
|------|-------|---------|-----|-----|-----|---------|---------|
| `/` | 100% | 903.47 ms | 499.25 | 2568.74 | 3873.10 | 16.14 s | 123.9 |
| `/health` | 100% | 466.79 ms | 241.36 | 2372.79 | 4003.81 | 8.79 s | 227.7 |

## 压测发现并修复的问题

- **`/api/app/status` 高延迟（平均 5.4s、QPS 0.19）**：根因是 `services/app_service.py:243` 的
  `process.cpu_percent(interval=0.1)` 强制同步阻塞 100ms。已改为 `interval=None`
  （返回自上次调用以来的增量 CPU 使用，不阻塞事件循环）。修复后该端点单发延迟
  `~106ms → 4ms`，normal 模式墙钟 QPS 从 0.19 提升到 214。

## 结论

- 常规并发（50）下所有端点 100% 成功，QPS 200+，P99 均低于 300ms，性能满足日常使用。
- 极限并发（200）下仍有极高成功率，P95~2.6s 处于可接受的降级区间（未出现 5xx）。
- `tests/stress_test.py` 新增**墙钟耗时**与**真实 QPS** 统计，修复了原脚本以请求耗时累加
  代替真实吞吐量的偏差（并发下原 QPS 严重低估）。
- 后续如需更高并发压测（如 1000+），建议改用 locust/wrk 以规避 GIL 与单机连接数限制。

## 复现方式

```bash
cd ~/perseus
docker compose -f docker-compose.dev.yml exec -T app \
  sh -c "cd /app && python3 tests/stress_test.py --mode normal --url http://127.0.0.1:8000"
docker compose -f docker-compose.dev.yml exec -T app \
  sh -c "cd /app && python3 tests/stress_test.py --mode extreme --url http://127.0.0.1:8000"
```