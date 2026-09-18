"""
应用管理服务层测试（F-055 覆盖率补齐）

覆盖 AppService 的权限校验、状态聚合、运行时间格式化、日志读取与重启命令推导。
"""
import sys

import pytest

from services.app_service import AppService, get_app_service, _get_restart_command
from core.exception import AuthorizationException, ValidationException


@pytest.fixture
def service():
    return AppService()


def test_check_permission_requires_debug_or_admin(service):
    """非调试且非管理员应拒绝；任一满足则放行"""
    with pytest.raises(AuthorizationException):
        service._check_permission(is_debug=False, is_admin=False)

    service._check_permission(is_debug=True, is_admin=False)
    service._check_permission(is_debug=False, is_admin=True)


def test_format_uptime_variants(service):
    """运行时间格式化覆盖天/时/分/秒与组合"""
    assert service._format_uptime(0) == "0秒"
    assert service._format_uptime(45) == "45秒"
    assert service._format_uptime(60) == "1分钟"
    assert service._format_uptime(3600) == "1小时"
    assert service._format_uptime(86400) == "1天"

    combined = service._format_uptime(90061)  # 1天 1小时 1分钟 1秒
    assert "1天" in combined
    assert "1小时" in combined
    assert "1分钟" in combined
    assert "1秒" in combined


def test_get_status_shape(service):
    """状态接口返回稳定字段与默认请求统计"""
    status = service.get_status()

    assert status["status"] == "running"
    assert status["version"] == "1.0.0"
    assert status["uptime_seconds"] >= 0
    assert status["requests"]["total_requests"] == 0
    assert "git_operations" in status
    assert "process" in status


def test_get_status_accepts_requests_info(service):
    """调用方传入的请求统计应原样透出"""
    status = service.get_status(requests_info={"total_requests": 7})
    assert status["requests"]["total_requests"] == 7


def test_default_info_helpers(service):
    """默认请求/Git 统计字段"""
    assert service._get_default_requests_info()["total_requests"] == 0
    assert service._get_git_operations_info()["queue_size"] == 0


def test_get_log_content_invalid_date(service):
    """非法日期格式抛 ValidationException"""
    with pytest.raises(ValidationException):
        service.get_log_content(date="not-a-date")


def test_get_log_content_missing_file(service):
    """不存在的日期目录返回 exists=False"""
    result = service.get_log_content(date="1970-01-01")
    assert result["exists"] is False
    assert result["content"] == ""
    assert result["lines"] == 0


def test_cleanup_old_logs_invalid_keep_days(service):
    """keep_days < 1 抛 ValidationException（先通过权限）"""
    with pytest.raises(ValidationException):
        service.cleanup_old_logs(keep_days=0, is_debug=True)


def test_cleanup_old_logs_requires_permission(service):
    """无权限时先抛 AuthorizationException"""
    with pytest.raises(AuthorizationException):
        service.cleanup_old_logs(keep_days=30, is_debug=False, is_admin=False)


def test_get_restart_command_python_mode(monkeypatch):
    """Python 脚本模式：解释器 + argv[0]"""
    monkeypatch.setattr(sys, "frozen", False, raising=False)
    monkeypatch.setattr(sys, "executable", "/usr/bin/python3")
    monkeypatch.setattr(sys, "argv", ["app.py"])

    cmd = _get_restart_command()
    assert cmd[0] == "/usr/bin/python3"
    assert "app.py" in cmd


def test_get_restart_command_frozen(monkeypatch):
    """PyInstaller 冻结模式：直接返回可执行文件"""
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", "/opt/perseus/perseus")

    assert _get_restart_command() == ["/opt/perseus/perseus"]


def test_get_app_service_singleton():
    """全局服务实例应复用"""
    assert get_app_service() is get_app_service()
