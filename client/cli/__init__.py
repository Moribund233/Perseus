"""
LanGit CLI客户端模块

提供两种CLI模式：
1. 命令参数型CLI（基于click库）
2. 交互界面CLI（基于rich库）
"""
from client.cli.cli import cli as click_cli
from client.cli.ui.rich_ui import get_rich_ui, RichUI

__all__ = [
    'click_cli',
    'get_rich_ui',
    'RichUI'
]
