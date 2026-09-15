"""程序化 Alembic 迁移运行器

将数据库 schema 演进统一收敛到 Alembic 迁移，替代启动时的 ``Base.metadata.create_all``：

- 初始化任务 / 开发便捷启动：调用 :func:`run_migrations` 将数据库升级到最新版本
- 运行容器启动：调用 :func:`is_schema_ready` 做只读就绪校验，不执行任何 DDL
- 兼容历史数据库（由 create_all 时代创建、缺少 ``alembic_version`` 表）：
  存在业务表则自动 ``stamp head`` 认领，否则 ``upgrade head`` 全新建表

所有入口均幂等、可重复执行，且以事务方式逐版本推进。
"""
import logging
from pathlib import Path
from typing import Optional

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text

from core.config import get_config
from models import Base

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ALEMBIC_DIR = PROJECT_ROOT / "alembic"
ALEMBIC_INI = PROJECT_ROOT / "alembic.ini"


def _to_sync_db_url(url: str) -> str:
    """将异步/带驱动 URL 转为 Alembic 可用的同步 SQLAlchemy URL。"""
    if url.startswith("postgresql+asyncpg://"):
        return url.replace("postgresql+asyncpg://", "postgresql://", 1)
    if url.startswith("sqlite+aiosqlite://"):
        path = url.removeprefix("sqlite+aiosqlite://")
        if path.startswith("/") and not path.startswith("/."):
            return f"sqlite:///{path}"  # 绝对路径需要 4 个斜杠
        return f"sqlite:///{path.lstrip('/')}"
    return url


def _resolve_db_url(db_url: Optional[str] = None) -> str:
    """解析最终同步 URL：显式传入优先，否则读配置。"""
    if db_url:
        return _to_sync_db_url(db_url)
    return _to_sync_db_url(get_config().database.url)


def _make_alembic_config(db_url: Optional[str] = None) -> Config:
    """构建 Alembic Config（script_location 定位到仓库内的 alembic 目录，不受 CWD 影响）。"""
    cfg = Config(str(ALEMBIC_INI))
    cfg.set_main_option("script_location", str(ALEMBIC_DIR))
    cfg.set_main_option("sqlalchemy.url", _resolve_db_url(db_url))
    # 程序化调用时跳过 alembic/env.py 的日志重配置，保留应用现有的日志处理器
    cfg.attributes["perseus_skip_logging_config"] = True
    return cfg


def get_head_revision(db_url: Optional[str] = None) -> Optional[str]:
    """获取迁移脚本树的 head revision（不连接数据库）。"""
    cfg = _make_alembic_config(db_url)
    return ScriptDirectory.from_config(cfg).get_current_head()


def get_applied_revision(db_url: Optional[str] = None) -> Optional[str]:
    """读取数据库中已应用的迁移版本；未初始化（无 alembic_version 表）返回 None。"""
    engine = create_engine(_resolve_db_url(db_url))
    try:
        inspector = inspect(engine)
        if "alembic_version" not in inspector.get_table_names():
            return None
        with engine.connect() as conn:
            row = conn.execute(text("SELECT version_num FROM alembic_version")).fetchone()
        return row[0] if row else None
    finally:
        engine.dispose()


def get_schema_state(db_url: Optional[str] = None) -> tuple:
    """返回 ``(applied, head, has_business_tables)``，用于就绪判断与日志。"""
    applied = get_applied_revision(db_url)
    head = get_head_revision(db_url)

    engine = create_engine(_resolve_db_url(db_url))
    try:
        db_tables = set(inspect(engine).get_table_names())
        has_business = bool(set(Base.metadata.tables) & db_tables)
    finally:
        engine.dispose()

    return applied, head, has_business


def is_schema_ready(db_url: Optional[str] = None) -> tuple:
    """只读就绪校验：schema 已迁移到位。

    Returns:
        tuple: ``(ready: bool, state: dict)``，state 含 applied/head
    """
    applied, head, _ = get_schema_state(db_url)
    ready = applied is not None and applied == head
    return ready, {"applied": applied, "head": head}


def run_migrations(db_url: Optional[str] = None) -> dict:
    """将数据库 schema 升级到最新（幂等、可重复执行）。

    行为：
    - 已有迁移跟踪（alembic_version 存在）→ ``alembic upgrade head`` 增量升级
    - 已有 create_all 时代业务表但无迁移跟踪 → ``alembic stamp head`` 认领现有结构
    - 全新数据库 → ``alembic upgrade head`` 全新建表

    Returns:
        dict: 含 ``success`` / ``applied`` / ``head``
    """
    applied_before, head, has_business = get_schema_state(db_url)
    cfg = _make_alembic_config(db_url)

    try:
        if applied_before is not None:
            command.upgrade(cfg, "head")
        elif has_business:
            logger.warning(
                "检测到已存在业务表但缺少 alembic_version，"
                "将执行 alembic stamp head 认领现有 schema"
            )
            command.stamp(cfg, "head")
        else:
            command.upgrade(cfg, "head")
    except Exception:
        logger.exception("数据库迁移失败")
        return {"success": False, "applied": applied_before, "head": head}

    applied = get_applied_revision(db_url)
    logger.info(f"数据库迁移完成: applied={applied} head={head}")
    return {"success": True, "applied": applied, "head": head}