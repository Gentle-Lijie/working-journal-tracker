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
