"""CLI config命令 - 配置管理"""

import os

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
    os.chmod(config_path, 0o600)

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
