"""
Nginx工具模块

负责Nginx的下载、安装和配置文件生成与管理
"""
import os
import requests
import zipfile
import shutil
import platform
import subprocess
from typing import Dict, Any, Optional, Tuple
from PySide6.QtCore import QThread, Signal


class NginxDownloader(QThread):
    """
    Nginx下载器线程类
    
    信号：
        progress_updated: 下载进度更新信号，参数为进度值(0-100)和状态文本
        download_completed: 下载完成信号，参数为是否成功和错误信息
    """
    progress_updated = Signal(int, str)  # 进度值(0-100), 状态文本
    download_completed = Signal(bool, str)  # 是否成功, 错误信息
    
    def __init__(self, nginx_version: str = "1.26.0", install_path: str = "nginx", mirror_url: str = None):
        """
        初始化Nginx下载器
        
        Args:
            nginx_version: Nginx版本号
            install_path: 安装路径（Windows为目录，Linux为可执行文件路径）
            mirror_url: 镜像URL，为空时使用华为云镜像
        """
        super().__init__()
        self._nginx_version = nginx_version
        self._install_path = install_path
        self._mirror_url = mirror_url
        
        # 确保install_path是绝对路径
        if self._install_path:
            self._install_path = os.path.abspath(self._install_path)
    
    def run(self):
        """
        线程运行函数，执行Nginx下载和安装
        """
        try:
            # 步骤1: 检查操作系统
            self.progress_updated.emit(0, "正在检测操作系统...")
            system = platform.system()
            
            # 步骤2: 检查Nginx是否已安装
            if self._is_nginx_installed(system):
                self.progress_updated.emit(100, "Nginx已安装，跳过安装")
                self.download_completed.emit(True, "Nginx已安装")
                return
            
            # 步骤3: 根据操作系统选择安装方式
            if system == "Windows":
                # Windows安装流程
                self._install_nginx_windows()
            else:
                # Linux/Other安装流程
                self._install_nginx_linux()
            
            # 步骤4: 完成
            self.progress_updated.emit(100, "Nginx安装完成")
            self.download_completed.emit(True, "")
            
        except Exception as e:
            error_msg = f"Nginx安装失败: {e}"
            self.progress_updated.emit(100, f"安装失败: {e[:30]}...")
            self.download_completed.emit(False, error_msg)
    
    def _is_nginx_installed(self, system: str) -> bool:
        """
        检查Nginx是否已安装
        
        Args:
            system: 操作系统名称
            
        Returns:
            bool: 是否已安装
        """
        if system == "Windows":
            # Windows: 检查安装目录是否存在nginx.exe
            nginx_exe = os.path.join(self._install_path, "nginx.exe")
            return os.path.isfile(nginx_exe)
        else:
            # Linux: 使用which命令检测nginx可执行文件
            return self._get_linux_nginx_path() is not None
    
    def _get_linux_nginx_path(self) -> Optional[str]:
        """
        获取Linux系统Nginx可执行文件的绝对路径
        
        Returns:
            Optional[str]: Nginx可执行文件路径，未找到返回None
        """
        try:
            # 使用which命令查找nginx
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
        
        return None
    
    def _install_nginx_windows(self):
        """
        Windows系统安装Nginx
        """
        # 步骤1: 下载Nginx
        self.progress_updated.emit(10, "正在下载Nginx...")
        download_url = self._get_download_url()
        zip_file = self._download_nginx(download_url)
        
        # 步骤2: 解压安装
        self.progress_updated.emit(60, "正在解压Nginx...")
        self._extract_nginx(zip_file)
        
        # 步骤3: 清理临时文件
        self.progress_updated.emit(90, "正在清理临时文件...")
        os.remove(zip_file)
    
    def _install_nginx_linux(self):
        """
        Linux系统安装Nginx
        
        使用包管理器安装Nginx，支持不同的Linux发行版
        """
        self.progress_updated.emit(10, "正在使用包管理器安装Nginx...")
        
        # 获取Linux发行版
        distro = self._get_linux_distro()
        
        # 根据发行版选择包管理器命令
        install_cmd = []
        if distro in ["Ubuntu", "Debian", "Linux Mint"]:
            install_cmd = ["apt-get", "update"]
        elif distro in ["CentOS", "Red Hat", "Fedora", "Rocky Linux"]:
            install_cmd = ["yum", "update"]
        elif distro in ["Arch Linux", "Manjaro"]:
            install_cmd = ["pacman", "-Sy"]
        else:
            # 默认使用apt-get（Debian/Ubuntu系）
            install_cmd = ["apt-get", "update"]
        
        # 执行更新命令
        self.progress_updated.emit(20, f"正在更新包列表...")
        subprocess.run(install_cmd, capture_output=True, check=True)
        
        # 执行安装命令
        self.progress_updated.emit(50, "正在安装Nginx...")
        if distro in ["Ubuntu", "Debian", "Linux Mint"]:
            subprocess.run(["apt-get", "install", "-y", "nginx"], capture_output=True, check=True)
        elif distro in ["CentOS", "Red Hat", "Fedora", "Rocky Linux"]:
            subprocess.run(["yum", "install", "-y", "nginx"], capture_output=True, check=True)
        elif distro in ["Arch Linux", "Manjaro"]:
            subprocess.run(["pacman", "-S", "--noconfirm", "nginx"], capture_output=True, check=True)
        else:
            # 默认使用apt-get（Debian/Ubuntu系）
            subprocess.run(["apt-get", "install", "-y", "nginx"], capture_output=True, check=True)
    
    def _get_linux_distro(self) -> str:
        """
        获取Linux发行版名称
        
        Returns:
            str: 发行版名称
        """
        try:
            with open("/etc/os-release", "r") as f:
                for line in f:
                    if line.startswith("NAME="):
                        return line.split("=")[1].strip().strip('"')
        except FileNotFoundError:
            # 如果无法读取/etc/os-release，尝试使用其他方法
            try:
                distro = subprocess.run(["lsb_release", "-is"], capture_output=True, text=True, check=True).stdout.strip()
                return distro
            except (subprocess.CalledProcessError, FileNotFoundError):
                pass
        
        # 默认返回Unknown
        return "Unknown"
    
    def _get_download_url(self) -> str:
        """
        获取Nginx下载链接
        
        Returns:
            str: Nginx下载链接
        """
        # 使用配置的镜像URL或默认华为云镜像
        base_url = self._mirror_url or "https://mirrors.huaweicloud.com/nginx/"
        # 确保URL以斜杠结尾
        if not base_url.endswith("/"):
            base_url += "/"
        # Windows版本下载链接
        return f"{base_url}nginx-{self._nginx_version}.zip"
    
    def _download_nginx(self, url: str) -> str:
        """
        下载Nginx压缩包
        
        Args:
            url: 下载链接
            
        Returns:
            str: 下载后的文件路径
        """
        zip_file = f"nginx-{self._nginx_version}.zip"
        
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            total_size = int(r.headers.get('content-length', 0))
            downloaded_size = 0
            
            with open(zip_file, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        
                        if total_size > 0:
                            progress = int((downloaded_size / total_size) * 50) + 10  # 10-60%
                            self.progress_updated.emit(progress, f"正在下载Nginx... {progress-10}%")
        
        return zip_file
    
    def _extract_nginx(self, zip_file: str):
        """
        解压Nginx压缩包
        
        Args:
            zip_file: 压缩包路径
        """
        # 创建临时解压目录
        temp_dir = f"nginx-{self._nginx_version}-temp"
        
        with zipfile.ZipFile(zip_file, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        
        # 获取解压后的目录名
        extracted_dir = os.path.join(temp_dir, f"nginx-{self._nginx_version}")
        
        # 移动到安装目录
        shutil.move(extracted_dir, self._install_path)
        
        # 删除临时目录
        shutil.rmtree(temp_dir)
    
    def is_nginx_installed(self) -> bool:
        """
        检查Nginx是否已安装（公开方法）
        
        Returns:
            bool: 是否已安装
        """
        system = platform.system()
        return self._is_nginx_installed(system)
    
    def get_nginx_path(self) -> str:
        """
        获取Nginx可执行文件路径
        
        Returns:
            str: Nginx可执行文件路径
        """
        system = platform.system()
        if system == "Windows":
            return os.path.join(self._install_path, "nginx.exe")
        else:
            # Linux: 返回检测到的绝对路径
            nginx_path = self._get_linux_nginx_path()
            if nginx_path:
                return nginx_path
            # 如果未检测到，返回默认路径（但可能不存在）
            return "/usr/sbin/nginx"
    
    def get_install_path(self) -> str:
        """
        获取安装路径（仅Windows使用，Linux返回空字符串）
        
        Returns:
            str: Windows下返回安装目录，Linux下返回空字符串
        """
        if platform.system() == "Windows":
            return self._install_path
        return ""
    
    def is_linux_nginx_installed(self) -> bool:
        """
        检测Linux系统是否已安装Nginx
        
        Returns:
            bool: 已安装返回True，否则返回False
        """
        return self._get_linux_nginx_path() is not None


class NginxConfigGenerator:
    """
    Nginx配置生成器类
    
    负责生成和管理Nginx配置文件
    """
    
    def __init__(self, config_path: str = None, install_path: str = None):
        """
        初始化Nginx配置生成器
        
        Args:
            config_path: Nginx配置文件路径（优先使用，推荐）
            install_path: Nginx安装路径（仅Windows下用于生成默认配置路径）
        """
        if config_path:
            # 如果提供了config_path，优先使用
            self._config_path = os.path.abspath(config_path)
        elif install_path and platform.system() == "Windows":
            # Windows: 根据install_path生成配置路径
            self._config_path = os.path.join(os.path.abspath(install_path), "conf", "nginx.conf")
        elif platform.system() == "Windows":
            # Windows默认路径
            self._config_path = os.path.abspath("nginx/conf/nginx.conf")
        else:
            # Linux系统使用用户级配置目录，避免需要root权限
            user_config_dir = os.path.expanduser("~/.config/langit/nginx")
            self._config_path = os.path.join(user_config_dir, "nginx.conf")
    
    def generate_config(self, config: Dict[str, Any]) -> bool:
        """
        生成Nginx配置文件
        
        Args:
            config: Nginx配置字典
            
        Returns:
            bool: 生成成功返回True，否则返回False
        """
        try:
            # 构建配置内容
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
            
            # 创建默认的index.html文件（如果不存在）
            index_html_path = os.path.join(html_dir, "index.html")
            if not os.path.exists(index_html_path):
                with open(index_html_path, 'w', encoding='utf-8') as f:
                    f.write("<html><body><h1>LanGit</h1><p>Welcome to LanGit!</p></body></html>")
            
            # 创建50x.html错误页面（如果不存在）
            error_html_path = os.path.join(html_dir, "50x.html")
            if not os.path.exists(error_html_path):
                with open(error_html_path, 'w', encoding='utf-8') as f:
                    f.write("<html><body><h1>Error</h1><p>An error occurred.</p></body></html>")
            
            # 写入配置文件
            with open(self._config_path, 'w', encoding='utf-8') as f:
                f.write(nginx_config)
            
            return True
        except Exception as e:
            print(f"生成Nginx配置文件失败: {e}")
            return False
    
    def _get_mime_types_path(self) -> str:
        """
        获取mime.types文件的绝对路径
        
        Returns:
            str: mime.types文件的绝对路径
        """
        # 常见mime.types文件位置
        common_paths = [
            "/etc/nginx/mime.types",
            "/usr/local/nginx/conf/mime.types",
            "/opt/nginx/conf/mime.types",
        ]
        
        # 优先查找系统路径
        for path in common_paths:
            if os.path.isfile(path):
                return path
        
        # 如果找不到，返回相对路径（兼容Windows）
        return "mime.types"
    
    def _build_config_content(self, config: Dict[str, Any]) -> str:
        """
        构建Nginx配置内容
        
        Args:
            config: Nginx配置字典
            
        Returns:
            str: Nginx配置内容
        """
        # 获取mime.types的绝对路径
        mime_types_path = self._get_mime_types_path()
        
        # 生成配置文件目录路径（用于存放pid、log等文件）
        config_dir = os.path.dirname(self._config_path)
        pid_path = os.path.join(config_dir, "nginx.pid")
        
        # 生成日志目录路径
        log_dir = os.path.join(config_dir, "logs")
        access_log_path = os.path.join(log_dir, "access.log")
        error_log_path = os.path.join(log_dir, "error.log")
        
        # 生成静态文件目录路径
        html_dir = os.path.join(config_dir, "html")
        
        # 基础配置模板
        base_config = f"""
worker_processes  {config.get('worker_processes', 'auto')};
pid {pid_path};

events {{
    worker_connections  {config.get('worker_connections', 1024)};
}}

http {{
    include       {mime_types_path};
    default_type  application/octet-stream;

    sendfile        on;
    keepalive_timeout  {config.get('keepalive_timeout', 65)};
    
    # 日志配置（用户目录下，避免权限问题）
    access_log  {access_log_path};
    error_log   {error_log_path};

    server {{
        listen       {config.get('listen_port', 80)};
        server_name  {config.get('server_name', 'localhost')};

        location / {{
            root   {html_dir};
            index  index.html index.htm;
        }}

        # LanGit API代理配置
        location /api/ {{
            proxy_pass http://{config.get('api_host', 'localhost')}:{config.get('api_port', 8000)}/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
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
        获取默认Nginx配置
        
        Returns:
            Dict[str, Any]: 默认配置字典
        """
        return {
            'worker_processes': 'auto',
            'worker_connections': 1024,
            'keepalive_timeout': 65,
            'listen_port': 80,
            'server_name': 'localhost',
            'api_host': 'localhost',
            'api_port': 8000
        }
    
    def update_config(self, key: str, value: Any) -> bool:
        """
        更新Nginx配置项
        
        Args:
            key: 配置键名
            value: 配置值
            
        Returns:
            bool: 更新成功返回True，否则返回False
        """
        # 读取当前配置
        if not os.path.exists(self._config_path):
            # 如果配置文件不存在，使用默认配置
            config = self.get_default_config()
        else:
            # 解析现有配置文件（简化实现，实际可能需要更复杂的解析）
            config = self.get_default_config()
        
        # 更新配置
        config[key] = value
        
        # 重新生成配置文件
        return self.generate_config(config)
    
    def validate_config(self, config: Dict[str, Any]) -> tuple[bool, list[str]]:
        """
        验证Nginx配置
        
        Args:
            config: Nginx配置字典
            
        Returns:
            tuple: (是否有效, 错误信息列表)
        """
        errors = []
        
        # 验证worker_processes
        worker_processes = config.get('worker_processes')
        if worker_processes != 'auto' and not isinstance(worker_processes, int):
            errors.append("worker_processes 必须是 'auto' 或整数")
        
        # 验证worker_connections
        worker_connections = config.get('worker_connections')
        if not isinstance(worker_connections, int) or worker_connections <= 0:
            errors.append("worker_connections 必须是正整数")
        
        # 验证keepalive_timeout
        keepalive_timeout = config.get('keepalive_timeout')
        if not isinstance(keepalive_timeout, int) or keepalive_timeout < 0:
            errors.append("keepalive_timeout 必须是非负整数")
        
        # 验证listen_port
        listen_port = config.get('listen_port')
        if not isinstance(listen_port, int) or listen_port < 1 or listen_port > 65535:
            errors.append("listen_port 必须是1-65535之间的整数")
        
        # 验证server_name
        server_name = config.get('server_name')
        if not isinstance(server_name, str) or not server_name.strip():
            errors.append("server_name 不能为空字符串")
        
        # 验证api_host
        api_host = config.get('api_host')
        if not isinstance(api_host, str) or not api_host.strip():
            errors.append("api_host 不能为空字符串")
        
        # 验证api_port
        api_port = config.get('api_port')
        if not isinstance(api_port, int) or api_port < 1 or api_port > 65535:
            errors.append("api_port 必须是1-65535之间的整数")
        
        return len(errors) == 0, errors


# 全局Nginx配置生成器实例
_nginx_config_generator: Optional[NginxConfigGenerator] = None


def get_nginx_config_generator(config_path: str = None, install_path: str = None) -> NginxConfigGenerator:
    """
    获取全局Nginx配置生成器实例
    
    Args:
        config_path: Nginx配置文件路径（优先使用）
        install_path: Nginx安装路径（Windows下用于生成默认配置路径）
        
    Returns:
        NginxConfigGenerator: Nginx配置生成器实例
    """
    global _nginx_config_generator
    if _nginx_config_generator is None:
        _nginx_config_generator = NginxConfigGenerator(config_path, install_path)
    return _nginx_config_generator


def generate_nginx_config(config: Optional[Dict[str, Any]] = None) -> bool:
    """
    生成Nginx配置文件
    
    Args:
        config: Nginx配置字典，不提供则使用默认配置
        
    Returns:
        bool: 生成成功返回True，否则返回False
    """
    generator = get_nginx_config_generator()
    if config is None:
        config = generator.get_default_config()
    return generator.generate_config(config)


def download_nginx(nginx_version: str = "1.26.0", install_path: str = "nginx") -> NginxDownloader:
    """
    下载并安装Nginx
    
    Args:
        nginx_version: Nginx版本号
        install_path: 安装路径
        
    Returns:
        NginxDownloader: Nginx下载器实例
    """
    downloader = NginxDownloader(nginx_version, install_path)
    downloader.start()
    return downloader
