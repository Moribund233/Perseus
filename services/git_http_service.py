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

    # 解析客户端发送的引用更新命令和 packfile
    commands, packfile_data = _parse_receive_pack_data(data)

    if not commands:
        return build_receive_pack_response([])

    # 验证命令权限并执行更新
    results = []
    for cmd in commands:
        result = _process_push_command(repo, cmd, user, packfile_data)
        results.append(result)

    return build_receive_pack_response(results)


def _parse_receive_pack_data(data: bytes) -> Tuple[list, Optional[bytes]]:
    """
    解析 receive-pack 数据，分离命令和 packfile

    Args:
        data: 客户端发送的原始数据

    Returns:
        tuple: (命令列表, packfile数据)
    """
    commands = []
    packfile_start = None

    offset = 0
    while offset < len(data):
        if offset + 4 > len(data):
            break

        try:
            length = int(data[offset:offset+4], 16)
        except ValueError:
            break

        if length == 0:
            offset += 4
            continue

        if length == 4:  # 0000 分隔符
            packfile_start = offset + 4
            break

        line = data[offset+4:offset+length]
        offset += length

        # 解析命令行: old_sha new_sha ref_name
        try:
            line_str = line.decode('utf-8', errors='ignore').strip()
            parts = line_str.split(' ')
            if len(parts) >= 3:
                commands.append({
                    'old_sha': parts[0],
                    'new_sha': parts[1],
                    'ref': parts[2]
                })
        except Exception:
            continue

    packfile = data[packfile_start:] if packfile_start else None
    return commands, packfile


def _process_push_command(
    repo: pygit2.Repository,
    cmd: dict,
    user: User,
    packfile_data: Optional[bytes]
) -> dict:
    """
    处理单个 push 命令

    Args:
        repo: Git 仓库对象
        cmd: 命令字典，包含 old_sha, new_sha, ref
        user: 操作用户
        packfile_data: packfile 数据

    Returns:
        dict: 操作结果
    """
    old_sha = cmd['old_sha']
    new_sha = cmd['new_sha']
    ref_name = cmd['ref']

    result = {
        'old_sha': old_sha,
        'new_sha': new_sha,
        'ref': ref_name,
        'status': 'ok'
    }

    try:
        # 检查引用是否存在
        ref = None
        try:
            ref = repo.lookup_reference(ref_name)
        except KeyError:
            pass

        # 验证 old_sha 是否匹配（防止竞态条件）
        if ref:
            current_sha = str(ref.target)
            if old_sha != '0' * 40 and current_sha != old_sha:
                result['status'] = 'ng refs/heads/main failed to update (non-fast-forward)'
                return result

        # 如果提供了 packfile，先解包
        if packfile_data:
            _unpack_packfile(repo, packfile_data)

        # 执行引用更新
        if new_sha == '0' * 40:
            # 删除引用
            if ref:
                ref.delete()
        else:
            # 创建或更新引用
            new_oid = pygit2.Oid(hex=new_sha)
            if ref:
                ref.set_target(new_oid)
            else:
                repo.create_reference(ref_name, new_oid)

        # 记录 push 日志
        _log_push_operation(repo, user, cmd)

    except Exception as e:
        result['status'] = f'ng {ref_name} {str(e)}'

    return result


def _unpack_packfile(repo: pygit2.Repository, packfile_data: bytes) -> None:
    """
    解包 packfile 数据

    Args:
        repo: Git 仓库对象
        packfile_data: packfile 原始数据

    Raises:
        GitHttpError: 解包失败
    """
    import subprocess
    import tempfile
    import os

    # 创建临时文件存储 packfile
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pack') as tmp_pack:
        tmp_pack.write(packfile_data)
        tmp_pack_path = tmp_pack.name

    try:
        # 使用 git unpack-objects 解包
        result = subprocess.run(
            ['git', 'unpack-objects'],
            input=packfile_data,
            capture_output=True,
            cwd=repo.path
        )

        if result.returncode != 0:
            raise GitHttpError(f"Failed to unpack packfile: {result.stderr.decode()}")

    finally:
        # 清理临时文件
        if os.path.exists(tmp_pack_path):
            os.unlink(tmp_pack_path)


def _log_push_operation(repo: pygit2.Repository, user: User, cmd: dict) -> None:
    """
    记录 push 操作日志

    Args:
        repo: Git 仓库对象
        user: 操作用户
        cmd: push 命令
    """
    import logging
    import os

    logger = logging.getLogger('git.push')

    # 获取仓库名称
    repo_name = os.path.basename(repo.path)

    action = 'delete' if cmd['new_sha'] == '0' * 40 else 'update'

    logger.info(
        f"Push {action}: repo={repo_name}, "
        f"user={user.username if user else 'anonymous'}, "
        f"ref={cmd['ref']}, "
        f"old={cmd['old_sha'][:8]}, "
        f"new={cmd['new_sha'][:8]}"
    )


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
