"""项目管理API"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from backend.database import get_db_session
from backend.models.project import Project
from shared.logging_config import get_logger
from shared.path_map import get_path_map

logger = get_logger(__name__)
router = APIRouter(prefix="/api/projects", tags=["projects"])


class ProjectCreate(BaseModel):
    name: str
    path: str | None = None
    description: str | None = None


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    is_active: bool | None = None


def _project_dict(p, path_map=None) -> dict:
    """将项目对象转为字典，附带本地路径"""
    if path_map is None:
        path_map = get_path_map()
    return {
        "id": p.id,
        "name": p.name,
        "path": path_map.get_path(p.name),
        "description": p.description,
        "is_active": p.is_active,
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
    }


@router.get("")
def list_projects(is_active: Optional[bool] = Query(None)):
    """获取项目列表"""
    logger.info(f"查询项目列表: is_active={is_active}")
    path_map = get_path_map()
    with get_db_session() as session:
        query = session.query(Project)
        if is_active is not None:
            query = query.filter(Project.is_active == is_active)
        projects = query.order_by(Project.created_at.desc()).all()
        logger.info(f"返回 {len(projects)} 个项目")
        return [_project_dict(p, path_map) for p in projects]


@router.post("")
def create_project(data: ProjectCreate):
    """创建项目"""
    logger.info(f"创建项目: name={data.name}")
    with get_db_session() as session:
        # 检查名称重复
        existing = session.query(Project).filter(Project.name == data.name).first()
        if existing:
            logger.warning(f"项目名称已存在: {data.name}")
            raise HTTPException(status_code=400, detail=f"项目名称已存在: {data.name}")

        project = Project(
            name=data.name,
            description=data.description,
        )
        session.add(project)
        session.flush()

        # 如果提供了路径，存到本地映射
        if data.path:
            get_path_map().set_path(data.name, data.path)

        logger.info(f"项目创建成功: id={project.id}, name={project.name}")
        return {
            "id": project.id,
            "name": project.name,
            "path": data.path,
            "message": "项目已创建",
        }


@router.get("/{project_id}")
def get_project(project_id: int):
    """获取项目详情"""
    logger.info(f"查询项目详情: project_id={project_id}")
    with get_db_session() as session:
        project = session.query(Project).get(project_id)
        if not project:
            logger.warning(f"项目不存在: project_id={project_id}")
            raise HTTPException(status_code=404, detail="项目不存在")
        return _project_dict(project)


@router.put("/{project_id}")
def update_project(project_id: int, data: ProjectUpdate):
    """更新项目"""
    logger.info(f"更新项目: project_id={project_id}, data={data.model_dump(exclude_none=True)}")
    with get_db_session() as session:
        project = session.query(Project).get(project_id)
        if not project:
            logger.warning(f"项目不存在: project_id={project_id}")
            raise HTTPException(status_code=404, detail="项目不存在")

        if data.name is not None:
            project.name = data.name
        if data.description is not None:
            project.description = data.description
        if data.is_active is not None:
            project.is_active = data.is_active

        logger.info(f"项目更新成功: project_id={project_id}")
        return {"message": "项目已更新"}


@router.delete("/{project_id}")
def delete_project(project_id: int):
    """软删除项目（设为不活跃）"""
    logger.info(f"删除项目: project_id={project_id}")
    with get_db_session() as session:
        project = session.query(Project).get(project_id)
        if not project:
            logger.warning(f"项目不存在: project_id={project_id}")
            raise HTTPException(status_code=404, detail="项目不存在")
        project.is_active = False
        get_path_map().remove_path(project.name)
        logger.info(f"项目已标记为不活跃: project_id={project_id}")
        return {"message": "项目已删除"}


@router.put("/{project_id}/path")
def set_project_path(project_id: int, data: dict):
    """设置项目的本机路径"""
    path = data.get("path", "").strip()
    logger.info(f"设置项目本机路径: project_id={project_id}, path={path}")
    with get_db_session() as session:
        project = session.query(Project).get(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="项目不存在")
        if path:
            get_path_map().set_path(project.name, path)
        else:
            get_path_map().remove_path(project.name)
        return {"message": "路径已更新", "path": get_path_map().get_path(project.name)}


@router.get("/tracker-status/all")
def get_tracker_status():
    """获取所有项目的追踪器运行状态"""
    logger.info("查询所有项目的追踪器运行状态")
    from shared.utils import get_all_daemon_pids
    status = get_all_daemon_pids()
    logger.info(f"返回 {len(status)} 个追踪器状态")
    return status
