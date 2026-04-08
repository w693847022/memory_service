"""阻挡位管理器 - 五层阻挡位 + 两阶段排空并发控制.

替代原有的四层乐观锁方案，提供更精细的并发控制：

五层阻挡位：
- B1 服务级: register/remove_project (全局)
- B2 项目范围级: project_rename, tag_delete, tag_merge (项目级)
- B3 标签/组定义级: tag_register/update, group create/update/delete/settings (项目级)
- B4 条目列表级: add/delete_item (项目+分组级)
- B5 条目ID级: update_item, add/remove_item_tag (项目+条目ID级)

执行流程:
上行检查 → 获取自身阻挡位 → 下行排空 → 版本检测 → IO锁 → 执行 → 释放IO锁 → 更新版本 → 释放阻挡位
"""

import asyncio
from contextlib import asynccontextmanager
from enum import IntEnum 
from typing import Dict

class BarrierLevel(IntEnum):
    """阻挡等级枚举"""
    B1 = 1
    B2 = 2
    B3 = 3
    B4 = 4
    B5 = 5

class DrainCounter:
    """活跃操作计数器 - 跟踪 B4/B5 级别正在执行的操作数.

    排空机制: 高级操作获取自身阻挡位后，等待活跃的低级操作归零再执行。
    """

    def __init__(self) -> None:
        self._cond = asyncio.Condition()
        self.B4_active: int = 0
        self.B5_active: int = 0

    async def increment(self, level: str) -> None:
        """递增指定级别的活跃计数."""
        async with self._cond:
            if level == "B4":
                self.B4_active += 1
            elif level == "B5":
                self.B5_active += 1

    async def decrement(self, level: str) -> None:
        """递减指定级别的活跃计数并通知等待者."""
        async with self._cond:
            if level == "B4":
                self.B4_active -= 1
            elif level == "B5":
                self.B5_active -= 1
            self._cond.notify_all()

    async def wait_zero(self, *levels: str) -> None:
        """等待指定级别的活跃计数全部归零."""
        async with self._cond:
            while not all(
                (l == "B4" and self.B4_active == 0) or
                (l == "B5" and self.B5_active == 0)
                for l in levels
            ):
                await self._cond.wait()


class ProjectBarriers:
    """每项目的阻挡位集合."""

    def __init__(self) -> None:
        self.B2: asyncio.Lock = asyncio.Lock()  # 项目范围级
        self.B3: asyncio.Lock = asyncio.Lock()  # 标签/组定义级
        self._B4_locks: Dict[str, asyncio.Lock] = {}  # 分组名 -> Lock
        self._B5_locks: Dict[str, asyncio.Lock] = {}  # 条目ID -> Lock
        self.drain: DrainCounter = DrainCounter()

    def get_B4(self, group_name: str) -> asyncio.Lock:
        """获取或创建 B4 锁（按分组名）."""
        if group_name not in self._B4_locks:
            self._B4_locks[group_name] = asyncio.Lock()
        return self._B4_locks[group_name]

    def get_B5(self, item_id: str) -> asyncio.Lock:
        """获取或创建 B5 锁（按条目ID）."""
        if item_id not in self._B5_locks:
            self._B5_locks[item_id] = asyncio.Lock()
        return self._B5_locks[item_id]

    def cleanup_B4(self, group_name: str) -> None:
        """清理指定分组的 B4 锁."""
        self._B4_locks.pop(group_name, None)

    def cleanup_B5(self, item_id: str) -> None:
        """清理指定条目的 B5 锁."""
        self._B5_locks.pop(item_id, None)

    def cleanup_all(self) -> None:
        """清理所有锁（项目删除时调用）."""
        self._B4_locks.clear()
        self._B5_locks.clear()


class BarrierManager:
    """全局阻挡位管理器.

    每个业务操作有对应的 async context manager 方法，内部封装：
    1. 上行检查（按序获取更高级别锁后释放）
    2. 获取自身级别锁
    3. 下行排空（等待低级活跃操作归零）
    4. yield 给业务代码
    5. finally 释放自身锁
    """

    def __init__(self) -> None:
        self._B1: asyncio.Lock = asyncio.Lock()  # 全局服务级
        self._io_lock: asyncio.Lock = asyncio.Lock()  # 全局 IO 锁
        self._projects: Dict[str, ProjectBarriers] = {}

    def _get_pb(self, project_id: str) -> ProjectBarriers:
        """获取或创建项目阻挡位."""
        if project_id not in self._projects:
            self._projects[project_id] = ProjectBarriers()
        return self._projects[project_id]

    def remove_project_barriers(self, project_id: str) -> None:
        """移除项目的所有阻挡位（项目删除时调用）."""
        pb = self._projects.pop(project_id, None)
        if pb:
            pb.cleanup_all()

    # ==================== IO 操作锁 ====================

    @asynccontextmanager
    async def io_operation(self):
        """IO 操作锁 - 保护文件写入."""
        async with self._io_lock:
            yield

    # ==================== 服务级操作 (B1) ====================

    @asynccontextmanager
    async def register_project(self):
        """注册项目 - 持有 B1."""
        await self._B1.acquire()
        try:
            yield
        finally:
            self._B1.release()

    @asynccontextmanager
    async def remove_project(self, pid: str):
        """删除项目 - 持有 B1，排空 B4+B5."""
        await self._B1.acquire()
        pb = self._get_pb(pid)
        try:
            await pb.drain.wait_zero("B4", "B5")
            yield
        finally:
            self._B1.release()
            self.remove_project_barriers(pid)

    # ==================== 项目范围级操作 (B2) ====================

    @asynccontextmanager
    async def project_rename(self, pid: str):
        """项目重命名 - 检查 B1，持有 B2，排空 B4+B5."""
        await self._B1.acquire()
        pb = self._get_pb(pid)
        await pb.B2.acquire()
        self._B1.release()
        try:
            await pb.drain.wait_zero("B4", "B5")
            yield
        finally:
            pb.B2.release()

    @asynccontextmanager
    async def tag_delete(self, pid: str):
        """标签删除 - 检查 B1+B3，持有 B2，排空 B4+B5."""
        await self._B1.acquire()
        pb = self._get_pb(pid)
        await pb.B2.acquire()
        self._B1.release()
        await pb.B3.acquire()
        pb.B3.release()
        try:
            await pb.drain.wait_zero("B4", "B5")
            yield
        finally:
            pb.B2.release()

    @asynccontextmanager
    async def tag_merge(self, pid: str):
        """标签合并 - 检查 B1+B3，持有 B2，排空 B4+B5."""
        await self._B1.acquire()
        pb = self._get_pb(pid)
        await pb.B2.acquire()
        self._B1.release()
        await pb.B3.acquire()
        pb.B3.release()
        try:
            await pb.drain.wait_zero("B4", "B5")
            yield
        finally:
            pb.B2.release()

    # ==================== 标签/组定义级操作 (B3) ====================

    @asynccontextmanager
    async def tag_register(self, pid: str):
        """标签注册 - 检查 B1+B2，持有 B3."""
        await self._B1.acquire()
        pb = self._get_pb(pid)
        await pb.B2.acquire()
        self._B1.release()
        pb.B2.release()
        await pb.B3.acquire()
        try:
            yield
        finally:
            pb.B3.release()

    @asynccontextmanager
    async def tag_update(self, pid: str):
        """标签更新 - 检查 B1+B2，持有 B3."""
        await self._B1.acquire()
        pb = self._get_pb(pid)
        await pb.B2.acquire()
        self._B1.release()
        pb.B2.release()
        await pb.B3.acquire()
        try:
            yield
        finally:
            pb.B3.release()

    @asynccontextmanager
    async def group_create(self, pid: str):
        """创建自定义组 - 检查 B1+B2，持有 B3."""
        await self._B1.acquire()
        pb = self._get_pb(pid)
        await pb.B2.acquire()
        self._B1.release()
        pb.B2.release()
        await pb.B3.acquire()
        try:
            yield
        finally:
            pb.B3.release()

    @asynccontextmanager
    async def group_update(self, pid: str):
        """更新自定义组 - 检查 B1+B2，持有 B3."""
        await self._B1.acquire()
        pb = self._get_pb(pid)
        await pb.B2.acquire()
        self._B1.release()
        pb.B2.release()
        await pb.B3.acquire()
        try:
            yield
        finally:
            pb.B3.release()

    @asynccontextmanager
    async def group_delete(self, pid: str, group_name: str):
        """删除自定义组 - 检查 B1+B2，持有 B3，排空 B4+B5."""
        await self._B1.acquire()
        pb = self._get_pb(pid)
        await pb.B2.acquire()
        self._B1.release()
        pb.B2.release()
        await pb.B3.acquire()
        try:
            await pb.drain.wait_zero("B4", "B5")
            yield
        finally:
            pb.B3.release()
            pb.cleanup_B4(group_name)

    @asynccontextmanager
    async def group_settings(self, pid: str):
        """更新组设置 - 检查 B1+B2，持有 B3."""
        await self._B1.acquire()
        pb = self._get_pb(pid)
        await pb.B2.acquire()
        self._B1.release()
        pb.B2.release()
        await pb.B3.acquire()
        try:
            yield
        finally:
            pb.B3.release()

    # ==================== 条目列表级操作 (B4) ====================

    @asynccontextmanager
    async def add_item(self, pid: str, group_name: str):
        """添加条目 - 检查 B1+B2+B3，持有 B4，计数+1."""
        await self._B1.acquire()
        pb = self._get_pb(pid)
        await pb.B2.acquire()
        self._B1.release()
        pb.B2.release()
        await pb.B3.acquire()
        pb.B3.release()
        b4 = pb.get_B4(group_name)
        await b4.acquire()
        try:
            await pb.drain.increment("B4")
            try:
                yield
            finally:
                await pb.drain.decrement("B4")
        finally:
            b4.release()

    @asynccontextmanager
    async def delete_item(self, pid: str, group_name: str, item_id: str):
        """删除条目 - 检查 B1+B2+B3+B5，持有 B4，计数+1."""
        await self._B1.acquire()
        pb = self._get_pb(pid)
        await pb.B2.acquire()
        self._B1.release()
        pb.B2.release()
        await pb.B3.acquire()
        pb.B3.release()
        b4 = pb.get_B4(group_name)
        await b4.acquire()
        # 等待目标条目的活跃操作完成
        b5 = pb.get_B5(item_id)
        await b5.acquire()
        b5.release()
        try:
            await pb.drain.increment("B4")
            try:
                yield
            finally:
                await pb.drain.decrement("B4")
        finally:
            b4.release()
            pb.cleanup_B5(item_id)

    # ==================== 条目ID级操作 (B5) ====================

    @asynccontextmanager
    async def update_item(self, pid: str, group_name: str, item_id: str):
        """更新条目 - 检查 B1+B2+B3+B4，持有 B5，计数+1."""
        await self._B1.acquire()
        pb = self._get_pb(pid)
        await pb.B2.acquire()
        self._B1.release()
        pb.B2.release()
        await pb.B3.acquire()
        pb.B3.release()
        b4 = pb.get_B4(group_name)
        await b4.acquire()
        b4.release()
        b5 = pb.get_B5(item_id)
        await b5.acquire()
        try:
            await pb.drain.increment("B5")
            try:
                yield
            finally:
                await pb.drain.decrement("B5")
        finally:
            b5.release()

    @asynccontextmanager
    async def add_item_tag(self, pid: str, group_name: str, item_id: str):
        """添加条目标签 - 同 update_item."""
        async with self.update_item(pid, group_name, item_id):
            yield

    @asynccontextmanager
    async def remove_item_tag(self, pid: str, group_name: str, item_id: str):
        """移除条目标签 - 同 update_item."""
        async with self.update_item(pid, group_name, item_id):
            yield
