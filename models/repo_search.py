"""代码搜索索引数据模型

搜索内容来自 Git 对象（pygit2 读取 ref 的 tree/blob），持久化到主库
（PostgreSQL 为核心设施）。每文件一行；PostgreSQL 侧由迁移创建
`pg_trgm` GIN 索引以加速 `ILIKE '%q%'` 子串检索。
"""
from sqlalchemy import Integer, String, Text, ForeignKey, UniqueConstraint, Uuid as SAUuid
from sqlalchemy.orm import mapped_column

from models.base import BaseModel


class RepoSearchFile(BaseModel):
    """仓库内单个文件的搜索内容（每文件一行）"""
    __tablename__ = "repo_search_files"

    repository_id = mapped_column(
        SAUuid(as_uuid=True), ForeignKey("repositories.id"), nullable=False, index=True
    )
    path = mapped_column(String(1024), nullable=False)
    content = mapped_column(Text, nullable=False)
    size = mapped_column(Integer, nullable=False, default=0)

    __table_args__ = (
        UniqueConstraint("repository_id", "path", name="uq_repo_search_file"),
    )


class RepoSearchState(BaseModel):
    """仓库搜索索引状态：记录已索引的提交，用于增量维护与陈旧检测"""
    __tablename__ = "repo_search_state"

    repository_id = mapped_column(
        SAUuid(as_uuid=True), ForeignKey("repositories.id"), nullable=False, unique=True
    )
    indexed_commit = mapped_column(String(40), nullable=True)
