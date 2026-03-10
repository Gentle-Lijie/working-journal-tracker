"""统计信息API"""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Query

from backend.database import get_db_session
from backend.models.activity import Activity
from backend.models.journal_entry import JournalEntry
from backend.models.token_usage import TokenUsage
from backend.models.work_session import WorkSession
from shared.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("/daily")
def daily_stats(date: Optional[str] = Query(None), project_id: Optional[int] = Query(None)):
    """每日统计"""
    logger.info(f"查询每日统计: date={date}, project_id={project_id}")
    if date:
        target_date = datetime.fromisoformat(date).date()
    else:
        target_date = datetime.now().date()

    start = datetime.combine(target_date, datetime.min.time())
    end = datetime.combine(target_date, datetime.max.time())

    with get_db_session() as session:
        # 工作时长（按项目分别合并重叠时间段）
        ws_query = session.query(WorkSession).filter(
            WorkSession.start_time >= start, WorkSession.start_time <= end
        )
        if project_id is not None:
            ws_query = ws_query.filter(WorkSession.project_id == project_id)
        sessions = ws_query.all()

        # 按项目分组计算时长
        project_intervals = {}
        for s in sessions:
            pid = s.project_id or 0  # None 视为 0
            end_time = s.end_time or datetime.now()
            if pid not in project_intervals:
                project_intervals[pid] = []
            project_intervals[pid].append((s.start_time, end_time))

        # 对每个项目的时间段进行合并，然后求和
        total_duration = 0
        for pid, intervals in project_intervals.items():
            # 按开始时间排序
            intervals.sort(key=lambda x: x[0])

            # 合并重叠区间
            merged = []
            for interval in intervals:
                if not merged:
                    merged.append(list(interval))
                else:
                    if interval[0] <= merged[-1][1]:  # 有重叠
                        merged[-1][1] = max(merged[-1][1], interval[1])
                    else:
                        merged.append(list(interval))

            # 累加该项目的工作时长
            project_duration = sum((end - start).total_seconds() for start, end in merged)
            total_duration += project_duration

        # 活动统计
        act_query = session.query(Activity).filter(
            Activity.timestamp >= start, Activity.timestamp <= end
        )
        if project_id is not None:
            act_query = act_query.filter(Activity.project_id == project_id)
        activities = act_query.all()

        git_commits = sum(1 for a in activities if a.activity_type == "git_commit")
        file_changes = len(activities) - git_commits

        # 日志条目
        j_query = session.query(JournalEntry).filter(
            JournalEntry.start_time >= start, JournalEntry.end_time <= end
        )
        if project_id is not None:
            j_query = j_query.filter(JournalEntry.project_id == project_id)
        journals = j_query.all()

        work_type_dist = {}
        for j in journals:
            work_type_dist[j.work_type] = work_type_dist.get(j.work_type, 0) + 1

        logger.info(f"每日统计结果: date={target_date.isoformat()}, sessions={len(sessions)}, activities={len(activities)}, journals={len(journals)}")
        return {
            "date": target_date.isoformat(),
            "work_duration": int(total_duration),
            "sessions": len(sessions),
            "activities": {
                "total": len(activities),
                "git_commits": git_commits,
                "file_changes": file_changes,
            },
            "journals": len(journals),
            "work_type_distribution": work_type_dist,
        }


@router.get("/tokens")
def token_stats(days: int = Query(7, le=90), project_id: Optional[int] = Query(None)):
    """Token使用统计"""
    logger.info(f"查询Token使用统计: days={days}, project_id={project_id}")
    start = datetime.now() - timedelta(days=days)

    with get_db_session() as session:
        usages = session.query(TokenUsage).filter(TokenUsage.created_at >= start).all()

        total_tokens = sum(u.total_tokens for u in usages)
        total_cost = sum(u.cost_estimate for u in usages)

        # 按日期分组
        daily_usage = {}
        for u in usages:
            date_key = u.created_at.date().isoformat()
            if date_key not in daily_usage:
                daily_usage[date_key] = {"tokens": 0, "cost": 0, "count": 0}
            daily_usage[date_key]["tokens"] += u.total_tokens
            daily_usage[date_key]["cost"] += u.cost_estimate
            daily_usage[date_key]["count"] += 1

        logger.info(f"Token统计结果: total_tokens={total_tokens}, total_cost={total_cost:.4f}, total_calls={len(usages)}")
        return {
            "period_days": days,
            "total_tokens": total_tokens,
            "total_cost": round(total_cost, 4),
            "total_calls": len(usages),
            "daily_usage": daily_usage,
        }


@router.get("/work-types")
def work_type_stats(days: int = Query(30, le=365), project_id: Optional[int] = Query(None)):
    """工作类型分布统计"""
    logger.info(f"查询工作类型分布统计: days={days}, project_id={project_id}")
    start = datetime.now() - timedelta(days=days)

    with get_db_session() as session:
        j_query = session.query(JournalEntry).filter(JournalEntry.created_at >= start)
        if project_id is not None:
            j_query = j_query.filter(JournalEntry.project_id == project_id)
        journals = j_query.all()

        distribution = {}
        for j in journals:
            distribution[j.work_type] = distribution.get(j.work_type, 0) + 1

        logger.info(f"工作类型统计结果: total_journals={len(journals)}, types={len(distribution)}")
        return {
            "period_days": days,
            "total_journals": len(journals),
            "distribution": distribution,
        }
