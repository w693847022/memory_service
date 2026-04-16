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

## 创建Feature记录

- summary: <用户需求摘要>
- content: <用户需求>
- status: pending
- 如果用户需求超出content限制则content也记录摘要然后建立note[<feature_id>-initial-requirements]进行记录

---

## 创建开发记录Note

- 建立note命名[<feature_id>-development-log]
- 在feature条目中增加这个note的关联

---

## 输出

```
feature_id: <生成的feature_id>
project_id: <项目ID>
project_name: <项目名称>
```
