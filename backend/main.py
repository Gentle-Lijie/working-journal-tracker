"""FastAPI应用入口"""

import atexit
import signal
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api import activities, ai, config, filesystem, git, journals, logs, projects, stats
from backend.database import init_database
from backend.services.ssh_tunnel import cleanup_tunnel, get_tunnel_manager
from shared.logging_config import setup_logging, get_logger

# 配置日志
setup_logging()
logger = get_logger(__name__)


def graceful_shutdown(signum=None, frame=None):
    """优雅关闭：清理所有资源"""
    logger.info("正在关闭应用...")
    try:
        # 停止 SSH 隧道
        cleanup_tunnel()
        logger.info("SSH 隧道已清理")
    except Exception as e:
        logger.warning(f"清理 SSH 隧道时出错: {e}")
    logger.info("应用已关闭")
    sys.exit(0)


# 注册信号处理
signal.signal(signal.SIGINT, graceful_shutdown)
signal.signal(signal.SIGTERM, graceful_shutdown)
atexit.register(graceful_shutdown)

# 创建FastAPI应用
app = FastAPI(
    title="工作日志追踪API",
    description="自动追踪工作活动，生成智能摘要",
    version="0.1.0",
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(projects.router)
app.include_router(activities.router)
app.include_router(journals.router)
app.include_router(config.router)
app.include_router(ai.router)
app.include_router(stats.router)
app.include_router(git.router)
app.include_router(logs.router)
app.include_router(filesystem.router)


@app.on_event("startup")
async def startup_event():
    """应用启动时初始化数据库"""
    logger.info("正在初始化数据库连接...")
    try:
        init_database()
        logger.info("数据库连接已初始化")
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时清理资源"""
    logger.info("正在关闭应用...")
    try:
        cleanup_tunnel()
        logger.info("SSH 隧道已清理")
    except Exception as e:
        logger.warning(f"清理 SSH 隧道时出错: {e}")


@app.get("/")
def root():
    """根路径"""
    return {
        "name": "工作日志追踪API",
        "version": "0.1.0",
        "docs": "/docs",
    }


@app.get("/health")
def health():
    """健康检查"""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
