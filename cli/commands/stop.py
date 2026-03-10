"""CLI stop命令 - 停止追踪"""

import os
import signal

from rich.console import Console

from tracker.daemon import get_daemon_pid

console = Console()


def run_stop(generate_summary: bool = False):
    """停止工作追踪"""
    pid = get_daemon_pid()

    if not pid:
        console.print("[yellow]追踪器未运行[/yellow]")
        return

    try:
        # 发送SIGTERM信号
        os.kill(pid, signal.SIGTERM)
        console.print(f"[green]追踪器已停止 (PID: {pid})[/green]")

        if generate_summary:
            console.print("[blue]正在生成摘要...[/blue]")
            from cli.commands.summary import run_summary

            run_summary(last_session=True)

    except ProcessLookupError:
        console.print("[yellow]进程不存在，清理PID文件[/yellow]")
        from shared.constants import PID_FILE
        from shared.utils import get_app_dir

        pid_path = get_app_dir() / PID_FILE
        pid_path.unlink(missing_ok=True)
    except PermissionError:
        console.print("[red]没有权限停止进程[/red]")
    except Exception as e:
        console.print(f"[red]停止失败: {e}[/red]")
