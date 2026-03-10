"""CLI stop命令 - 停止追踪"""

import os
import signal

from rich.console import Console

from shared.utils import get_all_daemon_pids, get_daemon_pid, remove_daemon_pid

console = Console()


def _stop_by_project_id(project_id: int, pid: int, generate_summary: bool = False):
    """停止指定项目的追踪器"""
    try:
        os.kill(pid, signal.SIGTERM)
        console.print(f"[green]追踪器已停止: project_id={project_id}, PID={pid}[/green]")

        if generate_summary:
            console.print("[blue]正在生成摘要...[/blue]")
            from cli.commands.summary import run_summary
            run_summary(last_session=True)

    except ProcessLookupError:
        console.print(f"[yellow]进程不存在 (PID: {pid})，清理PID文件[/yellow]")
        remove_daemon_pid(project_id)
    except PermissionError:
        console.print("[red]没有权限停止进程[/red]")
    except Exception as e:
        console.print(f"[red]停止失败: {e}[/red]")


def run_stop(generate_summary: bool = False, project_name: str | None = None):
    """停止工作追踪"""
    if project_name:
        # 按项目名称停止
        try:
            from backend.database import get_db_session, init_database
            from backend.models.project import Project

            init_database()
            with get_db_session() as session:
                project = session.query(Project).filter(Project.name == project_name).first()
                if not project:
                    console.print(f"[yellow]项目不存在: {project_name}[/yellow]")
                    return

                pid = get_daemon_pid(project.id)
                if not pid:
                    console.print(f"[yellow]项目 {project_name} 的追踪器未运行[/yellow]")
                    return

                _stop_by_project_id(project.id, pid, generate_summary)
        except Exception as e:
            console.print(f"[red]停止失败: {e}[/red]")
        return

    # 停止所有项目的追踪器
    all_pids = get_all_daemon_pids()

    # 也检查旧的单一PID文件（向后兼容）
    old_pid = get_daemon_pid(None)

    if not all_pids and not old_pid:
        console.print("[yellow]追踪器未运行[/yellow]")
        return

    if old_pid:
        try:
            os.kill(old_pid, signal.SIGTERM)
            console.print(f"[green]追踪器已停止 (PID: {old_pid})[/green]")
        except ProcessLookupError:
            console.print("[yellow]进程不存在，清理PID文件[/yellow]")
            remove_daemon_pid(None)
        except PermissionError:
            console.print("[red]没有权限停止进程[/red]")

    for project_id, pid in all_pids.items():
        _stop_by_project_id(project_id, pid)

    if generate_summary:
        console.print("[blue]正在生成摘要...[/blue]")
        from cli.commands.summary import run_summary
        run_summary(last_session=True)
