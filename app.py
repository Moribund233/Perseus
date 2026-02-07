import sys
from datetime import datetime
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
    )
    
    # 添加CORS中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:5173", "http://127.0.0.1:5173"],  # 限制允许的来源
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],  # 限制允许的HTTP方法
        allow_headers=["Content-Type", "Authorization"],  # 限制允许的请求头
    )
    
    # 根路由
    @app.get("/")
    async def root():
        return {
            "message": "Welcome to LanGit API",
            "title": config.app.title,
            "version": config.app.version,
            "status": "running"
        }
    
    # 健康检查路由
    @app.get("/health")
    async def health_check():
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "service": config.app.title
        }
    
    # 包含API路由
    from api.user import router as user_router
    app.include_router(user_router)
    
    # 包含仓库相关API路由
    from api.repository import router as repository_router
    app.include_router(repository_router)
    
    from api.repository_member import router as repository_member_router
    app.include_router(repository_member_router)
    
    from api.branch import router as branch_router
    app.include_router(branch_router)
    
    from api.commit import router as commit_router
    app.include_router(commit_router)
    
    # 包含错误API路由
    from api.error import router as error_router
    app.include_router(error_router)
    
    # 设置全局异常处理器
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


def run_uvicorn():
    """
    使用Uvicorn启动服务器（开发环境）
    开发环境始终使用1个worker，不需要多进程
    
    注意：不再支持direct_mode，统一使用子进程方式启动服务
    通过进程ID跟踪实现可靠的服务管理
    """
    import uvicorn
    import os
    import sys
    
    # 获取配置
    config = get_config()
    
    # 记录当前进程ID，便于后续管理
    current_pid = os.getpid()
    print(f"[INFO] App main process started with PID: {current_pid}")
    
    # 启动Uvicorn服务器（开发环境始终使用1个worker）
    # 注意：在主进程中可以使用reload模式，在子进程中会自动禁用
    uvicorn.run(
        "app:app",
        host=config.server.host,
        port=config.server.port,
        reload=config.server.reload,
        log_level=config.server.log_level,
        workers=1,  # 开发环境不需要多进程
        reload_excludes=["frontend/**"]  # 排除前端目录，避免前端更改时后端频繁重载
    )


def run_gunicorn():
    """
    使用Gunicorn + Uvicorn Workers启动服务器（生产环境，仅Linux）
    
    回退机制：
    1. Windows系统：自动回退到Uvicorn
    2. Gunicorn未安装：自动回退到Uvicorn
    3. Gunicorn启动失败：自动回退到Uvicorn
    """
    try:
        import gunicorn.app.base
        
        # 获取配置
        config = get_config()
        
        # 检查是否在Windows系统上（使用配置中的系统信息）
        if config.system and config.system.platform == "win32":
            print("Gunicorn is not supported on Windows. Falling back to Uvicorn...")
            run_uvicorn()
            return
        
        class GunicornApp(gunicorn.app.base.BaseApplication):
            """
            自定义Gunicorn应用类
            """
            
            def __init__(self, app, options=None):
                """
                初始化Gunicorn应用
                
                Args:
                    app: FastAPI应用实例
                    options: Gunicorn配置选项
                """
                self.options = options or {}
                self.application = app
                super().__init__()
            
            def load_config(self):
                """
                加载Gunicorn配置
                """
                for key, value in self.options.items():
                    if key in self.cfg.settings and value is not None:
                        self.cfg.set(key.lower(), value)
            
            def load(self):
                """
                加载FastAPI应用
                
                Returns:
                    FastAPI: FastAPI应用实例
                """
                return self.application
        
        # Gunicorn配置选项
        options = {
            "bind": f"{config.server.host}:{config.server.port}",
            "workers": config.server.workers,
            "worker_class": "uvicorn.workers.UvicornWorker",
            "loglevel": config.server.log_level,
            "accesslog": "-",
            "errorlog": "-",
        }
        
        # 启动Gunicorn服务器
        GunicornApp(app, options).run()
    except ImportError:
        print("Gunicorn library not found. Falling back to Uvicorn...")
        run_uvicorn()
    except Exception as e:
        print(f"Failed to start Gunicorn server: {e}. Falling back to Uvicorn...")
        run_uvicorn()


if __name__ == "__main__":
    """
    主函数入口
    
    根据配置文件中的debug配置项决定服务器类型：
    1. DEBUG=True：使用Uvicorn启动（开发环境）
    2. DEBUG=False：使用Gunicorn启动（生产环境，仅Linux）
    """
    # 初始化应用（只在主进程中执行一次）
    init_app()
    
    # 获取配置
    config = get_config()
    
    print(f"Starting {config.app.title} v{config.app.version}...")
    print(f"Environment: {'Development' if config.app.debug else 'Production'}")
    print(f"Server: http://{config.server.host}:{config.server.port}")
    print(f"Log Level: {config.server.log_level}")
    
    if config.app.debug:
        print("Using Uvicorn server (development mode)")
        run_uvicorn()
    else:
        print("Using Gunicorn + Uvicorn Workers server (production mode)")
        run_gunicorn()
