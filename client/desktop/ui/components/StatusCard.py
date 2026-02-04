"""
状态卡片组件

显示服务的运行状态、端口信息等
"""
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel
)
from PySide6.QtCore import Qt
from client.desktop.ui.constants import QSS_STYLES


class StatusCard(QWidget):
    """
    状态卡片组件类
    """
    def __init__(self, parent=None):
        """
        初始化状态卡片
        
        Args:
            parent: 父窗口
        """
        super().__init__(parent)
        self.setup_ui()
        self.setObjectName("card")
        self.setStyleSheet(QSS_STYLES["card"] + QSS_STYLES["status_label"] + QSS_STYLES["card_title"])
    
    def setup_ui(self):
        """
        设置UI组件
        """
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # 标题
        title_label = QLabel("服务状态")
        title_label.setObjectName("card_title")
        main_layout.addWidget(title_label)
        
        # 状态显示
        status_layout = QVBoxLayout()
        status_layout.setSpacing(8)
        
        # 服务状态
        self.status_row = self.create_status_row("服务状态:")
        self.status_value = self.status_row["value"]
        status_layout.addLayout(self.status_row["layout"])
        
        # 端口
        self.port_row = self.create_status_row("端口:")
        self.port_value = self.port_row["value"]
        status_layout.addLayout(self.port_row["layout"])
        
        # 地址
        self.address_row = self.create_status_row("地址:")
        self.address_value = self.address_row["value"]
        status_layout.addLayout(self.address_row["layout"])
        
        main_layout.addLayout(status_layout)
    
    def create_status_row(self, label_text: str):
        """
        创建状态行
        
        Args:
            label_text: 标签文本
            
        Returns:
            dict: 包含布局和值标签的字典
        """
        row_layout = QHBoxLayout()
        row_layout.setSpacing(6)
        row_layout.setContentsMargins(0, 0, 0, 0)
        
        # 标签
        label = QLabel(label_text)
        label.setMinimumWidth(50)
        label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        row_layout.addWidget(label)
        
        # 值
        value = QLabel()
        value.setObjectName("status_label")
        value.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        value.setWordWrap(True)
        row_layout.addWidget(value)
        
        return {"layout": row_layout, "value": value}
    
    def update_status(self, status: str, port: int, host: str):
        """
        更新状态信息
        
        Args:
            status: 服务状态
            port: 端口号
            host: 主机地址
        """
        # 更新状态显示
        self.status_value.setText(status)
        self.status_value.setObjectName(f"status_{status.lower()}")
        
        # 更新端口显示
        self.port_value.setText(str(port))
        self.port_value.setObjectName("status_label")
        
        # 更新地址显示
        self.address_value.setText(f"http://{host}:{port}")
        self.address_value.setObjectName("status_label")
        
        # 重新应用样式
        self.setStyleSheet(QSS_STYLES["card"] + QSS_STYLES["status_label"] + QSS_STYLES["card_title"])