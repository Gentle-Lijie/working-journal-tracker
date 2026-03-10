"""CLI status命令 - 查看追踪状态"""

from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from shared.utils import format_datetime, format_duration
from tracker.daemon import get_daemon_pid

console = Console()


def run_status():
    """显示当前追踪状态"""
    pid = get_daemon_pid()

    # 基本状态
    if pid:
        console.print(Panel(f"[green]运行中[/green] (PID: {pid})", title="追踪器状态"))
    else:
        console.print(Panel("[red]未运行[/red]", title="追踪器状态"))
        return

    # 查询数据库获取详细信息
    try:
        from backend.database import get_db_session, init_database
        from backend.models.activity import Activity
        from backend.models.work_session import WorkSession
        from shared.constants import SESSION_STATUS_ACTIVE

        init_database()

        with get_db_session() as session:
            # 获取当前活跃会话
            active_session = (
                session.query(WorkSession)
                .filter(WorkSession.status == SESSION_STATUS_ACTIVE)
                .order_by(WorkSession.start_time.desc())
                .first()
            )

            if active_session:
                duration = (datetime.now() - active_session.start_time).total_seconds()

                # 会话信息
                info_table = Table(show_header=False, box=None)
                info_table.add_column("Key", style="bold")
                info_table.add_column("Value")
                info_table.add_row("会话ID", f"#{active_session.id}")
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

                console.print(Panel(info_table, title="当前会话"))

                # 最近活动
                recent_activities = (
                    session.query(Activity)
                    .filter(Activity.session_id == active_session.id)
                    .order_by(Activity.timestamp.desc())
                    .limit(5)
                    .all()
                )

                if recent_activities:
                    act_table = Table(title="最近活动")
                    act_table.add_column("时间", style="dim")
                    act_table.add_column("类型")
                    act_table.add_column("描述")

                    for act in recent_activities:
                        act_table.add_row(
                            format_datetime(act.timestamp),
                            act.activity_type,
                            (act.description or "")[:60],
                        )

                    console.print(act_table)
            else:
                console.print("[yellow]没有活跃的工作会话[/yellow]")

    except Exception as e:
        console.print(f"[red]查询数据库失败: {e}[/red]")
