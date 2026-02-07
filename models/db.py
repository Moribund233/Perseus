"""
数据库依赖管理模块

提供数据库会话的获取和管理功能
"""
from sqlalchemy.orm import Session
from models import SessionLocal


async def get_db():
    """
    获取数据库会话
    
    Yields:
        Session: 数据库会话实例
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
