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
from client.controller.nginx_controller import get_nginx_controller


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
        self.nginx_controller = get_nginx_controller(config_path)
    
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
    
    def start(self, block: bool = False, timeout: int = 10) -> bool:
        """
        启动服务
        
        Args:
            block: 是否阻塞等待服务启动
            timeout: 阻塞等待的超时时间（秒）
            
        Returns:
            bool: 启动成功返回True，否则返回False
        """
        if self.is_running():
            self._log("服务已在运行中")
            return False
        
        port_str = self.get_config_value("server.port")
        port = int(port_str) if port_str else 8000
        
        # 检查并释放端口
        if not self.check_port_available(port):
            self._log(f"端口 {port} 已被占用，尝试停止占用端口的进程...")
            if not self._stop_port_processes(port):
                self._log(f"无法释放端口 {port}")
                return False
        
        self.state = ServiceState.STARTING
        self._log("正在启动服务...")
        
        try:
            # 直接调用uvicorn.run()函数启动服务，使用线程避免阻塞主线程
            from app import get_app
            import uvicorn
            
            # 获取配置
            host = self.get_config_value("server.host") or "127.0.0.1"
            log_level = self.get_config_value("server.log_level") or "info"
            
            # 禁用reload模式，在打包应用中reload会导致问题
            reload = False
            
            # 构建uvicorn配置
            config = uvicorn.Config(
                app=get_app(),
                host=host,
                port=port,
                reload=reload,
                log_level=log_level,
                workers=1
            )
            
            # 创建服务器实例
            server = uvicorn.Server(config)
            
            # 定义服务运行函数
            def run_server():
                try:
                    self._log(f"正在启动uvicorn服务: http://{host}:{port}")
                    server.run()
                except Exception as e:
                    self._log(f"服务运行失败: {type(e).__name__} - {e}")
                    self.state = ServiceState.ERROR
            
            # 保存服务器实例，用于后续停止服务
            self.server = server
            
            # 创建并启动服务线程
            self.server_thread = threading.Thread(target=run_server, daemon=True)
            self.server_thread.start()
            
            if block:
                success = self._wait_for_startup(timeout)
                if success:
                    self.state = ServiceState.RUNNING
                    # 启动服务后，根据代理配置启动Nginx
                    self.nginx_controller.start()
                return success
            else:
                self.state = ServiceState.RUNNING
                self._log("服务启动成功")
                # 启动服务后，根据代理配置启动Nginx
                self.nginx_controller.start()
                return True
                
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
            
            # 检查服务线程是否在运行
            if hasattr(self, 'server_thread') and self.server_thread.is_alive():
                # 尝试HTTP请求检测服务是否可用
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
            elif self.state == ServiceState.ERROR:
                return False
            
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
            timeout: 等待服务停止的超时时间（秒）
            
        Returns:
            bool: 停止成功返回True，否则返回False
        """
        if not self.is_running():
            self._log("服务未运行")
            return True
        
        if self.state == ServiceState.STOPPING:
            self._log("服务正在停止中...")
            return True
        
        self.state = ServiceState.STOPPING
        self._log("正在停止服务...")
        
        # 停止服务线程
        if hasattr(self, 'server') and hasattr(self, 'server_thread'):
            try:
                # 使用uvicorn的should_exit属性优雅停止服务器
                self.server.should_exit = True
                
                # 等待服务线程结束
                self._log("正在等待服务线程结束...")
                start_time = time.time()
                while self.server_thread.is_alive() and (time.time() - start_time) < timeout:
                    time.sleep(0.5)
                
                if self.server_thread.is_alive():
                    self._log("服务线程仍在运行，正在强制释放端口...")
                else:
                    self._log("服务线程已正常结束")
                
                # 清除服务器和线程属性
                delattr(self, 'server')
                delattr(self, 'server_thread')
            except Exception as e:
                self._log(f"停止服务线程失败: {e}")
        
        # 确保端口已释放
        port_str = self.get_config_value("server.port")
        port = int(port_str) if port_str else 8000
        self._stop_port_processes(port)
        
        # 停止服务后，停止Nginx
        self.nginx_controller.stop()
        
        # 更新服务状态
        self.state = ServiceState.STOPPED
        self._log("服务已停止")
        return True
    
    def restart(self, timeout: int = 10) -> bool:
        """
        重启服务
        
        Args:
            timeout: 等待服务重启的超时时间（秒）
            
        Returns:
            bool: 重启成功返回True，否则返回False
        """
        self._log("正在重启服务...")
        
        try:
            # 1. 停止服务（会自动停止Nginx）
            if not self.stop(timeout):
                self._log("服务停止失败，重启中断")
                return False
            
            # 2. 启动服务（会自动根据代理配置启动Nginx）
            return self.start(block=True, timeout=timeout)
        except Exception as e:
            self.state = ServiceState.ERROR
            self._log(f"服务重启失败: {type(e).__name__} - {e}")
            return False
    
    def is_running(self) -> bool:
        """
        检查服务是否正在运行
        
        检测逻辑：
        1. 首先检查服务线程是否在运行（最快）
        2. 检查端口是否被占用（中等速度）
        3. 最后通过HTTP请求检测健康端点（较慢，仅作为确认）
        
        Returns:
            bool: 运行中返回True，否则返回False
        """
        # 1. 检查服务线程是否在运行（最快）
        if hasattr(self, 'server_thread') and self.server_thread.is_alive():
            return True
        
        # 2. 检查端口是否被占用（中等速度）
        port_str = self.get_config_value("server.port")
        port = int(port_str) if port_str else 8000
        
        # 先快速检查端口是否被占用，避免不必要的HTTP请求
        if not self.check_port_available(port):
            # 端口被占用，再尝试HTTP请求确认是否是我们的服务
            try:
                import httpx
                # 使用更短的超时时间，避免阻塞
                response = httpx.get(f"http://localhost:{port}/health", timeout=0.5)
                if response.status_code == 200:
                    return True
            except Exception:
                # HTTP请求失败，可能是其他服务占用了端口
                pass
        
        return False
    
    def get_state(self) -> ServiceState:
        """
        获取服务当前状态
        
        Returns:
            ServiceState: 服务状态
        """
        if self.is_running():
            # 如果检测到服务正在运行，无论之前是什么状态，都更新为RUNNING
            self.state = ServiceState.RUNNING
        elif self.state != ServiceState.STARTING and self.state != ServiceState.STOPPING:
            # 如果服务不在运行且不是正在启动/停止，更新状态为STOPPED
            self.state = ServiceState.STOPPED
        elif self.state == ServiceState.STARTING:
            # 如果服务正在启动中，但is_running()返回True，更新为RUNNING
            if self.is_running():
                self.state = ServiceState.RUNNING
        
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