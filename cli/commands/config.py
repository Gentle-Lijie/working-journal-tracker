"""CLI config命令 - 配置管理"""

import os

import click
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from shared.config import get_config
from shared.constants import CONFIG_FILE
from shared.utils import get_app_dir

console = Console()


def run_config_init():
    """初始化配置文件"""
    config_path = get_app_dir() / CONFIG_FILE

    if config_path.exists():
        console.print(f"[yellow]配置文件已存在: {config_path}[/yellow]")
        return

    config = get_config()
    config.save()
    from shared.platform_compat import secure_chmod

    secure_chmod(config_path)

    console.print(f"[green]配置文件已创建: {config_path}[/green]")
    console.print("[dim]请编辑配置文件，设置数据库连接信息[/dim]")


def run_config_show():
    """显示当前配置"""
    config = get_config()
    config.load()

    config_dict = config.to_dict()

    # 隐藏敏感信息
    if "database" in config_dict and "password" in config_dict["database"]:
        config_dict["database"]["password"] = "***"

    import yaml

    config_yaml = yaml.dump(config_dict, default_flow_style=False, allow_unicode=True)
    syntax = Syntax(config_yaml, "yaml", theme="monokai", line_numbers=False)

    console.print(Panel(syntax, title="当前配置"))


def run_config_setup():
    """交互式配置向导"""
    config = get_config()
    config.load()
    cfg = config.to_dict()

    console.print(Panel("工作日志追踪工具 - 交互式配置向导", style="bold green"))

    # 数据库配置
    console.print("\n[bold cyan]== 数据库配置 ==[/bold cyan]")
    db = cfg["database"]
    db["host"] = click.prompt("数据库主机", default=db.get("host", "localhost"))
    db["port"] = click.prompt("数据库端口", default=db.get("port", 3307), type=int)
    db["user"] = click.prompt("数据库用户", default=db.get("user", "work_journal"))
    db["password"] = click.prompt("数据库密码", default=db.get("password", ""), hide_input=True, show_default=False)
    db["database"] = click.prompt("数据库名称", default=db.get("database", "work_journal"))

    # SSH 隧道配置
    console.print("\n[bold cyan]== SSH 隧道配置 ==[/bold cyan]")
    ssh = cfg["ssh"]
    ssh["enabled"] = click.confirm("启用SSH隧道", default=ssh.get("enabled", False))
    if ssh["enabled"]:
        ssh["host"] = click.prompt("SSH主机", default=ssh.get("host", ""))
        ssh["port"] = click.prompt("SSH端口", default=ssh.get("port", 22), type=int)
        ssh["username"] = click.prompt("SSH用户名", default=ssh.get("username", ""))
        ssh["auth_type"] = click.prompt(
            "认证方式 (key/password)", default=ssh.get("auth_type", "key"),
            type=click.Choice(["key", "password"], case_sensitive=False),
        )
        if ssh["auth_type"] == "key":
            ssh["key_path"] = click.prompt("密钥路径", default=ssh.get("key_path", "~/.ssh/id_rsa"))
        else:
            ssh["password"] = click.prompt("SSH密码", default="", hide_input=True, show_default=False)
        ssh["remote_host"] = click.prompt("远程数据库主机", default=ssh.get("remote_host", "127.0.0.1"))
        ssh["remote_port"] = click.prompt("远程数据库端口", default=ssh.get("remote_port", 3306), type=int)

    # 追踪器配置
    console.print("\n[bold cyan]== 追踪器配置 ==[/bold cyan]")
    tracker = cfg["tracker"]
    tracker["git_check_interval"] = click.prompt("Git检查间隔(秒)", default=tracker.get("git_check_interval", 30), type=int)
    tracker["file_batch_size"] = click.prompt("文件批量大小", default=tracker.get("file_batch_size", 10), type=int)
    tracker["file_batch_interval"] = click.prompt("文件批量间隔(秒)", default=tracker.get("file_batch_interval", 300), type=int)
    watch_paths_str = click.prompt(
        "监控路径(逗号分隔)", default=",".join(tracker.get("watch_paths", ["."]))
    )
    tracker["watch_paths"] = [p.strip() for p in watch_paths_str.split(",") if p.strip()]

    # AI 配置
    console.print("\n[bold cyan]== AI 服务配置 ==[/bold cyan]")
    ai = cfg["ai"]
    ai["default_config"] = click.prompt("默认AI配置名称", default=ai.get("default_config", "default"))
    ai["retry_attempts"] = click.prompt("重试次数", default=ai.get("retry_attempts", 3), type=int)
    ai["timeout"] = click.prompt("超时时间(秒)", default=ai.get("timeout", 30), type=int)

    # Web 配置
    console.print("\n[bold cyan]== Web 服务配置 ==[/bold cyan]")
    web = cfg["web"]
    web["host"] = click.prompt("Web服务地址", default=web.get("host", "127.0.0.1"))
    web["port"] = click.prompt("Web服务端口", default=web.get("port", 8000), type=int)

    # 保存
    config._config = cfg
    config.save()
    config_path = get_app_dir() / CONFIG_FILE
    console.print(f"\n[green]配置已保存到: {config_path}[/green]")


def run_config_web(host: str | None = None, port: int | None = None):
    """启动Web配置面板"""
    import uvicorn

    from backend.main import app
    from shared.config import get_config

    config = get_config()
    web_config = config.web

    host = host or web_config.get("host", "127.0.0.1")
    port = port or web_config.get("port", 8000)

    console.print(f"[green]启动Web配置面板: http://{host}:{port}[/green]")
    console.print("[dim]按 Ctrl+C 停止服务[/dim]")

    try:
        uvicorn.run(app, host=host, port=port, log_level="info")
    except KeyboardInterrupt:
        console.print("\n[yellow]服务已停止[/yellow]")
