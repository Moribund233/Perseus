from sqlalchemy import Column, String, Boolean, Integer, Text
from sqlalchemy.orm import relationship
from models.base import BaseModel


class Repository(BaseModel):
    """
    仓库数据模型
    
    存储Git仓库的基本信息，包括名称、路径、描述等
    """
    __tablename__ = "repositories"  # 数据库表名
    
    name = Column(String(100), index=True, nullable=False)
    """仓库名称，长度不超过100个字符"""
    
    path = Column(String(255), unique=True, nullable=False)
    """仓库路径，唯一，长度不超过255个字符"""
    
    description = Column(Text, nullable=True)
    """仓库描述，可选"""
    
    is_public = Column(Boolean, default=True)
    """是否公开仓库，默认为True"""
    
    owner_id = Column(Integer, nullable=False)
    """仓库所有者ID，关联用户表"""
    
    default_branch = Column(String(50), default="master")
    """默认分支名称，默认为master"""
    
    # 关系定义
    branches = relationship("Branch", back_populates="repository", cascade="all, delete-orphan")
    """仓库关联的分支列表"""
    
    commits = relationship("Commit", back_populates="repository", cascade="all, delete-orphan")
    """仓库关联的提交列表"""
    
    members = relationship("RepositoryMember", back_populates="repository", cascade="all, delete-orphan")
    """仓库关联的成员列表"""