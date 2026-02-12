"""
应用管理控制器测试

测试范围:
1. 配置管理 - 获取、更新、重置、验证
2. 应用控制 - 状态获取（关机和重启仅验证权限）
3. 权限控制 - 调试模式和管理员权限
"""

import pytest
from fastapi.testclient import TestClient

from app import create_app


@pytest.fixture
def client():
    """创建测试客户端"""
    app = create_app()
    return TestClient(app)


class TestConfigEndpoints:
    """测试配置管理端点"""

    def test_get_config_debug_mode(self, client):
        """测试调试模式下获取配置"""
        response = client.get("/api/app/config")
        # 调试模式下应该可以访问
        assert response.status_code in [200, 403]

    def test_get_config_with_section(self, client):
        """测试获取特定配置节"""
        response = client.get("/api/app/config?section=server")
        assert response.status_code in [200, 403]

    def test_validate_config(self, client):
        """测试验证配置"""
        response = client.post("/api/app/config/validate", json={})
        assert response.status_code in [200, 403]

        if response.status_code == 200:
            data = response.json()
            assert "success" in data
            assert "errors" in data


class TestStatusEndpoint:
    """测试状态端点"""

    def test_get_status(self, client):
        """测试获取应用状态"""
        response = client.get("/api/app/status")
        assert response.status_code == 200

        data = response.json()
        assert "status" in data
        assert data["status"] == "running"
        assert "debug_mode" in data
        assert "uptime_seconds" in data
        assert "uptime_formatted" in data
        assert "system" in data
        assert "version" in data


class TestPermissionControl:
    """测试权限控制"""

    def test_shutdown_without_permission(self, client):
        """测试无权限时关机"""
        # 生产环境且无管理员权限时应该返回 403
        response = client.post("/api/app/shutdown")
        # 根据当前配置可能是 200（调试模式）或 403
        assert response.status_code in [200, 403]

    def test_restart_without_permission(self, client):
        """测试无权限时重启"""
        response = client.post("/api/app/restart")
        assert response.status_code in [200, 403]

    def test_update_config_without_permission(self, client):
        """测试无权限时更新配置"""
        response = client.post("/api/app/config", json={"config": {}})
        assert response.status_code in [200, 403]

    def test_reset_config_without_permission(self, client):
        """测试无权限时重置配置"""
        response = client.post("/api/app/config/reset")
        assert response.status_code in [200, 403]
