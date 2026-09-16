"""仓库关注数据模型"""
from sqlalchemy import ForeignKey, UniqueConstraint, Uuid as SAUuid
from sqlalchemy.orm import relationship, mapped_column
from models.base import BaseModel


class Watcher(BaseModel):
    __tablename__ = "watchers"

    repository_id = mapped_column(SAUuid(as_uuid=True), ForeignKey("repositories.id"), nullable=False)
    user_id       = mapped_column(SAUuid(as_uuid=True), ForeignKey("users.id"), nullable=False)

    repository = relationship("Repository", backref="watchers")
    user       = relationship("User", backref="watched_repos")

    __table_args__ = (
        UniqueConstraint("repository_id", "user_id", name="uq_repo_user_watch"),
    )
