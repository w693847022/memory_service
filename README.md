# 多项目本地记忆 MCP 服务器

**[English Version](README_EN.md)**

## 项目简介

**AI Memory MCP** 是一个为 Claude Code 提供持久化项目记忆的 MCP 服务器。它让 AI 能够跨会话记住你的项目开发历程，包括功能规划、Bug 修复、开发笔记等关键信息，成为你开发过程中的"第二大脑"。

与传统的笔记工具不同，本项目专为 AI 交互设计，将记忆内容结构化存储，支持智能标签系统和关联查询，让 Claude 能够快速理解项目上下文并提供精准帮助。

---

## 主要功能

### 记录内容

| 分组 | 用途 | 记录内容 |
|------|------|----------|
| **Features (功能)** | 功能规划与跟踪 | 待开发功能、开发中功能、已完成功能 |
| **Fixes (修复)** | Bug 修复记录 | 问题描述、严重程度、解决方案 |
| **Notes (笔记)** | 开发知识沉淀 | 技术决策、调试过程、踩坑经验 |
| **Standards (规范)** | 项目规范约束 | 代码规范、命名约定、架构原则 |

### 记录关联

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

## 快速部署（Docker）

### 1. 启动服务

```bash
# 启动 Docker 容器（默认端口 8000）
cd docker && ./manage.sh start

# 查看状态
./manage.sh status

# 停止服务
./manage.sh stop
```

### 2. Claude Code 配置

编辑 Claude Code 配置文件，添加远程 MCP 服务器：

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

### 3. 验证安装

在 Claude Code 中测试：

```
请使用 MCP [memory] 列出所有项目
```

---

## 具体使用场景

### 场景一：开发便利性 - 跨会话记忆

**问题**: 你今天让 Claude 帮忙写了一个用户认证模块，三天后回来继续开发，但忘了之前的实现细节。

**传统方式**:
```
你: 我之前写了个用户登录，是什么方式来着？
Claude: 我不知道之前的内容，需要你重新描述...
```

**使用 Memory MCP**:
```
你: 继续开发用户认证功能
Claude: [查询记忆] 我看到你之前用 JWT 实现了用户登录，
        使用 RS256 算法，token 存储在 localStorage。
        要继续开发密码重置功能吗？
```

---

### 场景二：上下文管理 - 新人快速上手

**问题**: 新接手一个项目，代码里有 `handleAuth()` 函数，但不知道为什么要这样写。

**传统方式**:
```
你: 这个 handleAuth 为什么要检查三个条件？
Claude: 我不太清楚项目背景，需要你解释...
```

**使用 Memory MCP**:
```
你: handleAuth 函数的逻辑有点复杂
Claude: [查询记忆] 根据 note_20260315_002，
        这里需要检查三个条件是因为：
        1. 处理老用户迁移时的 token 格式差异
        2. 兼容移动端特殊认证流程
        3. 防止重放攻击
```

---

### 场景三：多项目信息获取 - 跨项目经验复用

**问题**: 你在项目 A 中解决了一个棘手的并发问题，现在项目 B 遇到类似问题。

**传统方式**:
```
你: 我之前在另一个项目解决过类似问题...具体怎么做的来着？
Claude: 我无法访问其他项目的信息...
```

**使用 Memory MCP**:
```
你: 项目 B 出现了并发冲突问题
Claude: [跨项目查询] 我发现你在项目 A 中
        用标签 "concurrency" 记录过类似问题的解决方案：

        fix_20260310_001: 使用乐观锁 + 重试机制解决
        note_20260310_001: 详细记录了实现代码和注意事项

        要在项目 B 中应用相同的方案吗？
```

---

### 场景四：规范约束 - AI 自动遵守项目约定

**问题**: 你的项目有特定的代码规范（如：异步函数必须加 `_async` 后缀），但 Claude 不知道。

**使用 Memory MCP**:
```
你: 写一个用户获取函数
Claude: [查询规范] 根据 standards 中的命名规范，
        异步函数需要加 _async 后缀。我将创建：

        def get_user_async(user_id: int) -> User:
            ...
```

---

### 场景五：Bug 修复追踪 - 关联分析

**问题**: 某个 Bug 反复出现，想了解历史修复记录。

**使用 Memory MCP**:
```
你: 登录接口又报错了
Claude: [查询历史] 该问题有 3 次修复记录：

        fix_20260301_001: Token 过期问题 (严重: high)
        fix_20260308_002: 时区处理错误 (严重: medium)
        fix_20260315_003: 并发竞态条件 (严重: critical)
                        ↑ 关联 feature_auth_002

        本次错误可能是...建议检查...
```

---

## 数据存储与管理

### 目录结构

所有数据存储在服务器容器内的持久化卷中：

```
/var/lib/project_memory_ai/
├── _metadata.json           # 全局元数据（项目列表、统计）
├── _stats.json              # 接口调用统计
│
├── project_a/               # 项目A目录（项目名称）
│   ├── project.json         # 项目数据（features/fixes/standards元信息）
│   └── notes/               # 笔记内容（独立md文件）
│       ├── note_20260320_001.md
│       └── note_20260320_002.md
│
├── project_b/               # 项目B目录
│   ├── project.json
│   └── notes/
│
└── .archived/               # 已归档的旧数据
    └── 20260320_123456_project_a.json
```

### 数据结构

#### project.json 格式

```json
{
  "id": "proj_xxxxx",                    // 项目 UUID
  "info": {
    "name": "项目名称",                   // 项目显示名称
    "path": "/path/to/project",          // 项目路径
    "description": "项目描述",
    "created_at": "2026-03-20T10:00:00",
    "updated_at": "2026-03-20T15:30:00",
    "tags": ["python", "web"]            // 项目级标签
  },
  "features": [                          // 功能列表
    {
      "id": "feat_20260320_001",
      "description": "实现用户登录",
      "status": "completed",             // pending/in_progress/completed
      "note_id": "note_20260320_001",    // 关联笔记
      "tags": ["auth", "frontend"],
      "created_at": "2026-03-20T10:00:00",
      "updated_at": "2026-03-20T14:00:00"
    }
  ],
  "fixes": [                             // Bug修复记录
    {
      "id": "fix_20260320_001",
      "description": "修复登录接口认证错误",
      "status": "completed",
      "severity": "critical",            // critical/high/medium/low
      "related_feature": "feat_20260320_001",  // 关联功能
      "note_id": "note_20260320_002",
      "tags": ["auth", "bug"],
      "created_at": "2026-03-20T12:00:00",
      "updated_at": "2026-03-20T13:00:00"
    }
  ],
  "notes": [                             // 笔记元信息（不含内容）
    {
      "id": "note_20260320_001",
      "description": "JWT登录实现方案",
      "tags": ["auth", "design"],
      "created_at": "2026-03-20T10:30:00",
      "updated_at": "2026-03-20T10:30:00"
    }
  ],
  "standards": [                         // 项目规范
    {
      "id": "std_20260320_001",
      "description": "命名规范",
      "content": "异步函数必须加 _async 后缀",
      "tags": ["naming", "style"],
      "created_at": "2026-03-20T09:00:00",
      "updated_at": "2026-03-20T09:00:00"
    }
  ],
  "tag_registry": {                      // 标签注册表
    "auth": {
      "description": "认证相关",
      "created_at": "2026-03-20T10:00:00",
      "usage_count": 5,
      "aliases": ["authentication"]
    }
  }
}
```

#### 笔记内容文件

```
# notes/note_20260320_001.md
登录功能使用 JWT 实现...

- 算法：RS256
- Token存储：localStorage
- 有效期：24小时
```

---

## 安全提醒

> 当前版本未实现多人协作的数据安全管理机制。

- 考虑后续更新

---

## 项目徽章

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.12+-green.svg)
![MCP](https://img.shields.io/badge/MCP-FastMCP-orange.svg)


## 许可

MIT License
