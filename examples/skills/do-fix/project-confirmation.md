## Stage 1: Project Confirmation

**目标**: 确认当前操作的项目，为后续相关性探索提供准确的项目名称

**流程**:

1. 调用 `project_list()` 获取所有已注册项目

2. 根据CLAUDE.md文件记录的项目名称查找

3. 将 `project_id` 和 `project_name` 插入上下文，供后续阶段使用

4. **展示** 项目ID:项目名称

---

## 回忆项目规范

使用技能 `rememory-std` 回忆以下规范：
- 项目结构规范
- 代码开发规范
- 测试规范
- 部署规范

所有规范摘要插入上下文，供后续所有阶段使用。
**向用户展示一下查到的各类规范数量**

---

## 创建Fix记录

- summary: <Bug描述摘要>
- content: <Bug描述>
- severity: <严重程度> (critical/high/medium/low，默认medium)
- status: pending
- 如果Bug描述超出content限制则content也记录摘要然后建立note[<fix_id>-initial-report]进行记录

**注意**: 如果用户未提供严重程度，默认使用 `medium`

---

## 创建开发记录Note

- 建立note命名[<fix_id>-development-log]
- 在fix条目中增加这个note的关联

---

## 输出

```
fix_id: <生成的fix_id>
project_id: <项目ID>
project_name: <项目名称>
```
