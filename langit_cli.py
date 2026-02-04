"""
LanGit CLI客户端入口文件

支持两种运行模式：
1. 命令参数模式（默认）：使用click库的命令行界面
2. 交互界面模式：使用rich库的交互式界面

Usage:
  python langit_cli.py [command] [options]    # 命令参数模式
  python langit_cli.py --interactive         # 交互界面模式
  python langit_cli.py -i                    # 交互界面模式
"""
import sys
import argparse
from client.cli import click_cli, get_rich_ui


def main():
    """
    主函数
    
    解析命令行参数，选择运行模式：
    - 命令参数模式：使用click库的命令行界面
    - 交互界面模式：使用rich库的交互式界面
    """
    # 创建解析器，用于处理--interactive和-i参数
    parser = argparse.ArgumentParser(
        description='LanGit FastAPI服务管理工具',
        add_help=False  # 不添加默认的help选项，由click处理
    )
    
    # 添加交互式模式选项
    parser.add_argument(
        '-i', '--interactive',
        action='store_true',
        help='启动交互式界面模式'
    )
    
    # 添加版本选项
    parser.add_argument(
        '-v', '--version',
        action='store_true',
        help='显示版本信息'
    )
    
    # 添加帮助选项
    parser.add_argument(
        '-h', '--help',
        action='store_true',
        help='显示帮助信息'
    )
    
    # 只解析已知的选项，剩余的参数交给click处理
    known_args, remaining_args = parser.parse_known_args()
    
    # 处理特殊选项
    if known_args.version:
        print('LanGit CLI v0.1.0')
        return
    
    if known_args.help:
        print(__doc__)
        return
    
    # 检查是否使用交互式模式
    if known_args.interactive:
        # 启动rich交互式界面
        rich_ui = get_rich_ui()
        rich_ui.run_interactive()
    else:
        # 启动click命令参数模式
        # 将剩余参数传递给click
        sys.argv = [sys.argv[0]] + remaining_args
        click_cli()


if __name__ == '__main__':
    main()
