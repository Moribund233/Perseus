"""
Nginx控制器模块

提供Nginx服务器的生命周期管理功能，包括启动、停止、重启等操作。
"""
import os
import sys
import subprocess
import time
import signal
from typing import Optional, Callable, List
from enum import Enum
from client.utils.log_manager import get_log_manager
from client.utils.nginx import NginxDownloader, NginxConfigGenerator


class NginxState(Enum):
    """Nginx状态枚举"""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"


class NginxController:
    """
    Nginx控制器类
    
    负责管理Nginx服务器的生命周期：启动、停止、重启等。
    """
    
    def __init__(self, config_path: str = "config.toml"):
        """
        初始化Nginx控制器
        
        Args:
            config_path: 配置文件路径
        """
        self.config_path = os.path.abspath(config_path)
        self.process: Optional[subprocess.Popen] = None
        self.state = NginxState.STOPPED
        self.log_manager = get_log_manager()
        
        # 从配置文件中读取Nginx配置
        nginx_config = self.get_nginx_config()
        
        # 获取install_path和config_path
        install_path = nginx_config.get("install_path", "nginx")
        config_path_nginx = nginx_config.get("config_path")

        # 确保install_path是绝对路径
        if install_path:
            install_path = os.path.abspath(install_path)
        
        # 初始化NginxDownloader
        self.nginx_downloader = NginxDownloader(
            nginx_version=nginx_config.get("version", "1.26.0"),
            install_path=install_path
        )
        
        # 初始化NginxConfigGenerator
        # 优先使用config_path，否则根据install_path生成
        self.nginx_generator = NginxConfigGenerator(config_path_nginx, install_path)
    
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
    
    def is_proxy_enabled(self) -> bool:
        """
        检查是否启用了代理
        
        Returns:
            bool: 启用代理返回True，否则返回False
        """
        try:
            import toml
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = toml.load(f)
            return config.get("nginx", {}).get("proxy", False)
        except Exception as e:
            self._log(f"检查代理配置失败: {e}")
            return False
    
    def get_nginx_config(self) -> dict:
        """
        获取Nginx配置
        
        Returns:
            dict: Nginx配置
        """
        try:
            import toml
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = toml.load(f)
            return config.get("nginx", {})
        except Exception as e:
            self._log(f"获取Nginx配置失败: {e}")
            return {}
    
    def is_nginx_installed(self) -> bool:
        """
        检查Nginx是否已安装
        
        Returns:
            bool: Nginx已安装返回True，否则返回False
        """
        return self.nginx_downloader.is_nginx_installed()
    
    def install_nginx(self) -> bool:
        """
        安装Nginx
        
        Returns:
            bool: 安装成功返回True，否则返回False
        """
        try:
            self._log("正在安装Nginx...")
            self.nginx_downloader.run()
            self._log("Nginx安装成功")
            return True
        except Exception as e:
            self._log(f"Nginx安装失败: {e}")
            return False
    
    def generate_nginx_config(self) -> bool:
        """
        生成Nginx配置文件
        
        Returns:
            bool: 生成成功返回True，否则返回False
        """
        try:
            nginx_config = self.get_nginx_config()
            self.nginx_generator.generate_config(nginx_config)
            self._log("Nginx配置文件生成成功")
            return True
        except Exception as e:
            self._log(f"Nginx配置文件生成失败: {e}")
            return False
    
    def start(self) -> bool:
        """
        启动Nginx服务器
        
        Returns:
            bool: 启动成功返回True，否则返回False
        """
        if not self.is_proxy_enabled():
            self._log("代理未启用，无需启动Nginx")
            return True
        
        if self.is_running():
            self._log("Nginx已在运行中")
            return True
        
        self.state = NginxState.STARTING
        self._log("正在启动Nginx...")
        
        try:
            nginx_path = self.nginx_downloader.get_nginx_path()
            # nginx_path 已经是绝对路径（由 NginxDownloader 保证）
            self._log(f"Nginx可执行文件绝对路径: {nginx_path}")
            
            # 获取Nginx工作目录（nginx.exe所在目录）
            nginx_cwd = os.path.dirname(nginx_path)
            self._log(f"Nginx工作目录: {nginx_cwd}")
            
            # 获取配置文件绝对路径
            config_path = os.path.abspath(self.nginx_generator._config_path)
            self._log(f"Nginx配置文件绝对路径: {config_path}")
            
            if sys.platform == "win32":
                # 检查Nginx可执行文件是否存在
                if not os.path.exists(nginx_path):
                    self._log(f"Nginx可执行文件不存在: {nginx_path}")
                    return False
                
                # 检查配置文件是否存在
                if not os.path.exists(config_path):
                    self._log(f"Nginx配置文件不存在: {config_path}")
                    return False
                
                # Windows下启动Nginx，使用-c参数指定配置文件路径，并设置工作目录
                cmd = [nginx_path, "-c", config_path]
                self._log(f"Windows下执行命令: {cmd}")
                
                # 尝试检查配置文件
                check_cmd = [nginx_path, "-t", "-c", config_path]
                try:
                    check_result = subprocess.run(check_cmd, capture_output=True, text=True, cwd=nginx_cwd, timeout=10)
                    self._log(f"配置检查结果: 返回码={check_result.returncode}")
                    if check_result.stderr:
                        # 区分错误信息和正常信息
                        stderr_text = check_result.stderr
                        if "successful" in stderr_text.lower() or "ok" in stderr_text.lower():
                            self._log(f"配置检查信息: {stderr_text}")
                        else:
                            self._log(f"配置检查错误: {stderr_text}")
                except subprocess.TimeoutExpired:
                    self._log("配置检查超时")
                    self.state = NginxState.ERROR
                    return False
                except Exception as e:
                    self._log(f"配置检查异常: {type(e).__name__}: {e}")
                    self.state = NginxState.ERROR
                    return False
                
                # 如果配置检查失败，返回错误
                if check_result.returncode != 0:
                    self._log(f"Nginx配置文件错误，返回码: {check_result.returncode}")
                    self.state = NginxState.ERROR
                    return False
                
                # 启动Nginx - 使用Popen非阻塞启动
                try:
                    # Nginx是守护进程，启动后会立即返回
                    process = subprocess.Popen(
                        cmd,
                        cwd=nginx_cwd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                    )
                    
                    # 等待短时间检查是否立即失败
                    try:
                        stdout, stderr = process.communicate(timeout=2)
                        if process.returncode != 0:
                            self._log(f"Nginx启动失败，返回码: {process.returncode}")
                            if stderr:
                                self._log(f"错误信息: {stderr.decode('utf-8', errors='ignore')}")
                            self.state = NginxState.ERROR
                            return False
                    except subprocess.TimeoutExpired:
                        # 超时说明Nginx正在运行（正常情况）
                        self._log("Nginx进程已启动")
                        pass
                    
                except Exception as e:
                    self._log(f"启动命令异常: {type(e).__name__}: {e}")
                
                # 检查Nginx是否真的在运行
                import time
                time.sleep(1)  # 等待1秒让Nginx启动
                
                if self.is_running():
                    self.state = NginxState.RUNNING
                    self._log("Nginx启动成功")
                    return True
                else:
                    self._log("Nginx启动后未检测到运行状态")
                    self.state = NginxState.ERROR
                    return False
            else:
                # Linux下启动Nginx，使用-c参数指定配置文件路径
                # 首先检查Nginx是否已安装
                nginx_cmd = self._get_linux_nginx_cmd()
                if not nginx_cmd:
                    self._log("错误: 未找到Nginx可执行文件，请确保已通过包管理器安装Nginx")
                    self.state = NginxState.ERROR
                    return False
                
                self._log(f"Linux Nginx命令: {nginx_cmd}")
                self._log(f"Linux配置文件路径: {config_path}")
                
                # 检查配置文件是否存在
                if not os.path.exists(config_path):
                    self._log(f"错误: Nginx配置文件不存在: {config_path}")
                    self.state = NginxState.ERROR
                    return False
                
                cmd = [nginx_cmd, "-c", config_path]
                self._log(f"Linux下执行命令: {cmd}")
                
                # 检查配置是否正确
                try:
                    check_cmd = [nginx_cmd, "-t", "-c", config_path]
                    self._log(f"检查Nginx配置: {check_cmd}")
                    check_result = subprocess.run(check_cmd, capture_output=True, text=True, timeout=10)
                    if check_result.returncode != 0:
                        self._log(f"配置检查失败: {check_result.stderr}")
                        self.state = NginxState.ERROR
                        return False
                    self._log("配置检查通过")
                except Exception as e:
                    self._log(f"配置检查异常: {type(e).__name__}: {e}")
                
                # 启动Nginx - 使用Popen非阻塞启动
                try:
                    # Nginx是守护进程，启动后会立即返回
                    process = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE
                    )
                    
                    # 等待短时间检查是否立即失败
                    try:
                        stdout, stderr = process.communicate(timeout=2)
                        if process.returncode != 0:
                            self._log(f"Nginx启动失败，返回码: {process.returncode}")
                            if stderr:
                                self._log(f"错误信息: {stderr.decode('utf-8', errors='ignore')}")
                            self.state = NginxState.ERROR
                            return False
                    except subprocess.TimeoutExpired:
                        # 超时说明Nginx正在运行（正常情况）
                        self._log("Nginx进程已启动")
                        pass
                    
                except Exception as e:
                    self._log(f"启动命令异常: {type(e).__name__}: {e}")
                
                # 检查Nginx是否真的在运行
                import time
                time.sleep(1)
                
                if self.is_running():
                    self.state = NginxState.RUNNING
                    self._log("Nginx启动成功")
                    return True
                else:
                    self._log("Nginx启动后未检测到运行状态")
                    self.state = NginxState.ERROR
                    return False
            
        except Exception as e:
            self.state = NginxState.ERROR
            self._log(f"Nginx启动失败 - 错误: {type(e).__name__}: {str(e)}")
            return False
            return False
    
    def stop(self) -> bool:
        """
        停止Nginx服务器

        Returns:
            bool: 停止成功返回True，否则返回False
        """
        if not self.is_running():
            self._log("Nginx未运行")
            return True

        self.state = NginxState.STOPPING
        self._log("正在停止Nginx...")

        try:
            # 获取配置文件绝对路径
            config_path = os.path.abspath(self.nginx_generator._config_path)

            # 获取Nginx工作目录（nginx.exe所在目录）
            nginx_path = self.nginx_downloader.get_nginx_path()
            # nginx_path 已经是绝对路径（由 NginxDownloader 保证）
            nginx_cwd = os.path.dirname(nginx_path)
            self._log(f"Nginx工作目录: {nginx_cwd}")

            if sys.platform == "win32":
                # Windows下停止Nginx，使用-c参数指定配置文件路径，并设置工作目录
                cmd = [nginx_path, "-c", config_path, "-s", "quit"]
                self._log(f"Windows下停止命令: {cmd}")
                try:
                    result = subprocess.run(cmd, capture_output=True, text=True, cwd=nginx_cwd, timeout=10)
                    if result.returncode != 0:
                        self._log(f"停止命令返回非零码: {result.returncode}")
                        if result.stderr:
                            self._log(f"停止错误输出: {result.stderr}")
                except subprocess.TimeoutExpired:
                    self._log("停止命令超时")
                except Exception as e:
                    self._log(f"停止命令异常: {type(e).__name__}: {e}")
            else:
                # Linux下停止Nginx，使用-c参数指定配置文件路径
                nginx_cmd = self._get_linux_nginx_cmd()
                if not nginx_cmd:
                    self._log("错误: 未找到Nginx可执行文件")
                    self._force_stop()
                    return False

                cmd = [nginx_cmd, "-c", config_path, "-s", "quit"]
                self._log(f"Linux下停止命令: {cmd}")
                try:
                    # Linux下也需要设置工作目录为Nginx可执行文件所在目录
                    nginx_cwd = os.path.dirname(os.path.abspath(nginx_cmd))
                    if not nginx_cwd:
                        nginx_cwd = "/etc/nginx"  # 默认工作目录
                    result = subprocess.run(cmd, capture_output=True, text=True, cwd=nginx_cwd, timeout=10)
                    if result.returncode != 0:
                        self._log(f"停止命令返回非零码: {result.returncode}")
                        if result.stderr:
                            self._log(f"停止错误输出: {result.stderr}")
                except subprocess.TimeoutExpired:
                    self._log("停止命令超时")
                except Exception as e:
                    self._log(f"停止命令异常: {type(e).__name__}: {e}")
            
            # 等待Nginx完全停止
            time.sleep(2)
            
            # 如果Nginx仍在运行，强制停止
            if self.is_running():
                self._log("Nginx仍在运行，尝试强制停止...")
                self._force_stop()
            else:
                self.state = NginxState.STOPPED
                self._log("Nginx停止成功")
                return True
            
            self.state = NginxState.STOPPED
            self._log("Nginx停止成功")
            return True
        except Exception as e:
            self._log(f"Nginx停止失败: {str(e)}")
            # 尝试强制停止
            self._force_stop()
            return False
    
    def _get_linux_nginx_cmd(self) -> str:
        """
        获取Linux系统下的Nginx命令路径
        
        Returns:
            str: Nginx命令路径，如果未找到则返回空字符串
        """
        # Linux下使用which命令查找系统安装的Nginx
        # 不依赖install_path配置，因为Linux通过包管理器安装
        try:
            result = subprocess.run(["which", "nginx"], capture_output=True, text=True, check=True)
            nginx_path = result.stdout.strip()
            if nginx_path and os.path.isfile(nginx_path) and os.access(nginx_path, os.X_OK):
                return nginx_path
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
        
        # 尝试常见的安装路径
        common_paths = ["/usr/sbin/nginx", "/usr/local/nginx/sbin/nginx", "/opt/nginx/sbin/nginx"]
        for path in common_paths:
            if os.path.isfile(path) and os.access(path, os.X_OK):
                return path
        
        return ""
    
    def _force_stop(self) -> bool:
        """
        强制停止Nginx服务器
        
        Returns:
            bool: 强制停止成功返回True，否则返回False
        """
        try:
            if sys.platform == "win32":
                # Windows下强制停止Nginx进程
                subprocess.run(["taskkill", "/F", "/IM", "nginx.exe"], check=True, capture_output=True)
            else:
                # Linux下强制停止Nginx进程
                # 获取配置文件路径
                config_path = os.path.abspath(self.nginx_generator._config_path)
                nginx_cmd = self._get_linux_nginx_cmd()
                
                if nginx_cmd:
                    # 尝试使用nginx -s stop停止
                    try:
                        subprocess.run([nginx_cmd, "-c", config_path, "-s", "stop"], 
                                     capture_output=True, timeout=5)
                    except Exception:
                        pass
                
                # 查找并终止Nginx进程
                result = subprocess.run(["pgrep", "-f", f"nginx.*{config_path}"], 
                                      capture_output=True, text=True)
                if result.returncode == 0 and result.stdout.strip():
                    for pid_str in result.stdout.strip().split('\n'):
                        try:
                            pid = int(pid_str.strip())
                            os.kill(pid, signal.SIGTERM)
                        except (ValueError, ProcessLookupError):
                            continue
                    time.sleep(1)
                    # 如果仍在运行，使用SIGKILL
                    result = subprocess.run(["pgrep", "-f", f"nginx.*{config_path}"], 
                                          capture_output=True, text=True)
                    if result.returncode == 0 and result.stdout.strip():
                        for pid_str in result.stdout.strip().split('\n'):
                            try:
                                pid = int(pid_str.strip())
                                os.kill(pid, signal.SIGKILL)
                            except (ValueError, ProcessLookupError):
                                continue
            
            self.state = NginxState.STOPPED
            self._log("Nginx已强制停止")
            return True
        except Exception as e:
            self._log(f"Nginx强制停止失败: {str(e)}")
            self.state = NginxState.ERROR
            return False
    
    def restart(self) -> bool:
        """
        重启Nginx服务器
        
        Returns:
            bool: 重启成功返回True，否则返回False
        """
        self._log("正在重启Nginx...")
        
        if not self.stop():
            self._log("Nginx停止失败，重启中断")
            return False
        
        return self.start()
    
    def is_running(self) -> bool:
        """
        检查Nginx是否正在运行
        
        Returns:
            bool: 运行中返回True，否则返回False
        """
        try:
            if sys.platform == "win32":
                # Windows下检查Nginx进程
                result = subprocess.run(
                    ["tasklist", "/FI", "IMAGENAME eq nginx.exe"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                return "nginx.exe" in result.stdout
            else:
                # Linux下检查Nginx进程
                result = subprocess.run(
                    ["nginx", "-t"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                return result.returncode == 0
        except Exception as e:
            self._log(f"检查Nginx运行状态失败: {str(e)}")
            return False
    
    def get_state(self) -> NginxState:
        """
        获取Nginx当前状态
        
        Returns:
            NginxState: Nginx状态
        """
        if self.is_running():
            # 如果检测到Nginx正在运行，无论之前是什么状态，都更新为RUNNING
            self.state = NginxState.RUNNING
        elif self.state != NginxState.STARTING and self.state != NginxState.STOPPING:
            # 如果Nginx不在运行且不是正在启动/停止，更新状态为STOPPED
            self.state = NginxState.STOPPED
        elif self.state == NginxState.STARTING:
            # 如果Nginx正在启动中，但is_running()返回True，更新为RUNNING
            if self.is_running():
                self.state = NginxState.RUNNING
        
        return self.state


# 创建全局Nginx控制器实例
_nginx_controller: Optional[NginxController] = None


def get_nginx_controller(config_path: str = "config.toml") -> NginxController:
    """
    获取全局Nginx控制器实例
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        NginxController: Nginx控制器实例
    """
    global _nginx_controller
    if _nginx_controller is None:
        _nginx_controller = NginxController(config_path)
    return _nginx_controller
