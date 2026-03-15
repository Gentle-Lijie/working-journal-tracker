"""文件变化监控器（使用 watchfiles 替代 watchdog，内存占用更低）"""

import gc
import logging
import threading
import time
from collections import deque
from datetime import datetime
from pathlib import Path

from watchfiles import watch

from backend.database import get_db_session
from backend.models.activity import Activity
from shared.constants import (
    ACTIVITY_TYPE_FILE_CREATE,
    ACTIVITY_TYPE_FILE_DELETE,
    ACTIVITY_TYPE_FILE_MODIFY,
)
from shared.utils import is_ignored

logger = logging.getLogger(__name__)

# 最大缓冲区大小
_MAX_BUFFER_SIZE = 500
# 刷新间隔（秒）
_FLUSH_INTERVAL = 60


class FileMonitor:
    """文件变化监控器（使用 watchfiles）"""

    def __init__(
        self,
        watch_paths: list[str],
        session_id: int,
        ignored_patterns: list[str],
        batch_size: int = 10,
        batch_interval: int = 300,
        project_id: int | None = None,
    ):
        self.watch_paths = [str(Path(p).resolve()) for p in watch_paths]
        self.session_id = session_id
        self.project_id = project_id
        self.ignored_patterns = ignored_patterns
        self.batch_size = batch_size
        self.batch_interval = batch_interval
        self._running = False
        # 事件缓冲区
        self._buffer: deque[dict] = deque(maxlen=_MAX_BUFFER_SIZE)
        self._lock = threading.Lock()
        # 监控线程
        self._watch_thread = None
        self._flush_thread = None

    def start(self):
        """启动文件监控"""
        self._running = True

        # 启动监控线程
        self._watch_thread = threading.Thread(target=self._watch_loop, daemon=True)
        self._watch_thread.start()

        # 启动定时刷新线程
        self._flush_thread = threading.Thread(target=self._flush_loop, daemon=True)
        self._flush_thread.start()

        logger.info(f"文件监控器已启动: {self.watch_paths}")

    def stop(self):
        """停止文件监控"""
        self._running = False

        # 等待线程结束
        if self._watch_thread and self._watch_thread.is_alive():
            self._watch_thread.join(timeout=2)
        if self._flush_thread and self._flush_thread.is_alive():
            self._flush_thread.join(timeout=2)

        # 刷新剩余数据
        self._flush_buffer()
        logger.info("文件监控器已停止")

    def _watch_loop(self):
        """文件监控主循环（使用 watchfiles）"""
        try:
            # watchfiles 会自动合并事件，减少内存占用
            for changes in watch(
                *self.watch_paths,
                watch_filter=self._filter_change,
                debounce=500,  # 500ms 防抖，合并快速连续事件
                step=100,  # 每 100ms 检查一次
            ):
                if not self._running:
                    break

                for change_type, path in changes:
                    if not self._running:
                        break
                    self._record_change(change_type, path)

        except Exception as e:
            if self._running:
                logger.error(f"文件监控出错: {e}")

    def _filter_change(self, change_type, path: str) -> bool:
        """过滤不需要监控的文件"""
        # 过滤忽略的文件
        if is_ignored(path, self.ignored_patterns):
            return False
        return True

    def _record_change(self, change_type, path: str):
        """记录文件变更"""
        # watchfiles 的 change_type: 1=created, 2=modified, 3=deleted
        type_map = {
            1: ACTIVITY_TYPE_FILE_CREATE,
            2: ACTIVITY_TYPE_FILE_MODIFY,
            3: ACTIVITY_TYPE_FILE_DELETE,
        }
        activity_type = type_map.get(change_type, ACTIVITY_TYPE_FILE_MODIFY)

        event_data = {
            "activity_type": activity_type,
            "filepath": path,
            "timestamp": datetime.now(),
        }

        with self._lock:
            self._buffer.append(event_data)

    def _flush_loop(self):
        """定时刷新缓冲区"""
        while self._running:
            time.sleep(_FLUSH_INTERVAL)
            if not self._running:
                break
            try:
                self._flush_buffer()
            except Exception as e:
                logger.error(f"刷新缓冲区失败: {e}")

    def _flush_buffer(self):
        """将缓冲区写入数据库"""
        with self._lock:
            if not self._buffer:
                return
            events = list(self._buffer)
            self._buffer.clear()

        if not events:
            return

        try:
            # 合并同一文件的多次变更，只保留最后一次
            merged = {}
            for event in events:
                filepath = event["filepath"]
                merged[filepath] = event
            events = list(merged.values())
            del merged

            with get_db_session() as session:
                type_desc = {
                    ACTIVITY_TYPE_FILE_CREATE: "创建",
                    ACTIVITY_TYPE_FILE_MODIFY: "修改",
                    ACTIVITY_TYPE_FILE_DELETE: "删除",
                }

                for event in events:
                    activity = Activity(
                        session_id=self.session_id,
                        project_id=self.project_id,
                        activity_type=event["activity_type"],
                        timestamp=event["timestamp"],
                        description=f"{type_desc.get(event['activity_type'], '变更')}文件: {Path(event['filepath']).name}",
                        metadata_json={"filepath": event["filepath"]},
                    )
                    session.add(activity)

            logger.info(f"批量写入 {len(events)} 条文件变更记录")

        except Exception as e:
            logger.error(f"写入文件变更记录失败: {e}")
        finally:
            # 清理临时变量
            del events
            gc.collect()
