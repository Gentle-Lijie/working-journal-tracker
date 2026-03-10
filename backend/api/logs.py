"""系统日志API"""

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Query

from shared.constants import LOG_FILE
from shared.logging_config import get_logger
from shared.utils import get_app_dir

router = APIRouter(prefix="/api/logs", tags=["logs"])
logger = get_logger(__name__)


@router.get("")
def get_logs(
    lines: int = Query(200, le=2000),
    level: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
):
    """获取系统日志"""
    logger.info(f"查询系统日志: lines={lines}, level={level}, keyword={keyword}")
    log_path = get_app_dir() / LOG_FILE

    if not log_path.exists():
        logger.warning("日志文件不存在")
        return {"logs": [], "total": 0}

    # 读取日志文件最后N行
    all_lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines

    # 解析日志行
    logs = []
    for line in recent_lines:
        if not line.strip():
            continue

        entry = _parse_log_line(line)

        # 按级别过滤
        if level and entry["level"] != level.upper():
            continue

        # 按关键词过滤
        if keyword and keyword.lower() not in entry["message"].lower():
            continue

        logs.append(entry)

    logger.info(f"返回 {len(logs)} 条日志")
    return {"logs": logs, "total": len(logs)}


@router.get("/tail")
def tail_logs(lines: int = Query(50, le=500)):
    """获取最新日志（用于实时刷新）"""
    log_path = get_app_dir() / LOG_FILE

    if not log_path.exists():
        return {"logs": []}

    all_lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines

    logs = [_parse_log_line(line) for line in recent_lines if line.strip()]
    return {"logs": logs}


def _parse_log_line(line: str) -> dict:
    """解析单行日志"""
    # 格式: 2026-03-10 15:44:17 - module - LEVEL - [file:line] - message
    parts = line.split(" - ", 4)
    if len(parts) >= 5:
        return {
            "timestamp": parts[0].strip(),
            "module": parts[1].strip(),
            "level": parts[2].strip(),
            "location": parts[3].strip(),
            "message": parts[4].strip(),
        }
    elif len(parts) >= 4:
        return {
            "timestamp": parts[0].strip(),
            "module": parts[1].strip(),
            "level": parts[2].strip(),
            "location": "",
            "message": parts[3].strip(),
        }
    else:
        return {
            "timestamp": "",
            "module": "",
            "level": "INFO",
            "location": "",
            "message": line.strip(),
        }
