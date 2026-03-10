"""活动记录模型"""

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.types import JSON

from backend.database import Base


class Activity(Base):
    __tablename__ = "activities"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("work_sessions.id"), nullable=False)
    activity_type = Column(String(50), nullable=False)  # git_commit, file_create, file_modify, file_delete
    timestamp = Column(DateTime, nullable=False, default=datetime.now)
    description = Column(Text, nullable=True)
    metadata_json = Column("metadata", JSON, nullable=True)  # 额外信息（commit hash, file path等）
    created_at = Column(DateTime, default=datetime.now)

    def __repr__(self):
        return f"<Activity(id={self.id}, type={self.activity_type}, time={self.timestamp})>"
