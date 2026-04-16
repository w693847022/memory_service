"""
智能分层缓存模块

实现 L1/L2/L3 三层缓存架构:
- L1: 热点数据 (TTL 60s, maxsize 20)
- L2: 常规数据 (TTL 600s, maxsize 100)
- L3: 项目列表 (LRU, maxsize 1000)

支持热点自动识别与升级机制。
"""

from cachetools import TTLCache, LRUCache
from typing import Optional, Any, Dict
import threading

from src.models.config import CacheConfig, CacheStats
from src.models.enums import CacheLevel


class SmartCache:
    """
    分层智能缓存策略

    三层架构:
    - L1: 热点数据 (TTL 60s, maxsize 20)
    - L2: 常规数据 (TTL 600s, maxsize 100)
    - L3: 项目列表 (LRU, maxsize 1000)

    特性:
    - 多级缓存查询 (L1 → L2 → L3)
    - 热点自动识别与升级
    - 线程安全的访问统计
    - 缓存统计信息
    """

    def __init__(self, config: Optional[CacheConfig] = None):
        """
        初始化智能缓存

        Args:
            config: 缓存配置，为 None 时使用默认配置
        """
        self._config = config or CacheConfig()

        # L1: 热点缓存
        self._l1_cache = TTLCache(
            maxsize=self._config.l1_maxsize,
            ttl=self._config.l1_ttl
        )

        # L2: 常规缓存
        self._l2_cache = TTLCache(
            maxsize=self._config.l2_maxsize,
            ttl=self._config.l2_ttl
        )

        # L3: 列表缓存 (LRU)
        self._l3_cache = LRUCache(maxsize=self._config.l3_maxsize)

        # 访问统计 (线程安全)
        self._access_count: Dict[str, int] = {}
        self._lock = threading.RLock()

        # 缓存统计
        self._stats = CacheStats()

    def get(self, key: str) -> Optional[Any]:
        """
        多级缓存查询

        查询顺序: L1 → L2 → L3

        Args:
            key: 缓存键

        Returns:
            缓存值，未命中返回 None
        """
        self._stats.total_access += 1

        # 1. 先查 L1
        if key in self._l1_cache:
            self._stats.l1_hits += 1
            self._record_access(key)
            return self._l1_cache[key]
        self._stats.l1_misses += 1

        # 2. 再查 L2
        if key in self._l2_cache:
            self._stats.l2_hits += 1
            self._record_access(key)
            data = self._l2_cache[key]
            # 热升级：移到 L1
            if self._config.promotion_enabled:
                self._promote_to_l1(key, data)
            return data
        self._stats.l2_misses += 1

        # 3. 最后查 L3
        if key in self._l3_cache:
            self._stats.l3_hits += 1
            self._record_access(key)
            return self._l3_cache[key]
        self._stats.l3_misses += 1

        return None

    def set(self, key: str, value: Any, level: CacheLevel = CacheLevel.L2_WARM) -> None:
        """
        写入缓存

        Args:
            key: 缓存键
            value: 缓存值
            level: 目标层级
        """
        if level == CacheLevel.L1_HOT:
            self._l1_cache[key] = value
        elif level == CacheLevel.L2_WARM:
            self._l2_cache[key] = value
        elif level == CacheLevel.L3_LIST:
            self._l3_cache[key] = value

    def delete(self, key: str) -> None:
        """
        从所有层级删除缓存

        Args:
            key: 缓存键
        """
        self._l1_cache.pop(key, None)
        self._l2_cache.pop(key, None)
        self._l3_cache.pop(key, None)
        with self._lock:
            self._access_count.pop(key, None)

    def clear(self, level: Optional[CacheLevel] = None) -> None:
        """
        清空缓存

        Args:
            level: 指定层级，为 None 时清空所有层级
        """
        if level is None or level == CacheLevel.L1_HOT:
            self._l1_cache.clear()
        if level is None or level == CacheLevel.L2_WARM:
            self._l2_cache.clear()
        if level is None or level == CacheLevel.L3_LIST:
            self._l3_cache.clear()
        if level is None:
            with self._lock:
                self._access_count.clear()

    def get_stats(self) -> CacheStats:
        """
        获取缓存统计

        Returns:
            CacheStats 对象的副本
        """
        # 返回副本以避免外部修改
        return CacheStats(
            l1_hits=self._stats.l1_hits,
            l1_misses=self._stats.l1_misses,
            l2_hits=self._stats.l2_hits,
            l2_misses=self._stats.l2_misses,
            l3_hits=self._stats.l3_hits,
            l3_misses=self._stats.l3_misses,
            promotions=self._stats.promotions,
            total_access=self._stats.total_access
        )

    def reset_stats(self) -> None:
        """重置统计计数器"""
        self._stats = CacheStats()

    def _record_access(self, key: str) -> None:
        """记录访问统计（线程安全）"""
        with self._lock:
            self._access_count[key] = self._access_count.get(key, 0) + 1

    def _promote_to_l1(self, key: str, value: Any) -> None:
        """将热数据升级到 L1"""
        with self._lock:
            if self._access_count.get(key, 0) >= self._config.hot_threshold:
                self._l1_cache[key] = value
                self._stats.promotions += 1

    # 保留对内部缓存的访问，用于兼容性
    @property
    def l1_cache(self) -> TTLCache:
        """获取 L1 缓存（只读）"""
        return self._l1_cache

    @property
    def l2_cache(self) -> TTLCache:
        """获取 L2 缓存（只读）"""
        return self._l2_cache

    @property
    def l3_cache(self) -> LRUCache:
        """获取 L3 缓存（只读）"""
        return self._l3_cache
