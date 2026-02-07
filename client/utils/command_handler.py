"""
命令处理模块

提供统一的命令处理功能，消除CLI和UI之间的重复代码。
"""
from typing import Dict, Any, Optional
from client.controller.service_controller import ServiceController
from client.utils.config_manager import ClientConfigManager


class CommandHandler:
    """
    命令处理器类
    
    负责统一处理各种命令，包括服务管理和配置操作。
    被CLI和UI界面共用，消除重复代码。
    """
    
    def __init__(self, controller: ServiceController, config_manager: ClientConfigManager):
        """
        初始化命令处理器
        
        Args:
            controller: 服务控制器实例
            config_manager: 配置管理器实例
        """
        self.controller = controller
        self.config_manager = config_manager
    
    def handle_start(self, block: bool = False, timeout: int = 10) -> tuple[bool, str]:
        """
        处理启动服务命令
        
        Args:
            block: 是否阻塞等待服务启动
            timeout: 超时时间（秒）
        
        Returns:
            tuple: (是否成功, 结果消息)
        """
        if self.controller.start(block=block, timeout=timeout):
            return True, "服务启动成功"
        else:
            return False, "服务启动失败"
    
    def handle_stop(self, timeout: int = 10) -> tuple[bool, str]:
        """
        处理停止服务命令
        
        Args:
            timeout: 超时时间（秒）
        
        Returns:
            tuple: (是否成功, 结果消息)
        """
        if self.controller.stop(timeout=timeout):
            return True, "服务停止成功"
        else:
            return False, "服务停止失败"
    
    def handle_restart(self, timeout: int = 15) -> tuple[bool, str]:
        """
        处理重启服务命令
        
        Args:
            timeout: 超时时间（秒）
        
        Returns:
            tuple: (是否成功, 结果消息)
        """
        if self.controller.restart(timeout=timeout):
            return True, "服务重启成功"
        else:
            return False, "服务重启失败"
    
    def handle_status(self) -> Dict[str, Any]:
        """
        处理查看服务状态命令
        
        Returns:
            Dict: 服务状态信息
        """
        state = self.controller.get_state()
        is_running = self.controller.is_running()
        
        status_info = {
            "state": state.value,
            "is_running": is_running
        }
        
        if is_running:
            # 使用config_manager获取配置值
            port = self.config_manager.get("server.port")
            host = self.config_manager.get("server.host")
            status_info["address"] = f"http://{host}:{port}"
            
            if hasattr(self.controller, 'process') and self.controller.process:
                status_info["pid"] = self.controller.process.pid
        
        return status_info
    
    def handle_logs(self, lines: int = 100) -> list[str]:
        """
        处理查看日志命令
        
        Args:
            lines: 显示日志行数
        
        Returns:
            list: 日志行列表
        """
        return self.controller.get_logs(lines=lines)
    
    def handle_clear_logs(self) -> tuple[bool, str]:
        """
        处理清除日志命令
        
        Returns:
            tuple: (是否成功, 结果消息)
        """
        self.controller.clear_logs()
        return True, "日志已清除"
    
    def handle_update_config(self, key: str, value: str) -> tuple[bool, str]:
        """
        处理更新配置命令
        
        Args:
            key: 配置键名
            value: 新的配置值
        
        Returns:
            tuple: (是否成功, 结果消息)
        """
        if self.controller.update_config(key, value):
            return True, f"配置已更新: {key} = {value}"
        else:
            return False, "配置更新失败"
    
    def handle_get_config(self, server_only: bool = False, app_only: bool = False, nginx_only: bool = False) -> Dict[str, Any]:
        """
        处理获取配置命令
        
        Args:
            server_only: 只获取服务器配置
            app_only: 只获取应用配置
            nginx_only: 只获取Nginx配置
        
        Returns:
            Dict: 配置信息
        """
        config = self.config_manager.load_config()
        
        if server_only:
            return {"server": config.get("server", {})}
        elif app_only:
            return {"app": config.get("app", {})}
        elif nginx_only:
            return {"nginx": config.get("nginx", {})}
        else:
            return config
    
    def handle_reset_config(self) -> tuple[bool, str]:
        """
        处理重置配置命令
        
        Returns:
            tuple: (是否成功, 结果消息)
        """
        if self.config_manager.reset_to_defaults():
            return True, "配置已重置为默认值"
        else:
            return False, "配置重置失败"
    
    def handle_validate_config(self) -> tuple[bool, list[str]]:
        """
        处理验证配置命令
        
        Returns:
            tuple: (是否有效, 错误信息列表)
        """
        return self.config_manager.validate_config()
    
    def handle_get_nginx_config(self) -> Dict[str, Any]:
        """
        处理获取Nginx配置命令
        
        Returns:
            Dict: Nginx配置信息
        """
        return {"nginx": self.config_manager.get_nginx_config()}
    
    def handle_generate_nginx_config(self) -> tuple[bool, str]:
        """
        处理生成Nginx配置文件命令
        
        Returns:
            tuple: (是否成功, 结果消息)
        """
        from client.utils.nginx import generate_nginx_config
        nginx_config = self.config_manager.get_nginx_config()
        if generate_nginx_config(nginx_config):
            return True, "Nginx配置文件生成成功"
        else:
            return False, "Nginx配置文件生成失败"
    
    def handle_nginx_start(self) -> tuple[bool, str]:
        """
        处理启动Nginx命令
        
        Returns:
            tuple: (是否成功, 结果消息)
        """
        # 直接调用nginx_controller的start方法并获取结果
        success = self.controller.nginx_controller.start()
        
        # 直接返回结果，不依赖日志
        if success:
            return True, "Nginx启动成功"
        else:
            return False, "Nginx启动失败"
    
    def handle_nginx_stop(self) -> tuple[bool, str]:
        """
        处理停止Nginx命令
        
        Returns:
            tuple: (是否成功, 结果消息)
        """
        if self.controller.nginx_controller.stop():
            return True, "Nginx停止成功"
        else:
            return False, "Nginx停止失败"
    
    def handle_nginx_restart(self) -> tuple[bool, str]:
        """
        处理重启Nginx命令
        
        Returns:
            tuple: (是否成功, 结果消息)
        """
        if self.controller.nginx_controller.restart():
            return True, "Nginx重启成功"
        else:
            return False, "Nginx重启失败"
    
    def handle_nginx_status(self) -> tuple[bool, Dict[str, Any]]:
        """
        处理查看Nginx状态命令
        
        Returns:
            tuple: (是否成功, Nginx状态信息)
        """
        try:
            is_running = self.controller.nginx_controller.is_running()
            state = self.controller.nginx_controller.get_state()
            is_installed = self.controller.nginx_controller.is_nginx_installed()
            is_proxy_enabled = self.controller.nginx_controller.is_proxy_enabled()
            
            status_info = {
                "state": state.value,
                "is_running": is_running,
                "is_installed": is_installed,
                "is_proxy_enabled": is_proxy_enabled
            }
            
            return True, status_info
        except Exception as e:
            return False, {"error": str(e)}
    
    def handle_nginx_install(self) -> tuple[bool, str]:
        """
        处理安装Nginx命令
        
        Returns:
            tuple: (是否成功, 结果消息)
        """
        if self.controller.nginx_controller.install_nginx():
            return True, "Nginx安装成功"
        else:
            return False, "Nginx安装失败"
