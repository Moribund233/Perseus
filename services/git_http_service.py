"""
Git HTTP 协议服务层

处理 Git Smart HTTP 协议相关的业务逻辑
支持 git clone/push/pull 操作
"""
import os
import re
import zlib
from typing import Optional, Tuple
from sqlalchemy.orm import Session
import pygit2

from exception import NotFoundException, AuthorizationException
from models import Repository, User
from models.repository_member import RepositoryMember
from client.utils.git_utils import get_repository_storage_path, repo_exists


class GitHttpError(Exception):
    """Git HTTP 协议错误"""
    pass


def get_repo_physical_path(repo_path: str) -> str:
    """
    获取仓库的物理存储路径

    Args:
        repo_path: 仓库路径（如 username/repo-name）

    Returns:
        str: 物理存储路径
    """
    return get_repository_storage_path(repo_path)


def check_repository_exists(repo_path: str) -> bool:
    """
    检查仓库是否存在

    Args:
        repo_path: 仓库路径

    Returns:
        bool: 仓库是否存在
    """
    physical_path = get_repo_physical_path(repo_path)
    return repo_exists(physical_path)


def get_repository_by_path(repo_path: str, db: Session) -> Optional[Repository]:
    """
    根据路径获取仓库

    Args:
        repo_path: 仓库路径（如 username/repo-name）
        db: 数据库会话

    Returns:
        Repository: 仓库对象，不存在则返回 None
    """
    # 尝试直接匹配路径
    repo = db.query(Repository).filter(Repository.path == repo_path).first()
    if repo:
        return repo

    # 尝试匹配 /{username}/{repo_name} 格式
    parts = repo_path.strip('/').split('/')
    if len(parts) >= 2:
        # 查找用户
        username = parts[0]
        repo_name = parts[1]
        user = db.query(User).filter(User.username == username).first()
        if user:
            # 查找该用户拥有的仓库
            repo = db.query(Repository).filter(
                Repository.owner_id == user.id,
                Repository.name == repo_name
            ).first()
            if repo:
                return repo

    return None


def check_git_permission(repo_path: str, user: Optional[User], action: str, db: Session) -> bool:
    """
    检查用户是否有 Git 操作权限

    Args:
        repo_path: 仓库路径
        user: 用户对象，None 表示匿名用户
        action: 操作类型，"read" 或 "write"
        db: 数据库会话

    Returns:
        bool: 是否有权限
    """
    repo = get_repository_by_path(repo_path, db)
    if not repo:
        return False

    # 公开仓库允许任何人读取
    if repo.is_public and action == "read":
        return True

    # 匿名用户只能访问公开仓库
    if not user:
        return False

    # 仓库所有者拥有所有权限
    if repo.owner_id == user.id:
        return True

    # 检查成员权限
    member = db.query(RepositoryMember).filter(
        RepositoryMember.repository_id == repo.id,
        RepositoryMember.user_id == user.id
    ).first()

    if not member or not member.is_active:
        return False

    if action == "read":
        return True
    elif action == "write":
        # 只有 maintainer 和 owner 角色可以写入
        return member.role in ["maintainer", "owner"]

    return False


def get_refs(repo_path: str) -> bytes:
    """
    获取仓库的引用列表（用于引用发现）

    Args:
        repo_path: 仓库路径

    Returns:
        bytes: 引用数据

    Raises:
        NotFoundException: 仓库不存在
    """
    physical_path = get_repo_physical_path(repo_path)

    if not repo_exists(physical_path):
        raise NotFoundException(detail="Repository not found")

    try:
        repo = pygit2.Repository(physical_path)
    except Exception as e:
        raise GitHttpError(f"Failed to open repository: {e}")

    refs = []

    # 添加 HEAD 引用
    try:
        head = repo.head
        if head.type == pygit2.GIT_REF_SYMBOLIC:
            refs.append((b"HEAD", head.target.encode()))
        else:
            refs.append((b"HEAD", str(head.target).encode()))
    except Exception:
        # HEAD 可能不存在或无效
        pass

    # 添加所有引用
    for ref_name in repo.listall_references():
        try:
            ref = repo.lookup_reference(ref_name)
            if ref.type == pygit2.GIT_REF_OID:
                refs.append((ref_name.encode(), str(ref.target).encode()))
        except Exception:
            continue

    # 构建引用发现包
    return build_refs_discovery(refs)


def build_refs_discovery(refs: list) -> bytes:
    """
    构建 Git 引用发现包

    Args:
        refs: 引用列表，每个元素是 (name, sha) 元组

    Returns:
        bytes: 引用发现数据
    """
    if not refs:
        return b"0000"

    lines = []
    for i, (name, sha) in enumerate(refs):
        if i == 0:
            # 第一个引用包含能力声明
            line = sha + b" " + name + b"\0side-band-64k shallow deepen-since deepen-not deepen-relative multi_ack_detailed no-done symref=HEAD:refs/heads/master agent=langit/0.1.0\n"
        else:
            line = sha + b" " + name + b"\n"

        # 计算长度（4位十六进制）
        length = len(line) + 4
        hex_length = format(length, "04x").encode()
        lines.append(hex_length + line)

    # 结束标记
    lines.append(b"0000")

    return b"".join(lines)


def process_upload_pack(repo_path: str, data: bytes) -> bytes:
    """
    处理 git-upload-pack 请求（clone/fetch）

    Args:
        repo_path: 仓库路径
        data: 客户端发送的数据

    Returns:
        bytes: 响应数据

    Raises:
        NotFoundException: 仓库不存在
        GitHttpError: 处理失败
    """
    physical_path = get_repo_physical_path(repo_path)

    if not repo_exists(physical_path):
        raise NotFoundException(detail="Repository not found")

    try:
        repo = pygit2.Repository(physical_path)
    except Exception as e:
        raise GitHttpError(f"Failed to open repository: {e}")

    # 解析客户端请求
    want_refs = []
    have_refs = []
    capabilities = set()

    # 解析 pkt-line 格式
    offset = 0
    while offset < len(data):
        if offset + 4 > len(data):
            break

        # 读取长度
        try:
            length = int(data[offset:offset+4], 16)
        except ValueError:
            break

        if length == 0:
            offset += 4
            continue

        if length < 4 or offset + length > len(data):
            break

        line = data[offset+4:offset+length]
        offset += length

        # 解析命令
        if line.startswith(b"want "):
            parts = line[5:].split(b" ", 1)
            sha = parts[0].decode().strip()
            want_refs.append(sha)
            if len(parts) > 1:
                caps = parts[1].decode().strip()
                capabilities.update(caps.split())
        elif line.startswith(b"have "):
            sha = line[5:].decode().strip()
            have_refs.append(sha)
        elif line == b"done":
            break

    # 生成 packfile
    try:
        pack_data = generate_packfile(repo, want_refs, have_refs)
        return pack_data
    except Exception as e:
        raise GitHttpError(f"Failed to generate packfile: {e}")


def process_receive_pack(repo_path: str, data: bytes, user: User) -> bytes:
    """
    处理 git-receive-pack 请求（push）

    Args:
        repo_path: 仓库路径
        data: 客户端发送的数据
        user: 操作用户

    Returns:
        bytes: 响应数据

    Raises:
        NotFoundException: 仓库不存在
        GitHttpError: 处理失败
        AuthorizationException: 无权限
    """
    physical_path = get_repo_physical_path(repo_path)

    if not repo_exists(physical_path):
        raise NotFoundException(detail="Repository not found")

    try:
        repo = pygit2.Repository(physical_path)
    except Exception as e:
        raise GitHttpError(f"Failed to open repository: {e}")

    # TODO: 实现接收 packfile 和更新引用
    # 这里需要解析 packfile 并更新引用

    # 返回成功响应
    return build_receive_pack_response([])


def generate_packfile(repo: pygit2.Repository, want_refs: list, have_refs: list) -> bytes:
    """
    生成 packfile 数据

    Args:
        repo: Git 仓库对象
        want_refs: 客户端想要的引用
        have_refs: 客户端已有的引用

    Returns:
        bytes: packfile 数据
    """
    # 收集需要发送的对象
    objects_to_send = set()

    # 获取想要的提交
    for ref in want_refs:
        try:
            commit = repo.revparse_single(ref)
            # 收集此提交及其所有祖先
            walker = repo.walk(commit.id, pygit2.GIT_SORT_TOPOLOGICAL)

            # 如果客户端有某些提交，停止遍历
            if have_refs:
                have_oids = {pygit2.Oid(hex=h) for h in have_refs}
                for c in walker:
                    if c.id in have_oids:
                        break
                    objects_to_send.add(c.id)
                    # 添加树对象
                    objects_to_send.add(c.tree_id)
                    # 添加父提交
                    for parent_id in c.parent_ids:
                        objects_to_send.add(parent_id)
            else:
                for c in walker:
                    objects_to_send.add(c.id)
                    objects_to_send.add(c.tree_id)
                    for parent_id in c.parent_ids:
                        objects_to_send.add(parent_id)

        except Exception:
            continue

    # 如果没有对象需要发送，返回空响应
    if not objects_to_send:
        return b"0008NAK\n0000"

    # 构建 packfile（简化版本，使用 side-band-64k）
    return build_packfile_response(repo, objects_to_send)


def build_packfile_response(repo: pygit2.Repository, objects: set) -> bytes:
    """
    构建包含 packfile 的响应

    Args:
        repo: Git 仓库对象
        objects: 对象 ID 集合

    Returns:
        bytes: 响应数据
    """
    # 使用 git pack-objects 命令生成 packfile
    import subprocess
    import tempfile

    # 创建对象列表
    obj_list = "\n".join(str(oid) for oid in objects)

    try:
        # 使用 git pack-objects 生成 packfile
        result = subprocess.run(
            ["git", "pack-objects", "--stdout", "--delta-base-offset"],
            input=obj_list,
            capture_output=True,
            text=True,
            cwd=repo.path,
            encoding='utf-8',
            errors='ignore'
        )

        if result.returncode != 0:
            # 如果 git 命令失败，返回 NAK
            return b"0008NAK\n0000"

        pack_data = result.stdout.encode('latin-1') if isinstance(result.stdout, str) else result.stdout

        # 使用 side-band-64k 编码
        return encode_sideband(pack_data)

    except Exception as e:
        # 如果失败，返回 NAK
        return b"0008NAK\n0000"


def encode_sideband(data: bytes, channel: int = 1) -> bytes:
    """
    使用 side-band-64k 编码数据

    Args:
        data: 原始数据
        channel: 通道号（1=数据，2=进度信息，3=错误信息）

    Returns:
        bytes: 编码后的数据
    """
    MAX_CHUNK = 65520  # 64k - 16 留一些余量
    chunks = []

    # 添加 NAK 响应
    chunks.append(b"0008NAK\n")

    for i in range(0, len(data), MAX_CHUNK):
        chunk = data[i:i + MAX_CHUNK]
        # 添加通道字节
        framed = bytes([channel]) + chunk
        # 添加长度前缀
        length = len(framed) + 4
        hex_length = format(length, "04x").encode()
        chunks.append(hex_length + framed)

    # 添加结束标记
    chunks.append(b"0000")

    return b"".join(chunks)


def build_receive_pack_response(results: list) -> bytes:
    """
    构建 receive-pack 响应

    Args:
        results: 操作结果列表

    Returns:
        bytes: 响应数据
    """
    lines = []

    for result in results:
        old_sha = result.get("old_sha", "0" * 40)
        new_sha = result.get("new_sha", "0" * 40)
        ref = result.get("ref", "")
        status = result.get("status", "ok")

        if status == "ok":
            line = f"{old_sha} {new_sha} {ref}\n".encode()
        else:
            line = f"{old_sha} {new_sha} {ref} {status}\n".encode()

        length = len(line) + 4
        hex_length = format(length, "04x").encode()
        lines.append(hex_length + line)

    # 添加结束标记
    lines.append(b"0000")

    return b"".join(lines)


def parse_service_name(service: str) -> str:
    """
    解析服务名称

    Args:
        service: 服务参数值

    Returns:
        str: 服务名称

    Raises:
        GitHttpError: 无效的服务名称
    """
    if not service.startswith("git-"):
        raise GitHttpError("Invalid service name")

    service_name = service[4:]  # 去掉 "git-" 前缀
    if service_name not in ["upload-pack", "receive-pack"]:
        raise GitHttpError("Unsupported service")

    return service_name
