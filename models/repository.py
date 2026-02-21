from sqlalchemy import Column, String, Boolean, Integer, Text, ForeignKey
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
    
    # Fork 相关字段
    forked_from_id = Column(Integer, ForeignKey("repositories.id"), nullable=True)
    """Fork 来源仓库ID，为空表示不是 Fork"""
    
    fork_count = Column(Integer, default=0)
    """被 Fork 的次数"""
    
    # 关系定义
    branches = relationship("Branch", back_populates="repository", cascade="all, delete-orphan")
    """仓库关联的分支列表"""
    
    commits = relationship("Commit", back_populates="repository", cascade="all, delete-orphan")
    """仓库关联的提交列表"""
    
    members = relationship("RepositoryMember", back_populates="repository", cascade="all, delete-orphan")
    """仓库关联的成员列表"""
    
    # Fork 关系
    forks = relationship(
        "Repository",
        backref="parent",
        remote_side="Repository.id",
        foreign_keys="Repository.forked_from_id"
    )
    """该仓库的所有 Fork 列表"""
    
    def is_fork(self) -> bool:
        """
        判断是否为 Fork 仓库
        
        Returns:
            bool: 是否为 Fork
        """
        return self.forked_from_id is not None
    
    def get_fork_path(self, username: str) -> str:
        """
        生成 Fork 后的仓库路径
        
        Args:
            username: Fork 者的用户名
            
        Returns:
            str: 新的仓库路径
        """
        return f"{username}/{self.name}"
    
    def __repr__(self) -> str:
        return f"<Repository(id={self.id}, name='{self.name}', path='{self.path}')>"
