---
name: do-fix
description: fix 简短Bug修复
allowed-tools: mcp__memory_mcp__project_list, mcp__memory_mcp__project_get, mcp__memory_mcp__project_add, mcp__memory_mcp__project_update, mcp__memory_mcp__project_tags_info, mcp__memory_mcp__tag_register, Read, Grep, Glob, Bash, Skill, AskUserQuestion
argument-hint: <Bug描述>
---

# 简短Bug修复技能

## ⚠️ 重要指令

**DO NOT ENTER PLAN MODE** - 此技能要求直接执行，不进入计划模式

**所有memory_mcp的操作使用子代理来处理，减少主窗口上下文**

---

## 使用示例

```
/skill do-fix "fix: 用户登录功能报错500"
```

---

## 流程概览

```
阶段1(项目确认) → 阶段2(问题澄清) → 阶段3(方案设计) → 阶段4(代码实现)
```

---

## 阶段 1: 项目确认

**目标**: 确认项目和创建fix记录

**流程**:

1. 解析入参，提取Bug描述（去掉 `fix:` 前缀）
2. 调用 ./project-confirmation.md 技能创建fix记录
   ```
   Skill: project-confirmation, args: "<Bug描述>"
   ```
3. 获取 `fix_id`

**输出**:
- `fix_id`: 修复ID
- `project_id`: 项目ID

---

## 阶段 2: 问题澄清与确认

**使用技能**: `requirement-confirmation`

```
Skill: requirement-confirmation, args: "<fix_id>"
```

**技能会完成**:
1. 问题澄清（多轮提问）
2. 问题确认
3. 创建note记录完整问题描述
4. 更新development-log

**输出**:
- `confirmed_requirements`: 确认的问题描述

---

## 阶段 3: 方案设计与选择

**使用技能**: `solution-design`

```
Skill: solution-design, args: "<fix_id>"
```

**技能会完成**:
1. 方案设计（探索代码库并设计方案）
2. 用户选择方案
3. 方案详细规划
4. 创建note记录完整方案
5. 更新development-log

**输出**:
- `selected_solution`: 选择的修复方案

---

## 阶段 4: 代码实现与测试

**使用技能**: `code-implementation`

```
Skill: code-implementation, args: "<fix_id>"
```

**技能会完成**:
1. 代码实现
2. 单元测试
3. 整合测试
4. **修复验证**：确认bug确实被修复
   - 复现问题（如可复现）
   - 执行修复
   - 验证修复（确认问题已解决）
5. 更新development-log

**输出**:
- `implementation_result`: 实现结果
- `fix_verified`: 修复验证结果

---

## 完成展示

```
fix:
  - fix_id
  - fix:summary
  - fix:content
  - fix:severity
  - fix:status

note:
  - note_id:summary (requirements)
  - note_id:summary (implementation-plan)
  - note_id:summary (development-log)

验证结果:
  - fix_verified: <true|false>
```
