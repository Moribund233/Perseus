from sqlalchemy import Boolean, Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship, backref
from models.base import BaseModel


class PullRequest(BaseModel):
    """
    Pull Request 数据模型
    
    存储代码合并请求信息，支持代码审查流程
    """
    __tablename__ = "pull_requests"
    
    repository_id = Column(Integer, ForeignKey("repositories.id"), nullable=False)
    """所属仓库ID"""
    
    pr_number = Column(Integer, nullable=False)
    """PR 编号（每个仓库内自增）"""
    
    title = Column(String(255), nullable=False)
    """PR 标题"""
    
    description = Column(Text, nullable=True)
    """PR 描述（支持 Markdown）"""
    
    source_branch = Column(String(100), nullable=False)
    """源分支（要合并的分支）"""
    
    target_branch = Column(String(100), nullable=False)
    """目标分支（合并到的分支）"""
    
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    """创建者ID"""
    
    status = Column(String(20), default="open")
    """PR 状态：open/merged/closed"""

    is_draft = Column(Boolean, default=False)
    """是否为草稿 PR"""
    
    # 合并相关信息
    merged_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    """合并者ID"""
    
    merged_commit_hash = Column(String(40), nullable=True)
    """合并后的提交哈希"""
    
    # 关联关系
    repository = relationship("Repository", backref="pull_requests")
    author = relationship("User", foreign_keys=[author_id], backref="created_prs")
    merger = relationship("User", foreign_keys=[merged_by], backref="merged_prs")
    
    # 关联的评论和审查
    comments = relationship("PRComment", back_populates="pull_request", cascade="all, delete-orphan")
    reviews = relationship("PRReview", back_populates="pull_request", cascade="all, delete-orphan")


class PRComment(BaseModel):
    """
    PR 评论模型
    
    支持行级评论和一般评论
    """
    __tablename__ = "pr_comments"
    
    pull_request_id = Column(Integer, ForeignKey("pull_requests.id"), nullable=False)
    """所属 PR ID"""
    
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    """评论作者ID"""
    
    content = Column(Text, nullable=False)
    """评论内容"""
    
    # 行级评论定位
    file_path = Column(String(500), nullable=True)
    """评论的文件路径（行级评论时必填）"""
    
    line_number = Column(Integer, nullable=True)
    """行号（行级评论时必填）"""
    
    commit_hash = Column(String(40), nullable=True)
    """评论针对的提交哈希"""
    
    parent_id = Column(Integer, ForeignKey("pr_comments.id"), nullable=True)
    """父评论ID（支持回复）"""
    
    # 关联关系
    pull_request = relationship("PullRequest", back_populates="comments")
    author = relationship("User", backref="pr_comments")
    replies = relationship("PRComment", backref=backref("parent", remote_side="PRComment.id"))


class PRReview(BaseModel):
    """
    PR 审查记录模型
    
    记录用户对 PR 的审查状态和意见
    """
    __tablename__ = "pr_reviews"
    
    pull_request_id = Column(Integer, ForeignKey("pull_requests.id"), nullable=False)
    """所属 PR ID"""
    
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    """审查者ID"""
    
    status = Column(String(20), nullable=False, default="pending")
    """审查状态：pending/approved/changes_requested"""
    
    comment = Column(Text, nullable=True)
    """审查意见"""
    
    # 关联关系
    pull_request = relationship("PullRequest", back_populates="reviews")
    reviewer = relationship("User", backref="pr_reviews")
