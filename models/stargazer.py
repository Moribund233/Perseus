"""仓库收藏数据模型"""
from sqlalchemy import Column, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from models.base import BaseModel


class Stargazer(BaseModel):
    __tablename__ = "stargazers"

    repository_id = Column(Integer, ForeignKey("repositories.id"), nullable=False)
    user_id       = Column(Integer, ForeignKey("users.id"), nullable=False)

    repository = relationship("Repository", backref="stargazers")
    user       = relationship("User", backref="starred_repos")

    __table_args__ = (
        UniqueConstraint("repository_id", "user_id", name="uq_repo_user_star"),
    )
