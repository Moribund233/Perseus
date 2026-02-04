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
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # 限制允许的来源
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
    
    return app


# FastAPI应用实例（延迟创建）
_app_instance = None


def get_app(config_path: str = "config.toml") -> FastAPI:
    """
    获取FastAPI应用实例（单例模式）
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        FastAPI: FastAPI应用实例
    """
    global _app_instance
    if _app_instance is None:
        _app_instance = create_app(config_path)
    return _app_instance


# 导出应用实例
app = get_app()


def run_uvicorn():
    """
    使用Uvicorn启动服务器（开发环境）
    开发环境始终使用1个worker，不需要多进程
    """
    import uvicorn
    
    # 获取配置
    config = get_config()
    
    # 启动Uvicorn服务器（开发环境始终使用1个worker）
    uvicorn.run(
        "app:app",
        host=config.server.host,
        port=config.server.port,
        reload=config.server.reload,
        log_level=config.server.log_level,
        workers=1,  # 开发环境不需要多进程
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
