"""Pull Request 标签数据模型"""
from sqlalchemy import Column, Integer, String, ForeignKey, Table, UniqueConstraint, Uuid as SAUuid
from sqlalchemy.orm import relationship
from models.base import BaseModel
from models import Base

pr_label_association = Table(
    "pr_labels",
    Base.metadata,
    Column("pull_request_id", SAUuid(as_uuid=True), ForeignKey("pull_requests.id"), primary_key=True),
    Column("label_id", SAUuid(as_uuid=True), ForeignKey("pr_label_definitions.id"), primary_key=True),
)


class PRLabel(BaseModel):
    """PR 标签定义模型"""
    __tablename__ = "pr_label_definitions"

    repository_id = Column(SAUuid(as_uuid=True), ForeignKey("repositories.id"), nullable=False)
    name = Column(String(50), nullable=False)
    color = Column(String(7), nullable=False, default="#cccccc")
    description = Column(String(255), nullable=True)

    repository = relationship("Repository", backref="pr_label_definitions")
    labeled_prs = relationship("PullRequest", secondary=pr_label_association, backref="pr_labels")

    __table_args__ = (
        UniqueConstraint("repository_id", "name", name="uq_pr_label_name"),
    )
