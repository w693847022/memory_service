"""阻挡位装饰器 - 声明式并发控制.

提供 @barrier() 装饰器，支持：
1. 声明式级别：level=OperationLevel.L2
2. 声明式文件：files=["_tags.json"]
3. 自动key生成：key="{project_id}:{group}" 从函数参数动态生成
4. 文件级别验证：运行时验证操作级别 >= 文件级别要求
5. 文件访问监控：验证只访问声明过的文件
"""

import asyncio
import functools
import inspect
from contextlib import asynccontextmanager
from typing import List, Optional, Dict, Any, Set

from business.core.barrier_constants import (
    OperationLevel,
    GLOBAL_BARRIER_KEY,
    FILE_LEVELS,
    DRAIN_STRATEGY,
)


class BarrierContext:
    """阻挡位上下文 - 文件访问监控.

    跟踪操作实际访问的文件，验证只访问声明过的文件。
    """

    def __init__(self, declared_files: List[str]):
        """初始化上下文.

        Args:
            declared_files: 声明的文件列表
        """
        self._declared_files: Set[str] = set(declared_files)
        self._accessed_files: Set[str] = set()

    def mark_access(self, file_path: str) -> None:
        """标记访问了某个文件.

        Args:
            file_path: 文件路径
        """
        self._accessed_files.add(file_path)

    def validate(self) -> None:
        """验证只访问了声明的文件.

        Raises:
            RuntimeError: 如果访问了未声明的文件
        """
        undeclared = self._accessed_files - self._declared_files
        if undeclared:
            raise RuntimeError(f"未声明的文件访问: {undeclared}")


class BarrierManager:
    """阻挡位管理器 - 通用实现.

    使用单一 _locks 字典存储所有锁，key 为动态生成的字符串。
    """

    def __init__(self):
        """初始化阻挡位管理器."""
        # 单一 locks 字典：key → asyncio.Lock
        self._locks: Dict[str, asyncio.Lock] = {
            GLOBAL_BARRIER_KEY: asyncio.Lock()
        }

        # 活跃计数器：用于排空机制
        # 格式: {"L3": {project_key: count}, "L4": {project_key: count}, "L5": {entry_key: count}}
        self._active_counters: Dict[str, Dict[str, int]] = {
            "L3": {},
            "L4": {},
            "L5": {},
        }

        # 条件变量：用于排空等待
        self._drain_cond = asyncio.Condition()

    @asynccontextmanager
    async def acquire(
        self,
        level: OperationLevel,
        key: str,
        files: List[str]
    ):
        """获取阻挡位 - 通用方法.

        Args:
            level: 操作级别
            key: 锁 key（动态生成）
            files: 声明修改的文件列表

        Yields:
            BarrierContext: 上下文对象
        """
        # 1. 上行检查：按序检查更高级别
        for higher_level in range(level.value - 1, 0, -1):
            higher_key = GLOBAL_BARRIER_KEY if higher_level == 1 else key
            await self._check_level(higher_key)

        # 2. 获取自身锁
        lock = self._locks.setdefault(key, asyncio.Lock())
        await lock.acquire()

        try:
            # 3. 下行排空
            drain_levels = DRAIN_STRATEGY.get(level, [])
            for drain_level in drain_levels:
                await self._drain_level(drain_level, key)

            # 4. 文件级别验证
            self._validate_file_level(level, files)

            # 5. 创建上下文并 yield
            ctx = BarrierContext(files)
            try:
                yield ctx
                # 6. 验证文件访问
                ctx.validate()
            finally:
                pass
        finally:
            lock.release()

    async def _check_level(self, key: str) -> None:
        """检查指定级别的锁是否可用.

        Args:
            key: 锁 key
        """
        lock = self._locks.get(key)
        if lock:
            # 尝试获取并立即释放，用于检查
            # 如果锁被持有，这里会等待
            async with lock:
                pass

    async def _drain_level(self, level: OperationLevel, key: str) -> None:
        """排空指定级别的活跃操作.

        Args:
            level: 要排空的级别
            key: 锁 key
        """
        level_name = f"L{level.value}"
        counters = self._active_counters.get(level_name, {})

        async with self._drain_cond:
            while counters.get(key, 0) > 0:
                await self._drain_cond.wait()

    def _validate_file_level(self, level: OperationLevel, files: List[str]) -> None:
        """验证操作级别是否满足文件级别要求.

        Args:
            level: 操作级别
            files: 文件列表（已格式化的实际文件路径）

        Raises:
            RuntimeError: 如果操作级别低于文件级别要求

        Note:
            L1 是最高级别（权限最大），L5 是最低级别（权限最小）
            高级别可以修改低级别文件：level.value <= file_level.value

            支持模式匹配：
            - 精确匹配："_index.json" == "_index.json"
            - 模式匹配："fixes/item_123.json" 匹配 "fixes/{item_id}.json"
        """
        for file in files:
            # 先尝试精确匹配
            required_level = FILE_LEVELS.get(file)

            # 如果精确匹配失败，尝试模式匹配
            if not required_level:
                required_level = self._match_file_pattern(file)

            if required_level and level.value > required_level.value:
                raise RuntimeError(
                    f"操作级别 L{level.value} 不能修改文件 {file} (需要 L{required_level.value} 或更高级别)"
                )

    def _match_file_pattern(self, file_path: str) -> Optional[OperationLevel]:
        """通过模式匹配查找文件级别.

        Args:
            file_path: 实际文件路径，如 "fixes/item_123.json"

        Returns:
            匹配到的操作级别，如果未匹配则返回 None

        Examples:
            _match_file_pattern("fixes/item_123.json") -> OperationLevel.L5
            _match_file_pattern("custom_group/item_456.json") -> OperationLevel.L5
            _match_file_pattern("_index.json") -> OperationLevel.L1
        """
        import re

        for pattern, required_level in FILE_LEVELS.items():
            # 将模式转换为正则表达式
            # {group} -> ([^/]+)  匹配非斜杠字符
            # {item_id} -> ([^/]+) 匹配非斜杠字符
            regex_pattern = pattern
            for var in re.findall(r'\{([^}]+)\}', pattern):
                regex_pattern = regex_pattern.replace(f"{{{var}}}", r"([^/]+)")

            # 尝试匹配
            if re.fullmatch(regex_pattern, file_path):
                return required_level

        return None

    async def increment_active(self, level: OperationLevel, key: str) -> None:
        """递增活跃计数.

        Args:
            level: 操作级别
            key: 锁 key
        """
        level_name = f"L{level.value}"
        counters = self._active_counters.get(level_name, {})
        async with self._drain_cond:
            counters[key] = counters.get(key, 0) + 1

    async def decrement_active(self, level: OperationLevel, key: str) -> None:
        """递减活跃计数并通知等待者.

        Args:
            level: 操作级别
            key: 锁 key
        """
        level_name = f"L{level.value}"
        counters = self._active_counters.get(level_name, {})
        async with self._drain_cond:
            counters[key] = counters.get(key, 1) - 1
            if counters[key] <= 0:
                counters.pop(key, None)
            self._drain_cond.notify_all()

    def cleanup_locks(self, key: str) -> None:
        """清理指定 key 的锁（项目删除时调用）.

        Args:
            key: 锁 key
        """
        self._locks.pop(key, None)
        for counters in self._active_counters.values():
            counters.pop(key, None)


# 全局阻挡位管理器实例
_global_barrier_manager: Optional[BarrierManager] = None


def get_barrier_manager() -> BarrierManager:
    """获取全局阻挡位管理器实例."""
    global _global_barrier_manager
    if _global_barrier_manager is None:
        _global_barrier_manager = BarrierManager()
    return _global_barrier_manager


def _format_template(template: str, params: dict, func_name: str, template_type: str = "模板") -> str:
    """格式化模板字符串.

    Args:
        template: 模板字符串，如 "{project_id}/{group}"
        params: 参数字典
        func_name: 函数名（用于错误信息）
        template_type: 模板类型（用于错误信息）

    Returns:
        格式化后的字符串

    Raises:
        ValueError: 如果模板中的参数在 params 中不存在
    """
    try:
        return template.format(**params)
    except KeyError as e:
        missing_vars = []
        # 查找所有可能的占位符
        import re
        pattern = r'\{([^}]+)\}'
        found_vars = re.findall(pattern, template)
        for var in found_vars:
            if var not in params:
                missing_vars.append(var)
        if missing_vars:
            raise ValueError(
                f"{template_type} '{template}' 中的参数 {missing_vars} 在函数 '{func_name}' 中不存在。"
                f"可用参数: {list(params.keys())}"
            )
        raise


def barrier(
    level: OperationLevel,
    files: List[str],
    key: Optional[str] = None
):
    """阻挡位装饰器 - 声明式并发控制.

    Args:
        level: 操作级别
        files: 声明修改的文件列表，支持动态模板
              例如: ["_tags.json"] 或 ["{group}/{item_id}.json"]
        key: 锁 key 模板，从函数参数动态生成
              例如: "{project_id}" 或 "{project_id}:{group}"

    Returns:
        装饰器函数

    Raises:
        ValueError: 如果 key 或 files 模板中的参数在函数中不存在

    Examples:
        @barrier(level=OperationLevel.L2, files=["_tags.json"], key="{project_id}")
        async def tag_delete(project_id: str, tag_name: str):
            return await storage.tag_delete(project_id, tag_name)

        @barrier(level=OperationLevel.L5,
                files=["{group}/{item_id}.json"],
                key="{project_id}:{group}:{item_id}")
        async def update_item(project_id: str, group: str, item_id: str, content: str):
            return await storage.update_item(project_id, group, item_id, content)
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # 1. 从函数签名提取参数名→值映射
            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()
            params = bound_args.arguments

            # 2. 格式化 key 模板
            if level == OperationLevel.L1:
                lock_key = GLOBAL_BARRIER_KEY
            elif key:
                lock_key = _format_template(key, params, func.__name__, "Key 模板")
            else:
                # 默认使用 project_id
                lock_key = params.get('project_id', '')
                if not lock_key:
                    raise ValueError(
                        f"函数 '{func.__name__}' 缺少 project_id 参数，且未指定 key 模板"
                    )

            # 3. 格式化 files 模板
            formatted_files = []
            for file_template in files:
                formatted_file = _format_template(file_template, params, func.__name__, "Files 模板")
                formatted_files.append(formatted_file)

            # 4. 获取阻挡位管理器
            manager = get_barrier_manager()

            # 5. 活跃计数处理（L4 和 L5 需要计数）
            if level in [OperationLevel.L4, OperationLevel.L5]:
                await manager.increment_active(level, lock_key)
                try:
                    async with manager.acquire(level, lock_key, formatted_files):
                        return await func(*args, **kwargs)
                finally:
                    await manager.decrement_active(level, lock_key)
            else:
                async with manager.acquire(level, lock_key, formatted_files):
                    return await func(*args, **kwargs)

        return wrapper
    return decorator
