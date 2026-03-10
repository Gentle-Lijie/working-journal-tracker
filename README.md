# 工作日志追踪工具

[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Vue.js](https://img.shields.io/badge/Vue.js-3.4+-4FC08D?style=flat-square&logo=vue.js&logoColor=white)](https://vuejs.org)
[![MySQL](https://img.shields.io/badge/MySQL-8.0+-4479A1?style=flat-square&logo=mysql&logoColor=white)](https://www.mysql.com)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-macOS%20|%20Linux-lightgrey?style=flat-square)]()

一个基于Python的工作日志自动追踪系统，通过监控Git提交和文件变更，自动记录工作活动并生成智能摘要。

## 功能特性

- 🔍 **自动追踪**：实时监控Git提交和文件变更
- 📝 **智能摘要**：使用AI自动生成工作摘要并分类
- 💻 **CLI工具**：简洁的命令行界面，快速启动/停止追踪
- 🌐 **Web面板**：可视化配置管理和统计查看
- 🔒 **安全连接**：支持SSH隧道连接云端数据库
- 📊 **数据统计**：工作时长、Token使用、工作类型分布

## 快速开始

### 安装

```bash
# 克隆仓库
git clone git@github.com:Gentle-Lijie/working-journal-tracker.git
cd working-journal-tracker

# 安装依赖
pip install -e .

# 初始化配置
work-journal config init

# 编辑配置文件
vim ~/.work-journal/config.yaml

# 初始化数据库
python scripts/init_db.py
```

### 基本使用

```bash
# 开始追踪
work-journal start

# 查看状态
work-journal status

# 生成摘要
work-journal summary --last-hour

# 停止追踪
work-journal stop

# 启动Web面板
work-journal config web
```

## 配置说明

配置文件位于 `~/.work-journal/config.yaml`

```yaml
database:
  host: localhost
  port: 3307
  user: work_journal
  password: ${DB_PASSWORD}  # 从环境变量读取
  database: work_journal

ssh:
  enabled: true
  config_name: default

tracker:
  git_check_interval: 30  # Git检查间隔（秒）
  file_batch_size: 10
  file_batch_interval: 300
  ignored_patterns:
    - "*.pyc"
    - "__pycache__"
    - "node_modules"
    - ".git"

ai:
  default_config: default
  retry_attempts: 3
  timeout: 30

web:
  host: 127.0.0.1
  port: 8000
```

## 技术栈

- **后端**：Python 3.12, FastAPI, SQLAlchemy, GitPython, watchdog
- **前端**：Vue 3, Vite, Pinia, Element Plus, ECharts
- **数据库**：MySQL 8.0+
- **AI集成**：OpenAI兼容API

## 项目结构

```
working-journal-tracker/
├── cli/                    # CLI命令行工具
├── backend/                # FastAPI后端
│   ├── models/            # 数据库模型
│   ├── api/               # API路由
│   └── services/          # 业务逻辑
├── tracker/               # 后台追踪服务
│   └── monitors/          # 监控器
├── shared/                # 共享代码
├── frontend/              # Vue 3前端
└── scripts/               # 工具脚本
```

## 开发

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 运行后端
uvicorn backend.main:app --reload

# 运行前端
cd frontend && pnpm dev
```

## 许可证

MIT License

## 作者

Gentle-Lijie
