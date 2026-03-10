"""Token使用记录模型"""

from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer

from backend.database import Base


class TokenUsage(Base):
    __tablename__ = "token_usage"

    id = Column(Integer, primary_key=True, autoincrement=True)
    api_config_id = Column(Integer, ForeignKey("api_configs.id"), nullable=True)
    journal_entry_id = Column(Integer, ForeignKey("journal_entries.id"), nullable=True)
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    cost_estimate = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.now)

    def __repr__(self):
        return f"<TokenUsage(id={self.id}, total={self.total_tokens})>"
