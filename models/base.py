from sqlalchemy import Column, Integer, DateTime
from sqlalchemy.sql import func
from models import Base


class BaseModel(Base):
    """
    基础数据模型类
    
    所有数据模型的基类，包含通用的ID、创建时间和更新时间字段
    """
    __abstract__ = True  # 抽象类，不会创建实际的数据库表
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    """主键ID，自增整数"""
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    """创建时间，默认值为当前时间"""
    
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    """更新时间，默认值为None，更新时自动设置为当前时间"""
