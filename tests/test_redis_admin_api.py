"""Redis 运维端点（/api/app/redis/*）权限与形状测试"""
import pytest


class TestRedisStatusEndpoint:
    def test_requires_auth(self, test_client):
        assert test_client.get("/api/app/redis/status").status_code == 401

    def test_non_admin_forbidden(self, test_client, auth_headers):
        r = test_client.get("/api/app/redis/status", headers=auth_headers)
        assert r.status_code == 403

    def test_admin_ok(self, test_client, admin_headers):
        r = test_client.get("/api/app/redis/status", headers=admin_headers)
        assert r.status_code == 200, r.text
        body = r.json()
        for key in (
            "configured", "reachable", "latency_ms", "server", "memory",
            "clients", "stats", "workers", "pubsub", "keyspace", "degradation",
            "generated_at",
        ):
            assert key in body, key
        # 测试环境未配置 Redis → 优雅降级
        assert body["reachable"] is False
        assert body["workers"]["items"] == []


class TestRedisConfigEndpoint:
    def test_requires_auth(self, test_client):
        assert test_client.get("/api/app/redis/config").status_code == 401

    def test_non_admin_forbidden(self, test_client, auth_headers):
        r = test_client.get("/api/app/redis/config", headers=auth_headers)
        assert r.status_code == 403

    def test_admin_ok(self, test_client, admin_headers):
        r = test_client.get("/api/app/redis/config", headers=admin_headers)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["editable"] is False
        assert "namespace" in body["settings"]
        assert "url" in body["settings"]
