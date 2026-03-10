"""活动记录API"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

from backend.services.activity_tracker import ActivityTracker

router = APIRouter(prefix="/api/activities", tags=["activities"])
tracker = ActivityTracker()


class ActivityCreate(BaseModel):
    session_id: int
    activity_type: str
    description: str
    metadata: dict | None = None


class ActivityResponse(BaseModel):
    id: int
    session_id: int
    activity_type: str
    timestamp: datetime
    description: str | None
    metadata: dict | None

    class Config:
        from_attributes = True


@router.get("")
def list_activities(
    session_id: Optional[int] = Query(None),
    project_id: Optional[int] = Query(None),
    from_time: Optional[str] = Query(None, alias="from"),
    to_time: Optional[str] = Query(None, alias="to"),
    activity_type: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0),
):
    """查询活动记录"""
    from_dt = datetime.fromisoformat(from_time) if from_time else None
    to_dt = datetime.fromisoformat(to_time) if to_time else None

    activities = tracker.get_activities(
        session_id=session_id,
        project_id=project_id,
        from_time=from_dt,
        to_time=to_dt,
        activity_type=activity_type,
        limit=limit,
        offset=offset,
    )

    return [
        {
            "id": a.id,
            "session_id": a.session_id,
            "project_id": a.project_id,
            "activity_type": a.activity_type,
            "timestamp": a.timestamp.isoformat(),
            "description": a.description,
            "metadata": a.metadata_json,
        }
        for a in activities
    ]


@router.post("")
def create_activity(data: ActivityCreate):
    """创建活动记录"""
    activity = tracker.add_activity(
        session_id=data.session_id,
        activity_type=data.activity_type,
        description=data.description,
        metadata=data.metadata,
    )
    return {"id": activity.id, "message": "活动记录已创建"}
