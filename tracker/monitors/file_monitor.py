"""文件变化监控器"""

import logging
import threading
import time
from datetime import datetime
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from backend.database import get_db_session
from backend.models.activity import Activity
from shared.constants import (
    ACTIVITY_TYPE_FILE_CREATE,
    ACTIVITY_TYPE_FILE_DELETE,
    ACTIVITY_TYPE_FILE_MODIFY,
)
from shared.utils import is_ignored

logger = logging.getLogger(__name__)


class FileChangeHandler(FileSystemEventHandler):
    """文件变化事件处理器"""

    def __init__(
        self,
        session_id: int,
        ignored_patterns: list[str],
        batch_size: int = 10,
        batch_interval: int = 300,
    ):
        self.session_id = session_id
        self.ignored_patterns = ignored_patterns
        self.batch_size = batch_size
        self.batch_interval = batch_interval
        self._buffer: list[dict] = []
        self._lock = threading.Lock()

    def on_created(self, event):
        if not event.is_directory:
            self._add_event(ACTIVITY_TYPE_FILE_CREATE, event.src_path)

    def on_modified(self, event):
        if not event.is_directory:
            self._add_event(ACTIVITY_TYPE_FILE_MODIFY, event.src_path)

    def on_deleted(self, event):
        if not event.is_directory:
            self._add_event(ACTIVITY_TYPE_FILE_DELETE, event.src_path)

    def _add_event(self, activity_type: str, filepath: str):
        """添加事件到缓冲区"""
        if is_ignored(filepath, self.ignored_patterns):
            return

        event_data = {
            "activity_type": activity_type,
            "filepath": filepath,
            "timestamp": datetime.now(),
        }

        with self._lock:
            self._buffer.append(event_data)
            if len(self._buffer) >= self.batch_size:
                self._flush()

    def _flush(self):
        """将缓冲区的事件写入数据库"""
        if not self._buffer:
            return

        events_to_write = self._buffer[:]
        self._buffer.clear()

        try:
            with get_db_session() as session:
                for event in events_to_write:
                    type_desc = {
                        ACTIVITY_TYPE_FILE_CREATE: "创建",
                        ACTIVITY_TYPE_FILE_MODIFY: "修改",
                        ACTIVITY_TYPE_FILE_DELETE: "删除",
                    }
                    activity = Activity(
                        session_id=self.session_id,
                        activity_type=event["activity_type"],
                        timestamp=event["timestamp"],
                        description=f"{type_desc.get(event['activity_type'], '变更')}文件: {Path(event['filepath']).name}",
                        metadata_json={"filepath": event["filepath"]},
                    )
                    session.add(activity)

            logger.info(f"批量写入 {len(events_to_write)} 条文件变更记录")

        except Exception as e:
            logger.error(f"写入文件变更记录失败: {e}")

    def flush_remaining(self):
        """刷新剩余的缓冲区数据"""
        with self._lock:
            self._flush()


class FileMonitor:
    """文件变化监控器"""

    def __init__(
        self,
        watch_paths: list[str],
        session_id: int,
        ignored_patterns: list[str],
        batch_size: int = 10,
        batch_interval: int = 300,
    ):
        self.watch_paths = [Path(p).resolve() for p in watch_paths]
        self.session_id = session_id
        self.ignored_patterns = ignored_patterns
        self.handler = FileChangeHandler(
            session_id=session_id,
            ignored_patterns=ignored_patterns,
            batch_size=batch_size,
            batch_interval=batch_interval,
        )
        self.observer = Observer()
        self._flush_timer = None
        self._running = False
        self.batch_interval = batch_interval

    def start(self):
        """启动文件监控"""
        self._running = True

        for path in self.watch_paths:
            if path.exists():
                self.observer.schedule(self.handler, str(path), recursive=True)
                logger.info(f"监控目录: {path}")

        self.observer.start()
        self._schedule_flush()
        logger.info("文件监控器已启动")

    def stop(self):
        """停止文件监控"""
        self._running = False

        if self._flush_timer:
            self._flush_timer.cancel()

        self.observer.stop()
        self.observer.join()

        # 刷新剩余数据
        self.handler.flush_remaining()
        logger.info("文件监控器已停止")

    def _schedule_flush(self):
        """定时刷新缓冲区"""
        if not self._running:
            return
        self.handler.flush_remaining()
        self._flush_timer = threading.Timer(self.batch_interval, self._schedule_flush)
        self._flush_timer.daemon = True
        self._flush_timer.start()
