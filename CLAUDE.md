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

## 项目结构

```
working-journal-tracker/
├── cli/                    # CLI 命令行工具
│   ├── main.py            # CLI 入口
│   └── commands/          # 命令实现
├── backend/               # FastAPI 后端
│   ├── main.py           # 应用入口
│   ├── database.py       # 数据库连接
│   ├── models/           # 数据库模型
│   ├── api/              # API 路由
│   └── services/         # 业务逻辑
├── tracker/              # 后台追踪服务
│   ├── daemon.py        # 守护进程
│   └── monitors/        # 监控器
├── shared/              # 共享代码
│   ├── config.py       # 配置管理
│   ├── constants.py    # 常量定义
│   └── utils.py        # 工具函数
├── frontend/           # Vue 3 前端
│   └── src/
│       ├── views/      # 页面组件
│       ├── components/ # 可复用组件
│       └── api/        # API 客户端
└── scripts/            # 工具脚本
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

## 常用命令

### 开发
```bash
# 安装依赖
pip install -e .

# 初始化配置
work-journal config init

# 初始化数据库
python scripts/init_db.py

# 启动后端
uvicorn backend.main:app --reload

# 启动前端
cd frontend && pnpm dev
```

### 使用
```bash
# 开始追踪
work-journal start

# 查看状态
work-journal status

# 生成摘要
work-journal summary --last-hour

# 停止追踪
work-journal stop

# 启动 Web 面板
work-journal config web
```

## 关键文件

| 文件 | 用途 |
|------|------|
| `shared/config.py` | 配置加载和管理 |
| `backend/database.py` | 数据库连接 |
| `backend/services/ai_service.py` | AI API 调用 |
| `tracker/daemon.py` | 守护进程主逻辑 |
| `cli/main.py` | CLI 入口 |

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
3. **守护进程**：追踪器以后台守护进程方式运行
4. **批量写入**：文件变更使用批量写入减少数据库操作
