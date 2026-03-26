---
name: rememory-std
description: 回忆项目规范 standard 规范 查询 插入上下文 使用MCP[memory_mcp]查询项目规范
allowed-tools: mcp__memory_mcp__project_list, mcp__memory_mcp__project_get
context: fork
argument-hint: <规范类型，如：代码规范、开发规范、API规范>
---

# rememory-std 技能

回忆项目规范并返回紧凑 JSON 格式。

## ⚠️ 第一步：参数检查

**检查命令参数**：

用户输入：`/rememory-std <参数>`

- 如果 `<参数>` 为空 → 无参数模式
- 如果 `<参数>` 不为空 → 有参数模式

**判断方法**：
- 空输入：`/rememory-std` 或 `/rememory-std `（后面只有空格）
- 有输入：`/rememory-std 代码规范`、`/rememory-std docs`

## 📋 执行流程

### 步骤 1：确定项目

1. 调用 `project_list` 获取项目列表
2. 根据以下优先级确定项目 ID：
   - **用户显式提供**：用户通过 `argument` 直接指定项目 ID
   - **自动推断**（可选）：如果用户未指定，可尝试从当前工作目录或 git remote 推断
3. **注意**：本技能只提供查询能力，不强制要求自动推断项目；若无法确定项目，应询问用户

### 步骤 2：获取所有规范

调用 `project_get(project_id="<项目ID>", group_name="standards")` 查询所有规范。

**异常处理**：
- 项目不存在 → 返回 `{"error": "project_not_found", "message": "项目不存在"}`
- 没有规范 → 返回 `{"project_id": "<ID>", "standards": {}}`

### 步骤 3：根据参数决定返回内容

#### 无参数模式
返回所有规范，按主标签分组。

#### 有参数模式 - 语义过滤

**匹配规则**：
- 首先进行**精确匹配**：直接用用户输入匹配标签名
- 若无精确匹配，进行**中文别名匹配**
- 匹配时**大小写不敏感**

**大范围分类**：

| 大范围 | 初始标签 | 说明 |
|--------|----------|------|
| 代码修改 | api, code-style, structure, naming, security, testing, idiom | 涉及代码、接口、结构等全面覆盖 |
| 部署 | ops, docker, structure, security | 涉及运维、Docker、配置等 |
| 文档 | docs, api, code-style, naming | 涉及文档、API 说明、代码示例、术语规范 |
| 安全 | security, api, code-style | 涉及安全、认证、加密等 |
| 测试 | testing, code-style, api, structure, idiom | 涉及测试、验证、接口测试、测试目录结构 |
| 项目结构 | structure, project | 涉及项目组织、目录规范等 |

**AI 补充标签**：
1. **自动补充**：根据用户输入的具体需求，AI 主动分析可能涉及的额外标签，直接补充，无需询问用户
2. **宁多勿少**：查询原则是"可以多不能少"，如果不确定是否相关，倾向于包含该标签
3. 将初始标签与补充标签合并后查询
4. 使用 `matched_tags` 字段显示最终匹配到的所有标签

**直接标签名**（精确匹配）：

| 标签名 | 说明 |
|--------|------|
| docs | 文档规范 |
| git | Git 规范 |
| code-style | 代码风格 |
| naming | 命名规范 |
| testing | 测试规范 |
| structure | 项目结构 |
| api | API 规范 |
| security | 安全规范 |
| idiom | 语言惯用法 |
| project | 项目规范 |
| ops | 运维规范 |
| docker | Docker 规范 |

**过滤规则**：
1. 根据用户输入查找匹配的标签（大范围优先，其次精确匹配，最后中文别名）
2. AI 补充可能涉及的额外标签
3. 只返回这些标签的规范
4. 使用 `matched_tags` 字段显示匹配到的标签

## 📤 输出格式

### 无参数输出

```json
{
  "project_id": "mcp_test",
  "standards": {
    "code-style": ["详细规范内容1...", "详细规范内容2..."],
    "structure": ["详细规范内容..."]
  }
}
```

### 有参数输出

```json
{
  "project_id": "mcp_test",
  "input": "代码规范",
  "matched_tags": ["code-style"],
  "standards": {
    "code-style": ["详细规范内容..."]
  }
}
```

**注意**：输出内容为规范的 `content` 字段详细内容，不需要 `summary`。

### 错误输出

```json
{
  "error": "project_not_found",
  "message": "项目不存在"
}
```

## ✅ 检查清单

执行前确认：
- [ ] 已检查用户是否输入了参数
- [ ] 已确定项目 ID（用户显式提供或询问）
- [ ] 无参数 → 返回所有规范
- [ ] 有参数 → 按映射表过滤，只返回匹配标签
- [ ] 输出格式正确
- [ ] 异常情况有对应错误提示
