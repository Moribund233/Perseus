"""
Nginx 配置生成模块

负责生成 Nginx 反向代理配置文件
"""
import os
import platform
from typing import Any, Dict, List, Optional


class NginxConfigGenerator:
    """
    Nginx 配置生成器

    根据服务端配置生成 Nginx 反向代理配置
    """

    def __init__(self, config_path: str = None, install_path: str = None):
        """
        初始化 Nginx 配置生成器

        Args:
            config_path: Nginx 配置文件路径（优先使用）
            install_path: Nginx 安装路径（Windows 下用于生成默认配置路径）
        """
        self._install_path = install_path

        if config_path:
            self._config_path = os.path.abspath(config_path)
        elif install_path and platform.system() == "Windows":
            self._config_path = os.path.join(
                os.path.abspath(install_path), "conf", "nginx.conf"
            )
        elif platform.system() == "Windows":
            self._config_path = os.path.abspath("nginx/conf/nginx.conf")
        else:
            # Linux 系统使用用户级配置目录
            user_config_dir = os.path.expanduser("~/.config/langit/nginx")
            self._config_path = os.path.join(user_config_dir, "nginx.conf")

    def generate_config(self, config: Dict[str, Any]) -> bool:
        """
        生成 Nginx 配置文件

        Args:
            config: Nginx 配置字典

        Returns:
            bool: 生成成功返回 True，否则返回 False
        """
        try:
            nginx_config = self._build_config_content(config)

            # 确保配置目录存在
            config_dir = os.path.dirname(self._config_path)
            os.makedirs(config_dir, exist_ok=True)

            # 确保日志目录存在
            log_dir = os.path.join(config_dir, "logs")
            os.makedirs(log_dir, exist_ok=True)

            # 确保静态文件目录存在
            html_dir = os.path.join(config_dir, "html")
            os.makedirs(html_dir, exist_ok=True)

            # 创建默认的 index.html 文件
            index_html_path = os.path.join(html_dir, "index.html")
            if not os.path.exists(index_html_path):
                with open(index_html_path, "w", encoding="utf-8") as f:
                    f.write(
                        "<html><body><h1>LanGit</h1><p>Welcome to LanGit!</p></body></html>"
                    )

            # 创建 50x.html 错误页面
            error_html_path = os.path.join(html_dir, "50x.html")
            if not os.path.exists(error_html_path):
                with open(error_html_path, "w", encoding="utf-8") as f:
                    f.write(
                        "<html><body><h1>Error</h1><p>An error occurred.</p></body></html>"
                    )

            # 写入配置文件
            with open(self._config_path, "w", encoding="utf-8") as f:
                f.write(nginx_config)

            return True
        except Exception as e:
            print(f"生成 Nginx 配置文件失败: {e}")
            return False

    def _get_mime_types_path(self) -> str:
        """
        获取 mime.types 文件的绝对路径

        Returns:
            str: mime.types 文件的绝对路径
        """
        common_paths = [
            "/etc/nginx/mime.types",
            "/usr/local/nginx/conf/mime.types",
            "/opt/nginx/conf/mime.types",
        ]

        for path in common_paths:
            if os.path.isfile(path):
                return path

        return "mime.types"

    def _build_config_content(self, config: Dict[str, Any]) -> str:
        """
        构建 Nginx 配置内容

        Args:
            config: Nginx 配置字典

        Returns:
            str: Nginx 配置内容
        """
        mime_types_path = self._get_mime_types_path()

        if self._install_path and platform.system() == "Windows":
            pid_path = "logs/nginx.pid"
            access_log_path = "logs/access.log"
            error_log_path = "logs/error.log"
            html_dir = "html"
        else:
            config_dir = os.path.dirname(self._config_path)
            pid_path = os.path.join(config_dir, "nginx.pid")
            log_dir = os.path.join(config_dir, "logs")
            access_log_path = os.path.join(log_dir, "access.log")
            error_log_path = os.path.join(log_dir, "error.log")
            html_dir = os.path.join(config_dir, "html")

            pid_path = pid_path.replace("\\", "/")
            access_log_path = access_log_path.replace("\\", "/")
            error_log_path = error_log_path.replace("\\", "/")
            html_dir = html_dir.replace("\\", "/")

        mime_types_path = mime_types_path.replace("\\", "/")

        base_config = f"""
worker_processes  {config.get('worker_processes', 'auto')};
pid {pid_path};

events {{
    worker_connections  {config.get('worker_connections', 1024)};
}}

http {{
    include       {mime_types_path};
    default_type  application/octet-stream;

    # 安全加固：隐藏Nginx版本号
    server_tokens off;

    sendfile        on;
    keepalive_timeout  {config.get('keepalive_timeout', 65)};

    # 日志配置
    access_log  {access_log_path};
    error_log   {error_log_path};

    # 速率限制配置
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=30r/m;
    limit_req_zone $binary_remote_addr zone=login_limit:10m rate=5r/m;
    limit_conn_zone $binary_remote_addr zone=conn_limit:10m;

    server {{
        listen       {config.get('listen_port', 80)};
        server_name  {config.get('server_name', 'localhost')};

        # 安全响应头
        add_header X-Content-Type-Options "nosniff" always;
        add_header X-Frame-Options "DENY" always;
        add_header X-XSS-Protection "1; mode=block" always;
        add_header Referrer-Policy "strict-origin-when-cross-origin" always;
        add_header Permissions-Policy "accelerometer=(), camera=(), geolocation=(), gyroscope=(), magnetometer=(), microphone=(), payment=(), usb=()" always;

        location / {{
            root   {html_dir};
            index  index.html index.htm;
        }}

        # LanGit API代理配置
        location /api/ {{
            # 速率限制
            limit_req zone=api_limit burst=10 nodelay;
            limit_conn conn_limit 20;

            proxy_pass http://{config.get('api_host', 'localhost')}:{config.get('api_port', 8000)};
            proxy_set_header Host $http_host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_set_header X-Forwarded-Host $host;
            proxy_set_header X-Forwarded-Port $server_port;

            # 修改后端返回的重定向URL
            proxy_redirect ~^http://([^/]+)(/.*)$ http://$http_host$2;

            # 隐藏上游服务器的敏感响应头
            proxy_hide_header Server;
            proxy_hide_header X-Powered-By;

            # 安全响应头
            add_header X-Content-Type-Options "nosniff" always;
            add_header X-Frame-Options "DENY" always;
            add_header X-XSS-Protection "1; mode=block" always;
            add_header Referrer-Policy "strict-origin-when-cross-origin" always;
            add_header Permissions-Policy "accelerometer=(), camera=(), geolocation=(), gyroscope=(), magnetometer=(), microphone=(), payment=(), usb=()" always;
            add_header Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self'; connect-src 'self'; media-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'self'; form-action 'self';" always;

            # CORS配置
            add_header Access-Control-Allow-Origin * always;
            add_header Access-Control-Allow-Methods 'GET, POST, PUT, DELETE, OPTIONS' always;
            add_header Access-Control-Allow-Headers 'Content-Type, Authorization' always;
            add_header Access-Control-Allow-Credentials 'true' always;

            # 处理OPTIONS请求
            if ($request_method = 'OPTIONS') {{
                return 204;
            }}
        }}

        # 登录接口 - 严格限流
        location /api/users/login {{
            limit_req zone=login_limit burst=3 nodelay;
            limit_conn conn_limit 5;

            proxy_pass http://{config.get('api_host', 'localhost')}:{config.get('api_port', 8000)}/api/users/login;
            proxy_set_header Host $http_host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_set_header X-Forwarded-Host $host;
            proxy_set_header X-Forwarded-Port $server_port;
            proxy_redirect ~^http://([^/]+)(/.*)$ http://$http_host$2;
            proxy_hide_header Server;
            proxy_hide_header X-Powered-By;

            # 安全响应头
            add_header X-Content-Type-Options "nosniff" always;
            add_header X-Frame-Options "DENY" always;
            add_header X-XSS-Protection "1; mode=block" always;
            add_header Referrer-Policy "strict-origin-when-cross-origin" always;
            add_header Permissions-Policy "accelerometer=(), camera=(), geolocation=(), gyroscope=(), magnetometer=(), microphone=(), payment=(), usb=()" always;
            add_header Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self'; connect-src 'self'; media-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'self'; form-action 'self';" always;

            add_header Access-Control-Allow-Origin * always;
            add_header Access-Control-Allow-Methods 'POST, OPTIONS' always;
            add_header Access-Control-Allow-Headers 'Content-Type, Authorization' always;
            add_header Access-Control-Allow-Credentials 'true' always;

            if ($request_method = 'OPTIONS') {{
                return 204;
            }}
        }}

        # 健康检查路径配置
        location /health {{
            proxy_pass http://{config.get('api_host', 'localhost')}:{config.get('api_port', 8000)}/health;
            proxy_set_header Host $http_host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_set_header X-Forwarded-Host $host;
            proxy_set_header X-Forwarded-Port $server_port;
            proxy_redirect ~^http://([^/]+)(/.*)$ http://$http_host$2;
            proxy_hide_header Server;
            proxy_hide_header X-Powered-By;

            add_header X-Content-Type-Options "nosniff" always;
            add_header X-Frame-Options "DENY" always;
            add_header X-XSS-Protection "1; mode=block" always;
            add_header Referrer-Policy "strict-origin-when-cross-origin" always;
            add_header Permissions-Policy "accelerometer=(), camera=(), geolocation=(), gyroscope=(), magnetometer=(), microphone=(), payment=(), usb=()" always;
            add_header Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self'; connect-src 'self'; media-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'self'; form-action 'self';" always;

            add_header Access-Control-Allow-Origin * always;
            add_header Access-Control-Allow-Methods 'GET, OPTIONS' always;
            add_header Access-Control-Allow-Headers 'Content-Type, Authorization' always;
            add_header Access-Control-Allow-Credentials 'true' always;

            if ($request_method = 'OPTIONS') {{
                return 204;
            }}
        }}

        # WebSocket代理配置
        location /ws/ {{
            proxy_pass http://{config.get('api_host', 'localhost')}:{config.get('api_port', 8000)}/ws/;

            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";

            proxy_set_header Host $http_host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_set_header X-Forwarded-Host $host;
            proxy_set_header X-Forwarded-Port $server_port;

            proxy_hide_header Server;
            proxy_hide_header X-Powered-By;

            proxy_read_timeout 86400;
            proxy_send_timeout 86400;

            add_header Access-Control-Allow-Origin * always;
            add_header Access-Control-Allow-Credentials 'true' always;
        }}

        error_page   500 502 503 504  /50x.html;
        location = /50x.html {{
            root   {html_dir};
        }}
    }}
}}
"""
        return base_config

    def get_default_config(self) -> Dict[str, Any]:
        """
        获取默认 Nginx 配置

        Returns:
            Dict[str, Any]: 默认配置字典
        """
        return {
            "worker_processes": "auto",
            "worker_connections": 1024,
            "keepalive_timeout": 65,
            "listen_port": 80,
            "server_name": "localhost",
            "api_host": "localhost",
            "api_port": 8000,
        }

    def get_config_path(self) -> str:
        """
        获取配置文件路径

        Returns:
            str: 配置文件路径
        """
        return self._config_path

    def validate_config(self, config: Dict[str, Any]) -> tuple[bool, List[str]]:
        """
        验证 Nginx 配置

        Args:
            config: Nginx 配置字典

        Returns:
            tuple[bool, List[str]]: (是否有效, 错误信息列表)
        """
        errors: List[str] = []

        worker_processes = config.get("worker_processes")
        if worker_processes != "auto" and not isinstance(worker_processes, int):
            errors.append("worker_processes 必须是 'auto' 或整数")

        worker_connections = config.get("worker_connections")
        if not isinstance(worker_connections, int) or worker_connections <= 0:
            errors.append("worker_connections 必须是正整数")

        keepalive_timeout = config.get("keepalive_timeout")
        if not isinstance(keepalive_timeout, int) or keepalive_timeout < 0:
            errors.append("keepalive_timeout 必须是非负整数")

        listen_port = config.get("listen_port")
        if not isinstance(listen_port, int) or listen_port < 1 or listen_port > 65535:
            errors.append("listen_port 必须是1-65535之间的整数")

        server_name = config.get("server_name")
        if not isinstance(server_name, str) or not server_name.strip():
            errors.append("server_name 不能为空字符串")

        api_host = config.get("api_host")
        if not isinstance(api_host, str) or not api_host.strip():
            errors.append("api_host 不能为空字符串")

        api_port = config.get("api_port")
        if not isinstance(api_port, int) or api_port < 1 or api_port > 65535:
            errors.append("api_port 必须是1-65535之间的整数")

        return len(errors) == 0, errors


# 全局 Nginx 配置生成器实例
_nginx_config_generator: Optional[NginxConfigGenerator] = None


def get_nginx_config_generator(
    config_path: str = None, install_path: str = None
) -> NginxConfigGenerator:
    """
    获取全局 Nginx 配置生成器实例

    Args:
        config_path: Nginx 配置文件路径
        install_path: Nginx 安装路径

    Returns:
        NginxConfigGenerator: Nginx 配置生成器实例
    """
    global _nginx_config_generator
    if _nginx_config_generator is None:
        _nginx_config_generator = NginxConfigGenerator(config_path, install_path)
    return _nginx_config_generator


def generate_nginx_config(config: Optional[Dict[str, Any]] = None) -> bool:
    """
    生成 Nginx 配置文件

    Args:
        config: Nginx 配置字典，不提供则使用默认配置

    Returns:
        bool: 生成成功返回 True，否则返回 False
    """
    generator = get_nginx_config_generator()
    if config is None:
        config = generator.get_default_config()
    return generator.generate_config(config)
