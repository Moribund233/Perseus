"""
错误API路由

提供用于测试和演示异常处理机制的API端点
"""
from fastapi import APIRouter
from exception import (
    ValidationException,
    AuthenticationException,
    AuthorizationException,
    NotFoundException,
    ConflictException,
    DatabaseException,
    NginxException,
    FileException
)

# 创建路由实例
router = APIRouter(prefix="/api/errors", tags=["errors"])


@router.get("/validation")
async def validation_error():
    """
    测试验证异常
    
    Returns:
        None: 抛出ValidationException
    """
    raise ValidationException(detail="Invalid request parameters")


@router.get("/authentication")
async def authentication_error():
    """
    测试认证异常
    
    Returns:
        None: 抛出AuthenticationException
    """
    raise AuthenticationException(detail="Authentication failed: Invalid credentials")


@router.get("/authorization")
async def authorization_error():
    """
    测试授权异常
    
    Returns:
        None: 抛出AuthorizationException
    """
    raise AuthorizationException(detail="Permission denied: Insufficient privileges")


@router.get("/not-found")
async def not_found_error():
    """
    测试资源不存在异常
    
    Returns:
        None: 抛出NotFoundException
    """
    raise NotFoundException(detail="Resource not found: ID does not exist")


@router.get("/conflict")
async def conflict_error():
    """
    测试资源冲突异常
    
    Returns:
        None: 抛出ConflictException
    """
    raise ConflictException(detail="Resource conflict: Duplicate entry")


@router.get("/database")
async def database_error():
    """
    测试数据库异常
    
    Returns:
        None: 抛出DatabaseException
    """
    raise DatabaseException(detail="Database error: Connection failed")


@router.get("/nginx")
async def nginx_error():
    """
    测试Nginx异常
    
    Returns:
        None: 抛出NginxException
    """
    raise NginxException(detail="Nginx error: Configuration failed")


@router.get("/file")
async def file_error():
    """
    测试文件操作异常
    
    Returns:
        None: 抛出FileException
    """
    raise FileException(detail="File error: Permission denied")


@router.get("/server")
async def server_error():
    """
    测试服务器内部错误
    
    Returns:
        None: 抛出未捕获的异常
    """
    # 故意抛出一个未捕获的异常
    raise Exception("Unexpected server error")


@router.get("/division-by-zero")
async def division_by_zero():
    """
    测试除零错误
    
    Returns:
        None: 抛出除零异常
    """
    # 故意引发除零异常
    1 / 0
