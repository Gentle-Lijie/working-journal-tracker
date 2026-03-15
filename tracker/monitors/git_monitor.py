"""Git提交监控器"""

import gc
import logging
import subprocess
import time
from datetime import datetime
from pathlib import Path

from git import Repo
from git.exc import GitCommandError, InvalidGitRepositoryError

from backend.database import get_db_session
from backend.models.activity import Activity
from shared.constants import ACTIVITY_TYPE_GIT_COMMIT

logger = logging.getLogger(__name__)

# GitPython 内存泄漏缓解：每 N 次检查后重建 Repo 对象（更频繁）
_REPO_REFRESH_INTERVAL = 20  # 约 10 分钟刷新一次（check_interval=30s）


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
        self._check_count = 0  # 用于定期重建 Repo 对象

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

    def _close_repo(self):
        """关闭并清理 Repo 对象（缓解 GitPython 内存泄漏）"""
        if self.repo:
            try:
                # 清理 GitPython 内部缓存
                if hasattr(self.repo, 'git') and hasattr(self.repo.git, 'clear_cache'):
                    self.repo.git.clear_cache()
                # 清理引用缓存
                if hasattr(self.repo, 'references'):
                    self.repo.references._clear_cache()
                self.repo.close()
            except Exception as e:
                logger.debug(f"关闭 Repo 对象时出错（可忽略）: {e}")
            finally:
                self.repo = None
                gc.collect()  # 强制垃圾回收

    def _refresh_repo(self):
        """定期重建 Repo 对象（缓解 GitPython 内存泄漏）"""
        logger.info("重建 Repo 对象以释放内存...")
        self._close_repo()
        self.initialize()

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
                self._check_count += 1

                # 定期重建 Repo 对象，释放 GitPython 累积的内存
                if self._check_count >= _REPO_REFRESH_INTERVAL:
                    self._refresh_repo()
                    self._check_count = 0

            except Exception as e:
                logger.error(f"检查Git提交时出错: {e}")

            time.sleep(self.check_interval)

    def stop(self):
        """停止监控"""
        self._running = False
        self._close_repo()
        logger.info("Git监控器已停止")

    def _check_new_commits(self):
        """检查新提交"""
        if not self.repo:
            return

        try:
            # 使用 git 命令行获取当前 commit hash，避免 GitPython 缓存
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                logger.debug(f"获取当前 commit 失败: {result.stderr}")
                return

            current_hash = result.stdout.strip()

            if current_hash != self.last_commit_hash:
                # 获取所有新提交（使用 git 命令行，避免 GitPython 内存泄漏）
                if self.last_commit_hash:
                    try:
                        log_result = subprocess.run(
                            ["git", "log", "--format=%H", f"{self.last_commit_hash}..{current_hash}"],
                            cwd=self.repo_path,
                            capture_output=True,
                            text=True,
                            timeout=30,
                        )
                        if log_result.returncode == 0:
                            new_hashes = [h.strip() for h in log_result.stdout.strip().split("\n") if h.strip()]
                        else:
                            new_hashes = [current_hash]
                    except Exception:
                        new_hashes = [current_hash]
                else:
                    new_hashes = [current_hash]

                # 记录每个新提交（逆序，从旧到新）
                for commit_hash in reversed(new_hashes):
                    self._record_commit_by_hash(commit_hash)

                self.last_commit_hash = current_hash

        except subprocess.TimeoutExpired:
            logger.warning("Git 命令超时")
        except Exception as e:
            logger.error(f"检查提交时出错: {e}")

    def _record_commit_by_hash(self, commit_hash: str):
        """使用 git 命令行记录提交（避免 GitPython 内存泄漏）"""
        try:
            # 获取提交信息
            log_format = "%H%n%an%n%ae%n%ct%n%s%n---STATS---"
            result = subprocess.run(
                ["git", "log", "-1", f"--format={log_format}", commit_hash],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                logger.error(f"获取提交信息失败: {commit_hash[:8]}")
                return

            lines = result.stdout.strip().split("\n")
            if len(lines) < 5:
                return

            hash_full = lines[0]
            author = lines[1]
            author_email = lines[2]
            timestamp = int(lines[3])
            message = "\n".join(lines[4:]).split("---STATS---")[0].strip()

            # 获取变更文件列表（使用 git diff-tree，更快且不缓存）
            diff_result = subprocess.run(
                ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", commit_hash],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=10,
            )
            changed_files = []
            if diff_result.returncode == 0:
                changed_files = [f.strip() for f in diff_result.stdout.strip().split("\n") if f.strip()]

            # 获取统计信息
            stat_result = subprocess.run(
                ["git", "show", "--numstat", "--format=", commit_hash],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=10,
            )
            insertions = 0
            deletions = 0
            files_count = len(changed_files)
            if stat_result.returncode == 0:
                for line in stat_result.stdout.strip().split("\n"):
                    if line.strip():
                        parts = line.split()
                        if len(parts) >= 2:
                            try:
                                # 新增行数（- 表示二进制文件）
                                if parts[0] != "-":
                                    insertions += int(parts[0])
                                # 删除行数
                                if parts[1] != "-":
                                    deletions += int(parts[1])
                            except ValueError:
                                pass

            # 构建元数据（纯 Python 数据，无 GitPython 对象引用）
            metadata = {
                "commit_hash": hash_full,
                "author": author,
                "author_email": author_email,
                "changed_files": changed_files,
                "stats": {
                    "insertions": insertions,
                    "deletions": deletions,
                    "files": files_count,
                },
            }
            commit_time = datetime.fromtimestamp(timestamp)
            commit_msg = message
            commit_hash_short = hash_full[:8]

            with get_db_session() as session:
                activity = Activity(
                    session_id=self.session_id,
                    project_id=self.project_id,
                    activity_type=ACTIVITY_TYPE_GIT_COMMIT,
                    timestamp=commit_time,
                    description=commit_msg,
                    metadata_json=metadata,
                )
                session.add(activity)

            logger.info(f"记录Git提交: {commit_hash_short} - {commit_msg[:50]}")

        except subprocess.TimeoutExpired:
            logger.warning(f"获取提交信息超时: {commit_hash[:8]}")
        except Exception as e:
            logger.error(f"记录提交失败: {e}")
