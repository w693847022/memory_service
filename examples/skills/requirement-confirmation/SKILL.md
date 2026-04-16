---
name: requirement-confirmation
description: 需求澄清与确认 - 通过多轮提问明确需求细节并确认（支持 feature 和 fix）
allowed-tools: mcp__memory_mcp__project_get, mcp__memory_mcp__project_add, mcp__memory_mcp__project_update, AskUserQuestion, Read, Grep, Glob, Agent
argument-hint: <feature_id|fix_id> 或 <需求描述>
---

# 需求澄清与确认技能

## 参数规范

| 参数类型 | 说明 | 执行模式 |
|---------|------|---------|
| `feature_id` | 已存在的功能ID | 更新模式：读取已有需求进行澄清 |
| `fix_id` | 已存在的修复ID | 更新模式：读取已有问题描述进行澄清 |
| `<需求描述>` | 自然语言描述（会自动判断feature或fix） | 创建模式：新建记录并澄清需求 |
| 无参数 | - | **拒绝执行** |

**注意**: 整合使用时，由主技能传入 `feature_id` 或 `fix_id`

---

## 前置条件

### 可选前置条件 (整合模式)
- 已完成项目确认 (`project_id` 已知)
- 已完成相关性探索 (推荐，可减少提问)

### 执行模式
- **整合模式**: 使用主流程提供的 `exploration_result` 和 `ambiguous_points`
- **独立模式**: 自主进行相关性探索

---

## ⚠️ 重要指令

**DO NOT ENTER PLAN MODE** - 此技能要求直接执行，不进入计划模式

**所有memory_mcp的操作使用子代理来处理，减少主窗口上下文**

---

## 参数类型判断（创建模式）

当收到自然语言描述时，在开始需求澄清前需要判断是 feature 还是 fix：

1. **关键词判断**：
   - 如果描述中包含 "bug"、"报错"、"修复"、"出错"、"问题"、"缺陷" 等词 → **fix**
   - 如果描述中包含 "新增"、"添加"、"功能"、"开发"、"实现" 等词 → **feature**
   - 包含两者都不明显的关键词 → 进入步骤2

2. **模糊时询问用户**：
   ```
   无法自动判断这是 Feature（功能开发）还是 Fix（Bug修复）。

   请问这是：
   1. Feature - 新功能开发或功能优化
   2. Fix - Bug修复
   ```

3. **根据用户选择设置 `record_type`**，然后继续对应的需求澄清流程

---

## 阶段 1: 需求澄清

**目标**: 基于相关性探索结果，通过多轮提问，明确功能需求细节

**流程**:

1. 分析用户提供的功能描述

2. 结合相关性探索结果（如果有），识别：
   - 已明确的事项（跳过）
   - 仍需澄清的模糊点
   - 边界条件、依赖关系

3. 每轮提问 2-4 个**针对性**问题

4. 用户回答后，进行信息整合后思考模糊点，如果有回到步骤3

**提问原则**:
- **优先利用历史信息**: 如果相似记录中已有明确信息，不再重复询问
- **聚焦差异点**: 针对当前需求与已有记录的差异进行提问
- **渐进式深入**: 先问核心问题，再问细节

**澄清完成标准**:
- 功能边界清晰
- 输入输出明确
- 技术约束确认

---

## 阶段 2: 需求确认

**目标**: 确认需求并记录

**流程**:

1. 输出需求摘要供用户确认：

```
## 需求确认

**类型**: <feature|fix>
**名称**: <名称>
**描述**: <一句话描述>

**详细需求/问题**:
- <需求点1>
- <需求点2>
- ...
```

2. 要求用户确认需求/问题
   - 如果用户要求修改则根据用户修改后重新确认

3. 更新对应记录（feature 或 fix）：
   - 如果是创建模式：根据 `record_type` 新建对应记录，返回 item_id
   - 如果是更新模式：更新已有记录的 content
   - content: 确认的需求/问题摘要

4. 建立note[<item_id>-requirements] 记录完整需求/问题描述
   - 在对应条目中增加这个note的关联

5. 更新development-log note
   - 记录需求澄清的关键问题和用户确认
   - 记录需求程序流程已经完成

---

## 输出

```
item_id: <feature_id|fix_id>
confirmed_requirements: <确认的需求/问题对象>
```

---

## 完成展示

展示创建/更新的记录ID：
```
record:
  - item_id
  - summary
  - content

note:
  - note_id:summary (requirements)
  - note_id:summary (development-log updated)
```
