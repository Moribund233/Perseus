"""
异步数据库支持模块

提供异步数据库会话管理，避免同步操作阻塞事件循环

使用 SQLAlchemy 2.0 的异步引擎和会话
"""
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
    AsyncEngine
)
from sqlalchemy.pool import NullPool

from core.config import get_config
from models import _resolve_pool_config

logger = logging.getLogger(__name__)

# 全局异步引擎和会话工厂
_async_engine: Optional[AsyncEngine] = None
_async_session_maker: Optional[async_sessionmaker] = None


def _get_async_url(sync_url: str) -> str:
    """
    将同步数据库 URL 转换为异步 URL

    Args:
        sync_url: 同步数据库 URL

    Returns:
        str: 异步数据库 URL
    """
    url_lower = sync_url.lower()

    # 如果已经是异步 URL，直接返回
    if url_lower.startswith("sqlite+aiosqlite://"):
        return sync_url
    if url_lower.startswith("postgresql+asyncpg://"):
        return sync_url

    if url_lower.startswith("sqlite://"):
        # SQLite: sqlite:///path -> sqlite+aiosqlite:///path
        return sync_url.replace("sqlite://", "sqlite+aiosqlite://", 1)
    elif url_lower.startswith("postgresql+psycopg2://"):
        # PostgreSQL with psycopg2 -> postgresql+asyncpg://
        return sync_url.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)
    elif url_lower.startswith("postgresql://"):
        # PostgreSQL: postgresql:// -> postgresql+asyncpg://
        return sync_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    else:
        return sync_url


def _create_async_engine_with_config() -> AsyncEngine:
    """
    根据配置创建异步数据库引擎

    Returns:
        AsyncEngine: SQLAlchemy 异步引擎实例
    """
    config = get_config()
    db_config = config.database

    async_url = _get_async_url(db_config.url)

    # SQLite 异步引擎使用 NullPool，PostgreSQL 使用连接池
    if async_url.startswith("sqlite"):
        engine = create_async_engine(
            async_url,
            poolclass=NullPool,
            future=True,
            echo=db_config.echo
        )
        logger.debug("异步 SQLite 引擎创建 (NullPool)")
    else:
        pool_config = _resolve_pool_config(db_config)
        engine = create_async_engine(
            async_url,
            pool_pre_ping=True,
            future=True,
            **pool_config
        )
        logger.debug(f"异步 PostgreSQL 引擎创建: pool_size={pool_config['pool_size']}, max_overflow={pool_config['max_overflow']}")

    return engine


def get_async_engine() -> Optional[AsyncEngine]:
    """
    获取异步数据库引擎（单例模式）
    
    Returns:
        AsyncEngine: 异步数据库引擎实例，创建失败返回 None
    """
    global _async_engine
    
    if _async_engine is None:
        try:
            _async_engine = _create_async_engine_with_config()
        except Exception as e:
            logger.error(f"创建异步数据库引擎失败: {e}")
            # 返回 None，让调用者处理
            return None
    
    return _async_engine


def get_async_session_maker() -> Optional[async_sessionmaker]:
    """
    获取异步会话工厂（单例模式）
    
    Returns:
        async_sessionmaker: 异步会话工厂，创建失败返回 None
    """
    global _async_session_maker
    
    if _async_session_maker is None:
        engine = get_async_engine()
        if engine is None:
            return None
        _async_session_maker = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False
        )
    
    return _async_session_maker


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """
    获取异步数据库会话（FastAPI 依赖）
    
    Yields:
        AsyncSession: 异步数据库会话实例
        
    Raises:
        RuntimeError: 数据库引擎未初始化时抛出
        
    Example:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_async_db)):
            result = await db.execute(select(Item))
            return result.scalars().all()
    """
    session_maker = get_async_session_maker()
    if session_maker is None:
        raise RuntimeError("数据库连接失败，请检查数据库配置和驱动是否安装")
    
    async with session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            logger.error(f"异步数据库会话异常: {e}")
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_async_db_context() -> AsyncGenerator[AsyncSession, None]:
    """
    获取异步数据库会话（异步上下文管理器）
    
    用于非 FastAPI 依赖注入场景
    
    Raises:
        RuntimeError: 数据库引擎未初始化时抛出
        
    Example:
        async with get_async_db_context() as db:
            result = await db.execute(select(User))
            users = result.scalars().all()
    """
    session_maker = get_async_session_maker()
    if session_maker is None:
        raise RuntimeError("数据库连接失败，请检查数据库配置和驱动是否安装")
    
    async with session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            logger.error(f"异步数据库会话异常: {e}")
            await session.rollback()
            raise
        finally:
            await session.close()


async def close_async_engine():
    """
    关闭异步数据库引擎
    
    在应用关闭时调用，释放所有连接
    """
    global _async_engine, _async_session_maker
    
    if _async_engine is not None:
        await _async_engine.dispose()
        _async_engine = None
        _async_session_maker = None
        logger.info("异步数据库引擎已关闭")
