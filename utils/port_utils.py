import os
from pathlib import Path
from typing import List, Optional

import psutil

from core.config import ConfigManager
from utils.logging import get_named_logger

logger = get_named_logger("port")


def get_port_processes(port: int) -> List[int]:
    """获取占用指定端口的进程PID列表（跨平台，使用psutil）"""
    pids = []
    try:
        for conn in psutil.net_connections(kind="inet"):
            if conn.laddr.port == port and conn.status == psutil.CONN_LISTEN:
                if conn.pid is not None and conn.pid not in pids:
                    pids.append(conn.pid)
    except (psutil.AccessDenied, psutil.NoSuchProcess):
        pass
    except Exception as e:
        logger.error(f"获取端口 {port} 占用情况时出错: {e}")

    return pids


def kill_process(pid: int, timeout: int = 5) -> bool:
    """安全终止进程"""
    try:
        proc = psutil.Process(pid)
        proc.terminate()
        proc.wait(timeout=timeout)
        return True
    except psutil.NoSuchProcess:
        return True
    except psutil.TimeoutExpired:
        try:
            proc.kill()
            proc.wait(timeout=2)
            return True
        except (psutil.NoSuchProcess, psutil.TimeoutExpired):
            return False
    except (psutil.AccessDenied, Exception):
        return False


def is_related_service_process(pid: int) -> bool:
    """
    检查进程是否为当前服务相关的进程

    通过比较工作目录和命令行特征来判断。
    同一工作目录下的langit相关进程被认为是相关进程。

    Args:
        pid: 进程ID

    Returns:
        bool: 是否为相关进程
    """
    try:
        current_pid = os.getpid()
        if pid == current_pid:
            return True

        current_proc = psutil.Process(current_pid)
        target_proc = psutil.Process(pid)

        # 获取当前进程的工作目录
        try:
            current_cwd = Path(current_proc.cwd()).resolve()
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            return False

        # 获取目标进程的工作目录和命令行
        try:
            target_cwd = Path(target_proc.cwd()).resolve()
            cmd_line = " ".join(target_proc.cmdline()).lower()
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            return False

        # 工作目录不同，肯定不是同一应用
        if current_cwd != target_cwd:
            return False

        # 在工作目录相同的前提下，检查命令行特征
        indicators = [
            "langit-server",      # 可执行文件名
            "langit_server",      # 模块名
            "app:app",            # Uvicorn/FastAPI入口
            "gunicorn_worker",    # 自定义worker
        ]

        # 排除其他Python应用
        exclusions = [
            "jupyter", "ipython", "pytest", "unittest",
            "pip", "conda", "npm", "node"
        ]

        has_indicator = any(ind in cmd_line for ind in indicators)
        has_exclusion = any(exc in cmd_line for exc in exclusions)

        return has_indicator and not has_exclusion

    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return False
    except Exception as e:
        logger.error(f"检查进程 {pid} 时出错: {e}")
        return False


def check_and_terminate_running_service(
    port: Optional[int] = None,
    config_path: str = "config.toml"
) -> bool:
    """检测并终止已占用指定端口的服务进程"""
    if port is None:
        config_manager = ConfigManager(config_path)
        config = config_manager.get_config()
        port = config.server.port

    pids = get_port_processes(port)

    if not pids:
        logger.debug(f"端口 {port} 空闲")
        return True

    logger.info(f"端口 {port} 被 {len(pids)} 个进程占用")

    related_pids = []
    for pid in pids:
        try:
            if is_related_service_process(pid):
                related_pids.append(pid)
            else:
                logger.debug(f"进程 PID {pid} 不是相关服务进程，跳过")
        except Exception as e:
            logger.warning(f"检查进程 PID {pid} 时出错: {e}，跳过")

    if not related_pids:
        logger.info(f"端口 {port} 没有相关服务进程占用")
        return True

    terminated_count = 0
    for pid in related_pids:
        logger.info(f"终止服务进程 PID {pid}...")
        if kill_process(pid):
            logger.info(f"服务进程 PID {pid} 已终止")
            terminated_count += 1
        else:
            logger.error(f"服务进程 PID {pid} 终止失败")

    if terminated_count == len(related_pids):
        logger.info(f"端口 {port} 已释放")
        return True
    else:
        logger.warning(f"端口 {port}: {len(related_pids) - terminated_count} 个进程未能终止")
        return False


def terminate_all_python_services(
    port: Optional[int] = None,
    config_path: str = "config.toml"
) -> int:
    """终止所有占用指定端口的Python服务进程"""
    if port is None:
        config_manager = ConfigManager(config_path)
        config = config_manager.get_config()
        port = config.server.port

    pids = get_port_processes(port)

    if not pids:
        logger.info(f"端口 {port} 没有占用进程")
        return 0

    terminated_count = 0
    for pid in pids:
        try:
            proc = psutil.Process(pid)
            proc_name = proc.name().lower()

            is_python_process = "python" in proc_name
            is_related_process = is_related_service_process(pid) if is_python_process else False

            if is_python_process and is_related_process:
                logger.info(f"终止服务进程 PID {pid}...")
                if kill_process(pid):
                    logger.info(f"服务进程 PID {pid} 已终止")
                    terminated_count += 1
                else:
                    logger.error(f"服务进程 PID {pid} 终止失败")
            elif is_python_process:
                logger.debug(f"跳过非相关Python进程 PID {pid}")
        except psutil.NoSuchProcess:
            pass
        except Exception as e:
            logger.error(f"获取进程信息失败 PID {pid}: {e}")

    logger.info(f"共终止 {terminated_count} 个服务进程")
    return terminated_count


def terminate_running_service(
    port: Optional[int] = None,
    config_path: str = "config.toml"
) -> bool:
    """检测并终止已占用指定端口的服务进程的便捷函数"""
    return check_and_terminate_running_service(port=port, config_path=config_path)


# ==================== PID文件管理工具 ====================

class PidFileManager:
    """PID文件管理器，用于在应用启动后记录主进程PID
    
    注意：只记录主进程PID，不记录worker进程
    - Uvicorn单worker: 1个主进程
    - Uvicorn多workers: 1个主进程 + N个workers
    - Gunicorn+Uvicorn: 1个Gunicorn主进程 + 1个管理进程 + N个Uvicorn workers
    
    无论哪种方式，只需要记录主进程PID即可管理和停止服务
    """

    def __init__(self, pid_file: str = "langit.pid"):
        self.pid_file = Path(pid_file)

    def write_pid(self, pid: Optional[int] = None) -> Path:
        """写入PID到文件（覆盖写模式），默认为当前进程PID"""
        pid = pid or os.getpid()
        self.pid_file.write_text(str(pid), encoding="utf-8")
        return self.pid_file

    def read_pid(self) -> Optional[int]:
        """从文件读取PID，失败返回None"""
        try:
            return int(self.pid_file.read_text(encoding="utf-8").strip())
        except (ValueError, IOError, FileNotFoundError):
            return None

    def is_process_running(self) -> bool:
        """检查PID文件中记录的进程是否仍在运行"""
        pid = self.read_pid()
        if pid is None:
            return False
        try:
            return psutil.Process(pid).is_running()
        except psutil.NoSuchProcess:
            return False


def get_pid_manager(pid_file: str = "langit.pid") -> PidFileManager:
    """获取PID文件管理器实例"""
    return PidFileManager(pid_file)
