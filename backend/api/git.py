"""Git日志API - 实时读取Git log"""

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Query
from git import Repo
from git.exc import InvalidGitRepositoryError

from backend.database import get_db_session
from backend.models.project import Project
from shared.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/git", tags=["git"])


@router.get("/log")
def get_git_log(limit: int = Query(20, le=100), project_id: Optional[int] = Query(None)):
    """实时读取Git提交记录"""
    logger.info(f"查询Git提交记录: limit={limit}, project_id={project_id}")
    # 根据project_id查找项目路径，否则使用项目根目录
    if project_id is not None:
        with get_db_session() as session:
            project = session.query(Project).get(project_id)
            if not project:
                logger.warning(f"项目不存在: project_id={project_id}")
                return []
            repo_path = Path(project.path)
    else:
        repo_path = Path(__file__).parent.parent.parent

    try:
        repo = Repo(repo_path)
    except InvalidGitRepositoryError:
        logger.warning(f"无效的Git仓库: path={repo_path}")
        return []

    commits = []
    for commit in repo.iter_commits(max_count=limit):
        changed_files = []
        stats = {"insertions": 0, "deletions": 0, "files": 0}
        try:
            if commit.parents:
                diffs = commit.parents[0].diff(commit)
                changed_files = [d.a_path or d.b_path for d in diffs]
            else:
                changed_files = list(commit.stats.files.keys())
            stats = {
                "insertions": commit.stats.total["insertions"],
                "deletions": commit.stats.total["deletions"],
                "files": commit.stats.total["files"],
            }
        except Exception as e:
            logger.error(f"解析提交统计信息失败: commit={commit.hexsha[:8]}, error={str(e)}")
            pass

        commits.append({
            "hash": commit.hexsha[:8],
            "message": commit.message.strip(),
            "author": str(commit.author),
            "timestamp": commit.committed_datetime.isoformat(),
            "changed_files": changed_files,
            "stats": stats,
        })

    logger.info(f"返回 {len(commits)} 条Git提交记录")
    return commits
