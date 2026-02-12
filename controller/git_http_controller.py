"""
Git HTTP 协议控制器层

处理 Git Smart HTTP 协议的 HTTP 请求
支持 git clone/push/pull 操作
"""
import base64
from fastapi import APIRouter, Request, Response, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from models.db import get_db
from models.user import User
from services.git_http_service import (
    get_refs,
    process_upload_pack,
    process_receive_pack,
    check_git_permission,
    get_repository_by_path,
    check_repository_exists,
    GitHttpError,
    parse_service_name
)
from exception import NotFoundException, AuthorizationException
from utils.rate_limiter import limiter, RateLimitConfig, get_git_operation_key

# 创建路由实例
router = APIRouter(prefix="/git", tags=["git-http"])


def extract_auth_user(request: Request, db: Session) -> User | None:
    """
    从请求中提取认证用户

    支持 HTTP Basic Auth 和 Token 认证

    Args:
        request: HTTP 请求对象
        db: 数据库会话

    Returns:
        User | None: 认证用户，未认证则返回 None
    """
    auth_header = request.headers.get("Authorization")

    if not auth_header:
        return None

    try:
        # 解析 Basic Auth
        if auth_header.startswith("Basic "):
            encoded = auth_header[6:]
            decoded = base64.b64decode(encoded).decode("utf-8")
            username, password = decoded.split(":", 1)

            # 验证用户
            from services.user_service import authenticate_user
            return authenticate_user(username, password, db)

        # 解析 Token Auth
        elif auth_header.startswith("Bearer "):
            token = auth_header[7:]
            # TODO: 实现 Token 验证
            return None

    except Exception:
        pass

    return None


def check_read_permission(repo_path: str, user: User | None, db: Session) -> None:
    """
    检查读取权限

    Args:
        repo_path: 仓库路径
        user: 用户对象
        db: 数据库会话

    Raises:
        HTTPException: 无权限时抛出 403 或 401
    """
    if not check_git_permission(repo_path, user, "read", db):
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                headers={"WWW-Authenticate": "Basic realm=\"Git\""},
                detail="Authentication required"
            )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied"
        )


def check_write_permission(repo_path: str, user: User | None, db: Session) -> None:
    """
    检查写入权限

    Args:
        repo_path: 仓库路径
        user: 用户对象
        db: 数据库会话

    Raises:
        HTTPException: 无权限时抛出 403 或 401
    """
    if not check_git_permission(repo_path, user, "write", db):
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                headers={"WWW-Authenticate": "Basic realm=\"Git\""},
                detail="Authentication required"
            )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied"
        )


@router.get("/{repo_path:path}/info/refs")
@limiter.limit(RateLimitConfig.GIT_OPERATIONS, key_func=get_git_operation_key)
async def git_refs(
    repo_path: str,
    service: str | None = None,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    Git 引用发现端点

    处理 Git 客户端的引用发现请求，支持 dumb 和 smart HTTP 协议

    Args:
        repo_path: 仓库路径（如 username/repo-name）
        service: 服务类型（git-upload-pack 或 git-receive-pack）
        request: HTTP 请求对象
        db: 数据库会话

    Returns:
        Response: 引用发现响应

    Raises:
        HTTPException: 仓库不存在或无权限
    """
    # 检查仓库是否存在
    if not check_repository_exists(repo_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found"
        )

    # 获取认证用户
    user = extract_auth_user(request, db)

    # 检查权限
    check_read_permission(repo_path, user, db)

    # 如果没有指定服务，返回 dumb HTTP 响应（简单的引用列表）
    if not service:
        refs_data = get_refs(repo_path)
        return Response(
            content=refs_data,
            media_type="text/plain"
        )

    # 解析服务名称
    try:
        service_name = parse_service_name(service)
    except GitHttpError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    # 检查写权限（如果是 receive-pack）
    if service_name == "receive-pack":
        check_write_permission(repo_path, user, db)

    # 生成 smart HTTP 响应
    refs_data = get_refs(repo_path)

    # 构建 smart HTTP 响应头
    service_line = f"001e# service=git-{service_name}\n".encode()
    header = service_line + b"0000"

    content = header + refs_data

    return Response(
        content=content,
        media_type=f"application/x-git-{service_name}-advertisement"
    )


@router.post("/{repo_path:path}/git-upload-pack")
@limiter.limit(RateLimitConfig.GIT_OPERATIONS, key_func=get_git_operation_key)
async def git_upload_pack(
    repo_path: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Git upload-pack 端点

    处理 Git clone/fetch 请求

    Args:
        repo_path: 仓库路径
        request: HTTP 请求对象
        db: 数据库会话

    Returns:
        Response: packfile 数据

    Raises:
        HTTPException: 仓库不存在或无权限
    """
    # 检查仓库是否存在
    if not check_repository_exists(repo_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found"
        )

    # 获取认证用户
    user = extract_auth_user(request, db)

    # 检查读取权限
    check_read_permission(repo_path, user, db)

    # 读取请求体
    body = await request.body()

    try:
        # 处理 upload-pack 请求
        response_data = process_upload_pack(repo_path, body)

        return Response(
            content=response_data,
            media_type="application/x-git-upload-pack-result"
        )

    except NotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found"
        )
    except GitHttpError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/{repo_path:path}/git-receive-pack")
@limiter.limit(RateLimitConfig.GIT_OPERATIONS, key_func=get_git_operation_key)
async def git_receive_pack(
    repo_path: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Git receive-pack 端点

    处理 Git push 请求

    Args:
        repo_path: 仓库路径
        request: HTTP 请求对象
        db: 数据库会话

    Returns:
        Response: 处理结果

    Raises:
        HTTPException: 仓库不存在或无权限
    """
    # 检查仓库是否存在
    if not check_repository_exists(repo_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found"
        )

    # 获取认证用户
    user = extract_auth_user(request, db)

    # 检查写入权限
    check_write_permission(repo_path, user, db)

    # 读取请求体
    body = await request.body()

    try:
        # 处理 receive-pack 请求
        response_data = process_receive_pack(repo_path, body, user)

        return Response(
            content=response_data,
            media_type="application/x-git-receive-pack-result"
        )

    except NotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found"
        )
    except AuthorizationException as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except GitHttpError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/{repo_path:path}/HEAD")
async def git_head(
    repo_path: str,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    获取 HEAD 引用

    用于 dumb HTTP 协议

    Args:
        repo_path: 仓库路径
        request: HTTP 请求对象
        db: 数据库会话

    Returns:
        Response: HEAD 引用内容
    """
    # 检查仓库是否存在
    if not check_repository_exists(repo_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found"
        )

    # 获取认证用户
    user = extract_auth_user(request, db) if request else None

    # 检查读取权限
    check_read_permission(repo_path, user, db)

    from utils.git_utils import get_repository_storage_path
    import os

    physical_path = get_repository_storage_path(repo_path)
    head_path = os.path.join(physical_path, "HEAD")

    if not os.path.exists(head_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="HEAD not found"
        )

    try:
        with open(head_path, "rb") as f:
            content = f.read()
        return Response(content=content, media_type="text/plain")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read HEAD: {e}"
        )


@router.get("/{repo_path:path}/objects/{oid:path}")
async def git_objects(
    repo_path: str,
    oid: str,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    获取 Git 对象

    用于 dumb HTTP 协议

    Args:
        repo_path: 仓库路径
        oid: 对象 ID
        request: HTTP 请求对象
        db: 数据库会话

    Returns:
        Response: 对象内容
    """
    # 检查仓库是否存在
    if not check_repository_exists(repo_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found"
        )

    # 获取认证用户
    user = extract_auth_user(request, db) if request else None

    # 检查读取权限
    check_read_permission(repo_path, user, db)

    from utils.git_utils import get_repository_storage_path
    import os
    import zlib

    physical_path = get_repository_storage_path(repo_path)

    # 构建对象路径（使用松散对象格式）
    if len(oid) >= 2:
        obj_dir = oid[:2]
        obj_file = oid[2:]
        obj_path = os.path.join(physical_path, "objects", obj_dir, obj_file)

        if os.path.exists(obj_path):
            try:
                with open(obj_path, "rb") as f:
                    compressed = f.read()
                    content = zlib.decompress(compressed)
                return Response(content=content, media_type="application/x-git-loose-object")
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to read object: {e}"
                )

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Object not found"
    )
