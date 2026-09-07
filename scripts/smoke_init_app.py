"""非 pytest 冒烟: 生产路径 init_app (dotenv 加载 + admin 引导 + 建表)"""
import asyncio

from core.init import init_app

ok = init_app()
print("init_app:", ok)
assert ok, "init_app 失败"

import sqlalchemy as sa

engine = sa.create_engine("sqlite:////tmp/smoke_init.db")
tables = sa.inspect(engine).get_table_names()
print("tables:", sorted(tables)[:6])
assert "users" in tables, "users 表未创建"


async def main():
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy import text

    aengine = create_async_engine("sqlite+aiosqlite:////tmp/smoke_init.db")
    async with aengine.connect() as conn:
        row = (
            await conn.execute(
                text("SELECT username, email, is_admin FROM users WHERE is_admin = 1")
            )
        ).fetchall()
    await aengine.dispose()
    print("admins:", row)
    assert row, "admin 未引导创建"


asyncio.run(main())
print("SMOKE OK")
