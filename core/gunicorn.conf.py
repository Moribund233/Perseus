"""
Gunicorn 配置文件

提供生产环境多进程部署配置。
支持从 config.toml 读取配置。

使用方法:
    gunicorn -c gunicorn.conf.py app:get_app()

或:
    python -m gunicorn -c gunicorn.conf.py "app:get_app()"
"""
import os
import sys
import multiprocessing
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.config import get_config
from utils.logging import get_logger

# 加载应用配置
app_config = get_config()
gunicorn_config = app_config.gunicorn

# ==================== 服务器配置 ====================

# 绑定地址和端口（从 server 配置读取）
bind = f"{app_config.server.host}:{app_config.server.port}"

# Worker 进程数（从 gunicorn 配置读取）
workers = gunicorn_config.workers
if workers <= 0:
    workers = multiprocessing.cpu_count() * 2 + 1

# Worker 类（从 gunicorn 配置读取）
worker_class = gunicorn_config.worker_class

# 每个 worker 的线程数（仅适用于 sync worker，uvicorn worker 忽略此设置）
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

# 进程名称
proc_name = "langit"

# 工作目录
chdir = str(project_root)

# ==================== 日志配置 ====================

# 日志级别（从 server 配置读取）
loglevel = app_config.server.log_level

# 访问日志
accesslog = "-" if gunicorn_config.access_log else None
access_log_format = gunicorn_config.access_log_format

# 错误日志
errorlog = "-"

# 是否捕获 stdout/stderr
capture_output = gunicorn_config.capture_output

# ==================== 性能优化配置 ====================

# SO_REUSEPORT 选项（Linux 多核负载均衡）
if gunicorn_config.enable_reuse_port:
    os.environ["GUNICORN_REUSE_PORT"] = "1"

# ==================== 生命周期钩子 ====================

logger = get_logger("gunicorn")


def on_starting(server):
    """
    Gunicorn 启动前调用

    Args:
        server: Arbiter 实例
    """
    logger.info(f"Gunicorn 正在启动: workers={workers}, worker_class={worker_class}, bind={bind}")


def on_reload(server):
    """
    重新加载配置时调用

    Args:
        server: Arbiter 实例
    """
    logger.info("Gunicorn 重新加载配置...")
    try:
        global app_config, gunicorn_config
        app_config = get_config(force_reload=True)
        gunicorn_config = app_config.gunicorn
        logger.info("配置已重新加载")
    except Exception as e:
        logger.error(f"重新加载配置失败: {e}")


def when_ready(server):
    """
    Gunicorn 启动完成，准备接收请求时调用

    Args:
        server: Arbiter 实例
    """
    logger.info("Gunicorn 已就绪，开始接收请求")


def on_exit(server):
    """
    Gunicorn 退出时调用

    Args:
        server: Arbiter 实例
    """
    logger.info("Gunicorn 正在退出...")
