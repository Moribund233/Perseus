"""
异常处理工具

提供统一的异常处理机制，用于捕获和处理应用中的各种异常
"""
import sys
import traceback
from fastapi import Request
from fastapi.responses import JSONResponse
from exception import (
    BaseException,
    ValidationException,
    AuthenticationException,
    AuthorizationException,
    NotFoundException,
    ConflictException,
    DatabaseException,
    NginxException,
    FileException
)


def _is_debug_mode() -> bool:
    """
    检查是否处于调试模式
    
    从配置文件读取debug设置
    
    Returns:
        bool: 调试模式返回True，生产模式返回False
    """
    try:
        from config import get_config
        config = get_config()
        return getattr(config.app, 'debug', True)
    except Exception:
        # 默认安全：非调试模式
        return False


def _log_exception(exc: Exception, traceback_str: str = None, is_debug: bool = False):
    """
    记录异常信息
    
    根据调试模式决定是否记录堆栈跟踪
    
    Args:
        exc: 异常对象
        traceback_str: 堆栈跟踪字符串（可选）
        is_debug: 是否调试模式
    """
    if is_debug:
        # 调试模式：记录完整堆栈
        if traceback_str is None:
            traceback_str = traceback.format_exc()
        print(f"[ERROR] Exception: {exc}\n{traceback_str}", file=sys.stderr)
    else:
        # 生产模式：只记录简要信息，避免泄露敏感信息
        print(f"[ERROR] {exc.__class__.__name__}: {exc}", file=sys.stderr)


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    全局异常处理器
    
    捕获并处理应用中所有未被捕获的异常
    
    安全特性：
    - 生产环境不返回堆栈跟踪
    - 生产环境返回统一错误信息
    - 敏感错误信息仅记录到日志
    
    Args:
        request: 请求对象
        exc: 异常对象
    
    Returns:
        JSONResponse: 包含错误信息的JSON响应
    """
    is_debug = _is_debug_mode()
    
    # 记录异常（根据模式决定详细程度）
    traceback_str = traceback.format_exc() if is_debug else None
    _log_exception(exc, traceback_str, is_debug)
    
    # 如果是自定义异常，直接返回（生产环境隐藏异常类型）
    if isinstance(exc, BaseException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "detail": exc.detail,
                "error": {
                    "code": exc.status_code,
                    "message": exc.detail,
                    "type": exc.__class__.__name__ if is_debug else "Error"
                }
            }
        )
    
    # 处理其他类型的异常
    # 生产环境返回统一错误信息，不暴露内部细节
    if is_debug:
        # 调试模式：返回详细错误信息
        error_msg = str(exc) if str(exc) else "Internal Server Error"
        error_type = exc.__class__.__name__
    else:
        # 生产模式：返回统一错误信息
        error_msg = "Internal Server Error"
        error_type = "InternalServerError"
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": error_msg if is_debug else "Internal Server Error",
            "error": {
                "code": 500,
                "message": error_msg if is_debug else "Internal Server Error",
                "type": error_type if is_debug else "InternalServerError"
            }
        }
    )


async def http_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    HTTP异常处理器
    
    处理FastAPI内置的HTTPException
    
    Args:
        request: 请求对象
        exc: 异常对象
    
    Returns:
        JSONResponse: 包含错误信息的JSON响应
    """
    from fastapi import HTTPException as FastAPIHTTPException
    if isinstance(exc, FastAPIHTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "detail": exc.detail,
                "error": {
                    "code": exc.status_code,
                    "message": exc.detail,
                    "type": "HTTPException"
                }
            }
        )
    
    # 如果不是FastAPI的HTTPException，交给全局异常处理器处理
    return await global_exception_handler(request, exc)


async def validation_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    验证异常处理器
    
    处理请求参数验证失败的异常
    
    Args:
        request: 请求对象
        exc: 异常对象
    
    Returns:
        JSONResponse: 包含错误信息的JSON响应
    """
    from pydantic import ValidationError
    if isinstance(exc, ValidationError):
        # 提取验证错误详情
        error_details = []
        for error in exc.errors():
            field = ".".join(str(item) for item in error["loc"])
            error_details.append({
                "field": field,
                "message": error["msg"],
                "type": error["type"]
            })
        
        return JSONResponse(
            status_code=400,
            content={
                "detail": "Validation Error",
                "error": {
                    "code": 400,
                    "message": "Validation Error",
                    "type": "ValidationException",
                    "details": error_details
                }
            }
        )
    
    # 如果不是Pydantic的ValidationError，交给全局异常处理器处理
    return await global_exception_handler(request, exc)


def setup_exception_handlers(app):
    """
    设置异常处理器
    
    将所有异常处理器注册到FastAPI应用中
    
    Args:
        app: FastAPI应用实例
    """
    # 注册自定义异常处理器
    app.add_exception_handler(BaseException, global_exception_handler)
    app.add_exception_handler(ValidationException, global_exception_handler)
    app.add_exception_handler(AuthenticationException, global_exception_handler)
    app.add_exception_handler(AuthorizationException, global_exception_handler)
    app.add_exception_handler(NotFoundException, global_exception_handler)
    app.add_exception_handler(ConflictException, global_exception_handler)
    app.add_exception_handler(DatabaseException, global_exception_handler)
    app.add_exception_handler(NginxException, global_exception_handler)
    app.add_exception_handler(FileException, global_exception_handler)
    
    # 注册FastAPI内置异常处理器
    from fastapi import HTTPException as FastAPIHTTPException
    app.add_exception_handler(FastAPIHTTPException, http_exception_handler)
    
    # 注册Pydantic验证异常处理器
    from pydantic import ValidationError
    app.add_exception_handler(ValidationError, validation_exception_handler)
    
    # 注册全局异常处理器
    app.add_exception_handler(Exception, global_exception_handler)
