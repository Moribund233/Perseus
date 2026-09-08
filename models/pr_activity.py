"""Pull Request 活动日志模型"""
from sqlalchemy import Integer, String, Text, ForeignKey, Uuid as SAUuid
from sqlalchemy.orm import relationship, mapped_column
from models.base import BaseModel


class PRActivity(BaseModel):
    """PR 活动日志，记录 review/merge/close/push/commented 等事件"""
    __tablename__ = "pr_activities"

    pull_request_id = mapped_column(SAUuid(as_uuid=True), ForeignKey("pull_requests.id"), nullable=False)
    actor_id = mapped_column(SAUuid(as_uuid=True), ForeignKey("users.id"), nullable=False)
    action = mapped_column(String(50), nullable=False)
    details = mapped_column(Text, nullable=True)

    pull_request = relationship("PullRequest", backref="activities")
    actor = relationship("User", backref="pr_activities")
