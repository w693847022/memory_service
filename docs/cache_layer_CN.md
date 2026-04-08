# 缓存层说明

## 概述

AI Memory MCP 实现了三层智能缓存架构，通过多级缓存和热点自动识别机制，有效提升系统性能并减少磁盘 I/O。

---

## 三层缓存架构

### L1: 热点缓存 (Hot Cache)

| 参数 | 配置值 | 说明 |
|------|--------|------|
| **类型** | TTLCache | 带过期时间的缓存 |
| **容量** | 20 个条目 | 只存储最热的数据 |
| **TTL** | 60 秒 | 短过期时间 |
| **用途** | 存储高频访问的项目数据 |

### L2: 常规缓存 (Warm Cache)

| 参数 | 配置值 | 说明 |
|------|--------|------|
| **类型** | TTLCache | 带过期时间的缓存 |
| **容量** | 100 个条目 | 存储常用数据 |
| **TTL** | 600 秒 (10分钟) | 中等过期时间 |
| **用途** | 存储常规访问的项目数据 |

### L3: 列表缓存 (List Cache)

| 参数 | 配置值 | 说明 |
|------|--------|------|
| **类型** | LRUCache | 最近最少使用淘汰 |
| **容量** | 1000 个条目 | 大容量存储 |
| **淘汰策略** | LRU | 淘汰最久未使用的数据 |
| **用途** | 存储项目列表等集合数据 |

---

## 查询流程

```
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌──────────┐
│  请求   │───→│   L1    │───→│   L2    │───→│   L3     │───→│ 磁盘读取 │
└─────────┘    │  检查   │    │  检查   │    │  检查    │    └──────────┘
               └─────────┘    └─────────┘    └─────────┘
                    │              │              │
                    ▼              ▼              ▼
               ┌─────────┐    ┌─────────┐    ┌─────────┐
               │ 命中:   │    │ 命中:   │    │ 命中:   │
               │ 返回    │    │ 升级到L1│    │ 返回    │
               │ 记录访问│    │ 记录访问│    │ 记录访问│
               └─────────┘    └─────────┘    └─────────┘
```

### 查询顺序

1. **L1 热点缓存** - 最快，命中后直接返回
2. **L2 常规缓存** - 中速，命中后升级到 L1
3. **L3 列表缓存** - 低速，命中后返回
4. **磁盘读取** - 最慢，未命中时读取存储

---

## 热点自动识别与升级

### 升级机制

```
┌─────────────────────────────────────────────────────┐
│                热点识别流程                          │
├─────────────────────────────────────────────────────┤
│                                                     │
│  数据在 L2 缓存                                     │
│         │                                           │
│         ▼                                           │
│  每次访问计数 +1                                    │
│         │                                           │
│         ▼                                           │
│  计数 ≥ 10 次（可配置阈值）                         │
│         │                                           │
│         ▼                                           │
│  自动升级到 L1 热点缓存                             │
│         │                                           │
│         ▼                                           │
│  后续访问直接从 L1 获取（更快）                      │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### 配置参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `hot_threshold` | 10 次 | 升级为热点所需的访问次数 |
| `promotion_enabled` | True | 是否启用自动升级 |

### 线程安全

- 访问计数使用 `RLock` 保护
- 升级操作在锁内执行
- 统计数据原子更新

---

## 缓存配置

### CacheConfig 类

```python
@dataclass
class CacheConfig:
    # L1: 热点缓存
    l1_ttl: int = 60           # 60秒
    l1_maxsize: int = 20       # 最多20个

    # L2: 常规缓存
    l2_ttl: int = 600          # 10分钟
    l2_maxsize: int = 100      # 最多100个

    # L3: 列表缓存 (LRU)
    l3_maxsize: int = 1000     # 最多1000个

    # 热点识别
    hot_threshold: int = 10    # 访问10次升级为热点
    promotion_enabled: bool = True  # 是否启用自动升级
```

### 自定义配置

```python
from business.core.smart_cache import SmartCache, CacheConfig

# 自定义配置
config = CacheConfig(
    l1_ttl=120,              # L1 TTL 改为 2 分钟
    l1_maxsize=50,           # L1 容量改为 50
    hot_threshold=5,         # 5 次访问即升级
    promotion_enabled=True
)

cache = SmartCache(config=config)
```

---

## 缓存统计

### CacheStats 类

```python
@dataclass
class CacheStats:
    l1_hits: int = 0         # L1 命中次数
    l1_misses: int = 0       # L1 未命中次数
    l2_hits: int = 0         # L2 命中次数
    l2_misses: int = 0       # L2 未命中次数
    l3_hits: int = 0         # L3 命中次数
    l3_misses: int = 0       # L3 未命中次数
    promotions: int = 0      # L2→L1 升级次数
    total_access: int = 0    # 总访问次数

    @property
    def hit_rate(self) -> float:  # 缓存命中率
        ...
```

### 查看统计

```python
# 获取统计信息
stats = cache.get_stats()
print(f"命中率: {stats.hit_rate:.2%}")
print(f"L2→L1 升级: {stats.promotions} 次")
print(f"总访问: {stats.total_access} 次")

# 重置统计
cache.reset_stats()
```

---

## API 使用

### 基本操作

```python
from business.core.smart_cache import SmartCache, CacheLevel

# 初始化缓存
cache = SmartCache()

# 写入缓存（默认 L2）
cache.set("project:abc", project_data)

# 写入到指定层级
cache.set("project:abc", project_data, level=CacheLevel.L1_HOT)

# 读取缓存（自动查询 L1 → L2 → L3）
data = cache.get("project:abc")

# 删除缓存（从所有层级删除）
cache.delete("project:abc")

# 清空指定层级
cache.clear(level=CacheLevel.L2_WARM)

# 清空所有层级
cache.clear()
```

---

## 性能优化建议

### 1. 合理设置 TTL

| 场景 | 建议 TTL | 原因 |
|------|----------|------|
| 高频访问项目 | 60-120 秒 | 保持热度 |
| 常规项目 | 300-600 秒 | 平衡性能和一致性 |
| 低频项目 | 600+ 秒 | 减少 I/O |

### 2. 监控缓存命中率

```python
stats = cache.get_stats()
if stats.hit_rate < 0.7:
    # 命中率低于 70%，考虑调整配置
    pass
```

### 3. 及时清理无用缓存

```python
# 删除项目时清理缓存
cache.delete(f"project:{project_id}")
```

---

## 最佳实践

1. **热点数据预加载**
   ```python
   # 系统启动时预加载常用项目
   for pid in active_project_ids:
       cache.set(f"project:{pid}", load_project(pid))
   ```

2. **批量操作后清空**
   ```python
   # 批量更新后清空相关缓存
   cache.clear(level=CacheLevel.L2_WARM)
   ```

3. **定期查看统计**
   ```python
   # 定期输出统计信息用于调优
   import logging
   stats = cache.get_stats()
   logging.info(f"缓存统计: 命中率={stats.hit_rate:.2%}")
   ```

---

## 相关模块

- `src/business/core/smart_cache.py` - 缓存层实现
- `src/business/core/storage_base.py` - 存储层使用缓存
