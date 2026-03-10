"""CLI入口 - 使用Click框架"""

import click

from shared.config import get_config


@click.group()
@click.version_option(version="0.1.0", prog_name="work-journal")
def cli():
    """工作日志追踪工具 - 自动记录工作活动，生成工作摘要"""
    # 加载配置
    get_config().load()


@cli.command()
@click.option("--path", "-p", default=".", help="要追踪的项目路径")
def start(path):
    """开始追踪工作活动"""
    from cli.commands.start import run_start
    run_start(path)


@cli.command()
@click.option("--summary", "-s", is_flag=True, help="停止前生成摘要")
@click.option("--project", "-p", "project_name", default=None, help="指定停止的项目名称")
def stop(summary, project_name):
    """停止追踪"""
    from cli.commands.stop import run_stop
    run_stop(generate_summary=summary, project_name=project_name)


@cli.command()
def status():
    """查看当前追踪状态"""
    from cli.commands.status import run_status
    run_status()


@cli.command()
@click.option("--last-hour", is_flag=True, help="最近一小时的摘要")
@click.option("--today", is_flag=True, help="今日摘要")
@click.option("--from-time", type=str, help="起始时间 (YYYY-MM-DD HH:MM)")
@click.option("--to-time", type=str, help="结束时间 (YYYY-MM-DD HH:MM)")
def summary(last_hour, today, from_time, to_time):
    """生成工作摘要"""
    from cli.commands.summary import run_summary
    run_summary(last_hour=last_hour, today=today, from_time=from_time, to_time=to_time)


@cli.group()
def config():
    """配置管理"""
    pass


@config.command(name="init")
def config_init():
    """初始化配置文件"""
    from cli.commands.config import run_config_init
    run_config_init()


@config.command(name="show")
def config_show():
    """显示当前配置"""
    from cli.commands.config import run_config_show
    run_config_show()


@config.command(name="setup")
def config_setup():
    """交互式配置向导"""
    from cli.commands.config import run_config_setup
    run_config_setup()


@config.command(name="web")
@click.option("--host", default=None, help="Web服务地址")
@click.option("--port", default=None, type=int, help="Web服务端口")
def config_web(host, port):
    """启动Web配置面板"""
    from cli.commands.config import run_config_web
    run_config_web(host=host, port=port)


# === 项目管理命令组 ===

@cli.group()
def project():
    """项目管理"""
    pass


@project.command(name="add")
@click.argument("name")
@click.argument("path")
@click.option("--desc", "-d", default=None, help="项目描述")
def project_add(name, path, desc):
    """添加项目"""
    from cli.commands.project import run_project_add
    run_project_add(name, path, description=desc)


@project.command(name="list")
def project_list():
    """列出所有项目"""
    from cli.commands.project import run_project_list
    run_project_list()


@project.command(name="remove")
@click.argument("name")
def project_remove(name):
    """移除项目"""
    from cli.commands.project import run_project_remove
    run_project_remove(name)


if __name__ == "__main__":
    cli()
