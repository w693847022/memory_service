"""SmartCache 单元测试."""

import time
import threading

from business.core.smart_cache import (
    SmartCache,
    CacheLevel,
)
from src.models.config import (
    CacheConfig,
    CacheL1Config,
    CacheL2Config,
    CacheL3Config,
)


class TestCacheBasics:
    """测试缓存基本功能."""

    def test_cache_get_set(self):
        """测试基本读写操作."""
        cache = SmartCache()

        # 写入 L2 缓存
        cache.set("key1", "value1", CacheLevel.L2_WARM)
        assert cache.get("key1") == "value1"

        # 写入 L1 缓存
        cache.set("key2", "value2", CacheLevel.L1_HOT)
        assert cache.get("key2") == "value2"

        # 写入 L3 缓存
        cache.set("key3", "value3", CacheLevel.L3_LIST)
        assert cache.get("key3") == "value3"

    def test_cache_get_missing_key(self):
        """测试读取不存在的键."""
        cache = SmartCache()
        assert cache.get("nonexistent") is None

    def test_cache_set_default_level(self):
        """测试默认写入层级."""
        cache = SmartCache()

        # 默认写入 L2
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
        assert "key1" in cache.l2_cache


class TestMultiLevelLookup:
    """测试多级缓存查询."""

    def test_multi_level_lookup_order(self):
        """测试 L1 → L2 → L3 查询顺序."""
        cache = SmartCache()

        # 同一个键写入不同层级
        cache.set("key1", "l1_value", CacheLevel.L1_HOT)
        cache.set("key1", "l2_value", CacheLevel.L2_WARM)
        cache.set("key1", "l3_value", CacheLevel.L3_LIST)

        # 应该返回 L1 的值（最先找到）
        assert cache.get("key1") == "l1_value"

    def test_l1_miss_l2_hit(self):
        """测试 L1 未命中，L2 命中."""
        cache = SmartCache()

        cache.set("key1", "value", CacheLevel.L2_WARM)
        assert cache.get("key1") == "value"

    def test_l1_l2_miss_l3_hit(self):
        """测试 L1、L2 未命中，L3 命中."""
        cache = SmartCache()

        cache.set("key1", "value", CacheLevel.L3_LIST)
        assert cache.get("key1") == "value"


class TestHotPromotion:
    """测试热点自动升级."""

    def test_hot_promotion_threshold(self):
        """测试达到阈值后自动升级."""
        config = CacheConfig(hot_threshold=5, promotion_enabled=True)
        cache = SmartCache(config)

        # 写入 L2
        cache.set("hot_key", "hot_value", CacheLevel.L2_WARM)

        # 访问 4 次，不应该升级
        for _ in range(4):
            cache.get("hot_key")
        assert "hot_key" not in cache.l1_cache

        # 第 5 次访问，应该升级到 L1
        cache.get("hot_key")
        assert "hot_key" in cache.l1_cache

    def test_hot_promotion_disabled(self):
        """测试禁用升级功能."""
        config = CacheConfig(hot_threshold=5, promotion_enabled=False)
        cache = SmartCache(config)

        cache.set("key1", "value", CacheLevel.L2_WARM)

        # 访问多次，不应该升级
        for _ in range(10):
            cache.get("key1")
        assert "key1" not in cache.l1_cache

    def test_promotion_stats(self):
        """测试升级统计."""
        config = CacheConfig(hot_threshold=3, promotion_enabled=True)
        cache = SmartCache(config)

        cache.set("key1", "value", CacheLevel.L2_WARM)

        # 触发升级
        for _ in range(3):
            cache.get("key1")

        stats = cache.get_stats()
        assert stats.promotions == 1


class TestCacheDeletion:
    """测试缓存删除."""

    def test_delete_from_all_levels(self):
        """测试从所有层级删除."""
        cache = SmartCache()

        # 写入所有层级
        cache.set("key1", "value", CacheLevel.L1_HOT)
        cache.set("key2", "value", CacheLevel.L2_WARM)
        cache.set("key3", "value", CacheLevel.L3_LIST)

        # 删除
        cache.delete("key1")
        cache.delete("key2")
        cache.delete("key3")

        assert cache.get("key1") is None
        assert cache.get("key2") is None
        assert cache.get("key3") is None

    def test_delete_nonexistent_key(self):
        """测试删除不存在的键."""
        cache = SmartCache()
        # 不应该抛出异常
        cache.delete("nonexistent")


class TestCacheClear:
    """测试缓存清空."""

    def test_clear_all_levels(self):
        """测试清空所有层级."""
        cache = SmartCache()

        cache.set("key1", "value1", CacheLevel.L1_HOT)
        cache.set("key2", "value2", CacheLevel.L2_WARM)
        cache.set("key3", "value3", CacheLevel.L3_LIST)

        cache.clear()

        assert len(cache.l1_cache) == 0
        assert len(cache.l2_cache) == 0
        assert len(cache.l3_cache) == 0

    def test_clear_specific_level(self):
        """测试清空指定层级."""
        cache = SmartCache()

        cache.set("key1", "value1", CacheLevel.L1_HOT)
        cache.set("key2", "value2", CacheLevel.L2_WARM)
        cache.set("key3", "value3", CacheLevel.L3_LIST)

        # 只清空 L1
        cache.clear(CacheLevel.L1_HOT)

        assert len(cache.l1_cache) == 0
        assert len(cache.l2_cache) == 1
        assert len(cache.l3_cache) == 1


class TestCacheStats:
    """测试缓存统计."""

    def test_cache_stats_initial(self):
        """测试初始统计."""
        cache = SmartCache()
        stats = cache.get_stats()

        assert stats.l1_hits == 0
        assert stats.l1_misses == 0
        assert stats.l2_hits == 0
        assert stats.l2_misses == 0
        assert stats.l3_hits == 0
        assert stats.l3_misses == 0
        assert stats.promotions == 0
        assert stats.hit_rate == 0.0

    def test_cache_stats_after_access(self):
        """测试访问后的统计."""
        cache = SmartCache()

        cache.set("key1", "value", CacheLevel.L1_HOT)
        cache.get("key1")  # L1 命中

        stats = cache.get_stats()
        assert stats.l1_hits == 1
        assert stats.l1_misses == 0  # L1 直接命中，无未命中

    def test_hit_rate_calculation(self):
        """测试命中率计算."""
        cache = SmartCache()

        cache.set("key1", "value", CacheLevel.L1_HOT)

        # 5 次命中
        for _ in range(5):
            cache.get("key1")

        # 5 次未命中
        for _ in range(5):
            cache.get("nonexistent")

        stats = cache.get_stats()
        # 5 L1命中 / (5 L1命中 + 5 L1未命中 + 5 L2未命中 + 5 L3未命中) = 5/20 = 0.25
        assert 0.24 < stats.hit_rate < 0.26

    def test_reset_stats(self):
        """测试重置统计."""
        cache = SmartCache()

        cache.set("key1", "value", CacheLevel.L1_HOT)
        cache.get("key1")

        cache.reset_stats()
        stats = cache.get_stats()

        assert stats.l1_hits == 0
        assert stats.l1_misses == 0


class TestThreadSafety:
    """测试线程安全."""

    def test_concurrent_access(self):
        """测试并发访问."""
        cache = SmartCache()
        cache.set("counter", 0, CacheLevel.L2_WARM)

        def increment():
            for _ in range(100):
                cache.get("counter")

        threads = [threading.Thread(target=increment) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        stats = cache.get_stats()
        assert stats.total_access == 1000


class TestTTLExpiration:
    """测试 TTL 过期."""

    def test_l1_ttl_expiration(self):
        """测试 L1 TTL 过期."""
        config = CacheConfig(l1=CacheL1Config(ttl=1))  # 1 秒过期
        cache = SmartCache(config)

        cache.set("key1", "value", CacheLevel.L1_HOT)
        assert cache.get("key1") == "value"

        # 等待过期
        time.sleep(1.5)
        assert cache.get("key1") is None

    def test_l2_ttl_expiration(self):
        """测试 L2 TTL 过期."""
        config = CacheConfig(l2=CacheL2Config(ttl=1))  # 1 秒过期
        cache = SmartCache(config)

        cache.set("key1", "value", CacheLevel.L2_WARM)
        assert cache.get("key1") == "value"

        # 等待过期
        time.sleep(1.5)
        assert cache.get("key1") is None


class TestLRUEviction:
    """测试 LRU 淘汰."""

    def test_l3_lru_eviction(self):
        """测试 L3 LRU 淘汰."""
        config = CacheConfig(l3=CacheL3Config(maxsize=2))
        cache = SmartCache(config)

        # 填满缓存
        cache.set("key1", "value1", CacheLevel.L3_LIST)
        cache.set("key2", "value2", CacheLevel.L3_LIST)

        # 访问 key1 使其更新为最近使用
        cache.get("key1")

        # 添加 key3，应该淘汰 key2
        cache.set("key3", "value3", CacheLevel.L3_LIST)

        assert cache.get("key1") == "value1"
        assert cache.get("key2") is None  # 被淘汰
        assert cache.get("key3") == "value3"


class TestConfigOverride:
    """测试配置覆盖."""

    def test_custom_config(self):
        """测试自定义配置."""
        config = CacheConfig(
            l1=CacheL1Config(ttl=10, maxsize=5),
            l2=CacheL2Config(ttl=100, maxsize=20),
            l3=CacheL3Config(maxsize=50),
            hot_threshold=3,
        )
        cache = SmartCache(config)

        assert cache._config.l1_ttl == 10
        assert cache._config.l1_maxsize == 5
        assert cache._config.l2_ttl == 100
        assert cache._config.l2_maxsize == 20
        assert cache._config.l3_maxsize == 50
        assert cache._config.hot_threshold == 3

    def test_default_config(self):
        """测试默认配置."""
        cache = SmartCache()

        assert cache._config.l1_ttl == 60
        assert cache._config.l1_maxsize == 20
        assert cache._config.l2_ttl == 600
        assert cache._config.l2_maxsize == 100
        assert cache._config.l3_maxsize == 1000
        assert cache._config.hot_threshold == 10
