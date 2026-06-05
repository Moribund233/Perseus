"""
速率限制工具模块

提供速率限制配置的定义，实际限制由反向代理（Nginx）处理。
API 端不再依赖 slowapi。
"""
import logging
from typing import Optional
from core.config import get_config

logger = logging.getLogger(__name__)

# 保持向后兼容：limiter 对象导出（实际已不使用）
limiter = None


def _get_default_limit() -> str:
    """获取默认限流配置字符串"""
    try:
        config = get_config()
        rate_limit = getattr(config, 'rate_limit', None)
        if rate_limit:
            return getattr(rate_limit, 'default_limits', "200 per minute").to_limit_string()
    except Exception:
        pass
    return "200 per minute"


def setup_rate_limiter(app):
    """
    初始化速率限制（当前仅记录日志，实际限制由 Nginx 处理）

    Args:
        app: FastAPI 应用实例
    """
    limit_str = _get_default_limit()
    logger.info(f"Rate limiter configured (enforced by Nginx): {limit_str}")


# 预定义的速率限制配置
class RateLimitConfig:
    """
    速率限制配置类

    提供常用的速率限制配置，从配置文件动态读取
    返回字符串格式用于记录或传递给 Nginx
    """

    _DEFAULTS = {
        'STRICT': "5 per minute",
        'STANDARD': "30 per minute",
        'GENEROUS': "2000 per hour",
        'GIT_OPERATIONS': "10 per minute",
        'DOWNLOAD': "20 per minute"
    }

    @classmethod
    def _get_config_value(cls, key: str, config_attr: str) -> str:
        """
        动态从配置读取限流值

        Args:
            key: 类属性名
            config_attr: 配置中的属性名

        Returns:
            str: 限流配置字符串
        """
        try:
            _config = get_config()
            _rate_limit_config = getattr(_config, 'rate_limit', None)
            if _rate_limit_config:
                rate_limit_item = getattr(_rate_limit_config, config_attr, None)
                if rate_limit_item:
                    return rate_limit_item.to_limit_string()
        except Exception:
            pass
        return cls._DEFAULTS.get(key, "30 per minute")

    @classmethod
    def STRICT(cls) -> str:
        """严格限流配置"""
        return cls._get_config_value('STRICT', 'strict')

    @classmethod
    def STANDARD(cls) -> str:
        """标准限流配置"""
        return cls._get_config_value('STANDARD', 'standard')

    @classmethod
    def GENEROUS(cls) -> str:
        """宽松限流配置"""
        return cls._get_config_value('GENEROUS', 'generous')

    @classmethod
    def GIT_OPERATIONS(cls) -> str:
        """Git 操作限流配置"""
        return cls._get_config_value('GIT_OPERATIONS', 'git_operations')

    @classmethod
    def DOWNLOAD(cls) -> str:
        """下载限流配置"""
        return cls._get_config_value('DOWNLOAD', 'download')


def get_rate_limit_config():
    """
    获取速率限制配置类

    Returns:
        RateLimitConfig: 速率限制配置类
    """
    return RateLimitConfig


def get_git_operation_key(request) -> str:
    """
    获取 Git 操作限流键

    根据用户 IP 或认证用户生成限流键

    Args:
        request: HTTP 请求对象

    Returns:
        str: 限流键
    """
    # 优先使用认证用户
    user = getattr(request.state, "user", None)
    if user:
        return f"git:{user.id}"
    # 使用 IP 地址
    return f"git:{request.client.host if request.client else 'unknown'}"


def create_custom_limiter(limit_str: str):
    """
    创建自定义限流装饰器（已弃用，仅保留接口）

    Args:
        limit_str: 限流配置字符串

    Returns:
        None: 实际限流由 Nginx 处理
    """
    logger.debug(f"Rate limit requested: {limit_str} (enforced by Nginx)")
    return lambda func: func
