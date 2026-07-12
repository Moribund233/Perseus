from sqlalchemy import Column, String, Boolean
from sqlalchemy.orm import relationship
from models.base import BaseModel


class User(BaseModel):
    """
    用户数据模型

    存储系统用户信息，包含用户名、邮箱和密码等字段
    """
    __tablename__ = "users"  # 数据库表名

    username = Column(String(50), unique=True, index=True, nullable=False)
    """用户名，唯一，长度不超过50个字符"""

    email = Column(String(100), unique=True, index=True, nullable=False)
    """邮箱，唯一，长度不超过100个字符"""

    password = Column(String(255), nullable=False)
    """密码，经过哈希处理，长度不超过255个字符"""

    full_name = Column(String(100), nullable=True)
    """用户全名，可选，长度不超过100个字符"""

    avatar_url = Column(String(512), nullable=True)
    """用户头像 URL，可选，长度不超过512个字符"""

    is_active = Column(Boolean, default=True)
    """用户是否激活，默认为True"""

    is_admin = Column(Boolean, default=False)
    """用户是否为管理员，默认为False"""

    # 关联关系
    ssh_keys = relationship("SSHKey", back_populates="user", cascade="all, delete-orphan")
    """用户的 SSH Keys"""
