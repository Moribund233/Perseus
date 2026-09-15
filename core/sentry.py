"""
Sentry 错误监控集成（F-053 监控集成）

根据配置初始化 Sentry SDK，服务端异常自动上报。

设计要点:
- 未配置 ``sentry.dsn`` 时完全跳过，不导入 sentry-sdk（启动零开销）
- 延迟导入 ``sentry_sdk``，即使依赖未安装也不阻塞应用启动
- ``environment`` 按 debug 自动推导，也可通过配置显式覆盖
- 集成 Starlette ASGI 中间件，配合 FastAPI 请求上下文上报
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# 进程内初始化标记: 避免重复 init / 重复导入
_initialized: bool = False
_enabled: bool = False


def sentry_enabled() -> bool:
    """当前进程是否已启用 Sentry"""
    return _enabled


def reset_sentry() -> None:
    """重置进程内状态（用于测试）"""
    global _initialized, _enabled
    _initialized = False
    _enabled = False


def init_sentry(config) -> bool:
    """
    根据配置初始化 Sentry SDK。

    Args:
        config: 全局 Config 对象（读取 config.sentry / config.app.debug）

    Returns:
        bool: 是否已启用 Sentry
    """
    global _initialized, _enabled

    # 已初始化过则幂等返回
    if _initialized:
        return _enabled

    sentry_settings = config.sentry
    dsn = (sentry_settings.dsn or "").strip()

    # 未配置 DSN: 跳过，不产生任何开销
    if not dsn:
        _initialized = True
        _enabled = False
        logger.info("Sentry 未启用：未配置 PERSEUS_SENTRY_DSN")
        return False

    # 延迟导入，未安装 sentry-sdk 时降级为禁用
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration
    except ImportError:
        _initialized = True
        _enabled = False
        logger.warning("Sentry DSN 已配置但 sentry-sdk 未安装，跳过初始化")
        return False

    environment = sentry_settings.environment or (
        "development" if config.app.debug else "production"
    )
    release = sentry_settings.release or None

    sentry_sdk.init(
        dsn=dsn,
        traces_sample_rate=sentry_settings.traces_sample_rate,
        environment=environment,
        release=release,
        send_default_pii=False,
        integrations=[
            StarletteIntegration(transaction_style="endpoint"),
            FastApiIntegration(transaction_style="endpoint"),
            LoggingIntegration(level=logging.WARNING, event_level=logging.ERROR),
        ],
    )

    _initialized = True
    _enabled = True
    logger.info("Sentry 已启用（environment=%s）", environment)
    return True


def sentry_middleware(app):
    """
    包装 ASGI 应用为 Sentry 请求中间件。

    未启用或未安装 sentry-sdk 时原样返回，保证链路无感。
    """
    if not _enabled:
        return app

    try:
        from sentry_sdk.integrations.starlette import SentryAsgiMiddleware
    except ImportError:
        return app

    return SentryAsgiMiddleware(app)