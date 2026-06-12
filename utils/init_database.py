"""
数据库初始化工具模块

提供数据库表创建和首次运行管理员引导功能。
管理员凭据通过环境变量注入，不在代码中硬编码。
"""
import os
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from models import Base
from utils.logging import get_named_logger

logger = get_named_logger("database")

# 管理员环境变量名称
ENV_ADMIN_USERNAME = "PERSEUS_ADMIN_USERNAME"
ENV_ADMIN_PASSWORD = "PERSEUS_ADMIN_PASSWORD"
ENV_ADMIN_EMAIL = "PERSEUS_ADMIN_EMAIL"


def _to_sync_db_url(url: str) -> str:
    """将异步驱动 URL 转为同步 URL（用于表创建和命令行工具）"""
    return url.replace("+aiosqlite", "", 1).replace("+asyncpg", "", 1)


class DatabaseInitializer:
    """
    数据库初始化器

    负责初始化数据库表结构，以及首次运行时自动创建管理员用户。
    """

    def __init__(self, db_url: Optional[str] = None):
        self.db_url = db_url
        self._engine = None
        self._SessionLocal = None

    def _get_sync_engine(self):
        """获取同步引擎（create_tables 需要同步连接）"""
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

    def create_tables(self) -> bool:
        """
        创建数据库表结构

        Returns:
            bool: 创建是否成功
        """
        try:
            engine = self._get_sync_engine()
            Base.metadata.create_all(bind=engine)
            return True
        except Exception as e:
            logger.error(f"数据库表创建失败: {e}")
            return False

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
            session.commit()

            logger.info(f"管理员用户已自动创建: {username} <{email}>")
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"管理员自动创建失败: {e}")
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
    1. 创建表结构
    2. 首次运行自动创建管理员用户（由 autobootstrap_admin 控制）

    Args:
        db_url: 数据库连接URL，默认使用models中定义的URL

    Returns:
        bool: 初始化是否成功
    """
    initializer = DatabaseInitializer(db_url)

    if not initializer.create_tables():
        return False

    if not initializer.autobootstrap_admin():
        return False

    return True
