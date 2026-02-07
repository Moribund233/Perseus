# 模型初始化模块
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

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

__all__ = ["Base", "SessionLocal", "engine", "BaseModel", "User"]
