"""
全局异常类定义

定义应用中所有的自定义异常类，用于统一的错误处理
"""
from fastapi import HTTPException, status


class BaseException(HTTPException):
    """
    基础异常类
    
    所有自定义异常的基类，继承自FastAPI的HTTPException
    """
    def __init__(self,
                 status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
                 detail: str = "Internal Server Error",
                 headers: dict = None):
        """
        初始化基础异常
        
        Args:
            status_code: HTTP状态码
            detail: 错误详情
            headers: 响应头
        """
        super().__init__(
            status_code=status_code,
            detail=detail,
            headers=headers
        )


class ValidationException(BaseException):
    """
    验证异常
    
    用于处理请求参数验证失败的情况
    """
    def __init__(self, detail: str = "Validation Error"):
        """
        初始化验证异常
        
        Args:
            detail: 错误详情
        """
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail
        )


class AuthenticationException(BaseException):
    """
    认证异常
    
    用于处理用户认证失败的情况
    """
    def __init__(self, detail: str = "Authentication Failed"):
        """
        初始化认证异常
        
        Args:
            detail: 错误详情
        """
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"}
        )


class AuthorizationException(BaseException):
    """
    授权异常
    
    用于处理用户权限不足的情况
    """
    def __init__(self, detail: str = "Permission Denied"):
        """
        初始化授权异常
        
        Args:
            detail: 错误详情
        """
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail
        )


class NotFoundException(BaseException):
    """
    资源不存在异常
    
    用于处理请求的资源不存在的情况
    """
    def __init__(self, detail: str = "Resource Not Found"):
        """
        初始化资源不存在异常
        
        Args:
            detail: 错误详情
        """
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail
        )


class ConflictException(BaseException):
    """
    资源冲突异常
    
    用于处理资源冲突的情况，如重复创建
    """
    def __init__(self, detail: str = "Resource Conflict"):
        """
        初始化资源冲突异常
        
        Args:
            detail: 错误详情
        """
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail
        )


class DatabaseException(BaseException):
    """
    数据库异常
    
    用于处理数据库操作失败的情况
    """
    def __init__(self, detail: str = "Database Operation Failed"):
        """
        初始化数据库异常
        
        Args:
            detail: 错误详情
        """
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail
        )


class NginxException(BaseException):
    """
    Nginx异常
    
    用于处理Nginx相关操作失败的情况
    """
    def __init__(self, detail: str = "Nginx Operation Failed"):
        """
        初始化Nginx异常
        
        Args:
            detail: 错误详情
        """
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail
        )


class FileException(BaseException):
    """
    文件操作异常
    
    用于处理文件操作失败的情况
    """
    def __init__(self, detail: str = "File Operation Failed"):
        """
        初始化文件操作异常
        
        Args:
            detail: 错误详情
        """
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail
        )


class RepositoryBrowserException(BaseException):
    """
    仓库浏览异常基类
    
    用于处理仓库浏览相关操作的异常情况
    """
    def __init__(self, detail: str = "Repository Browser Error"):
        """
        初始化仓库浏览异常
        
        Args:
            detail: 错误详情
        """
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail
        )


class RepositoryNotFoundException(RepositoryBrowserException):
    """
    仓库不存在异常
    
    用于处理请求的仓库不存在的情况
    """
    def __init__(self, detail: str = "Repository Not Found"):
        """
        初始化仓库不存在异常
        
        Args:
            detail: 错误详情
        """
        # 直接调用 BaseException 以设置正确的状态码
        BaseException.__init__(
            self,
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail
        )


class PathNotFoundException(RepositoryBrowserException):
    """
    路径不存在异常
    
    用于处理请求的路径不存在的情况
    """
    def __init__(self, detail: str = "Path Not Found"):
        """
        初始化路径不存在异常
        
        Args:
            detail: 错误详情
        """
        # 直接调用 BaseException 以设置正确的状态码
        BaseException.__init__(
            self,
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail
        )


class InvalidPathException(RepositoryBrowserException):
    """
    无效路径异常
    
    用于处理路径格式无效的情况
    """
    def __init__(self, detail: str = "Invalid Path"):
        """
        初始化无效路径异常
        
        Args:
            detail: 错误详情
        """
        # 直接调用 BaseException 以设置正确的状态码
        BaseException.__init__(
            self,
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail
        )
