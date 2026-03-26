---
name: memory-query
description: query memory explore show search 搜索 记忆 查询 回忆 展示 使用MCP[memory_mcp]查询过往记录
allowed-tools: mcp__memory_mcp__project_list, mcp__memory_mcp__project_tags_info, mcp__memory_mcp__project_get, mcp__memory_mcp__project_groups_list
argument-hint: <搜索内容>
context: fork
---

# memory-query 技能

自动判断输入类型，在所有分组中搜索相关记忆条目并格式化输出。

## 输入类型判断

根据语言（中文/英文）匹配标签，判断顺序：需求 → Bug → 关键字（兜底）

### 需求模式

| 中文特征 | 英文特征 |
|----------|----------|
| 添加、新增、实现、功能、特性 | add, new, implement, feature, enhance |

**匹配标签**：`enhancement`, `api`, `implementation`, `feature`, `storage`, `structure`

### Bug模式

| 中文特征 | 英文特征 |
|----------|----------|
| bug、问题、错误、修复、fix | bug, error, fix, issue, broken |

**匹配标签**：`fix`, `validation`, `implementation`, `refactor`

### 关键字模式

直接使用输入作为标签名搜索（无特征匹配时）

## 执行流程

### 步骤 1：确定项目 ID

1. 调用 `project_list` 获取项目列表
2. 从当前目录 `CLAUDE.md` 提取项目名称（格式：`# 项目名称`）
3. 匹配获取项目 ID
4. **异常**：未找到项目 → 直接报错中断

### 步骤 2：根据输入判断类型并生成标签列表

```
输入内容 → 检测语言 → 匹配标签
```

- 检测输入是否包含中文特征词 → 需求/Bug模式（中文标签）
- 检测输入是否包含英文特征词 → 需求/Bug模式（英文标签）
- 两者都没有 → 关键字模式，直接用输入作为标签

### 步骤 3：在所有分组中查询并获取详情

1. 对每个标签在所有分组中查询（列表模式）：
```python
project_get(project_id, group_name="features", tags=<tag>)
project_get(project_id, group_name="notes", tags=<tag>)
project_get(project_id, group_name="fixes", tags=<tag>)
project_get(project_id, group_name="standards", tags=<tag>)
```

2. 对每个结果调用 `project_get` + `item_id` 获取完整 content：
```python
project_get(project_id, group_name=<group>, item_id=<item_id>)
```

### 步骤 4：JSON 结构化输出

```json
{
  "input": "<原始输入>",
  "type": "<需求|Bug|关键字>",
  "tags": ["<标签列表>"],
  "items": [
    {
      "id": "<item_id>",
      "group": "<group>",
      "summary": "<summary>",
      "content": "<content>",
      "status": "<status>",  // 仅 features/fixes 分组有此字段：pending/in_progress/completed
      "severity": "<severity>"  // 仅 fixes 分组有此字段：critical/high/medium/low
    }
  ]
}
```

**返回字段说明**：
- `id`: 条目 ID
- `group`: 分组名称
- `summary`: 条目摘要
- `content`: 条目内容
- `status`: 状态（仅 features/fixes 分组有此字段，notes/standards 无此字段）
- `severity`: 严重程度（仅 fixes 分组有此字段，notes/standards/features 无此字段）

**异常处理**：
- 项目不存在 → `{"error": "project_not_found"}`
- 标签无结果 → items 为空数组
- 查询失败 → 中断并报告错误

## 示例

| 输入 | 类型 | 匹配标签 |
|------|------|----------|
| `添加一个xxx接口` | 需求 | enhancement, api, implementation |
| `add new feature` | 需求 | enhancement, feature |
| `xxx有问题` | Bug | fix, validation |
| `docker` | 关键字 | docker |
| `fix bug` | Bug | fix |
