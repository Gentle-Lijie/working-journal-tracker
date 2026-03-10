"""数据库连接管理"""

import logging
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

from backend.services.ssh_tunnel import get_tunnel_manager
from shared.config import get_config

logger = logging.getLogger(__name__)

Base = declarative_base()

_engine = None
_SessionLocal = None


def init_database():
    """初始化数据库连接"""
    global _engine, _SessionLocal

    config = get_config()
    db_config = config.database
    ssh_config = config.ssh

    # 如果启用SSH隧道，先建立隧道
    if ssh_config.get("enabled"):
        # 这里需要从数据库加载SSH配置，暂时使用配置文件中的值
        # 实际使用时需要先初始化数据库，然后从api_configs表读取
        tunnel_manager = get_tunnel_manager()
        # 简化版：直接使用配置文件中的数据库配置
        host = db_config["host"]
        port = db_config["port"]
    else:
        host = db_config["host"]
        port = db_config["port"]

    # 构建数据库URL
    db_url = (
        f"mysql+pymysql://{db_config['user']}:{db_config['password']}"
        f"@{host}:{port}/{db_config['database']}"
        "?charset=utf8mb4"
    )

    _engine = create_engine(
        db_url,
        pool_pre_ping=True,
        pool_recycle=3600,
        echo=False,
    )

    _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
    logger.info(f"数据库连接已初始化: {host}:{port}/{db_config['database']}")


def get_engine():
    """获取数据库引擎"""
    if _engine is None:
        init_database()
    return _engine


def get_session() -> Session:
    """获取数据库会话"""
    if _SessionLocal is None:
        init_database()
    return _SessionLocal()


@contextmanager
def get_db_session():
    """数据库会话上下文管理器"""
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def create_tables():
    """创建所有表"""
    # 导入所有模型以确保它们被注册
    from backend.models import (  # noqa: F401
        activity,
        api_config,
        journal_entry,
        ssh_config,
        token_usage,
        work_session,
    )

    Base.metadata.create_all(bind=get_engine())
    logger.info("数据库表已创建")


def drop_tables():
    """删除所有表（谨慎使用）"""
    Base.metadata.drop_all(bind=get_engine())
    logger.warning("数据库表已删除")
