"""
客户端配置管理模块

提供客户端级别的配置操作功能，包括配置读取、更新、验证等。
该模块被CLI和桌面客户端共用。
"""
import os
from typing import Any, Dict, Optional
import toml


class ClientConfigManager:
    """
    客户端配置管理器类
    
    负责客户端配置文件的读取、更新和验证。
    主要用于管理config.toml中的客户端相关配置。
    """
    
    def __init__(self, config_path: str = "config.toml"):
        """
        初始化配置管理器
        
        Args:
            config_path: 配置文件路径
        """
        self.config_path = config_path
    
    def load_config(self) -> Dict[str, Any]:
        """
        加载配置文件
        
        Returns:
            Dict[str, Any]: 配置数据
        """
        if not os.path.exists(self.config_path):
            print(f"配置文件不存在: {self.config_path}")
            return {}
        
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                return toml.load(f)
        except toml.TomlDecodeError as e:
            print(f"配置文件格式错误 ({self.config_path}): {e}")
            return {}
        except PermissionError as e:
            print(f"无权限读取配置文件 ({self.config_path}): {e}")
            return {}
        except IsADirectoryError as e:
            print(f"配置路径是目录，不是文件 ({self.config_path}): {e}")
            return {}
        except Exception as e:
            print(f"加载配置文件失败 ({self.config_path}): {type(e).__name__}: {e}")
            return {}
    
    def save_config(self, config: Dict[str, Any]) -> bool:
        """
        保存配置文件
        
        Args:
            config: 配置数据
            
        Returns:
            bool: 保存成功返回True，否则返回False
        """
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                toml.dump(config, f)
            return True
        except PermissionError as e:
            print(f"无权限写入配置文件 ({self.config_path}): {e}")
            return False
        except IsADirectoryError as e:
            print(f"配置路径是目录，不是文件 ({self.config_path}): {e}")
            return False
        except Exception as e:
            print(f"保存配置文件失败 ({self.config_path}): {type(e).__name__}: {e}")
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值
        
        支持点号分隔的嵌套键，如 'server.port'
        
        Args:
            key: 配置键名
            default: 默认值
            
        Returns:
            Any: 配置值，不存在返回默认值
        """
        config = self.load_config()
        
        keys = key.split(".")
        value = config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any) -> bool:
        """
        设置配置值
        
        支持点号分隔的嵌套键，如 'server.port'
        
        Args:
            key: 配置键名
            value: 配置值
            
        Returns:
            bool: 设置成功返回True，否则返回False
        """
        config = self.load_config()
        
        keys = key.split(".")
        current = config
        
        # 创建嵌套结构
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        
        current[keys[-1]] = value
        
        return self.save_config(config)
    
    def delete(self, key: str) -> bool:
        """
        删除配置项
        
        Args:
            key: 配置键名
            
        Returns:
            bool: 删除成功返回True，否则返回False
        """
        config = self.load_config()
        
        keys = key.split(".")
        current = config
        
        # 导航到父节点
        for k in keys[:-1]:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return False
        
        # 删除键
        if isinstance(current, dict) and keys[-1] in current:
            del current[keys[-1]]
            return self.save_config(config)
        
        return False
    
    def get_server_config(self) -> Dict[str, Any]:
        """
        获取服务器配置
        
        Returns:
            Dict[str, Any]: 服务器配置字典
        """
        config = self.load_config()
        return config.get("server", {})
    
    def get_app_config(self) -> Dict[str, Any]:
        """
        获取应用配置
        
        Returns:
            Dict[str, Any]: 应用配置字典
        """
        config = self.load_config()
        return config.get("app", {})
    
    def update_server_port(self, port: int) -> bool:
        """
        更新服务器端口
        
        Args:
            port: 新端口号
            
        Returns:
            bool: 更新成功返回True，否则返回False
        """
        return self.set("server.port", port)
    
    def update_server_host(self, host: str) -> bool:
        """
        更新服务器地址
        
        Args:
            host: 新服务器地址
            
        Returns:
            bool: 更新成功返回True，否则返回False
        """
        return self.set("server.host", host)
    
    def update_server_log_level(self, log_level: str) -> bool:
        """
        更新日志级别
        
        Args:
            log_level: 新日志级别
            
        Returns:
            bool: 更新成功返回True，否则返回False
        """
        valid_levels = ["debug", "info", "warning", "error", "critical"]
        if log_level not in valid_levels:
            print(f"无效的日志级别: {log_level}")
            print(f"可选值: {valid_levels}")
            return False
        
        return self.set("server.log_level", log_level)
    
    def reset_to_defaults(self) -> bool:
        """
        重置为默认值
        
        Returns:
            bool: 重置成功返回True，否则返回False
        """
        try:
            # 直接调用服务端init模块的reset_config方法
            from init import reset_config
            reset_config()
            return True
        except Exception as e:
            print(f"调用服务端重置配置方法失败: {e}")
            # 如果调用失败，使用备份的硬编码默认配置
            default_config = {
                "server": {
                    "host": "0.0.0.0",
                    "port": 8000,
                    "reload": False,
                    "workers": 1,
                    "log_level": "info"
                },
                "app": {
                    "title": "LanGit API",
                    "description": "A Git-based collaborative development tool API",
                    "version": "0.1.0",
                    "debug": True
                },
                "nginx": {
                "enabled": True,
                "proxy": False,
                "version": "1.26.0",
                "mirror_url": None,
                "install_path": "nginx",
                "worker_processes": "auto",
                "worker_connections": 1024,
                "keepalive_timeout": 65,
                "listen_port": 8080,
                "server_name": "localhost",
                "api_host": "localhost",
                "api_port": 8000
            }
            }
            return self.save_config(default_config)
    
    def validate_config(self) -> tuple[bool, list[str]]:
        """
        验证配置文件
        
        Returns:
            tuple: (是否有效, 错误信息列表)
        """
        errors = []
        config = self.load_config()
        
        # 验证服务器配置
        server = config.get("server", {})
        
        # 验证host格式
        if "host" in server:
            host = server["host"]
            if not isinstance(host, str) or not host:
                errors.append("服务器地址不能为空")
            else:
                # 简单的IP地址或主机名验证
                import re
                ip_pattern = r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$'
                hostname_pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?)*$'
                if host != "localhost" and host != "0.0.0.0" and not re.match(ip_pattern, host) and not re.match(hostname_pattern, host):
                    errors.append("服务器地址格式无效，请输入有效的IP地址或主机名")
        
        # 验证port范围
        if "port" in server:
            port = server["port"]
            try:
                port = int(port)
                if port < 1 or port > 65535:
                    errors.append("服务器端口必须是1-65535之间的整数")
            except (ValueError, TypeError):
                errors.append("服务器端口必须是1-65535之间的整数")
        
        # 验证reload是否为布尔值
        if "reload" in server and not isinstance(server["reload"], bool):
            errors.append("服务器热重载配置必须是布尔值")
        
        # 验证workers是否为正整数
        if "workers" in server:
            workers = server["workers"]
            try:
                workers = int(workers)
                if workers < 1:
                    errors.append("服务器工作进程数必须是正整数")
            except (ValueError, TypeError):
                errors.append("服务器工作进程数必须是正整数")
        
        # 验证log_level
        if "log_level" in server:
            log_level = server["log_level"]
            valid_levels = ["debug", "info", "warning", "error", "critical"]
            if log_level not in valid_levels:
                errors.append(f"日志级别必须是以下之一: {', '.join(valid_levels)}")
        
        # 验证应用配置
        app = config.get("app", {})
        
        # 验证title是否为非空字符串
        if "title" in app:
            if not isinstance(app["title"], str) or not app["title"].strip():
                errors.append("应用标题不能为空")
        
        # 验证description是否为字符串
        if "description" in app and not isinstance(app["description"], str):
            errors.append("应用描述必须是字符串")
        
        # 验证version格式
        if "version" in app:
            version = app["version"]
            if not isinstance(version, str):
                errors.append("应用版本必须是字符串")
            else:
                # 简单的版本格式验证 (x.y.z 或 x.y)
                import re
                version_pattern = r'^\d+(\.\d+){1,2}$'
                if not re.match(version_pattern, version):
                    errors.append("应用版本格式无效，建议使用 x.y.z 或 x.y 格式")
        
        # 验证debug是否为布尔值
        if "debug" in app and not isinstance(app["debug"], bool):
            errors.append("调试模式必须是布尔值")
        
        # 验证Nginx配置
        nginx = config.get("nginx", {})
        
        # 验证enabled是否为布尔值
        if "enabled" in nginx and not isinstance(nginx["enabled"], bool):
            errors.append("Nginx启用配置必须是布尔值")
        
        # 验证proxy是否为布尔值
        if "proxy" in nginx and not isinstance(nginx["proxy"], bool):
            errors.append("Nginx代理配置必须是布尔值")
        
        # 验证version是否为非空字符串
        if "version" in nginx:
            if not isinstance(nginx["version"], str) or not nginx["version"].strip():
                errors.append("Nginx版本不能为空")
        
        # 验证mirror_url是否为字符串（可选）
        if "mirror_url" in nginx and nginx["mirror_url"] is not None:
            if not isinstance(nginx["mirror_url"], str):
                errors.append("Nginx镜像URL必须是字符串")
        
        # 验证install_path是否为非空字符串（仅Windows需要）
        import platform
        if platform.system() == "Windows":
            if "install_path" in nginx:
                if not isinstance(nginx["install_path"], str) or not nginx["install_path"].strip():
                    errors.append("Nginx安装路径不能为空")
        
        # 验证worker_processes
        if "worker_processes" in nginx:
            worker_processes = nginx["worker_processes"]
            if worker_processes != "auto" and not isinstance(worker_processes, int):
                errors.append("Nginx worker_processes 必须是 'auto' 或整数")
        
        # 验证worker_connections
        if "worker_connections" in nginx:
            worker_connections = nginx["worker_connections"]
            try:
                worker_connections = int(worker_connections)
                if worker_connections <= 0:
                    errors.append("Nginx worker_connections 必须是正整数")
            except (ValueError, TypeError):
                errors.append("Nginx worker_connections 必须是正整数")
        
        # 验证keepalive_timeout
        if "keepalive_timeout" in nginx:
            keepalive_timeout = nginx["keepalive_timeout"]
            try:
                keepalive_timeout = int(keepalive_timeout)
                if keepalive_timeout < 0:
                    errors.append("Nginx keepalive_timeout 必须是非负整数")
            except (ValueError, TypeError):
                errors.append("Nginx keepalive_timeout 必须是非负整数")
        
        # 验证listen_port
        if "listen_port" in nginx:
            listen_port = nginx["listen_port"]
            try:
                listen_port = int(listen_port)
                if listen_port < 1 or listen_port > 65535:
                    errors.append("Nginx监听端口必须是1-65535之间的整数")
            except (ValueError, TypeError):
                errors.append("Nginx监听端口必须是1-65535之间的整数")
        
        # 验证server_name是否为非空字符串
        if "server_name" in nginx:
            if not isinstance(nginx["server_name"], str) or not nginx["server_name"].strip():
                errors.append("Nginx服务器名称不能为空")
        
        # 验证api_host是否为非空字符串
        if "api_host" in nginx:
            if not isinstance(nginx["api_host"], str) or not nginx["api_host"].strip():
                errors.append("Nginx API主机不能为空")
        
        # 验证api_port
        if "api_port" in nginx:
            api_port = nginx["api_port"]
            try:
                api_port = int(api_port)
                if api_port < 1 or api_port > 65535:
                    errors.append("Nginx API端口必须是1-65535之间的整数")
            except (ValueError, TypeError):
                errors.append("Nginx API端口必须是1-65535之间的整数")
        
        return len(errors) == 0, errors
    
    def get_nginx_config(self) -> Dict[str, Any]:
        """
        获取Nginx配置
        
        Returns:
            Dict[str, Any]: Nginx配置字典
        """
        config = self.load_config()
        return config.get("nginx", {})
    
    def update_nginx_config(self, nginx_config: Dict[str, Any]) -> bool:
        """
        更新Nginx配置
        
        Args:
            nginx_config: Nginx配置字典
            
        Returns:
            bool: 更新成功返回True，否则返回False
        """
        config = self.load_config()
        
        # 合并Nginx配置
        config["nginx"] = {**config.get("nginx", {}), **nginx_config}
        
        return self.save_config(config)
    
    def update_nginx_port(self, port: int) -> bool:
        """
        更新Nginx监听端口
        
        Args:
            port: 新端口号
            
        Returns:
            bool: 更新成功返回True，否则返回False
        """
        return self.set("nginx.listen_port", port)
    
    def update_nginx_server_name(self, server_name: str) -> bool:
        """
        更新Nginx服务器名称
        
        Args:
            server_name: 新服务器名称
            
        Returns:
            bool: 更新成功返回True，否则返回False
        """
        return self.set("nginx.server_name", server_name)
    
    def update_nginx_api_proxy(self, host: str, port: int) -> bool:
        """
        更新Nginx API代理配置
        
        Args:
            host: API主机地址
            port: API端口号
            
        Returns:
            bool: 更新成功返回True，否则返回False
        """
        self.set("nginx.api_host", host)
        self.set("nginx.api_port", port)
        return True
    
    def toggle_nginx(self, enabled: bool) -> bool:
        """
        启用或禁用Nginx
        
        Args:
            enabled: 是否启用
            
        Returns:
            bool: 更新成功返回True，否则返回False
        """
        return self.set("nginx.enabled", enabled)


# 创建全局配置管理器实例
_config_manager: Optional[ClientConfigManager] = None


def get_client_config_manager(config_path: str = "config.toml") -> ClientConfigManager:
    """
    获取全局配置管理器实例
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        ClientConfigManager: 配置管理器实例
    """
    global _config_manager
    if _config_manager is None:
        _config_manager = ClientConfigManager(config_path)
    return _config_manager
