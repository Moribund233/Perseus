"""
UI常量定义模块

包含应用程序使用的QSS样式、尺寸常量等
"""

# QSS样式表定义
QSS_STYLES = {
    "main_window": """
        /* 主窗口样式 */
        QMainWindow {
            background-color: #f5f5f7;
            border: none;
        }
        
        QWidget {
            font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
        }
    """,
    
    "left_panel": """
        /* 左侧面板样式 */
        QWidget#left_panel {
            background-color: #ffffff;
            border-right: 1px solid #e0e0e0;
            border-radius: 8px;
            margin: 10px;
        }
    """,
    
    "right_panel": """
        /* 右侧面板样式 */
        QWidget#right_panel {
            background-color: #ffffff;
            border-radius: 8px;
            margin: 10px;
        }
    """,
    
    "scroll_area": """
        /* 滚动区域样式 */
        QScrollArea {
            background-color: transparent;
            border: none;
        }
        
        QScrollArea::viewport {
            background-color: transparent;
        }
        
        QScrollBar:vertical {
            background-color: #f0f0f0;
            width: 8px;
            margin: 0px;
            border-radius: 4px;
        }
        
        QScrollBar::handle:vertical {
            background-color: #c0c0c0;
            border-radius: 4px;
            min-height: 20px;
        }
        
        QScrollBar::handle:vertical:hover {
            background-color: #a0a0a0;
        }
        
        QScrollBar::add-line:vertical,
        QScrollBar::sub-line:vertical {
            height: 0px;
        }
        
        QScrollBar::add-page:vertical,
        QScrollBar::sub-page:vertical {
            background-color: transparent;
        }
    """,
    
    "card": """
        /* 卡片样式 */
        QWidget#card {
            background-color: #ffffff;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            padding: 10px;
            margin-bottom: 10px;
        }
        
        QWidget#card:hover {
            border-color: #d0d0d0;
        }
    """,
    
    "card_title": """
        /* 卡片标题样式 */
        QLabel#card_title {
            font-size: 12px;
            font-weight: 600;
            color: #1d1d1f;
            margin-bottom: 8px;
        }
    """,
    
    "button": """
        /* 按钮样式 */
        QPushButton {
            background-color: #007aff;
            color: white;
            border: none;
            border-radius: 6px;
            padding: 6px 12px;
            font-size: 12px;
            font-weight: 500;
        }
        
        QPushButton:hover {
            background-color: #0056b3;
        }
        
        QPushButton:pressed {
            background-color: #004085;
        }
        
        QPushButton:disabled {
            background-color: #d0d0d0;
            color: #909090;
        }
        
        QPushButton#secondary_button {
            background-color: #f0f0f0;
            color: #1d1d1f;
            border: 1px solid #e0e0e0;
        }
        
        QPushButton#secondary_button:hover {
            background-color: #e0e0e0;
        }
    """,
    
    "status_label": """
        /* 状态标签样式 */
        QLabel#status_label {
            font-size: 12px;
            padding: 4px 8px;
            border-radius: 12px;
            font-weight: 500;
        }
        
        QLabel#status_running {
            background-color: #e8f5e8;
            color: #2e7d32;
        }
        
        QLabel#status_stopped {
            background-color: #ffebee;
            color: #c62828;
        }
        
        QLabel#status_starting {
            background-color: #fff3e0;
            color: #ef6c00;
        }
        
        QLabel#status_stopping {
            background-color: #fff3e0;
            color: #ef6c00;
        }
        
        QLabel#status_error {
            background-color: #ffebee;
            color: #c62828;
        }
    """,
    
    "log_text": """
        /* 日志文本框样式 */
        QTextEdit {
            background-color: #1d1d1f;
            color: #f5f5f7;
            border: 1px solid #333333;
            border-radius: 6px;
            padding: 8px;
            font-family: 'Consolas', 'Monaco', monospace;
            font-size: 10px;
            line-height: 1.3;
        }
        
        QTextEdit:focus {
            border-color: #007aff;
        }
    """,
    
    "line_edit": """
        /* 输入框样式 */
        QLineEdit {
            background-color: #f5f5f7;
            color: #1d1d1f;
            border: 1px solid #e0e0e0;
            border-radius: 4px;
            padding: 4px 8px;
            font-size: 12px;
        }
        
        QLineEdit:focus {
            background-color: white;
            border-color: #007aff;
        }
    """,
    
    "combo_box": """
        /* 下拉框样式 */
        QComboBox {
            background-color: #f5f5f7;
            color: #1d1d1f;
            border: 1px solid #e0e0e0;
            border-radius: 4px;
            padding: 4px 8px;
            font-size: 12px;
        }
        
        QComboBox:focus {
            background-color: white;
            border-color: #007aff;
        }
        
        QComboBox QAbstractItemView {
            background-color: white;
            border: 1px solid #e0e0e0;
            border-radius: 4px;
            padding: 2px;
        }
    """,
    
    "checkbox": """
        /* 复选框样式 */
        QCheckBox {
            color: #1d1d1f;
            font-size: 14px;
        }
        
        QCheckBox::indicator {
            width: 18px;
            height: 18px;
            border: 2px solid #e0e0e0;
            border-radius: 4px;
            background-color: white;
        }
        
        QCheckBox::indicator:checked {
            background-color: #007aff;
            border-color: #007aff;
            image: url(:/icons/check.svg);
        }
    """,
    "splash_screen": """
        /* 首屏样式 */
        QSplashScreen {
            background-color: white;
            border-radius: 10px;
        }
        
        QLabel#splash_app_name {
            color: #1d1d1f;
            font-size: 28px;
            font-weight: bold;
        }
        
        QLabel#splash_app_desc {
            color: #666666;
            font-size: 14px;
        }
        
        QLabel#splash_status {
            color: #888888;
            font-size: 12px;
        }
        
        QProgressBar#splash_progress {
            background-color: #f0f0f0;
            border: none;
            border-radius: 4px;
            text-align: center;
        }
        
        QProgressBar#splash_progress::chunk {
            background-color: #007aff;
            border-radius: 4px;
        }
    """
}

# 尺寸常量定义
UI_SIZES = {
    "main_window": {
        "width": 614,
        "height": 461
    },
    "left_panel": {
        "width": 192
    },
    "card": {
        "min_width": 168,
        "padding": 10
    },
    "button": {
        "min_height": 22,
        "min_width": 48
    },
    "status_label": {
        "height": 19
    },
    "splash_screen": {
        "width": 600,
        "height": 400
    }
}

# 图标路径
ICONS = {
    "start": ":/icons/start.svg",
    "stop": ":/icons/stop.svg",
    "restart": ":/icons/restart.svg",
    "settings": ":/icons/settings.svg",
    "info": ":/icons/info.svg",
    "error": ":/icons/error.svg",
    "warning": ":/icons/warning.svg"
}