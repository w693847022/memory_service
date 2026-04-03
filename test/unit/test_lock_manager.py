"""OptimisticLockManager 单元测试."""

import threading
import time
import pytest
from business.core.lock_manager import (
    OptimisticLockManager,
    LockResult,
    LockGranularity
)


class TestOptimisticLockManager:
    """OptimisticLockManager 单元测试."""

    def test_lock_key_generation(self):
        """测试锁键生成."""
        mgr = OptimisticLockManager()

        # 测试不同粒度的键格式
        assert mgr._make_project_key("pid123") == "p:pid123"
        assert mgr._make_group_key("pid123", "features") == "g:pid123:features"
        assert mgr._make_item_key("pid123", "features", "feat_001") == "i:pid123:features:feat_001"
        assert mgr._make_tag_key("pid123", "python") == "t:pid123:python"

    def test_try_acquire_project_success(self):
        """测试非阻塞获取项目级锁成功."""
        mgr = OptimisticLockManager()
        result = mgr.try_acquire_project("pid123")

        assert result.success is True
        assert result.acquired is True
        assert result.lock is not None
        assert result.error is None

        # 清理
        mgr.release_project("pid123")

    def test_try_acquire_group_success(self):
        """测试非阻塞获取分组级锁成功."""
        mgr = OptimisticLockManager()
        result = mgr.try_acquire_group("pid123", "features")

        assert result.success is True
        assert result.acquired is True
        assert result.lock is not None

        # 清理
        mgr.release_group("pid123", "features")

    def test_try_acquire_item_success(self):
        """测试非阻塞获取条目级锁成功."""
        mgr = OptimisticLockManager()
        result = mgr.try_acquire_item("pid123", "features", "feat_001")

        assert result.success is True
        assert result.acquired is True
        assert result.lock is not None

        # 清理
        mgr.release_item("pid123", "features", "feat_001")

    def test_try_acquire_tag_success(self):
        """测试非阻塞获取标签级锁成功."""
        mgr = OptimisticLockManager()
        result = mgr.try_acquire_tag("pid123", "python")

        assert result.success is True
        assert result.acquired is True
        assert result.lock is not None

        # 清理
        mgr.release_tag("pid123", "python")

    def test_try_acquire_item_blocking(self):
        """测试非阻塞获取条目级锁失败."""
        mgr = OptimisticLockManager()

        # 第一次获取
        result1 = mgr.try_acquire_item("pid", "features", "feat_001")
        assert result1.acquired is True

        # 第二次获取（应该失败）
        result2 = mgr.try_acquire_item("pid", "features", "feat_001")
        assert result2.acquired is False
        assert result2.error == "lock_held"
        assert result2.retryable is True
        assert result2.error_message is not None

        # 清理
        mgr.release_item("pid", "features", "feat_001")

    def test_context_manager_item_success(self):
        """测试条目级锁上下文管理器."""
        mgr = OptimisticLockManager()

        with mgr.acquire_item("pid", "features", "feat_001") as result:
            assert result.acquired is True
            assert result.lock is not None

        # 上下文退出后锁应该释放
        result2 = mgr.try_acquire_item("pid", "features", "feat_001")
        assert result2.acquired is True

        mgr.release_item("pid", "features", "feat_001")

    def test_context_manager_item_blocking(self):
        """测试条目级锁上下文管理器被阻塞."""
        mgr = OptimisticLockManager()

        # 手动获取锁
        result1 = mgr.try_acquire_item("pid", "features", "feat_001")
        assert result1.acquired is True

        # 上下文管理器应该获取失败
        with mgr.acquire_item("pid", "features", "feat_001") as result:
            assert result.acquired is False
            assert result.error == "lock_held"
            assert result.retryable is True

        # 清理
        mgr.release_item("pid", "features", "feat_001")

    def test_context_manager_exception(self):
        """测试上下文管理器异常时释放锁."""
        mgr = OptimisticLockManager()

        try:
            with mgr.acquire_item("pid", "features", "feat_001") as result:
                assert result.acquired is True
                raise ValueError("测试异常")
        except ValueError:
            pass

        # 异常后锁应该释放
        result = mgr.try_acquire_item("pid", "features", "feat_001")
        assert result.acquired is True

        mgr.release_item("pid", "features", "feat_001")

    def test_cross_layer_no_conflict(self):
        """测试跨层级锁不冲突."""
        mgr = OptimisticLockManager()

        # 同时获取不同层级的锁
        r1 = mgr.try_acquire_project("pid123")
        r2 = mgr.try_acquire_group("pid123", "features")
        r3 = mgr.try_acquire_item("pid123", "features", "feat_001")
        r4 = mgr.try_acquire_tag("pid123", "python")

        # 所有锁都应该获取成功
        assert r1.acquired is True
        assert r2.acquired is True
        assert r3.acquired is True
        assert r4.acquired is True

        # 清理
        mgr.release_project("pid123")
        mgr.release_group("pid123", "features")
        mgr.release_item("pid123", "features", "feat_001")
        mgr.release_tag("pid123", "python")

    def test_double_checked_locking(self):
        """测试双重检查锁定（并发安全性）."""
        mgr = OptimisticLockManager()
        results = []

        def acquire_lock():
            result = mgr.try_acquire_item("pid", "features", "feat_001")
            results.append(result.acquired)
            if result.acquired:
                time.sleep(0.01)
                mgr.release_item("pid", "features", "feat_001")

        threads = [threading.Thread(target=acquire_lock) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 只有一个线程应该获取成功
        assert sum(results) == 1

    def test_cleanup_item_lock(self):
        """测试条目锁清理."""
        mgr = OptimisticLockManager()

        # 获取锁
        result = mgr.try_acquire_item("pid", "features", "feat_001")
        assert result.acquired is True
        mgr.release_item("pid", "features", "feat_001")

        # 清理锁
        mgr.cleanup_item_lock("pid", "features", "feat_001")

        # 锁应该不存在
        assert "i:pid:features:feat_001" not in mgr._item_locks

    def test_cleanup_group_locks(self):
        """测试分组锁清理."""
        mgr = OptimisticLockManager()

        # 创建分组锁和条目锁
        mgr.try_acquire_group("pid", "features")
        mgr.release_group("pid", "features")
        mgr.try_acquire_item("pid", "features", "feat_001")
        mgr.release_item("pid", "features", "feat_001")

        # 清理分组锁
        mgr.cleanup_group_locks("pid", "features")

        # 验证清理
        assert "g:pid:features" not in mgr._group_locks
        assert "i:pid:features:feat_001" not in mgr._item_locks

    def test_cleanup_tag_lock(self):
        """测试标签锁清理."""
        mgr = OptimisticLockManager()

        # 获取锁
        result = mgr.try_acquire_tag("pid", "python")
        assert result.acquired is True
        mgr.release_tag("pid", "python")

        # 清理锁
        mgr.cleanup_tag_lock("pid", "python")

        # 锁应该不存在
        assert "t:pid:python" not in mgr._tag_locks

    def test_cleanup_project_locks(self):
        """测试项目锁清理."""
        mgr = OptimisticLockManager()

        # 创建多个锁
        mgr.try_acquire_project("pid123")
        mgr.release_project("pid123")
        mgr.try_acquire_group("pid123", "features")
        mgr.release_group("pid123", "features")
        mgr.try_acquire_item("pid123", "features", "feat_001")
        mgr.release_item("pid123", "features", "feat_001")
        mgr.try_acquire_tag("pid123", "python")
        mgr.release_tag("pid123", "python")

        # 清理项目所有锁
        mgr.cleanup_project_locks("pid123")

        # 验证清理
        assert "p:pid123" not in mgr._project_locks
        assert not any(k.startswith("g:pid123:") for k in mgr._group_locks)
        assert not any(k.startswith("i:pid123:") for k in mgr._item_locks)
        assert not any(k.startswith("t:pid123:") for k in mgr._tag_locks)

    def test_context_manager_with_current_data(self):
        """测试上下文管理器携带当前数据."""
        mgr = OptimisticLockManager()
        current_data = {"version": 5, "content": "test"}

        with mgr.acquire_item(
            "pid", "features", "feat_001",
            current_version=5,
            current_data=current_data
        ) as result:
            assert result.acquired is True
            assert result.current_version == 5
            assert result.current_data == current_data

        # 上下文管理器会自动释放锁，不需要手动释放

    def test_concurrent_same_layer_different_keys(self):
        """测试同层级不同键的并发获取."""
        mgr = OptimisticLockManager()
        results = []

        def acquire_lock(item_id):
            result = mgr.try_acquire_item("pid", "features", item_id)
            results.append(result.acquired)
            if result.acquired:
                time.sleep(0.01)
                mgr.release_item("pid", "features", item_id)

        # 同时获取不同条目的锁
        item_ids = ["feat_001", "feat_002", "feat_003"]
        threads = [threading.Thread(target=acquire_lock, args=(item_id,)) for item_id in item_ids]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 所有都应该成功（不同条目的锁）
        assert sum(results) == 3

    def test_release_nonexistent_lock(self):
        """测试释放不存在的锁（不报错）."""
        mgr = OptimisticLockManager()

        # 释放不存在的锁，应该不报错
        mgr.release_project("nonexistent")
        mgr.release_group("nonexistent", "features")
        mgr.release_item("nonexistent", "features", "feat_001")
        mgr.release_tag("nonexistent", "python")

    def test_multiple_acquire_release_cycles(self):
        """测试多次获取释放循环."""
        mgr = OptimisticLockManager()

        for _ in range(5):
            result = mgr.try_acquire_item("pid", "features", "feat_001")
            assert result.acquired is True
            mgr.release_item("pid", "features", "feat_001")

        # 清理
        mgr.cleanup_item_lock("pid", "features", "feat_001")
