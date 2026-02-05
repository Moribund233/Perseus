"""
客户端服务控制器模块

提供FastAPI服务生命周期管理功能，包括启动、停止、重启等操作。
该模块被CLI和桌面客户端共用。
"""
import os
import sys
import subprocess
import signal
import time
import threading
from typing import Optional, Callable, List
from enum import Enum
from client.utils.log_manager import get_log_manager


class ServiceState(Enum):
    """服务状态枚举"""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"


class ServiceController:
    """
    FastAPI服务控制器类
    
    负责管理服务的生命周期：启动、停止、重启、日志收集等。
    被CLI和桌面客户端共用。
    """
    
    def __init__(self, config_path: str = "config.toml"):
        """
        初始化服务控制器
        
        Args:
            config_path: 配置文件路径
        """
        self.config_path = config_path
        self.process: Optional[subprocess.Popen] = None
        self.state = ServiceState.STOPPED
        self.log_manager = get_log_manager()
    
    def set_log_callback(self, callback: Callable[[str], None]) -> None:
        """
        设置日志回调函数
        
        Args:
            callback: 接受日志字符串的回调函数
        """
        self.log_manager.add_callback(callback)
    
    def _log(self, message: str) -> None:
        """
        内部日志方法
        
        Args:
            message: 日志消息
        """
        self.log_manager.add_log(message)
    
    def get_logs(self, lines: int = 100) -> List[str]:
        """
        获取日志行
        
        Args:
            lines: 获取的日志行数
            
        Returns:
            List[str]: 日志行列表
        """
        return self.log_manager.get_logs(lines)
    
    def clear_logs(self) -> None:
        """清除所有日志"""
        self.log_manager.clear_logs()
    
    def check_port_available(self, port: int) -> bool:
        """
        检查端口是否可用
        
        Args:
            port: 端口号
            
        Returns:
            bool: 端口可用返回True，否则返回False
        """
        if sys.platform == "win32":
            result = subprocess.run(
                ["netstat", "-ano", f"| findstr :{port}"],
                capture_output=True,
                text=True,
                timeout=5,
                shell=True
            )
            return "LISTENING" not in result.stdout
        else:
            result = subprocess.run(
                ["lsof", "-i", f":{port}", "-t"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode != 0 or not result.stdout.strip()
    
    def get_config_value(self, key: str) -> Optional[str]:
        """
        获取配置值
        
        Args:
            key: 配置键名，支持点号分隔的嵌套键，如 'server.port'
            
        Returns:
            Optional[str]: 配置值，不存在返回None
        """
        if not os.path.exists(self.config_path):
            self._log(f"配置文件不存在: {self.config_path}")
            return None
        
        try:
            import toml
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = toml.load(f)
            
            keys = key.split(".")
            value = config
            for k in keys:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    self._log(f"配置项不存在: {key}")
                    return None
            
            return str(value)
        except toml.TomlDecodeError as e:
            self._log(f"配置文件格式错误: {e}")
            return None
        except PermissionError as e:
            self._log(f"无权限读取配置文件: {e}")
            return None
        except Exception as e:
            self._log(f"读取配置值失败: {key} - {e}")
            return None
    
    def update_config(self, key: str, value: str) -> bool:
        """
        更新配置值
        
        Args:
            key: 配置键名，支持点号分隔的嵌套键
            value: 新的配置值
            
        Returns:
            bool: 更新成功返回True，否则返回False
        """
        if not os.path.exists(self.config_path):
            self._log(f"配置文件不存在: {self.config_path}")
            return False
        
        try:
            import toml
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = toml.load(f)
            
            keys = key.split(".")
            current = config
            for k in keys[:-1]:
                if k not in current:
                    current[k] = {}
                current = current[k]
            
            # 尝试转换为合适的类型
            try:
                if value.isdigit():
                    value = int(value)
                elif value.lower() in ("true", "false"):
                    value = value.lower() == "true"
            except ValueError:
                pass
            
            current[keys[-1]] = value
            
            with open(self.config_path, "w", encoding="utf-8") as f:
                toml.dump(config, f)
            
            self._log(f"配置已更新: {key} = {value}")
            return True
        except toml.TomlDecodeError as e:
            self._log(f"配置文件格式错误: {e}")
            return False
        except PermissionError as e:
            self._log(f"无权限读写配置文件: {e}")
            return False
        except IsADirectoryError as e:
            self._log(f"配置路径是目录，不是文件: {e}")
            return False
        except Exception as e:
            self._log(f"配置更新失败: {key} = {value} - {type(e).__name__}: {e}")
            return False
    
    def _get_python_executable(self) -> str:
        """
        获取Python可执行文件路径
        
        Returns:
            str: Python可执行文件路径
        """
        return sys.executable
    
    def _get_app_path(self) -> str:
        """
        获取应用主文件路径
        
        Returns:
            str: app.py的绝对路径
            
        Raises:
            FileNotFoundError: 找不到app.py文件时抛出
        """
        # 获取当前文件的绝对路径
        current_file = os.path.abspath(__file__)
        
        # 向上查找app.py文件，最多查找5级目录
        for _ in range(5):  # 最多向上查找5级目录
            parent_dir = os.path.dirname(current_file)
            app_path = os.path.join(parent_dir, "app.py")
            if os.path.exists(app_path):
                return app_path
            current_file = parent_dir
        
        # 如果找不到，抛出异常
        raise FileNotFoundError("app.py文件未找到，无法启动服务")
    
    def start(self, block: bool = False, timeout: int = 10) -> bool:
        """
        启动服务
        
        Args:
            block: 是否阻塞等待服务启动
            timeout: 阻塞等待的超时时间（秒）
            
        Returns:
            bool: 启动成功返回True，否则返回False
        """
        if self.state == ServiceState.RUNNING:
            self._log("服务已在运行中")
            return False
        
        port_str = self.get_config_value("server.port")
        port = int(port_str) if port_str else 8000
        
        if not self.check_port_available(port):
            self._log(f"端口 {port} 已被占用，尝试停止占用端口的进程...")
            if not self._stop_port_processes(port):
                self._log(f"无法释放端口 {port}")
                return False
        
        self.state = ServiceState.STARTING
        self._log("正在启动服务...")
        
        try:
            python_path = self._get_python_executable()
            app_path = self._get_app_path()
            
            self._log(f"启动命令: {python_path} {app_path}")
            
            env = os.environ.copy()
            env["PYTHONPATH"] = os.path.dirname(os.path.dirname(app_path))
            
            self.process = subprocess.Popen(
                [python_path, app_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env=env,
                cwd=os.path.dirname(app_path),
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
            )
            
            self._log(f"进程已启动, PID: {self.process.pid}")
            
            if block:
                return self._wait_for_startup(timeout)
            else:
                threading.Thread(target=self._read_output, daemon=True).start()
                time.sleep(0.5)
                
                if self.is_running():
                    self.state = ServiceState.RUNNING
                    self._log("服务启动成功")
                    return True
                else:
                    self.state = ServiceState.STARTING
                    self._log("服务启动中...")
                    return True
                
        except FileNotFoundError as e:
            self.state = ServiceState.ERROR
            self._log(f"服务启动失败: 找不到文件 - {e}")
            return False
        except PermissionError as e:
            self.state = ServiceState.ERROR
            self._log(f"服务启动失败: 权限不足 - {e}")
            return False
        except subprocess.SubprocessError as e:
            self.state = ServiceState.ERROR
            self._log(f"服务启动失败: 子进程错误 - {e}")
            return False
        except Exception as e:
            self.state = ServiceState.ERROR
            self._log(f"服务启动失败: {type(e).__name__} - {e}")
            return False
    
    def _read_output(self) -> None:
        """读取进程输出"""
        if not self.process:
            return
        
        for line in iter(self.process.stdout.readline, ""):
            if line:
                self._log(line.rstrip())
        
        self.process.stdout.close()
    
    def _wait_for_startup(self, timeout: int) -> bool:
        """
        等待服务启动
        
        Args:
            timeout: 超时时间（秒）
            
        Returns:
            bool: 启动成功返回True，超时返回False
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if self.state == ServiceState.ERROR:
                return False
            
            if self.process is None:
                self._log("进程未初始化")
                return False
            
            poll_result = self.process.poll()
            if poll_result is not None:
                self._log(f"进程已退出，退出码: {poll_result}")
                self.state = ServiceState.ERROR
                return False
            
            try:
                port_str = self.get_config_value("server.port")
                port = int(port_str) if port_str else 8000
                import httpx
                response = httpx.get(f"http://localhost:{port}/health", timeout=2)
                if response.status_code == 200:
                    self.state = ServiceState.RUNNING
                    self._log("服务启动成功")
                    return True
            except Exception:
                pass
            
            time.sleep(0.5)
        
        self._log(f"服务启动超时（{timeout}秒）")
        return False
    
    def _stop_port_processes(self, port: int) -> bool:
        """
        停止占用指定端口的进程
        
        Args:
            port: 端口号
            
        Returns:
            bool: 成功返回True，否则返回False
        """
        try:
            pids = []
            
            if sys.platform == "win32":
                result = subprocess.run(
                    ["netstat", "-ano", f"| findstr :{port}"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    shell=True
                )
                if result.returncode == 0:
                    for line in result.stdout.strip().split("\n"):
                        if "LISTENING" in line:
                            parts = line.split()
                            if parts:
                                try:
                                    pid = int(parts[-1])
                                    pids.append(pid)
                                except (ValueError, IndexError):
                                    continue
            else:
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
            
            # 停止所有进程
            for pid in pids:
                try:
                    if sys.platform == "win32":
                        subprocess.run(
                            ["taskkill", "/F", "/PID", str(pid)],
                            capture_output=True,
                            timeout=5
                        )
                    else:
                        os.kill(pid, signal.SIGTERM)
                    
                    self._log(f"已停止进程 PID: {pid}")
                except Exception as e:
                    self._log(f"停止进程 PID:{pid} 失败: {e}")
                    continue
            
            # 等待端口释放
            time.sleep(1)
            return True
            
        except Exception as e:
            self._log(f"停止端口进程失败: {e}")
            return False
    
    def stop(self, timeout: int = 10) -> bool:
        """
        停止服务
        
        Args:
            timeout: 等待进程终止的超时时间（秒）
            
        Returns:
            bool: 停止成功返回True，否则返回False
        """
        # 更新服务状态，确保准确检测服务是否在运行
        self.get_state()
        
        if self.state == ServiceState.STOPPED:
            self._log("服务未运行")
            return True
        
        if self.state == ServiceState.STOPPING:
            self._log("服务正在停止中...")
            return True
        
        self.state = ServiceState.STOPPING
        self._log("正在停止服务...")
        
        if not self.process:
            # 检测服务是否通过端口在运行
            if self.is_running():
                self._log("检测到服务在运行，但无进程信息，尝试通过端口停止服务...")
                # 通过端口停止服务
                port_str = self.get_config_value("server.port")
                port = int(port_str) if port_str else 8000
                if self._stop_port_processes(port):
                    self.state = ServiceState.STOPPED
                    self._log("服务已停止")
                    return True
                else:
                    self.state = ServiceState.ERROR
                    self._log("服务停止失败")
                    return False
            else:
                self.state = ServiceState.STOPPED
                return True
        
        try:
            # 根据平台发送终止信号
            if sys.platform == "win32":
                self.process.terminate()
            else:
                self.process.send_signal(signal.SIGTERM)
            
            # 等待进程终止
            try:
                self.process.wait(timeout=timeout)
                self.state = ServiceState.STOPPED
                self._log("服务已停止")
                return True
            except subprocess.TimeoutExpired:
                # 如果超时，强制终止
                if sys.platform == "win32":
                    self.process.kill()
                else:
                    self.process.kill()
                
                self.process.wait(timeout=5)
                self.state = ServiceState.STOPPED
                self._log("服务已强制停止")
                return True
                
        except Exception as e:
            self.state = ServiceState.ERROR
            self._log(f"服务停止失败: {e}")
            return False
    
    def restart(self, timeout: int = 10) -> bool:
        """
        重启服务
        
        Args:
            timeout: 等待服务重启的超时时间（秒）
            
        Returns:
            bool: 重启成功返回True，否则返回False
        """
        self._log("正在重启服务...")
        
        was_running = self.state == ServiceState.RUNNING
        
        if was_running:
            if not self.stop(timeout):
                return False
            
            # 等待完全停止
            time.sleep(1)
        
        return self.start(block=True, timeout=timeout)
    
    def is_running(self) -> bool:
        """
        检查服务是否正在运行
        
        检测逻辑：
        1. 首先检查当前控制器实例的进程是否在运行
        2. 如果进程信息不可用，则通过端口检测判断服务是否在运行
        3. 最后通过进程名称检测确认服务状态
        
        Returns:
            bool: 运行中返回True，否则返回False
        """
        # 检查当前控制器实例的进程是否在运行
        if self.process:
            if self.process.poll() is None:
                return True
        
        # 通过端口检测服务是否在运行
        port_str = self.get_config_value("server.port")
        port = int(port_str) if port_str else 8000
        
        # 检查端口是否被占用且响应HTTP请求
        try:
            import httpx
            response = httpx.get(f"http://localhost:{port}/health", timeout=2)
            if response.status_code == 200:
                return True
        except Exception:
            pass
        
        # 通过进程名称检测服务是否在运行
        try:
            import subprocess
            import sys
            import os
            
            current_pid = os.getpid()
            
            if sys.platform == "win32":
                # Windows平台：通过进程命令行检测
                result = subprocess.run(
                    ["wmic", "process", "get", "CommandLine,ProcessId"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                # 遍历进程列表，查找app.py进程（排除当前进程）
                found = False
                for line in result.stdout.strip().split('\n'):
                    line = line.strip()
                    if not line:
                        continue
                    
                    # 提取PID和命令行
                    parts = line.split(maxsplit=1)
                    if len(parts) < 2:
                        continue
                    
                    try:
                        pid = int(parts[0].strip())
                        cmdline = parts[1].strip()
                        
                        # 排除当前进程
                        if pid == current_pid:
                            continue
                        
                        # 精确匹配app.py，避免误判
                        if 'app.py' in cmdline and not any(test_script in cmdline for test_script in ['test_', 'pytest', 'debugpy']):
                            found = True
                            break
                    except (ValueError, IndexError):
                        continue
                
                return found
            else:
                # Linux/macOS平台：通过ps命令检测
                result = subprocess.run(
                    ["ps", "aux"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                # 遍历进程列表，查找app.py进程（排除当前进程）
                found = False
                for line in result.stdout.strip().split('\n'):
                    line = line.strip()
                    if not line:
                        continue
                    
                    # 提取PID
                    parts = line.split()
                    if len(parts) < 2:
                        continue
                    
                    try:
                        pid = int(parts[1])
                        
                        # 排除当前进程
                        if pid == current_pid:
                            continue
                        
                        # 精确匹配app.py，避免误判
                        if 'app.py' in line and not any(test_script in line for test_script in ['test_', 'pytest', 'debugpy']):
                            found = True
                            break
                    except (ValueError, IndexError):
                        continue
                
                return found
        except Exception:
            pass
        
        return False
    
    def get_state(self) -> ServiceState:
        """
        获取服务当前状态
        
        Returns:
            ServiceState: 服务状态
        """
        if self.is_running():
            # 如果检测到服务正在运行，更新状态为RUNNING
            self.state = ServiceState.RUNNING
        elif self.state != ServiceState.STARTING and self.state != ServiceState.STOPPING:
            # 如果服务不在运行且不是正在启动/停止，更新状态为STOPPED
            self.state = ServiceState.STOPPED
        
        return self.state


# 创建全局服务控制器实例
_service_controller: Optional[ServiceController] = None


def get_service_controller(config_path: str = "config.toml") -> ServiceController:
    """
    获取全局服务控制器实例
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        ServiceController: 服务控制器实例
    """
    global _service_controller
    if _service_controller is None:
        _service_controller = ServiceController(config_path)
    return _service_controller
