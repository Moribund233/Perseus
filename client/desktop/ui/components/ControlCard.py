"""
控制卡片组件

提供服务的启动、停止、重启等控制功能
"""
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QGridLayout
)
from PySide6.QtCore import Qt, Signal
from client.desktop.ui.constants import QSS_STYLES


class ControlCard(QWidget):
    """
    控制卡片组件类
    
    信号：
        start_clicked: 启动按钮点击信号
        stop_clicked: 停止按钮点击信号
        restart_clicked: 重启按钮点击信号
    """
    # 定义信号
    start_clicked = Signal()
    stop_clicked = Signal()
    restart_clicked = Signal()
    
    def __init__(self, parent=None):
        """
        初始化控制卡片
        
        Args:
            parent: 父窗口
        """
        super().__init__(parent)
        self.setup_ui()
        self.setup_connections()
        self.setObjectName("card")
        self.setStyleSheet(QSS_STYLES["card"] + QSS_STYLES["button"] + QSS_STYLES["card_title"])
    
    def setup_ui(self):
        """
        设置UI组件
        """
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # 标题
        title_label = QLabel("服务控制")
        title_label.setObjectName("card_title")
        main_layout.addWidget(title_label)
        
        # 按钮布局
        buttons_layout = QGridLayout()
        buttons_layout.setSpacing(8)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        
        # 启动按钮
        self.start_button = QPushButton("启动")
        self.start_button.setMinimumHeight(25)
        self.start_button.setCursor(Qt.PointingHandCursor)
        buttons_layout.addWidget(self.start_button, 0, 0)
        
        # 停止按钮
        self.stop_button = QPushButton("停止")
        self.stop_button.setMinimumHeight(25)
        self.stop_button.setCursor(Qt.PointingHandCursor)
        buttons_layout.addWidget(self.stop_button, 0, 1)
        
        # 重启按钮
        self.restart_button = QPushButton("重启")
        self.restart_button.setMinimumHeight(25)
        self.restart_button.setCursor(Qt.PointingHandCursor)
        buttons_layout.addWidget(self.restart_button, 1, 0, 1, 2)
        
        main_layout.addLayout(buttons_layout)
    
    def setup_connections(self):
        """
        设置信号连接
        """
        self.start_button.clicked.connect(self.start_clicked)
        self.stop_button.clicked.connect(self.stop_clicked)
        self.restart_button.clicked.connect(self.restart_clicked)
    
    def update_buttons_state(self, is_running: bool):
        """
        更新按钮状态
        
        Args:
            is_running: 服务是否正在运行
        """
        self.start_button.setEnabled(not is_running)
        self.stop_button.setEnabled(is_running)
        self.restart_button.setEnabled(True)