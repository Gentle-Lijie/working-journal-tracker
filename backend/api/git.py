"""Git日志API - 实时读取Git log"""

from pathlib import Path

from fastapi import APIRouter, Query
from git import Repo
from git.exc import InvalidGitRepositoryError

router = APIRouter(prefix="/api/git", tags=["git"])


@router.get("/log")
def get_git_log(limit: int = Query(20, le=100)):
    """实时读取Git提交记录"""
    # 从项目根目录读取
    repo_path = Path(__file__).parent.parent.parent
    try:
        repo = Repo(repo_path)
    except InvalidGitRepositoryError:
        return []

    commits = []
    for commit in repo.iter_commits(max_count=limit):
        # 获取变更文件
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
        except Exception:
            pass

        commits.append({
            "hash": commit.hexsha[:8],
            "message": commit.message.strip(),
            "author": str(commit.author),
            "timestamp": commit.committed_datetime.isoformat(),
            "changed_files": changed_files,
            "stats": stats,
        })

    return commits
