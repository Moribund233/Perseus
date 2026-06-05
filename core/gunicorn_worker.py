"""
自定义 Gunicorn Uvicorn Worker

基于标准 UvicornWorker，在 Linux 环境下使用 uvloop + httptools 获得最佳性能。

使用方法:
    gunicorn -k gunicorn_worker.LanGitUvicornWorker app:get_app()
"""
import os
import logging

from uvicorn.workers import UvicornWorker

logger = logging.getLogger(__name__)


class LanGitUvicornWorker(UvicornWorker):
    """
    LanGit 自定义 Uvicorn Worker

    在 Linux 上使用 uvloop 和 httptools 获得最佳性能。
    """

    CONFIG_KWARGS = {
        "loop": "uvloop",
        "http": "httptools",
        "lifespan": "on",
    }

    def load_config(self) -> None:
        """加载配置"""
        super().load_config()
        self.config.lifespan = "on"
        self.config.loop = "uvloop"
        self.config.http = "httptools"
