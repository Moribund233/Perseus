# 模型初始化模块
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# 数据库连接URL - 会被client初始化时设置
DATABASE_URL = "sqlite:///./langit.db"

# 创建数据库引擎
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}  # SQLite需要此参数
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建基础模型类
Base = declarative_base()

# 导入所有模型
from models.base import BaseModel
from models.user import User
from models.repository import Repository
from models.repository_member import RepositoryMember
from models.branch import Branch
from models.commit import Commit
from models.pull_request import PullRequest, PRComment, PRReview
from models.issue import Issue, Label, IssueComment

__all__ = ["Base", "SessionLocal", "engine", "BaseModel", "User", "Repository", "RepositoryMember", "Branch", "Commit",
           "PullRequest", "PRComment", "PRReview", "Issue", "Label", "IssueComment"]
