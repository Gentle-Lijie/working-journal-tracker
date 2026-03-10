"""工作会话模型"""

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String

from backend.database import Base
from shared.constants import SESSION_STATUS_ACTIVE


class WorkSession(Base):
    __tablename__ = "work_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    start_time = Column(DateTime, nullable=False, default=datetime.now)
    end_time = Column(DateTime, nullable=True)
    status = Column(String(20), nullable=False, default=SESSION_STATUS_ACTIVE)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def __repr__(self):
        return f"<WorkSession(id={self.id}, status={self.status}, start={self.start_time})>"
