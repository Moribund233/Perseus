"""
LanGit 桌面客户端启动入口

启动PySide6桌面应用程序，显示主窗口
"""
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from client.desktop.MainWindow import MainWindow


def main():
    """
    主函数
    
    初始化QApplication并显示主窗口
    """
    # 首先调用服务端init模块生成配置文件
    print("正在初始化配置文件...")
    try:
        from init import init_app
        init_app(check_service=True)  # 初始化配置文件，并检查服务
        print("配置文件初始化完成")
    except Exception as e:
        print(f"配置文件初始化失败: {e}")
        print("继续启动客户端...")
    
    # 创建应用程序实例
    app = QApplication(sys.argv)
    
    # 设置应用程序名称和图标
    app.setApplicationName("LanGit")
    app.setApplicationDisplayName("LanGit 桌面客户端")
    
    # 设置应用程序图标
    icon_path = "client/desktop/ui/icons/logo.ico"
    app.setWindowIcon(QIcon(icon_path))
    
    # 创建并显示主窗口
    window = MainWindow()
    window.show()
    
    # 运行应用程序事件循环
    sys.exit(app.exec())


if __name__ == "__main__":
    main()