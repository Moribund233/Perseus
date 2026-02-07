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
