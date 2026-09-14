"""
全局异常类定义

定义应用中所有的自定义异常类，用于统一的错误处理
"""
from fastapi import HTTPException, status


class BaseException(HTTPException):
    """
    基础异常类
    
    所有自定义异常的基类，继承自FastAPI的HTTPException。

    `error_code` 是供国际化使用的稳定错误码（如 ``"room_not_found"``），
    与 `detail` 分离，允许异常处理器根据 `Accept-Language` 自动返回
    对应语言的错误消息。未传 `error_code` 时沿用原 `detail`，完全向后兼容。
    """
    def __init__(self,
                 status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
                 detail: str = "Internal Server Error",
                 headers: dict | None = None,
                 error_code: str | None = None):
        super().__init__(
            status_code=status_code,
            detail=detail,
            headers=headers,
        )
        self.error_code = error_code


class ValidationException(BaseException):
    def __init__(self, detail: str = "Validation Error", error_code: str | None = None):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
            error_code=error_code,
        )


class AuthenticationException(BaseException):
    def __init__(self, detail: str = "Authentication Failed", error_code: str | None = None):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
            error_code=error_code,
        )


class AuthorizationException(BaseException):
    def __init__(self, detail: str = "Permission Denied", error_code: str | None = None):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
            error_code=error_code,
        )


class NotFoundException(BaseException):
    def __init__(self, detail: str = "Resource Not Found", error_code: str | None = None):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
            error_code=error_code,
        )


class ConflictException(BaseException):
    def __init__(self, detail: str = "Resource Conflict", error_code: str | None = None):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
            error_code=error_code,
        )


class DatabaseException(BaseException):
    """
    数据库异常

    用于处理数据库操作失败的情况
    """
    def __init__(self, detail: str = "Database Operation Failed", error_code: str | None = None):
        """
        初始化数据库异常

        Args:
            detail: 错误详情
        """
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
            error_code=error_code,
        )


class FileException(BaseException):
    """
    文件操作异常
    
    用于处理文件操作失败的情况
    """
    def __init__(self, detail: str = "File Operation Failed", error_code: str | None = None):
        """
        初始化文件操作异常
        
        Args:
            detail: 错误详情
        """
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
            error_code=error_code,
        )


class RepositoryBrowserException(BaseException):
    """
    仓库浏览异常基类
    
    用于处理仓库浏览相关操作的异常情况
    """
    def __init__(self, detail: str = "Repository Browser Error", error_code: str | None = None):
        """
        初始化仓库浏览异常
        
        Args:
            detail: 错误详情
        """
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
            error_code=error_code,
        )


class RepositoryNotFoundException(RepositoryBrowserException):
    """
    仓库不存在异常

    用于处理请求的仓库不存在的情况
    """
    def __init__(self, detail: str = "Repository Not Found", error_code: str | None = None):
        """
        初始化仓库不存在异常

        Args:
            detail: 错误详情
        """
        # 直接调用 BaseException 的 __init__，避免 RepositoryBrowserException 的参数问题
        BaseException.__init__(
            self,
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
            error_code=error_code,
        )

class PathNotFoundException(RepositoryBrowserException):
    """
    路径不存在异常

    用于处理请求的路径不存在的情况
    """
    def __init__(self, detail: str = "Path Not Found", error_code: str | None = None):
        """
        初始化路径不存在异常

        Args:
            detail: 错误详情
        """
        # 直接调用 BaseException 的 __init__，避免 RepositoryBrowserException 的参数问题
        BaseException.__init__(
            self,
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
            error_code=error_code,
        )

class InvalidPathException(RepositoryBrowserException):
    """
    无效路径异常

    用于处理路径格式无效的情况
    """
    def __init__(self, detail: str = "Invalid Path", error_code: str | None = None):
        """
        初始化无效路径异常

        Args:
            detail: 错误详情
        """
        # 直接调用 BaseException 的 __init__，避免 RepositoryBrowserException 的参数问题
        BaseException.__init__(
            self,
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
            error_code=error_code,
        )

class AppServiceException(BaseException):
    """
    应用服务异常

    用于处理应用服务层操作失败的情况
    """
    def __init__(self,
                 detail: str = "App Service Error",
                 status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
                 error_code: str | None = None):
        """
        初始化应用服务异常

        Args:
            detail: 错误详情
            status_code: HTTP 状态码
        """
        super().__init__(
            status_code=status_code,
            detail=detail,
            error_code=error_code,
        )


class ConfigValidationException(AppServiceException):
    """
    配置验证异常

    用于处理配置数据验证失败的情况
    """
    def __init__(self, detail: str = "Config Validation Error"):
        """
        初始化配置验证异常

        Args:
            detail: 错误详情
        """
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
        )
