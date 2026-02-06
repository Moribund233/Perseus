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
            install_path: 安装路径
            mirror_url: 镜像URL，为空时使用华为云镜像
        """
        super().__init__()
        self._nginx_version = nginx_version
        self._install_path = install_path
        self._mirror_url = mirror_url
    
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
            # Windows: 检查安装目录是否存在
            return os.path.exists(self._install_path)
        else:
            # Linux: 检查是否可以执行nginx命令
            try:
                subprocess.run(["nginx", "-v"], capture_output=True, check=True)
                return True
            except (subprocess.CalledProcessError, FileNotFoundError):
                return False
    
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
            # Linux系统中Nginx通常安装在/usr/sbin/nginx
            return "/usr/sbin/nginx"


class NginxConfigGenerator:
    """
    Nginx配置生成器类
    
    负责生成和管理Nginx配置文件
    """
    
    def __init__(self, config_path: str = None):
        """
        初始化Nginx配置生成器
        
        Args:
            config_path: Nginx配置文件路径
        """
        # 根据操作系统选择默认配置文件路径
        if config_path is None:
            if platform.system() == "Windows":
                self._config_path = "nginx/conf/nginx.conf"
            else:
                # Linux系统默认配置文件路径
                self._config_path = "/etc/nginx/nginx.conf"
        else:
            self._config_path = config_path
    
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
            os.makedirs(os.path.dirname(self._config_path), exist_ok=True)
            
            # 写入配置文件
            with open(self._config_path, 'w', encoding='utf-8') as f:
                f.write(nginx_config)
            
            return True
        except Exception as e:
            print(f"生成Nginx配置文件失败: {e}")
            return False
    
    def _build_config_content(self, config: Dict[str, Any]) -> str:
        """
        构建Nginx配置内容
        
        Args:
            config: Nginx配置字典
            
        Returns:
            str: Nginx配置内容
        """
        # 基础配置模板
        base_config = f"""
worker_processes  {config.get('worker_processes', 'auto')};

events {{
    worker_connections  {config.get('worker_connections', 1024)};
}}

http {{
    include       mime.types;
    default_type  application/octet-stream;

    sendfile        on;
    keepalive_timeout  {config.get('keepalive_timeout', 65)};

    server {{
        listen       {config.get('listen_port', 80)};
        server_name  {config.get('server_name', 'localhost')};

        location / {{
            root   html;
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
            root   html;
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


def get_nginx_config_generator(config_path: str = "nginx/conf/nginx.conf") -> NginxConfigGenerator:
    """
    获取全局Nginx配置生成器实例
    
    Args:
        config_path: Nginx配置文件路径
        
    Returns:
        NginxConfigGenerator: Nginx配置生成器实例
    """
    global _nginx_config_generator
    if _nginx_config_generator is None:
        _nginx_config_generator = NginxConfigGenerator(config_path)
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
