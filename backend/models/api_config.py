"""API配置模型"""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text

from backend.database import Base


class ApiConfig(Base):
    __tablename__ = "api_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    api_key = Column(Text, nullable=False)  # 加密存储
    base_url = Column(String(500), nullable=False)
    model = Column(String(100), nullable=False)
    endpoint = Column(String(200), nullable=True, default="/v1/chat/completions")
    is_active = Column(Boolean, default=False)
    test_status = Column(String(20), nullable=True)  # success, failed, untested
    test_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def __repr__(self):
        return f"<ApiConfig(id={self.id}, name={self.name}, model={self.model})>"
