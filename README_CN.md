# AI Memory MCP - 项目本地记忆服务器

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12+-green.svg)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/MCP-FastMCP-orange.svg)](https://modelcontextprotocol.io/)
[![Version](https://img.shields.io/badge/version-v1.0.0-brightgreen.svg)](VERSION)

**[English Version](README.md)**

---

## 项目简介

**AI Memory MCP** 是一个专为 Claude Code 设计的持久化项目记忆 MCP 服务器。它让 AI 能够跨会话记住你的项目开发历程，包括功能规划、Bug 修复、开发笔记、代码规范等关键信息，成为你开发过程中的"第二大脑"。

### 核心特色

| 特性 | 说明 |
|------|------|
| 结构化记忆 | 将项目信息分类为 Features、Fixes、Notes、Standards 四大维度 |
| 智能关联 | 支持条目间相互关联，构建完整的项目知识图谱 |
| 标签系统 | 强大的标签管理能力，支持跨维度查询和经验复用 |
| 三层架构 | MCP Server、FastAPI Server、Business Server 分离，易于扩展 |
| 全异步设计 | 高性能异步架构，支持高并发访问 |
| Docker 部署 | 一键容器化部署，数据持久化存储 |

---

## 系统架构

项目采用三层架构设计，各层职责明确：

```
┌─────────────────┐     ┌─────────────────┐
│   MCP Clients   │     │   Web Clients   │
│  (Claude Code)  │     │   (Browser)     │
└────────┬────────┘     └────────┬────────┘
         │                       │
         ▼                       ▼
┌─────────────────┐     ┌─────────────────┐
│   MCP Server    │     │  FastAPI Server │
│   (mcp_server)  │     │   (rest_api)    │
│  - SSE/HTTP     │     │  - RESTful API  │
└────────┬────────┘     └────────┬────────┘
         │                       │
         └───────────┬───────────┘
                     ▼
         ┌─────────────────────┐
         │   Business Server   │
         │   (business)        │
         │  - 核心业务逻辑     │
         │  - 数据存储管理     │
         │  - 标签系统         │
         └─────────────────────┘
```

### 目录结构

```
ai_memory_mcp/
├── src/
│   ├── business/      # 业务逻辑层（核心）
│   ├── mcp_server/    # MCP 服务器层
│   ├── rest_api/      # FastAPI REST API 层
│   ├── clients/       # 客户端模块
│   └── common/        # 公共模块
├── docker/            # Docker 部署文件
├── test/              # 测试文件（unit/integration/e2e/performance）
├── scripts/           # 工具脚本
├── examples/          # 示例代码（agents/skills）
├── docs/              # 文档
├── config/            # 配置文件
├── run_mcp.py         # MCP 启动脚本
├── start_business.py  # 业务服务启动脚本
└── start_fastapi.py   # FastAPI 启动脚本
```

---

## 快速部署

### 方式一：Docker 部署（推荐）

```bash
# 1. 进入 Docker 目录
cd docker

# 2. 启动服务（默认端口 8000）
./manage.sh start

# 3. 查看状态
./manage.sh status

# 4. 停止服务
./manage.sh stop

# 5. 查看日志
docker logs -f ai-memory-mcp
```

### 方式二：本地开发

```bash
# 1. 创建 Conda 环境
conda create -n ai_memory_mcp python=3.12
conda activate ai_memory_mcp

# 2. 安装依赖
pip install -r requirements.txt

# 3. 启动业务服务
python start_business.py

# 4. 启动 MCP 服务器（新终端）
python run_mcp.py

# 5. 启动 FastAPI 服务（可选，新终端）
python start_fastapi.py
```

### Claude Code 配置

编辑 Claude Code 配置文件，添加 MCP 服务器：

**本地模式**：
```json
{
  "mcpServers": {
    "memory": {
      "command": "python",
      "args": ["/path/to/ai_memory_mcp/run_mcp.py"],
      "env": {
        "PYTHONPATH": "/path/to/ai_memory_mcp/src"
      }
    }
  }
}
```

**Docker 模式**：
```json
{
  "mcpServers": {
    "memory": {
      "url": "http://localhost:8000/mcp",
      "type": "http"
    }
  }
}
```

### 验证安装

在 Claude Code 中测试：

```
请使用 MCP [memory] 列出所有项目
```

---

## 核心功能

### 记忆内容分类

| 分组 | 用途 | 记录内容 |
|------|------|----------|
| **Features** | 功能规划与跟踪 | 待开发功能、开发中功能、已完成功能 |
| **Fixes** | Bug 修复记录 | 问题描述、严重程度、解决方案 |
| **Notes** | 开发知识沉淀 | 技术决策、调试过程、踩坑经验 |
| **Standards** | 项目规范约束 | 代码规范、命名约定、架构原则 |

### 记忆关联系统

```
┌─────────────────┐
│   Features      │ ─┐
│   (功能列表)     │  │ 关联
└─────────────────┘  │
                     ├─→ Notes (笔记)
┌─────────────────┐  │    (记录开发过程/决策原因)
│   Fixes         │ ─┘
│   (Bug修复)      │
└─────────────────┘
```

- **Feature ↔ Note**: 功能开发时可关联相关笔记（如设计决策、参考文档）
- **Fix ↔ Note**: Bug 修复时可关联排查过程
- **Fix ↔ Feature**: Bug 修复可关联到具体功能模块
- **标签系统**: 所有条目支持多标签，便于跨维度查询

---

## MCP 工具列表

### 项目管理

| 工具 | 功能 |
|------|------|
| `project_register` | 注册新项目 |
| `project_list` | 列出所有项目 |
| `project_get` | 获取项目信息或查询条目 |
| `project_rename` | 重命名项目 |
| `project_remove` | 归档或删除项目 |

### 条目管理

| 工具 | 功能 |
|------|------|
| `project_add` | 添加新条目（features/fixes/notes/standards） |
| `project_update` | 更新条目内容 |
| `project_delete` | 删除条目 |

### 标签系统

| 工具 | 功能 |
|------|------|
| `tag_register` | 注册新标签（定义语义） |
| `tag_update` | 更新标签语义 |
| `tag_delete` | 删除标签 |
| `tag_merge` | 合并标签 |
| `project_tags_info` | 查询标签信息 |
| `project_item_tag_manage` | 管理条目标签 |

### 查询功能

- 支持按状态过滤（pending/in_progress/completed）
- 支持按严重程度过滤（critical/high/medium/low）
- 支持按标签过滤
- 支持按创建/修改时间过滤
- 支持正则表达式匹配摘要
- 支持分页查询

---

## 使用场景示例

### 场景一：跨会话继续开发

**场景**: 上周让 Claude 实现了 API 认证中间件，今天回来继续开发。

```
你: 继续完善 API 认证功能，添加刷新 token 机制

Claude: [查询记忆] 检索到项目记录：
        - feat_20260401: 已实现 JWT 认证，使用 FastAPI Security
        - note_20260401: 记录了密钥存储在 /secrets/jwt_key.pem
        - standards_20260315: 认证相关函数需添加 @auth_required 装饰器

        基于现有实现，刷新 token 机制可以这样设计...
```

### 场景二：复用已解决的经验

**场景**: 新项目遇到之前解决过的 Docker 网络问题。

```
你: Docker Compose 启动后服务间无法通信

Claude: [跨项目查询] 在项目 web-dashboard 中发现类似问题：
        - fix_20260310: Docker 网络通信失败
        - 解决方案：使用自定义网络 network_mode: bridge
        - note_20260310: 需要在 docker-compose.yml 中显式声明 networks

        已为新项目生成相同的配置...
```

### 场景三：遵守项目约定

**场景**: 让 AI 按照团队的代码规范生成代码。

```
你: 实现用户订单查询接口

Claude: [查询规范] 根据 project standards：
        - 所有接口返回统一的 Result<T> 包装格式
        - 分页参数使用 PageRequest(page, size)
        - 异步函数命名需包含 _async 后缀

        生成代码：

        async def get_orders_async(req: PageRequest) -> Result[List[Order]]:
            ...
```

---

## 数据存储

### 存储位置

Docker 模式：容器内持久化卷 `/var/lib/project_memory_ai/`

本地模式：项目根目录下的 `data/` 目录

### 数据目录结构

```
/var/lib/project_memory_ai/
├── _metadata.json              # 全局元数据（项目列表、统计）
├── _stats.json                 # 接口调用统计
│
├── project_a/                  # 项目A目录（项目名称）
│   ├── _project.json           # 项目元信息（id, name, info, _version）
│   ├── _tags.json              # 标签注册表（tag -> description, aliases）
│   ├── _group_configs.json     # 分组配置（可选）
│   │
│   ├── features/               # 功能分组
│   │   ├── _index.json         # 功能索引（id -> summary, status, tags...）
│   │   ├── feat_20260408_001.json  # 功能详情
│   │   └── feat_20260408_002.json
│   │
│   ├── fixes/                  # Bug修复分组（结构同 features）
│   ├── notes/                  # 笔记分组（结构同 features）
│   └── standards/              # 规范分组（结构同 features）
│
├── project_b/                  # 项目B目录
│
└── .archived/                  # 已归档的项目
    ├── 20260408_123456_project_a.tar.gz
    └── 20260408_123456_project_a.meta.json
```

---

## 开发指南

### 环境要求

- Python 3.12+
- Conda（推荐）
- Docker（用于容器化部署）

### 运行测试

```bash
# 使用测试脚本
./scripts/run_tests.sh

# 或手动运行
pytest test/ -v --cov=src/business --cov-report=html
```

### 代码规范

- 使用 `black` 进行代码格式化
- 使用 `ruff` 进行代码检查
- 使用 `mypy` 进行类型检查

---

## 项目状态

| 项目 | 当前版本 | 开发分支 | 主分支 |
|------|---------|---------|--------|
| ai_memory_mcp | v1.0.0 | dev | main |

### 开发统计

- Features: 63
- Notes: 125
- Fixes: 24
- Standards: 18
- 标签数: 59

---

## 贡献指南

欢迎贡献！请查看 [CONTRIBUTING.md](CONTRIBUTING.md) 了解详情。

---

## 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

---

## 相关链接

- [MCP 协议规范](https://modelcontextprotocol.io/)
- [Claude Code 文档](https://code.anthropic.com/)
- [FastMCP 文档](https://github.com/jlowin/fastmcp)
