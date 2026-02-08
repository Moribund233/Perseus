"""
速率限制工具

提供基于 slowapi 的速率限制功能，防止暴力破解和 DDoS 攻击
"""
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, Response
from typing import Optional, Callable
import logging

from config import get_config

# 日志记录器
logger = logging.getLogger(__name__)


# 获取速率限制配置
_config = get_config()
_rate_limit_config = getattr(_config, 'rate_limit', None)

# 使用配置或默认值
_default_limits = getattr(_rate_limit_config, 'default_limits', ["200 per minute", "1000 per hour"]) if _rate_limit_config else ["200 per minute", "1000 per hour"]

# 创建速率限制器实例
# 使用客户端 IP 作为标识
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=_default_limits
)


def get_limiter() -> Limiter:
    """
    获取速率限制器实例

    Returns:
        Limiter: 速率限制器实例
    """
    return limiter


def setup_rate_limiter(app):
    """
    在 FastAPI 应用中设置速率限制

    Args:
        app: FastAPI 应用实例
    """
    # 将限制器状态附加到应用
    app.state.limiter = limiter

    # 添加速率限制异常处理器
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    logger.info("Rate limiter initialized")


# 预定义的速率限制配置
class RateLimitConfig:
    """
    速率限制配置类

    提供常用的速率限制配置，从配置文件读取或使用默认值
    支持类属性访问和实例属性访问
    """

    # 类属性默认值
    STRICT = ["5 per minute", "20 per hour"]
    STANDARD = ["30 per minute", "500 per hour"]
    GENEROUS = ["100 per minute", "2000 per hour"]
    GIT_OPERATIONS = ["10 per minute", "100 per hour"]
    DOWNLOAD = ["20 per minute", "200 per hour"]

    def __init__(self):
        """初始化，从配置读取或使用默认值"""
        _config = get_config()
        _rate_limit_config = getattr(_config, 'rate_limit', None)

        # 严格限制 - 用于敏感操作（登录、认证等）
        self.STRICT = getattr(_rate_limit_config, 'strict', ["5 per minute", "20 per hour"]) if _rate_limit_config else ["5 per minute", "20 per hour"]

        # 标准限制 - 用于普通 API
        self.STANDARD = getattr(_rate_limit_config, 'standard', ["30 per minute", "500 per hour"]) if _rate_limit_config else ["30 per minute", "500 per hour"]

        # 宽松限制 - 用于读取操作
        self.GENEROUS = getattr(_rate_limit_config, 'generous', ["100 per minute", "2000 per hour"]) if _rate_limit_config else ["100 per minute", "2000 per hour"]

        # Git 操作限制 - 用于 Git HTTP 端点
        self.GIT_OPERATIONS = getattr(_rate_limit_config, 'git_operations', ["10 per minute", "100 per hour"]) if _rate_limit_config else ["10 per minute", "100 per hour"]

        # 下载限制 - 用于文件下载
        self.DOWNLOAD = getattr(_rate_limit_config, 'download', ["20 per minute", "200 per hour"]) if _rate_limit_config else ["20 per minute", "200 per hour"]


# 创建单例实例
_rate_limit_config_instance = None


def get_rate_limit_config() -> RateLimitConfig:
    """
    获取速率限制配置实例

    Returns:
        RateLimitConfig: 速率限制配置实例
    """
    global _rate_limit_config_instance
    if _rate_limit_config_instance is None:
        _rate_limit_config_instance = RateLimitConfig()
    return _rate_limit_config_instance


# 自定义 key 函数
def get_user_key(request: Request) -> str:
    """
    基于用户 ID 的速率限制 key 函数

    如果用户已认证，使用用户 ID；否则使用 IP 地址

    Args:
        request: HTTP 请求对象

    Returns:
        str: 速率限制 key
    """
    # 尝试获取用户 ID
    if hasattr(request.state, "user") and request.state.user:
        user_id = getattr(request.state.user, "id", None)
        if user_id:
            return f"user:{user_id}"

    # 回退到 IP 地址
    return get_remote_address(request)


def get_git_operation_key(request: Request) -> str:
    """
    Git 操作速率限制 key 函数

    结合仓库路径和用户标识

    Args:
        request: HTTP 请求对象

    Returns:
        str: 速率限制 key
    """
    # 获取仓库路径
    path = request.url.path

    # 提取仓库路径（如 /git/user/repo.git/info/refs）
    parts = path.strip("/").split("/")
    if len(parts) >= 3:
        repo_path = f"{parts[1]}/{parts[2]}"
    else:
        repo_path = "unknown"

    # 获取用户标识
    user_key = get_user_key(request)

    return f"git:{repo_path}:{user_key}"


def create_custom_limiter(
    limits: list,
    key_func: Optional[Callable] = None,
    per_method: bool = False,
    exempt_when: Optional[Callable] = None
):
    """
    创建自定义速率限制装饰器

    Args:
        limits: 限制规则列表
        key_func: 自定义 key 函数
        per_method: 是否按 HTTP 方法分别限制
        exempt_when: 豁免条件函数

    Returns:
        callable: 速率限制装饰器
    """
    return limiter.limit(
        ",".join(limits),
        key_func=key_func or get_remote_address,
        per_method=per_method,
        exempt_when=exempt_when
    )
