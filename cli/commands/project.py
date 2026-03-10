"""CLI project命令 - 项目管理"""

from pathlib import Path

from rich.console import Console
from rich.table import Table

from backend.database import get_db_session, init_database
from backend.models.project import Project

console = Console()


def run_project_add(name: str, path: str, description: str | None = None):
    """添加项目"""
    resolved_path = str(Path(path).resolve())

    try:
        init_database()
    except Exception as e:
        console.print(f"[red]数据库连接失败: {e}[/red]")
        return

    with get_db_session() as session:
        # 检查重复
        existing = session.query(Project).filter(
            (Project.name == name) | (Project.path == resolved_path)
        ).first()
        if existing:
            if existing.name == name:
                console.print(f"[yellow]项目名称已存在: {name}[/yellow]")
            else:
                console.print(f"[yellow]项目路径已存在: {resolved_path}[/yellow]")
            return

        project = Project(name=name, path=resolved_path, description=description)
        session.add(project)
        session.flush()
        console.print(f"[green]项目已添加: {name} (ID: {project.id})[/green]")
        console.print(f"[dim]路径: {resolved_path}[/dim]")


def run_project_list():
    """列出所有项目"""
    try:
        init_database()
    except Exception as e:
        console.print(f"[red]数据库连接失败: {e}[/red]")
        return

    with get_db_session() as session:
        projects = session.query(Project).order_by(Project.created_at.desc()).all()

        if not projects:
            console.print("[yellow]暂无项目[/yellow]")
            return

        table = Table(title="项目列表")
        table.add_column("ID", style="dim")
        table.add_column("名称", style="bold")
        table.add_column("路径")
        table.add_column("状态")
        table.add_column("描述")

        for p in projects:
            status = "[green]活跃[/green]" if p.is_active else "[red]已停用[/red]"
            table.add_row(
                str(p.id),
                p.name,
                p.path,
                status,
                p.description or "",
            )

        console.print(table)


def run_project_remove(name: str):
    """移除项目（软删除）"""
    try:
        init_database()
    except Exception as e:
        console.print(f"[red]数据库连接失败: {e}[/red]")
        return

    with get_db_session() as session:
        project = session.query(Project).filter(Project.name == name).first()
        if not project:
            console.print(f"[yellow]项目不存在: {name}[/yellow]")
            return

        project.is_active = False
        console.print(f"[green]项目已移除: {name}[/green]")
