"""CLI start命令 - 开始追踪"""

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from rich.console import Console

from backend.database import get_db_session, init_database
from backend.models.project import Project
from backend.models.work_session import WorkSession
from shared.constants import SESSION_STATUS_ACTIVE
from shared.path_map import get_path_map
from shared.platform_compat import detach_process_args
from shared.utils import get_app_dir, get_daemon_pid

console = Console()


def _get_or_create_project(path: str) -> int | None:
    """根据路径查找或创建项目，返回project_id"""
    path_map = get_path_map()
    repo_path = str(Path(path).resolve())

    with get_db_session() as session:
        # 通过本地路径映射反查项目名
        project_name = path_map.get_name_by_path(repo_path)
        if project_name:
            project = session.query(Project).filter(Project.name == project_name).first()
            if project:
                if not project.is_active:
                    project.is_active = True
                console.print(f"[blue]项目: {project.name} (ID: {project.id})[/blue]")
                return project.id

        # 自动创建项目，使用目录名作为项目名
        name = Path(repo_path).name
        # 避免名称冲突
        existing = session.query(Project).filter(Project.name == name).first()
        if existing:
            name = f"{name}-{Path(repo_path).parent.name}"

        project = Project(name=name)
        session.add(project)
        session.flush()
        # 路径存本地
        path_map.set_path(name, repo_path)
        console.print(f"[green]自动创建项目: {name} (ID: {project.id})[/green]")
        return project.id


def run_start(path: str):
    """启动工作追踪"""
    repo_path = str(Path(path).resolve())
    console.print(f"[blue]项目路径: {repo_path}[/blue]")

    # 初始化数据库
    try:
        init_database()
    except Exception as e:
        console.print(f"[red]数据库连接失败: {e}[/red]")
        console.print("[dim]请检查配置文件: ~/.work-journal/config.yaml[/dim]")
        return

    # 获取或创建项目
    project_id = _get_or_create_project(repo_path)

    # 检查该项目是否已有运行的守护进程
    if project_id is not None:
        pid = get_daemon_pid(project_id)
        if pid:
            console.print(f"[yellow]该项目的追踪器已在运行中 (PID: {pid})[/yellow]")
            return

    # 创建新的工作会话
    try:
        with get_db_session() as session:
            work_session = WorkSession(
                start_time=datetime.now(),
                status=SESSION_STATUS_ACTIVE,
                project_id=project_id,
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
daemon = TrackerDaemon(session_id={session_id}, repo_path='{repo_path}', project_id={project_id})
daemon.start()
""",
            ],
            env=env,
            **detach_process_args(),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        console.print(f"[green]追踪器已启动 (PID: {process.pid})[/green]")
        console.print("[dim]追踪内容: Git提交、文件变更[/dim]")
        console.print(f"[dim]日志文件: {get_app_dir() / 'work-journal.log'}[/dim]")

    except Exception as e:
        console.print(f"[red]启动守护进程失败: {e}[/red]")
