"""通用工具函数"""

import os
from datetime import datetime
from pathlib import Path

from cryptography.fernet import Fernet

from shared.constants import APP_DIR, SECRET_KEY_FILE
from shared.platform_compat import is_process_running, secure_chmod


def get_app_dir() -> Path:
    """获取应用数据目录 ~/.work-journal/"""
    app_dir = Path.home() / APP_DIR
    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir


def get_or_create_secret_key() -> bytes:
    """获取或创建加密密钥"""
    key_path = get_app_dir() / SECRET_KEY_FILE
    if key_path.exists():
        return key_path.read_bytes()
    key = Fernet.generate_key()
    key_path.write_bytes(key)
    secure_chmod(key_path)
    return key


def encrypt_value(value: str) -> str:
    """加密敏感信息"""
    key = get_or_create_secret_key()
    f = Fernet(key)
    return f.encrypt(value.encode()).decode()


def decrypt_value(encrypted: str) -> str:
    """解密敏感信息"""
    key = get_or_create_secret_key()
    f = Fernet(key)
    return f.decrypt(encrypted.encode()).decode()


def format_duration(seconds: float) -> str:
    """格式化时长为可读字符串"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    if hours > 0:
        return f"{hours}小时{minutes}分钟"
    return f"{minutes}分钟"


def format_datetime(dt: datetime) -> str:
    """格式化日期时间"""
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def is_ignored(filepath: str, patterns: list[str]) -> bool:
    """检查文件是否应被忽略"""
    path = Path(filepath)
    for pattern in patterns:
        if pattern.startswith("*"):
            if path.suffix == pattern[1:] or path.name.endswith(pattern[1:]):
                return True
        elif pattern in path.parts:
            return True
    return False


# === 多项目 PID 管理 ===

def save_daemon_pid(pid: int, project_id: int | None = None):
    """保存守护进程PID文件"""
    from shared.constants import PID_FILE
    if project_id is not None:
        pid_name = f"tracker-{project_id}.pid"
    else:
        pid_name = PID_FILE
    pid_path = get_app_dir() / pid_name
    pid_path.write_text(str(pid))


def get_daemon_pid(project_id: int | None = None) -> int | None:
    """获取守护进程PID"""
    from shared.constants import PID_FILE
    if project_id is not None:
        pid_name = f"tracker-{project_id}.pid"
    else:
        pid_name = PID_FILE
    pid_path = get_app_dir() / pid_name
    if pid_path.exists():
        try:
            pid = int(pid_path.read_text().strip())
            if is_process_running(pid):
                return pid
            pid_path.unlink(missing_ok=True)
        except ValueError:
            pid_path.unlink(missing_ok=True)
    return None


def remove_daemon_pid(project_id: int | None = None):
    """删除守护进程PID文件"""
    from shared.constants import PID_FILE
    if project_id is not None:
        pid_name = f"tracker-{project_id}.pid"
    else:
        pid_name = PID_FILE
    pid_path = get_app_dir() / pid_name
    pid_path.unlink(missing_ok=True)


def get_all_daemon_pids() -> dict[int, int]:
    """获取所有运行中的守护进程 {project_id: pid}"""
    app_dir = get_app_dir()
    result = {}
    for pid_file in app_dir.glob("tracker-*.pid"):
        try:
            # 只匹配 tracker-{project_id}.pid，排除组件 PID 文件
            name = pid_file.stem  # e.g., "tracker-1" or "tracker-1-git"
            parts = name.split("-", 1)
            if len(parts) != 2:
                continue
            # 检查是否是组件 PID（包含第二个连字符）
            if "-" in parts[1]:
                continue  # 这是组件 PID，跳过
            project_id = int(parts[1])
            pid = int(pid_file.read_text().strip())
            if is_process_running(pid):
                result[project_id] = pid
            else:
                pid_file.unlink(missing_ok=True)
        except (ValueError, IndexError):
            pid_file.unlink(missing_ok=True)
    return result


# === 组件 PID 管理 ===

COMPONENT_TYPES = ["git", "file", "journal"]
"""支持的组件类型"""


def save_component_pid(pid: int, project_id: int, component: str):
    """保存组件进程 PID 文件

    Args:
        pid: 进程 ID
        project_id: 项目 ID
        component: 组件类型 (git/file/journal)
    """
    if component not in COMPONENT_TYPES:
        raise ValueError(f"无效的组件类型: {component}，支持: {COMPONENT_TYPES}")
    pid_name = f"tracker-{project_id}-{component}.pid"
    pid_path = get_app_dir() / pid_name
    pid_path.write_text(str(pid))


def get_component_pid(project_id: int, component: str) -> int | None:
    """获取组件进程 PID

    Args:
        project_id: 项目 ID
        component: 组件类型 (git/file/journal)

    Returns:
        运行中的进程 PID，如果未运行返回 None
    """
    if component not in COMPONENT_TYPES:
        raise ValueError(f"无效的组件类型: {component}，支持: {COMPONENT_TYPES}")
    pid_name = f"tracker-{project_id}-{component}.pid"
    pid_path = get_app_dir() / pid_name
    if pid_path.exists():
        try:
            pid = int(pid_path.read_text().strip())
            if is_process_running(pid):
                return pid
            pid_path.unlink(missing_ok=True)
        except ValueError:
            pid_path.unlink(missing_ok=True)
    return None


def remove_component_pid(project_id: int, component: str):
    """删除组件进程 PID 文件

    Args:
        project_id: 项目 ID
        component: 组件类型 (git/file/journal)
    """
    if component not in COMPONENT_TYPES:
        raise ValueError(f"无效的组件类型: {component}，支持: {COMPONENT_TYPES}")
    pid_name = f"tracker-{project_id}-{component}.pid"
    pid_path = get_app_dir() / pid_name
    pid_path.unlink(missing_ok=True)


def get_all_component_pids(project_id: int) -> dict[str, int | None]:
    """获取项目所有组件的 PID 状态

    Args:
        project_id: 项目 ID

    Returns:
        {component: pid | None} 字典
    """
    return {comp: get_component_pid(project_id, comp) for comp in COMPONENT_TYPES}


def get_all_projects_components_status() -> dict[int, dict[str, int | None]]:
    """获取所有项目所有组件的状态

    Returns:
        {project_id: {component: pid | None}} 字典
    """
    app_dir = get_app_dir()
    result: dict[int, dict[str, int | None]] = {}

    # 扫描所有组件 PID 文件
    for pid_file in app_dir.glob("tracker-*-*.pid"):
        try:
            name = pid_file.stem  # e.g., "tracker-1-git"
            parts = name.split("-", 1)
            if len(parts) != 2:
                continue
            rest = parts[1]  # e.g., "1-git"
            if "-" not in rest:
                continue  # 这是项目 PID，跳过

            # 解析 project_id 和 component
            id_comp = rest.split("-", 1)
            if len(id_comp) != 2:
                continue
            project_id = int(id_comp[0])
            component = id_comp[1]

            if component not in COMPONENT_TYPES:
                continue

            if project_id not in result:
                result[project_id] = {comp: None for comp in COMPONENT_TYPES}

            pid = int(pid_file.read_text().strip())
            if is_process_running(pid):
                result[project_id][component] = pid
            else:
                pid_file.unlink(missing_ok=True)
        except (ValueError, IndexError):
            pid_file.unlink(missing_ok=True)

    return result
