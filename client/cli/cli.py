"""
LanGit CLI客户端 - Click命令行界面

提供命令参数型CLI，用于管理FastAPI服务的生命周期。
"""
import click
from typing import Optional
from client.controller.service_controller import get_service_controller, ServiceState
from client.utils.config_manager import get_client_config_manager
from client.utils.command_handler import CommandHandler


@click.group()
@click.option('--config', '-c', default='config.toml', help='配置文件路径')
@click.pass_context
def cli(ctx, config: str):
    """
    LanGit FastAPI服务管理工具
    
    用于启动、停止、重启和管理FastAPI服务。
    """
    ctx.ensure_object(dict)
    ctx.obj['config'] = config
    ctx.obj['controller'] = get_service_controller(config)
    ctx.obj['config_manager'] = get_client_config_manager(config)
    ctx.obj['command_handler'] = CommandHandler(ctx.obj['controller'], ctx.obj['config_manager'])


@cli.command()
@click.pass_context
@click.option('--block', '-b', is_flag=True, help='阻塞等待服务启动完成')
@click.option('--timeout', '-t', default=10, help='启动超时时间（秒）')
def start(ctx, block: bool, timeout: int):
    """
    启动FastAPI服务
    
    Args:
        block: 是否阻塞等待服务启动完成
        timeout: 启动超时时间（秒）
    """
    command_handler = ctx.obj['command_handler']
    success, message = command_handler.handle_start(block=block, timeout=timeout)
    if success:
        click.echo(message)
    else:
        click.echo(message, err=True)


@cli.command()
@click.pass_context
@click.option('--timeout', '-t', default=10, help='停止超时时间（秒）')
def stop(ctx, timeout: int):
    """
    停止FastAPI服务
    
    Args:
        timeout: 停止超时时间（秒）
    """
    command_handler = ctx.obj['command_handler']
    success, message = command_handler.handle_stop(timeout=timeout)
    if success:
        click.echo(message)
    else:
        click.echo(message, err=True)


@cli.command()
@click.pass_context
@click.option('--timeout', '-t', default=15, help='重启超时时间（秒）')
def restart(ctx, timeout: int):
    """
    重启FastAPI服务
    
    Args:
        timeout: 重启超时时间（秒）
    """
    command_handler = ctx.obj['command_handler']
    success, message = command_handler.handle_restart(timeout=timeout)
    if success:
        click.echo(message)
    else:
        click.echo(message, err=True)


@cli.command()
@click.pass_context
def status(ctx):
    """
    查看服务状态
    """
    command_handler = ctx.obj['command_handler']
    status_info = command_handler.handle_status()
    click.echo(f'服务状态: {status_info["state"]}')
    
    if status_info["is_running"]:
        click.echo(f'服务地址: {status_info["address"]}')
        if "pid" in status_info:
            click.echo(f'进程ID: {status_info["pid"]}')


@cli.command()
@click.pass_context
@click.option('--lines', '-n', default=100, help='显示日志行数')
def logs(ctx, lines: int):
    """
    查看服务日志
    
    Args:
        lines: 显示日志行数
    """
    command_handler = ctx.obj['command_handler']
    logs = command_handler.handle_logs(lines=lines)
    for line in logs:
        click.echo(line)


@cli.command()
@click.pass_context
def clear_logs(ctx):
    """
    清除服务日志
    """
    command_handler = ctx.obj['command_handler']
    success, message = command_handler.handle_clear_logs()
    click.echo(message)


@cli.command()
@click.pass_context
@click.argument('key')
@click.argument('value')
def config(ctx, key: str, value: str):
    """
    更新配置项
    
    Args:
        key: 配置键名，支持点号分隔的嵌套键，如 'server.port'
        value: 新的配置值
    """
    command_handler = ctx.obj['command_handler']
    success, message = command_handler.handle_update_config(key, value)
    if success:
        click.echo(message)
    else:
        click.echo(message, err=True)


@cli.command()
@click.pass_context
@click.option('--server', '-s', is_flag=True, help='只显示服务器配置')
@click.option('--app', '-a', is_flag=True, help='只显示应用配置')
@click.option('--nginx', '-n', is_flag=True, help='只显示Nginx配置')
def show_config(ctx, server: bool, app: bool, nginx: bool):
    """
    显示配置信息
    
    Args:
        server: 只显示服务器配置
        app: 只显示应用配置
        nginx: 只显示Nginx配置
    """
    command_handler = ctx.obj['command_handler']
    config = command_handler.handle_get_config(server_only=server, app_only=app, nginx_only=nginx)
    
    for section, section_config in config.items():
        for key, value in section_config.items():
            click.echo(f'{section}.{key} = {value}')


@cli.command()
@click.pass_context
def reset_config(ctx):
    """
    重置配置为默认值
    """
    command_handler = ctx.obj['command_handler']
    success, message = command_handler.handle_reset_config()
    if success:
        click.echo(message)
    else:
        click.echo(message, err=True)


@cli.command()
@click.pass_context
@click.argument('port', type=int)
def port(ctx, port: int):
    """
    更新服务器端口
    
    Args:
        port: 新的端口号
    """
    command_handler = ctx.obj['command_handler']
    success, message = command_handler.handle_update_server_port(port)
    if success:
        click.echo(message)
    else:
        click.echo(message, err=True)


@cli.command()
@click.pass_context
@click.argument('host')
def host(ctx, host: str):
    """
    更新服务器地址
    
    Args:
        host: 新的服务器地址
    """
    command_handler = ctx.obj['command_handler']
    success, message = command_handler.handle_update_server_host(host)
    if success:
        click.echo(message)
    else:
        click.echo(message, err=True)


@cli.command()
@click.pass_context
@click.argument('log_level')
def log_level(ctx, log_level: str):
    """
    更新日志级别
    
    Args:
        log_level: 新的日志级别，可选值: debug, info, warning, error, critical
    """
    command_handler = ctx.obj['command_handler']
    success, message = command_handler.handle_update_server_log_level(log_level)
    if success:
        click.echo(message)
    else:
        click.echo(message, err=True)


@cli.command()
@click.pass_context
def validate(ctx):
    """
    验证配置文件
    """
    command_handler = ctx.obj['command_handler']
    is_valid, errors = command_handler.handle_validate_config()
    
    if is_valid:
        click.echo('配置文件验证通过')
    else:
        click.echo('配置文件验证失败', err=True)
        for error in errors:
            click.echo(f'  - {error}', err=True)


# Nginx命令组
@cli.group()
def nginx():
    """
    Nginx服务器管理命令
    """
    pass


@nginx.command()
@click.pass_context
def show(ctx):
    """
    显示Nginx配置信息
    """
    command_handler = ctx.obj['command_handler']
    nginx_config = command_handler.handle_get_nginx_config()
    
    for key, value in nginx_config['nginx'].items():
        click.echo(f'nginx.{key} = {value}')


@nginx.command()
@click.pass_context
@click.argument('key')
@click.argument('value')
def update(ctx, key: str, value: str):
    """
    更新Nginx配置项
    
    Args:
        key: 配置键名，如 'listen_port' 或 'server_name'
        value: 新的配置值
    """
    command_handler = ctx.obj['command_handler']
    success, message = command_handler.handle_update_nginx_config(key, value)
    if success:
        click.echo(message)
    else:
        click.echo(message, err=True)


@nginx.command()
@click.pass_context
@click.argument('port', type=int)
def port(ctx, port: int):
    """
    更新Nginx监听端口
    
    Args:
        port: 新的端口号
    """
    command_handler = ctx.obj['command_handler']
    success, message = command_handler.handle_update_nginx_port(port)
    if success:
        click.echo(message)
    else:
        click.echo(message, err=True)


@nginx.command()
@click.pass_context
@click.argument('server_name')
def server_name(ctx, server_name: str):
    """
    更新Nginx服务器名称
    
    Args:
        server_name: 新的服务器名称
    """
    command_handler = ctx.obj['command_handler']
    success, message = command_handler.handle_update_nginx_server_name(server_name)
    if success:
        click.echo(message)
    else:
        click.echo(message, err=True)


@nginx.command()
@click.pass_context
@click.argument('host')
@click.argument('port', type=int)
def proxy(ctx, host: str, port: int):
    """
    更新Nginx API代理配置
    
    Args:
        host: API主机地址
        port: API端口号
    """
    command_handler = ctx.obj['command_handler']
    success, message = command_handler.handle_update_nginx_api_proxy(host, port)
    if success:
        click.echo(message)
    else:
        click.echo(message, err=True)


@nginx.command()
@click.pass_context
@click.argument('enabled', type=bool)
def toggle(ctx, enabled: bool):
    """
    启用/禁用Nginx
    
    Args:
        enabled: 是否启用Nginx (true/false)
    """
    command_handler = ctx.obj['command_handler']
    success, message = command_handler.handle_toggle_nginx(enabled)
    if success:
        click.echo(message)
    else:
        click.echo(message, err=True)


@nginx.command()
@click.pass_context
def generate(ctx):
    """
    生成Nginx配置文件
    """
    command_handler = ctx.obj['command_handler']
    success, message = command_handler.handle_generate_nginx_config()
    if success:
        click.echo(message)
    else:
        click.echo(message, err=True)


if __name__ == '__main__':
    cli()