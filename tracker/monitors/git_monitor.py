"""Git提交监控器"""

import logging
import time
from datetime import datetime
from pathlib import Path

from git import Repo
from git.exc import GitCommandError, InvalidGitRepositoryError

from backend.database import get_db_session
from backend.models.activity import Activity
from shared.constants import ACTIVITY_TYPE_GIT_COMMIT

logger = logging.getLogger(__name__)


class GitMonitor:
    """Git提交监控器"""

    def __init__(self, repo_path: str, session_id: int, check_interval: int = 30, project_id: int | None = None):
        self.repo_path = Path(repo_path)
        self.session_id = session_id
        self.project_id = project_id
        self.check_interval = check_interval
        self.last_commit_hash = None
        self.repo = None
        self._running = False

    def initialize(self):
        """初始化Git仓库"""
        try:
            self.repo = Repo(self.repo_path)
            if self.repo.head.is_valid():
                self.last_commit_hash = self.repo.head.commit.hexsha
            logger.info(f"Git监控器已初始化: {self.repo_path}")
        except (InvalidGitRepositoryError, GitCommandError) as e:
            logger.warning(f"不是有效的Git仓库: {self.repo_path}, {e}")
            self.repo = None

    def start(self):
        """启动监控"""
        if not self.repo:
            logger.warning("Git仓库未初始化，跳过监控")
            return

        self._running = True
        logger.info("Git监控器已启动")

        while self._running:
            try:
                self._check_new_commits()
            except Exception as e:
                logger.error(f"检查Git提交时出错: {e}")

            time.sleep(self.check_interval)

    def stop(self):
        """停止监控"""
        self._running = False
        logger.info("Git监控器已停止")

    def _check_new_commits(self):
        """检查新提交"""
        if not self.repo:
            return

        try:
            # 刷新仓库状态
            self.repo.remotes.origin.fetch() if self.repo.remotes else None
            current_commit = self.repo.head.commit

            if current_commit.hexsha != self.last_commit_hash:
                # 获取所有新提交
                if self.last_commit_hash:
                    try:
                        old_commit = self.repo.commit(self.last_commit_hash)
                        new_commits = list(self.repo.iter_commits(f"{old_commit}..{current_commit}"))
                    except Exception:
                        new_commits = [current_commit]
                else:
                    new_commits = [current_commit]

                # 记录每个新提交
                for commit in reversed(new_commits):
                    self._record_commit(commit)

                self.last_commit_hash = current_commit.hexsha

        except Exception as e:
            logger.error(f"检查提交时出错: {e}")

    def _record_commit(self, commit):
        """记录Git提交"""
        try:
            # 获取变更的文件
            changed_files = []
            if commit.parents:
                diffs = commit.parents[0].diff(commit)
                changed_files = [d.a_path or d.b_path for d in diffs]
            else:
                # 首次提交
                changed_files = list(commit.stats.files.keys())

            metadata = {
                "commit_hash": commit.hexsha,
                "author": str(commit.author),
                "author_email": commit.author.email,
                "changed_files": changed_files,
                "stats": {
                    "insertions": commit.stats.total["insertions"],
                    "deletions": commit.stats.total["deletions"],
                    "files": commit.stats.total["files"],
                },
            }

            with get_db_session() as session:
                activity = Activity(
                    session_id=self.session_id,
                    project_id=self.project_id,
                    activity_type=ACTIVITY_TYPE_GIT_COMMIT,
                    timestamp=datetime.fromtimestamp(commit.committed_date),
                    description=commit.message.strip(),
                    metadata_json=metadata,
                )
                session.add(activity)

            logger.info(f"记录Git提交: {commit.hexsha[:8]} - {commit.message[:50]}")

        except Exception as e:
            logger.error(f"记录提交失败: {e}")
