"""配置加载和管理"""

import os
from pathlib import Path

import yaml

from shared.constants import (
    CONFIG_FILE,
    DEFAULT_FILE_BATCH_INTERVAL,
    DEFAULT_FILE_BATCH_SIZE,
    DEFAULT_GIT_CHECK_INTERVAL,
    DEFAULT_IGNORED_PATTERNS,
    DEFAULT_WEB_HOST,
    DEFAULT_WEB_PORT,
)
from shared.utils import get_app_dir

# 默认配置模板
DEFAULT_CONFIG = {
    "database": {
        "host": "localhost",
        "port": 3307,
        "user": "work_journal",
        "password": "",
        "database": "work_journal",
    },
    "ssh": {
        "enabled": False,
        "config_name": "default",
    },
    "tracker": {
        "git_check_interval": DEFAULT_GIT_CHECK_INTERVAL,
        "file_batch_size": DEFAULT_FILE_BATCH_SIZE,
        "file_batch_interval": DEFAULT_FILE_BATCH_INTERVAL,
        "ignored_patterns": DEFAULT_IGNORED_PATTERNS,
        "watch_paths": ["."],
    },
    "ai": {
        "default_config": "default",
        "retry_attempts": 3,
        "timeout": 30,
    },
    "web": {
        "host": DEFAULT_WEB_HOST,
        "port": DEFAULT_WEB_PORT,
    },
}


class AppConfig:
    """应用配置管理器"""

    _instance = None
    _config: dict = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._loaded = False
        return cls._instance

    def load(self, config_path: str | None = None):
        """加载配置文件"""
        if config_path:
            path = Path(config_path)
        else:
            path = get_app_dir() / CONFIG_FILE

        # 从默认配置开始
        self._config = _deep_copy_dict(DEFAULT_CONFIG)

        if path.exists():
            with open(path) as f:
                file_config = yaml.safe_load(f) or {}
            _deep_merge(self._config, file_config)

        # 处理环境变量替换
        self._resolve_env_vars(self._config)
        self._loaded = True

    def _resolve_env_vars(self, d: dict):
        """递归替换 ${ENV_VAR} 为环境变量值"""
        for key, value in d.items():
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                env_name = value[2:-1]
                d[key] = os.environ.get(env_name, "")
            elif isinstance(value, dict):
                self._resolve_env_vars(value)

    @property
    def database(self) -> dict:
        self._ensure_loaded()
        return self._config["database"]

    @property
    def ssh(self) -> dict:
        self._ensure_loaded()
        return self._config["ssh"]

    @property
    def tracker(self) -> dict:
        self._ensure_loaded()
        return self._config["tracker"]

    @property
    def ai(self) -> dict:
        self._ensure_loaded()
        return self._config["ai"]

    @property
    def web(self) -> dict:
        self._ensure_loaded()
        return self._config["web"]

    def get(self, *keys, default=None):
        """通过点分路径获取配置值"""
        d = self._config
        for key in keys:
            if isinstance(d, dict) and key in d:
                d = d[key]
            else:
                return default
        return d

    def save(self, config_path: str | None = None):
        """保存配置到文件"""
        if config_path:
            path = Path(config_path)
        else:
            path = get_app_dir() / CONFIG_FILE

        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            yaml.dump(self._config, f, default_flow_style=False, allow_unicode=True)
        os.chmod(path, 0o600)

    def _ensure_loaded(self):
        if not self._loaded:
            self.load()

    def to_dict(self) -> dict:
        self._ensure_loaded()
        return _deep_copy_dict(self._config)


def _deep_copy_dict(d: dict) -> dict:
    result = {}
    for k, v in d.items():
        if isinstance(v, dict):
            result[k] = _deep_copy_dict(v)
        elif isinstance(v, list):
            result[k] = v[:]
        else:
            result[k] = v
    return result


def _deep_merge(base: dict, override: dict):
    """将override深度合并到base中"""
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value


def get_config() -> AppConfig:
    """获取全局配置实例"""
    return AppConfig()
