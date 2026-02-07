from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from models.base import BaseModel


class Commit(BaseModel):
    """
    提交数据模型
    
    存储Git仓库的提交信息，包括哈希值、作者、提交信息等
    """
    __tablename__ = "commits"  # 数据库表名
    
    hash = Column(String(40), unique=True, nullable=False)
    """提交哈希值，唯一，长度为40个字符(sha1)"""
    
    repository_id = Column(Integer, ForeignKey("repositories.id"), nullable=False)
    """仓库ID，外键关联到repositories表"""
    
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False)
    """分支ID，外键关联到branches表"""
    
    author_name = Column(String(100), nullable=False)
    """作者名称，长度不超过100个字符"""
    
    author_email = Column(String(100), nullable=False)
    """作者邮箱，长度不超过100个字符"""
    
    committer_name = Column(String(100), nullable=False)
    """提交者名称，长度不超过100个字符"""
    
    committer_email = Column(String(100), nullable=False)
    """提交者邮箱，长度不超过100个字符"""
    
    commit_message = Column(Text, nullable=False)
    """提交信息"""
    
    commit_date = Column(DateTime(timezone=True), server_default=func.now())
    """提交时间，默认值为当前时间"""
    
    parent_hashes = Column(Text, nullable=True)
    """父提交哈希值，多个哈希值用逗号分隔"""
    
    # 关系定义
    repository = relationship("Repository", back_populates="commits")
    """关联的仓库对象"""
    
    branch = relationship("Branch", back_populates="commits")
    """关联的分支对象"""