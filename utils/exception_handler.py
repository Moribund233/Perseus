"""
异常处理工具

提供统一的异常处理机制，用于捕获和处理应用中的各种异常
"""
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


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    全局异常处理器
    
    捕获并处理应用中所有未被捕获的异常
    
    Args:
        request: 请求对象
        exc: 异常对象
    
    Returns:
        JSONResponse: 包含错误信息的JSON响应
    """
    # 记录完整的异常堆栈信息
    traceback_str = traceback.format_exc()
    print(f"[ERROR] Global Exception: {exc}\n{traceback_str}")
    
    # 如果是自定义异常，直接返回
    if isinstance(exc, BaseException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "detail": exc.detail,
                "error": {
                    "code": exc.status_code,
                    "message": exc.detail,
                    "type": exc.__class__.__name__
                }
            }
        )
    
    # 处理其他类型的异常
    error_msg = "Internal Server Error"
    return JSONResponse(
        status_code=500,
        content={
            "detail": error_msg,
            "error": {
                "code": 500,
                "message": error_msg,
                "type": "InternalServerError"
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
