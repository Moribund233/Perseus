"""
数据库初始化工具模块

提供数据库表创建和测试数据初始化功能
"""
import hashlib
from typing import Optional

from passlib.context import CryptContext
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 导入模型
from models import Base, engine, SessionLocal
from utils.logging_utils import get_logger

# 密码哈希上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

logger = get_logger("database")


class DatabaseInitializer:
    """
    数据库初始化器

    负责初始化SQLite数据库，包括创建表结构和可选的测试数据
    """

    def __init__(self, db_url: Optional[str] = None):
        """
        初始化数据库初始化器

        Args:
            db_url: 数据库连接URL，默认使用models中定义的URL
        """
        self.db_url = db_url
        self._engine = None
        self._SessionLocal = None

    def create_tables(self) -> bool:
        """
        创建数据库表结构

        Returns:
            bool: 创建是否成功
        """
        try:
            if self.db_url:
                self._engine = create_engine(
                    self.db_url, connect_args={"check_same_thread": False}
                )
                Base.metadata.create_all(bind=self._engine)
            else:
                Base.metadata.create_all(bind=engine)
            return True
        except Exception as e:
            logger.error(f"数据库表创建失败: {e}")
            return False

    def create_test_data(self) -> bool:
        """
        创建测试数据

        仅在开发环境下使用，创建默认用户、仓库、分支和提交数据

        Returns:
            bool: 创建是否成功
        """
        session = SessionLocal() if self._SessionLocal is None else self._SessionLocal()

        try:
            self._create_test_users(session)
            self._create_test_repositories(session)
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"创建测试数据失败: {e}")
            return False
        finally:
            session.close()

    def _create_test_users(self, session) -> None:
        """
        创建测试用户数据

        Args:
            session: 数据库会话
        """
        from models.user import User

        user_count = session.query(User).count()
        if user_count > 0:
            return

        # 创建管理员用户
        admin_user = User(
            username="admin",
            email="admin@example.com",
            password=pwd_context.hash("admin123"[:72]),
            full_name="Admin User",
            is_active=True,
            is_admin=True,
        )
        session.add(admin_user)

        # 创建普通用户
        test_user = User(
            username="test",
            email="test@example.com",
            password=pwd_context.hash("test123"[:72]),
            full_name="Test User",
            is_active=True,
            is_admin=False,
        )
        session.add(test_user)

        session.commit()
        logger.info("测试用户数据创建成功")

    def _create_test_repositories(self, session) -> None:
        """
        创建测试仓库、分支和提交数据

        Args:
            session: 数据库会话
        """
        from models.user import User
        from models.repository import Repository
        from models.branch import Branch
        from models.commit import Commit

        repo_count = session.query(Repository).count()
        if repo_count > 0:
            return

        # 获取管理员用户
        admin_user = session.query(User).filter(User.username == "admin").first()
        if not admin_user:
            return

        # 创建测试仓库
        test_repos = [
            Repository(
                name="test-repo-1",
                path="/repos/test-repo-1",
                description="第一个测试仓库",
                is_public=True,
                owner_id=admin_user.id,
                default_branch="master",
            ),
            Repository(
                name="test-repo-2",
                path="/repos/test-repo-2",
                description="第二个测试仓库",
                is_public=False,
                owner_id=admin_user.id,
                default_branch="main",
            ),
        ]

        for repo in test_repos:
            session.add(repo)

        session.commit()
        logger.info("测试仓库数据创建成功")

        # 创建分支数据
        for repo in test_repos:
            # 创建主分支
            main_branch = Branch(
                name=repo.default_branch,
                repository_id=repo.id,
                is_protected=True,
                is_default=True,
            )
            session.add(main_branch)

            # 创建开发分支
            dev_branch = Branch(
                name="develop",
                repository_id=repo.id,
                is_protected=False,
                is_default=False,
            )
            session.add(dev_branch)

        session.commit()
        logger.info("测试分支数据创建成功")

        # 创建提交数据
        branches = session.query(Branch).all()
        for i, branch in enumerate(branches):
            unique_hash = hashlib.sha1(
                f"initial-commit-{branch.repository_id}-{branch.id}-{i}".encode()
            ).hexdigest()
            initial_commit = Commit(
                hash=unique_hash,
                repository_id=branch.repository_id,
                branch_id=branch.id,
                author_name="Admin User",
                author_email="admin@example.com",
                committer_name="Admin User",
                committer_email="admin@example.com",
                commit_message="Initial commit",
                parent_hashes="",
            )
            session.add(initial_commit)

        session.commit()
        logger.info("测试提交数据创建成功")


def init_database(
    db_url: Optional[str] = None, create_test_data: bool = False
) -> bool:
    """
    初始化数据库的便捷函数

    Args:
        db_url: 数据库连接URL，默认使用models中定义的URL
        create_test_data: 是否创建测试数据

    Returns:
        bool: 初始化是否成功
    """
    initializer = DatabaseInitializer(db_url)

    if not initializer.create_tables():
        return False

    if create_test_data:
        initializer.create_test_data()

    return True
