"""
数据库生命周期管理测试（F-055 覆盖率补齐）

覆盖 DatabaseResetManager 的表名校验、SQLite 文件删除与重置编排流程。
"""
import asyncio
import os
import tempfile

import pytest

from services.database_manager import DatabaseResetManager


@pytest.fixture
def manager():
    return DatabaseResetManager()


def test_is_valid_table_name(manager):
    """表名白名单校验"""
    assert manager._is_valid_table_name("users") is True
    assert manager._is_valid_table_name("table_1") is True
    assert manager._is_valid_table_name("users; DROP") is False
    assert manager._is_valid_table_name("a-b") is False
    assert manager._is_valid_table_name("") is False
    assert manager._is_valid_table_name(None) is False


def test_drop_sqlite_data_removes_file(manager):
    """SQLite 重置应删除数据库文件"""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    assert os.path.exists(path)

    manager.db_type = "sqlite"
    manager.db_url = f"sqlite:///{path}"
    manager._drop_sqlite_data()

    assert not os.path.exists(path)


def test_drop_data_unsupported_type(manager):
    """未知数据库类型抛 ValueError"""
    manager.db_type = "mysql"
    with pytest.raises(ValueError):
        asyncio.run(manager._drop_data())


@pytest.mark.asyncio
async def test_reset_database_orchestration(manager, monkeypatch):
    """重置流程按顺序调用四个步骤并汇总结果"""
    calls = {}

    async def fake_close():
        calls["close"] = True

    async def fake_drop():
        calls["drop"] = True

    def fake_create():
        calls["create"] = True

    def fake_bootstrap():
        calls["bootstrap"] = True
        return True

    monkeypatch.setattr(manager, "_close_connections", fake_close)
    monkeypatch.setattr(manager, "_drop_data", fake_drop)
    monkeypatch.setattr(manager, "_create_tables", fake_create)
    monkeypatch.setattr(manager, "_bootstrap_admin", fake_bootstrap)

    result = await manager.reset_database()

    assert result["success"] is True
    assert result["admin_bootstrapped"] is True
    assert result["elapsed_seconds"] >= 0
    assert calls == {"close": True, "drop": True, "create": True, "bootstrap": True}


@pytest.mark.asyncio
async def test_reset_database_propagates_error(manager, monkeypatch):
    """步骤异常应向上抛出"""
    async def fake_close():
        pass

    async def fake_drop():
        raise RuntimeError("boom")

    monkeypatch.setattr(manager, "_close_connections", fake_close)
    monkeypatch.setattr(manager, "_drop_data", fake_drop)

    with pytest.raises(RuntimeError):
        await manager.reset_database()
