"""CLI project命令 - 项目管理"""

from pathlib import Path

from rich.console import Console
from rich.table import Table

from backend.database import get_db_session, init_database
from backend.models.project import Project
from shared.path_map import get_path_map

console = Console()


def run_project_add(name: str, path: str, description: str | None = None):
    """添加项目"""
    resolved_path = str(Path(path).resolve())

    try:
        init_database()
    except Exception as e:
        console.print(f"[red]数据库连接失败: {e}[/red]")
        return

    path_map = get_path_map()

    with get_db_session() as session:
        # 检查名称重复
        existing = session.query(Project).filter(Project.name == name).first()
        if existing:
            console.print(f"[yellow]项目名称已存在: {name}[/yellow]")
            return

        # 检查本地路径是否已被其他项目使用
        existing_name = path_map.get_name_by_path(resolved_path)
        if existing_name:
            console.print(f"[yellow]该路径已关联到项目: {existing_name}[/yellow]")
            return

        project = Project(name=name, description=description)
        session.add(project)
        session.flush()
        # 路径存本地
        path_map.set_path(name, resolved_path)
        console.print(f"[green]项目已添加: {name} (ID: {project.id})[/green]")
        console.print(f"[dim]路径: {resolved_path}[/dim]")


def run_project_list():
    """列出所有项目"""
    try:
        init_database()
    except Exception as e:
        console.print(f"[red]数据库连接失败: {e}[/red]")
        return

    path_map = get_path_map()

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
            local_path = path_map.get_path(p.name) or "（本机未配置）"
            table.add_row(
                str(p.id),
                p.name,
                local_path,
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
        # 同时清理本地路径映射
        get_path_map().remove_path(name)
        console.print(f"[green]项目已移除: {name}[/green]")
