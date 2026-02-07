from sqlalchemy import Column, String, Boolean, Integer, ForeignKey
from sqlalchemy.orm import relationship
from models.base import BaseModel


class Branch(BaseModel):
    """
    分支数据模型
    
    存储Git仓库的分支信息，包括分支名称、保护状态等
    """
    __tablename__ = "branches"  # 数据库表名
    
    name = Column(String(50), nullable=False)
    """分支名称，长度不超过50个字符"""
    
    repository_id = Column(Integer, ForeignKey("repositories.id"), nullable=False)
    """仓库ID，外键关联到repositories表"""
    
    is_protected = Column(Boolean, default=False)
    """分支是否受保护，默认为False"""
    
    require_code_review = Column(Boolean, default=False)
    """是否需要代码审查，默认为False"""
    
    require_status_checks = Column(Boolean, default=False)
    """是否需要状态检查，默认为False"""
    
    is_default = Column(Boolean, default=False)
    """是否为默认分支，默认为False"""
    
    # 关系定义
    repository = relationship("Repository", back_populates="branches")
    """关联的仓库对象"""
    
    commits = relationship("Commit", back_populates="branch")
    """关联的提交列表"""