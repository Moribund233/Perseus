"""
客户端初始化工具类

负责客户端启动时的初始化流程，包括调用服务端init模块生成配置文件
并提供初始化状态管理
"""
from typing import Optional
from PySide6.QtCore import QThread, Signal


class InitThread(QThread):
    """
    初始化线程类
    
    信号：
        progress_updated: 进度更新信号，参数为进度值(0-100)和状态文本
        initialization_completed: 初始化完成信号，参数为是否成功和错误信息
    """
    progress_updated = Signal(int, str)  # 进度值(0-100), 状态文本
    initialization_completed = Signal(bool, str)  # 是否成功, 错误信息
    
    def __init__(self, check_service: bool = True):
        """
        初始化线程
        
        Args:
            check_service: 是否检查服务状态
        """
        super().__init__()
        self._check_service = check_service
    
    def run(self):
        """
        线程运行函数
        """
        try:
            # 步骤1: 开始初始化
            self.progress_updated.emit(0, "正在准备初始化...")
            
            # 步骤2: 调用服务端init模块生成配置文件
            self.progress_updated.emit(30, "正在初始化配置文件...")
            
            from init import init_app
            init_app(check_service=self._check_service)
            
            # 步骤3: 初始化Nginx服务器
            self.progress_updated.emit(50, "正在初始化Nginx服务器...")
            
            # 导入Nginx工具
            from client.utils.nginx import get_nginx_config_generator, NginxDownloader
            from client.utils.config_manager import get_client_config_manager
            import platform
            
            # 获取配置
            config_manager = get_client_config_manager()
            nginx_config = config_manager.get_nginx_config()
            
            # 检查Nginx是否启用
            if nginx_config.get("enabled", True):
                # 下载并安装Nginx
                self.progress_updated.emit(60, "正在检查Nginx安装...")
                
                try:
                    # 创建Nginx下载器实例并同步执行
                    nginx_downloader = NginxDownloader(
                        nginx_version=nginx_config.get("version", "1.26.0"),
                        install_path=nginx_config.get("install_path", "nginx"),
                        mirror_url=nginx_config.get("mirror_url")
                    )
                    nginx_downloader.run()  # 同步执行，确保Nginx安装完成
                    
                    # 生成Nginx配置文件
                    self.progress_updated.emit(80, "正在生成Nginx配置文件...")
                    # 使用配置中的install_path和config_path
                    import os
                    install_path = nginx_config.get("install_path", "nginx")
                    # 确保install_path是绝对路径
                    if install_path:
                        install_path = os.path.abspath(install_path)
                    config_path = nginx_config.get("config_path")
                    nginx_generator = get_nginx_config_generator(config_path, install_path)
                    nginx_generator.generate_config(nginx_config)
                except Exception as e:
                    # 在Linux系统上，Nginx安装失败不应阻止应用程序启动
                    # 记录错误并继续
                    print(f"Nginx初始化失败: {e}")
                    self.progress_updated.emit(90, f"Nginx初始化失败: {e[:30]}...")
                    self.progress_updated.emit(100, "配置文件初始化完成")
                    # 继续执行，不中断初始化流程
            
            # 步骤4: 初始化仓库存储目录
            self.progress_updated.emit(85, "正在初始化仓库存储目录...")

            # 导入Git工具
            from client.utils.git_utils import ensure_repository_root
            repo_root = ensure_repository_root()
            print(f"仓库根目录已确保存在: {repo_root}")

            # 步骤5: 初始化数据库
            self.progress_updated.emit(90, "正在初始化数据库...")

            # 导入数据库初始化工具
            from client.utils.init_database import init_database
            init_database()

            # 步骤6: 初始化完成
            self.progress_updated.emit(100, "配置文件初始化完成")
            
            # 发送初始化完成信号
            self.initialization_completed.emit(True, "")
            
        except Exception as e:
            error_msg = f"配置文件初始化失败: {e}"
            # 修复错误：避免对ValidationError对象进行切片操作
            error_display = str(e)[:30] + "..." if len(str(e)) > 30 else str(e)
            self.progress_updated.emit(100, f"初始化失败: {error_display}")
            
            # 发送初始化失败信号
            self.initialization_completed.emit(False, error_msg)


class ClientInitializer:
    """
    客户端初始化器
    
    负责客户端的初始化流程，包括调用服务端init模块生成配置文件
    并管理初始化状态
    """
    
    def __init__(self):
        """
        初始化客户端初始化器
        """
        self._is_ready = False
        self._init_error = None
        self._init_thread = None
    
    @property
    def is_ready(self) -> bool:
        """
        获取初始化状态
        
        Returns:
            bool: 是否已完成初始化
        """
        return self._is_ready
    
    @property
    def init_error(self) -> Optional[str]:
        """
        获取初始化错误信息
        
        Returns:
            Optional[str]: 初始化错误信息，如无错误则返回None
        """
        return self._init_error
    
    def initialize(self, check_service: bool = True, use_thread: bool = True) -> InitThread:
        """
        执行初始化流程
        
        Args:
            check_service: 是否检查服务状态
            use_thread: 是否在新线程中执行初始化
        
        Returns:
            InitThread: 初始化线程实例
        """
        if use_thread:
            # 创建并启动初始化线程
            self._init_thread = InitThread(check_service=check_service)
            self._init_thread.start()
            return self._init_thread
        else:
            # 同步执行初始化
            init_thread = InitThread(check_service=check_service)
            init_thread.run()
            return init_thread


# 创建全局初始化器实例
client_initializer = ClientInitializer()


def init_client(check_service: bool = True, use_thread: bool = True) -> InitThread:
    """
    初始化客户端
    
    Args:
        check_service: 是否检查服务状态
        use_thread: 是否在新线程中执行初始化
    
    Returns:
        InitThread: 初始化线程实例
    """
    return client_initializer.initialize(check_service=check_service, use_thread=use_thread)


def get_initializer() -> ClientInitializer:
    """
    获取全局初始化器实例
    
    Returns:
        ClientInitializer: 客户端初始化器实例
    """
    return client_initializer
