"""
主窗口模块

包含应用程序的主窗口布局和事件处理
"""
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QScrollArea,
    QTextEdit,
    QSplitter,
    QLabel
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont, QIcon, QPixmap
from client.desktop.ui.components.ControlCard import ControlCard
from client.desktop.ui.components.StatusCard import StatusCard
from client.desktop.ui.components.SettingsCard import SettingsCard
from client.desktop.ui.constants import QSS_STYLES, UI_SIZES
from client.controller.service_controller import ServiceController, ServiceState
from client.utils.config_manager import ClientConfigManager


class LogUpdaterThread(QThread):
    """
    日志更新线程
    
    信号：
        new_log: 新日志行信号
    """
    new_log = Signal(str)
    
    def __init__(self, service_controller: ServiceController):
        """
        初始化日志更新线程
        
        Args:
            service_controller: 服务控制器实例
        """
        super().__init__()
        self.service_controller = service_controller
        self.running = True
    
    def run(self):
        """
        运行线程
        """
        def log_callback(log_line):
            """
            日志回调函数
            
            Args:
                log_line: 日志行
            """
            self.new_log.emit(log_line)
        
        # 设置日志回调
        self.service_controller.set_log_callback(log_callback)
        
        # 初始加载现有日志
        for log_line in self.service_controller.get_logs(100):
            self.new_log.emit(log_line)
        
        # 保持线程运行
        while self.running:
            self.msleep(100)
    
    def stop(self):
        """
        停止线程
        """
        self.running = False
        self.wait()


class MainWindow(QMainWindow):
    """
    主窗口类
    """
    def __init__(self, parent=None):
        """
        初始化主窗口
        
        Args:
            parent: 父窗口
        """
        super().__init__(parent)
        self.setup_ui()
        self.setup_connections()
        self.setup_controllers()
        self.load_initial_data()
    
    def setup_ui(self):
        """
        设置UI组件
        """
        # 设置窗口属性
        self.setWindowTitle("LanGit 桌面客户端")
        self.resize(UI_SIZES["main_window"]["width"], UI_SIZES["main_window"]["height"])
        self.setMinimumSize(600, 400)
        
        # 设置窗口图标
        icon_path = "d:/Project/Python/LanGit/client/desktop/ui/icons/logo.svg"
        pixmap = QPixmap(icon_path)
        self.setWindowIcon(QIcon(pixmap))
        
        # 主部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局 - 分割器
        splitter = QSplitter(Qt.Horizontal, central_widget)
        splitter.setHandleWidth(5)
        splitter.setStyleSheet("QSplitter::handle { background-color: #e0e0e0; }")
        
        # 左侧面板 - 卡片容器
        left_widget = QWidget()
        left_widget.setObjectName("left_panel")
        left_widget.setStyleSheet(QSS_STYLES["left_panel"])
        
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(8, 8, 8, 8)
        
        # 滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet(QSS_STYLES["scroll_area"])
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)  # 取消水平滚动条
        
        # 滚动内容
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(0)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        
        # 添加卡片
        self.control_card = ControlCard()
        scroll_layout.addWidget(self.control_card)
        
        self.status_card = StatusCard()
        scroll_layout.addWidget(self.status_card)
        
        self.settings_card = SettingsCard()
        scroll_layout.addWidget(self.settings_card)
        
        # 添加伸缩空间
        scroll_layout.addStretch()
        
        # 设置滚动内容
        scroll_area.setWidget(scroll_content)
        left_layout.addWidget(scroll_area)
        
        # 右侧面板 - 日志区域
        right_widget = QWidget()
        right_widget.setObjectName("right_panel")
        right_widget.setStyleSheet(QSS_STYLES["right_panel"])
        
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(8, 8, 8, 8)
        right_layout.setSpacing(8)
        
        # 日志标题
        log_title = QLabel("服务日志")
        log_title.setObjectName("card_title")
        log_title.setStyleSheet(QSS_STYLES["card_title"])
        right_layout.addWidget(log_title)
        
        # 日志文本框
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setLineWrapMode(QTextEdit.NoWrap)
        self.log_text.setStyleSheet(QSS_STYLES["log_text"])
        self.log_text.setFont(QFont("Consolas", 8))
        right_layout.addWidget(self.log_text)
        
        # 添加到分割器
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        
        # 设置初始分割比例
        splitter.setSizes([UI_SIZES["left_panel"]["width"], self.width() - UI_SIZES["left_panel"]["width"]])
        
        # 设置主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(splitter)
    
    def setup_connections(self):
        """
        设置信号连接
        """
        # 控制卡片信号
        self.control_card.start_clicked.connect(self.on_start_clicked)
        self.control_card.stop_clicked.connect(self.on_stop_clicked)
        self.control_card.restart_clicked.connect(self.on_restart_clicked)
        
        # 设置卡片信号
        self.settings_card.config_changed.connect(self.on_config_changed)
        self.settings_card.reset_clicked.connect(self.on_reset_config)
    
    def setup_controllers(self):
        """
        设置控制器
        """
        # 创建服务控制器实例
        self.service_controller = ServiceController()
        
        # 创建配置管理器实例
        self.config_manager = ClientConfigManager()
        
        # 创建并启动日志更新线程
        self.log_thread = LogUpdaterThread(self.service_controller)
        self.log_thread.new_log.connect(self.add_log_line)
        self.log_thread.start()
    
    def load_initial_data(self):
        """
        加载初始数据
        """
        # 获取配置
        server_config = self.config_manager.get_server_config()
        host = server_config.get("host", "0.0.0.0")
        port = server_config.get("port", 8000)
        log_level = server_config.get("log_level", "info")
        workers = server_config.get("workers", 1)

        # 获取Nginx配置
        nginx_config = self.config_manager.get_nginx_config()
        nginx_proxy = nginx_config.get("proxy", True)
        nginx_port = nginx_config.get("listen_port", 8080)
        nginx_server_name = nginx_config.get("server_name", "localhost")
        
        # 获取Nginx高级配置
        nginx_version = nginx_config.get("version", "1.26.0")
        nginx_install_path = nginx_config.get("install_path", "nginx")
        nginx_worker_processes = nginx_config.get("worker_processes", "auto")
        nginx_worker_connections = nginx_config.get("worker_connections", 1024)
        nginx_keepalive_timeout = nginx_config.get("keepalive_timeout", 65)
        
        # 更新设置卡片
        self.settings_card.update_config(
            host, port, log_level, workers, 
            nginx_proxy, nginx_port, nginx_server_name,
            nginx_version, nginx_install_path, nginx_worker_processes,
            nginx_worker_connections, nginx_keepalive_timeout
        )
        
        # 更新状态卡片
        self.update_status_card()
    
    def update_status_card(self):
        """
        更新状态卡片
        """
        # 获取服务状态
        state = self.service_controller.get_state()
        
        # 获取配置
        server_config = self.config_manager.get_server_config()
        host = server_config.get("host", "0.0.0.0")
        port = server_config.get("port", 8000)
        
        # 更新状态显示
        state_text = state.value.upper()
        self.status_card.update_status(state_text, port, host)
        
        # 更新控制按钮状态
        self.control_card.update_buttons_state(self.service_controller.is_running())
    
    def add_log_line(self, log_line: str):
        """
        添加日志行到日志文本框
        
        Args:
            log_line: 日志行
        """
        self.log_text.append(log_line)
        # 自动滚动到底部
        self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())
    
    def on_start_clicked(self):
        """
        启动按钮点击事件
        """
        # 更新按钮状态
        self.control_card.update_buttons_state(True)
        
        # 启动服务
        success = self.service_controller.start()
        if not success:
            self.control_card.update_buttons_state(False)
        
        # 更新状态卡片
        self.update_status_card()
    
    def on_stop_clicked(self):
        """
        停止按钮点击事件
        """
        # 更新按钮状态
        self.control_card.update_buttons_state(False)
        
        # 停止服务
        self.service_controller.stop()
        
        # 更新状态卡片
        self.update_status_card()
    
    def on_restart_clicked(self):
        """
        重启按钮点击事件
        """
        # 更新按钮状态
        self.control_card.update_buttons_state(True)
        
        # 重启服务
        success = self.service_controller.restart()
        if not success:
            self.control_card.update_buttons_state(False)
        
        # 更新状态卡片
        self.update_status_card()
    
    def on_config_changed(self, key: str, value: str):
        """
        配置变更事件
        
        Args:
            key: 配置键
            value: 配置值
        """
        # 更新配置
        self.service_controller.update_config(key, value)
        
        # 更新状态卡片
        self.update_status_card()
    
    def on_reset_config(self):
        """
        重置配置事件
        """
        # 重置配置
        self.config_manager.reset_to_defaults()
        
        # 重新加载初始数据
        self.load_initial_data()
    
    def closeEvent(self, event):
        """
        窗口关闭事件
        
        Args:
            event: 关闭事件
        """
        # 停止日志更新线程
        self.log_thread.stop()
        
        # 停止服务
        if self.service_controller.is_running():
            self.service_controller.stop()
        
        super().closeEvent(event)