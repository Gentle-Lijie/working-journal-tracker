"""项目管理API"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from backend.database import get_db_session
from backend.models.project import Project

router = APIRouter(prefix="/api/projects", tags=["projects"])


class ProjectCreate(BaseModel):
    name: str
    path: str
    description: str | None = None


class ProjectUpdate(BaseModel):
    name: str | None = None
    path: str | None = None
    description: str | None = None
    is_active: bool | None = None


@router.get("")
def list_projects(is_active: Optional[bool] = Query(None)):
    """获取项目列表"""
    with get_db_session() as session:
        query = session.query(Project)
        if is_active is not None:
            query = query.filter(Project.is_active == is_active)
        projects = query.order_by(Project.created_at.desc()).all()
        return [
            {
                "id": p.id,
                "name": p.name,
                "path": p.path,
                "description": p.description,
                "is_active": p.is_active,
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "updated_at": p.updated_at.isoformat() if p.updated_at else None,
            }
            for p in projects
        ]


@router.post("")
def create_project(data: ProjectCreate):
    """创建项目"""
    with get_db_session() as session:
        # 检查重复
        existing = session.query(Project).filter(
            (Project.name == data.name) | (Project.path == data.path)
        ).first()
        if existing:
            if existing.name == data.name:
                raise HTTPException(status_code=400, detail=f"项目名称已存在: {data.name}")
            raise HTTPException(status_code=400, detail=f"项目路径已存在: {data.path}")

        project = Project(
            name=data.name,
            path=data.path,
            description=data.description,
        )
        session.add(project)
        session.flush()
        return {
            "id": project.id,
            "name": project.name,
            "path": project.path,
            "message": "项目已创建",
        }


@router.get("/{project_id}")
def get_project(project_id: int):
    """获取项目详情"""
    with get_db_session() as session:
        project = session.query(Project).get(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="项目不存在")
        return {
            "id": project.id,
            "name": project.name,
            "path": project.path,
            "description": project.description,
            "is_active": project.is_active,
            "created_at": project.created_at.isoformat() if project.created_at else None,
            "updated_at": project.updated_at.isoformat() if project.updated_at else None,
        }


@router.put("/{project_id}")
def update_project(project_id: int, data: ProjectUpdate):
    """更新项目"""
    with get_db_session() as session:
        project = session.query(Project).get(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="项目不存在")

        if data.name is not None:
            project.name = data.name
        if data.path is not None:
            project.path = data.path
        if data.description is not None:
            project.description = data.description
        if data.is_active is not None:
            project.is_active = data.is_active

        return {"message": "项目已更新"}


@router.delete("/{project_id}")
def delete_project(project_id: int):
    """软删除项目（设为不活跃）"""
    with get_db_session() as session:
        project = session.query(Project).get(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="项目不存在")
        project.is_active = False
        return {"message": "项目已删除"}


@router.get("/by-path/{path:path}")
def get_project_by_path(path: str):
    """根据路径查找项目"""
    with get_db_session() as session:
        project = session.query(Project).filter(Project.path == path).first()
        if not project:
            raise HTTPException(status_code=404, detail="项目不存在")
        return {
            "id": project.id,
            "name": project.name,
            "path": project.path,
            "is_active": project.is_active,
        }


@router.get("/tracker-status/all")
def get_tracker_status():
    """获取所有项目的追踪器运行状态"""
    from shared.utils import get_all_daemon_pids
    return get_all_daemon_pids()
