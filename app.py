import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI

from core.init import init_app

# 注意：logger 和 config 的导入被延迟到 create_app() 内部
# 以确保 init_app() 先执行环境变量检查


def create_app(config_path: str = "config.toml") -> FastAPI:
    """
    创建FastAPI应用实例

    注意：CORS 由 Nginx 反向代理统一处理，不在应用层配置。
    无论是开发环境还是生产环境，都通过 Nginx 处理跨域。

    Args:
        config_path: 配置文件路径

    Returns:
        FastAPI: FastAPI应用实例
    """
    # 延迟导入所有可能触发 config/models 加载的模块
    # 确保 init_app() 先执行环境变量检查
    from core.lifespan import app_lifespan
    from core.config import get_config
    from utils.logging import get_logger

    # 获取 logger
    logger = get_logger("app")

    # 获取配置
    config = get_config(config_path)

    # 创建FastAPI应用实例，使用lifespan管理生命周期
    app = FastAPI(
        title=config.app.title,
        description=config.app.description,
        version=config.app.version,
        debug=config.app.debug,
        lifespan=app_lifespan
    )

    # 添加并发限制中间件（最先添加，保护服务免受过多并发请求影响）
    from middleware.concurrency import ConcurrencyMiddleware
    conc = config.concurrency
    app.add_middleware(
        ConcurrencyMiddleware,
        max_concurrent=conc.max_concurrent,
        max_wait_time=conc.max_wait_time
    )

    # 添加请求耗时日志中间件（记录慢请求）
    from middleware.timeout import RequestTimeLoggerMiddleware
    app.add_middleware(RequestTimeLoggerMiddleware, threshold_seconds=30.0)

    # 添加安全响应头中间件
    # 注意：CORS 由 Nginx 处理，应用层只添加其他安全头
    from middleware.security_headers import SecurityHeadersMiddleware
    enable_hsts = not config.app.debug
    app.add_middleware(
        SecurityHeadersMiddleware,
        enable_hsts=enable_hsts,
        hsts_max_age=31536000,
        allow_iframe=False,
        add_security_headers=True
    )

    # 添加审计日志中间件
    from middleware.audit_logger import AuditLoggerMiddleware
    app.add_middleware(AuditLoggerMiddleware)

    # 添加请求统计中间件
    from middleware.request_stats import RequestStatsMiddleware
    app.add_middleware(RequestStatsMiddleware, exclude_paths=["/health", "/docs", "/openapi.json"])

    # 注意：CORS 由 Nginx 反向代理统一处理
    # 开发环境: docker-compose.dev.yml 中的 Nginx 处理
    # 生产环境: docker-compose.yml 中的 Nginx 处理
    logger.info("CORS 由 Nginx 反向代理处理")

    # 包含所有 API v1 路由（包括根路由、健康检查、应用管理等）
    from api.routes_config import api_v1_router
    app.include_router(api_v1_router)

    # 注意：Git HTTP Smart Protocol 由 Nginx + git-http-backend 处理
    # 参见 docker/nginx/nginx.conf 配置

    # 设置全局异常处理器（必须在路由注册之后设置，确保能捕获所有异常）
    from utils.exception_handler import setup_exception_handlers
    setup_exception_handlers(app)

    return app


class AppCache:
    """
    FastAPI应用实例缓存

    缓存已创建的应用实例，避免重复初始化。
    使用模块级缓存而非手动单例模式，降低复杂度。
    """
    _app: Optional[FastAPI] = None
    _config_path: Optional[str] = None

    @classmethod
    def get_app(cls, config_path: str = "config.toml") -> FastAPI:
        """
        获取FastAPI应用实例（缓存）

        Args:
            config_path: 配置文件路径

        Returns:
            FastAPI: FastAPI应用实例
        """
        if cls._app is None or cls._config_path != config_path:
            cls._app = create_app(config_path)
            cls._config_path = config_path
        return cls._app

    @classmethod
    def reset(cls):
        """重置缓存（用于测试）"""
        cls._app = None
        cls._config_path = None


def get_app(config_path: str = "config.toml") -> FastAPI:
    """
    获取FastAPI应用实例（缓存）

    Args:
        config_path: 配置文件路径

    Returns:
        FastAPI: FastAPI应用实例
    """
    return AppCache.get_app(config_path)


# 模块级 app 实例（供 uvicorn app:app 使用）
app = get_app()


def start_server():
    """
    启动 Web 服务器

    根据 config.app.debug 自动选择服务器：
    - debug=True: Uvicorn（开发，支持热重载）
    - debug=False: 优先 Gunicorn，回退 Uvicorn（生产）
    """
    import uvicorn
    from utils.logging import get_logger
    from core.config import get_config

    # 创建应用实例（在 init_app() 成功之后）
    app = get_app()

    config = get_config()
    logger = get_logger("app")
    debug = config.app.debug

    env_name = "开发环境" if debug else "生产环境"
    logger.info(f"服务启动: http://{config.server.host}:{config.server.port} ({env_name})")

    if debug:
        uvicorn.run(
            app,
            host=config.server.host,
            port=config.server.port,
            reload=config.server.reload,
            log_level=config.server.log_level,
            workers=1,
            reload_excludes=["frontend/**"]
        )
