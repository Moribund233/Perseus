"""
设置卡片组件

提供服务配置的查看和修改功能
"""
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QComboBox,
    QPushButton,
    QGridLayout
)
from PySide6.QtCore import Qt, Signal
from client.desktop.ui.constants import QSS_STYLES


class SettingsCard(QWidget):
    """
    设置卡片组件类
    
    信号：
        config_changed: 配置变更信号，携带键值对
        reset_clicked: 重置配置按钮点击信号
    """
    # 定义信号
    config_changed = Signal(str, str)
    reset_clicked = Signal()
    
    def __init__(self, parent=None):
        """
        初始化设置卡片
        
        Args:
            parent: 父窗口
        """
        super().__init__(parent)
        self.setup_ui()
        self.setObjectName("card")
        self.setStyleSheet(
            QSS_STYLES["card"] + 
            QSS_STYLES["button"] + 
            QSS_STYLES["line_edit"] + 
            QSS_STYLES["combo_box"] + 
            QSS_STYLES["card_title"]
        )
    
    def setup_ui(self):
        """
        设置UI组件
        """
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # 标题
        title_label = QLabel("服务配置")
        title_label.setObjectName("card_title")
        main_layout.addWidget(title_label)
        
        # 配置项布局
        config_layout = QGridLayout()
        config_layout.setSpacing(8)
        config_layout.setContentsMargins(0, 0, 0, 0)
        
        # 主机地址
        config_layout.addWidget(QLabel("主机地址:"), 0, 0)
        self.host_input = QLineEdit()
        self.host_input.setPlaceholderText("例如: 0.0.0.0")
        self.host_input.textChanged.connect(lambda text: self.config_changed.emit("server.host", text))
        config_layout.addWidget(self.host_input, 0, 1)
        
        # 端口
        config_layout.addWidget(QLabel("端口:"), 1, 0)
        self.port_input = QLineEdit()
        self.port_input.setPlaceholderText("例如: 8000")
        self.port_input.textChanged.connect(lambda text: self.config_changed.emit("server.port", text))
        config_layout.addWidget(self.port_input, 1, 1)
        
        # 日志级别
        config_layout.addWidget(QLabel("日志级别:"), 2, 0)
        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["debug", "info", "warning", "error", "critical"])
        self.log_level_combo.currentTextChanged.connect(lambda text: self.config_changed.emit("server.log_level", text))
        config_layout.addWidget(self.log_level_combo, 2, 1)
        
        # 工作进程数
        config_layout.addWidget(QLabel("工作进程:"), 3, 0)
        self.workers_input = QLineEdit()
        self.workers_input.setPlaceholderText("例如: 1")
        self.workers_input.textChanged.connect(lambda text: self.config_changed.emit("server.workers", text))
        config_layout.addWidget(self.workers_input, 3, 1)
        
        # Nginx配置分割线
        from PySide6.QtWidgets import QFrame, QCheckBox
        nginx_separator = QFrame()
        nginx_separator.setFrameShape(QFrame.HLine)
        nginx_separator.setFrameShadow(QFrame.Sunken)
        config_layout.addWidget(nginx_separator, 4, 0, 1, 2)
        
        # Nginx配置标题
        nginx_title = QLabel("Nginx配置")
        nginx_title.setObjectName("card_title")
        config_layout.addWidget(nginx_title, 5, 0, 1, 2)
        
        # Nginx代理开关
        config_layout.addWidget(QLabel("启用代理:"), 6, 0)
        self.nginx_proxy_check = QCheckBox()
        self.nginx_proxy_check.clicked.connect(lambda checked: self.config_changed.emit("nginx.proxy", str(checked)))
        config_layout.addWidget(self.nginx_proxy_check, 6, 1)
        
        # Nginx监听端口
        config_layout.addWidget(QLabel("Nginx端口:"), 7, 0)
        self.nginx_port_input = QLineEdit()
        self.nginx_port_input.setPlaceholderText("例如: 8080")
        self.nginx_port_input.textChanged.connect(lambda text: self.config_changed.emit("nginx.listen_port", text))
        config_layout.addWidget(self.nginx_port_input, 7, 1)
        
        # Nginx服务器名称
        config_layout.addWidget(QLabel("服务器名称:"), 8, 0)
        self.nginx_server_name_input = QLineEdit()
        self.nginx_server_name_input.setPlaceholderText("例如: localhost")
        self.nginx_server_name_input.textChanged.connect(lambda text: self.config_changed.emit("nginx.server_name", text))
        config_layout.addWidget(self.nginx_server_name_input, 8, 1)
        
        # 添加Nginx高级配置折叠面板
        from PySide6.QtWidgets import QPushButton
        
        # 创建折叠面板容器
        advanced_container = QWidget()
        advanced_layout = QVBoxLayout(advanced_container)
        advanced_layout.setSpacing(8)
        advanced_layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建折叠按钮
        toggle_button = QPushButton("▼ 高级配置")
        toggle_button.setStyleSheet("text-align: left;")
        toggle_button.setCheckable(True)
        toggle_button.setChecked(False)
        advanced_layout.addWidget(toggle_button)
        
        # 创建高级配置内容区域
        advanced_content = QWidget()
        advanced_content_layout = QGridLayout(advanced_content)
        advanced_content_layout.setSpacing(8)
        advanced_content_layout.setContentsMargins(0, 0, 0, 0)
        advanced_content.setVisible(False)  # 默认隐藏
        
        # Nginx版本
        advanced_content_layout.addWidget(QLabel("Nginx版本:"), 0, 0)
        self.nginx_version_input = QLineEdit()
        self.nginx_version_input.setPlaceholderText("例如: 1.26.0")
        self.nginx_version_input.textChanged.connect(lambda text: self.config_changed.emit("nginx.version", text))
        advanced_content_layout.addWidget(self.nginx_version_input, 0, 1)
        
        # 镜像URL
        advanced_content_layout.addWidget(QLabel("镜像URL:"), 1, 0)
        self.nginx_mirror_url_input = QLineEdit()
        self.nginx_mirror_url_input.setPlaceholderText("例如: https://mirrors.huaweicloud.com/nginx/")
        self.nginx_mirror_url_input.textChanged.connect(lambda text: self.config_changed.emit("nginx.mirror_url", text))
        advanced_content_layout.addWidget(self.nginx_mirror_url_input, 1, 1)
        
        # 安装路径
        advanced_content_layout.addWidget(QLabel("安装路径:"), 2, 0)
        self.nginx_install_path_input = QLineEdit()
        self.nginx_install_path_input.setPlaceholderText("例如: nginx")
        self.nginx_install_path_input.textChanged.connect(lambda text: self.config_changed.emit("nginx.install_path", text))
        advanced_content_layout.addWidget(self.nginx_install_path_input, 2, 1)
        
        # Worker进程数
        advanced_content_layout.addWidget(QLabel("Worker进程:"), 3, 0)
        self.nginx_worker_processes_input = QLineEdit()
        self.nginx_worker_processes_input.setPlaceholderText("例如: auto")
        self.nginx_worker_processes_input.textChanged.connect(lambda text: self.config_changed.emit("nginx.worker_processes", text))
        advanced_content_layout.addWidget(self.nginx_worker_processes_input, 3, 1)
        
        # Worker连接数
        advanced_content_layout.addWidget(QLabel("Worker连接:"), 4, 0)
        self.nginx_worker_connections_input = QLineEdit()
        self.nginx_worker_connections_input.setPlaceholderText("例如: 1024")
        self.nginx_worker_connections_input.textChanged.connect(lambda text: self.config_changed.emit("nginx.worker_connections", text))
        advanced_content_layout.addWidget(self.nginx_worker_connections_input, 4, 1)
        
        # Keepalive超时
        advanced_content_layout.addWidget(QLabel("Keepalive超时:"), 5, 0)
        self.nginx_keepalive_timeout_input = QLineEdit()
        self.nginx_keepalive_timeout_input.setPlaceholderText("例如: 65")
        self.nginx_keepalive_timeout_input.textChanged.connect(lambda text: self.config_changed.emit("nginx.keepalive_timeout", text))
        advanced_content_layout.addWidget(self.nginx_keepalive_timeout_input, 5, 1)
        
        # 将内容区域添加到容器布局
        advanced_layout.addWidget(advanced_content)
        
        # 连接折叠按钮信号
        def toggle_advanced():
            is_visible = advanced_content.isVisible()
            advanced_content.setVisible(not is_visible)
            toggle_button.setText("▼ 高级配置" if is_visible else "▲ 高级配置")
        
        toggle_button.clicked.connect(toggle_advanced)
        
        # 将折叠面板添加到配置布局
        config_layout.addWidget(advanced_container, 9, 0, 1, 2)
        
        main_layout.addLayout(config_layout)
        
        # 重置按钮
        self.reset_button = QPushButton("重置默认配置")
        self.reset_button.setObjectName("secondary_button")
        self.reset_button.setMinimumHeight(25)
        self.reset_button.setCursor(Qt.PointingHandCursor)
        self.reset_button.clicked.connect(self.reset_clicked)
        main_layout.addWidget(self.reset_button)
    
    def update_config(self, host: str, port: int, log_level: str, workers: int, 
                     nginx_proxy: bool = True, nginx_port: int = 8080, 
                     nginx_server_name: str = "localhost", nginx_version: str = "1.26.0", 
                     nginx_install_path: str = "nginx", nginx_worker_processes: str = "auto", 
                     nginx_worker_connections: int = 1024, nginx_keepalive_timeout: int = 65):
        """
        更新配置显示
        
        Args:
            host: 主机地址
            port: 端口号
            log_level: 日志级别
            workers: 工作进程数
            nginx_proxy: 是否启用Nginx代理
            nginx_port: Nginx监听端口
            nginx_server_name: Nginx服务器名称
            nginx_version: Nginx版本
            nginx_install_path: Nginx安装路径
            nginx_worker_processes: Nginx工作进程数
            nginx_worker_connections: Nginx工作进程最大连接数
            nginx_keepalive_timeout: Nginx长连接超时时间
        """
        self.host_input.setText(host)
        self.port_input.setText(str(port))
        self.log_level_combo.setCurrentText(log_level)
        self.workers_input.setText(str(workers))
        
        # 更新Nginx基本配置
        self.nginx_proxy_check.setChecked(nginx_proxy)
        self.nginx_port_input.setText(str(nginx_port))
        self.nginx_server_name_input.setText(nginx_server_name)
        
        # 更新Nginx高级配置
        self.nginx_version_input.setText(nginx_version)
        self.nginx_install_path_input.setText(nginx_install_path)
        self.nginx_worker_processes_input.setText(nginx_worker_processes)
        self.nginx_worker_connections_input.setText(str(nginx_worker_connections))
        self.nginx_keepalive_timeout_input.setText(str(nginx_keepalive_timeout))