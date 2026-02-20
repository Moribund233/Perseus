# 模型初始化模块
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import QueuePool, StaticPool
import os
import logging

logger = logging.getLogger(__name__)

# 数据库连接URL - 会被client初始化时设置
DATABASE_URL = "sqlite:///./langit.db"

# 检测是否处于开发/测试模式（高并发测试场景）
# 通过环境变量控制，可以在压力测试时优化性能
IS_STRESS_TEST = os.environ.get("LANGIT_STRESS_TEST", "false").lower() == "true"
IS_DEBUG = os.environ.get("LANGIT_APP_DEBUG", "false").lower() == "true"

# 根据环境选择连接池策略
if IS_STRESS_TEST:
    # 压力测试模式：使用更大的连接池，但设置更短的超时
    # 注意：SQLite 是文件级数据库，真正并发写入仍受限于文件锁
    logger.info("启用压力测试模式数据库配置")
    engine = create_engine(
        DATABASE_URL,
        connect_args={
            "check_same_thread": False,
            "timeout": 5,  # SQLite 内部超时5秒
            "isolation_level": None,  # 使用自动提交模式，减少锁竞争
        },
        poolclass=QueuePool,
        pool_size=5,  # 较小的连接池，避免过度竞争
        max_overflow=10,  # 最大溢出连接数
        pool_timeout=5,  # 获取连接超时时间5秒（快速失败）
        pool_recycle=300,  # 5分钟回收连接
        pool_pre_ping=True,  # 连接前ping测试
        echo=False,  # 关闭SQL日志，减少IO
    )
elif IS_DEBUG:
    # 开发模式：标准配置，平衡性能和调试需求
    logger.info("启用开发模式数据库配置")
    engine = create_engine(
        DATABASE_URL,
        connect_args={
            "check_same_thread": False,
            "timeout": 10,  # SQLite 内部超时10秒
        },
        poolclass=QueuePool,
        pool_size=10,
        max_overflow=20,
        pool_timeout=30,
        pool_recycle=3600,
        pool_pre_ping=True,
    )
else:
    # 生产模式：保守配置，稳定性优先
    logger.info("启用生产模式数据库配置")
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=QueuePool,
        pool_size=10,
        max_overflow=20,
        pool_timeout=30,
        pool_recycle=3600,
        pool_pre_ping=True,
    )


# 添加连接池事件监听，用于调试和监控
@event.listens_for(engine, "connect")
def on_connect(dbapi_conn, connection_record):
    """新连接建立时的回调"""
    # 设置 SQLite 优化参数
    dbapi_conn.execute("PRAGMA journal_mode=WAL")  # 使用 WAL 模式提高并发性能
    dbapi_conn.execute("PRAGMA synchronous=NORMAL")  # 平衡性能和安全性
    dbapi_conn.execute("PRAGMA cache_size=10000")  # 增加缓存大小
    dbapi_conn.execute("PRAGMA temp_store=MEMORY")  # 临时表存储在内存


@event.listens_for(engine, "checkout")
def on_checkout(dbapi_conn, connection_record, connection_proxy):
    """连接从池中取出时的回调"""
    pass


@event.listens_for(engine, "checkin")
def on_checkin(dbapi_conn, connection_record):
    """连接归还到池时的回调"""
    pass

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
