"""守护进程主逻辑"""

import logging
import os
import signal
import sys
import threading
from datetime import datetime
from pathlib import Path

from shared.config import get_config
from shared.constants import LOG_FILE, SESSION_STATUS_STOPPED
from shared.platform_compat import IS_WINDOWS
from shared.utils import get_app_dir, remove_daemon_pid, save_daemon_pid

logger = logging.getLogger(__name__)


class TrackerDaemon:
    """追踪器守护进程"""

    def __init__(self, session_id: int, repo_path: str, project_id: int | None = None):
        self.session_id = session_id
        self.repo_path = repo_path
        self.project_id = project_id
        self.git_monitor = None
        self.file_monitor = None
        self._running = False

    def start(self):
        """启动守护进程"""
        self._running = True
        config = get_config()
        tracker_config = config.tracker

        # 写入PID文件
        self._write_pid()

        # 设置信号处理（Windows 不支持 SIGTERM 注册）
        signal.signal(signal.SIGINT, self._signal_handler)
        if not IS_WINDOWS:
            signal.signal(signal.SIGTERM, self._signal_handler)

        # 配置日志
        self._setup_logging()

        logger.info(f"守护进程启动: session_id={self.session_id}, project_id={self.project_id}, path={self.repo_path}")

        # 启动Git监控
        from tracker.monitors.git_monitor import GitMonitor

        self.git_monitor = GitMonitor(
            repo_path=self.repo_path,
            session_id=self.session_id,
            project_id=self.project_id,
            check_interval=tracker_config.get("git_check_interval", 30),
        )
        self.git_monitor.initialize()

        git_thread = threading.Thread(target=self.git_monitor.start, daemon=True)
        git_thread.start()

        # 启动文件监控
        from tracker.monitors.file_monitor import FileMonitor

        watch_paths = tracker_config.get("watch_paths", [self.repo_path])
        # 如果是相对路径，转换为基于repo_path的绝对路径
        resolved_paths = []
        for p in watch_paths:
            path = Path(p)
            if not path.is_absolute():
                path = Path(self.repo_path) / path
            resolved_paths.append(str(path.resolve()))

        self.file_monitor = FileMonitor(
            watch_paths=resolved_paths,
            session_id=self.session_id,
            project_id=self.project_id,
            ignored_patterns=tracker_config.get("ignored_patterns", []),
            batch_size=tracker_config.get("file_batch_size", 10),
            batch_interval=tracker_config.get("file_batch_interval", 300),
        )
        self.file_monitor.start()

        # 保持主线程运行
        try:
            while self._running:
                git_thread.join(timeout=1)
                if not git_thread.is_alive() and self._running:
                    # Git线程异常退出，重启
                    logger.warning("Git监控线程异常退出，正在重启...")
                    git_thread = threading.Thread(target=self.git_monitor.start, daemon=True)
                    git_thread.start()
        except (KeyboardInterrupt, SystemExit):
            self.stop()

    def stop(self):
        """停止守护进程"""
        logger.info("正在停止守护进程...")
        self._running = False

        if self.git_monitor:
            self.git_monitor.stop()

        if self.file_monitor:
            self.file_monitor.stop()

        # 更新会话状态
        try:
            from backend.database import get_db_session
            from backend.models.work_session import WorkSession

            with get_db_session() as session:
                work_session = session.query(WorkSession).get(self.session_id)
                if work_session:
                    work_session.end_time = datetime.now()
                    work_session.status = SESSION_STATUS_STOPPED
        except Exception as e:
            logger.error(f"更新会话状态失败: {e}")

        self._remove_pid()
        logger.info("守护进程已停止")

    def _signal_handler(self, signum, frame):
        """信号处理器"""
        logger.info(f"收到信号: {signum}")
        self.stop()
        sys.exit(0)

    def _write_pid(self):
        """写入PID文件"""
        save_daemon_pid(os.getpid(), self.project_id)
        logger.info(f"PID文件已写入: project_id={self.project_id}")

    def _remove_pid(self):
        """删除PID文件"""
        remove_daemon_pid(self.project_id)

    def _setup_logging(self):
        """配置守护进程日志"""
        log_path = get_app_dir() / LOG_FILE
        handler = logging.FileHandler(log_path)
        handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        logging.getLogger().addHandler(handler)
        logging.getLogger().setLevel(logging.INFO)


def get_daemon_pid(project_id: int | None = None) -> int | None:
    """获取守护进程PID"""
    from shared.utils import get_daemon_pid as _get_pid
    return _get_pid(project_id)


def is_daemon_running(project_id: int | None = None) -> bool:
    """检查守护进程是否在运行"""
    return get_daemon_pid(project_id) is not None


def get_all_running_daemons() -> dict[int, int]:
    """获取所有运行中的守护进程 {project_id: pid}"""
    from shared.utils import get_all_daemon_pids
    return get_all_daemon_pids()
