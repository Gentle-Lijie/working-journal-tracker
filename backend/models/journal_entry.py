"""日志条目模型"""

from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text

from backend.database import Base


class JournalEntry(Base):
    __tablename__ = "journal_entries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True)
    session_id = Column(Integer, nullable=True)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    work_type = Column(String(20), nullable=False, default="其他")
    summary = Column(Text, nullable=False)
    ai_model = Column(String(100), nullable=True)
    tokens_used = Column(Integer, nullable=True, default=0)
    cost_estimate = Column(Float, nullable=True, default=0.0)
    created_at = Column(DateTime, default=datetime.now)

    def __repr__(self):
        return f"<JournalEntry(id={self.id}, type={self.work_type}, start={self.start_time})>"
