---
name: memory-std
description: 初始化项目标准 standard 规范 初始化 初始化标准 使用MCP[memory_mcp]记录项目标准
allowed-tools: mcp__memory_mcp__project_list, mcp__memory_mcp__project_get, mcp__memory_mcp__project_add, mcp__memory_mcp__project_tags_info, mcp__memory_mcp__tag_register, Glob, Grep, Read, Bash
---

# Memory-std 技能

根据用户输入，将项目规范记录到 memory_mcp。

## 触发方式

```
/memory-std <输入内容>
```

## 流程概览

```
确定项目 → 解析输入类型 → 探索/拆分 → 记录标签并添加
```

## 输入类型与处理

- 如果没有输入则表示项目范围下,左右种类探索
- **代码范围**: `src/api`, `tests/`, `工具函数` → 探索该范围内所有规范种类
- **种类**: `代码风格`, `git规范`, `API规范` → 按该种类探索项目已有/应有关联规范
- **确切规范**: `使用snake_case`, `4空格缩进` → 拆分提取关键词，按种类归类后记录

## 格式要求

- **summary**: `{种类}规范-{关键词}`
- **content**: 规范详情

---

## 阶段 1: 确定项目

```python
project_list()
```
> 自动匹配当前目录项目

---

## 阶段 2: 解析输入类型

### 类型判断

```
输入内容 → 判断类型 → 确定探索范围
```

- **代码范围**: 含路径分隔符 `/` 或常见目录名 → 探索该目录下的所有种类规范
- **种类**: 匹配种类标签表 → 按种类探索
- **确切规范**: 其他情况 → 拆分提取关键词，归类后记录

### 种类标签

| 种类 | 标签 |
|------|------|
| 代码风格/缩进/格式化 | code-style |
| 命名 | naming |
| 提交/git | git |
| API/接口 | api |
| 测试 | testing |
| 文档 | docs |
| 目录结构 | structure |
| 语言惯用法 | idiom |
| 项目规范（兜底/模糊场景） | project |

---

## 阶段 3: 项目内探索

### 代码范围探索

1.没有则全项目范围探索

### 种类探索

1.未指定则全种类探索

### 拆分规范

```
输入: 使用snake_case命名

拆分结果:
  - 种类: naming
  - 关键词: snake_case
  - summary: 命名规范-snake_case
  - content: 使用snake_case进行变量/函数命名
```

---

## 阶段 4: 记录

### 标签处理

```python
project_tags_info(project_id)
# 注册未存在的标签
tag_register(project_id, tag_name, summary)
```

### 添加标准

```python
project_add(
    project_id="<项目ID>",
    group="standards",
    summary="{种类}规范-{关键词}",
    content="<规范详情>",
    tags="<种类标签>"
)
```

---

## 输出

```
## 规范已记录

**summary**: 命名规范-snake_case
**content**: 使用snake_case进行变量/函数命名
**tags**: naming
```
