"""
Gunicorn 配置文件

提供生产环境多进程部署配置，支持：
- 多worker进程管理
- 优雅关闭协调
- 进程生命周期管理
- 日志配置
- 配置驱动（从config.toml读取）

使用方法:
    gunicorn -c gunicorn.conf.py app:get_app()

或:
    python -m gunicorn -c gunicorn.conf.py "app:get_app()"
"""
import os
import sys
import multiprocessing
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config import get_config
from utils.logging import get_logger

# 加载应用配置
app_config = get_config()
gunicorn_config = app_config.gunicorn

# ==================== 服务器配置 ====================

# 绑定地址和端口（从server配置读取）
bind = f"{app_config.server.host}:{app_config.server.port}"

# Worker进程数（从gunicorn配置读取）
workers = gunicorn_config.workers
if workers <= 0:
    workers = multiprocessing.cpu_count() * 2 + 1

# Worker类（从gunicorn配置读取）
worker_class = gunicorn_config.worker_class

# 每个worker的线程数（仅适用于sync worker，uvicorn worker忽略此设置）
threads = gunicorn_config.threads

# 最大并发连接数
worker_connections = gunicorn_config.worker_connections

# 等待连接的最大队列长度
backlog = gunicorn_config.backlog

# 超时配置（秒）
timeout = gunicorn_config.timeout
graceful_timeout = gunicorn_config.graceful_timeout
keepalive = gunicorn_config.keepalive

# 最大请求数（防止内存泄漏）
max_requests = gunicorn_config.max_requests
max_requests_jitter = gunicorn_config.max_requests_jitter

# 预加载应用（节省内存）
preload_app = gunicorn_config.preload_app

# ==================== 进程管理配置 ====================

# 守护进程模式（后台运行）
daemon = gunicorn_config.daemon

# PID文件路径
pidfile = str(project_root / "langit.pid")

# 进程名称
proc_name = "langit"

# 工作目录
chdir = str(project_root)

# ==================== 日志配置 ====================

# 日志级别（从server配置读取）
loglevel = app_config.server.log_level

# 访问日志
accesslog = "-" if gunicorn_config.access_log else None  # 输出到stdout或禁用
access_log_format = gunicorn_config.access_log_format

# 错误日志
errorlog = "-"  # 输出到stderr

# 是否捕获stdout/stderr
capture_output = gunicorn_config.capture_output

# 是否启用syslog
syslog = False

# ==================== 性能优化配置 ====================

# SO_REUSEPORT选项（Linux多核负载均衡）
if gunicorn_config.enable_reuse_port and sys.platform != "win32":
    import socket
    # 通过环境变量传递，在worker中设置
    os.environ["GUNICORN_REUSE_PORT"] = "1"

# ==================== 生命周期钩子 ====================

# 获取logger
logger = get_logger("gunicorn")


def on_starting(server):
    """
    Gunicorn启动前调用
    
    Args:
        server: Arbiter实例
    """
    logger.info("Gunicorn正在启动...")
    logger.info(f"配置: workers={workers}, worker_class={worker_class}, bind={bind}")


def on_reload(server):
    """
    重新加载配置时调用
    
    Args:
        server: Arbiter实例
    """
    logger.info("Gunicorn重新加载配置...")
    
    # 重新加载配置
    try:
        global app_config, gunicorn_config
        app_config = get_config(force_reload=True)
        gunicorn_config = app_config.gunicorn
        logger.info("配置已重新加载")
    except Exception as e:
        logger.error(f"重新加载配置失败: {e}")


def when_ready(server):
    """
    Gunicorn启动完成，准备接收请求时调用
    
    Args:
        server: Arbiter实例
    """
    logger.info("Gunicorn已就绪，开始接收请求")
    
    # 初始化Master进程的IPC管理器
    try:
        from lifespan import get_lifecycle_manager
        manager = get_lifecycle_manager()
        manager.setup_for_master(server.pid)
    except Exception as e:
        logger.error(f"初始化Master生命周期管理器失败: {e}")


def worker_int(worker):
    """
    Worker收到SIGINT或SIGQUIT信号时调用
    
    Args:
        worker: Worker实例
    """
    logger.info(f"Worker {worker.pid} 收到中断信号")


def worker_abort(worker):
    """
    Worker收到SIGABRT信号时调用
    
    Args:
        worker: Worker实例
    """
    logger.warning(f"Worker {worker.pid} 异常终止")


def on_exit(server):
    """
    Gunicorn退出时调用
    
    Args:
        server: Arbiter实例
    """
    logger.info("Gunicorn正在退出...")
    
    # 清理IPC资源
    try:
        from lifespan import get_lifecycle_manager
        manager = get_lifecycle_manager()
        manager.cleanup()
    except Exception as e:
        logger.error(f"清理IPC资源失败: {e}")
