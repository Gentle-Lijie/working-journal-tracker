# 应用常量

APP_NAME = "work-journal"
APP_DIR = ".work-journal"
CONFIG_FILE = "config.yaml"
PID_FILE = "tracker.pid"
SECRET_KEY_FILE = ".secret_key"
LOG_FILE = "work-journal.log"

# 默认配置值
DEFAULT_GIT_CHECK_INTERVAL = 30  # 秒
DEFAULT_FILE_BATCH_SIZE = 10
DEFAULT_FILE_BATCH_INTERVAL = 300  # 秒
DEFAULT_WEB_HOST = "127.0.0.1"
DEFAULT_WEB_PORT = 8000
DEFAULT_FRONTEND_PORT = 5173

# 活动类型
ACTIVITY_TYPE_GIT_COMMIT = "git_commit"
ACTIVITY_TYPE_FILE_CREATE = "file_create"
ACTIVITY_TYPE_FILE_MODIFY = "file_modify"
ACTIVITY_TYPE_FILE_DELETE = "file_delete"

# 工作类型分类
WORK_TYPES = [
    "开发",    # 编码、调试
    "会议",    # 会议讨论
    "调研",    # 技术调研
    "测试",    # 测试相关
    "文档",    # 文档编写
    "其他",    # 其他
]

# 会话状态
SESSION_STATUS_ACTIVE = "active"
SESSION_STATUS_STOPPED = "stopped"

# AI相关
DEFAULT_AI_TIMEOUT = 30
DEFAULT_AI_RETRY_ATTEMPTS = 3

# 默认忽略的文件模式
DEFAULT_IGNORED_PATTERNS = [
    "*.pyc",
    "__pycache__",
    "node_modules",
    ".git",
    ".idea",
    ".vscode",
    "*.swp",
    "*.swo",
    ".DS_Store",
    "*.log",
    "dist",
    "build",
    "*.egg-info",
    ".env",
]
