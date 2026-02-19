"""
日志系统

基于 WebSocket 的实时日志系统

特性：
- 简化的配置
- 多文件分离：app.log (INFO及以下), error.log (WARNING及以上), audit.log (审计日志)
- 按日期分目录存储
- 保留文件日志（用于持久化）
- WebSocket 实时推送
- 内存缓冲区（用于快速查询历史日志）
"""
import logging
import sys
from pathlib import Path
from typing import Optional, Dict, List
from logging.handlers import RotatingFileHandler
from datetime import datetime

# WebSocket handler 延迟导入，避免循环依赖
_websocket_handler = None


def _get_websocket_log_handler():
    """延迟获取 WebSocket 日志处理器"""
    global _websocket_handler
    if _websocket_handler is None:
        from api.websocket.handlers.log_handler import get_websocket_log_handler
        _websocket_handler = get_websocket_log_handler()
    return _websocket_handler


class LogManager:
    """
    日志管理器

    支持多文件分离：
    - app.log: INFO 级别及以下（DEBUG, INFO）
    - error.log: WARNING 级别及以上（WARNING, ERROR, CRITICAL）
    - audit.log: 审计日志（单独记录）

    按日期分目录存储：logs/YYYY-MM-DD/
    """

    DEFAULT_LOG_DIR = "logs"
    DATE_FORMAT = "%Y-%m-%d"

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
        websocket_output: bool = True,
        separate_error_log: bool = True,  # 是否分离 error.log
        use_date_directory: bool = True,  # 是否按日期分目录
    ):
        """
        初始化日志管理器

        Args:
            log_dir: 日志根目录
            app_name: 应用名称
            level: 日志级别
            max_bytes: 单个日志文件最大大小
            backup_count: 备份文件数量
            console_output: 是否输出到控制台
            websocket_output: 是否通过 WebSocket 实时推送
            separate_error_log: 是否将错误日志分离到单独文件
            use_date_directory: 是否按日期分目录存储
        """
        self.log_dir = Path(log_dir)
        self.app_name = app_name
        self.level = self.LEVEL_MAP.get(level.lower(), logging.INFO)
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        self.console_output = console_output
        self.websocket_output = websocket_output
        self.separate_error_log = separate_error_log
        self.use_date_directory = use_date_directory

        self._logger: Optional[logging.Logger] = None

    def _get_log_dir(self) -> Path:
        """获取日志目录（支持按日期分目录）"""
        if self.use_date_directory:
            today = datetime.now().strftime(self.DATE_FORMAT)
            log_dir = self.log_dir / today
        else:
            log_dir = self.log_dir
        log_dir.mkdir(parents=True, exist_ok=True)
        return log_dir

    def _create_formatter(self, simple: bool = False) -> logging.Formatter:
        """创建日志格式器"""
        if simple:
            fmt = "%(levelname)s:     %(message)s"
            date_fmt = None
        else:
            fmt = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            date_fmt = "%Y-%m-%d %H:%M:%S"
        return logging.Formatter(fmt, date_fmt)

    def _create_file_handler(
        self,
        filename: str,
        level: int = logging.DEBUG
    ) -> RotatingFileHandler:
        """创建文件日志处理器"""
        log_dir = self._get_log_dir()
        log_file = log_dir / filename

        handler = RotatingFileHandler(
            log_file,
            maxBytes=self.max_bytes,
            backupCount=self.backup_count,
            encoding="utf-8",
        )
        handler.setFormatter(self._create_formatter())
        handler.setLevel(level)
        return handler

    def _create_console_handler(self) -> logging.StreamHandler:
        """创建控制台日志处理器"""
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(self._create_formatter(simple=True))
        handler.setLevel(self.level)
        return handler

    def _create_app_handler(self) -> RotatingFileHandler:
        """创建 app.log 处理器"""
        handler = self._create_file_handler(f"{self.app_name}.log", logging.DEBUG)
        # 如果启用错误日志分离，添加过滤器只记录 INFO 及以下级别
        if self.separate_error_log:
            handler.addFilter(lambda record: record.levelno <= logging.INFO)
        return handler

    def _create_error_handler(self) -> RotatingFileHandler:
        """创建 error.log 处理器（WARNING 及以上）"""
        handler = self._create_file_handler("error.log", logging.WARNING)
        return handler

    def get_logger(self, name: Optional[str] = None) -> logging.Logger:
        """
        获取日志记录器

        Args:
            name: 日志记录器名称

        Returns:
            logging.Logger: 配置好的日志记录器
        """
        if name is None:
            name = self.app_name

        logger = logging.getLogger(name)
        logger.setLevel(self.level)

        # 避免重复添加处理器
        if not logger.handlers:
            # 添加 app.log 处理器
            logger.addHandler(self._create_app_handler())

            # 添加 error.log 处理器（如果启用）
            if self.separate_error_log:
                logger.addHandler(self._create_error_handler())

            # 添加控制台处理器
            if self.console_output:
                logger.addHandler(self._create_console_handler())

            # 添加 WebSocket 处理器（实时推送）
            if self.websocket_output:
                ws_handler = _get_websocket_log_handler()
                ws_handler.setLevel(self.level)
                logger.addHandler(ws_handler)

        return logger

    def get_named_logger(self, name: str) -> logging.Logger:
        """获取指定名称的日志记录器"""
        return self.get_logger(f"{self.app_name}.{name}")

    def get_audit_logger(self) -> logging.Logger:
        """
        获取审计日志记录器

        审计日志单独存储在 audit.log 中
        """
        logger = logging.getLogger(f"{self.app_name}.audit")
        logger.setLevel(logging.INFO)

        # 审计日志只添加一次处理器
        if not logger.handlers:
            # 创建 audit.log 处理器
            handler = self._create_file_handler("audit.log", logging.INFO)
            handler.setFormatter(self._create_formatter())
            logger.addHandler(handler)

            # 可选：同时输出到控制台
            if self.console_output:
                console_handler = logging.StreamHandler(sys.stdout)
                console_handler.setFormatter(
                    logging.Formatter("[AUDIT] %(asctime)s - %(message)s", "%Y-%m-%d %H:%M:%S")
                )
                logger.addHandler(console_handler)

            # 添加 WebSocket 处理器（实时推送）
            if self.websocket_output:
                ws_handler = _get_websocket_log_handler()
                ws_handler.setLevel(logging.INFO)
                logger.addHandler(ws_handler)

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
    websocket_output: bool = True,
    separate_error_log: bool = True,
    use_date_directory: bool = True,
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
        websocket_output: 是否通过 WebSocket 实时推送
        separate_error_log: 是否分离错误日志
        use_date_directory: 是否按日期分目录

    Returns:
        LogManager: 日志管理器实例
    """
    global _log_manager

    # 如果日志系统已经初始化，直接返回现有实例（幂等性）
    if _log_manager is not None:
        return _log_manager

    _log_manager = LogManager(
        log_dir=log_dir,
        app_name=app_name,
        level=level,
        max_bytes=max_bytes,
        backup_count=backup_count,
        console_output=console_output,
        websocket_output=websocket_output,
        separate_error_log=separate_error_log,
        use_date_directory=use_date_directory,
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


def get_audit_logger() -> logging.Logger:
    """
    获取审计日志记录器

    Returns:
        logging.Logger: 审计日志记录器
    """
    global _log_manager
    if _log_manager is None:
        _log_manager = init_logging()
    return _log_manager.get_audit_logger()


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
    import shutil

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
                    shutil.rmtree(item)
                    deleted_count += 1
            except ValueError:
                # 目录名不是日期格式，跳过
                pass

    return deleted_count


# ==================== 日志信息获取 ====================


def get_log_info(log_dir: str = "logs") -> Dict[str, any]:
    """
    获取日志系统信息

    Args:
        log_dir: 日志根目录

    Returns:
        Dict: 日志信息
    """
    log_path = Path(log_dir)
    today = datetime.now().strftime("%Y-%m-%d")
    today_dir = log_path / today

    files = []
    total_size = 0

    if today_dir.exists():
        for log_file in today_dir.iterdir():
            if log_file.suffix == ".log":
                stat = log_file.stat()
                size = stat.st_size
                total_size += size
                files.append({
                    "name": log_file.name,
                    "size": size,
                    "size_formatted": _format_file_size(size),
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                })

    # 获取所有日期目录
    available_dates = []
    if log_path.exists():
        for item in log_path.iterdir():
            if item.is_dir():
                try:
                    datetime.strptime(item.name, "%Y-%m-%d")
                    available_dates.append(item.name)
                except ValueError:
                    pass

    available_dates.sort(reverse=True)

    return {
        "log_dir": str(log_path),
        "today_dir": str(today_dir),
        "files": files,
        "total_size": total_size,
        "total_size_formatted": _format_file_size(total_size),
        "available_dates": available_dates[:30],
    }


def _format_file_size(size_bytes: int) -> str:
    """格式化文件大小"""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def read_log_file(
    date: str,
    filename: str = "langit.log",
    lines: int = 100,
    log_dir: str = "logs"
) -> List[str]:
    """
    读取日志文件内容

    Args:
        date: 日期 (YYYY-MM-DD)
        filename: 日志文件名
        lines: 读取行数（从末尾开始）
        log_dir: 日志根目录

    Returns:
        List[str]: 日志行列表
    """
    log_path = Path(log_dir) / date / filename

    if not log_path.exists():
        return []

    try:
        with open(log_path, "r", encoding="utf-8") as f:
            all_lines = f.readlines()
            return all_lines[-lines:] if len(all_lines) > lines else all_lines
    except Exception:
        return []
