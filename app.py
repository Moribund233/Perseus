from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from init import init_app
from config import get_config
from utils.logging import get_logger
from lifespan import app_lifespan

logger = get_logger("app")


def create_app(config_path: str = "config.toml") -> FastAPI:
    """
    创建FastAPI应用实例

    Args:
        config_path: 配置文件路径

    Returns:
        FastAPI: FastAPI应用实例
    """
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
    # 根据是否压力测试调整并发限制
    if config.database.is_stress_test:
        max_concurrent = 200  # 压力测试模式允许更多并发
        max_wait_time = 10.0
    else:
        max_concurrent = 100  # 正常模式限制并发
        max_wait_time = 5.0
    app.add_middleware(
        ConcurrencyMiddleware,
        max_concurrent=max_concurrent,
        max_wait_time=max_wait_time
    )
    logger.info(f"并发限制: max_concurrent={max_concurrent}, max_wait_time={max_wait_time}s")

    # 添加请求超时中间件（防止请求无限期挂起）
    from middleware.timeout import TimeoutMiddleware
    # 根据数据库类型调整超时时间
    if config.database.is_sqlite:
        timeout_seconds = 30.0  # SQLite 可能需要更长时间
    else:
        timeout_seconds = 30.0  # PostgreSQL/MySQL 正常超时
    app.add_middleware(TimeoutMiddleware, timeout_seconds=timeout_seconds)
    logger.info(f"请求超时: {timeout_seconds}s")

    # 添加安全响应头中间件（确保所有响应都包含安全头）
    from middleware.security_headers import SecurityHeadersMiddleware
    # 根据debug配置自动启用HSTS：非debug模式（生产环境）启用HSTS
    enable_hsts = not config.app.debug
    # 如果启用了反向代理，让代理服务器处理基础安全头，应用只处理HSTS
    add_security_headers = not config.proxy.proxy
    app.add_middleware(
        SecurityHeadersMiddleware,
        enable_hsts=enable_hsts,  # 生产环境启用 HSTS，开发环境禁用
        hsts_max_age=31536000,  # HSTS max-age: 1年
        allow_iframe=False,
        add_security_headers=add_security_headers  # 代理服务器处理时跳过基础安全头
    )

    # 添加审计日志中间件
    from middleware.audit_logger import AuditLoggerMiddleware
    app.add_middleware(AuditLoggerMiddleware)

    # 添加请求统计中间件
    from middleware.request_stats import RequestStatsMiddleware
    app.add_middleware(RequestStatsMiddleware, exclude_paths=["/health", "/docs", "/openapi.json"])

    # 设置速率限制
    from utils.rate_limiter import setup_rate_limiter
    setup_rate_limiter(app)

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
    from api.api_v1 import api_v1_router
    app.include_router(api_v1_router)

    # 注册 Git HTTP 协议路由（根路径，遵循 Gitee/GitHub 标准）
    # 必须在 API v1 路由之后注册，避免路由冲突
    # URL 格式: /{username}/{repo_name}.git/...
    from controller.git_http_controller import router as git_http_router
    app.include_router(git_http_router)

    # 设置全局异常处理器（必须在路由注册之后设置，确保能捕获所有异常）
    from utils.exception_handler import setup_exception_handlers
    setup_exception_handlers(app)

    return app


class AppSingleton:
    """
    FastAPI应用实例的单例管理器
    用于替代全局变量，更适合测试
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AppSingleton, cls).__new__(cls)
            cls._instance._app = None
            cls._instance._config_path = None
        return cls._instance
    
    def get_app(self, config_path: str = "config.toml") -> FastAPI:
        """
        获取FastAPI应用实例
        
        Args:
            config_path: 配置文件路径
            
        Returns:
            FastAPI: FastAPI应用实例
        """
        if self._app is None or self._config_path != config_path:
            self._app = create_app(config_path)
            self._config_path = config_path
        return self._app
    
    def reset(self):
        """
        重置单例实例，用于测试
        """
        self._app = None
        self._config_path = None


# 创建单例管理器实例
app_singleton = AppSingleton()


def get_app(config_path: str = "config.toml") -> FastAPI:
    """
    获取FastAPI应用实例（单例模式）
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        FastAPI: FastAPI应用实例
    """
    return app_singleton.get_app(config_path)


# 导出应用实例
app = get_app()


def start_server():
    """
    启动 Web 服务器
    
    根据 config.app.debug 自动选择服务器：
    - debug=True: Uvicorn（开发环境，支持热重载）
    - debug=False: Gunicorn+Uvicorn（生产环境，Linux）
    
    回退机制：Windows/Gunicorn未安装/启动失败时自动使用Uvicorn
    """
    import uvicorn
    from utils.port_utils import get_pid_manager
    
    config = get_config()
    debug = config.app.debug
    
    # 记录主进程PID（覆盖写模式，新启动自动覆盖旧内容）
    pid_manager = get_pid_manager()
    pid_file = pid_manager.write_pid()
    logger.info(f"PID file created: {pid_file} (PID: {pid_manager.read_pid()})")
    
    logger.info(f"Starting {config.app.title} v{config.app.version}")
    logger.info(f"Environment: {'Development' if debug else 'Production'}")
    logger.info(f"Server: http://{config.server.host}:{config.server.port}")

    if debug:
        # 开发环境：Uvicorn
        logger.info("Using Uvicorn (development mode)")
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
        # 生产环境：尝试 Gunicorn
        is_windows = config.system and config.system.platform == "win32"
        
        if not is_windows:
            try:
                import gunicorn.app.base
                
                class GunicornApp(gunicorn.app.base.BaseApplication):
                    def __init__(self, app, options=None):
                        self.options = options or {}
                        self.application = app
                        super().__init__()
                    def load_config(self):
                        for key, value in self.options.items():
                            if key in self.cfg.settings and value is not None:
                                self.cfg.set(key.lower(), value)
                    def load(self):
                        return self.application
                
                logger.info("Using Gunicorn + Uvicorn Workers (production mode)")
                GunicornApp(app, {
                    "bind": f"{config.server.host}:{config.server.port}",
                    "workers": config.server.workers,
                    "worker_class": "uvicorn.workers.UvicornWorker",
                    "loglevel": config.server.log_level,
                    "accesslog": "-",
                    "errorlog": "-",
                }).run()
                return
            except ImportError:
                logger.warning("Gunicorn not found, using Uvicorn instead")
            except Exception as e:
                logger.warning(f"Gunicorn failed ({e}), using Uvicorn instead")

        # 回退到 Uvicorn
        logger.info("Using Uvicorn (production mode)")
        uvicorn.run(
            app,
            host=config.server.host,
            port=config.server.port,
            log_level=config.server.log_level,
            workers=config.server.workers
        )


if __name__ == "__main__":
    """主函数入口"""
    # 初始化应用，如果失败则退出
    if not init_app():
        import sys
        sys.exit(1)
    start_server()
