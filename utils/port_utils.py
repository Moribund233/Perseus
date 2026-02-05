import os
import signal
import subprocess
import sys
from typing import List, Optional

from config import ConfigManager


def get_port_processes_linux(port: int) -> List[int]:
    """
    在Linux系统上获取占用指定端口的进程PID列表

    Args:
        port: 端口号

    Returns:
        List[int]: 进程PID列表
    """
    pids = []
    try:
        result = subprocess.run(
            ["lsof", "-i", f":{port}", "-t"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            for line in result.stdout.strip().split("\n"):
                line = line.strip()
                if line:
                    try:
                        pid = int(line)
                        pids.append(pid)
                    except ValueError:
                        continue
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        print(f"获取端口 {port} 占用情况时出错: {e}")
    except Exception as e:
        print(f"处理端口 {port} 占用情况时发生意外错误: {e}")

    return pids


def get_port_processes_windows(port: int) -> List[int]:
    """
    在Windows系统上获取占用指定端口的进程PID列表

    Args:
        port: 端口号

    Returns:
        List[int]: 进程PID列表
    """
    pids = []
    try:
        # 使用PowerShell命令改进Windows端口检查，避免管道问题
        cmd = f"powershell -Command \"netstat -ano | Select-String -Pattern ':${port}' | Where-Object {{ $_ -match 'LISTENING' }} | ForEach-Object {{ $_.ToString().Split()[-1] }}\""
        result = subprocess.run(
            cmd, 
            capture_output=True,
            text=True,
            timeout=5,
            shell=True
        )
        if result.returncode == 0 and result.stdout.strip():
            for line in result.stdout.strip().split("\n"):
                line = line.strip()
                if line:
                    try:
                        pid = int(line)
                        pids.append(pid)
                    except ValueError:
                        continue
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        print(f"获取端口 {port} 占用情况时出错: {e}")
    except Exception as e:
        print(f"处理端口 {port} 占用情况时发生意外错误: {e}")

    return pids


def get_port_processes(port: int) -> List[int]:
    """
    获取占用指定端口的进程PID列表（跨平台）

    Args:
        port: 端口号

    Returns:
        List[int]: 进程PID列表
    """
    if sys.platform == "win32":
        return get_port_processes_windows(port)
    else:
        return get_port_processes_linux(port)


def kill_process(pid: int, timeout: int = 5) -> bool:
    """
    安全终止进程

    Args:
        pid: 进程PID
        timeout: 等待进程终止的超时时间（秒）

    Returns:
        bool: 是否成功终止进程
    """
    try:
        if sys.platform == "win32":
            result = subprocess.run(
                ["taskkill", "/F", "/PID", str(pid)],
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return result.returncode == 0
        else:
            os.kill(pid, signal.SIGTERM)
            return True
    except (ProcessLookupError, PermissionError, subprocess.TimeoutExpired):
        try:
            if sys.platform != "win32":
                os.kill(pid, signal.SIGKILL)
            return True
        except (ProcessLookupError, PermissionError):
            pass
    return False


def check_and_terminate_running_service(
    port: Optional[int] = None,
    config_path: str = "config.toml"
) -> bool:
    """
    检测并终止已占用指定端口的服务进程

    Args:
        port: 可选，指定要检测的端口。如果为None，则使用配置文件中的端口。
        config_path: 配置文件路径

    Returns:
        bool: 如果端口空闲或服务已成功终止返回True，否则返回False
    """
    if port is None:
        config_manager = ConfigManager(config_path)
        config = config_manager.get_config()
        port = config.server.port

    print(f"正在检测端口 {port} 的占用情况...")

    pids = get_port_processes(port)

    if not pids:
        print(f"端口 {port} 当前空闲，无需终止进程")
        return True

    print(f"发现 {len(pids)} 个进程占用端口 {port}：")
    for pid in pids:
        print(f"  - PID: {pid}")

    # 只终止相关的服务进程
    related_pids = []
    for pid in pids:
        try:
            if is_related_service_process(pid):
                related_pids.append(pid)
            else:
                print(f"  ⚠ 进程 PID {pid} 不是相关服务进程，将被跳过")
        except Exception as e:
            print(f"  ✗ 检查进程 PID {pid} 时出错: {e}，将被跳过")

    if not related_pids:
        print(f"端口 {port} 没有相关的服务进程占用")
        return True

    terminated_count = 0
    for pid in related_pids:
        print(f"正在终止相关服务进程 PID {pid}...")
        if kill_process(pid):
            print(f"  ✓ 服务进程 PID {pid} 已终止")
            terminated_count += 1
        else:
            print(f"  ✗ 服务进程 PID {pid} 终止失败")

    if terminated_count == len(related_pids):
        print(f"所有占用端口 {port} 的相关服务进程已成功终止")
        return True
    else:
        print(f"警告：{len(related_pids) - terminated_count} 个相关服务进程未能终止")
        return False


def is_related_service_process(pid: int) -> bool:
    """
    检查进程是否为当前服务相关的进程
    
    Args:
        pid: 进程PID
        
    Returns:
        bool: 如果是相关服务进程返回True，否则返回False
    """
    try:
        if sys.platform == "win32":
            # Windows平台：使用wmic命令获取进程命令行
            cmd = f"wmic process where ProcessId={pid} get CommandLine /value"
            proc_info = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=5,
                shell=True
            )
            if proc_info.returncode == 0:
                cmd_line = proc_info.stdout.lower()
                # 检查命令行是否包含当前服务的关键词
                return "langit" in cmd_line or "app.py" in cmd_line or "gunicorn" in cmd_line
        else:
            # Linux平台：使用ps命令获取进程命令行
            proc_info = subprocess.run(
                ["ps", "-p", str(pid), "-o", "cmd="],
                capture_output=True,
                text=True,
                timeout=5
            )
            if proc_info.returncode == 0:
                cmd_line = proc_info.stdout.lower()
                # 检查命令行是否包含当前服务的关键词
                return "langit" in cmd_line or "app.py" in cmd_line or "gunicorn" in cmd_line
    except Exception as e:
        print(f"检查进程 {pid} 命令行时出错: {e}")
    return False


def terminate_all_python_services(
    port: Optional[int] = None,
    config_path: str = "config.toml"
) -> int:
    """
    终止所有占用指定端口的Python服务进程

    Args:
        port: 可选，指定要检测的端口。如果为None，则检测所有端口。
        config_path: 配置文件路径

    Returns:
        int: 成功终止的进程数量
    """
    if port is None:
        config_manager = ConfigManager(config_path)
        config = config_manager.get_config()
        port = config.server.port

    print(f"正在终止所有占用端口 {port} 的Python服务进程...")

    pids = get_port_processes(port)

    if not pids:
        print(f"端口 {port} 没有占用进程")
        return 0

    terminated_count = 0
    for pid in pids:
        try:
            is_python_process = False
            is_related_process = False
            
            if sys.platform == "win32":
                # Windows平台：使用tasklist命令获取进程信息
                proc_info = subprocess.run(
                    ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if proc_info.returncode == 0 and proc_info.stdout.strip():
                    # 解析CSV输出，检查进程名是否包含python
                    for line in proc_info.stdout.strip().split("\n"):
                        if "python" in line.lower():
                            is_python_process = True
                            break
            else:
                # Linux平台：使用ps命令获取进程信息
                proc_info = subprocess.run(
                    ["ps", "-p", str(pid), "-o", "comm="],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                proc_name = proc_info.stdout.strip()
                if "python" in proc_name.lower():
                    is_python_process = True
            
            # 检查是否为相关服务进程
            if is_python_process:
                is_related_process = is_related_service_process(pid)
            
            if is_python_process and is_related_process:
                print(f"正在终止相关服务进程 PID {pid}...")
                if kill_process(pid):
                    print(f"  ✓ 服务进程 PID {pid} 已终止")
                    terminated_count += 1
                else:
                    print(f"  ✗ 服务进程 PID {pid} 终止失败")
            elif is_python_process:
                print(f"  ⚠ 跳过非相关Python进程 PID {pid}")
        except subprocess.TimeoutExpired:
            print(f"  ✗ 获取进程信息超时 PID {pid}")
        except Exception as e:
            print(f"  ✗ 获取进程信息失败 PID {pid}: {e}")

    print(f"共终止 {terminated_count} 个相关服务进程")
    return terminated_count


def terminate_running_service(
    port: Optional[int] = None,
    config_path: str = "config.toml"
) -> bool:
    """
    检测并终止已占用指定端口的服务进程的便捷函数

    Args:
        port: 可选，指定要检测的端口。如果为None，则使用配置文件中的端口。
        config_path: 配置文件路径

    Returns:
        bool: 是否成功终止服务
    """
    return check_and_terminate_running_service(port=port, config_path=config_path)
