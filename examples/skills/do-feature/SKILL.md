---
name: do-feature
description: feature 简短功能开发
allowed-tools: mcp__memory_mcp__project_list, mcp__memory_mcp__project_get, mcp__memory_mcp__project_add, mcp__memory_mcp__project_update, mcp__memory_mcp__project_tags_info, mcp__memory_mcp__tag_register, Read, Grep, Glob, Bash, Bash(python:*), Bash(pytest:*), Skill, wc, AskUserQuestion
argument-hint: <功能描述>
---

# 简短功能开发技能

## ⚠️ 重要指令

**DO NOT ENTER PLAN MODE** - 此技能要求直接执行，不进入计划模式

**所有memory_mcp的操作使用子代理来处理，减少主窗口上下文**

---

## 使用示例

```
/skill do-feature "feature: 添加用户登录功能"
```

---

## 流程概览

```
阶段1(项目确认) → 阶段2(方案设计) → 阶段3(代码实现)
```

---

## 阶段 1: 项目确认

**目标**: 确认项目和创建feature记录

**流程**:

1. 解析入参，提取功能描述（去掉 `feature:` 前缀）
2. 调用 ./project-confirmation.md 技能创建feature记录
   ```
   Skill: project-confirmation, args: "<功能描述>"
   ```
3. 获取 `feature_id`

**输出**:
- `feature_id`: 功能ID
- `project_id`: 项目ID

---

## 阶段 2: 方案设计与选择

**调用技能处理该阶段**: `solution-design`

```
Skill: solution-design, args: "<feature_id>"
```

**技能会完成**:
1. 方案设计（探索代码库并设计方案）
2. 用户选择方案
3. 方案详细规划
4. 创建note记录完整方案
5. 更新development-log

**输出**:
- `selected_solution`: 选择的实现方案

---

## 阶段 3: 代码实现与测试

**调用技能处理该阶段**: `code-implementation`

```
Skill: code-implementation, args: "<feature_id>"
```

**技能会完成**:
1. 代码实现
2. 单元测试
3. 整合测试
4. 更新development-log

**输出**:
- `implementation_result`: 实现结果

---

## 完成展示

```
feature:
  - feature_id
  - feature:summary
  - feature:content

note:
  - note_id:summary (implementation-plan)
  - note_id:summary (development-log)

总结本次修改:xxx
```
