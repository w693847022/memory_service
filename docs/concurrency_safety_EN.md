# Concurrency Safety Documentation

## Overview

AI Memory MCP implements a concurrency control mechanism based on **five-tier barriers** and **two-phase draining**, ensuring data consistency and operational safety in high-concurrency scenarios.

---

## Core Concepts

### Barrier

A barrier is a hierarchical lock mechanism where each business operation corresponds to a specific barrier level. Higher-level operations must wait for lower-level active operations to complete before executing.

### Drain

The drain mechanism ensures all lower-level active operations have finished before higher-level operations execute. It tracks active operations through counters and waits for them to reach zero.

---

## Five-Tier Barrier Architecture

```
┌─────────────────────────────────────────────────────────┐
│              Five-Tier Barrier System                   │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  B1: Service Level                                     │
│  ├─ register_project / remove_project                  │
│  └─ Global lock, affects all projects                  │
│                                                         │
│  B2: Project Scope Level                               │
│  ├─ project_rename / tag_delete / tag_merge            │
│  └─ Project-level lock, affects entire project         │
│                                                         │
│  B3: Tag/Group Definition Level                        │
│  ├─ tag_register/update, group_*                       │
│  └─ Project-level lock, affects tag/group definitions  │
│                                                         │
│  B4: Entry List Level                                  │
│  ├─ add_item / delete_item                             │
│  └─ Project+Group level lock, affects specific group   │
│                                                         │
│  B5: Entry ID Level                                    │
│  ├─ update_item / add/remove_item_tag                  │
│  └─ Project+Entry level lock, affects specific entry   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## Barrier Level Descriptions

### B1: Service Level

| Operation | Description | Scope |
|-----------|-------------|-------|
| `register_project` | Register new project | Global |
| `remove_project` | Delete project | Global, drain B4+B5 |

**Characteristics**:
- Single global lock
- Blocks all other project-related operations
- Requires draining all active operations when deleting

### B2: Project Scope Level

| Operation | Description | Scope |
|-----------|-------------|-------|
| `project_rename` | Rename project | Single project, drain B4+B5 |
| `tag_delete` | Delete tag | Single project, drain B4+B5 |
| `tag_merge` | Merge tags | Single project, drain B4+B5 |

**Characteristics**:
- Isolated per project
- Blocks all entry operations for that project
- Requires draining B4 and B5 active operations

### B3: Tag/Group Definition Level

| Operation | Description | Scope |
|-----------|-------------|-------|
| `tag_register` | Register tag | Tag definition in single project |
| `tag_update` | Update tag | Tag definition in single project |
| `group_create` | Create custom group | Group definition in single project |
| `group_update` | Update custom group | Group definition in single project |
| `group_delete` | Delete custom group | Single project, drain B4+B5 |
| `group_settings` | Update group settings | Group definition in single project |

**Characteristics**:
- Isolated per project
- Blocks tag/group structure changes for that project
- Requires draining active operations when deleting

### B4: Entry List Level

| Operation | Description | Scope |
|-----------|-------------|-------|
| `add_item` | Add entry | Specific group in single project |
| `delete_item` | Delete entry | Specific group in single project |

**Characteristics**:
- Isolated by `project+group`
- Increments active counter
- Allows concurrent operations on different groups

### B5: Entry ID Level

| Operation | Description | Scope |
|-----------|-------------|-------|
| `update_item` | Update entry | Specific entry in single project |
| `add_item_tag` | Add entry tag | Specific entry in single project |
| `remove_item_tag` | Remove entry tag | Specific entry in single project |

**Characteristics**:
- Isolated by `project+entry_id`
- Finest-grained lock
- Allows full concurrency on different entries

---

## Execution Flow

### Standard Flow

```
┌─────────────────────────────────────────────────────────┐
│                 Operation Execution Flow                │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  1. Upward Check                                        │
│     │                                                    │
│     ├─ Acquire higher-level locks in order             │
│     │  (B5 → B4 → B3 → B2 → B1)                         │
│     │                                                    │
│     ├─ Confirm no higher-level operation executing     │
│     │                                                    │
│     └─ Release higher-level locks                       │
│                                                         │
│  2. Acquire Own Barrier                                 │
│     │                                                    │
│     └─ Acquire lock for current operation's level      │
│                                                         │
│  3. Downward Drain                                      │
│     │                                                    │
│     ├─ Wait for lower-level active operations to zero  │
│     │  (for operations requiring drain)                 │
│     │                                                    │
│     └─ DrainCounter.wait_zero()                         │
│                                                         │
│  4. Execute Business Logic                              │
│     │                                                    │
│     ├─ Version check (if needed)                        │
│     │                                                    │
│     ├─ Acquire IO lock                                  │
│     │                                                    │
│     ├─ Execute actual operation                         │
│     │                                                    │
│     └─ Release IO lock                                  │
│                                                         │
│  5. Cleanup & Release                                   │
│     │                                                    │
│     ├─ Update version number                            │
│     │                                                    │
│     ├─ Decrement active counter                         │
│     │                                                    │
│     └─ Release own barrier                              │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Example: Update Entry (B5)

```python
async def update_item(project_id, group_name, item_id):
    # 1. Upward check
    await B1.acquire(); B1.release()          # Check service level
    await B2.acquire(); B2.release()          # Check project level
    await B3.acquire(); B3.release()          # Check tag/group level
    await B4.acquire(); B4.release()          # Check list level

    # 2. Acquire own lock
    await B5.acquire()

    # 3. Increment counter
    drain.increment("B5")

    try:
        # 4. Execute business logic
        # ... actual operation ...
        pass
    finally:
        # 5. Cleanup
        drain.decrement("B5")
        B5.release()
```

---

## Drain Mechanism

### DrainCounter

Active operation counter tracking B4/B5 level operations.

```python
class DrainCounter:
    def __init__(self):
        self.B4_active: int = 0      # B4 active operations
        self.B5_active: int = 0      # B5 active operations
        self._cond = asyncio.Condition()

    async def wait_zero(self, *levels):
        """Wait for specified level active counts to reach zero"""
        async with self._cond:
            while not all(count == 0 for count in levels):
                await self._cond.wait()
```

### Drain Usage Scenarios

| Operation | Requires Drain | Reason |
|-----------|----------------|--------|
| `remove_project` | B4 + B5 | Ensure all entry operations finish before deletion |
| `project_rename` | B4 + B5 | Ensure no entry modifications during rename |
| `tag_delete` | B4 + B5 | Ensure entries don't reference tag before deletion |
| `tag_merge` | B4 + B5 | Ensure entry operations complete before merge |
| `group_delete` | B4 + B5 | Ensure entry operations complete before deletion |

---

## Concurrency Examples

### Scenario 1: Concurrent Updates to Different Entries

```
Timeline:
T1: Request A updates entry item_1 (acquires B5_item_1 lock)
T2: Request B updates entry item_2 (acquires B5_item_2 lock)
T3: Request A executes update
T4: Request B executes update

Result: ✅ Concurrent execution, no interference
```

### Scenario 2: Project Deletion with Drain

```
Timeline:
T1: Request A updates entry item_1 (B5 active +1)
T2: Request B deletes project (needs to drain B4+B5)
T3: Request B waits for B5 to reach zero...
T4: Request A completes update (B5 active -1)
T5: Request B detects B5=0, proceeds with deletion

Result: ✅ Safe deletion, no operations missed
```

### Scenario 3: Project Rename Conflict

```
Timeline:
T1: Request A adds entry (B4 active +1)
T2: Request B renames project (needs to drain B4+B5)
T3: Request B waits for B4 to reach zero...
T4: Request A completes addition (B4 active -1)
T5: Request B detects B4=0, proceeds with rename

Result: ✅ Rename executes when no active operations
```

---

## API Usage

### Basic Usage

```python
from business.core.barrier_manager import BarrierManager

# Initialize barrier manager
barrier = BarrierManager()

# Update entry (B5)
async with barrier.update_item(project_id, group_name, item_id):
    # Execute update operation
    await update_item_data(...)
```

### Operation Level Reference

```python
# B1: Service Level
async with barrier.register_project():
    # Register project
    pass

async with barrier.remove_project(project_id):
    # Delete project
    pass

# B2: Project Scope Level
async with barrier.project_rename(project_id):
    # Rename project
    pass

async with barrier.tag_delete(project_id):
    # Delete tag
    pass

# B3: Tag/Group Definition Level
async with barrier.tag_register(project_id):
    # Register tag
    pass

async with barrier.group_create(project_id):
    # Create custom group
    pass

# B4: Entry List Level
async with barrier.add_item(project_id, group_name):
    # Add entry
    pass

async with barrier.delete_item(project_id, group_name, item_id):
    # Delete entry
    pass

# B5: Entry ID Level
async with barrier.update_item(project_id, group_name, item_id):
    # Update entry
    pass

async with barrier.add_item_tag(project_id, group_name, item_id):
    # Add entry tag
    pass
```

---

## Lock Cleanup

### Automatic Cleanup

Some operations automatically clean up unneeded locks:

```python
# Clean up B5 lock after deleting entry
async with barrier.delete_item(pid, group, item_id):
    ...
# Auto: barrier.cleanup_B5(item_id)

# Clean up B4 lock after deleting group
async with barrier.group_delete(pid, group_name):
    ...
# Auto: barrier.cleanup_B4(group_name)

# Clean up all locks after deleting project
async with barrier.remove_project(project_id):
    ...
# Auto: barrier.remove_project_barriers(project_id)
```

### Manual Cleanup

```python
# Clean up specific entry lock
barrier._get_pb(project_id).cleanup_B5(item_id)

# Clean up specific group lock
barrier._get_pb(project_id).cleanup_B4(group_name)

# Clean up all project locks
barrier.remove_project_barriers(project_id)
```

---

## Best Practices

### 1. Use Context Manager

```python
# ✅ Recommended: Use async with
async with barrier.update_item(pid, group, item_id):
    await do_update()

# ❌ Avoid: Manual lock management
await barrier._B1.acquire()
try:
    await do_something()
finally:
    await barrier._B1.release()
```

### 2. Minimize Lock Hold Time

```python
# ✅ Recommended: Only necessary operations in lock
async with barrier.update_item(pid, group, item_id):
    data = await prepare_data()  # Fast
    await save_data(data)        # Must be in lock

# ❌ Avoid: Expensive operations in lock
async with barrier.update_item(pid, group, item_id):
    data = await fetch_from_api()  # Slow, shouldn't be in lock
    await process_heavy(data)      # Slow, shouldn't be in lock
    await save_data(data)
```

### 3. Use Correct Operation Level

```python
# Ensure correct barrier level
async with barrier.update_item(pid, group, item_id):  # B5
    # Single entry update - Correct

# Wrong example: Using B5 for B2 operation
async with barrier.update_item(pid, group, item_id):  # B5
    await project_rename(pid)  # Requires B2, Wrong!
```

---

## Related Modules

- `src/business/core/barrier_manager.py` - Barrier manager implementation
- `src/business/storage.py` - Storage layer using barriers
