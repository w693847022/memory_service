#!/usr/bin/env python3
"""跨项目并发测试(B1级别).

测试不同项目之间的并发操作：
1. 并发注册多个项目
2. 并发删除不同项目
3. 项目A的rename和项目B的add_item并行
"""

import sys
import os
import asyncio
import tempfile
import shutil
from pathlib import Path
import pytest
import pytest_asyncio

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from business.storage import Storage
from business.project_service import ProjectService
from business.tag_service import TagService
from business.groups_service import GroupsService
from business.core import barrier_decorator
from business.core.barrier_decorator import BarrierManager


@pytest.mark.asyncio
class TestCrossProjectConcurrent:
    """跨项目并发测试类."""

    @pytest_asyncio.fixture(autouse=True)
    async def setup_teardown(self):
        """每个测试方法前后的设置和清理."""
        self.temp_dir = None
        self.storage = None
        self.project_service = None
        self.tag_service = None
        self.project_ids = []
        yield
        # 清理所有创建的项目
        if self.project_service and self.project_ids:
            for pid in self.project_ids:
                try:
                    await self.project_service.remove_project(pid, mode="delete")
                except Exception as e:
                    print(f"清理项目 {pid} 失败: {e}")
        # 清理临时目录
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    async def async_setup_method(self):
        """每个测试方法前执行：设置测试环境."""
        self.temp_dir = tempfile.mkdtemp()
        # 重置全局 BarrierManager，确保使用新的事件循环
        barrier_decorator._global_barrier_manager = None
        # 创建独立的 BarrierManager 避免跨事件循环锁问题
        barrier_manager = BarrierManager()
        self.storage = Storage(storage_dir=self.temp_dir, barrier_manager=barrier_manager)
        self.groups_service = GroupsService(self.storage)
        self.project_service = ProjectService(self.storage, groups_service=self.groups_service)
        self.tag_service = TagService(self.storage)

    async def test_concurrent_register_multiple_projects(self):
        """测试：并发注册多个项目（应该都成功）.

        验证点：
        1. 多个register_project操作可以并行执行
        2. 每个项目都获得唯一的project_id
        3. 所有项目都成功注册
        """
        await self.async_setup_method()

        # 并发注册5个项目
        project_names = [f"concurrent_project_{i}" for i in range(5)]
        tasks = []

        for name in project_names:
            task = self.project_service.register_project(
                name=name,
                path=f"/tmp/{name}",
                summary=f"测试项目 {name}"
            )
            tasks.append(task)

        # 并发执行所有注册操作
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 验证所有操作都成功
        project_ids = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                raise AssertionError(f"注册项目 {i} 失败，抛出异常: {result}")

            assert result["success"], f"注册项目 {i} 失败: {result.get('error')}"
            project_id = result["data"]["project_id"]
            project_ids.append(project_id)
            print(f"✓ 项目 {i} 注册成功: {project_names[i]} -> {project_id}")

        # 保存project_ids用于清理
        self.project_ids.extend(project_ids)

        # 验证所有project_id都是唯一的
        assert len(set(project_ids)) == len(project_ids), "project_id应该唯一"
        print(f"✓ 所有 {len(project_ids)} 个项目注册成功，project_id唯一")

        # 验证可以查询到所有项目
        for pid in project_ids:
            result = await self.project_service.get_project(project_id=pid, include_items=True)
            assert result["success"], f"无法查询到项目 {pid}"
            print(f"✓ 项目 {pid} 可以正常查询")

        print("✓ 并发注册多个项目：全部成功")

    async def test_concurrent_remove_different_projects(self):
        """测试：并发删除不同项目（应该都成功）.

        验证点：
        1. 先注册多个项目
        2. 并发删除这些项目
        3. 所有删除操作都成功
        4. 删除后无法再查询到项目
        """
        await self.async_setup_method()

        # 先注册5个项目
        project_ids = []
        for i in range(5):
            result = await self.project_service.register_project(
                name=f"remove_test_{i}",
                path=f"/tmp/remove_test_{i}",
                summary=f"待删除项目 {i}"
            )
            assert result["success"]
            project_ids.append(result["data"]["project_id"])
            print(f"✓ 注册项目 {i}: {result['data']['project_id']}")

        print(f"已注册 {len(project_ids)} 个项目，开始并发删除...")

        # 并发删除所有项目
        tasks = []
        for pid in project_ids:
            task = self.project_service.remove_project(
                project_id=pid,
                mode="delete"
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 验证所有删除操作都成功
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                raise AssertionError(f"删除项目 {i} 失败，抛出异常: {result}")

            assert result["success"], f"删除项目 {i} 失败: {result.get('error')}"
            print(f"✓ 项目 {i} 删除成功: {project_ids[i]}")

        # 清空 project_ids 列表，防止 cleanup fixture 重复删除
        self.project_ids.clear()

        # 验证所有项目都无法再查询到
        # 等待一下确保文件系统操作完成
        await asyncio.sleep(0.1)

        for i, pid in enumerate(project_ids):
            # 刷新缓存
            await self.project_service.storage.refresh_projects_cache()
            # 检查项目目录是否存在
            project_dir = self.project_service.storage._get_project_dir(pid)
            assert not project_dir.exists(), f"项目 {pid} 的目录应该已被删除"
            print(f"✓ 项目 {pid} 确认已删除（目录不存在）")

        print("✓ 并发删除不同项目：全部成功")

    async def test_cross_project_operations_mixed(self):
        """测试：项目A的rename和项目B的add_item并行（跨项目混合操作）.

        验证点：
        1. 注册项目A和项目B
        2. 同时执行：项目A的rename + 项目B的add_item
        3. 两个操作都应该成功（跨项目无冲突）
        4. 验证项目A确实被重命名
        5. 验证项目B确实添加了条目
        """
        await self.async_setup_method()

        # 注册项目A
        result_a = await self.project_service.register_project(
            name="project_a",
            path="/tmp/project_a",
            summary="项目A - 用于测试rename"
        )
        assert result_a["success"]
        project_id_a = result_a["data"]["project_id"]
        self.project_ids.append(project_id_a)
        print(f"✓ 注册项目A: {project_id_a}")

        # 注册项目B
        result_b = await self.project_service.register_project(
            name="project_b",
            path="/tmp/project_b",
            summary="项目B - 用于测试add_item"
        )
        assert result_b["success"]
        project_id_b = result_b["data"]["project_id"]
        self.project_ids.append(project_id_b)
        print(f"✓ 注册项目B: {project_id_b}")

        # 并发执行：项目A的rename + 项目B的add_item
        rename_task = self.project_service.project_rename(
            project_id=project_id_a,
            new_name="renamed_project_a"
        )

        add_item_task = self.project_service.add_item(
            project_id=project_id_b,
            group="features",
            content="测试条目内容",
            summary="跨项目并发测试条目",
            status="pending",
            tags=["cross_project_test"]
        )

        print("开始并发执行：项目A rename + 项目B add_item...")
        results = await asyncio.gather(rename_task, add_item_task, return_exceptions=True)

        rename_result, add_item_result = results

        # 验证rename结果
        if isinstance(rename_result, Exception):
            raise AssertionError(f"项目A rename失败，抛出异常: {rename_result}")
        assert rename_result["success"], f"项目A rename失败: {rename_result.get('error')}"
        print(f"✓ 项目A rename成功: project_a -> renamed_project_a")

        # 验证add_item结果
        if isinstance(add_item_result, Exception):
            raise AssertionError(f"项目B add_item失败，抛出异常: {add_item_result}")
        assert add_item_result["success"], f"项目B add_item失败: {add_item_result.get('error')}"
        item_id_b = add_item_result["data"]["item_id"]
        print(f"✓ 项目B add_item成功: {item_id_b}")

        # 验证项目A确实被重命名
        result_a_check = await self.project_service.get_project(project_id=project_id_a)
        assert result_a_check["success"], "无法查询项目A"
        assert result_a_check["data"]["info"]["name"] == "renamed_project_a", "项目A名称未更新"
        print(f"✓ 验证项目A名称: {result_a_check['data']['info']['name']}")

        # 验证项目B确实添加了条目
        result_b_check = await self.project_service.get_project(project_id=project_id_b, include_items=True)
        assert result_b_check["success"], "无法查询项目B"
        features = result_b_check["data"].get("features", [])
        assert len(features) > 0, "项目B的features分组应该有条目"
        assert any(item["id"] == item_id_b for item in features), "未找到添加的条目"
        print(f"✓ 验证项目B条目: 共 {len(features)} 个条目，包含 {item_id_b}")

        print("✓ 跨项目混合操作：项目A rename + 项目B add_item 并行成功")

    async def test_cross_project_concurrent_add_items(self):
        """测试：跨项目并发添加条目（扩展测试）.

        验证点：
        1. 注册3个项目
        2. 并发在每个项目中添加条目
        3. 所有操作都成功
        4. 每个项目都能查询到添加的条目
        """
        await self.async_setup_method()

        # 注册3个项目
        project_ids = []
        for i in range(3):
            result = await self.project_service.register_project(
                name=f"item_test_project_{i}",
                path=f"/tmp/item_test_{i}",
                summary=f"条目测试项目 {i}"
            )
            assert result["success"]
            project_ids.append(result["data"]["project_id"])
            self.project_ids.append(result["data"]["project_id"])
            print(f"✓ 注册项目 {i}: {result['data']['project_id']}")

        # 并发在每个项目中添加条目
        tasks = []
        for i, pid in enumerate(project_ids):
            task = self.project_service.add_item(
                project_id=pid,
                group="features",
                content=f"项目 {i} 的测试条目",
                summary=f"项目{i}条目",
                status="pending",
                tags=[f"project_{i}"]
            )
            tasks.append(task)

        print("开始并发添加条目到不同项目...")
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 验证所有操作都成功
        item_ids = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                raise AssertionError(f"项目 {i} add_item失败，抛出异常: {result}")

            assert result["success"], f"项目 {i} add_item失败: {result.get('error')}"
            item_ids.append(result["data"]["item_id"])
            print(f"✓ 项目 {i} add_item成功: {result['data']['item_id']}")

        # 验证每个项目都能查询到添加的条目
        for i, (pid, item_id) in enumerate(zip(project_ids, item_ids)):
            result = await self.project_service.get_project(project_id=pid, include_items=True)
            assert result["success"], f"无法查询项目 {pid}"
            features = result["data"].get("features", [])
            assert len(features) > 0, f"项目 {pid} 的features分组应该有条目"
            assert any(item["id"] == item_id for item in features), f"项目 {pid} 未找到条目 {item_id}"
            print(f"✓ 验证项目 {i} 条目: {item_id} 存在")

        print("✓ 跨项目并发添加条目：全部成功")

    async def test_cross_project_rename_and_delete_parallel(self):
        """测试：项目A rename和项目B delete并行（跨项目不同操作）.

        验证点：
        1. 注册项目A和项目B
        2. 同时执行：项目A rename + 项目B delete
        3. 两个操作都应该成功（跨项目无冲突）
        4. 验证项目A被重命名
        5. 验证项目B被删除
        """
        await self.async_setup_method()

        # 注册项目A
        result_a = await self.project_service.register_project(
            name="rename_test_a",
            path="/tmp/rename_test_a",
            summary="项目A - rename测试"
        )
        assert result_a["success"]
        project_id_a = result_a["data"]["project_id"]
        print(f"✓ 注册项目A: {project_id_a}")

        # 注册项目B
        result_b = await self.project_service.register_project(
            name="delete_test_b",
            path="/tmp/delete_test_b",
            summary="项目B - delete测试"
        )
        assert result_b["success"]
        project_id_b = result_b["data"]["project_id"]
        print(f"✓ 注册项目B: {project_id_b}")

        # 并发执行：项目A rename + 项目B delete
        rename_task = self.project_service.project_rename(
            project_id=project_id_a,
            new_name="renamed_test_a"
        )

        delete_task = self.project_service.remove_project(
            project_id=project_id_b,
            mode="delete"
        )

        print("开始并发执行：项目A rename + 项目B delete...")
        results = await asyncio.gather(rename_task, delete_task, return_exceptions=True)

        rename_result, delete_result = results

        # 验证rename结果
        if isinstance(rename_result, Exception):
            raise AssertionError(f"项目A rename失败，抛出异常: {rename_result}")
        assert rename_result["success"], f"项目A rename失败: {rename_result.get('error')}"
        print(f"✓ 项目A rename成功")

        # 验证delete结果
        if isinstance(delete_result, Exception):
            raise AssertionError(f"项目B delete失败，抛出异常: {delete_result}")
        assert delete_result["success"], f"项目B delete失败: {delete_result.get('error')}"
        print(f"✓ 项目B delete成功")

        # 验证项目A被重命名
        result_a_check = await self.project_service.get_project(project_id=project_id_a)
        assert result_a_check["success"], "无法查询项目A"
        assert result_a_check["data"]["info"]["name"] == "renamed_test_a", "项目A名称未更新"
        print(f"✓ 验证项目A名称: {result_a_check['data']['info']['name']}")

        # 验证项目B被删除
        # 等待一下确保文件系统操作完成
        await asyncio.sleep(0.1)
        await self.project_service.storage.refresh_projects_cache()

        project_b_dir = self.project_service.storage._get_project_dir(project_id_b)
        assert not project_b_dir.exists(), "项目B应该已被删除"
        print(f"✓ 验证项目B已删除")

        # 保存项目A用于清理
        self.project_ids.append(project_id_a)

        print("✓ 跨项目不同操作：项目A rename + 项目B delete 并行成功")
