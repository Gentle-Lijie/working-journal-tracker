"""CLI status命令 - 查看追踪状态"""

from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from shared.path_map import get_path_map
from shared.utils import format_datetime, format_duration, get_all_daemon_pids, get_daemon_pid

console = Console()


def run_status():
    """显示当前追踪状态"""
    # 收集所有运行中的守护进程
    all_pids = get_all_daemon_pids()
    old_pid = get_daemon_pid(None)

    if not all_pids and not old_pid:
        console.print(Panel("[red]未运行[/red]", title="追踪器状态"))
        return

    # 显示运行中的追踪器
    if old_pid:
        console.print(Panel(f"[green]运行中[/green] (PID: {old_pid}) [dim]（旧版单项目模式）[/dim]", title="追踪器状态"))

    if all_pids:
        pid_table = Table(title="运行中的追踪器")
        pid_table.add_column("项目ID", style="dim")
        pid_table.add_column("PID")
        pid_table.add_column("项目名称")
        pid_table.add_column("路径")

        # 查询项目信息
        try:
            from backend.database import get_db_session, init_database
            from backend.models.project import Project

            init_database()
            path_map = get_path_map()
            with get_db_session() as session:
                for project_id, pid in all_pids.items():
                    project = session.query(Project).get(project_id)
                    name = project.name if project else "未知"
                    path = path_map.get_path(name) if project else "未知"
                    pid_table.add_row(str(project_id), str(pid), name, path or "（本机未配置）")
        except Exception:
            for project_id, pid in all_pids.items():
                pid_table.add_row(str(project_id), str(pid), "-", "-")

        console.print(pid_table)

    # 查询数据库获取详细信息
    try:
        from backend.database import get_db_session, init_database
        from backend.models.activity import Activity
        from backend.models.work_session import WorkSession
        from shared.constants import SESSION_STATUS_ACTIVE

        init_database()

        with get_db_session() as session:
            # 获取所有活跃会话
            active_sessions = (
                session.query(WorkSession)
                .filter(WorkSession.status == SESSION_STATUS_ACTIVE)
                .order_by(WorkSession.start_time.desc())
                .all()
            )

            if not active_sessions:
                console.print("[yellow]没有活跃的工作会话[/yellow]")
                return

            for active_session in active_sessions:
                duration = (datetime.now() - active_session.start_time).total_seconds()

                info_table = Table(show_header=False, box=None)
                info_table.add_column("Key", style="bold")
                info_table.add_column("Value")
                info_table.add_row("会话ID", f"#{active_session.id}")
                if active_session.project_id:
                    info_table.add_row("项目ID", str(active_session.project_id))
                info_table.add_row("开始时间", format_datetime(active_session.start_time))
                info_table.add_row("已运行", format_duration(duration))

                # 活动统计
                activity_count = (
                    session.query(Activity)
                    .filter(Activity.session_id == active_session.id)
                    .count()
                )
                git_count = (
                    session.query(Activity)
                    .filter(
                        Activity.session_id == active_session.id,
                        Activity.activity_type == "git_commit",
                    )
                    .count()
                )
                file_count = activity_count - git_count

                info_table.add_row("活动总数", str(activity_count))
                info_table.add_row("Git提交", str(git_count))
                info_table.add_row("文件变更", str(file_count))

                title = f"会话 #{active_session.id}"
                if active_session.project_id:
                    from backend.models.project import Project
                    project = session.query(Project).get(active_session.project_id)
                    if project:
                        title = f"项目: {project.name} (会话 #{active_session.id})"

                console.print(Panel(info_table, title=title))

    except Exception as e:
        console.print(f"[red]查询数据库失败: {e}[/red]")
