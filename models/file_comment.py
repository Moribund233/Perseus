"""
行内评论模型（Editor Discussions / 文件+行号锚定）

将评论锚定到仓库内文件的具体行（可选分支/提交），不依赖 PR 上下文。
"""
from sqlalchemy import Integer, String, Text, Boolean, ForeignKey, Index, CheckConstraint, Uuid as SAUuid
from sqlalchemy.orm import relationship, backref, mapped_column
from models.base import BaseModel


class FileComment(BaseModel):
    __tablename__ = "file_comments"

    repository_id = mapped_column(SAUuid(as_uuid=True), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True)
    author_id = mapped_column(SAUuid(as_uuid=True), ForeignKey("users.id"), nullable=False)
    content = mapped_column(Text, nullable=False)
    file_path = mapped_column(String(500), nullable=False)
    line_number = mapped_column(Integer, nullable=True)
    branch = mapped_column(String(100), nullable=True)
    commit_hash = mapped_column(String(40), nullable=True)
    parent_id = mapped_column(SAUuid(as_uuid=True), ForeignKey("file_comments.id"), nullable=True)
    resolved = mapped_column(Boolean, default=False, nullable=False)

    repository = relationship("Repository", backref="file_comments")
    author = relationship("User", backref="file_comments")
    replies = relationship(
        "FileComment",
        backref=backref("parent", remote_side="FileComment.id"),
    )

    __table_args__ = (
        CheckConstraint("line_number IS NULL OR line_number >= 1", name="ck_file_comment_line_positive"),
        Index("ix_file_comments_repo_file_created", "repository_id", "file_path", "created_at"),
    )

    def __repr__(self):
        return f"<FileComment(id={self.id}, file={self.file_path}:{self.line_number}, repo_id={self.repository_id})>"