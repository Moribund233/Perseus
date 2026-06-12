"""
Alembic 迁移环境配置

通过 DATABASE_URL 环境变量连接数据库（与应用的配置方式一致）。
运行方式:
    alembic upgrade head          # 升级到最新
    alembic downgrade -1          # 回退一步
    alembic revision --autogenerate -m "描述"  # 自动生成迁移
"""
import os
import sys
from logging.config import fileConfig

from sqlalchemy import create_engine, pool

from alembic import context

# 将项目根目录加入 sys.path，确保可以导入 models
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入模型 metadata
from models import Base
target_metadata = Base.metadata

# Alembic Config 对象
config = context.config



def _to_sync_database_url(db_url: str) -> str:
    """将异步 DATABASE_URL 转为 Alembic 可用的同步 SQLAlchemy URL。"""
    if db_url.startswith('postgresql+asyncpg://'):
        return db_url.replace('postgresql+asyncpg://', 'postgresql://', 1)
    if db_url.startswith('sqlite+aiosqlite://'):
        path = db_url.removeprefix('sqlite+aiosqlite://')
        if path.startswith('/') and not path.startswith('/.'):
            # 绝对路径需要 4 个斜杠: sqlite:////absolute/path
            return f'sqlite:///{path}'
        # 相对路径: sqlite:///./file.db
        return f'sqlite:///{path.lstrip("/")}'
    return db_url

# 从环境变量读取 DATABASE_URL（与应用保持一致）
db_url = os.environ.get("DATABASE_URL")
if db_url:
    # Alembic 需要同步驱动，将异步驱动转换为同步驱动
    # sqlite+aiosqlite -> sqlite
    # postgresql+asyncpg -> postgresql
    sync_url = _to_sync_database_url(db_url)
    config.set_main_option("sqlalchemy.url", sync_url)

# 日志配置
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def run_migrations_offline() -> None:
    """离线模式运行迁移（生成 SQL 脚本，不连接数据库）"""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """在线模式运行迁移（直接连接数据库执行）"""
    url = config.get_main_option("sqlalchemy.url")
    if not url:
        raise RuntimeError(
            "Database URL not configured. Set DATABASE_URL or sqlalchemy.url in alembic.ini."
        )

    connectable = create_engine(url, poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # SQLite 需要 batch 模式来支持 ALTER TABLE
            render_as_batch=connection.dialect.name == "sqlite",
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
