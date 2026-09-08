"""仓库标签数据模型"""
from sqlalchemy import Column, Integer, String, ForeignKey, Table, UniqueConstraint, Uuid as SAUuid
from sqlalchemy.orm import relationship, mapped_column
from models.base import BaseModel
from models import Base

repo_label_association = Table(
    "repo_labels",
    Base.metadata,
    Column("repository_id", SAUuid(as_uuid=True), ForeignKey("repositories.id"), primary_key=True),
    Column("label_id", SAUuid(as_uuid=True), ForeignKey("repo_label_definitions.id"), primary_key=True),
)


class RepoLabel(BaseModel):
    __tablename__ = "repo_label_definitions"

    repository_id = mapped_column(SAUuid(as_uuid=True), ForeignKey("repositories.id"), nullable=False)
    name = mapped_column(String(50), nullable=False)
    color = mapped_column(String(7), nullable=False, default="#cccccc")
    description = mapped_column(String(255), nullable=True)

    repository = relationship("Repository", backref="repo_label_definitions")
    labeled_repos = relationship("Repository", secondary=repo_label_association, backref="repo_labels")

    __table_args__ = (
        UniqueConstraint("repository_id", "name", name="uq_repo_label_name"),
    )
