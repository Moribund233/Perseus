"""
数据库依赖管理模块

提供数据库会话的获取和管理功能
"""
import logging
from contextlib import contextmanager
from sqlalchemy.orm import Session
from models import SessionLocal

logger = logging.getLogger(__name__)


async def get_db():
    """
    获取数据库会话（异步生成器）
    
    Yields:
        Session: 数据库会话实例
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"数据库会话异常: {e}")
        db.rollback()
        raise
    finally:
        db.close()


@contextmanager
def get_db_context():
    """
    获取数据库会话（同步上下文管理器）
    
    用于非FastAPI依赖注入场景
    
    Example:
        with get_db_context() as db:
            user = db.query(User).first()
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"数据库会话异常: {e}")
        db.rollback()
        raise
    finally:
        db.close()
