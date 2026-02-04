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
        
        main_layout.addLayout(config_layout)
        
        # 重置按钮
        self.reset_button = QPushButton("重置默认配置")
        self.reset_button.setObjectName("secondary_button")
        self.reset_button.setMinimumHeight(25)
        self.reset_button.setCursor(Qt.PointingHandCursor)
        self.reset_button.clicked.connect(self.reset_clicked)
        main_layout.addWidget(self.reset_button)
    
    def update_config(self, host: str, port: int, log_level: str, workers: int):
        """
        更新配置显示
        
        Args:
            host: 主机地址
            port: 端口号
            log_level: 日志级别
            workers: 工作进程数
        """
        self.host_input.setText(host)
        self.port_input.setText(str(port))
        self.log_level_combo.setCurrentText(log_level)
        self.workers_input.setText(str(workers))