"""
首屏组件

显示应用程序的启动画面，包括Logo、名称和初始化进度
"""
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QProgressBar,
    QSplashScreen,
    QFrame
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QIcon, QColor
from client.desktop.ui.constants import UI_SIZES, QSS_STYLES


class SplashScreen(QSplashScreen):
    """
    首屏组件类
    
    信号：
        initialization_completed: 初始化完成信号
    """
    # 定义信号
    initialization_completed = Signal()
    
    def __init__(self, parent=None):
        """
        初始化首屏组件
        
        Args:
            parent: 父窗口
        """
        # 创建白色背景的QPixmap
        width = UI_SIZES.get("splash_screen", {}).get("width", 600)
        height = UI_SIZES.get("splash_screen", {}).get("height", 400)
        pixmap = QPixmap(width, height)
        pixmap.fill(QColor(255, 255, 255))  # 白色背景
        
        super().__init__(pixmap, Qt.WindowStaysOnTopHint)
        
        # 设置窗口属性
        self.setObjectName("splash_screen")
        self.setFixedSize(width, height)
        self.setWindowFlags(Qt.SplashScreen | Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        
        # 初始化UI组件
        self.setup_ui()
        
        # 初始化进度
        self._progress = 0
        
        # 将窗口居中显示
        self.center()
        
    def center(self):
        """
        将窗口居中显示在屏幕上
        """
        # 获取屏幕几何信息
        screen_geometry = self.screen().availableGeometry()
        # 获取窗口几何信息
        window_geometry = self.frameGeometry()
        # 计算窗口中心位置
        center_point = screen_geometry.center()
        # 将窗口中心设置为屏幕中心
        window_geometry.moveCenter(center_point)
        # 移动窗口到计算出的位置
        self.move(window_geometry.topLeft())
    
    def setup_ui(self):
        """
        设置UI组件
        """
        # 创建一个透明背景的容器用于显示文本
        mask_widget = QWidget(self)
        mask_widget.setStyleSheet("background-color: transparent;")
        mask_widget.setFixedSize(400, 200)
        
        # 居中容器
        mask_layout = QVBoxLayout(self)
        mask_layout.setAlignment(Qt.AlignCenter)
        mask_layout.addWidget(mask_widget, alignment=Qt.AlignCenter)
        
        # 容器内部布局
        inner_layout = QVBoxLayout(mask_widget)
        inner_layout.setSpacing(20)
        inner_layout.setContentsMargins(30, 30, 30, 30)
        inner_layout.setAlignment(Qt.AlignCenter)
        
        # 应用名称
        self.app_name_label = QLabel("LanGit")
        self.app_name_label.setObjectName("splash_app_name")
        self.app_name_label.setAlignment(Qt.AlignCenter)
        inner_layout.addWidget(self.app_name_label)
        
        # 应用描述
        self.app_desc_label = QLabel("局域网Git服务平台")
        self.app_desc_label.setObjectName("splash_app_desc")
        self.app_desc_label.setAlignment(Qt.AlignCenter)
        inner_layout.addWidget(self.app_desc_label)
        
        # 状态信息
        self.status_label = QLabel("正在初始化...")
        self.status_label.setObjectName("splash_status")
        self.status_label.setAlignment(Qt.AlignCenter)
        inner_layout.addWidget(self.status_label)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("splash_progress")
        self.progress_bar.setFixedWidth(300)
        self.progress_bar.setMinimumHeight(8)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        inner_layout.addWidget(self.progress_bar)
        
        # 应用QSS样式
        self.setStyleSheet(QSS_STYLES["splash_screen"])
    
    def update_progress(self, progress: int, status: str):
        """
        更新进度和状态
        
        Args:
            progress: 进度值（0-100）
            status: 状态文本
        """
        self._progress = max(0, min(100, progress))
        self.progress_bar.setValue(self._progress)
        self.status_label.setText(status)
    
    def set_status(self, status: str):
        """
        设置状态信息
        
        Args:
            status: 状态文本
        """
        self.status_label.setText(status)
    
    def set_progress(self, progress: int):
        """
        设置进度值
        
        Args:
            progress: 进度值（0-100）
        """
        self._progress = max(0, min(100, progress))
        self.progress_bar.setValue(self._progress)
    
    def complete_initialization(self):
        """
        完成初始化
        
        设置进度为100%，显示完成信息，然后发出初始化完成信号
        """
        self._progress = 100
        self.progress_bar.setValue(self._progress)
        self.status_label.setText("初始化完成，正在启动应用...")
        
        # 直接发出完成信号
        self.initialization_completed.emit()
    
    def show_message(self, message: str, alignment: Qt.Alignment = Qt.AlignBottom | Qt.AlignHCenter):
        """
        在首屏上显示消息
        
        Args:
            message: 要显示的消息
            alignment: 消息对齐方式
        """
        super().showMessage(message, alignment, Qt.white)
