"""统计信息API"""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Query

from backend.database import get_db_session
from backend.models.activity import Activity
from backend.models.journal_entry import JournalEntry
from backend.models.token_usage import TokenUsage
from backend.models.work_session import WorkSession

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("/daily")
def daily_stats(date: Optional[str] = Query(None), project_id: Optional[int] = Query(None)):
    """每日统计"""
    if date:
        target_date = datetime.fromisoformat(date).date()
    else:
        target_date = datetime.now().date()

    start = datetime.combine(target_date, datetime.min.time())
    end = datetime.combine(target_date, datetime.max.time())

    with get_db_session() as session:
        # 工作时长
        ws_query = session.query(WorkSession).filter(
            WorkSession.start_time >= start, WorkSession.start_time <= end
        )
        if project_id is not None:
            ws_query = ws_query.filter(WorkSession.project_id == project_id)
        sessions = ws_query.all()

        total_duration = 0
        for s in sessions:
            end_time = s.end_time or datetime.now()
            duration = (end_time - s.start_time).total_seconds()
            total_duration += duration

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
    start = datetime.now() - timedelta(days=days)

    with get_db_session() as session:
        j_query = session.query(JournalEntry).filter(JournalEntry.created_at >= start)
        if project_id is not None:
            j_query = j_query.filter(JournalEntry.project_id == project_id)
        journals = j_query.all()

        distribution = {}
        for j in journals:
            distribution[j.work_type] = distribution.get(j.work_type, 0) + 1

        return {
            "period_days": days,
            "total_journals": len(journals),
            "distribution": distribution,
        }
