# Agents 文档

本文档记录项目中使用的 AI Agent 开发模式和最佳实践。

## 项目概述

工作日志追踪工具是一个基于 Python 的自动追踪系统，通过监控 Git 提交和文件变更，自动记录工作活动并生成智能摘要。

## Agent 使用场景

### 1. 代码探索 Agent

用于快速理解代码库结构和查找特定代码：

```
探索 backend/services 目录，了解 AI 服务的实现方式
```

### 2. 研究Agent

用于深入研究技术问题：

```
研究如何实现 SSH 隧道连接 MySQL 数据库
```

### 3. 通用 Agent

用于复杂的多步骤任务：

```
实现一个新的 API 端点，包括数据库模型、服务层和路由
```

## 项目架构

```
├── cli/                 # CLI 命令行工具
├── backend/             # FastAPI 后端
│   ├── models/         # SQLAlchemy 数据库模型
│   ├── api/            # API 路由
│   └── services/       # 业务逻辑服务
├── tracker/            # 后台追踪服务
│   └── monitors/       # Git 和文件监控器
├── shared/             # 共享代码
├── frontend/           # Vue 3 前端
└── scripts/            # 工具脚本
```

## 开发约定

### 代码风格

- 所有注释和文档使用中文
- 变量名、函数名、类名使用英文
- 遵循 PEP 8 规范

### 数据库

- 使用 SQLAlchemy ORM
- 迁移使用 Alembic（如需要）
- 敏感信息使用 Fernet 加密

### API

- RESTful 风格
- 使用 Pydantic 模型验证
- 统一的错误响应格式

### 前端

- Vue 3 Composition API
- Element Plus UI 组件
- ECharts 图表

## 常见任务

### 添加新的 API 端点

1. 在 `backend/models/` 创建数据库模型
2. 在 `backend/services/` 创建服务层
3. 在 `backend/api/` 创建路由
4. 在 `backend/main.py` 注册路由

### 添加新的 CLI 命令

1. 在 `cli/commands/` 创建命令模块
2. 在 `cli/main.py` 注册命令

### 添加前端页面

1. 在 `frontend/src/views/` 创建页面组件
2. 在 `frontend/src/router/index.js` 添加路由
3. 在 `frontend/src/api/client.js` 添加 API 调用

## 故障排除

### 数据库连接问题

1. 检查配置文件 `~/.work-journal/config.yaml`
2. 确认 SSH 隧道是否正常运行
3. 检查数据库凭据

### 追踪器不工作

1. 检查守护进程状态：`work-journal status`
2. 查看日志：`~/.work-journal/work-journal.log`
3. 确认项目是 Git 仓库

### AI 服务问题

1. 检查 API 配置是否正确
2. 测试 API 连接
3. 查看错误日志
