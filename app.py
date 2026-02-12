import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from init import init_app
from config import get_config


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

    # 创建FastAPI应用实例
    app = FastAPI(
        title=config.app.title,
        description=config.app.description,
        version=config.app.version,
        debug=config.app.debug,
        redirect_slashes=False,  # 禁用尾部斜杠重定向，避免CORS问题
    )

    # 确保日志目录存在
    os.makedirs("logs", exist_ok=True)

    # 添加安全响应头中间件（最先添加，确保所有响应都包含安全头）
    from middleware.security_headers import SecurityHeadersMiddleware
    # 根据debug配置自动启用HSTS：非debug模式（生产环境）启用HSTS
    enable_hsts = not config.app.debug
    # 如果启用了Nginx反向代理，让Nginx处理基础安全头，应用只处理HSTS
    add_security_headers = not config.nginx.proxy
    app.add_middleware(
        SecurityHeadersMiddleware,
        enable_hsts=enable_hsts,  # 生产环境启用 HSTS，开发环境禁用
        hsts_max_age=31536000,  # HSTS max-age: 1年
        allow_iframe=False,
        add_security_headers=add_security_headers  # Nginx代理时跳过基础安全头
    )

    # 添加审计日志中间件
    from middleware.audit_logger import AuditLoggerMiddleware
    app.add_middleware(AuditLoggerMiddleware)

    # 设置速率限制
    from utils.rate_limiter import setup_rate_limiter
    setup_rate_limiter(app)

    # 根据是否启用Nginx反向代理来决定是否启用CORS中间件
    if not config.nginx.proxy:
        # 未启用Nginx反向代理，启用FastAPI的CORS中间件
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # 允许所有来源，生产环境中应该限制为特定域名
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],  # 限制允许的HTTP方法
            allow_headers=["Content-Type", "Authorization"],  # 限制允许的请求头
        )

    # 包含所有 API v1 路由（包括根路由、健康检查、应用管理等）
    from api.api_v1 import api_v1_router
    app.include_router(api_v1_router)

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
    
    config = get_config()
    debug = config.app.debug
    
    print(f"Starting {config.app.title} v{config.app.version}...")
    print(f"Environment: {'Development' if debug else 'Production'}")
    print(f"Server: http://{config.server.host}:{config.server.port}")
    
    if debug:
        # 开发环境：Uvicorn
        print("Using Uvicorn (development mode)")
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
                
                print("Using Gunicorn + Uvicorn Workers (production mode)")
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
                print("Gunicorn not found, using Uvicorn instead...")
            except Exception as e:
                print(f"Gunicorn failed ({e}), using Uvicorn instead...")
        
        # 回退到 Uvicorn
        print("Using Uvicorn (production mode)")
        uvicorn.run(
            app,
            host=config.server.host,
            port=config.server.port,
            log_level=config.server.log_level,
            workers=config.server.workers
        )


if __name__ == "__main__":
    """主函数入口"""
    init_app()
    start_server()
