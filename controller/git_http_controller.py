"""
Git HTTP 协议控制器层

处理 Git Smart HTTP 协议的 HTTP 请求
通过调用 git http-backend 实现，支持 git clone/push/pull 操作

URL 格式：
    http://host/git/{username}/{repo-name}
    
注意：URL 不需要 .git 后缀
"""
import base64
from fastapi import APIRouter, Request, Response, Depends, HTTPException, status
from sqlalchemy.orm import Session

from models.db import get_db
from models.user import User
from services.git_http_service import (
    check_git_permission,
    get_repository_by_path,
    check_repository_exists,
    parse_service_name,
    GitHttpError,
    get_git_backend_service,
    GitHttpBackendError
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

    # 解析 Basic Auth
    if auth_header.startswith("Basic "):
        encoded = auth_header[6:]
        try:
            decoded = base64.b64decode(encoded).decode("utf-8")
            username, password = decoded.split(":", 1)
        except (base64.binascii.Error, UnicodeDecodeError, ValueError):
            # 无效的 Basic Auth 格式
            return None

        # 验证用户
        from services.user_service import authenticate_user
        return authenticate_user(username, password, db)

    # 解析 Token Auth
    elif auth_header.startswith("Bearer "):
        token = auth_header[7:]
        # TODO: 实现 Token 验证
        return None

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


def resolve_repository(repo_path: str, db: Session):
    """
    解析仓库路径并验证仓库是否存在

    Args:
        repo_path: 仓库路径（如 username/repo-name）
        db: 数据库会话

    Returns:
        Repository: 仓库对象

    Raises:
        HTTPException: 仓库不存在时抛出 404
    """
    from models.repository import Repository

    repo = get_repository_by_path(repo_path, db)
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found"
        )

    # 检查物理仓库是否存在
    if not check_repository_exists(repo.path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found"
        )

    return repo


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

    处理 Git 客户端的引用发现请求，支持 smart HTTP 协议
    支持带或不带 .git 后缀的路径

    Args:
        repo_path: 仓库路径（如 username/repo-name 或 username/repo-name.git）
        service: 服务类型（git-upload-pack 或 git-receive-pack）
        request: HTTP 请求对象
        db: 数据库会话

    Returns:
        Response: 引用发现响应

    Raises:
        HTTPException: 仓库不存在或无权限
    """
    # 获取认证用户（先认证，不管仓库是否存在）
    user = extract_auth_user(request, db)

    # 解析服务名称（如果有）
    service_name = None
    if service:
        try:
            service_name = parse_service_name(service)
        except GitHttpError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )

    # 确保仓库存在于数据库中（用于权限检查）
    repo = get_repository_by_path(repo_path, db)
    if not repo:
        # 仓库不存在，但先检查是否需要认证
        # 如果不存在且未认证，返回 401（让客户端有机会用认证重试）
        # 如果不存在但已认证，返回 404
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                headers={"WWW-Authenticate": "Basic realm=\"Git\""},
                detail="Authentication required"
            )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found"
        )

    # 根据服务类型检查不同的权限
    if service_name == "receive-pack":
        # git-receive-pack 需要写权限
        check_write_permission(repo_path, user, db)
    else:
        # 默认或 git-upload-pack 需要读权限
        check_read_permission(repo_path, user, db)

    # 检查物理仓库是否存在
    if not check_repository_exists(repo.path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found"
        )

    # 调用 git http-backend 处理请求
    try:
        backend_service = get_git_backend_service()
        status_code, headers, body = await backend_service.handle_request(
            repo_path=repo.path,
            request=request,
            body=None,
            remote_user=user.username if user else None
        )
        
        # 构建 FastAPI 响应
        response_headers = {}
        
        # 转发重要的响应头
        for header_name in ['Content-Type', 'Cache-Control', 'Pragma', 'Expires']:
            if header_name in headers:
                response_headers[header_name] = headers[header_name]
        
        # 如果没有 Content-Type，根据服务设置默认值
        if 'Content-Type' not in response_headers:
            if service:
                response_headers['Content-Type'] = f'application/x-git-{service_name}-advertisement'
            else:
                response_headers['Content-Type'] = 'text/plain'
        
        return Response(
            content=body,
            status_code=status_code,
            headers=response_headers
        )
        
    except NotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found"
        )
    except GitHttpBackendError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Git backend error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
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
    支持带或不带 .git 后缀的路径

    Args:
        repo_path: 仓库路径（支持 .git 后缀）
        request: HTTP 请求对象
        db: 数据库会话

    Returns:
        Response: packfile 数据

    Raises:
        HTTPException: 仓库不存在或无权限
    """
    # 解析仓库并验证存在性
    repo = resolve_repository(repo_path, db)

    # 获取认证用户
    user = extract_auth_user(request, db)

    # 检查读取权限
    check_read_permission(repo_path, user, db)

    # 读取请求体
    body = await request.body()

    try:
        # 调用 git http-backend 处理请求
        backend_service = get_git_backend_service()
        status_code, headers, response_body = await backend_service.handle_request(
            repo_path=repo.path,
            request=request,
            body=body,
            remote_user=user.username if user else None
        )
        
        # 构建响应头
        response_headers = {}
        for header_name in ['Content-Type', 'Cache-Control']:
            if header_name in headers:
                response_headers[header_name] = headers[header_name]
        
        if 'Content-Type' not in response_headers:
            response_headers['Content-Type'] = 'application/x-git-upload-pack-result'
        
        return Response(
            content=response_body,
            status_code=status_code,
            headers=response_headers
        )
        
    except NotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found"
        )
    except GitHttpBackendError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Git backend error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
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
    支持带或不带 .git 后缀的路径

    Args:
        repo_path: 仓库路径（支持 .git 后缀）
        request: HTTP 请求对象
        db: 数据库会话

    Returns:
        Response: 处理结果

    Raises:
        HTTPException: 仓库不存在或无权限
    """
    # 解析仓库并验证存在性
    repo = resolve_repository(repo_path, db)

    # 获取认证用户
    user = extract_auth_user(request, db)

    # 检查写入权限
    check_write_permission(repo_path, user, db)

    # 读取请求体
    body = await request.body()

    try:
        # 调用 git http-backend 处理请求
        backend_service = get_git_backend_service()
        status_code, headers, response_body = await backend_service.handle_request(
            repo_path=repo.path,
            request=request,
            body=body,
            remote_user=user.username if user else None
        )
        
        # 构建响应头
        response_headers = {}
        for header_name in ['Content-Type', 'Cache-Control']:
            if header_name in headers:
                response_headers[header_name] = headers[header_name]
        
        if 'Content-Type' not in response_headers:
            response_headers['Content-Type'] = 'application/x-git-receive-pack-result'
        
        return Response(
            content=response_body,
            status_code=status_code,
            headers=response_headers
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
    except GitHttpBackendError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Git backend error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
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
    支持带或不带 .git 后缀的路径

    Args:
        repo_path: 仓库路径（支持 .git 后缀）
        request: HTTP 请求对象
        db: 数据库会话

    Returns:
        Response: HEAD 引用内容
    """
    # 解析仓库并验证存在性
    repo = resolve_repository(repo_path, db)

    # 获取认证用户
    user = extract_auth_user(request, db) if request else None

    # 检查读取权限
    check_read_permission(repo_path, user, db)

    try:
        # 调用 git http-backend 处理请求
        backend_service = get_git_backend_service()
        status_code, headers, body = await backend_service.handle_request(
            repo_path=repo.path,
            request=request,
            body=None,
            remote_user=user.username if user else None
        )
        
        response_headers = {}
        for header_name in ['Content-Type', 'Cache-Control']:
            if header_name in headers:
                response_headers[header_name] = headers[header_name]
        
        return Response(
            content=body,
            status_code=status_code,
            headers=response_headers
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get HEAD: {str(e)}"
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
    支持带或不带 .git 后缀的路径

    Args:
        repo_path: 仓库路径（支持 .git 后缀）
        oid: 对象 ID
        request: HTTP 请求对象
        db: 数据库会话

    Returns:
        Response: 对象内容
    """
    # 解析仓库并验证存在性
    repo = resolve_repository(repo_path, db)

    # 获取认证用户
    user = extract_auth_user(request, db) if request else None

    # 检查读取权限
    check_read_permission(repo_path, user, db)

    try:
        # 调用 git http-backend 处理请求
        backend_service = get_git_backend_service()
        status_code, headers, body = await backend_service.handle_request(
            repo_path=repo.path,
            request=request,
            body=None,
            remote_user=user.username if user else None
        )
        
        response_headers = {}
        for header_name in ['Content-Type', 'Cache-Control']:
            if header_name in headers:
                response_headers[header_name] = headers[header_name]
        
        return Response(
            content=body,
            status_code=status_code,
            headers=response_headers
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get object: {str(e)}"
        )
