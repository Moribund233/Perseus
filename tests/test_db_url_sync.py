"""
同步数据库 URL 归一化测试

回归保护：SQLAlchemy 2.1 起 `postgresql://` 的默认 DBAPI 变为 psycopg3，
而本项目依赖 psycopg2，因此同步/迁移路径必须显式固定 `postgresql+psycopg2://`。
（`alembic/env.py` 的同名转换无法在测试中直接导入，其行为由迁移流程覆盖。）
"""
from utils.db_migrate import _to_sync_db_url as migrate_url
from utils.init_database import _to_sync_db_url as init_url


PG = "postgresql://u:p@h:5432/d"
PG_ASYNC = "postgresql+asyncpg://u:p@h:5432/d"
SQLITE_ASYNC = "sqlite+aiosqlite:///./x.db"


def test_db_migrate_postgres_normalized():
    assert migrate_url(PG) == "postgresql+psycopg2://u:p@h:5432/d"
    assert migrate_url(PG_ASYNC) == "postgresql+psycopg2://u:p@h:5432/d"
    assert migrate_url("postgres://u:p@h:5432/d") == "postgresql+psycopg2://u:p@h:5432/d"


def test_db_migrate_sqlite_and_other_untouched():
    assert migrate_url(SQLITE_ASYNC) == "sqlite:///./x.db"
    assert migrate_url("sqlite:///./x.db") == "sqlite:///./x.db"


def test_init_database_postgres_normalized():
    assert init_url(PG) == "postgresql+psycopg2://u:p@h:5432/d"
    assert init_url(PG_ASYNC) == "postgresql+psycopg2://u:p@h:5432/d"
    assert init_url(SQLITE_ASYNC) == "sqlite:///./x.db"
