"""
错误处理路由

提供统一的错误信息获取接口，支持根据配置输出不同详细程度的错误信息
"""
from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse
from typing import Optional
from pydantic import BaseModel

from config import get_config
from api.dependencies import get_current_user

# 创建路由实例
router = APIRouter(prefix="/api/errors", tags=["errors"])


class ErrorInfoResponse(BaseModel):
    """错误信息响应模型"""
    code: int
    message: str
    type: str
    details: Optional[str] = None
    traceback: Optional[str] = None
    timestamp: str
    path: Optional[str] = None
    request_id: Optional[str] = None


class ErrorLogEntry(BaseModel):
    """错误日志条目"""
    id: str
    timestamp: str
    code: int
    type: str
    message: str
    path: Optional[str] = None
    user_id: Optional[int] = None


def _should_show_details(is_authenticated: bool = False) -> bool:
    """
    根据配置和认证状态决定是否显示详细错误信息
    
    Args:
        is_authenticated: 用户是否已认证
        
    Returns:
        bool: 是否显示详细信息
    """
    config = get_config()
    
    # 调试模式始终显示详细信息
    if config.app.debug:
        return True
    
    # 生产环境下，认证用户可以查看详细信息
    # 可以根据需要扩展为仅管理员可见
    return is_authenticated


@router.get("/info/{error_code}", response_model=ErrorInfoResponse)
async def get_error_info(
    error_code: int,
    request: Request,
    message: Optional[str] = None,
    error_type: Optional[str] = None,
    details: Optional[str] = None,
    request_id: Optional[str] = None,
    current_user: Optional[dict] = Depends(get_current_user)
):
    """
    获取错误详细信息
    
    根据配置和用户权限返回不同详细程度的错误信息
    
    Args:
        error_code: HTTP 错误状态码
        message: 错误消息
        error_type: 错误类型
        details: 错误详情
        request_id: 请求ID
        current_user: 当前用户信息（可选）
        
    Returns:
        ErrorInfoResponse: 错误信息响应
    """
    from datetime import datetime
    
    config = get_config()
    is_authenticated = current_user is not None
    show_details = _should_show_details(is_authenticated)
    
    # 构建基础响应
    response = ErrorInfoResponse(
        code=error_code,
        message=message or _get_default_message(error_code),
        type=error_type or "UnknownError",
        timestamp=datetime.now().isoformat(),
        path=str(request.url.path) if request else None,
        request_id=request_id
    )
    
    # 根据权限添加详细信息
    if show_details:
        response.details = details
        # 调试模式下可以包含堆栈跟踪（如果提供）
        if config.app.debug and details:
            response.traceback = details
    
    return response


@router.get("/recent", response_model=list[ErrorLogEntry])
async def get_recent_errors(
    limit: int = 10,
    current_user: dict = Depends(get_current_user)
):
    """
    获取最近的错误日志（仅管理员可用）
    
    Args:
        limit: 返回条目数量限制
        current_user: 当前用户信息
        
    Returns:
        list[ErrorLogEntry]: 错误日志列表
    """
    # TODO: 实现错误日志存储和查询
    # 这里返回空列表作为占位
    return []


@router.post("/report")
async def report_error(
    error_data: dict,
    request: Request,
    current_user: Optional[dict] = Depends(get_current_user)
):
    """
    接收前端报告的错误
    
    用于前端捕获到未处理的错误时上报给服务端
    
    Args:
        error_data: 错误数据
        request: 请求对象
        current_user: 当前用户信息（可选）
        
    Returns:
        dict: 处理结果
    """
    from datetime import datetime
    import logging
    
    logger = logging.getLogger(__name__)
    
    # 记录前端错误
    error_info = {
        "timestamp": datetime.now().isoformat(),
        "user_agent": request.headers.get("user-agent"),
        "client_ip": request.client.host if request.client else None,
        "user_id": current_user.get("id") if current_user else None,
        "error": error_data
    }
    
    logger.error(f"Frontend error reported: {error_info}")
    
    return {"status": "received", "message": "Error reported successfully"}


def _get_default_message(error_code: int) -> str:
    """
    根据错误码获取默认错误消息
    
    Args:
        error_code: HTTP 状态码
        
    Returns:
        str: 默认错误消息
    """
    messages = {
        400: "请求错误",
        401: "未授权",
        403: "禁止访问",
        404: "页面未找到",
        408: "请求超时",
        409: "资源冲突",
        500: "服务器内部错误",
        502: "网关错误",
        503: "服务不可用",
        504: "网关超时"
    }
    return messages.get(error_code, "未知错误")


# 保留测试端点，但仅在调试模式下可用
@router.get("/test/{error_type}")
async def test_error(error_type: str):
    """
    测试错误处理（仅调试模式可用）
    
    Args:
        error_type: 错误类型
        
    Returns:
        None: 抛出对应异常
    """
    config = get_config()
    
    # 生产环境禁用测试端点
    if not config.app.debug:
        from exception import NotFoundException
        raise NotFoundException(detail="Test endpoints are disabled in production")
    
    from exception import (
        ValidationException,
        AuthenticationException,
        AuthorizationException,
        NotFoundException,
        ConflictException,
        DatabaseException
    )
    
    error_map = {
        "validation": ValidationException,
        "authentication": AuthenticationException,
        "authorization": AuthorizationException,
        "not-found": NotFoundException,
        "conflict": ConflictException,
        "database": DatabaseException
    }
    
    exc_class = error_map.get(error_type)
    if exc_class:
        raise exc_class(detail=f"Test {error_type} error")
    else:
        raise NotFoundException(detail=f"Unknown error type: {error_type}")
