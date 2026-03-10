"""文件系统浏览API — 供前端目录选择器使用"""

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Query

from shared.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/filesystem", tags=["filesystem"])


@router.get("/browse")
def browse_directory(path: Optional[str] = Query(None)):
    """浏览目录，返回子目录列表"""
    if not path:
        # 默认返回用户主目录
        target = Path.home()
    else:
        target = Path(path)

    if not target.exists():
        return {"path": str(target), "parent": str(target.parent), "dirs": [], "error": "路径不存在"}

    if not target.is_dir():
        target = target.parent

    resolved = target.resolve()
    dirs = []
    try:
        for entry in sorted(resolved.iterdir()):
            if entry.is_dir() and not entry.name.startswith("."):
                dirs.append({"name": entry.name, "path": str(entry)})
    except PermissionError:
        return {"path": str(resolved), "parent": str(resolved.parent), "dirs": [], "error": "无权限访问"}

    # 检查是否为 git 仓库
    is_git = (resolved / ".git").exists()

    return {
        "path": str(resolved),
        "parent": str(resolved.parent) if resolved.parent != resolved else None,
        "is_git": is_git,
        "dirs": dirs,
    }
