# Claude Code 项目指南

本文档为 Claude Code 提供项目特定的上下文和指导。

## 项目信息

**名称**：工作日志追踪工具 (Working Journal Tracker)
**语言**：Python 3.12 + Vue 3
**框架**：FastAPI + SQLAlchemy
**数据库**：MySQL 8.0+

## 技术栈

### 后端
- FastAPI - Web 框架
- SQLAlchemy - ORM
- GitPython - Git 操作
- watchdog - 文件监控
- cryptography - 加密
- httpx - HTTP 客户端

### 前端
- Vue 3 - 前端框架
- Vite - 构建工具
- Element Plus - UI 组件库
- ECharts - 图表库
- Pinia - 状态管理

## 核心架构

### 多项目支持
- 单数据库 + `project_id` 字段区分项目数据
- 每个项目独立守护进程，PID 文件格式 `tracker-{project_id}.pid`
- 所有查询接口支持 `project_id` 过滤，`null` 表示全部项目
- 旧数据 `project_id=NULL` 向后兼容，在"全部项目"视图中可见

### 数据模型关系
```
Project (1) ──> (N) WorkSession
Project (1) ──> (N) Activity      （冗余字段避免 JOIN）
Project (1) ──> (N) JournalEntry  （冗余字段避免 JOIN）
WorkSession (1) ──> (N) Activity
```

## 项目结构

```
working-journal-tracker/
├── cli/                    # CLI 命令行工具
│   ├── main.py            # CLI 入口（Click 框架）
│   └── commands/          # 命令实现
│       ├── start.py       # 启动追踪（自动创建 Project）
│       ├── stop.py        # 停止追踪（支持按项目停止）
│       ├── status.py      # 查看状态（显示所有活跃项目）
│       ├── summary.py     # 生成摘要
│       ├── config.py      # 配置管理
│       └── project.py     # 项目管理（add/list/remove）
├── backend/               # FastAPI 后端
│   ├── main.py           # 应用入口
│   ├── database.py       # 数据库连接（SSH 隧道支持）
│   ├── models/           # 数据库模型
│   │   ├── project.py    # 项目模型
│   │   ├── work_session.py
│   │   ├── activity.py
│   │   ├── journal_entry.py
│   │   ├── api_config.py
│   │   ├── ssh_config.py
│   │   └── token_usage.py
│   ├── api/              # API 路由
│   │   ├── projects.py   # 项目 CRUD + 追踪器状态
│   │   ├── activities.py # 活动记录（支持 project_id 过滤）
│   │   ├── journals.py   # 日志查询与生成（支持 project_id）
│   │   ├── stats.py      # 统计信息（支持 project_id）
│   │   ├── git.py        # Git 日志（支持按项目路径读取）
│   │   ├── ai.py         # AI 接口
│   │   └── config.py     # 配置管理
│   └── services/         # 业务逻辑
│       ├── activity_tracker.py  # 活动查询（支持 project_id）
│       ├── journal_generator.py # 日志生成（支持 project_id）
│       ├── ai_service.py       # AI API 调用
│       └── ssh_tunnel.py       # SSH 隧道管理
├── tracker/              # 后台追踪服务
│   ├── daemon.py        # 守护进程（支持 project_id）
│   └── monitors/        # 监控器
│       ├── git_monitor.py   # Git 提交监控（写入 project_id）
│       └── file_monitor.py  # 文件变更监控（写入 project_id）
├── shared/              # 共享代码
│   ├── config.py       # 配置管理（AppConfig 单例）
│   ├── constants.py    # 常量定义
│   └── utils.py        # 工具函数 + 多 PID 管理
├── frontend/           # Vue 3 前端
│   └── src/
│       ├── App.vue         # 主布局（含项目选择器）
│       ├── main.js         # 入口（Pinia + Router + ElementPlus）
│       ├── router/index.js # 路由配置
│       ├── stores/         # Pinia 状态管理
│       │   └── project.js  # 项目 store（currentProjectId）
│       ├── views/          # 页面组件
│       │   ├── Dashboard.vue  # 仪表盘（watch 项目切换）
│       │   ├── Journals.vue   # 日志管理
│       │   ├── Projects.vue   # 项目管理（CRUD + 状态）
│       │   ├── Config.vue     # 系统配置
│       │   └── Stats.vue      # 统计图表
│       ├── components/     # 可复用组件
│       └── api/
│           └── client.js   # Axios API 客户端
└── scripts/            # 工具脚本
    ├── launch.sh       # 一键启动（支持多路径参数）
    ├── migrate_add_project.py  # 多项目迁移脚本
    ├── init_db.py      # 数据库初始化
    └── dev_setup.sh    # 开发环境搭建
```

## 开发约定

### 语言
- 代码注释：中文
- 文档：中文
- 日志消息：中文
- 用户界面：中文
- 变量/函数/类名：英文

### 代码风格
- 遵循 PEP 8
- 使用类型注解
- 函数添加 docstring

### Git 提交
- 使用约定式提交
- 格式：`type: 描述`
- 类型：feat, fix, docs, style, refactor, test, chore

### Web UI 优先原则
- **Web UI 的功能必须 ≥ CLI**，Web 是主要用户界面
- 所有 CLI 能做的操作，Web UI 都应提供对应界面
- Web UI 可以提供 CLI 不具备的增强功能（图表、批量操作、实时刷新等）
- 新增功能时，优先考虑 Web UI 体验，CLI 作为补充
- 前端所有数据视图都必须支持按项目过滤（通过顶部项目选择器）

## 常用命令

### 开发
```bash
# 安装依赖
pip install -e .

# 初始化配置
work-journal config init

# 初始化数据库
python scripts/init_db.py

# 数据库迁移（多项目支持）
python scripts/migrate_add_project.py

# 启动后端
uvicorn backend.main:app --reload

# 启动前端
cd frontend && pnpm dev

# 一键启动（支持多项目）
bash scripts/launch.sh /path/to/project1 /path/to/project2
```

### 使用
```bash
# 项目管理
work-journal project add <name> <path>
work-journal project list
work-journal project remove <name>

# 开始追踪（自动创建项目记录）
work-journal start --path /path/to/project

# 同时追踪多个项目
work-journal start --path /path/to/project1
work-journal start --path /path/to/project2

# 查看所有项目状态
work-journal status

# 停止指定项目
work-journal stop --project <name>

# 停止所有项目
work-journal stop

# 生成摘要
work-journal summary --last-hour

# 启动 Web 面板
work-journal config web
```

## 关键文件

| 文件 | 用途 |
|------|------|
| `shared/config.py` | 配置加载和管理 |
| `shared/utils.py` | 工具函数 + 多 PID 文件管理 |
| `backend/database.py` | 数据库连接 |
| `backend/models/project.py` | 项目模型 |
| `backend/api/projects.py` | 项目 CRUD API + 追踪器状态 |
| `backend/services/ai_service.py` | AI API 调用 |
| `tracker/daemon.py` | 守护进程主逻辑（多项目） |
| `cli/main.py` | CLI 入口 |
| `frontend/src/stores/project.js` | 前端项目状态管理 |

## 配置

配置文件位于 `~/.work-journal/config.yaml`

关键配置项：
- `database` - 数据库连接信息
- `ssh` - SSH 隧道配置
- `tracker` - 追踪器设置
- `ai` - AI 服务配置
- `web` - Web 服务配置

## 注意事项

1. **敏感信息**：API Key 和密码使用 Fernet 加密存储
2. **SSH 隧道**：数据库连接支持通过 SSH 隧道
3. **守护进程**：每个项目独立守护进程，PID 文件 `~/.work-journal/tracker-{project_id}.pid`
4. **批量写入**：文件变更使用批量写入减少数据库操作
5. **向后兼容**：旧数据 `project_id=NULL` 在"全部项目"视图中正常显示
6. **数据库迁移**：新部署需运行 `python scripts/migrate_add_project.py`
