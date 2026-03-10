"""通用工具函数"""

import os
from datetime import datetime
from pathlib import Path

from cryptography.fernet import Fernet

from shared.constants import APP_DIR, SECRET_KEY_FILE


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
    os.chmod(key_path, 0o600)
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
            os.kill(pid, 0)
            return pid
        except (ValueError, ProcessLookupError, PermissionError):
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
            project_id = int(pid_file.stem.split("-", 1)[1])
            pid = int(pid_file.read_text().strip())
            os.kill(pid, 0)
            result[project_id] = pid
        except (ValueError, ProcessLookupError, PermissionError, IndexError):
            pid_file.unlink(missing_ok=True)
    return result
