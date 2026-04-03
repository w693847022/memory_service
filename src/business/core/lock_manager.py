"""乐观锁管理器 - 支持多粒度并发控制.

提供四层锁粒度：
- 项目级锁 (project): 项目元数据操作
- 分组级锁 (group): 增删条目、分组管理
- 条目级锁 (item): 条目内容修改
- 标签级锁 (tag): 标签注册和管理

特性：
1. 非阻塞获取锁 (try_acquire)
2. 上下文管理器自动释放
3. 线程安全的双重检查锁定
4. 自动锁清理机制
"""

from enum import Enum
from dataclasses import dataclass
import threading
import contextlib
from typing import Optional, Dict, Any, Generator


class LockGranularity(Enum):
    """锁粒度枚举."""
    PROJECT = "project"
    GROUP = "group"
    ITEM = "item"
    TAG = "tag"


@dataclass
class LockResult:
    """锁获取结果.

    Attributes:
        success: 是否成功获取锁
        acquired: 是否获取到锁（同 success，语义更清晰）
        lock: 锁对象（仅当 success=True 时有效）
        current_version: 当前数据版本号
        current_data: 当前数据快照（冲突时返回）
        error: 错误码
        error_message: 错误信息
        retryable: 是否可重试
    """
    success: bool
    acquired: bool = False
    lock: Optional[threading.Lock] = None
    current_version: Optional[int] = None
    current_data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    error_message: Optional[str] = None
    retryable: bool = True


class OptimisticLockManager:
    """乐观锁管理器 - 支持多粒度锁和非阻塞获取.

    四层架构：
    1. 项目级锁: 项目元数据操作
       - register_project, project_rename, remove_project

    2. 分组级锁: 增删条目、分组管理
       - add_item, delete_item, create_custom_group, delete_custom_group

    3. 条目级锁: 条目内容修改
       - update_item, manage_item_tags

    4. 标签级锁: 标签注册和管理
       - tag_register, tag_update, tag_delete, tag_merge

    使用示例：
        >>> lock_mgr = OptimisticLockManager()
        >>>
        >>> # 上下文管理器方式（推荐）
        >>> with lock_mgr.acquire_item(pid, "features", "feat_001") as result:
        ...     if result.acquired:
        ...         # 执行更新
        ...         data["version"] += 1
        ...         save(data)
        ...     else:
        ...         # 处理冲突
        ...         return {"error": "concurrent_update"}
    """

    def __init__(self) -> None:
        """初始化乐观锁管理器."""
        # 四层锁字典
        self._project_locks: Dict[str, threading.Lock] = {}
        self._group_locks: Dict[str, threading.Lock] = {}
        self._item_locks: Dict[str, threading.Lock] = {}
        self._tag_locks: Dict[str, threading.Lock] = {}

        # 保护各层锁字典的全局锁
        self._locks_lock = threading.Lock()

    # ==================== 键生成方法 ====================

    def _make_project_key(self, project_id: str) -> str:
        """生成项目级锁的键.

        Args:
            project_id: 项目ID

        Returns:
            锁键，格式: p:{project_id}
        """
        return f"p:{project_id}"

    def _make_group_key(self, project_id: str, group_name: str) -> str:
        """生成分组级锁的键.

        Args:
            project_id: 项目ID
            group_name: 分组名称

        Returns:
            锁键，格式: g:{project_id}:{group_name}
        """
        return f"g:{project_id}:{group_name}"

    def _make_item_key(self, project_id: str, group_name: str, item_id: str) -> str:
        """生成条目级锁的键.

        Args:
            project_id: 项目ID
            group_name: 分组名称
            item_id: 条目ID

        Returns:
            锁键，格式: i:{project_id}:{group_name}:{item_id}
        """
        return f"i:{project_id}:{group_name}:{item_id}"

    def _make_tag_key(self, project_id: str, tag_name: str) -> str:
        """生成标签级锁的键.

        Args:
            project_id: 项目ID
            tag_name: 标签名称

        Returns:
            锁键，格式: t:{project_id}:{tag_name}
        """
        return f"t:{project_id}:{tag_name}"

    # ==================== 锁获取（内部方法） ====================

    def _get_lock_dict(self, granularity: LockGranularity) -> Dict[str, threading.Lock]:
        """获取指定粒度的锁字典.

        Args:
            granularity: 锁粒度

        Returns:
            对应粒度的锁字典
        """
        lock_maps = {
            LockGranularity.PROJECT: self._project_locks,
            LockGranularity.GROUP: self._group_locks,
            LockGranularity.ITEM: self._item_locks,
            LockGranularity.TAG: self._tag_locks,
        }
        return lock_maps[granularity]

    def _get_or_create_lock(self, key: str, granularity: LockGranularity) -> threading.Lock:
        """获取或创建锁（双重检查锁定）.

        Args:
            key: 锁的键
            granularity: 锁粒度

        Returns:
            锁对象
        """
        lock_dict = self._get_lock_dict(granularity)

        # 第一次检查：无锁读取（快速路径）
        lock = lock_dict.get(key)
        if lock is not None:
            return lock

        # 第二次检查：获取锁后再次检查
        with self._locks_lock:
            lock = lock_dict.get(key)
            if lock is None:
                lock = threading.Lock()
                lock_dict[key] = lock
        return lock

    # ==================== 非阻塞获取方法 ====================

    def try_acquire_project(
        self,
        project_id: str,
        current_version: Optional[int] = None,
        current_data: Optional[Dict[str, Any]] = None
    ) -> LockResult:
        """尝试获取项目级锁（非阻塞）.

        Args:
            project_id: 项目ID
            current_version: 当前版本号（可选，用于冲突返回）
            current_data: 当前数据快照（可选，用于冲突返回）

        Returns:
            LockResult 对象
        """
        key = self._make_project_key(project_id)
        lock = self._get_or_create_lock(key, LockGranularity.PROJECT)

        acquired = lock.acquire(blocking=False)

        if acquired:
            return LockResult(success=True, acquired=True, lock=lock)
        else:
            return LockResult(
                success=False,
                acquired=False,
                error="lock_held",
                error_message="项目正在被其他操作修改",
                current_version=current_version,
                current_data=current_data,
                retryable=True
            )

    def try_acquire_group(
        self,
        project_id: str,
        group_name: str,
        current_version: Optional[int] = None,
        current_data: Optional[Dict[str, Any]] = None
    ) -> LockResult:
        """尝试获取分组级锁（非阻塞）.

        Args:
            project_id: 项目ID
            group_name: 分组名称
            current_version: 当前版本号（可选）
            current_data: 当前数据快照（可选）

        Returns:
            LockResult 对象
        """
        key = self._make_group_key(project_id, group_name)
        lock = self._get_or_create_lock(key, LockGranularity.GROUP)

        acquired = lock.acquire(blocking=False)

        if acquired:
            return LockResult(success=True, acquired=True, lock=lock)
        else:
            return LockResult(
                success=False,
                acquired=False,
                error="lock_held",
                error_message=f"分组 '{group_name}' 正在被其他操作修改",
                current_version=current_version,
                current_data=current_data,
                retryable=True
            )

    def try_acquire_item(
        self,
        project_id: str,
        group_name: str,
        item_id: str,
        current_version: Optional[int] = None,
        current_data: Optional[Dict[str, Any]] = None
    ) -> LockResult:
        """尝试获取条目级锁（非阻塞）.

        Args:
            project_id: 项目ID
            group_name: 分组名称
            item_id: 条目ID
            current_version: 当前版本号（可选）
            current_data: 当前数据快照（可选）

        Returns:
            LockResult 对象
        """
        key = self._make_item_key(project_id, group_name, item_id)
        lock = self._get_or_create_lock(key, LockGranularity.ITEM)

        acquired = lock.acquire(blocking=False)

        if acquired:
            return LockResult(success=True, acquired=True, lock=lock)
        else:
            return LockResult(
                success=False,
                acquired=False,
                error="lock_held",
                error_message=f"条目 '{item_id}' 正在被其他操作修改",
                current_version=current_version,
                current_data=current_data,
                retryable=True
            )

    def try_acquire_tag(
        self,
        project_id: str,
        tag_name: str,
        current_version: Optional[int] = None,
        current_data: Optional[Dict[str, Any]] = None
    ) -> LockResult:
        """尝试获取标签级锁（非阻塞）.

        Args:
            project_id: 项目ID
            tag_name: 标签名称
            current_version: 当前版本号（可选）
            current_data: 当前数据快照（可选）

        Returns:
            LockResult 对象
        """
        key = self._make_tag_key(project_id, tag_name)
        lock = self._get_or_create_lock(key, LockGranularity.TAG)

        acquired = lock.acquire(blocking=False)

        if acquired:
            return LockResult(success=True, acquired=True, lock=lock)
        else:
            return LockResult(
                success=False,
                acquired=False,
                error="lock_held",
                error_message=f"标签 '{tag_name}' 正在被其他操作修改",
                current_version=current_version,
                current_data=current_data,
                retryable=True
            )

    # ==================== 上下文管理器 ====================

    @contextlib.contextmanager
    def acquire_project(
        self,
        project_id: str,
        current_version: Optional[int] = None,
        current_data: Optional[Dict[str, Any]] = None
    ) -> Generator[LockResult, None, None]:
        """获取项目级锁的上下文管理器（自动释放）.

        Args:
            project_id: 项目ID
            current_version: 当前版本号（可选）
            current_data: 当前数据快照（可选）

        Yields:
            LockResult 对象
        """
        key = self._make_project_key(project_id)
        lock = self._get_or_create_lock(key, LockGranularity.PROJECT)

        acquired = lock.acquire(blocking=False)

        result = LockResult(
            success=acquired,
            acquired=acquired,
            lock=lock if acquired else None,
            current_version=current_version,
            current_data=current_data,
            error=None if acquired else "lock_held",
            error_message=None if acquired else "项目正在被其他操作修改",
            retryable=True
        )

        try:
            yield result
        finally:
            if acquired:
                lock.release()

    @contextlib.contextmanager
    def acquire_group(
        self,
        project_id: str,
        group_name: str,
        current_version: Optional[int] = None,
        current_data: Optional[Dict[str, Any]] = None
    ) -> Generator[LockResult, None, None]:
        """获取分组级锁的上下文管理器（自动释放）.

        Args:
            project_id: 项目ID
            group_name: 分组名称
            current_version: 当前版本号（可选）
            current_data: 当前数据快照（可选）

        Yields:
            LockResult 对象
        """
        key = self._make_group_key(project_id, group_name)
        lock = self._get_or_create_lock(key, LockGranularity.GROUP)

        acquired = lock.acquire(blocking=False)

        result = LockResult(
            success=acquired,
            acquired=acquired,
            lock=lock if acquired else None,
            current_version=current_version,
            current_data=current_data,
            error=None if acquired else "lock_held",
            error_message=None if acquired else f"分组 '{group_name}' 正在被其他操作修改",
            retryable=True
        )

        try:
            yield result
        finally:
            if acquired:
                lock.release()

    @contextlib.contextmanager
    def acquire_item(
        self,
        project_id: str,
        group_name: str,
        item_id: str,
        current_version: Optional[int] = None,
        current_data: Optional[Dict[str, Any]] = None
    ) -> Generator[LockResult, None, None]:
        """获取条目级锁的上下文管理器（自动释放）.

        Args:
            project_id: 项目ID
            group_name: 分组名称
            item_id: 条目ID
            current_version: 当前版本号（可选）
            current_data: 当前数据快照（可选）

        Yields:
            LockResult 对象
        """
        key = self._make_item_key(project_id, group_name, item_id)
        lock = self._get_or_create_lock(key, LockGranularity.ITEM)

        acquired = lock.acquire(blocking=False)

        result = LockResult(
            success=acquired,
            acquired=acquired,
            lock=lock if acquired else None,
            current_version=current_version,
            current_data=current_data,
            error=None if acquired else "lock_held",
            error_message=None if acquired else f"条目 '{item_id}' 正在被其他操作修改",
            retryable=True
        )

        try:
            yield result
        finally:
            if acquired:
                lock.release()

    @contextlib.contextmanager
    def acquire_tag(
        self,
        project_id: str,
        tag_name: str,
        current_version: Optional[int] = None,
        current_data: Optional[Dict[str, Any]] = None
    ) -> Generator[LockResult, None, None]:
        """获取标签级锁的上下文管理器（自动释放）.

        Args:
            project_id: 项目ID
            tag_name: 标签名称
            current_version: 当前版本号（可选）
            current_data: 当前数据快照（可选）

        Yields:
            LockResult 对象
        """
        key = self._make_tag_key(project_id, tag_name)
        lock = self._get_or_create_lock(key, LockGranularity.TAG)

        acquired = lock.acquire(blocking=False)

        result = LockResult(
            success=acquired,
            acquired=acquired,
            lock=lock if acquired else None,
            current_version=current_version,
            current_data=current_data,
            error=None if acquired else "lock_held",
            error_message=None if acquired else f"标签 '{tag_name}' 正在被其他操作修改",
            retryable=True
        )

        try:
            yield result
        finally:
            if acquired:
                lock.release()

    # ==================== 锁释放方法 ====================

    def release_project(self, project_id: str) -> None:
        """释放项目级锁.

        Args:
            project_id: 项目ID

        Note:
            通常不需要手动调用，上下文管理器会自动释放。
            仅在手动管理锁时使用。
        """
        key = self._make_project_key(project_id)
        lock_dict = self._get_lock_dict(LockGranularity.PROJECT)
        lock = lock_dict.get(key)
        if lock:
            lock.release()

    def release_group(self, project_id: str, group_name: str) -> None:
        """释放分组级锁.

        Args:
            project_id: 项目ID
            group_name: 分组名称
        """
        key = self._make_group_key(project_id, group_name)
        lock_dict = self._get_lock_dict(LockGranularity.GROUP)
        lock = lock_dict.get(key)
        if lock:
            lock.release()

    def release_item(self, project_id: str, group_name: str, item_id: str) -> None:
        """释放条目级锁.

        Args:
            project_id: 项目ID
            group_name: 分组名称
            item_id: 条目ID
        """
        key = self._make_item_key(project_id, group_name, item_id)
        lock_dict = self._get_lock_dict(LockGranularity.ITEM)
        lock = lock_dict.get(key)
        if lock:
            lock.release()

    def release_tag(self, project_id: str, tag_name: str) -> None:
        """释放标签级锁.

        Args:
            project_id: 项目ID
            tag_name: 标签名称
        """
        key = self._make_tag_key(project_id, tag_name)
        lock_dict = self._get_lock_dict(LockGranularity.TAG)
        lock = lock_dict.get(key)
        if lock:
            lock.release()

    # ==================== 锁清理方法 ====================

    def cleanup_item_lock(self, project_id: str, group_name: str, item_id: str) -> None:
        """清理条目锁（在删除条目时调用）.

        Args:
            project_id: 项目ID
            group_name: 分组名称
            item_id: 条目ID
        """
        key = self._make_item_key(project_id, group_name, item_id)
        with self._locks_lock:
            self._item_locks.pop(key, None)

    def cleanup_group_locks(self, project_id: str, group_name: str) -> None:
        """清理分组的所有锁（在删除分组时调用）.

        Args:
            project_id: 项目ID
            group_name: 分组名称
        """
        with self._locks_lock:
            group_prefix = f"g:{project_id}:{group_name}"
            self._group_locks = {k: v for k, v in self._group_locks.items() if not k.startswith(group_prefix)}

            item_prefix = f"i:{project_id}:{group_name}:"
            self._item_locks = {k: v for k, v in self._item_locks.items() if not k.startswith(item_prefix)}

    def cleanup_tag_lock(self, project_id: str, tag_name: str) -> None:
        """清理标签锁（在删除标签时调用）.

        Args:
            project_id: 项目ID
            tag_name: 标签名称
        """
        key = self._make_tag_key(project_id, tag_name)
        with self._locks_lock:
            self._tag_locks.pop(key, None)

    def cleanup_project_locks(self, project_id: str) -> None:
        """清理项目相关的所有锁（在删除项目时调用）.

        Args:
            project_id: 项目ID
        """
        with self._locks_lock:
            # 清理项目级锁
            self._project_locks.pop(self._make_project_key(project_id), None)

            # 清理该项目的所有分组、条目、标签锁
            project_prefix = f"{project_id}:"

            self._group_locks = {
                k: v for k, v in self._group_locks.items()
                if not k.startswith(f"g:{project_prefix}")
            }
            self._item_locks = {
                k: v for k, v in self._item_locks.items()
                if not k.startswith(f"i:{project_prefix}")
            }
            self._tag_locks = {
                k: v for k, v in self._tag_locks.items()
                if not k.startswith(f"t:{project_prefix}")
            }
