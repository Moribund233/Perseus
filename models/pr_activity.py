"""Pull Request 活动日志模型"""
from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from models.base import BaseModel


class PRActivity(BaseModel):
    """PR 活动日志，记录 review/merge/close/push/commented 等事件"""
    __tablename__ = "pr_activities"

    pull_request_id = Column(Integer, ForeignKey("pull_requests.id"), nullable=False)
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action = Column(String(50), nullable=False)
    details = Column(Text, nullable=True)

    pull_request = relationship("PullRequest", backref="activities")
    actor = relationship("User", backref="pr_activities")
