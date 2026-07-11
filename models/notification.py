from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from models.base import BaseModel


class Notification(BaseModel):
    """通知模型 - 存储用户站内通知"""

    __tablename__ = "notifications"

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    """接收通知的用户 ID"""

    type = Column(String(50), nullable=False)
    """通知类型: pull_request, issue, review, comment"""

    title = Column(String(255), nullable=False)
    """通知标题"""

    message = Column(Text, nullable=False)
    """通知内容"""

    repository_id = Column(Integer, ForeignKey("repositories.id"), nullable=True, index=True)
    """关联仓库 ID"""

    target_type = Column(String(50), nullable=True)
    """目标类型: pull_request, issue"""

    target_id = Column(Integer, nullable=True)
    """目标 ID"""

    is_read = Column(Boolean, default=False, nullable=False)
    """是否已读"""

    read_at = Column(DateTime(timezone=True), nullable=True)
    """阅读时间"""

    # Relationships
    user = relationship("User", backref="notifications")
    repository = relationship("Repository", backref="notifications")

    __table_args__ = (
        Index("ix_notifications_user_id_is_read", "user_id", "is_read"),
        Index("ix_notifications_created_at", "created_at"),
    )

    def __repr__(self):
        return f"<Notification(id={self.id}, user_id={self.user_id}, type='{self.type}', title='{self.title}')>"