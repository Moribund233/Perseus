"""
日志系统

基于 WebSocket 的实时日志系统

特性：
- 简化的配置
- 多文件分离：app.log (INFO及以下), error.log (WARNING及以上), audit.log (审计日志)
- 按日期分目录存储
- 保留文件日志（用于持久化）
- WebSocket 实时推送（所有日志自动继承）
- 内存缓冲区（用于快速查询历史日志）
"""
import logging
import re
import sys
from pathlib import Path
from typing import Optional, Dict, List, Any, Tuple
from logging.handlers import RotatingFileHandler
from datetime import datetime

_websocket_handler = None

# RotatingFileHandler 默认保留策略（init_logging 未显式传参时生效）
DEFAULT_MAX_BYTES = 10 * 1024 * 1024
DEFAULT_BACKUP_COUNT = 5


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

    所有日志器自动继承根日志器的处理器，确保 WebSocket 能接收所有日志
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
        app_name: str = "perseus",
        level: str = "info",
        max_bytes: int = 10 * 1024 * 1024,
        backup_count: int = 5,
        console_output: bool = True,
        websocket_output: bool = True,
        separate_error_log: bool = True,
        use_date_directory: bool = True,
    ):
        self.log_dir = Path(log_dir)
        self.app_name = app_name
        self.level = self.LEVEL_MAP.get(level.lower(), logging.INFO)
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        self.console_output = console_output
        self.websocket_output = websocket_output
        self.separate_error_log = separate_error_log
        self.use_date_directory = use_date_directory

        self._initialized = False

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
        if self.separate_error_log:
            handler.addFilter(lambda record: record.levelno <= logging.INFO)
        return handler

    def _create_error_handler(self) -> RotatingFileHandler:
        """创建 error.log 处理器（WARNING 及以上）"""
        handler = self._create_file_handler("error.log", logging.WARNING)
        return handler

    def setup_root_logger(self) -> None:
        """
        配置根日志器

        在根日志器上配置处理器，所有子日志器自动继承
        这确保 WebSocket 能接收所有模块的日志
        """
        if self._initialized:
            return

        root_logger = logging.getLogger()
        root_logger.setLevel(self.level)

        if not root_logger.handlers:
            root_logger.addHandler(self._create_app_handler())

            if self.separate_error_log:
                root_logger.addHandler(self._create_error_handler())

            if self.console_output:
                root_logger.addHandler(self._create_console_handler())

            if self.websocket_output:
                ws_handler = _get_websocket_log_handler()
                ws_handler.setLevel(self.level)
                root_logger.addHandler(ws_handler)

        self._initialized = True

    def get_logger(self, name: Optional[str] = None) -> logging.Logger:
        """
        获取日志记录器

        Args:
            name: 日志记录器名称

        Returns:
            logging.Logger: 日志记录器（继承根日志器的处理器）
        """
        self.setup_root_logger()

        if name is None:
            name = self.app_name

        logger = logging.getLogger(name)
        logger.setLevel(self.level)
        logger.propagate = True

        return logger

    def get_named_logger(self, name: str) -> logging.Logger:
        """获取指定名称的日志记录器"""
        return self.get_logger(f"{self.app_name}.{name}")

    def get_audit_logger(self) -> logging.Logger:
        """
        获取审计日志记录器

        审计日志单独存储在 audit.log 中
        """
        self.setup_root_logger()

        logger = logging.getLogger(f"{self.app_name}.audit")
        logger.setLevel(logging.INFO)
        logger.propagate = False

        if not logger.handlers:
            handler = self._create_file_handler("audit.log", logging.INFO)
            handler.setFormatter(self._create_formatter())
            logger.addHandler(handler)

            if self.console_output:
                console_handler = logging.StreamHandler(sys.stdout)
                console_handler.setFormatter(
                    logging.Formatter("[AUDIT] %(asctime)s - %(message)s", "%Y-%m-%d %H:%M:%S")
                )
                logger.addHandler(console_handler)

            if self.websocket_output:
                ws_handler = _get_websocket_log_handler()
                ws_handler.setLevel(logging.INFO)
                logger.addHandler(ws_handler)

        return logger


_log_manager: Optional[LogManager] = None


def init_logging(
    log_dir: str = "logs",
    app_name: str = "perseus",
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

    在根日志器上配置处理器，所有子日志器自动继承
    """
    global _log_manager

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

    _log_manager.setup_root_logger()

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
                pass

    return deleted_count


def get_log_retention() -> Tuple[int, int]:
    """返回当前日志保留策略 (max_bytes, backup_count)"""
    global _log_manager
    if _log_manager is not None:
        return _log_manager.max_bytes, _log_manager.backup_count
    return DEFAULT_MAX_BYTES, DEFAULT_BACKUP_COUNT


_SEGMENT_RE = re.compile(r"^(?P<base>.+\.log)(?:\.(?P<idx>\d+))?$")


def parse_log_segment(name: str) -> Optional[Tuple[str, int]]:
    """
    解析日志文件名中的基名与分片序号。

    - ``error.log``   → ``("error.log", 0)``（当前段）
    - ``error.log.3`` → ``("error.log", 3)``（第 3 个备份，数字越大越旧）
    - 非日志文件      → ``None``
    """
    m = _SEGMENT_RE.match(name)
    if not m:
        return None
    return m.group("base"), int(m.group("idx") or 0)


def resolve_log_segments(
    log_dir: str,
    date: str,
    log_name: str,
) -> List[Tuple[int, Path]]:
    """
    解析某日期下某个日志文件的全部磁盘分片（RotatingFileHandler 产物）。

    Args:
        log_dir: 日志根目录
        date: 日期 (YYYY-MM-DD)
        log_name: 文件基名（不含 .log）

    Returns:
        List[Tuple[int, Path]]: ``(分片序号, 路径)`` 按**新→旧**排序；
        序号 0 为当前段，数字越大越旧。无匹配时返回空列表。
    """
    day_dir = Path(log_dir) / date
    base = f"{log_name}.log"
    segments: List[Tuple[int, Path]] = []
    if day_dir.exists():
        for path in day_dir.iterdir():
            parsed = parse_log_segment(path.name)
            if parsed and parsed[0] == base:
                segments.append((parsed[1], path))
    segments.sort(key=lambda item: item[0])
    return segments


def get_log_info(log_dir: str = "logs") -> Dict[str, Any]:
    """
    获取日志系统信息

    每个日志文件按基名聚合其磁盘分片（``X.log`` + ``X.log.1..N``），
    返回分片数、合计大小与是否已达保留上限（更早分片可能已被丢弃）。

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
    _, backup_count = get_log_retention()

    if today_dir.exists():
        groups: Dict[str, List[Tuple[int, Path]]] = {}
        for log_file in today_dir.iterdir():
            parsed = parse_log_segment(log_file.name)
            if parsed:
                groups.setdefault(parsed[0], []).append((parsed[1], log_file))

        for base in sorted(groups):
            segs = sorted(groups[base], key=lambda item: item[0])
            seg_total = 0
            for _, seg_path in segs:
                try:
                    seg_total += seg_path.stat().st_size
                except OSError:
                    pass
            total_size += seg_total

            current = next((p for idx, p in segs if idx == 0), None)
            newest_path = current or segs[0][1]
            current_size = current.stat().st_size if current else 0
            max_idx = segs[-1][0]

            files.append({
                "name": base,
                "size": current_size,
                "size_formatted": _format_file_size(current_size),
                "modified": datetime.fromtimestamp(newest_path.stat().st_mtime).isoformat(),
                "parts": len(segs),
                "total_size": seg_total,
                "total_size_formatted": _format_file_size(seg_total),
                "truncated": backup_count > 0 and max_idx >= backup_count,
            })

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


def _format_file_size(size_bytes: float) -> str:
    """格式化文件大小"""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def read_log_file(
    date: str,
    filename: str = "perseus.log",
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
