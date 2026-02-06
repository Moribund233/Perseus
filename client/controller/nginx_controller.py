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
        self.config_path = config_path
        self.process: Optional[subprocess.Popen] = None
        self.state = NginxState.STOPPED
        self.log_manager = get_log_manager()
        
        # 从配置文件中读取Nginx配置
        nginx_config = self.get_nginx_config()
        
        # 初始化NginxDownloader
        self.nginx_downloader = NginxDownloader(
            nginx_version=nginx_config.get("version", "1.26.0"),
            install_path=nginx_config.get("install_path", "nginx")
        )
        
        # 初始化NginxConfigGenerator
        self.nginx_generator = NginxConfigGenerator(os.path.join(nginx_config.get("install_path", "nginx"), "conf", "nginx.conf"))
    
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
            return config.get("proxy", {}).get("enabled", False)
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
        
        # 检查Nginx是否已安装
        if not self.is_nginx_installed():
            self._log("Nginx未安装，正在安装...")
            if not self.install_nginx():
                self._log("Nginx安装失败，无法启动")
                return False
        
        # 生成Nginx配置文件
        if not self.generate_nginx_config():
            self._log("Nginx配置文件生成失败，无法启动")
            return False
        
        self.state = NginxState.STARTING
        self._log("正在启动Nginx...")
        
        try:
            nginx_path = self.nginx_downloader.get_nginx_path()
            # 转换为绝对路径
            nginx_path = os.path.abspath(nginx_path)
            self._log(f"Nginx可执行文件绝对路径: {nginx_path}")
            
            if sys.platform == "win32":
                # 检查Nginx可执行文件是否存在
                if not os.path.exists(nginx_path):
                    self._log(f"Nginx可执行文件不存在: {nginx_path}")
                    return False
                
                # Windows下启动Nginx
                cmd = [nginx_path]
                self._log(f"Windows下执行命令: {cmd}")
                
                # 尝试检查配置文件
                check_cmd = [nginx_path, "-t"]
                check_result = subprocess.run(check_cmd, capture_output=True, text=True)
                self._log(f"配置检查结果: 返回码={check_result.returncode}, 标准输出={check_result.stdout}, 标准错误={check_result.stderr}")
                
                # 如果配置检查失败，返回错误
                if check_result.returncode != 0:
                    self._log(f"Nginx配置文件错误: {check_result.stderr}")
                    return False
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                self._log(f"命令执行结果: 返回码={result.returncode}, 标准输出={result.stdout}, 标准错误={result.stderr}")
                
                # Nginx在Windows下启动成功时返回码为0，并且stdout和stderr都为空
                # 但有时候即使返回码为1，Nginx也可能已经启动成功（例如，当配置文件中的某些选项不被支持时）
                # 所以我们需要检查Nginx是否真的在运行
                if result.returncode != 0:
                    self._log(f"Nginx启动命令返回错误，但将检查是否真的在运行: {result.stderr}")
                    
                # 检查Nginx是否真的在运行
                if self.is_running():
                    self.state = NginxState.RUNNING
                    self._log("Nginx启动成功")
                    return True
                else:
                    raise subprocess.CalledProcessError(result.returncode, cmd)
            else:
                # Linux下启动Nginx
                cmd = ["nginx"]
                self._log(f"Linux下执行命令: {cmd}")
                result = subprocess.run(cmd, capture_output=True, text=True)
                self._log(f"命令执行结果: 返回码={result.returncode}, 标准输出={result.stdout}, 标准错误={result.stderr}")
                
                if result.returncode != 0:
                    raise subprocess.CalledProcessError(result.returncode, cmd)
            
            self.state = NginxState.RUNNING
            self._log("Nginx启动成功")
            return True
        except subprocess.CalledProcessError as e:
            self.state = NginxState.ERROR
            self._log(f"Nginx启动失败 - 命令执行错误: {e}")
            return False
        except Exception as e:
            self.state = NginxState.ERROR
            self._log(f"Nginx启动失败 - 其他错误: {type(e).__name__}: {str(e)}")
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
            nginx_path = self.nginx_downloader.get_nginx_path()
            if sys.platform == "win32":
                # Windows下停止Nginx
                cmd = [nginx_path, "-s", "quit"]
                subprocess.run(cmd, check=True, capture_output=True)
            else:
                # Linux下停止Nginx
                cmd = ["nginx", "-s", "quit"]
                subprocess.run(cmd, check=True, capture_output=True)
            
            # 等待Nginx完全停止
            time.sleep(1)
            
            # 如果Nginx仍在运行，强制停止
            if self.is_running():
                self._log("Nginx仍在运行，尝试强制停止...")
                self._force_stop()
            
            self.state = NginxState.STOPPED
            self._log("Nginx停止成功")
            return True
        except subprocess.CalledProcessError as e:
            self._log(f"Nginx停止命令执行失败: {e.stderr.decode() if e.stderr else str(e)}")
            # 尝试强制停止
            self._force_stop()
            return False
        except Exception as e:
            self._log(f"Nginx停止失败: {str(e)}")
            # 尝试强制停止
            self._force_stop()
            return False
    
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
                result = subprocess.run(["lsof", "-i", ":80", "-t"], capture_output=True, text=True)
                if result.returncode == 0 and result.stdout.strip():
                    pid = int(result.stdout.strip())
                    os.kill(pid, signal.SIGTERM)
                    time.sleep(1)
                    # 如果仍在运行，使用SIGKILL
                    if subprocess.run(["lsof", "-i", ":80", "-t"], capture_output=True, text=True).stdout.strip():
                        os.kill(pid, signal.SIGKILL)
            
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
