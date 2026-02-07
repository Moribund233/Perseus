from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from models.base import BaseModel


class RepositoryMember(BaseModel):
    """
    仓库成员数据模型
    
    管理仓库与用户之间的多对多关系，包含成员权限信息
    """
    __tablename__ = "repository_members"  # 数据库表名
    
    repository_id = Column(Integer, ForeignKey("repositories.id"), nullable=False)
    """仓库ID，外键关联到repositories表"""
    
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    """用户ID，外键关联到users表"""
    
    role = Column(String(20), nullable=False, default="developer")
    """成员角色，可选值：owner, admin, developer, readonly，默认为developer"""
    
    is_active = Column(Boolean, default=True)
    """成员是否激活，默认为True"""
    
    # 关系定义
    repository = relationship("Repository", back_populates="members")
    """关联的仓库对象"""
    
    user = relationship("User", backref="repository_memberships")
    """关联的用户对象"""