"""CLI start命令 - 开始追踪"""

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from rich.console import Console

from backend.database import get_db_session, init_database
from backend.models.work_session import WorkSession
from shared.constants import SESSION_STATUS_ACTIVE
from shared.utils import get_app_dir
from tracker.daemon import get_daemon_pid

console = Console()


def run_start(path: str):
    """启动工作追踪"""
    # 检查是否已有运行的守护进程
    pid = get_daemon_pid()
    if pid:
        console.print(f"[yellow]追踪器已在运行中 (PID: {pid})[/yellow]")
        return

    repo_path = str(Path(path).resolve())
    console.print(f"[blue]项目路径: {repo_path}[/blue]")

    # 初始化数据库
    try:
        init_database()
    except Exception as e:
        console.print(f"[red]数据库连接失败: {e}[/red]")
        console.print("[dim]请检查配置文件: ~/.work-journal/config.yaml[/dim]")
        return

    # 创建新的工作会话
    try:
        with get_db_session() as session:
            work_session = WorkSession(
                start_time=datetime.now(),
                status=SESSION_STATUS_ACTIVE,
            )
            session.add(work_session)
            session.flush()
            session_id = work_session.id

        console.print(f"[green]工作会话已创建: #{session_id}[/green]")
    except Exception as e:
        console.print(f"[red]创建会话失败: {e}[/red]")
        return

    # 启动守护进程
    try:
        daemon_script = Path(__file__).parent.parent.parent / "tracker" / "daemon.py"
        env = os.environ.copy()
        env["PYTHONPATH"] = str(Path(__file__).parent.parent.parent)

        process = subprocess.Popen(
            [
                sys.executable,
                "-c",
                f"""
import sys
sys.path.insert(0, '{Path(__file__).parent.parent.parent}')
from shared.config import get_config
get_config().load()
from backend.database import init_database
init_database()
from tracker.daemon import TrackerDaemon
daemon = TrackerDaemon(session_id={session_id}, repo_path='{repo_path}')
daemon.start()
""",
            ],
            env=env,
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        console.print(f"[green]追踪器已启动 (PID: {process.pid})[/green]")
        console.print("[dim]追踪内容: Git提交、文件变更[/dim]")
        console.print(f"[dim]日志文件: {get_app_dir() / 'work-journal.log'}[/dim]")

    except Exception as e:
        console.print(f"[red]启动守护进程失败: {e}[/red]")
