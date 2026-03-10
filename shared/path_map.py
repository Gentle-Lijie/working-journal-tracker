"""本地路径映射管理 — 项目名称到本机路径的映射，存储在 ~/.work-journal/path_map.yaml"""

from pathlib import Path

import yaml

from shared.utils import get_app_dir

PATH_MAP_FILE = "path_map.yaml"


class PathMap:
    """本地路径映射管理器"""

    def _file_path(self) -> Path:
        return get_app_dir() / PATH_MAP_FILE

    def _load(self) -> dict[str, str]:
        """读取映射文件"""
        path = self._file_path()
        if not path.exists():
            return {}
        with open(path) as f:
            data = yaml.safe_load(f)
        return data if isinstance(data, dict) else {}

    def _save(self, mapping: dict[str, str]):
        """写入映射文件"""
        path = self._file_path()
        with open(path, "w") as f:
            yaml.dump(mapping, f, default_flow_style=False, allow_unicode=True)

    def get_path(self, project_name: str) -> str | None:
        """获取项目的本地路径"""
        return self._load().get(project_name)

    def set_path(self, project_name: str, path: str):
        """设置项目的本地路径"""
        mapping = self._load()
        mapping[project_name] = str(Path(path).resolve())
        self._save(mapping)

    def remove_path(self, project_name: str):
        """移除项目的本地路径"""
        mapping = self._load()
        if project_name in mapping:
            del mapping[project_name]
            self._save(mapping)

    def get_all(self) -> dict[str, str]:
        """获取所有映射"""
        return self._load()

    def get_name_by_path(self, path: str) -> str | None:
        """根据路径反查项目名称"""
        resolved = str(Path(path).resolve())
        for name, p in self._load().items():
            if str(Path(p).resolve()) == resolved:
                return name
        return None


def get_path_map() -> PathMap:
    """获取路径映射实例"""
    return PathMap()
