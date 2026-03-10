# Agents 文档

本文档记录项目中使用的 AI Agent 开发模式和最佳实践。

## 项目概述

工作日志追踪工具是一个基于 Python 的自动追踪系统，通过监控 Git 提交和文件变更，自动记录工作活动并生成智能摘要。支持多项目同时追踪，提供 CLI 和 Web 双界面。

## Agent 使用场景

### 1. 代码探索 Agent

用于快速理解代码库结构和查找特定代码：

```
探索 backend/services 目录，了解 AI 服务的实现方式
查找所有使用 project_id 过滤的 API 端点
```

### 2. 研究 Agent

用于深入研究技术问题：

```
研究如何实现 SSH 隧道连接 MySQL 数据库
分析多项目守护进程的 PID 管理策略
```

### 3. 通用 Agent

用于复杂的多步骤任务：

```
实现一个新的 API 端点，包括数据库模型、服务层和路由
添加新的前端页面，包括路由注册、API 调用和状态管理
```

## 核心架构

### 多项目支持

```
Project (1) ──> (N) WorkSession
Project (1) ──> (N) Activity      （冗余字段避免 JOIN）
Project (1) ──> (N) JournalEntry  （冗余字段避免 JOIN）
WorkSession (1) ──> (N) Activity
```

- 单数据库 + `project_id` 字段区分项目数据
- 每个项目独立守护进程，PID 文件 `tracker-{project_id}.pid`
- 所有查询接口支持 `project_id` 过滤，`null` 表示全部项目

### 日志系统

- 统一日志配置：`shared/logging_config.py`
- 格式：`时间 - 模块 - 级别 - [文件:行号] - 消息`
- 后端所有 API 端点记录请求参数和返回数量
- 前端 axios 拦截器记录请求/响应
- Web 端系统日志页面实时查看

### 项目结构

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
│   │   ├── journals.py   # 日志查询与生成
│   │   ├── stats.py      # 统计信息
│   │   ├── git.py        # Git 日志（按项目路径读取）
│   │   ├── logs.py       # 系统日志 API
│   │   ├── ai.py         # AI 接口
│   │   └── config.py     # 配置管理
│   └── services/         # 业务逻辑
│       ├── activity_tracker.py  # 活动查询
│       ├── journal_generator.py # 日志生成
│       ├── ai_service.py       # AI API 调用
│       └── ssh_tunnel.py       # SSH 隧道管理
├── tracker/              # 后台追踪服务
│   ├── daemon.py        # 守护进程（支持 project_id）
│   └── monitors/        # 监控器
│       ├── git_monitor.py   # Git 提交监控
│       └── file_monitor.py  # 文件变更监控
├── shared/              # 共享代码
│   ├── config.py       # 配置管理（AppConfig 单例）
│   ├── constants.py    # 常量定义
│   ├── utils.py        # 工具函数 + 多 PID 管理
│   └── logging_config.py # 统一日志配置
├── frontend/           # Vue 3 前端
│   └── src/
│       ├── App.vue         # 主布局（含项目选择器）
│       ├── main.js         # 入口
│       ├── router/index.js # 路由配置
│       ├── stores/         # Pinia 状态管理
│       │   └── project.js  # 项目 store
│       ├── views/          # 页面组件
│       │   ├── Dashboard.vue  # 仪表盘
│       │   ├── Journals.vue   # 工作日志
│       │   ├── Projects.vue   # 项目管理
│       │   ├── Config.vue     # 系统配置
│       │   ├── Stats.vue      # 统计图表
│       │   └── Logs.vue       # 系统日志
│       └── api/
│           └── client.js   # API 客户端（含日志拦截器）
└── scripts/            # 工具脚本
    ├── launch.sh       # 一键启动（支持多路径）
    ├── migrate_add_project.py  # 多项目迁移
    ├── init_db.py      # 数据库初始化
    └── dev_setup.sh    # 开发环境搭建
```

## 开发约定

### 代码风格

- 所有注释和文档使用中文
- 变量名、函数名、类名使用英文
- 遵循 PEP 8 规范
- 使用类型注解
- 函数添加 docstring

### 数据库

- 使用 SQLAlchemy ORM
- 新表/字段通过迁移脚本添加（`scripts/migrate_*.py`）
- 敏感信息使用 Fernet 加密
- 所有数据表支持 `project_id` 字段过滤

### API

- RESTful 风格
- 使用 Pydantic 模型验证
- 所有端点添加详细日志（请求参数 + 返回数量）
- 查询接口统一支持 `project_id` 过滤参数

### 前端

- Vue 3 Composition API
- Element Plus UI 组件
- ECharts 图表
- Pinia 状态管理
- 所有数据视图 watch 项目切换自动刷新

### Web UI 优先原则

- Web UI 的功能必须 ≥ CLI
- 新增功能优先考虑 Web UI 体验
- CLI 作为补充和自动化接口

### Git 提交

- 使用约定式提交
- 格式：`type: 描述`
- 类型：feat, fix, docs, style, refactor, test, chore

## 常见任务

### 添加新的 API 端点

1. 在 `backend/models/` 创建数据库模型（含 `project_id` 字段）
2. 在 `backend/services/` 创建服务层（支持 `project_id` 过滤）
3. 在 `backend/api/` 创建路由（添加日志、支持 `project_id` 参数）
4. 在 `backend/main.py` 注册路由
5. 在 `frontend/src/api/client.js` 添加 API 调用

### 添加新的 CLI 命令

1. 在 `cli/commands/` 创建命令模块
2. 在 `cli/main.py` 注册命令

### 添加前端页面

1. 在 `frontend/src/views/` 创建页面组件
2. 在 `frontend/src/router/index.js` 添加路由
3. 在 `frontend/src/App.vue` 添加导航菜单项
4. 在 `frontend/src/api/client.js` 添加 API 调用
5. 使用 `useProjectStore()` 支持项目过滤
6. 添加 `watch(() => projectStore.currentProjectId, loadData)` 响应项目切换

### 添加日志

- 后端：使用 `from shared.logging_config import get_logger`，`logger = get_logger(__name__)`
- 前端：axios 拦截器自动记录，组件内使用 `console.log/error`

## 故障排除

### 数据库连接问题

1. 检查配置文件 `~/.work-journal/config.yaml`
2. 确认 SSH 隧道是否正常运行
3. 检查数据库凭据
4. 查看系统日志：Web 面板 → 系统日志 或 `~/.work-journal/work-journal.log`

### 追踪器不工作

1. 检查守护进程状态：`work-journal status`
2. 查看日志：`~/.work-journal/work-journal.log`
3. 确认项目是 Git 仓库
4. 检查 PID 文件：`ls ~/.work-journal/tracker-*.pid`

### 多项目问题

1. 确认项目路径使用绝对路径
2. 检查是否有重复的项目名称或路径：`work-journal project list`
3. 每个项目的 PID 文件独立：`tracker-{project_id}.pid`
4. 停止指定项目：`work-journal stop --project <name>`

### AI 服务问题

1. 检查 API 配置是否正确（Web 面板 → 配置 → AI 服务）
2. 测试 API 连接
3. 查看系统日志中的错误信息
