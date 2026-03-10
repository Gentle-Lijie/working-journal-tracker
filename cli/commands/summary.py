"""CLI summary命令 - 生成工作摘要"""

from datetime import datetime, timedelta

from rich.console import Console
from rich.panel import Panel

from shared.utils import format_datetime

console = Console()


def run_summary(
    last_hour: bool = False,
    today: bool = False,
    from_time: str | None = None,
    to_time: str | None = None,
    last_session: bool = False,
):
    """生成工作摘要"""
    now = datetime.now()

    # 确定时间范围
    if last_hour:
        start = now - timedelta(hours=1)
        end = now
    elif today:
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = now
    elif from_time:
        start = datetime.strptime(from_time, "%Y-%m-%d %H:%M")
        end = datetime.strptime(to_time, "%Y-%m-%d %H:%M") if to_time else now
    else:
        # 默认最近一小时
        start = now - timedelta(hours=1)
        end = now

    console.print(f"[blue]时间范围: {format_datetime(start)} ~ {format_datetime(end)}[/blue]")

    try:
        from backend.database import get_db_session, init_database
        from backend.models.activity import Activity

        init_database()

        with get_db_session() as session:
            # 查询活动记录
            activities = (
                session.query(Activity)
                .filter(Activity.timestamp >= start, Activity.timestamp <= end)
                .order_by(Activity.timestamp)
                .all()
            )

            if not activities:
                console.print("[yellow]该时间段没有活动记录[/yellow]")
                return

            console.print(f"[green]找到 {len(activities)} 条活动记录[/green]")

            # 尝试调用AI生成摘要
            try:
                from backend.services.ai_service import get_ai_service

                ai_service = get_ai_service()

                # 构建活动描述
                activity_descriptions = []
                for act in activities:
                    activity_descriptions.append(
                        f"[{format_datetime(act.timestamp)}] {act.activity_type}: {act.description}"
                    )

                console.print("[blue]正在使用AI生成摘要...[/blue]")
                result = ai_service.generate_summary(
                    activities=activity_descriptions,
                    start_time=start,
                    end_time=end,
                )

                if result:
                    console.print(
                        Panel(
                            result["summary"],
                            title=f"工作摘要 - {result.get('work_type', '其他')}",
                            subtitle=f"模型: {result.get('model', 'unknown')}",
                        )
                    )
                else:
                    _print_basic_summary(activities)

            except Exception as e:
                console.print(f"[yellow]AI摘要生成失败: {e}，显示基本摘要[/yellow]")
                _print_basic_summary(activities)

    except Exception as e:
        console.print(f"[red]生成摘要失败: {e}[/red]")


def _print_basic_summary(activities):
    """打印基本摘要（无AI）"""
    git_commits = [a for a in activities if a.activity_type == "git_commit"]
    file_changes = [a for a in activities if a.activity_type != "git_commit"]

    lines = []
    if git_commits:
        lines.append(f"Git提交 ({len(git_commits)}):")
        for c in git_commits:
            lines.append(f"  - {c.description}")

    if file_changes:
        lines.append(f"\n文件变更 ({len(file_changes)}):")
        for f in file_changes[:20]:
            lines.append(f"  - {f.description}")
        if len(file_changes) > 20:
            lines.append(f"  ... 还有 {len(file_changes) - 20} 条")

    console.print(Panel("\n".join(lines), title="基本摘要"))
