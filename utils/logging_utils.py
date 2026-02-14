import logging
import queue
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler, QueueHandler, QueueListener
from pathlib import Path
from typing import Optional


class LogManager:
    """
    日志管理器
    统一日志输出与生成，日志按日期分目录存储
    例如：logs/2026-02-14/error.log
    """

    DEFAULT_LOG_DIR = "logs"
    DATE_FORMAT = "%Y-%m-%d"

    # 日志级别映射
    LEVEL_MAP = {
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "warning": logging.WARNING,
        "error": logging.ERROR,
        "critical": logging.CRITICAL,
    }

    def __init__(
        self,
        log_dir: str = DEFAULT_LOG_DIR,
        app_name: str = "langit",
        level: str = "info",
        max_bytes: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5,
        console_output: bool = True,
    ):
        """
        初始化日志管理器

        Args:
            log_dir: 日志根目录
            app_name: 应用名称，用于日志文件名前缀
            level: 日志级别 (debug/info/warning/error/critical)
            max_bytes: 单个日志文件最大大小（字节）
            backup_count: 备份文件数量
            console_output: 是否同时输出到控制台
        """
        self.log_dir = Path(log_dir)
        self.app_name = app_name
        self.level = self.LEVEL_MAP.get(level.lower(), logging.INFO)
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        self.console_output = console_output

        self._logger: Optional[logging.Logger] = None
        self._handlers: list = []

    def _get_today_log_dir(self) -> Path:
        """
        获取今天的日志目录

        Returns:
            Path: 日志目录路径，格式为 logs/2026-02-14
        """
        today = datetime.now().strftime(self.DATE_FORMAT)
        return self.log_dir / today

    def _ensure_log_dir(self) -> Path:
        """
        确保日志目录存在

        Returns:
            Path: 日志目录路径
        """
        today_dir = self._get_today_log_dir()
        today_dir.mkdir(parents=True, exist_ok=True)
        return today_dir

    def _create_formatter(self, simple: bool = False) -> logging.Formatter:
        """
        创建日志格式器

        Args:
            simple: 是否使用简化格式（类似Uvicorn）

        Returns:
            logging.Formatter: 日志格式器
        """
        if simple:
            # 简化格式：INFO:     消息内容
            fmt = "%(levelname)s:     %(message)s"
            date_fmt = None
        else:
            # 文件日志使用详细格式
            fmt = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            date_fmt = "%Y-%m-%d %H:%M:%S"
        return logging.Formatter(fmt, date_fmt)

    def _create_file_handler(self, log_name: str, level: Optional[int] = None) -> RotatingFileHandler:
        """
        创建文件日志处理器

        Args:
            log_name: 日志文件名（不含扩展名）
            level: 日志级别，默认为初始化时设置的级别

        Returns:
            RotatingFileHandler: 文件日志处理器
        """
        today_dir = self._ensure_log_dir()
        log_file = today_dir / f"{log_name}.log"

        handler = RotatingFileHandler(
            log_file,
            maxBytes=self.max_bytes,
            backupCount=self.backup_count,
            encoding="utf-8",
        )
        handler.setFormatter(self._create_formatter())
        handler.setLevel(level if level is not None else self.level)
        return handler

    def _create_console_handler(self) -> logging.StreamHandler:
        """
        创建控制台日志处理器

        Returns:
            logging.StreamHandler: 控制台日志处理器
        """
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(self._create_formatter(simple=True))
        handler.setLevel(self.level)
        return handler

    def get_logger(self, name: Optional[str] = None) -> logging.Logger:
        """
        获取日志记录器

        Args:
            name: 日志记录器名称，默认为应用名称

        Returns:
            logging.Logger: 日志记录器
        """
        if name is None:
            name = self.app_name

        logger = logging.getLogger(name)
        logger.setLevel(self.level)

        # 避免重复添加处理器
        if not logger.handlers:
            # 添加 app 日志处理器（只记录 INFO 级别，不包含错误）
            app_handler = self._create_file_handler("app", level=logging.INFO)
            # 添加过滤器，排除 WARNING 及以上级别
            app_handler.addFilter(lambda record: record.levelno < logging.WARNING)
            logger.addHandler(app_handler)

            # 添加 error 日志处理器（记录 WARNING 及以上级别）
            error_handler = self._create_file_handler("error", level=logging.WARNING)
            logger.addHandler(error_handler)

            # 添加控制台处理器
            if self.console_output:
                logger.addHandler(self._create_console_handler())

        return logger

    def get_named_logger(self, name: str) -> logging.Logger:
        """
        获取指定名称的日志记录器

        Args:
            name: 日志记录器名称

        Returns:
            logging.Logger: 日志记录器
        """
        logger = logging.getLogger(f"{self.app_name}.{name}")
        logger.setLevel(self.level)

        if not logger.handlers:
            logger.addHandler(self._create_file_handler(name))

            if self.console_output:
                logger.addHandler(self._create_console_handler())

        return logger


# ==================== 便捷函数 ====================


_log_manager: Optional[LogManager] = None


def init_logging(
    log_dir: str = "logs",
    app_name: str = "langit",
    level: str = "info",
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 5,
    console_output: bool = True,
) -> LogManager:
    """
    初始化日志系统

    Args:
        log_dir: 日志根目录
        app_name: 应用名称
        level: 日志级别
        max_bytes: 单个日志文件最大大小
        backup_count: 备份文件数量
        console_output: 是否输出到控制台

    Returns:
        LogManager: 日志管理器实例
    """
    global _log_manager
    _log_manager = LogManager(
        log_dir=log_dir,
        app_name=app_name,
        level=level,
        max_bytes=max_bytes,
        backup_count=backup_count,
        console_output=console_output,
    )
    return _log_manager


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    获取日志记录器

    Args:
        name: 日志记录器名称

    Returns:
        logging.Logger: 日志记录器
    """
    global _log_manager
    if _log_manager is None:
        _log_manager = init_logging()
    return _log_manager.get_logger(name)


def get_named_logger(name: str) -> logging.Logger:
    """
    获取指定名称的日志记录器

    Args:
        name: 日志记录器名称

    Returns:
        logging.Logger: 日志记录器
    """
    global _log_manager
    if _log_manager is None:
        _log_manager = init_logging()
    return _log_manager.get_named_logger(name)


def ensure_log_dir(log_dir: str = "logs") -> Path:
    """
    确保日志根目录存在

    Args:
        log_dir: 日志根目录路径

    Returns:
        Path: 日志根目录路径
    """
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    return log_path


# ==================== 装饰器 ====================


def log_execution(logger_name: Optional[str] = None, level: str = "info"):
    """
    函数执行日志装饰器
    记录函数的执行时间、参数和返回值

    Args:
        logger_name: 日志记录器名称
        level: 日志级别

    Returns:
        Callable: 装饰器函数
    """
    def decorator(func):
        logger = get_named_logger(logger_name or func.__module__)
        log_func = getattr(logger, level.lower(), logger.info)

        def wrapper(*args, **kwargs):
            start_time = datetime.now()
            func_name = func.__name__

            log_func(f"开始执行 {func_name}")

            try:
                result = func(*args, **kwargs)
                elapsed = (datetime.now() - start_time).total_seconds()
                log_func(f"{func_name} 执行完成，耗时 {elapsed:.3f}s")
                return result
            except Exception as e:
                elapsed = (datetime.now() - start_time).total_seconds()
                logger.error(f"{func_name} 执行失败，耗时 {elapsed:.3f}s，错误: {e}")
                raise

        return wrapper
    return decorator


# ==================== 日志清理工具 ====================


def cleanup_old_logs(log_dir: str = "logs", keep_days: int = 30) -> int:
    """
    清理指定天数之前的日志目录

    Args:
        log_dir: 日志根目录
        keep_days: 保留天数

    Returns:
        int: 删除的目录数量
    """
    from datetime import timedelta

    log_path = Path(log_dir)
    if not log_path.exists():
        return 0

    cutoff_date = datetime.now() - timedelta(days=keep_days)
    deleted_count = 0

    for item in log_path.iterdir():
        if item.is_dir():
            try:
                dir_date = datetime.strptime(item.name, "%Y-%m-%d")
                if dir_date < cutoff_date:
                    import shutil
                    shutil.rmtree(item)
                    deleted_count += 1
            except ValueError:
                # 目录名不是日期格式，跳过
                pass

    return deleted_count


# ==================== 异步日志管理器 ====================


class AsyncLogManager(LogManager):
    """
    异步日志管理器

    使用 QueueHandler 和 QueueListener 实现异步日志记录
    日志消息先放入队列，由后台线程批量写入文件，避免 I/O 阻塞主线程

    特性：
    - 非阻塞日志写入
    - 自动后台线程管理
    - 优雅关闭时自动刷新剩余日志
    """

    def __init__(
        self,
        log_dir: str = "logs",
        app_name: str = "langit",
        level: str = "info",
        max_bytes: int = 10 * 1024 * 1024,
        backup_count: int = 5,
        console_output: bool = True,
    ):
        """
        初始化异步日志管理器

        Args:
            log_dir: 日志根目录
            app_name: 应用名称
            level: 日志级别
            max_bytes: 单个日志文件最大大小
            backup_count: 备份文件数量
            console_output: 是否同时输出到控制台
        """
        super().__init__(
            log_dir=log_dir,
            app_name=app_name,
            level=level,
            max_bytes=max_bytes,
            backup_count=backup_count,
            console_output=console_output,
        )

        # 创建日志队列
        self._log_queue: queue.Queue = queue.Queue(-1)  # 无界队列
        self._queue_listener: Optional[QueueListener] = None
        self._target_handlers: list = []
        self._is_async_setup = False

    def _setup_async_handlers(self):
        """设置异步日志处理器"""
        if self._is_async_setup:
            return

        # 创建目标处理器（实际写入文件的处理器）
        today_dir = self._ensure_log_dir()

        # app.log 处理器（只记录 INFO 级别）
        app_handler = self._create_file_handler("app", level=logging.INFO)
        app_handler.addFilter(lambda record: record.levelno < logging.WARNING)

        # error.log 处理器（记录 WARNING 及以上级别）
        error_handler = self._create_file_handler("error", level=logging.WARNING)

        self._target_handlers = [app_handler, error_handler]

        # 创建队列监听器（后台线程）
        self._queue_listener = QueueListener(
            self._log_queue,
            *self._target_handlers,
            respect_handler_level=True
        )

        # 启动监听器
        self._queue_listener.start()
        self._is_async_setup = True

    def get_logger(self, name: Optional[str] = None) -> logging.Logger:
        """
        获取异步日志记录器

        Args:
            name: 日志记录器名称

        Returns:
            logging.Logger: 异步日志记录器
        """
        if name is None:
            name = self.app_name

        logger = logging.getLogger(name)
        logger.setLevel(self.level)

        # 避免重复添加处理器
        if not logger.handlers:
            # 确保异步处理器已设置
            self._setup_async_handlers()

            # 使用 QueueHandler 替代普通 Handler
            queue_handler = QueueHandler(self._log_queue)
            logger.addHandler(queue_handler)

            # 添加控制台处理器（控制台输出保持同步，避免延迟）
            if self.console_output:
                logger.addHandler(self._create_console_handler())

        return logger

    def get_named_logger(self, name: str) -> logging.Logger:
        """
        获取指定名称的异步日志记录器

        Args:
            name: 日志记录器名称

        Returns:
            logging.Logger: 异步日志记录器
        """
        logger = logging.getLogger(f"{self.app_name}.{name}")
        logger.setLevel(self.level)

        if not logger.handlers:
            self._setup_async_handlers()
            queue_handler = QueueHandler(self._log_queue)
            logger.addHandler(queue_handler)

            if self.console_output:
                logger.addHandler(self._create_console_handler())

        return logger

    def shutdown(self):
        """
        优雅关闭异步日志

        停止队列监听器，确保所有剩余日志都被写入
        """
        if self._queue_listener and self._is_async_setup:
            try:
                self._queue_listener.stop()
            except (AttributeError, Exception):
                # 忽略已停止或未完成初始化的监听器
                pass
            finally:
                self._is_async_setup = False
                self._queue_listener = None

    def __del__(self):
        """析构时自动关闭"""
        try:
            self.shutdown()
        except Exception:
            # 忽略析构时的错误
            pass


# ==================== 异步日志便捷函数 ====================


_async_log_manager: Optional[AsyncLogManager] = None


def init_async_logging(
    log_dir: str = "logs",
    app_name: str = "langit",
    level: str = "info",
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 5,
    console_output: bool = True,
) -> AsyncLogManager:
    """
    初始化异步日志系统

    Args:
        log_dir: 日志根目录
        app_name: 应用名称
        level: 日志级别
        max_bytes: 单个日志文件最大大小
        backup_count: 备份文件数量
        console_output: 是否输出到控制台

    Returns:
        AsyncLogManager: 异步日志管理器实例
    """
    global _async_log_manager
    _async_log_manager = AsyncLogManager(
        log_dir=log_dir,
        app_name=app_name,
        level=level,
        max_bytes=max_bytes,
        backup_count=backup_count,
        console_output=console_output,
    )
    return _async_log_manager


def get_async_logger(name: Optional[str] = None) -> logging.Logger:
    """
    获取异步日志记录器

    Args:
        name: 日志记录器名称

    Returns:
        logging.Logger: 异步日志记录器
    """
    global _async_log_manager
    if _async_log_manager is None:
        _async_log_manager = init_async_logging()
    return _async_log_manager.get_logger(name)


def shutdown_async_logging():
    """关闭异步日志系统"""
    global _async_log_manager
    if _async_log_manager:
        _async_log_manager.shutdown()
        _async_log_manager = None
