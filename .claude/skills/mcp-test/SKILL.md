---
name: mcp-test
description: 对 memory_mcp 全部 MCP 接口执行冒烟测试，验证服务可用性
allowed-tools: Agent, mcp__memory_mcp__project_register, mcp__memory_mcp__project_get, mcp__memory_mcp__project_list, mcp__memory_mcp__project_groups_list, mcp__memory_mcp__project_add, mcp__memory_mcp__project_update, mcp__memory_mcp__project_rename, mcp__memory_mcp__project_archive, mcp__memory_mcp__project_item_tag_manage, mcp__memory_mcp__project_tags_info, mcp__memory_mcp__tag_register, mcp__memory_mcp__tag_update, mcp__memory_mcp__tag_delete
---

对 memory_mcp 全部 MCP 接口执行冒烟测试，验证服务可用性。

使用子代理执行全部测试，避免污染主上下文。子代理 prompt 如下：

---

请对 memory_mcp 的全部 MCP 接口依次执行冒烟测试。每个接口调用后检查返回结果是否包含错误，记录 pass/fail。全部完成后输出汇总报告。

使用唯一前缀 `smoke_{{当前时间戳}}` 避免与已有数据冲突。

### 测试步骤

#### 1. 项目注册 - project_register
调用 `project_register`，参数：
- name: `smoke_{{timestamp}}_test_project`
- summary: "冒烟测试项目"
- tags: "test,smoke"

记录返回的 `project_id`，后续步骤全部使用此 ID。

#### 2. 项目查询 - project_get（整体）
调用 `project_get`，参数：
- project_id: 步骤1返回的 ID

验证返回包含项目基本信息（name, id 等）。

#### 3. 项目列表 - project_list
调用 `project_list`，参数：
- name_pattern: `smoke_{{timestamp}}`

验证返回列表包含刚注册的测试项目。

#### 4. 分组查询 - project_groups_list
调用 `project_groups_list`，参数：
- project_id: 测试项目 ID

验证返回包含内置分组（features, fixes, notes, standards），记录各分组的配置信息（status_values, severity_values 等），后续步骤按配置使用。

#### 5. 条目添加 - project_add
分别对四个内置分组各添加一条条目。调用 `project_add`，参数：
- **features**: summary="冒烟测试功能", status="pending", severity="medium"
- **fixes**: summary="冒烟测试修复", status="pending", severity="medium"
- **notes**: summary="冒烟测试笔记"
- **standards**: summary="冒烟测试规范"

记录每条返回的 `item_id`。

#### 6. 条目列表查询 - project_get（分组模式）
调用 `project_get`，参数：
- project_id: 测试项目 ID
- group_name: "features"
- view_mode: "summary"

验证返回包含步骤5添加的 features 条目。

#### 7. 条目详情查询 - project_get（详情模式）
调用 `project_get`，参数：
- project_id: 测试项目 ID
- group_name: "features"
- item_id: 步骤5中 features 条目的 ID

验证返回包含完整的条目详情（content, version 等）。

#### 8. 条目更新 - project_update
调用 `project_update`，参数：
- project_id: 测试项目 ID
- group: "features"
- item_id: features 条目 ID
- summary: "冒烟测试功能-已更新"
- status: "completed"

验证更新成功。

#### 9. 标签注册 - tag_register
调用 `tag_register`，参数：
- project_id: 测试项目 ID
- tag_name: "smoke_test_tag"
- summary: "冒烟测试标签"

验证注册成功。

#### 10. 标签查询 - project_tags_info
调用 `project_tags_info`，参数：
- project_id: 测试项目 ID

验证返回包含刚注册的 `smoke_test_tag`。

#### 11. 标签更新 - tag_update
调用 `tag_update`，参数：
- project_id: 测试项目 ID
- tag_name: "smoke_test_tag"
- summary: "冒烟测试标签-已更新"

验证更新成功。

#### 12. 条目标签管理 - project_item_tag_manage
依次执行三种操作：
- **add**: project_id=测试项目ID, group_name="features", item_id=features条目ID, operation="add", tag="smoke_test_tag"
- **set**: 同上，operation="set", tags="smoke_test_tag,test"
- **remove**: 同上，operation="remove", tag="test"

验证每步操作成功。

#### 13. 项目重命名 - project_rename
调用 `project_rename`，参数：
- project_id: 测试项目 ID
- new_name: `smoke_{{timestamp}}_test_project_renamed`

验证重命名成功。

#### 14. 项目归档 - project_archive
调用 `project_archive`，参数：
- project_id: 测试项目 ID

验证归档成功。

### 汇总报告
全部步骤完成后，输出格式如下的汇总报告：

```
MCP 接口冒烟测试报告
====================
测试时间: {{当前时间}}
测试项目: smoke_{{timestamp}}_test_project (已清理)

接口测试结果:
  1. project_register      : PASS / FAIL
  2. project_get (整体)     : PASS / FAIL
  3. project_list           : PASS / FAIL
  4. project_groups_list    : PASS / FAIL
  5. project_add            : PASS / FAIL
  6. project_get (分组)     : PASS / FAIL
  7. project_get (详情)     : PASS / FAIL
  8. project_update         : PASS / FAIL
  9. tag_register           : PASS / FAIL
 10. project_tags_info      : PASS / FAIL
 11. tag_update             : PASS / FAIL
 12. project_item_tag_manage: PASS / FAIL
 13. project_rename         : PASS / FAIL
 14. project_archive        : PASS / FAIL
--------------------
通过: X/14  失败: X/14
====================
```

如果有失败的步骤，附上失败原因（返回的错误信息）。
