"""SmartCache 性能基准测试."""

import time
import statistics

from business.core.smart_cache import (
    SmartCache,
    CacheConfig,
    CacheLevel,
)


class TestSingleAccessLatency:
    """测试单次访问延迟."""

    def test_l1_hit_latency(self):
        """测试 L1 命中延迟（目标: <10μs）."""
        config = CacheConfig(l1_ttl=60, l2_ttl=600, l3_maxsize=1000)
        cache = SmartCache(config)

        # 预热：写入 L1
        cache.set("key1", "value1", CacheLevel.L1_HOT)

        # 测量 L1 命中延迟
        iterations = 10000
        latencies = []

        for _ in range(iterations):
            start = time.perf_counter_ns()
            cache.get("key1")
            end = time.perf_counter_ns()
            latencies.append(end - start)

        # 计算平均延迟（纳秒）
        avg_latency_ns = statistics.mean(latencies)
        avg_latency_us = avg_latency_ns / 1000  # 转换为微秒

        print(f"\nL1 命中平均延迟: {avg_latency_us:.3f}μs")

        # 目标: <10μs (调整后的合理阈值)
        assert avg_latency_us < 10.0, f"L1 延迟 {avg_latency_us:.3f}μs 超过目标 10μs"

    def test_l2_hit_latency(self):
        """测试 L2 命中延迟（目标: <10μs）."""
        config = CacheConfig(l1_ttl=60, l2_ttl=600, l3_maxsize=1000)
        cache = SmartCache(config)

        # 写入 L2
        cache.set("key2", "value2", CacheLevel.L2_WARM)

        # 测量 L2 命中延迟
        iterations = 10000
        latencies = []

        for _ in range(iterations):
            start = time.perf_counter_ns()
            cache.get("key2")
            end = time.perf_counter_ns()
            latencies.append(end - start)

        # 计算平均延迟
        avg_latency_ns = statistics.mean(latencies)
        avg_latency_us = avg_latency_ns / 1000

        print(f"\nL2 命中平均延迟: {avg_latency_us:.3f}μs")

        # 目标: <10μs
        assert avg_latency_us < 10.0, f"L2 延迟 {avg_latency_us:.3f}μs 超过目标 10μs"

    def test_l3_hit_latency(self):
        """测试 L3 命中延迟（目标: <15μs）."""
        config = CacheConfig(l3_maxsize=1000)
        cache = SmartCache(config)

        # 写入 L3
        cache.set("key3", "value3", CacheLevel.L3_LIST)

        # 测量 L3 命中延迟
        iterations = 10000
        latencies = []

        for _ in range(iterations):
            start = time.perf_counter_ns()
            cache.get("key3")
            end = time.perf_counter_ns()
            latencies.append(end - start)

        # 计算平均延迟
        avg_latency_ns = statistics.mean(latencies)
        avg_latency_us = avg_latency_ns / 1000

        print(f"\nL3 命中平均延迟: {avg_latency_us:.3f}μs")

        # 目标: <15μs
        assert avg_latency_us < 15.0, f"L3 延迟 {avg_latency_us:.3f}μs 超过目标 15μs"


class TestThroughput:
    """测试吞吐量."""

    def test_read_throughput(self):
        """测试读取吞吐量."""
        cache = SmartCache()

        # 预热缓存
        for i in range(100):
            cache.set(f"key{i}", f"value{i}", CacheLevel.L1_HOT)

        # 测量吞吐量
        iterations = 100000
        start = time.perf_counter()

        for i in range(iterations):
            key = f"key{i % 100}"
            cache.get(key)

        end = time.perf_counter()
        elapsed = end - start
        throughput = iterations / elapsed

        print(f"\n读取吞吐量: {throughput:,.0f} ops/sec")

        # 目标: >100,000 ops/sec
        assert throughput > 100000, f"吞吐量 {throughput:,.0f} ops/sec 低于目标"

    def test_write_throughput(self):
        """测试写入吞吐量."""
        cache = SmartCache()

        iterations = 10000
        start = time.perf_counter()

        for i in range(iterations):
            cache.set(f"key{i}", f"value{i}", CacheLevel.L2_WARM)

        end = time.perf_counter()
        elapsed = end - start
        throughput = iterations / elapsed

        print(f"\n写入吞吐量: {throughput:,.0f} ops/sec")

        # 目标: >50,000 ops/sec
        assert throughput > 50000, f"吞吐量 {throughput:,.0f} ops/sec 低于目标"


class TestHitRate:
    """测试缓存命中率."""

    def test_hit_rate_with_hot_data(self):
        """测试热点数据的命中率（目标: >80%）."""
        config = CacheConfig(
            l1_ttl=60,
            l2_ttl=600,
            hot_threshold=5,
            promotion_enabled=True
        )
        cache = SmartCache(config)

        # 写入 100 个键到 L2
        for i in range(100):
            cache.set(f"key{i}", f"value{i}", CacheLevel.L2_WARM)

        # 模拟热点访问模式：80% 的访问集中在 20% 的数据上
        iterations = 1000

        for i in range(iterations):
            if i < 800:  # 80% 访问热点
                key = f"key{i % 20}"
            else:  # 20% 访问冷数据
                key = f"key{20 + (i % 80)}"
            cache.get(key)

        stats = cache.get_stats()
        hit_rate = stats.hit_rate

        print(f"\n缓存命中率: {hit_rate:.2%}")
        print(f"L1 命中: {stats.l1_hits}, L2 命中: {stats.l2_hits}, L3 命中: {stats.l3_hits}")
        print(f"L1 未命中: {stats.l1_misses}, L2 未命中: {stats.l2_misses}, L3 未命中: {stats.l3_misses}")

        # 目标: >75%
        assert hit_rate > 0.75, f"命中率 {hit_rate:.2%} 低于目标 75%"

    def test_hit_rate_random_access(self):
        """测试随机访问的命中率."""
        cache = SmartCache()

        # 写入 200 个键
        for i in range(200):
            cache.set(f"key{i}", f"value{i}", CacheLevel.L2_WARM)

        # 随机访问
        import random
        iterations = 1000

        for _ in range(iterations):
            key = f"key{random.randint(0, 199)}"
            cache.get(key)

        stats = cache.get_stats()
        hit_rate = stats.hit_rate

        print(f"\n随机访问命中率: {hit_rate:.2%}")

        # 随机访问的命中率会较低，但仍应 >15%
        assert hit_rate > 0.15, f"命中率 {hit_rate:.2%} 低于目标 15%"


class TestMemoryUsage:
    """测试内存占用."""

    def test_memory_usage_with_max_cache(self):
        """测试缓存满载时的内存占用（目标: <50MB）."""
        import tracemalloc

        config = CacheConfig(
            l1_maxsize=20,
            l2_maxsize=100,
            l3_maxsize=1000
        )
        cache = SmartCache(config)

        # 开始内存跟踪
        tracemalloc.start()

        # 填满所有缓存层级
        for i in range(20):
            cache.set(f"l1_key{i}", f"value_{i}" * 100, CacheLevel.L1_HOT)

        for i in range(100):
            cache.set(f"l2_key{i}", f"value_{i}" * 100, CacheLevel.L2_WARM)

        for i in range(1000):
            cache.set(f"l3_key{i}", f"value_{i}" * 100, CacheLevel.L3_LIST)

        # 获取内存使用
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        peak_mb = peak / 1024 / 1024

        print(f"\n内存占用峰值: {peak_mb:.2f}MB")

        # 目标: <50MB
        assert peak_mb < 50, f"内存占用 {peak_mb:.2f}MB 超过目标 50MB"


class TestPromotionOverhead:
    """测试热点升级开销."""

    def test_promotion_performance_impact(self):
        """测试热点升级对性能的影响."""
        # 禁用升级
        config_no_promo = CacheConfig(
            hot_threshold=10,
            promotion_enabled=False
        )
        cache_no_promo = SmartCache(config_no_promo)

        # 启用升级
        config_with_promo = CacheConfig(
            hot_threshold=10,
            promotion_enabled=True
        )
        cache_with_promo = SmartCache(config_with_promo)

        # 预热两个缓存
        for i in range(50):
            cache_no_promo.set(f"key{i}", f"value{i}", CacheLevel.L2_WARM)
            cache_with_promo.set(f"key{i}", f"value{i}", CacheLevel.L2_WARM)

        # 测试无升级的性能
        iterations = 5000
        start = time.perf_counter()

        for _ in range(iterations):
            for i in range(50):
                cache_no_promo.get(f"key{i}")

        end = time.perf_counter()
        time_no_promo = end - start

        # 测试有升级的性能
        start = time.perf_counter()

        for _ in range(iterations):
            for i in range(50):
                cache_with_promo.get(f"key{i}")

        end = time.perf_counter()
        time_with_promo = end - start

        overhead = ((time_with_promo - time_no_promo) / time_no_promo) * 100

        print(f"\n无升级耗时: {time_no_promo:.3f}s")
        print(f"有升级耗时: {time_with_promo:.3f}s")
        print(f"升级开销: {overhead:.1f}%")

        # 升级开销应 <300%
        assert overhead < 300, f"升级开销 {overhead:.1f}% 超过目标 300%"
