from sqlalchemy import Column, Integer, String, Text, ForeignKey, Table, Uuid as SAUuid
from sqlalchemy.orm import relationship, mapped_column
from models.base import BaseModel
from models import Base


# 多对多关联表：Issue 与 Label
issue_label_association = Table(
    "issue_labels",
    Base.metadata,
    Column("issue_id", SAUuid(as_uuid=True), ForeignKey("issues.id")),
    Column("label_id", SAUuid(as_uuid=True), ForeignKey("labels.id"))
)


class Issue(BaseModel):
    """
    Issue 数据模型
    
    跟踪问题、bug、功能请求等
    """
    __tablename__ = "issues"
    
    repository_id = mapped_column(SAUuid(as_uuid=True), ForeignKey("repositories.id"), nullable=False)
    """所属仓库ID"""
    
    issue_number = mapped_column(Integer, nullable=False)
    """Issue 编号（每个仓库内自增）"""
    
    title = mapped_column(String(255), nullable=False)
    """标题"""
    
    description = mapped_column(Text, nullable=True)
    """描述（支持 Markdown）"""
    
    author_id = mapped_column(SAUuid(as_uuid=True), ForeignKey("users.id"), nullable=False)
    """创建者ID"""
    
    status = mapped_column(String(20), default="open")
    """状态：open/closed"""
    
    priority = mapped_column(String(20), default="medium")
    """优先级：low/medium/high/critical"""
    
    assignee_id = mapped_column(SAUuid(as_uuid=True), ForeignKey("users.id"), nullable=True)
    """指派给的用户ID"""
    
    closed_by = mapped_column(SAUuid(as_uuid=True), ForeignKey("users.id"), nullable=True)
    """关闭者ID"""
    
    # 关联关系
    repository = relationship("Repository", backref="issues")
    author = relationship("User", foreign_keys=[author_id], backref="created_issues")
    assignee = relationship("User", foreign_keys=[assignee_id], backref="assigned_issues")
    closer = relationship("User", foreign_keys=[closed_by], backref="closed_issues")
    
    labels = relationship("Label", secondary=issue_label_association, backref="issues")
    comments = relationship("IssueComment", back_populates="issue", cascade="all, delete-orphan")


class Label(BaseModel):
    """
    标签模型
    
    用于分类 Issue 和 PR
    """
    __tablename__ = "labels"
    
    repository_id = mapped_column(SAUuid(as_uuid=True), ForeignKey("repositories.id"), nullable=False)
    """所属仓库ID"""
    
    name = mapped_column(String(50), nullable=False)
    """标签名称"""
    
    color = mapped_column(String(7), nullable=False, default="#cccccc")
    """标签颜色（十六进制）"""
    
    description = mapped_column(String(255), nullable=True)
    """标签描述"""
    
    # 关联关系
    repository = relationship("Repository", backref="labels")


class IssueComment(BaseModel):
    """
    Issue 评论模型
    """
    __tablename__ = "issue_comments"
    
    issue_id = mapped_column(SAUuid(as_uuid=True), ForeignKey("issues.id"), nullable=False)
    """所属 Issue ID"""
    
    author_id = mapped_column(SAUuid(as_uuid=True), ForeignKey("users.id"), nullable=False)
    """作者ID"""
    
    content = mapped_column(Text, nullable=False)
    """评论内容"""
    
    # 关联关系
    issue = relationship("Issue", back_populates="comments")
    author = relationship("User", backref="issue_comments")
