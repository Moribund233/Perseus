import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.init import init_app

# 注意：logger 和 config 的导入被延迟到 create_app() 内部
# 以确保 init_app() 先执行环境变量检查


def create_app(config_path: str = "config.toml") -> FastAPI:
    """
    创建FastAPI应用实例

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

    # 添加请求超时中间件（防止请求无限期挂起）
    from middleware.timeout import TimeoutMiddleware
    app.add_middleware(TimeoutMiddleware, timeout_seconds=30.0)

    from middleware.security_headers import SecurityHeadersMiddleware
    enable_hsts = not config.app.debug
    add_security_headers = not config.proxy.proxy
    app.add_middleware(
        SecurityHeadersMiddleware,
        enable_hsts=enable_hsts,
        hsts_max_age=31536000,
        allow_iframe=False,
        add_security_headers=add_security_headers
    )

    # 添加审计日志中间件
    from middleware.audit_logger import AuditLoggerMiddleware
    app.add_middleware(AuditLoggerMiddleware)

    # 添加请求统计中间件
    from middleware.request_stats import RequestStatsMiddleware
    app.add_middleware(RequestStatsMiddleware, exclude_paths=["/health", "/docs", "/openapi.json"])

    # 根据是否启用反向代理来决定是否启用CORS中间件
    if not config.proxy.proxy:
        # 未启用反向代理，启用FastAPI的CORS中间件
        # 使用配置文件中的CORS设置
        cors_config = config.cors

        # 生产环境安全检查
        if not config.app.debug:
            # 生产环境不允许使用通配符
            if "*" in cors_config.allow_origins:
                logger.warning(
                    "生产环境检测到CORS allow_origins包含通配符'*'，"
                    "这会带来安全风险。建议配置具体的允许域名。"
                )
                # 生产环境强制使用安全的默认值
                allow_origins = ["http://localhost:3000", "http://127.0.0.1:3000"]
            else:
                allow_origins = cors_config.allow_origins
        else:
            allow_origins = cors_config.allow_origins

        app.add_middleware(
            CORSMiddleware,
            allow_origins=allow_origins,
            allow_credentials=cors_config.allow_credentials,
            allow_methods=cors_config.allow_methods,
            allow_headers=cors_config.allow_headers,
            max_age=cors_config.max_age,
        )

        logger.info(f"CORS配置: allow_origins={allow_origins}")

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
    else:
        # 生产模式优先尝试 Gunicorn
        try:
            import gunicorn.app.base
            from gunicorn.config import Config

            class PerseusGunicornApp(gunicorn.app.base.BaseApplication):
                """
                Perseus 自定义 Gunicorn 应用
                """
                def __init__(self, app, options=None):
                    self.options = options or {}
                    self.application = app
                    super().__init__()

                def init(self, parser, opts, args):
                    pass

                def load_config(self):
                    for key, value in self.options.items():
                        if key in self.cfg.settings and value is not None:
                            self.cfg.set(key.lower(), value)

                def load(self):
                    return self.application

            gunicorn_cfg = config.gunicorn
            options = {
                "bind": f"{config.server.host}:{config.server.port}",
                "workers": gunicorn_cfg.workers,
                "worker_class": gunicorn_cfg.worker_class,
                "threads": gunicorn_cfg.threads,
                "worker_connections": gunicorn_cfg.worker_connections,
                "backlog": gunicorn_cfg.backlog,
                "timeout": gunicorn_cfg.timeout,
                "graceful_timeout": gunicorn_cfg.graceful_timeout,
                "keepalive": gunicorn_cfg.keepalive,
                "max_requests": gunicorn_cfg.max_requests,
                "max_requests_jitter": gunicorn_cfg.max_requests_jitter,
                "preload_app": gunicorn_cfg.preload_app,
                "daemon": gunicorn_cfg.daemon,
                "loglevel": config.server.log_level,
                "accesslog": "-" if gunicorn_cfg.access_log else None,
                "errorlog": "-",
                "capture_output": gunicorn_cfg.capture_output,
                "proc_name": "perseus",
            }

            PerseusGunicornApp(app, options).run()
            return
        except ImportError:
            logger.info("Gunicorn 未安装，使用 Uvicorn 作为替代")
        except Exception as e:
            logger.warning(f"Gunicorn 启动失败: {e}，回退到 Uvicorn")

        # 回退到 Uvicorn
        uvicorn.run(
            app,
            host=config.server.host,
            port=config.server.port,
            log_level=config.server.log_level,
            workers=1
        )


if __name__ == "__main__":
    """主函数入口"""
    # 初始化应用，如果失败则退出
    if not init_app():
        import sys
        sys.exit(1)
    start_server()
