"""通用审计日志模型"""
from sqlalchemy import Column, Integer, String, Text, ForeignKey, Uuid as SAUuid
from sqlalchemy.orm import relationship
from models.base import BaseModel


class Activity(BaseModel):
    """
    通用审计日志

    记录仓库、Issue、PR、Release 等所有实体的操作日志。
    使用 entity_type + entity_id 实现多态关联。
    """
    __tablename__ = "activities"

    repository_id = Column(SAUuid(as_uuid=True), ForeignKey("repositories.id"), nullable=False)
    actor_id      = Column(SAUuid(as_uuid=True), ForeignKey("users.id"), nullable=False)
    entity_type   = Column(String(50), nullable=False)
    entity_id     = Column(SAUuid(as_uuid=True), nullable=False)
    action        = Column(String(50), nullable=False)
    details       = Column(Text, nullable=True)

    repository = relationship("Repository", backref="activities")
    actor      = relationship("User", backref="activities")
