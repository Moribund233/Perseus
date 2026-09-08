from sqlalchemy import Integer, String, Text, Boolean, DateTime, ForeignKey, Index, Uuid as SAUuid
from sqlalchemy.orm import relationship, mapped_column
from models.base import BaseModel


class Notification(BaseModel):
    """通知模型 - 存储用户站内通知"""

    __tablename__ = "notifications"

    user_id = mapped_column(SAUuid(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    """接收通知的用户 ID"""

    type = mapped_column(String(50), nullable=False)
    """通知类型: pull_request, issue, review, comment"""

    title = mapped_column(String(255), nullable=False)
    """通知标题"""

    message = mapped_column(Text, nullable=False)
    """通知内容"""

    repository_id = mapped_column(SAUuid(as_uuid=True), ForeignKey("repositories.id"), nullable=True, index=True)
    """关联仓库 ID"""

    target_type = mapped_column(String(50), nullable=True)
    """目标类型: pull_request, issue"""

    target_id = mapped_column(SAUuid(as_uuid=True), nullable=True)
    """目标 ID"""

    is_read = mapped_column(Boolean, default=False, nullable=False)
    """是否已读"""

    read_at = mapped_column(DateTime(timezone=True), nullable=True)
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