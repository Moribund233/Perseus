"""
数据库初始化工具模块

提供数据库迁移、首次运行管理员引导等功能。
schema 演进统一走 Alembic 迁移（utils/db_migrate），不再使用 create_all。
管理员凭据通过环境变量注入，不在代码中硬编码。
"""
import os
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker, Session

from models import Base
from utils.logging import get_named_logger

logger = get_named_logger("database")

# 管理员环境变量名称
ENV_ADMIN_USERNAME = "PERSEUS_ADMIN_USERNAME"
ENV_ADMIN_PASSWORD = "PERSEUS_ADMIN_PASSWORD"
ENV_ADMIN_EMAIL = "PERSEUS_ADMIN_EMAIL"


def _to_sync_db_url(url: str) -> str:
    """将异步驱动 URL 转为同步 URL（用于迁移和命令行工具）"""
    sync_url = url.replace("+aiosqlite", "", 1).replace("+asyncpg", "", 1)
    # SQLAlchemy 2.1 起 postgresql:// 默认驱动为 psycopg3；本项目使用 psycopg2
    if sync_url.startswith("postgresql://"):
        return sync_url.replace("postgresql://", "postgresql+psycopg2://", 1)
    if sync_url.startswith("postgres://"):
        return sync_url.replace("postgres://", "postgresql+psycopg2://", 1)
    return sync_url


class DatabaseInitializer:
    """
    数据库初始化器

    负责数据库 schema 迁移（Alembic），以及首次运行时自动创建管理员用户。
    """

    def __init__(self, db_url: Optional[str] = None):
        self.db_url = db_url
        self._engine = None
        self._SessionLocal: sessionmaker | None = None

    def _get_sync_engine(self):
        """获取同步引擎（bootstrap 等操作需要同步连接）"""
        if self._engine is None:
            if self.db_url:
                sync_url = _to_sync_db_url(self.db_url)
            else:
                from core.config import get_config
                config = get_config()
                sync_url = _to_sync_db_url(config.database.url)
            connect_args = {}
            if sync_url.startswith("sqlite://"):
                connect_args["check_same_thread"] = False
            self._engine = create_engine(sync_url, connect_args=connect_args)
        return self._engine

    def run_migrations(self, db_url: Optional[str] = None) -> dict:
        """
        将数据库 schema 升级到最新（Alembic，幂等）。

        Returns:
            dict: 含 ``success`` / ``applied`` / ``head``
        """
        from utils.db_migrate import run_migrations
        return run_migrations(db_url or self.db_url)

    def create_tables(self) -> bool:
        """
        创建数据库表结构（兼容入口）。

        等价于执行 Alembic 迁移（含历史库 stamp 认领），
        返回是否成功。

        Returns:
            bool: 创建是否成功
        """
        return self.run_migrations()["success"]

    def is_schema_ready(self, db_url: Optional[str] = None) -> tuple:
        """
        只读就绪校验：schema 是否已迁移到位（不执行 DDL）。

        Returns:
            tuple: ``(ready: bool, state: dict)``
        """
        from utils.db_migrate import is_schema_ready
        return is_schema_ready(db_url or self.db_url)

    def autobootstrap_admin(self) -> bool:
        """
        首次运行自动创建管理员用户。

        仅在没有任何管理员用户（is_admin=True）时执行。
        凭据从环境变量读取，不硬编码在代码中。

        环境变量:
            PERSEUS_ADMIN_USERNAME: 管理员用户名（默认: admin）
            PERSEUS_ADMIN_PASSWORD: 管理员密码（必需）
            PERSEUS_ADMIN_EMAIL:    管理员邮箱（默认: admin@example.com）

        Returns:
            bool: 操作是否成功（无管理员需要创建时也返回 True）
        """
        from models.user import User
        from utils.password_utils import get_password_hash

        session = self._get_session()
        try:
            admin_exists = session.query(User).filter(User.is_admin == True).first()
            if admin_exists:
                return True

            username = os.environ.get(ENV_ADMIN_USERNAME, "admin")
            password = os.environ.get(ENV_ADMIN_PASSWORD)
            email = os.environ.get(ENV_ADMIN_EMAIL, "admin@example.com")

            if not password:
                logger.warning(
                    f"{ENV_ADMIN_PASSWORD} 未设置，跳过管理员自动创建。"
                    f"请通过注册接口或设置 {ENV_ADMIN_PASSWORD} 环境变量创建管理员。"
                )
                return True

            admin = User(
                username=username,
                email=email,
                password=get_password_hash(password),
                full_name="System Administrator",
                is_active=True,
                is_admin=True,
            )
            session.add(admin)
            try:
                session.commit()
            except IntegrityError:
                # 多进程/多 worker 并发启动时的竞态：唯一约束冲突
                # 说明管理员已由其他进程创建，视为成功
                session.rollback()
                logger.info(f"管理员用户已由其他进程创建: {username}")
                return True

            logger.info(f"管理员用户已自动创建: {username} <{email}>")
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"管理员自动创建失败: {e}")
            return False
        finally:
            session.close()

    def reset_admin_password(self, new_password: str) -> bool:
        """
        重设管理员密码（运维用，由 scripts/reset_admin.py 调用）。

        管理员按 ``PERSEUS_ADMIN_USERNAME``（默认 admin）定位。

        Returns:
            bool: 操作是否成功
        """
        if not new_password:
            logger.error("未提供新密码，拒绝重设")
            return False

        from models.user import User
        from utils.password_utils import get_password_hash

        session = self._get_session()
        try:
            username = os.environ.get(ENV_ADMIN_USERNAME, "admin")
            admin = session.query(User).filter(User.username == username).first()
            if admin is None:
                logger.error(f"管理员用户不存在: {username}")
                return False
            admin.password = get_password_hash(new_password)
            session.commit()
            logger.info(f"管理员密码已重置: {username}")
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"管理员密码重设失败: {e}")
            return False
        finally:
            session.close()

    def _get_session(self) -> Session:
        """获取数据库会话"""
        if self._SessionLocal is None:
            engine = self._get_sync_engine()
            self._SessionLocal = sessionmaker(bind=engine)
        return self._SessionLocal()


def init_database(db_url: Optional[str] = None) -> bool:
    """
    初始化数据库的便捷函数

    执行:
    1. Alembic 迁移到最新 schema（幂等）
    2. 首次运行自动创建管理员用户（由 autobootstrap_admin 控制）

    Args:
        db_url: 数据库连接URL，默认使用models中定义的URL

    Returns:
        bool: 初始化是否成功
    """
    initializer = DatabaseInitializer(db_url)

    migrated = initializer.run_migrations()
    if not migrated["success"]:
        logger.error("数据库迁移失败，初始化中止")
        return False

    if not initializer.autobootstrap_admin():
        return False

    return True


def verify_database_ready(db_url: Optional[str] = None) -> tuple[bool, dict]:
    """
    运行容器启动时的只读就绪校验（不执行任何 DDL / 写入）。

    多容器部署中业务容器应设置 ``PERSEUS_INIT_DATABASE=false``，
    由独立的 init 任务先完成迁移与管理员引导。

    Returns:
        tuple: ``(ready: bool, state: dict)``，state 含 applied/head
    """
    return DatabaseInitializer(db_url).is_schema_ready(db_url)
