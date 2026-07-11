"""LFS 指针文件解析和生成工具"""
from dataclasses import dataclass


LFS_POINTER_VERSION = "https://git-lfs.github.com/spec/v1"
REQUIRED_FIELDS = {"version", "oid", "size"}


@dataclass
class LFSPointer:
    """LFS 指针文件数据"""
    version: str
    oid: str
    size: int
    extras: dict[str, str] | None = None


def parse_pointer(content: str) -> LFSPointer:
    """
    解析 LFS 指针文件内容

    Args:
        content: 指针文件内容

    Returns:
        LFSPointer: 解析后的指针数据

    Raises:
        ValueError: 指针文件格式无效
    """
    if not content or not content.strip():
        raise ValueError("Empty pointer content")

    lines = content.strip().split("\n")
    fields: dict[str, str] = {}
    extras: dict[str, str] = {}

    for line in lines:
        if " " not in line:
            continue
        key, value = line.split(" ", 1)
        if key in REQUIRED_FIELDS:
            fields[key] = value
        else:
            extras[key] = value

    missing = REQUIRED_FIELDS - set(fields.keys())
    if missing:
        raise ValueError(f"Missing required field: {', '.join(missing)}")

    if fields["version"] != LFS_POINTER_VERSION:
        raise ValueError(f"Invalid LFS pointer version: {fields['version']}")

    try:
        size = int(fields["size"])
    except ValueError:
        raise ValueError(f"Invalid size: {fields['size']}")

    return LFSPointer(
        version=fields["version"],
        oid=fields["oid"],
        size=size,
        extras=extras if extras else None,
    )


def create_pointer(oid: str, size: int) -> str:
    """
    生成 LFS 指针文件内容

    Args:
        oid: 对象 ID (sha256:xxx)
        size: 文件大小

    Returns:
        str: 指针文件内容
    """
    return f"version {LFS_POINTER_VERSION}\noid {oid}\nsize {size}\n"


def is_lfs_pointer(content: str) -> bool:
    """
    判断内容是否为 LFS 指针文件

    Args:
        content: 文件内容

    Returns:
        bool: 是否为 LFS 指针
    """
    if not content:
        return False

    try:
        parse_pointer(content)
        return True
    except ValueError:
        return False
