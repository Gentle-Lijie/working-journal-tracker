"""SSH配置模型"""

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text

from backend.database import Base


class SshConfig(Base):
    __tablename__ = "ssh_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    host = Column(String(255), nullable=False)
    port = Column(Integer, default=22)
    username = Column(String(100), nullable=False)
    auth_type = Column(String(20), nullable=False, default="password")  # password or key
    encrypted_credential = Column(Text, nullable=False)  # 加密的密码或密钥路径
    remote_host = Column(String(255), default="127.0.0.1")
    remote_port = Column(Integer, default=3306)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def __repr__(self):
        return f"<SshConfig(id={self.id}, name={self.name}, host={self.host})>"
