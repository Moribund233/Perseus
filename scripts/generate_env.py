#!/usr/bin/env python3
"""
Perseus .env 生成脚本

生成 docker-compose.yml 所需的环境变量文件（.env）。
已存在的变量保留原值，只补全缺失项，可重复执行（幂等）。

用法:
    python scripts/generate_env.py            # 生成/补全 .env
    python scripts/generate_env.py --show     # 生成后打印（密钥脱敏）
    python scripts/generate_env.py --force    # 重新生成所有密钥类变量

生成项:
    PERSEUS_SECURITY_SECRET_KEY   JWT 签名密钥（必需）
    POSTGRES_PASSWORD             PostgreSQL 密码（compose 中 db 服务与 DATABASE_URL 共用）
    PERSEUS_ADMIN_PASSWORD        初始管理员密码
    PERSEUS_COLLAB_INTERNAL_SECRET  协作网关 (collab) 与 app 的服务间共享密钥
    PERSEUS_APP_DEBUG             调试模式（固定 false，可手动改）
    LOG_LEVEL                     日志级别（固定 info，可手动改）
"""
from __future__ import annotations

import argparse
import base64
import re
import secrets
import string
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_ROOT / ".env"

ALPHABET = string.ascii_letters + string.digits + "!@#$%^&*_-+="


def generate_secret(length: int = 64) -> str:
    """生成 URL 安全的随机密钥（用于 JWT 签名等）"""
    return secrets.token_urlsafe(length)


def generate_password(length: int = 20) -> str:
    """生成包含字母/数字/符号的随机密码（避免包含 URL 特殊字符 % 与引号）"""
    safe_alphabet = re.sub(r"[%'\"\\]", "", ALPHABET)
    while True:
        pwd = "".join(secrets.choice(safe_alphabet) for _ in range(length))
        # 保证复杂度：至少含小写、大写、数字
        if (
            any(c.islower() for c in pwd)
            and any(c.isupper() for c in pwd)
            and any(c.isdigit() for c in pwd)
        ):
            return pwd


def random_suffix() -> str:
    return base64.b32encode(secrets.token_bytes(2)).decode().rstrip("=")


# 变量名 -> (生成函数, 说明)
GENERATED_VARS: dict[str, tuple] = {
    "PERSEUS_SECURITY_SECRET_KEY": (lambda: generate_secret(64), "JWT 签名密钥"),
    "POSTGRES_PASSWORD": (lambda: generate_password(), "PostgreSQL 密码"),
    "PERSEUS_ADMIN_PASSWORD": (lambda: generate_password(), "初始管理员密码"),
    "PERSEUS_COLLAB_INTERNAL_SECRET": (lambda: generate_secret(48), "协作网关内部共享密钥"),
}

# 非密钥的默认项（已存在则不覆盖）
DEFAULT_VARS: dict[str, str] = {
    "PERSEUS_APP_DEBUG": "false",
    "LOG_LEVEL": "info",
}


def parse_env(text: str) -> dict[str, str]:
    """解析 .env 文本为字典（忽略注释与空行，保留首次出现的键）"""
    result: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        result.setdefault(key.strip(), value.strip().strip("'\""))
    return result


def serialize_env(env: dict[str, str], comments: dict[str, str] | None = None) -> str:
    comments = comments or {}
    lines = [
        "# Perseus 环境变量（由 scripts/generate_env.py 生成）",
        "# 密钥类变量缺失时自动生成；已存在的值不会被覆盖。",
        "",
    ]
    for key, value in env.items():
        if key in comments:
            lines.append(f"# {comments[key]}")
        lines.append(f"{key}={value}")
    lines.append("")
    return "\n".join(lines)


def mask(value: str) -> str:
    if len(value) <= 8:
        return "****"
    return value[:4] + "****" + value[-4:]


def main() -> int:
    parser = argparse.ArgumentParser(description="生成 Perseus .env 文件")
    parser.add_argument("--show", action="store_true", help="输出变量概览（密钥脱敏）")
    parser.add_argument("--force", action="store_true", help="重新生成所有密钥类变量")
    args = parser.parse_args()

    existing: dict[str, str] = {}
    if ENV_FILE.exists():
        existing = parse_env(ENV_FILE.read_text(encoding="utf-8"))

    env: dict[str, str] = {}
    comments: dict[str, str] = {}

    for key, (factory, desc) in GENERATED_VARS.items():
        if args.force or not existing.get(key):
            env[key] = factory()
            comments[key] = f"{desc}（自动生成）"
            if args.force:
                comments[key] = f"{desc}（重新生成）"
        else:
            env[key] = existing[key]
            comments[key] = f"{desc}（沿用已有值）"

    for key, value in DEFAULT_VARS.items():
        env[key] = existing.get(key, value)

    with open(ENV_FILE, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(serialize_env(env, comments))
    print(f"[OK] 已写入 {ENV_FILE}")

    if args.show:
        print("-" * 56)
        for key, value in env.items():
            display = mask(value) if key in GENERATED_VARS else value
            print(f"{key}={display}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
