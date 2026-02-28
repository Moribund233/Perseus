"""
异常处理工具

提供统一的异常处理机制，用于捕获和处理应用中的各种异常
"""
import logging
import traceback
from fastapi import Request
from fastapi.responses import JSONResponse
from core.exception import (
    BaseException,
    ValidationException,
    AuthenticationException,
    AuthorizationException,
    NotFoundException,
    ConflictException,
    DatabaseException,
    FileException,
    RepositoryBrowserException,
    RepositoryNotFoundException,
    PathNotFoundException,
    InvalidPathException
)
from utils.logging import get_named_logger

# 创建异常日志记录器
logger = get_named_logger("exception")


def _is_debug_mode() -> bool:
    """检查是否处于调试模式"""
    try:
        from core.config import get_config
        config = get_config()
        return getattr(config.app, 'debug', True)
    except Exception:
        return False


def _log_exception(exc: Exception, is_debug: bool = False):
    """
    记录异常信息

    所有模式（调试/生产）：
    - error.log：记录简化信息 + 完整堆栈跟踪
    - 控制台：只输出简化信息，避免堆栈跟踪刷屏
    """
    exc_type = exc.__class__.__name__
    exc_msg = str(exc) if str(exc) else "Unknown error"

    # 获取完整堆栈跟踪
    tb_str = traceback.format_exc()

    # 记录简化信息（写入 error.log）
    logger.error(f"{exc_type}: {exc_msg}")

    # 将堆栈跟踪记录到 error.log（所有模式都记录，便于排查问题）
    for handler in logger.handlers:
        if isinstance(handler, logging.FileHandler):
            # 只记录到 error 日志文件（通过检查文件名）
            if "error" in handler.baseFilename.lower():
                handler.emit(logging.LogRecord(
                    name=logger.name,
                    level=logging.ERROR,
                    pathname="",
                    lineno=0,
                    msg=f"Stack trace:\n{tb_str}",
                    args=(),
                    exc_info=None
                ))
            # 注意：异步日志不需要手动 flush，QueueListener 会自动处理


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    全局异常处理器

    捕获并处理应用中所有未被捕获的异常
    """
    is_debug = _is_debug_mode()

    # 记录异常
    _log_exception(exc, is_debug)

    # 如果是自定义异常，直接返回
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

    # 处理仓库浏览器异常
    if isinstance(exc, RepositoryBrowserException):
        return _handle_browser_error(exc, is_debug)

    # 处理其他类型的异常
    if is_debug:
        error_msg = str(exc) if str(exc) else "Internal Server Error"
        error_type = exc.__class__.__name__
    else:
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


def _handle_browser_error(exc: RepositoryBrowserException, is_debug: bool = False) -> JSONResponse:
    """处理仓库浏览器异常"""
    if isinstance(exc, RepositoryNotFoundException):
        status_code = 404
    elif isinstance(exc, PathNotFoundException):
        status_code = 404
    elif isinstance(exc, InvalidPathException):
        status_code = 400
    else:
        status_code = 500

    error_msg = str(exc)
    error_type = exc.__class__.__name__ if is_debug else "RepositoryBrowserException"

    return JSONResponse(
        status_code=status_code,
        content={
            "detail": error_msg,
            "error": {
                "code": status_code,
                "message": error_msg,
                "type": error_type
            }
        }
    )


async def http_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """HTTP异常处理器"""
    from fastapi import HTTPException as FastAPIHTTPException
    if isinstance(exc, FastAPIHTTPException):
        # 记录HTTP异常（4xx客户端错误使用warning，5xx服务器错误使用error）
        if exc.status_code >= 500:
            logger.error(f"HTTP {exc.status_code}: {exc.detail}")
        elif exc.status_code >= 400:
            logger.warning(f"HTTP {exc.status_code}: {exc.detail}")

        # 构建响应头，包含原始异常的 headers（如 WWW-Authenticate）
        headers = exc.headers if exc.headers else {}

        return JSONResponse(
            status_code=exc.status_code,
            headers=headers,
            content={
                "detail": exc.detail,
                "error": {
                    "code": exc.status_code,
                    "message": exc.detail,
                    "type": "HTTPException"
                }
            }
        )

    return await global_exception_handler(request, exc)


async def validation_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """验证异常处理器"""
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

        # 记录验证错误
        logger.warning(f"Validation Error: {error_details}")

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

    return await global_exception_handler(request, exc)


async def builtin_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Python 内置异常处理器

    处理 ValueError、AttributeError、TypeError 等 Python 内置异常
    防止这些异常未被捕获而导致控制台输出堆栈跟踪
    """
    is_debug = _is_debug_mode()

    # 记录异常
    _log_exception(exc, is_debug)

    # 根据异常类型确定状态码
    status_code = 500
    if isinstance(exc, (ValueError, TypeError)):
        status_code = 400

    if is_debug:
        error_msg = str(exc) if str(exc) else "Internal Server Error"
        error_type = exc.__class__.__name__
    else:
        error_msg = "Internal Server Error"
        error_type = "InternalServerError"

    return JSONResponse(
        status_code=status_code,
        content={
            "detail": error_msg if is_debug else "Internal Server Error",
            "error": {
                "code": status_code,
                "message": error_msg if is_debug else "Internal Server Error",
                "type": error_type if is_debug else "InternalServerError"
            }
        }
    )


def setup_exception_handlers(app):
    """设置异常处理器"""
    # 注册 Python 内置异常处理器（最先注册，确保能捕获这些常见异常）
    app.add_exception_handler(ValueError, builtin_exception_handler)
    app.add_exception_handler(AttributeError, builtin_exception_handler)
    app.add_exception_handler(TypeError, builtin_exception_handler)
    app.add_exception_handler(KeyError, builtin_exception_handler)
    app.add_exception_handler(ZeroDivisionError, builtin_exception_handler)

    # 注册自定义异常处理器
    app.add_exception_handler(BaseException, global_exception_handler)
    app.add_exception_handler(ValidationException, global_exception_handler)
    app.add_exception_handler(AuthenticationException, global_exception_handler)
    app.add_exception_handler(AuthorizationException, global_exception_handler)
    app.add_exception_handler(NotFoundException, global_exception_handler)
    app.add_exception_handler(ConflictException, global_exception_handler)
    app.add_exception_handler(DatabaseException, global_exception_handler)
    app.add_exception_handler(FileException, global_exception_handler)

    # 注册仓库浏览器异常处理器
    app.add_exception_handler(RepositoryBrowserException, global_exception_handler)
    app.add_exception_handler(RepositoryNotFoundException, global_exception_handler)
    app.add_exception_handler(PathNotFoundException, global_exception_handler)
    app.add_exception_handler(InvalidPathException, global_exception_handler)

    # 注册FastAPI内置异常处理器
    from fastapi import HTTPException as FastAPIHTTPException
    app.add_exception_handler(FastAPIHTTPException, http_exception_handler)

    # 注册Pydantic验证异常处理器
    from pydantic import ValidationError
    app.add_exception_handler(ValidationError, validation_exception_handler)

    # 注册全局异常处理器（最后注册，作为兜底）
    app.add_exception_handler(Exception, global_exception_handler)
