"""独立组件运行入口

用于按需启动单个追踪器组件，便于调试内存泄漏问题。
每个组件作为独立进程运行，有独立的 PID 文件。
"""

import logging
import os
import signal
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

from shared.config import get_config
from shared.constants import LOG_FILE, SESSION_STATUS_ACTIVE
from shared.platform_compat import IS_WINDOWS
from shared.utils import (
    COMPONENT_TYPES,
    get_app_dir,
    remove_component_pid,
    save_component_pid,
)

logger = logging.getLogger(__name__)


def _setup_logging(component: str, project_id: int):
    """配置组件日志"""
    log_path = get_app_dir() / f"component-{project_id}-{component}.log"
    handler = logging.FileHandler(log_path)
    handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )
    logging.getLogger().addHandler(handler)
    logging.getLogger().setLevel(logging.INFO)
    logger.info(f"组件日志已配置: {log_path}")


def _get_or_create_active_session(project_id: int) -> int:
    """获取或创建活跃的工作会话

    Returns:
        session_id
    """
    from backend.database import get_db_session
    from backend.models.work_session import WorkSession
    from shared.constants import SESSION_STATUS_ACTIVE

    with get_db_session() as session:
        # 查找是否有活跃会话
        active_session = (
            session.query(WorkSession)
            .filter(
                WorkSession.project_id == project_id,
                WorkSession.status == SESSION_STATUS_ACTIVE,
            )
            .first()
        )
        if active_session:
            logger.info(f"使用现有会话: session_id={active_session.id}")
            return active_session.id

        # 创建新会话
        work_session = WorkSession(
            start_time=datetime.now(),
            status=SESSION_STATUS_ACTIVE,
            project_id=project_id,
        )
        session.add(work_session)
        session.flush()
        logger.info(f"创建新会话: session_id={work_session.id}")
        return work_session.id


def _seconds_until_next_hour() -> float:
    """计算距离下一个整点的秒数"""
    now = datetime.now()
    next_hour = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
    return (next_hour - now).total_seconds()


def run_git_monitor(project_id: int, repo_path: str):
    """单独运行 Git 监控组件

    Args:
        project_id: 项目 ID
        repo_path: Git 仓库路径
    """
    from backend.database import init_database
    from shared.path_map import get_path_map

    # 初始化
    get_config().load()
    init_database()
    _setup_logging("git", project_id)

    # 获取项目路径（如果未提供）
    if not repo_path:
        from backend.database import get_db_session
        from backend.models.project import Project

        with get_db_session() as session:
            project = session.query(Project).get(project_id)
            if project:
                repo_path = get_path_map().get_path(project.name)

    if not repo_path:
        logger.error("未提供项目路径，无法启动 Git 监控")
        return

    repo_path = str(Path(repo_path).resolve())
    logger.info(f"启动 Git 监控组件: project_id={project_id}, path={repo_path}")

    # 获取或创建会话
    session_id = _get_or_create_active_session(project_id)

    # 写入 PID
    save_component_pid(os.getpid(), project_id, "git")

    # 设置信号处理
    _running = True

    def signal_handler(signum, frame):
        nonlocal _running
        logger.info(f"收到信号: {signum}")
        _running = False

    signal.signal(signal.SIGINT, signal_handler)
    if not IS_WINDOWS:
        signal.signal(signal.SIGTERM, signal_handler)

    # 初始化 Git 监控器
    from tracker.monitors.git_monitor import GitMonitor

    config = get_config()
    tracker_config = config.tracker
    git_monitor = GitMonitor(
        repo_path=repo_path,
        session_id=session_id,
        project_id=project_id,
        check_interval=tracker_config.get("git_check_interval", 30),
    )
    git_monitor.initialize()

    try:
        while _running:
            try:
                git_monitor._check_new_commits()
                git_monitor._check_count += 1

                # 定期垃圾回收
                if git_monitor._check_count >= 20:
                    import gc
                    gc.collect()
                    git_monitor._check_count = 0

            except Exception as e:
                logger.error(f"检查 Git 提交时出错: {e}")

            # 分段 sleep，以便及时响应停止信号
            for _ in range(git_monitor.check_interval):
                if not _running:
                    break
                time.sleep(1)

    finally:
        git_monitor.stop()
        remove_component_pid(project_id, "git")
        logger.info("Git 监控组件已停止")


def run_file_monitor(project_id: int, watch_paths: list[str] | None = None):
    """单独运行文件监控组件

    Args:
        project_id: 项目 ID
        watch_paths: 监控路径列表，为空时使用配置中的路径
    """
    from backend.database import init_database
    from shared.path_map import get_path_map

    # 初始化
    get_config().load()
    init_database()
    _setup_logging("file", project_id)

    # 获取监控路径
    if not watch_paths:
        from backend.database import get_db_session
        from backend.models.project import Project

        config = get_config()
        tracker_config = config.tracker

        with get_db_session() as session:
            project = session.query(Project).get(project_id)
            if project:
                repo_path = get_path_map().get_path(project.name)
                if repo_path:
                    # 使用配置中的路径或默认使用项目路径
                    watch_paths = tracker_config.get("watch_paths", [repo_path])
                    # 处理相对路径
                    resolved_paths = []
                    for p in watch_paths:
                        path = Path(p)
                        if not path.is_absolute():
                            path = Path(repo_path) / path
                        resolved_paths.append(str(path.resolve()))
                    watch_paths = resolved_paths

    if not watch_paths:
        logger.error("未提供监控路径，无法启动文件监控")
        return

    logger.info(f"启动文件监控组件: project_id={project_id}, paths={watch_paths}")

    # 获取或创建会话
    session_id = _get_or_create_active_session(project_id)

    # 写入 PID
    save_component_pid(os.getpid(), project_id, "file")

    # 设置信号处理
    _running = True

    def signal_handler(signum, frame):
        nonlocal _running
        logger.info(f"收到信号: {signum}")
        _running = False

    signal.signal(signal.SIGINT, signal_handler)
    if not IS_WINDOWS:
        signal.signal(signal.SIGTERM, signal_handler)

    # 初始化文件监控器
    config = get_config()
    tracker_config = config.tracker

    from tracker.monitors.file_monitor import FileMonitor

    file_monitor = FileMonitor(
        watch_paths=watch_paths,
        session_id=session_id,
        project_id=project_id,
        ignored_patterns=tracker_config.get("ignored_patterns", []),
        batch_size=tracker_config.get("file_batch_size", 10),
        batch_interval=tracker_config.get("file_batch_interval", 300),
    )

    try:
        file_monitor.start()

        # 保持主线程运行
        while _running:
            time.sleep(1)

    finally:
        file_monitor.stop()
        remove_component_pid(project_id, "file")
        logger.info("文件监控组件已停止")


def run_journal_generator(project_id: int):
    """单独运行日志生成器组件

    整点自动生成工作日志

    Args:
        project_id: 项目 ID
    """
    from backend.database import init_database

    # 初始化
    get_config().load()
    init_database()
    _setup_logging("journal", project_id)

    logger.info(f"启动日志生成器组件: project_id={project_id}")

    # 获取或创建会话
    session_id = _get_or_create_active_session(project_id)

    # 写入 PID
    save_component_pid(os.getpid(), project_id, "journal")

    # 设置信号处理
    _running = True

    def signal_handler(signum, frame):
        nonlocal _running
        logger.info(f"收到信号: {signum}")
        _running = False

    signal.signal(signal.SIGINT, signal_handler)
    if not IS_WINDOWS:
        signal.signal(signal.SIGTERM, signal_handler)

    try:
        while _running:
            wait = _seconds_until_next_hour()
            logger.info(f"下次日志生成将在 {wait:.0f} 秒后（下一个整点）")

            # 分段 sleep，以便及时响应停止信号
            deadline = time.monotonic() + wait
            while _running and time.monotonic() < deadline:
                time.sleep(min(5, deadline - time.monotonic()))

            if not _running:
                break

            try:
                _generate_journal_internal(project_id, session_id)
            except Exception as e:
                logger.error(f"自动生成日志失败: {e}")

    finally:
        remove_component_pid(project_id, "journal")
        logger.info("日志生成器组件已停止")


def _generate_journal_internal(project_id: int, session_id: int):
    """内部函数：生成日志"""
    from backend.database import get_db_session
    from backend.models.journal_entry import JournalEntry
    from backend.models.work_session import WorkSession
    from backend.services.journal_generator import JournalGenerator

    now = datetime.now()

    # 查找该项目最近一条日志的 end_time 作为起点
    with get_db_session() as session:
        last_entry = (
            session.query(JournalEntry)
            .filter(JournalEntry.project_id == project_id)
            .order_by(JournalEntry.end_time.desc())
            .first()
        )
        if last_entry:
            start_time = last_entry.end_time
        else:
            # 没有历史日志，从当前会话开始时间算起
            ws = session.query(WorkSession).get(session_id)
            start_time = ws.start_time if ws else now - timedelta(hours=1)

    if start_time >= now:
        logger.info("起始时间不早于当前时间，跳过日志生成")
        return

    logger.info(f"自动生成日志: {start_time} ~ {now}, project_id={project_id}")
    generator = JournalGenerator()
    entry = generator.generate(
        start_time=start_time,
        end_time=now,
        session_id=session_id,
        project_id=project_id,
    )
    if entry:
        logger.info(f"自动日志已生成: #{entry.id}")
    else:
        logger.info("该时段无活动记录，跳过")


if __name__ == "__main__":
    """命令行入口

    用法:
        python -m tracker.run_component <component> <project_id> [repo_path]

    示例:
        python -m tracker.run_component git 1 /path/to/repo
        python -m tracker.run_component file 1
        python -m tracker.run_component journal 1
    """
    if len(sys.argv) < 3:
        print("用法: python -m tracker.run_component <component> <project_id> [repo_path]")
        print(f"支持的组件: {', '.join(COMPONENT_TYPES)}")
        sys.exit(1)

    component = sys.argv[1]
    if component not in COMPONENT_TYPES:
        print(f"错误: 不支持的组件 '{component}'")
        print(f"支持的组件: {', '.join(COMPONENT_TYPES)}")
        sys.exit(1)

    try:
        project_id = int(sys.argv[2])
    except ValueError:
        print(f"错误: project_id 必须是整数")
        sys.exit(1)

    repo_path = sys.argv[3] if len(sys.argv) > 3 else ""

    if component == "git":
        run_git_monitor(project_id, repo_path)
    elif component == "file":
        run_file_monitor(project_id, None)
    elif component == "journal":
        run_journal_generator(project_id)
