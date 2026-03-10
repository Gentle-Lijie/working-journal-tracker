"""活动追踪服务"""

import logging
from datetime import datetime

from backend.database import get_db_session
from backend.models.activity import Activity

logger = logging.getLogger(__name__)


class ActivityTracker:
    """活动追踪服务"""

    def get_activities(
        self,
        session_id: int | None = None,
        project_id: int | None = None,
        from_time: datetime | None = None,
        to_time: datetime | None = None,
        activity_type: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Activity]:
        """查询活动记录"""
        with get_db_session() as db_session:
            query = db_session.query(Activity)

            if session_id:
                query = query.filter(Activity.session_id == session_id)
            if project_id is not None:
                query = query.filter(Activity.project_id == project_id)
            if from_time:
                query = query.filter(Activity.timestamp >= from_time)
            if to_time:
                query = query.filter(Activity.timestamp <= to_time)
            if activity_type:
                query = query.filter(Activity.activity_type == activity_type)

            activities = (
                query.order_by(Activity.timestamp.desc()).offset(offset).limit(limit).all()
            )
            # 确保在session关闭前将所有属性加载到内存
            for a in activities:
                _ = a.id, a.session_id, a.activity_type, a.timestamp, a.description, a.metadata_json
            db_session.expunge_all()
            return activities

    def add_activity(
        self,
        session_id: int,
        activity_type: str,
        description: str,
        metadata: dict | None = None,
    ) -> Activity:
        """添加活动记录"""
        with get_db_session() as db_session:
            activity = Activity(
                session_id=session_id,
                activity_type=activity_type,
                timestamp=datetime.now(),
                description=description,
                metadata_json=metadata,
            )
            db_session.add(activity)
            db_session.flush()
            _ = activity.id
            db_session.expunge(activity)
            return activity

    def count_activities(
        self,
        session_id: int | None = None,
        from_time: datetime | None = None,
        to_time: datetime | None = None,
    ) -> dict:
        """统计活动数量"""
        with get_db_session() as db_session:
            query = db_session.query(Activity)

            if session_id:
                query = query.filter(Activity.session_id == session_id)
            if from_time:
                query = query.filter(Activity.timestamp >= from_time)
            if to_time:
                query = query.filter(Activity.timestamp <= to_time)

            total = query.count()
            git_commits = query.filter(Activity.activity_type == "git_commit").count()

            return {
                "total": total,
                "git_commits": git_commits,
                "file_changes": total - git_commits,
            }
