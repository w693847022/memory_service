# 并发安全说明

## 概述

AI Memory MCP 实现了基于**五层阻挡位**和**两阶段排空**的并发控制机制，确保在高并发场景下的数据一致性和操作安全性。

---

## 核心概念

### 阻挡位（Barrier）

阻挡位是一种分层级的锁机制，每个业务操作对应特定层级的阻挡位。高级别的操作需要等待低级别的活跃操作完成后才能执行。

### 排空（Drain）

排空机制确保高级别操作执行前，所有低级别的活跃操作都已结束。通过计数器跟踪活跃操作，等待归零后继续执行。

---

## 五层阻挡位架构

```
┌─────────────────────────────────────────────────────────┐
│                    五层阻挡位体系                        │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  B1: 服务级 (Service)                                   │
│  ├─ register_project / remove_project                  │
│  └─ 全局锁，影响所有项目                                │
│                                                         │
│  B2: 项目范围级 (Project Scope)                         │
│  ├─ project_rename / tag_delete / tag_merge            │
│  └─ 项目级锁，影响整个项目                              │
│                                                         │
│  B3: 标签/组定义级 (Tag/Group Definition)               │
│  ├─ tag_register/update, group_*                       │
│  └─ 项目级锁，影响标签和组定义                          │
│                                                         │
│  B4: 条目列表级 (Entry List)                            │
│  ├─ add_item / delete_item                             │
│  └─ 项目+分组级锁，影响特定分组                         │
│                                                         │
│  B5: 条目ID级 (Entry ID)                                │
│  ├─ update_item / add/remove_item_tag                  │
│  └─ 项目+条目级锁，影响特定条目                         │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 阻挡位级别说明

### B1: 服务级（Service Level）

| 操作 | 说明 | 影响范围 |
|------|------|----------|
| `register_project` | 注册新项目 | 全局 |
| `remove_project` | 删除项目 | 全局，需排空 B4+B5 |

**特性**：
- 全局唯一锁
- 阻止所有其他项目相关操作
- 删除项目时需排空所有活跃操作

### B2: 项目范围级（Project Scope Level）

| 操作 | 说明 | 影响范围 |
|------|------|----------|
| `project_rename` | 项目重命名 | 单个项目，需排空 B4+B5 |
| `tag_delete` | 删除标签 | 单个项目，需排空 B4+B5 |
| `tag_merge` | 合并标签 | 单个项目，需排空 B4+B5 |

**特性**：
- 按项目隔离
- 阻止该项目的所有条目操作
- 需要排空 B4、B5 级别的活跃操作

### B3: 标签/组定义级（Tag/Group Definition Level）

| 操作 | 说明 | 影响范围 |
|------|------|----------|
| `tag_register` | 注册标签 | 单个项目的标签定义 |
| `tag_update` | 更新标签 | 单个项目的标签定义 |
| `group_create` | 创建自定义组 | 单个项目的组定义 |
| `group_update` | 更新自定义组 | 单个项目的组定义 |
| `group_delete` | 删除自定义组 | 单个项目，需排空 B4+B5 |
| `group_settings` | 更新组设置 | 单个项目的组定义 |

**特性**：
- 按项目隔离
- 阻止该项目的标签/组结构变更
- 删除组时需要排空相关活跃操作

### B4: 条目列表级（Entry List Level）

| 操作 | 说明 | 影响范围 |
|------|------|----------|
| `add_item` | 添加条目 | 单个项目的特定分组 |
| `delete_item` | 删除条目 | 单个项目的特定分组 |

**特性**：
- 按 `项目+分组` 隔离
- 增加活跃计数
- 允许不同分组的并发操作

### B5: 条目ID级（Entry ID Level）

| 操作 | 说明 | 影响范围 |
|------|------|----------|
| `update_item` | 更新条目 | 单个项目的特定条目 |
| `add_item_tag` | 添加条目标签 | 单个项目的特定条目 |
| `remove_item_tag` | 移除条目标签 | 单个项目的特定条目 |

**特性**：
- 按 `项目+条目ID` 隔离
- 最细粒度的锁
- 允许不同条目的完全并发

---

## 执行流程

### 标准流程

```
┌─────────────────────────────────────────────────────────┐
│                    操作执行流程                          │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  1. 上行检查 (Upward Check)                             │
│     │                                                    │
│     ├─ 按序获取更高级别的锁                              │
│     │  (B5 → B4 → B3 → B2 → B1)                         │
│     │                                                    │
│     ├─ 确认没有更高级操作在执行                          │
│     │                                                    │
│     └─ 释放高级别锁                                      │
│                                                         │
│  2. 获取自身阻挡位 (Acquire Own Barrier)                 │
│     │                                                    │
│     └─ 获取当前操作对应层级的锁                          │
│                                                         │
│  3. 下行排空 (Downward Drain)                           │
│     │                                                    │
│     ├─ 等待低级别活跃操作归零                            │
│     │  (对于需要排空的操作)                              │
│     │                                                    │
│     └─ DrainCounter.wait_zero()                         │
│                                                         │
│  4. 执行业务逻辑 (Execute)                               │
│     │                                                    │
│     ├─ 版本检测（如需要）                                │
│     │                                                    │
│     ├─ 获取 IO 锁                                        │
│     │                                                    │
│     ├─ 执行实际操作                                      │
│     │                                                    │
│     └─ 释放 IO 锁                                        │
│                                                         │
│  5. 清理与释放 (Cleanup)                                 │
│     │                                                    │
│     ├─ 更新版本号                                        │
│     │                                                    │
│     ├─ 减少活跃计数                                      │
│     │                                                    │
│     └─ 释放自身阻挡位                                    │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 示例：更新条目 (B5)

```python
async def update_item(project_id, group_name, item_id):
    # 1. 上行检查
    await B1.acquire(); B1.release()          # 检查服务级
    await B2.acquire(); B2.release()          # 检查项目级
    await B3.acquire(); B3.release()          # 检查标签组级
    await B4.acquire(); B4.release()          # 检查列表级

    # 2. 获取自身锁
    await B5.acquire()

    # 3. 计数+1
    drain.increment("B5")

    try:
        # 4. 执行业务逻辑
        # ... 实际操作 ...
        pass
    finally:
        # 5. 清理
        drain.decrement("B5")
        B5.release()
```

---

## 排空机制

### DrainCounter

活跃操作计数器，跟踪 B4/B5 级别的操作数量。

```python
class DrainCounter:
    def __init__(self):
        self.B4_active: int = 0      # B4 活跃操作数
        self.B5_active: int = 0      # B5 活跃操作数
        self._cond = asyncio.Condition()

    async def wait_zero(self, *levels):
        """等待指定级别的活跃计数归零"""
        async with self._cond:
            while not all(count == 0 for count in levels):
                await self._cond.wait()
```

### 排空使用场景

| 操作 | 需要排空 | 原因 |
|------|----------|------|
| `remove_project` | B4 + B5 | 删除项目前确保所有条目操作完成 |
| `project_rename` | B4 + B5 | 重命名前确保没有条目正在修改 |
| `tag_delete` | B4 + B5 | 删除标签前确保条目不再引用 |
| `tag_merge` | B4 + B5 | 合并标签前确保条目操作完成 |
| `group_delete` | B4 + B5 | 删除分组前确保条目操作完成 |

---

## 并发场景示例

### 场景 1: 同时更新不同条目

```
时间线：
T1: 请求 A 更新条目 item_1 (获取 B5_item_1 锁)
T2: 请求 B 更新条目 item_2 (获取 B5_item_2 锁)
T3: 请求 A 执行更新
T4: 请求 B 执行更新

结果：✅ 并发执行，互不影响
```

### 场景 2: 删除项目时的排空

```
时间线：
T1: 请求 A 更新条目 item_1 (B5 活跃 +1)
T2: 请求 B 删除项目 (需要排空 B4+B5)
T3: 请求 B 等待 B5 归零...
T4: 请求 A 完成更新 (B5 活跃 -1)
T5: 请求 B 检测到 B5=0，继续执行删除

结果：✅ 安全删除，不会遗漏操作
```

### 场景 3: 项目重命名冲突

```
时间线：
T1: 请求 A 添加条目 (B4 活跃 +1)
T2: 请求 B 项目重命名 (需要排空 B4+B5)
T3: 请求 B 等待 B4 归零...
T4: 请求 A 完成添加 (B4 活跃 -1)
T5: 请求 B 检测到 B4=0，继续重命名

结果：✅ 重命名在无活跃操作时执行
```

---

## API 使用

### 基本用法

```python
from business.core.barrier_manager import BarrierManager

# 初始化阻挡位管理器
barrier = BarrierManager()

# 更新条目 (B5)
async with barrier.update_item(project_id, group_name, item_id):
    # 执行更新操作
    await update_item_data(...)
```

### 操作级别对照

```python
# B1: 服务级
async with barrier.register_project():
    # 注册项目
    pass

async with barrier.remove_project(project_id):
    # 删除项目
    pass

# B2: 项目范围级
async with barrier.project_rename(project_id):
    # 项目重命名
    pass

async with barrier.tag_delete(project_id):
    # 删除标签
    pass

# B3: 标签/组定义级
async with barrier.tag_register(project_id):
    # 注册标签
    pass

async with barrier.group_create(project_id):
    # 创建自定义组
    pass

# B4: 条目列表级
async with barrier.add_item(project_id, group_name):
    # 添加条目
    pass

async with barrier.delete_item(project_id, group_name, item_id):
    # 删除条目
    pass

# B5: 条目ID级
async with barrier.update_item(project_id, group_name, item_id):
    # 更新条目
    pass

async with barrier.add_item_tag(project_id, group_name, item_id):
    # 添加条目标签
    pass
```

---

## 锁清理

### 自动清理

某些操作会自动清理不再需要的锁：

```python
# 删除条目后清理 B5 锁
async with barrier.delete_item(pid, group, item_id):
    ...
# 自动: barrier.cleanup_B5(item_id)

# 删除分组后清理 B4 锁
async with barrier.group_delete(pid, group_name):
    ...
# 自动: barrier.cleanup_B4(group_name)

# 删除项目后清理所有锁
async with barrier.remove_project(project_id):
    ...
# 自动: barrier.remove_project_barriers(project_id)
```

### 手动清理

```python
# 清理特定条目的锁
barrier._get_pb(project_id).cleanup_B5(item_id)

# 清理特定分组的锁
barrier._get_pb(project_id).cleanup_B4(group_name)

# 清理项目的所有锁
barrier.remove_project_barriers(project_id)
```

---

## 最佳实践

### 1. 使用 Context Manager

```python
# ✅ 推荐：使用 async with
async with barrier.update_item(pid, group, item_id):
    await do_update()

# ❌ 避免：手动管理锁
await barrier._B1.acquire()
try:
    await do_something()
finally:
    await barrier._B1.release()
```

### 2. 最小化锁持有时间

```python
# ✅ 推荐：锁内只做必要操作
async with barrier.update_item(pid, group, item_id):
    data = await prepare_data()  # 快速
    await save_data(data)        # 必须在锁内

# ❌ 避免：锁内做耗时操作
async with barrier.update_item(pid, group, item_id):
    data = await fetch_from_api()  # 耗时，不应在锁内
    await process_heavy(data)      # 耗时，不应在锁内
    await save_data(data)
```

### 3. 注意操作级别

```python
# 确保使用正确的阻挡位级别
async with barrier.update_item(pid, group, item_id):  # B5
    # 单条目更新 - 正确

# 错误示例：用 B5 做需要 B2 的操作
async with barrier.update_item(pid, group, item_id):  # B5
    await project_rename(pid)  # 需要 B2，错误！
```

---

## 相关模块

- `src/business/core/barrier_manager.py` - 阻挡位管理器实现
- `src/business/storage.py` - 存储层使用阻挡位
