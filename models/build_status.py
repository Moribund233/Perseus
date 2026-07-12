from sqlalchemy import Column, String, Integer, DateTime, Text
from models.base import BaseModel


VALID_STATUSES = {"pending", "running", "success", "failure", "error", "cancelled"}


class BuildStatus(BaseModel):
    __tablename__ = "build_status"

    repo_id = Column(Integer, nullable=False, index=True)
    branch = Column(String(255), nullable=False)
    commit_sha = Column(String(64), nullable=False)
    commit_message = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="pending", index=True)
    triggered_by = Column(Integer, nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    details_url = Column(String(512), nullable=True)
    logs = Column(Text, nullable=True)
