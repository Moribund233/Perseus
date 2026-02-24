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

# 限流器实例（延迟初始化）
limiter = None


def _get_rate_limit_config():
    """获取限流配置"""
    try:
        _config = get_config()
        _rate_limit_config = getattr(_config, 'rate_limit', None)
        if _rate_limit_config:
            return {
                'default_limits': getattr(_rate_limit_config, 'default_limits', ["200 per minute", "1000 per hour"]),
                'strict': getattr(_rate_limit_config, 'strict', ["5 per minute", "20 per hour"]),
                'standard': getattr(_rate_limit_config, 'standard', ["30 per minute", "500 per hour"]),
                'generous': getattr(_rate_limit_config, 'generous', ["100 per minute", "2000 per hour"]),
                'git_operations': getattr(_rate_limit_config, 'git_operations', ["10 per minute", "100 per hour"]),
                'download': getattr(_rate_limit_config, 'download', ["20 per minute", "200 per hour"])
            }
    except Exception as e:
        logger.warning(f"Failed to load rate limit config: {e}")
    return None


def get_limiter() -> Limiter:
    """
    获取速率限制器实例

    Returns:
        Limiter: 速率限制器实例
    """
    global limiter
    if limiter is None:
        # 延迟初始化，确保配置已加载
        config = _get_rate_limit_config()
        default_limits = config['default_limits'] if config else ["200 per minute", "1000 per hour"]
        limiter = Limiter(
            key_func=get_remote_address,
            default_limits=default_limits
        )
        logger.info(f"Rate limiter created with limits: {default_limits}")
    return limiter


def setup_rate_limiter(app):
    """
    在 FastAPI 应用中设置速率限制

    Args:
        app: FastAPI 应用实例
    """
    global limiter
    
    # 获取或创建限流器实例
    _limiter = get_limiter()
    
    # 将限制器状态附加到应用
    app.state.limiter = _limiter

    # 添加速率限制异常处理器
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    logger.info("Rate limiter initialized")


# 预定义的速率限制配置
class RateLimitConfig:
    """
    速率限制配置类

    提供常用的速率限制配置，从配置文件动态读取
    返回逗号分隔的字符串格式，兼容 slowapi
    """

    # 默认值（当配置不可用时使用）
    _DEFAULTS = {
        'STRICT': "5 per minute, 20 per hour",
        'STANDARD': "30 per minute, 500 per hour",
        'GENEROUS': "100 per minute, 2000 per hour",
        'GIT_OPERATIONS': "10 per minute, 100 per hour",
        'DOWNLOAD': "20 per minute, 200 per hour"
    }

    @classmethod
    def _get_config_value(cls, key: str, config_key: str) -> str:
        """
        动态从配置读取限流值

        Args:
            key: 类属性名
            config_key: 配置中的键名

        Returns:
            str: 限流配置字符串
        """
        try:
            _config = get_config()
            _rate_limit_config = getattr(_config, 'rate_limit', None)
            if _rate_limit_config:
                limits = getattr(_rate_limit_config, config_key, None)
                if limits:
                    return cls._format_limit(limits)
        except Exception:
            pass
        return cls._DEFAULTS.get(key, "30 per minute, 500 per hour")

    @staticmethod
    def _format_limit(limits) -> str:
        """
        将限制配置格式化为 slowapi 兼容的字符串

        Args:
            limits: 列表或字符串

        Returns:
            str: 逗号分隔的限制字符串
        """
        if isinstance(limits, str):
            return limits
        if isinstance(limits, list):
            return ", ".join(limits)
        return str(limits)

    @classmethod
    @property
    def STRICT(cls) -> str:
        """严格限流配置"""
        return cls._get_config_value('STRICT', 'strict')

    @classmethod
    @property
    def STANDARD(cls) -> str:
        """标准限流配置"""
        return cls._get_config_value('STANDARD', 'standard')

    @classmethod
    @property
    def GENEROUS(cls) -> str:
        """宽松限流配置"""
        return cls._get_config_value('GENEROUS', 'generous')

    @classmethod
    @property
    def GIT_OPERATIONS(cls) -> str:
        """Git 操作限流配置"""
        return cls._get_config_value('GIT_OPERATIONS', 'git_operations')

    @classmethod
    @property
    def DOWNLOAD(cls) -> str:
        """下载限流配置"""
        return cls._get_config_value('DOWNLOAD', 'download')


# 为了保持向后兼容，提供函数式接口
def get_rate_limit_config():
    """
    获取速率限制配置类

    Returns:
        RateLimitConfig: 速率限制配置类
    """
    return RateLimitConfig


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
