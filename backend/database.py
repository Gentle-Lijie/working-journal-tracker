"""数据库连接管理"""

import logging
from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError, DisconnectionError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

from backend.services.ssh_tunnel import get_tunnel_manager
from shared.config import get_config

logger = logging.getLogger(__name__)

Base = declarative_base()

_engine = None
_SessionLocal = None
_ssh_enabled = None


def _reconnect_database():
    """重新建立数据库连接（用于SSH隧道重连后）"""
    global _engine, _SessionLocal

    # 销毁旧引擎
    if _engine:
        _engine.dispose()
        _engine = None
    if _SessionLocal:
        _SessionLocal = None

    # 重新初始化
    init_database()
    logger.info("数据库连接已重建")


@event.listens_for(Engine, "connect")
def on_connect(dbapi_conn, connection_record):
    """连接建立时的回调"""
    pass


@event.listens_for(Engine, "engine_connect")
def on_engine_connect(conn, branch):
    """引擎连接时的回调，处理SSH隧道断开情况"""
    # 检查是否是SSH隧道模式
    global _ssh_enabled
    if _ssh_enabled is None:
        config = get_config()
        _ssh_enabled = config.ssh.get("enabled", False)

    if not _ssh_enabled:
        return

    # 尝试执行简单查询检测连接
    try:
        cursor = conn.connection.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
    except Exception as e:
        logger.warning(f"数据库连接检测失败，尝试重连SSH隧道: {e}")
        tunnel_manager = get_tunnel_manager()
        result = tunnel_manager.ensure_connection()
        if result:
            logger.info("SSH隧道重连成功，重建数据库连接...")
            _reconnect_database()
            raise DisconnectionError("数据库连接已重置")  # 触发连接池重建


def init_database(force_rebuild: bool = False):
    """初始化数据库连接"""
    global _engine, _SessionLocal, _ssh_enabled

    config = get_config()
    db_config = config.database
    ssh_config = config.ssh
    _ssh_enabled = ssh_config.get("enabled", False)

    # 如果启用SSH隧道，先建立隧道
    if _ssh_enabled:
        tunnel_manager = get_tunnel_manager()
        host, port = tunnel_manager.start(ssh_config)
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
        pool_pre_ping=True,  # 连接前检测
        pool_recycle=3600,   # 1小时回收连接
        echo=False,
        pool_size=5,
        max_overflow=10,
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
    """数据库会话上下文管理器（带自动重连）"""
    max_retries = 2
    for attempt in range(max_retries):
        session = get_session()
        try:
            yield session
            session.commit()
            return
        except OperationalError as e:
            session.rollback()
            session.close()

            if attempt < max_retries - 1 and "Lost connection" in str(e):
                logger.warning(f"检测到连接丢失，尝试重连 ({attempt + 1}/{max_retries})...")
                # 触发SSH隧道重连检查
                if _ssh_enabled:
                    tunnel_manager = get_tunnel_manager()
                    tunnel_manager.ensure_connection()
                    # 重建数据库连接
                    _reconnect_database()
                continue
            raise
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
        project,
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
