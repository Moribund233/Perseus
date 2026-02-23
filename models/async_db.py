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

from config import get_config

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
    
    if url_lower.startswith("sqlite"):
        # SQLite: sqlite:///path -> sqlite+aiosqlite:///path
        return sync_url.replace("sqlite://", "sqlite+aiosqlite://", 1)
    elif url_lower.startswith("postgresql+psycopg2://"):
        # PostgreSQL with psycopg2: postgresql+psycopg2:// -> postgresql+asyncpg://
        return sync_url.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)
    elif url_lower.startswith("postgresql+pg8000://"):
        # PostgreSQL with pg8000: postgresql+pg8000:// -> postgresql+asyncpg://
        return sync_url.replace("postgresql+pg8000://", "postgresql+asyncpg://", 1)
    elif url_lower.startswith("postgresql://"):
        # PostgreSQL: postgresql:// -> postgresql+asyncpg://
        return sync_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif url_lower.startswith("mysql+pymysql://"):
        # MySQL with pymysql: mysql+pymysql:// -> mysql+aiomysql://
        return sync_url.replace("mysql+pymysql://", "mysql+aiomysql://", 1)
    elif url_lower.startswith("mysql://"):
        # MySQL: mysql:// -> mysql+aiomysql://
        return sync_url.replace("mysql://", "mysql+aiomysql://", 1)
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
    
    # 转换 URL 为异步版本
    async_url = _get_async_url(db_config.url)
    db_type = db_config.db_type
    
    logger.info(f"创建异步数据库引擎: {db_type}")
    
    # 连接池配置
    if db_config.is_stress_test:
        pool_size = db_config.stress_pool_size
        max_overflow = db_config.stress_max_overflow
        pool_timeout = db_config.stress_pool_timeout
        pool_recycle = db_config.stress_pool_recycle
    else:
        pool_size = db_config.pool_size
        max_overflow = db_config.max_overflow
        pool_timeout = db_config.pool_timeout
        pool_recycle = db_config.pool_recycle
    
    # 创建异步引擎
    engine = create_async_engine(
        async_url,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_timeout=pool_timeout,
        pool_recycle=pool_recycle,
        pool_pre_ping=True,
        echo=db_config.echo,
        # 异步引擎特定配置
        future=True,
    )
    
    logger.info(
        f"异步数据库引擎已创建: "
        f"pool_size={pool_size}, "
        f"max_overflow={max_overflow}, "
        f"pool_timeout={pool_timeout}s"
    )
    
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


async def init_async_db():
    """
    初始化异步数据库
    
    创建所有表（如果不存在）
    """
    engine = get_async_engine()
    if engine is None:
        logger.error("异步数据库初始化失败：数据库引擎未创建")
        return
    
    # 导入所有模型以确保表被创建
    from models import Base
    
    async with engine.begin() as conn:
        # 注意：生产环境应该使用 Alembic 进行迁移
        # 这里仅用于开发和测试
        # await conn.run_sync(Base.metadata.create_all)
        pass
    
    logger.info("异步数据库初始化完成")
