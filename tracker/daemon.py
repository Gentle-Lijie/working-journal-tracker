"""守护进程主逻辑"""

import logging
import os
import signal
import sys
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path

from shared.config import get_config
from shared.constants import LOG_FILE, SESSION_STATUS_STOPPED
from shared.platform_compat import IS_WINDOWS
from shared.utils import get_app_dir, remove_daemon_pid, save_daemon_pid

logger = logging.getLogger(__name__)


def _seconds_until_next_hour() -> float:
    """计算距离下一个整点的秒数"""
    now = datetime.now()
    next_hour = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
    return (next_hour - now).total_seconds()


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

        # 启动整点日志自动生成
        journal_thread = threading.Thread(target=self._journal_scheduler, daemon=True)
        journal_thread.start()

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

    def _journal_scheduler(self):
        """整点自动生成日志的调度线程"""
        logger.info("日志自动生成调度器已启动")
        while self._running:
            wait = _seconds_until_next_hour()
            logger.info(f"下次日志生成将在 {wait:.0f} 秒后（下一个整点）")
            # 分段 sleep，以便及时响应停止信号
            deadline = time.monotonic() + wait
            while self._running and time.monotonic() < deadline:
                time.sleep(min(5, deadline - time.monotonic()))
            if not self._running:
                break
            try:
                self._generate_journal()
            except Exception as e:
                logger.error(f"自动生成日志失败: {e}")

    def _generate_journal(self):
        """生成日志：从上一条日志的终点到当前时间"""
        from backend.database import get_db_session
        from backend.models.journal_entry import JournalEntry
        from backend.services.journal_generator import JournalGenerator

        now = datetime.now()

        # 查找该项目最近一条日志的 end_time 作为起点
        with get_db_session() as session:
            last_entry = (
                session.query(JournalEntry)
                .filter(JournalEntry.project_id == self.project_id)
                .order_by(JournalEntry.end_time.desc())
                .first()
            )
            if last_entry:
                start_time = last_entry.end_time
            else:
                # 没有历史日志，从当前会话开始时间算起
                from backend.models.work_session import WorkSession
                ws = session.query(WorkSession).get(self.session_id)
                start_time = ws.start_time if ws else now - timedelta(hours=1)

        if start_time >= now:
            logger.info("起始时间不早于当前时间，跳过日志生成")
            return

        logger.info(f"自动生成日志: {start_time} ~ {now}, project_id={self.project_id}")
        generator = JournalGenerator()
        entry = generator.generate(
            start_time=start_time,
            end_time=now,
            session_id=self.session_id,
            project_id=self.project_id,
        )
        if entry:
            logger.info(f"自动日志已生成: #{entry.id}")
        else:
            logger.info("该时段无活动记录，跳过")

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
