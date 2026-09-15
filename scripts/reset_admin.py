#!/usr/bin/env python3
"""运维脚本：重设管理员密码。

设计为在应用容器内运行（复用其数据库配置）:
  docker compose run --rm --no-deps app python scripts/reset_admin.py '<新密码>'
或直接指定:
  python scripts/reset_admin.py '<新密码>'

未传密码时从环境变量 PERSEUS_ADMIN_PASSWORD 读取。
管理员用户名取 PERSEUS_ADMIN_USERNAME（默认 admin）。

退出码:
  0  成功
  1  失败（未提供密码 / 用户不存在 / 数据库错误）
"""
import argparse
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def main() -> int:
    parser = argparse.ArgumentParser(description="重设 Perseus 管理员密码")
    parser.add_argument("password", nargs="?", help="新密码（缺省时使用 PERSEUS_ADMIN_PASSWORD）")
    args = parser.parse_args()

    password = args.password or os.environ.get("PERSEUS_ADMIN_PASSWORD")
    if not password:
        print("错误: 未提供新密码，请作为参数传入或设置 PERSEUS_ADMIN_PASSWORD", file=sys.stderr)
        return 1

    from utils.logging import init_logging, get_named_logger

    init_logging(
        log_dir="logs",
        app_name="reset-admin",
        level="info",
        console_output=True,
        use_date_directory=True,
        separate_error_log=True,
        websocket_output=False,
    )
    logger = get_named_logger("reset-admin")
    from core.config import ConfigManager
    from utils.init_database import DatabaseInitializer

    ConfigManager("config.toml")
    initializer = DatabaseInitializer()

    if initializer.reset_admin_password(password):
        logger.info("管理员密码已重置（用户见 PERSEUS_ADMIN_USERNAME）")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())