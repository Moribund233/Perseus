"""
LanGit CLI客户端 - Rich交互界面

提供基于rich库的交互式命令行界面，用于管理FastAPI服务的生命周期。
"""
import time
import threading
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.layout import Layout
from rich.live import Live
from rich.prompt import Prompt, Confirm
from rich.status import Status
from rich.progress import Progress, SpinnerColumn, TextColumn
from client.controller.service_controller import get_service_controller, ServiceState
from client.utils.config_manager import get_client_config_manager


class RichUI:
    """
    Rich交互式UI类
    
    提供基于rich库的交互式命令行界面，用于管理FastAPI服务。
    """
    
    def __init__(self, config_path: str = 'config.toml'):
        """
        初始化RichUI
        
        Args:
            config_path: 配置文件路径
        """
        self.console = Console()
        self.config_path = config_path
        self.controller = get_service_controller(config_path)
        self.config_manager = get_client_config_manager(config_path)
        self.is_running = False
        self.log_update_event = threading.Event()
        self.log_lines = []
        
        # 设置日志回调
        self.controller.set_log_callback(self._on_log)
    
    def _on_log(self, log_line: str) -> None:
        """
        日志回调函数
        
        Args:
            log_line: 日志行
        """
        self.log_lines.append(log_line)
        # 保留最近1000条日志
        if len(self.log_lines) > 1000:
            self.log_lines = self.log_lines[-1000:]
        self.log_update_event.set()
    
    def _get_service_status_panel(self) -> Panel:
        """
        获取服务状态面板
        
        Returns:
            Panel: 服务状态面板
        """
        state = self.controller.get_state()
        is_running = self.controller.is_running()
        
        status_text = Text()
        status_text.append("服务状态: ", style="bold")
        
        if state == ServiceState.RUNNING:
            status_text.append("RUNNING", style="green bold")
        elif state == ServiceState.STARTING:
            status_text.append("STARTING", style="yellow bold")
        elif state == ServiceState.STOPPING:
            status_text.append("STOPPING", style="yellow bold")
        elif state == ServiceState.ERROR:
            status_text.append("ERROR", style="red bold")
        else:
            status_text.append("STOPPED", style="gray bold")
        
        # 获取服务器配置
        server_config = self.config_manager.get_server_config()
        host = server_config.get('host', '0.0.0.0')
        port = server_config.get('port', 8000)
        
        table = Table.grid(padding=(0, 2), expand=True)
        table.add_row("状态", status_text)
        table.add_row("地址", f"http://{host}:{port}")
        table.add_row("配置文件", self.config_path)
        
        if is_running and hasattr(self.controller, 'process') and self.controller.process:
            table.add_row("PID", str(self.controller.process.pid))
        
        return Panel(table, title="服务信息", title_align="left")
    
    def _get_logs_panel(self, lines: int = 20) -> Panel:
        """
        获取日志面板
        
        Args:
            lines: 显示日志行数
        
        Returns:
            Panel: 日志面板
        """
        logs = self.log_lines[-lines:]
        log_text = "\n".join(logs)
        
        return Panel(
            log_text,
            title="服务日志",
            title_align="left",
            height=25
        )
    
    def _get_menu_panel(self) -> Panel:
        """
        获取菜单面板
        
        Returns:
            Panel: 菜单面板
        """
        menu_items = [
            "[1] 启动服务",
            "[2] 停止服务",
            "[3] 重启服务",
            "[4] 查看状态",
            "[5] 查看配置",
            "[6] 修改配置",
            "[7] 查看日志",
            "[8] 清除日志",
            "[9] 重置配置",
            "[0] 退出"
        ]
        
        menu_text = "\n".join(menu_items)
        
        return Panel(
            menu_text,
            title="操作菜单",
            title_align="left",
            style="blue"
        )
    
    def _refresh_ui(self, layout: Layout) -> None:
        """
        刷新UI布局
        
        Args:
            layout: UI布局
        """
        layout.split(
            Layout(name="header", size=3),
            Layout(name="main", ratio=1),
            Layout(name="footer", size=10)
        )
        
        layout["main"].split_row(
            Layout(name="left", size=40),
            Layout(name="right", ratio=1)
        )
        
        layout["header"].update(
            Panel(
                Text("LanGit FastAPI服务管理工具", style="bold blue"),
                title_align="center"
            )
        )
        
        layout["left"].split_column(
            Layout(name="status", size=15),
            Layout(name="menu")
        )
        
        layout["status"].update(self._get_service_status_panel())
        layout["menu"].update(self._get_menu_panel())
        layout["right"].update(self._get_logs_panel())
        
        layout["footer"].update(
            Panel(
                Text("按Enter键刷新 | 输入菜单编号执行操作", style="dim"),
                title_align="center"
            )
        )
    
    def _handle_menu_choice(self, choice: str) -> bool:
        """
        处理菜单选择
        
        Args:
            choice: 菜单选择
        
        Returns:
            bool: 是否继续运行UI
        """
        if choice == "1":
            self._action_start()
        elif choice == "2":
            self._action_stop()
        elif choice == "3":
            self._action_restart()
        elif choice == "4":
            self._action_status()
        elif choice == "5":
            self._action_show_config()
        elif choice == "6":
            self._action_edit_config()
        elif choice == "7":
            self._action_show_logs()
        elif choice == "8":
            self._action_clear_logs()
        elif choice == "9":
            self._action_reset_config()
        elif choice == "0":
            return False
        else:
            self.console.print("[red]无效的选择，请重新输入[/red]")
        
        return True
    
    def _action_start(self) -> None:
        """
        执行启动服务操作
        """
        if self.controller.is_running():
            self.console.print("[yellow]服务已在运行中[/yellow]")
            return
        
        with Status("正在启动服务...", console=self.console) as status:
            if self.controller.start(block=True, timeout=10):
                self.console.print("[green]服务启动成功[/green]")
            else:
                self.console.print("[red]服务启动失败[/red]")
    
    def _action_stop(self) -> None:
        """
        执行停止服务操作
        """
        if not self.controller.is_running():
            self.console.print("[yellow]服务未在运行中[/yellow]")
            return
        
        with Status("正在停止服务...", console=self.console) as status:
            if self.controller.stop(timeout=10):
                self.console.print("[green]服务停止成功[/green]")
            else:
                self.console.print("[red]服务停止失败[/red]")
    
    def _action_restart(self) -> None:
        """
        执行重启服务操作
        """
        with Status("正在重启服务...", console=self.console) as status:
            if self.controller.restart(timeout=15):
                self.console.print("[green]服务重启成功[/green]")
            else:
                self.console.print("[red]服务重启失败[/red]")
    
    def _action_status(self) -> None:
        """
        执行查看状态操作
        """
        self.console.print(self._get_service_status_panel())
    
    def _action_show_config(self) -> None:
        """
        执行查看配置操作
        """
        config = self.config_manager.load_config()
        
        table = Table(title="配置信息", expand=True)
        table.add_column("配置项", style="bold")
        table.add_column("值")
        
        for section, section_config in config.items():
            for key, value in section_config.items():
                table.add_row(f"{section}.{key}", str(value))
        
        self.console.print(table)
    
    def _action_edit_config(self) -> None:
        """
        执行修改配置操作
        """
        key = Prompt.ask("请输入配置项键名", default="server.port")
        current_value = self.config_manager.get(key)
        
        if current_value is not None:
            self.console.print(f"当前值: {current_value}")
        
        value = Prompt.ask("请输入新值")
        
        if self.controller.update_config(key, value):
            self.console.print("[green]配置更新成功[/green]")
        else:
            self.console.print("[red]配置更新失败[/red]")
    
    def _action_show_logs(self) -> None:
        """
        执行查看日志操作
        """
        lines = Prompt.ask("请输入显示日志行数", default="50")
        try:
            lines = int(lines)
        except ValueError:
            lines = 50
        
        logs = self.log_lines[-lines:]
        log_text = "\n".join(logs)
        self.console.print(Panel(log_text, title="完整日志"))
    
    def _action_clear_logs(self) -> None:
        """
        执行清除日志操作
        """
        if Confirm.ask("确定要清除所有日志吗？"):
            self.controller.clear_logs()
            self.log_lines.clear()
            self.console.print("[green]日志已清除[/green]")
    
    def _action_reset_config(self) -> None:
        """
        执行重置配置操作
        """
        if Confirm.ask("确定要重置配置为默认值吗？"):
            if self.config_manager.reset_to_defaults():
                self.console.print("[green]配置已重置为默认值[/green]")
            else:
                self.console.print("[red]配置重置失败[/red]")
    
    def run_interactive(self) -> None:
        """
        运行交互式UI
        
        启动基于rich库的交互式命令行界面。
        """
        self.is_running = True
        
        layout = Layout()
        self._refresh_ui(layout)
        
        with Live(layout, console=self.console, refresh_per_second=10) as live:
            while self.is_running:
                # 检查日志更新
                if self.log_update_event.wait(0.1):
                    layout["right"].update(self._get_logs_panel())
                    self.log_update_event.clear()
                
                # 检查服务状态变化
                layout["status"].update(self._get_service_status_panel())
                
                # 等待用户输入
                choice = self.console.input("\n请输入操作编号: ").strip()
                if choice:
                    if not self._handle_menu_choice(choice):
                        self.is_running = False
                
                # 刷新UI
                self._refresh_ui(layout)
    
    def run_cli(self, command: str, **kwargs) -> None:
        """
        运行CLI命令模式
        
        Args:
            command: 命令名称
            **kwargs: 命令参数
        """
        with Status(f"执行命令: {command}", console=self.console) as status:
            if command == "start":
                block = kwargs.get("block", False)
                timeout = kwargs.get("timeout", 10)
                if self.controller.start(block=block, timeout=timeout):
                    self.console.print("[green]服务启动成功[/green]")
                else:
                    self.console.print("[red]服务启动失败[/red]")
            
            elif command == "stop":
                timeout = kwargs.get("timeout", 10)
                if self.controller.stop(timeout=timeout):
                    self.console.print("[green]服务停止成功[/green]")
                else:
                    self.console.print("[red]服务停止失败[/red]")
            
            elif command == "restart":
                timeout = kwargs.get("timeout", 10)
                if self.controller.restart(timeout=timeout):
                    self.console.print("[green]服务重启成功[/green]")
                else:
                    self.console.print("[red]服务重启失败[/red]")
            
            elif command == "status":
                self.console.print(self._get_service_status_panel())
            
            elif command == "logs":
                lines = kwargs.get("lines", 20)
                logs = self.controller.get_logs(lines=lines)
                log_text = "\n".join(logs)
                self.console.print(Panel(log_text, title="服务日志"))
            
            elif command == "clear_logs":
                self.controller.clear_logs()
                self.console.print("[green]日志已清除[/green]")
            
            elif command == "config":
                key = kwargs.get("key")
                value = kwargs.get("value")
                if key and value:
                    if self.controller.update_config(key, value):
                        self.console.print(f"[green]配置已更新: {key} = {value}[/green]")
                    else:
                        self.console.print("[red]配置更新失败[/red]")
                else:
                    self._action_show_config()
            
            else:
                self.console.print(f"[red]未知命令: {command}[/red]")


# 创建全局RichUI实例
_rich_ui: Optional[RichUI] = None


def get_rich_ui(config_path: str = "config.toml") -> RichUI:
    """
    获取全局RichUI实例
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        RichUI: RichUI实例
    """
    global _rich_ui
    if _rich_ui is None:
        _rich_ui = RichUI(config_path)
    return _rich_ui
