"""
异常处理工具

提供统一的异常处理机制，用于捕获和处理应用中的各种异常
"""
import traceback
from fastapi import Request
from fastapi.responses import JSONResponse
from core.exception import BaseException
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

    记录完整堆栈跟踪。日志系统通过处理器分离：
    - app.log (INFO 及以下): 含简化信息
    - error.log (WARNING 及以上): 含完整堆栈跟踪
    """
    exc_type = exc.__class__.__name__
    exc_msg = str(exc) if str(exc) else "Unknown error"

    # 简化信息 + 完整堆栈跟踪（均以 ERROR 级别记录）
    # error.log（WARNING 及以上）会自动接收，app.log 的过滤器会跳过
    logger.error(f"{exc_type}: {exc_msg}\n{traceback.format_exc()}")


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    全局异常处理器

    捕获并处理应用中所有未被捕获的异常。

    自定义异常（继承自 BaseException）已在其 __init__ 中设置了正确的
    status_code，因此无需按子类分别映射状态码。
    """
    is_debug = _is_debug_mode()

    # 记录异常
    _log_exception(exc, is_debug)

    # 如果是自定义异常，直接使用异常中设定的 HTTP 状态码返回
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
    """设置异常处理器

    FastAPI 的异常处理器按继承链自动匹配：
    注册 BaseException 即可覆盖所有继承自它的子类，无需逐一注册。
    """
    # 注册 Python 内置异常处理器（最先注册，确保能捕获这些常见异常）
    app.add_exception_handler(ValueError, builtin_exception_handler)
    app.add_exception_handler(AttributeError, builtin_exception_handler)
    app.add_exception_handler(TypeError, builtin_exception_handler)
    app.add_exception_handler(KeyError, builtin_exception_handler)
    app.add_exception_handler(ZeroDivisionError, builtin_exception_handler)

    # 注册自定义异常根处理器
    # 所有继承自 BaseException 的子类（含 RepositoryBrowserException 体系）
    # 会自动由此处理器处理，无需为每个子类单独注册。
    app.add_exception_handler(BaseException, global_exception_handler)

    # 注册FastAPI内置异常处理器
    from fastapi import HTTPException as FastAPIHTTPException
    app.add_exception_handler(FastAPIHTTPException, http_exception_handler)

    # 注册Pydantic验证异常处理器
    from pydantic import ValidationError
    app.add_exception_handler(ValidationError, validation_exception_handler)

    # 注册全局异常处理器（最后注册，作为兜底）
    app.add_exception_handler(Exception, global_exception_handler)
