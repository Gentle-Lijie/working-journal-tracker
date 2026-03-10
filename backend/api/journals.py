"""日志查询API"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

from backend.database import get_db_session
from backend.models.journal_entry import JournalEntry
from backend.services.journal_generator import JournalGenerator
from shared.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/journals", tags=["journals"])
generator = JournalGenerator()


class JournalGenerateRequest(BaseModel):
    start_time: str
    end_time: str
    session_id: int | None = None
    project_id: int | None = None


class JournalResponse(BaseModel):
    id: int
    session_id: int | None
    start_time: datetime
    end_time: datetime
    work_type: str
    summary: str
    ai_model: str | None
    tokens_used: int

    class Config:
        from_attributes = True


@router.get("")
def list_journals(
    from_date: Optional[str] = Query(None, alias="from"),
    to_date: Optional[str] = Query(None, alias="to"),
    work_type: Optional[str] = Query(None),
    project_id: Optional[int] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
):
    """查询日志条目"""
    logger.info(f"查询日志条目: from={from_date}, to={to_date}, work_type={work_type}, project_id={project_id}, limit={limit}, offset={offset}")
    with get_db_session() as session:
        query = session.query(JournalEntry)

        if from_date:
            from_dt = datetime.fromisoformat(from_date)
            query = query.filter(JournalEntry.start_time >= from_dt)
        if to_date:
            to_dt = datetime.fromisoformat(to_date)
            query = query.filter(JournalEntry.end_time <= to_dt)
        if work_type:
            query = query.filter(JournalEntry.work_type == work_type)
        if project_id is not None:
            query = query.filter(JournalEntry.project_id == project_id)

        journals = query.order_by(JournalEntry.start_time.desc()).offset(offset).limit(limit).all()

        logger.info(f"返回 {len(journals)} 条日志条目")
        return [
            {
                "id": j.id,
                "session_id": j.session_id,
                "project_id": j.project_id,
                "start_time": j.start_time.isoformat(),
                "end_time": j.end_time.isoformat(),
                "work_type": j.work_type,
                "summary": j.summary,
                "ai_model": j.ai_model,
                "tokens_used": j.tokens_used,
            }
            for j in journals
        ]


@router.post("/generate")
def generate_journal(data: JournalGenerateRequest):
    """生成日志条目"""
    logger.info(f"生成日志条目: start_time={data.start_time}, end_time={data.end_time}, session_id={data.session_id}, project_id={data.project_id}")
    start_time = datetime.fromisoformat(data.start_time)
    end_time = datetime.fromisoformat(data.end_time)

    entry = generator.generate(
        start_time=start_time,
        end_time=end_time,
        session_id=data.session_id,
        project_id=data.project_id,
    )

    if not entry:
        logger.warning(f"日志生成失败: 没有找到活动记录 (start_time={data.start_time}, end_time={data.end_time})")
        return {"success": False, "message": "没有找到活动记录"}

    logger.info(f"日志生成成功: id={entry.id}, work_type={entry.work_type}, tokens_used={entry.tokens_used}")
    return {
        "success": True,
        "journal": {
            "id": entry.id,
            "work_type": entry.work_type,
            "summary": entry.summary,
            "tokens_used": entry.tokens_used,
        },
    }
