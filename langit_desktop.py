"""
LanGit 桌面客户端启动入口

启动PySide6桌面应用程序，显示主窗口
"""
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt
from client.desktop.MainWindow import MainWindow
from client.desktop.ui.components.SplashScreen import SplashScreen
from client.utils.init import init_client, get_initializer


def main():
    """
    主函数
    
    初始化QApplication，显示首屏，异步初始化配置文件，完成后显示主窗口
    """
    # 创建应用程序实例
    app = QApplication(sys.argv)
    
    # 设置应用程序名称和图标
    app.setApplicationName("LanGit")
    app.setApplicationDisplayName("LanGit 桌面客户端")
    
    # 设置应用程序图标
    icon_path = "client/desktop/ui/icons/logo.ico"
    app.setWindowIcon(QIcon(icon_path))
    
    # 创建并显示首屏
    splash = SplashScreen()
    splash.show()
    
    # 处理首屏显示
    app.processEvents()
    
    # 初始化客户端（异步执行）
    init_thread = init_client(check_service=True, use_thread=True)
    
    # 创建主窗口实例（但不立即显示）
    main_window = None
    
    def on_progress_updated(progress: int, status: str):
        """
        进度更新回调函数
        
        Args:
            progress: 进度值（0-100）
            status: 状态文本
        """
        splash.update_progress(progress, status)
    
    def on_initialization_complete(success: bool, error: str):
        """
        初始化完成回调函数
        
        Args:
            success: 初始化是否成功
            error: 错误信息
        """
        nonlocal main_window
        
        if not success and error:
            print(f"配置文件初始化失败: {error}")
            print("继续启动客户端...")
        else:
            print("配置文件初始化完成")
        
        # 创建主窗口
        main_window = MainWindow()
        
        # 首屏关闭后显示主窗口
        def show_main_window():
            splash.close()
            main_window.show()
        
        # 先连接首屏完成信号到显示主窗口函数
        splash.initialization_completed.connect(show_main_window)
        
        # 然后完成初始化，更新首屏状态并发出信号
        splash.complete_initialization()
    
    # 连接信号和槽函数
    init_thread.progress_updated.connect(on_progress_updated)
    init_thread.initialization_completed.connect(on_initialization_complete)
    
    # 运行应用程序事件循环
    sys.exit(app.exec())


if __name__ == "__main__":
    main()