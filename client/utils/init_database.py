"""
数据库初始化工具类

负责客户端启动时的数据库初始化流程，包括创建数据库表结构等
"""
import os
from typing import Optional
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext

# 导入模型
from models import Base, engine, SessionLocal

# 密码哈希上下文
pwd_context = CryptContext(
    schemes=["bcrypt"], 
    deprecated="auto"
)


class DatabaseInitializer:
    """
    数据库初始化器
    
    负责初始化SQLite数据库，包括创建表结构等
    """
    
    def __init__(self, db_url: Optional[str] = None):
        """
        初始化数据库初始化器
        
        Args:
            db_url: 数据库连接URL，默认使用models中定义的URL
        """
        self.db_url = db_url
        self.engine = None
        self.SessionLocal = None
    
    def initialize_database(self) -> bool:
        """
        执行数据库初始化流程
        
        Returns:
            bool: 初始化是否成功
        """
        try:
            # 如果提供了自定义数据库URL，则使用它创建新的引擎
            if self.db_url:
                self.engine = create_engine(
                    self.db_url,
                    connect_args={"check_same_thread": False}
                )
                self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
                # 使用新引擎创建表
                Base.metadata.create_all(bind=self.engine)
            else:
                # 使用默认引擎创建表
                Base.metadata.create_all(bind=engine)
            
            # 创建测试数据（可选）
            self._create_test_data()
            
            return True
        except Exception as e:
            print(f"数据库初始化失败: {e}")
            return False
    
    def _create_test_data(self):
        """
        创建测试数据
        
        仅在开发环境下创建测试数据，生产环境下应禁用
        """
        try:
            # 获取会话
            session = SessionLocal() if self.SessionLocal is None else self.SessionLocal()
            
            # 检查是否已有用户数据
            from models.user import User
            user_count = session.query(User).count()
            
            if user_count == 0:
                # 创建管理员用户
                admin_user = User(
                    username="admin",
                    email="admin@example.com",
                    password=pwd_context.hash("admin123"[:72]),  # 使用哈希密码，限制长度
                    full_name="Admin User",
                    is_active=True,
                    is_admin=True
                )
                session.add(admin_user)
                
                # 创建普通用户
                test_user = User(
                    username="test",
                    email="test@example.com",
                    password=pwd_context.hash("test123"[:72]),  # 使用哈希密码，限制长度
                    full_name="Test User",
                    is_active=True,
                    is_admin=False
                )
                session.add(test_user)
                
                session.commit()
                print("测试用户数据创建成功")
            
            # 检查是否已有仓库数据
            from models.repository import Repository
            repo_count = session.query(Repository).count()
            
            if repo_count == 0:
                # 获取管理员用户
                admin_user = session.query(User).filter(User.username == "admin").first()
                
                # 创建测试仓库1
                test_repo1 = Repository(
                    name="test-repo-1",
                    path="/repos/test-repo-1",
                    description="第一个测试仓库",
                    is_public=True,
                    owner_id=admin_user.id,
                    default_branch="master"
                )
                session.add(test_repo1)
                
                # 创建测试仓库2
                test_repo2 = Repository(
                    name="test-repo-2",
                    path="/repos/test-repo-2",
                    description="第二个测试仓库",
                    is_public=False,
                    owner_id=admin_user.id,
                    default_branch="main"
                )
                session.add(test_repo2)
                
                session.commit()
                print("测试仓库数据创建成功")
                
                # 创建分支数据
                from models.branch import Branch
                for repo in [test_repo1, test_repo2]:
                    # 创建主分支
                    main_branch = Branch(
                        name=repo.default_branch,
                        repository_id=repo.id,
                        is_protected=True,
                        is_default=True
                    )
                    session.add(main_branch)
                    
                    # 创建开发分支
                    dev_branch = Branch(
                        name="develop",
                        repository_id=repo.id,
                        is_protected=False,
                        is_default=False
                    )
                    session.add(dev_branch)
                
                session.commit()
                print("测试分支数据创建成功")
                
                # 创建提交数据
                from models.commit import Commit
                branches = session.query(Branch).all()
                for branch in branches:
                    # 创建初始提交
                    initial_commit = Commit(
                        hash="a" * 40,  # 模拟sha1哈希
                        repository_id=branch.repository_id,
                        branch_id=branch.id,
                        author_name="Admin User",
                        author_email="admin@example.com",
                        committer_name="Admin User",
                        committer_email="admin@example.com",
                        commit_message="Initial commit",
                        parent_hashes=""
                    )
                    session.add(initial_commit)
                
                session.commit()
                print("测试提交数据创建成功")
        except Exception as e:
            session.rollback()
            print(f"创建测试数据失败: {e}")
        finally:
            session.close()


def init_database(db_url: Optional[str] = None) -> bool:
    """
    初始化数据库的便捷函数
    
    Args:
        db_url: 数据库连接URL，默认使用models中定义的URL
    
    Returns:
        bool: 初始化是否成功
    """
    initializer = DatabaseInitializer(db_url)
    return initializer.initialize_database()
