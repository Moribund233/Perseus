"""
LanGit CLI客户端 - Click命令行界面

提供命令参数型CLI，用于管理FastAPI服务的生命周期。
"""
import click
from typing import Optional
from client.controller.service_controller import get_service_controller, ServiceState
from client.utils.config_manager import get_client_config_manager


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
    controller = ctx.obj['controller']
    if controller.start(block=block, timeout=timeout):
        click.echo('服务启动成功')
    else:
        click.echo('服务启动失败', err=True)


@cli.command()
@click.pass_context
@click.option('--timeout', '-t', default=10, help='停止超时时间（秒）')
def stop(ctx, timeout: int):
    """
    停止FastAPI服务
    
    Args:
        timeout: 停止超时时间（秒）
    """
    controller = ctx.obj['controller']
    if controller.stop(timeout=timeout):
        click.echo('服务停止成功')
    else:
        click.echo('服务停止失败', err=True)


@cli.command()
@click.pass_context
@click.option('--timeout', '-t', default=10, help='重启超时时间（秒）')
def restart(ctx, timeout: int):
    """
    重启FastAPI服务
    
    Args:
        timeout: 重启超时时间（秒）
    """
    controller = ctx.obj['controller']
    if controller.restart(timeout=timeout):
        click.echo('服务重启成功')
    else:
        click.echo('服务重启失败', err=True)


@cli.command()
@click.pass_context
def status(ctx):
    """
    查看服务状态
    """
    controller = ctx.obj['controller']
    state = controller.get_state()
    click.echo(f'服务状态: {state.value}')
    
    if controller.is_running():
        port = controller.get_config_value('server.port')
        host = controller.get_config_value('server.host')
        click.echo(f'服务地址: http://{host}:{port}')


@cli.command()
@click.pass_context
@click.option('--lines', '-n', default=100, help='显示日志行数')
def logs(ctx, lines: int):
    """
    查看服务日志
    
    Args:
        lines: 显示日志行数
    """
    controller = ctx.obj['controller']
    logs = controller.get_logs(lines=lines)
    for line in logs:
        click.echo(line)


@cli.command()
@click.pass_context
def clear_logs(ctx):
    """
    清除服务日志
    """
    controller = ctx.obj['controller']
    controller.clear_logs()
    click.echo('日志已清除')


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
    controller = ctx.obj['controller']
    if controller.update_config(key, value):
        click.echo(f'配置已更新: {key} = {value}')
    else:
        click.echo('配置更新失败', err=True)


@cli.command()
@click.pass_context
@click.option('--server', '-s', is_flag=True, help='只显示服务器配置')
@click.option('--app', '-a', is_flag=True, help='只显示应用配置')
def show_config(ctx, server: bool, app: bool):
    """
    显示配置信息
    
    Args:
        server: 只显示服务器配置
        app: 只显示应用配置
    """
    config_manager = ctx.obj['config_manager']
    config = config_manager.load_config()
    
    if server:
        server_config = config_manager.get_server_config()
        for key, value in server_config.items():
            click.echo(f'server.{key} = {value}')
    elif app:
        app_config = config_manager.get_app_config()
        for key, value in app_config.items():
            click.echo(f'app.{key} = {value}')
    else:
        for section, section_config in config.items():
            for key, value in section_config.items():
                click.echo(f'{section}.{key} = {value}')


@cli.command()
@click.pass_context
def reset_config(ctx):
    """
    重置配置为默认值
    """
    config_manager = ctx.obj['config_manager']
    if config_manager.reset_to_defaults():
        click.echo('配置已重置为默认值')
    else:
        click.echo('配置重置失败', err=True)


@cli.command()
@click.pass_context
@click.argument('port', type=int)
def port(ctx, port: int):
    """
    更新服务器端口
    
    Args:
        port: 新的端口号
    """
    config_manager = ctx.obj['config_manager']
    if config_manager.update_server_port(port):
        click.echo(f'服务器端口已更新为: {port}')
    else:
        click.echo('服务器端口更新失败', err=True)


@cli.command()
@click.pass_context
@click.argument('host')
def host(ctx, host: str):
    """
    更新服务器地址
    
    Args:
        host: 新的服务器地址
    """
    config_manager = ctx.obj['config_manager']
    if config_manager.update_server_host(host):
        click.echo(f'服务器地址已更新为: {host}')
    else:
        click.echo('服务器地址更新失败', err=True)


@cli.command()
@click.pass_context
@click.argument('log_level')
def log_level(ctx, log_level: str):
    """
    更新日志级别
    
    Args:
        log_level: 新的日志级别，可选值: debug, info, warning, error, critical
    """
    config_manager = ctx.obj['config_manager']
    if config_manager.update_server_log_level(log_level):
        click.echo(f'日志级别已更新为: {log_level}')
    else:
        click.echo('日志级别更新失败', err=True)


@cli.command()
@click.pass_context
def validate(ctx):
    """
    验证配置文件
    """
    config_manager = ctx.obj['config_manager']
    is_valid, errors = config_manager.validate_config()
    
    if is_valid:
        click.echo('配置文件验证通过')
    else:
        click.echo('配置文件验证失败', err=True)
        for error in errors:
            click.echo(f'  - {error}', err=True)


if __name__ == '__main__':
    cli()