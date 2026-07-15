"""
SSH Key 模型

F-019: SSH Key 管理
"""

from sqlalchemy import Column, String, Integer, ForeignKey, Text, Uuid as SAUuid
from sqlalchemy.orm import relationship
from models.base import BaseModel


class SSHKey(BaseModel):
    """
    SSH 公钥模型

    存储用户的 SSH 公钥，用于 Git SSH 认证
    """
    __tablename__ = "ssh_keys"

    name = Column(String(100), nullable=False)
    """Key 名称，用户自定义，如 'My Laptop'"""

    public_key = Column(Text, nullable=False)
    """SSH 公钥内容"""

    fingerprint = Column(String(100), nullable=False, index=True)
    """Key 的 fingerprint，用于唯一标识和查找"""

    user_id = Column(SAUuid(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    """所属用户 ID"""

    # 关联关系
    user = relationship("User", back_populates="ssh_keys")

    def to_dict(self):
        """转换为字典格式"""
        return {
            "id": self.id,
            "name": self.name,
            "public_key": self.public_key,
            "fingerprint": self.fingerprint,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
