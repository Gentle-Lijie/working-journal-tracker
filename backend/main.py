"""FastAPI应用入口"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api import activities, ai, config, filesystem, git, journals, logs, projects, stats
from backend.database import init_database
from shared.logging_config import setup_logging, get_logger

# 配置日志
setup_logging()
logger = get_logger(__name__)

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
