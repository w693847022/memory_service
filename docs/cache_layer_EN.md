# Cache Layer Documentation

## Overview

AI Memory MCP implements a three-tier smart caching architecture with multi-level caching and automatic hotspot detection, effectively improving system performance and reducing disk I/O.

---

## Three-Tier Cache Architecture

### L1: Hot Cache

| Parameter | Value | Description |
|-----------|-------|-------------|
| **Type** | TTLCache | Time-based expiration cache |
| **Capacity** | 20 entries | Stores only hottest data |
| **TTL** | 60 seconds | Short expiration |
| **Purpose** | High-frequency project data |

### L2: Warm Cache

| Parameter | Value | Description |
|-----------|-------|-------------|
| **Type** | TTLCache | Time-based expiration cache |
| **Capacity** | 100 entries | Stores commonly used data |
| **TTL** | 600 seconds (10 min) | Medium expiration |
| **Purpose** | Regular access project data |

### L3: List Cache

| Parameter | Value | Description |
|-----------|-------|-------------|
| **Type** | LRUCache | Least Recently Used eviction |
| **Capacity** | 1000 entries | Large capacity storage |
| **Eviction** | LRU | Evicts least recently used |
| **Purpose** | Project lists and collections |

---

## Query Flow

```
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌──────────┐
│ Request │───→│   L1    │───→│   L2    │───→│   L3     │───→│ Disk Read │
└─────────┘    │  Check  │    │  Check  │    │  Check   │    └──────────┘
               └─────────┘    └─────────┘    └─────────┘
                    │              │              │
                    ▼              ▼              ▼
               ┌─────────┐    ┌─────────┐    ┌─────────┐
               │ Hit:    │    │ Hit:    │    │ Hit:    │
               │ Return  │    │ Promote │    │ Return  │
               │ Record  │    │ to L1   │    │ Record  │
               └─────────┘    └─────────┘    └─────────┘
```

### Query Order

1. **L1 Hot Cache** - Fastest, return on hit
2. **L2 Warm Cache** - Medium, promote to L1 on hit
3. **L3 List Cache** - Slow, return on hit
4. **Disk Read** - Slowest, read from storage on miss

---

## Hotspot Detection & Promotion

### Promotion Mechanism

```
┌─────────────────────────────────────────────────────┐
│              Hotspot Detection Flow                  │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Data in L2 Cache                                   │
│         │                                           │
│         ▼                                           │
│  Access count +1 per visit                          │
│         │                                           │
│         ▼                                           │
│  Count ≥ 10 (configurable threshold)                │
│         │                                           │
│         ▼                                           │
│  Auto-promote to L1 Hot Cache                       │
│         │                                           │
│         ▼                                           │
│  Future accesses served from L1 (faster)            │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### Configuration Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `hot_threshold` | 10 | Access count to promote to hot |
| `promotion_enabled` | True | Enable auto-promotion |

### Thread Safety

- Access counter protected by `RLock`
- Promotion operation executes within lock
- Statistics updated atomically

---

## Cache Configuration

### CacheConfig Class

```python
@dataclass
class CacheConfig:
    # L1: Hot cache
    l1_ttl: int = 60           # 60 seconds
    l1_maxsize: int = 20       # Max 20 entries

    # L2: Warm cache
    l2_ttl: int = 600          # 10 minutes
    l2_maxsize: int = 100      # Max 100 entries

    # L3: List cache (LRU)
    l3_maxsize: int = 1000     # Max 1000 entries

    # Hotspot detection
    hot_threshold: int = 10    # Promote after 10 accesses
    promotion_enabled: bool = True  # Enable auto-promotion
```

### Custom Configuration

```python
from business.core.smart_cache import SmartCache, CacheConfig

# Custom configuration
config = CacheConfig(
    l1_ttl=120,              # L1 TTL to 2 minutes
    l1_maxsize=50,           # L1 capacity to 50
    hot_threshold=5,         # Promote after 5 accesses
    promotion_enabled=True
)

cache = SmartCache(config=config)
```

---

## Cache Statistics

### CacheStats Class

```python
@dataclass
class CacheStats:
    l1_hits: int = 0         # L1 hit count
    l1_misses: int = 0       # L1 miss count
    l2_hits: int = 0         # L2 hit count
    l2_misses: int = 0       # L2 miss count
    l3_hits: int = 0         # L3 hit count
    l3_misses: int = 0       # L3 miss count
    promotions: int = 0      # L2→L1 promotion count
    total_access: int = 0    # Total access count

    @property
    def hit_rate(self) -> float:  # Cache hit rate
        ...
```

### Viewing Statistics

```python
# Get statistics
stats = cache.get_stats()
print(f"Hit rate: {stats.hit_rate:.2%}")
print(f"L2→L1 promotions: {stats.promotions}")
print(f"Total accesses: {stats.total_access}")

# Reset statistics
cache.reset_stats()
```

---

## API Usage

### Basic Operations

```python
from business.core.smart_cache import SmartCache, CacheLevel

# Initialize cache
cache = SmartCache()

# Write to cache (default L2)
cache.set("project:abc", project_data)

# Write to specific level
cache.set("project:abc", project_data, level=CacheLevel.L1_HOT)

# Read from cache (auto query L1 → L2 → L3)
data = cache.get("project:abc")

# Delete from cache (all levels)
cache.delete("project:abc")

# Clear specific level
cache.clear(level=CacheLevel.L2_WARM)

# Clear all levels
cache.clear()
```

---

## Performance Optimization Tips

### 1. Set Appropriate TTL

| Scenario | Suggested TTL | Reason |
|----------|---------------|--------|
| High-frequency projects | 60-120 sec | Maintain hotness |
| Regular projects | 300-600 sec | Balance performance vs consistency |
| Low-frequency projects | 600+ sec | Reduce I/O |

### 2. Monitor Cache Hit Rate

```python
stats = cache.get_stats()
if stats.hit_rate < 0.7:
    # Hit rate below 70%, consider adjusting config
    pass
```

### 3. Clean Up Unused Cache

```python
# Clean cache when deleting project
cache.delete(f"project:{project_id}")
```

---

## Best Practices

1. **Preload Hot Data**
   ```python
   # Preload frequently used projects on startup
   for pid in active_project_ids:
       cache.set(f"project:{pid}", load_project(pid))
   ```

2. **Clear After Batch Operations**
   ```python
   # Clear related cache after batch updates
   cache.clear(level=CacheLevel.L2_WARM)
   ```

3. **Regular Statistics Review**
   ```python
   # Periodically log statistics for tuning
   import logging
   stats = cache.get_stats()
   logging.info(f"Cache stats: hit_rate={stats.hit_rate:.2%}")
   ```

---

## Related Modules

- `src/business/core/smart_cache.py` - Cache layer implementation
- `src/business/core/storage_base.py` - Storage layer using cache
