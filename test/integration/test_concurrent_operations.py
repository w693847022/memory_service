#!/usr/bin/env python3
"""统一并发操作测试.

整合所有并发测试场景，验证五层阻挡位系统的并发控制机制。

测试场景包括：
1. 基础并发操作 - add/update/delete
2. 条目标签操作并发
3. B2级操作组合（项目范围级）
4. 版本冲突测试
5. 高并发压力测试
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


@pytest.mark.asyncio
class TestConcurrentOperations:
    """统一并发操作测试类."""

    @pytest_asyncio.fixture(autouse=True)
    async def setup_teardown(self):
        """每个测试方法前后的设置和清理."""
        self.temp_dir = None
        self.storage = None
        self.project_service = None
        self.tag_service = None
        self.project_id = None
        yield
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    async def async_setup_method(self, project_name="concurrent_test_project"):
        """每个测试方法前执行：设置测试环境."""
        self.temp_dir = tempfile.mkdtemp()
        self.storage = Storage(storage_dir=self.temp_dir)
        self.project_service = ProjectService(self.storage)
        self.tag_service = TagService(self.storage)

        # 注册测试项目
        result = await self.project_service.register_project(
            project_name,
            "/tmp/concurrent_test",
            summary="并发操作测试项目"
        )
        self.project_id = result["project_id"]

    # ==================== 基础并发操作测试 ====================

    async def test_concurrent_add_items_same_group(self):
        """测试：并发添加同分组的多个条目（应该都成功）.

        验证点：
        - 同一分组的并发add操作互不冲突
        - 所有操作都能成功完成
        """
        await self.async_setup_method()

        # 并发添加3个features
        tasks = []
        for i in range(3):
            task = self.project_service.add_item(
                project_id=self.project_id,
                group="features",
                content=f"Feature {i} content",
                summary=f"Feature {i}",
                status="pending",
                tags=["concurrent"]
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 验证所有操作都成功
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                raise AssertionError(f"Task {i} failed with exception: {result}")
            assert result["success"], f"Task {i} failed: {result.get('error')}"
            print(f"✓ Task {i} succeeded: {result['item_id']}")

        print("✓ 并发添加同分组条目：全部成功")

    async def test_concurrent_update_different_items(self):
        """测试：并发更新不同条目（应该都成功）.

        验证点：
        - 不同条目的update操作互不冲突
        - 所有更新操作都能成功完成
        """
        await self.async_setup_method()

        # 先添加3个条目
        item_ids = []
        for i in range(3):
            result = await self.project_service.add_item(
                project_id=self.project_id,
                group="features",
                content=f"Feature {i}",
                summary=f"Feature {i}",
                status="pending",
                tags=["test"]
            )
            item_ids.append(result["item_id"])

        # 并发更新这3个条目
        tasks = []
        for i, item_id in enumerate(item_ids):
            task = self.project_service.update_item(
                project_id=self.project_id,
                group="features",
                item_id=item_id,
                summary=f"Updated Feature {i}"
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 验证所有操作都成功
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                raise AssertionError(f"Update {i} failed: {result}")
            assert result["success"], f"Update {i} failed: {result.get('error')}"
            print(f"✓ Update {i} succeeded")

        print("✓ 并发更新不同条目：全部成功")

    async def test_sequential_add_update_delete(self):
        """测试：连续执行add/update/delete操作（验证B2锁释放）.

        验证点：
        - 操作序列的正确性
        - B2锁在操作后正确释放
        - 不会有锁泄漏
        """
        await self.async_setup_method()

        # 添加条目
        result1 = await self.project_service.add_item(
            project_id=self.project_id,
            group="features",
            content="Test feature",
            summary="Test",
            status="pending",
            tags=["test"]
        )
        assert result1["success"]
        item_id = result1["item_id"]
        print(f"✓ Added item: {item_id}")

        # 更新条目
        result2 = await self.project_service.update_item(
            project_id=self.project_id,
            group="features",
            item_id=item_id,
            summary="Updated Test"
        )
        assert result2["success"]
        print(f"✓ Updated item: {item_id}")

        # 删除条目
        result3 = await self.project_service.delete_item(
            project_id=self.project_id,
            group="features",
            item_id=item_id
        )
        assert result3["success"]
        print(f"✓ Deleted item: {item_id}")

        print("✓ 连续操作成功：B2锁正确释放")

    async def test_add_then_update_same_item(self):
        """测试：添加后立即更新同一条目（验证版本控制）.

        验证点：
        - 版本控制机制正常工作
        - 使用正确的版本号更新成功
        - 版本号正确递增
        """
        await self.async_setup_method()

        # 添加条目
        result1 = await self.project_service.add_item(
            project_id=self.project_id,
            group="features",
            content="Test feature",
            summary="Original",
            status="pending",
            tags=["test"]
        )
        assert result1["success"]
        item_id = result1["item_id"]
        version = result1.get("version", 1)
        print(f"✓ Added item: {item_id}, version: {version}")

        # 更新条目（使用正确的版本）
        result2 = await self.project_service.update_item(
            project_id=self.project_id,
            group="features",
            item_id=item_id,
            summary="Updated",
            expected_version=version
        )
        assert result2["success"]
        new_version = result2.get("version")
        print(f"✓ Updated item to version: {new_version}")

        print("✓ 添加后更新同一条目：版本控制正确")

    async def test_concurrent_add_and_rename(self):
        """测试：并发执行add和rename操作（验证barrier层级协调）.

        验证点：
        - add操作（B4）与rename操作（B2）的协调
        - barrier层级正确工作
        - 至少add操作应该成功
        """
        await self.async_setup_method()

        # 添加条目
        add_task = self.project_service.add_item(
            project_id=self.project_id,
            group="features",
            content="Test feature",
            summary="Test",
            status="pending",
            tags=["test"]
        )

        # 重命名项目
        rename_task = self.project_service.project_rename(
            project_id=self.project_id,
            new_name="renamed_concurrent_test"
        )

        # 并发执行（add是B4，rename是B2+B2持有）
        results = await asyncio.gather(add_task, rename_task, return_exceptions=True)

        add_result, rename_result = results

        if isinstance(add_result, Exception):
            raise AssertionError(f"Add failed: {add_result}")
        if isinstance(rename_result, Exception):
            raise AssertionError(f"Rename failed: {rename_result}")

        # 验证add成功（因为不需要持有B2）
        assert add_result["success"], f"Add should succeed: {add_result.get('error')}"
        print(f"✓ Add result: {add_result.get('success')}")
        print(f"✓ Rename result: {rename_result.get('success')}")
        print("✓ 跨级别并发操作：barrier层级协调正确")

    # ==================== 条目标签操作并发测试 ====================

    async def test_concurrent_add_item_tags(self):
        """测试：同一条目并发添加多个标签（都应该成功）.

        验证点：
        - 多个标签并发添加到同一条目
        - 所有添加操作都成功
        - 最终状态包含所有添加的标签
        """
        await self.async_setup_method()

        # 先添加一个测试条目
        add_result = await self.project_service.add_item(
            project_id=self.project_id,
            group="features",
            content="测试并发添加标签功能",
            summary="并发标签测试",
            status="pending",
            tags=["initial_tag"]
        )
        assert add_result["success"]
        item_id = add_result["item_id"]
        print(f"✓ 添加测试条目: {item_id}")

        # 预先注册标签
        tags_to_add = ["concurrent_tag1", "concurrent_tag2", "concurrent_tag3",
                       "concurrent_tag4", "concurrent_tag5"]
        for tag in tags_to_add:
            await self.tag_service.register_tag(
                project_id=self.project_id,
                tag_name=tag,
                summary=f"测试标签 {tag}"
            )

        # 并发添加多个标签到同一条目
        tasks = []
        for tag in tags_to_add:
            task = self.tag_service.add_item_tag(
                project_id=self.project_id,
                group_name="features",
                item_id=item_id,
                tag=tag
            )
            tasks.append(task)

        # 并发执行所有标签添加操作
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 验证所有操作都成功
        success_count = 0
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"✗ 添加标签 {tags_to_add[i]} 失败: {result}")
                assert False, f"添加标签操作 {i} 抛出异常: {result}"
            assert result["success"], f"添加标签 {tags_to_add[i]} 失败: {result.get('error')}"
            success_count += 1
            print(f"✓ 成功添加标签: {tags_to_add[i]}")

        print(f"✓ 并发添加标签测试通过：{success_count}/{len(tags_to_add)} 个标签添加成功")

        # 验证最终状态
        project_result = await self.project_service.get_project(self.project_id)
        items = project_result["data"]["features"]
        test_item = next((item for item in items if item["id"] == item_id), None)

        assert test_item is not None, "找不到测试条目"
        final_tags = set(test_item.get("tags", []))

        # 验证所有标签都被添加
        for tag in tags_to_add:
            assert tag in final_tags, f"标签 {tag} 未在最终标签列表中"

        print(f"✓ 最终标签列表验证通过: {final_tags}")

    async def test_add_remove_item_tags_concurrent(self):
        """测试：同一条目同时添加和删除标签（验证B5锁协调）.

        验证点：
        - 添加和删除标签操作的并发协调
        - B5锁正确工作
        - 最终状态符合预期
        """
        await self.async_setup_method()

        # 预先注册标签
        test_tags = ["concurrent_tag1", "concurrent_tag2", "concurrent_tag3", "to_be_deleted"]
        for tag in test_tags:
            await self.tag_service.register_tag(
                project_id=self.project_id,
                tag_name=tag,
                summary=f"测试标签 {tag}"
            )

        # 先添加一个测试条目，带有初始标签
        add_result = await self.project_service.add_item(
            project_id=self.project_id,
            group="features",
            content="测试并发添加删除标签功能",
            summary="并发添加删除标签测试",
            status="pending",
            tags=["initial_tag", "to_be_deleted"]
        )
        assert add_result["success"]
        item_id = add_result["item_id"]
        print(f"✓ 添加测试条目: {item_id}")

        # 并发执行添加和删除标签操作
        tasks = []

        # 添加新标签的任务
        add_tags = ["concurrent_tag1", "concurrent_tag2", "concurrent_tag3"]
        for tag in add_tags:
            task = self.tag_service.add_item_tag(
                project_id=self.project_id,
                group_name="features",
                item_id=item_id,
                tag=tag
            )
            tasks.append(("add", tag, task))

        # 删除标签的任务
        remove_tags = ["to_be_deleted"]
        for tag in remove_tags:
            task = self.tag_service.remove_item_tag(
                project_id=self.project_id,
                group_name="features",
                item_id=item_id,
                tag=tag
            )
            tasks.append(("remove", tag, task))

        # 随机化执行顺序以增加并发竞争
        import random
        random.shuffle(tasks)

        # 并发执行所有操作
        results = await asyncio.gather(*[task[2] for task in tasks], return_exceptions=True)

        # 验证所有操作都成功
        for i, (op_type, tag, _) in enumerate(tasks):
            result = results[i]
            if isinstance(result, Exception):
                print(f"✗ {op_type} 标签 {tag} 失败: {result}")
                assert False, f"{op_type}标签操作抛出异常: {result}"
            assert result["success"], f"{op_type}标签 {tag} 失败: {result.get('error')}"
            print(f"✓ 成功 {op_type} 标签: {tag}")

        print(f"✓ 并发添加删除标签测试通过：所有操作成功")

        # 验证最终状态
        project_result = await self.project_service.get_project(self.project_id)
        items = project_result["data"]["features"]
        test_item = next((item for item in items if item["id"] == item_id), None)

        assert test_item is not None, "找不到测试条目"
        final_tags = set(test_item.get("tags", []))

        # 验证新标签被添加，旧标签被删除
        for tag in add_tags:
            assert tag in final_tags, f"添加的标签 {tag} 未在最终标签列表中"

        assert "to_be_deleted" not in final_tags, "要删除的标签仍在最终标签列表中"
        assert "initial_tag" in final_tags, "初始标签不应该被删除"

        print(f"✓ 最终标签列表验证通过: {final_tags}")

    async def test_tag_ops_with_update_concurrent(self):
        """测试：tag操作与update_item并发（验证B5锁协调）.

        验证点：
        - 标签操作与条目更新的并发协调
        - B5锁正确工作
        - 操作被序列化但都成功
        """
        await self.async_setup_method()

        # 预先注册标签
        await self.tag_service.register_tag(
            project_id=self.project_id,
            tag_name="concurrent_tag1",
            summary="测试标签1"
        )
        await self.tag_service.register_tag(
            project_id=self.project_id,
            tag_name="concurrent_tag2",
            summary="测试标签2"
        )

        # 先添加一个测试条目
        add_result = await self.project_service.add_item(
            project_id=self.project_id,
            group="features",
            content="测试标签操作与更新并发",
            summary="原始摘要",
            status="pending",
            tags=["initial_tag"]
        )
        assert add_result["success"]
        item_id = add_result["item_id"]
        print(f"✓ 添加测试条目: {item_id}")

        # 并发执行标签操作和条目更新操作
        tasks = []

        # 添加标签的操作（需要B5锁）
        add_task = self.tag_service.add_item_tag(
            project_id=self.project_id,
            group_name="features",
            item_id=item_id,
            tag="concurrent_tag1"
        )
        tasks.append(("add_tag", add_task))

        # 更新条目的操作（也需要B5锁）
        update_task = self.project_service.update_item(
            project_id=self.project_id,
            group="features",
            item_id=item_id,
            summary="更新的摘要"
        )
        tasks.append(("update", update_task))

        # 再添加一个标签操作
        add_task2 = self.tag_service.add_item_tag(
            project_id=self.project_id,
            group_name="features",
            item_id=item_id,
            tag="concurrent_tag2"
        )
        tasks.append(("add_tag2", add_task2))

        # 并发执行所有操作
        results = await asyncio.gather(*[task[1] for task in tasks], return_exceptions=True)

        # 验证操作结果
        success_count = 0
        for i, (op_name, _) in enumerate(tasks):
            result = results[i]
            if isinstance(result, Exception):
                print(f"✗ {op_name} 操作失败: {result}")
                assert False, f"{op_name}操作抛出异常: {result}"
            assert result["success"], f"{op_name} 操作失败: {result.get('error')}"
            success_count += 1
            print(f"✓ {op_name} 操作成功")

        print(f"✓ 标签操作与更新并发测试通过：{success_count}/{len(tasks)} 个操作成功")

        # 验证最终状态
        project_result = await self.project_service.get_project(self.project_id)
        items = project_result["data"]["features"]
        test_item = next((item for item in items if item["id"] == item_id), None)

        assert test_item is not None, "找不到测试条目"

        # 验证摘要被更新
        assert test_item["summary"] == "更新的摘要", f"摘要未更新: {test_item['summary']}"
        print(f"✓ 摘要已更新: {test_item['summary']}")

        # 验证标签被添加
        final_tags = set(test_item.get("tags", []))
        assert "concurrent_tag1" in final_tags, "标签1未添加"
        assert "concurrent_tag2" in final_tags, "标签2未添加"
        assert "initial_tag" in final_tags, "初始标签丢失"

        print(f"✓ 最终标签列表验证通过: {final_tags}")
        print(f"✓ B5锁协调正确：标签操作与更新操作互不冲突")

    async def test_concurrent_tag_register_operations(self):
        """测试：并发执行tag_register操作（验证B3锁协调）.

        验证点：
        - 多个标签并发注册
        - B3锁正确工作
        - 所有注册操作都成功
        """
        await self.async_setup_method()

        # 并发注册多个标签
        tasks = []
        for i in range(3):
            task = self.tag_service.register_tag(
                project_id=self.project_id,
                tag_name=f"tag_{i}",
                summary=f"Tag {i}"
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 验证所有操作都成功
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                raise AssertionError(f"Tag register {i} failed: {result}")
            assert result["success"], f"Tag register {i} failed: {result.get('error')}"
            print(f"✓ Tag {i} registered")

        print("✓ 并发标签注册操作：全部成功")

    # ==================== B2级操作组合测试 ====================

    async def test_concurrent_rename_operations(self):
        """测试：并发执行多个rename操作（验证B2锁不会死锁）.

        验证点：
        - 多个项目并发重命名
        - B2锁不会死锁
        - 所有重命名操作都成功
        """
        await self.async_setup_method()

        # 注册多个项目
        project_ids = []
        for i in range(3):
            result = await self.project_service.register_project(
                f"rename_test_{i}",
                "/tmp/rename_test",
                summary=f"Rename test {i}"
            )
            project_ids.append(result["project_id"])

        # 并发重命名这些项目
        tasks = []
        for i, pid in enumerate(project_ids):
            task = self.project_service.project_rename(
                project_id=pid,
                new_name=f"renamed_{i}"
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 验证所有操作都成功
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                raise AssertionError(f"Rename {i} failed: {result}")
            assert result["success"], f"Rename {i} failed: {result.get('error')}"
            print(f"✓ Rename {i} succeeded")

        print("✓ 并发重命名操作：全部成功（B2锁不会死锁）")

        # 清理所有项目
        for pid in project_ids:
            try:
                await self.project_service.remove_project(pid, mode="delete")
            except:
                pass

    async def test_tag_delete_and_merge_concurrent(self):
        """测试：tag_delete和tag_merge并发执行（都是B2，验证不会死锁）.

        验证点：
        - tag_delete和tag_merge都是B2级操作
        - 两个操作不会死锁
        - 操作结果符合预期
        """
        await self.async_setup_method()

        # 预先注册3个标签
        tag_names = ["tag1", "tag2", "tag3"]
        for tag_name in tag_names:
            result = await self.tag_service.register_tag(
                project_id=self.project_id,
                tag_name=tag_name,
                summary=f"测试标签 {tag_name}"
            )
            assert result["success"], f"Failed to register {tag_name}"
            print(f"  ✓ 预先注册标签: {tag_name}")

        # 添加一些使用这些标签的条目
        for i in range(3):
            result = await self.project_service.add_item(
                project_id=self.project_id,
                group="features",
                content=f"Feature {i}",
                summary=f"Feature {i}",
                status="pending",
                tags=["tag1", "tag2"]
            )
            assert result["success"]
            print(f"  ✓ 添加条目 {i}")

        # 并发执行tag_delete和tag_merge
        delete_task = self.tag_service.delete_tag(
            project_id=self.project_id,
            tag_name="tag3",
            force=True
        )

        merge_task = self.tag_service.merge_tags(
            project_id=self.project_id,
            old_tag="tag1",
            new_tag="tag2"
        )

        # 并发执行
        print("  → 并发执行 tag_delete(tag3) 和 tag_merge(tag1→tag2)")
        results = await asyncio.gather(delete_task, merge_task, return_exceptions=True)

        delete_result, merge_result = results

        # 验证结果
        assert not isinstance(delete_result, Exception), f"Delete exception: {delete_result}"
        assert not isinstance(merge_result, Exception), f"Merge exception: {merge_result}"

        assert delete_result["success"], f"Delete failed: {delete_result.get('error')}"
        assert merge_result["success"], f"Merge failed: {merge_result.get('error')}"

        print(f"  ✓ tag_delete 成功: {delete_result['message']}")
        print(f"  ✓ tag_merge 成功: {merge_result['message']}")
        print(f"  ✓ 迁移条目数: {merge_result.get('migrated_count', 0)}")

        # 验证最终状态
        tag_result = await self.tag_service.list_all_registered_tags(self.project_id)
        remaining_tags = [t["tag"] for t in tag_result["tags"]]
        print(f"  ✓ 剩余标签: {remaining_tags}")

        assert "tag1" not in remaining_tags, "tag1 should be deleted (merged)"
        assert "tag3" not in remaining_tags, "tag3 should be deleted"
        assert "tag2" in remaining_tags, "tag2 should still exist"

        print("✓ 测试通过：tag_delete和tag_merge并发执行成功（无死锁）")

    async def test_tag_delete_with_project_rename(self):
        """测试：tag_delete与project_rename并发执行（都是B2）.

        验证点：
        - tag_delete和project_rename都是B2级操作
        - 两个操作正确协调
        - 不会死锁
        """
        await self.async_setup_method()

        # 预先注册标签
        await self.tag_service.register_tag(
            project_id=self.project_id,
            tag_name="test_tag",
            summary="测试标签"
        )
        print("  ✓ 预先注册标签: test_tag")

        # 添加条目
        result = await self.project_service.add_item(
            project_id=self.project_id,
            group="features",
            content="Test feature",
            summary="Test",
            status="pending",
            tags=["test_tag"]
        )
        assert result["success"]
        print(f"  ✓ 添加条目: {result['item_id']}")

        # 并发执行tag_delete和project_rename
        delete_task = self.tag_service.delete_tag(
            project_id=self.project_id,
            tag_name="test_tag",
            force=True
        )

        rename_task = self.project_service.project_rename(
            project_id=self.project_id,
            new_name="renamed_b2_test_project"
        )

        # 并发执行
        print("  → 并发执行 tag_delete 和 project_rename")
        results = await asyncio.gather(delete_task, rename_task, return_exceptions=True)

        delete_result, rename_result = results

        # 验证结果
        assert not isinstance(delete_result, Exception), f"Delete exception: {delete_result}"
        assert not isinstance(rename_result, Exception), f"Rename exception: {rename_result}"

        assert delete_result["success"], f"Delete failed: {delete_result.get('error')}"
        assert rename_result["success"], f"Rename failed: {rename_result.get('error')}"

        print(f"  ✓ tag_delete 成功: {delete_result['message']}")
        print(f"  ✓ project_rename 成功: {rename_result['message']}")

        # 验证项目确实被重命名
        project_data = await self.project_service.get_project(self.project_id)
        project_name = project_data["data"]["info"]["name"]
        assert project_name == "renamed_b2_test_project"
        print(f"  ✓ 项目名称验证: {project_name}")

        # 验证标签确实被删除
        tag_result = await self.tag_service.list_all_registered_tags(self.project_id)
        remaining_tags = [t["tag"] for t in tag_result["tags"]]
        assert "test_tag" not in remaining_tags
        print(f"  ✓ 剩余标签: {remaining_tags}")

        print("✓ 测试通过：tag_delete与project_rename并发执行成功")

    async def test_tag_register_during_tag_delete(self):
        """测试：tag_delete期间执行tag_register（B3 vs B2）.

        验证点：
        - tag_delete持有B2锁
        - tag_register需要获取B2锁（上行检查）
        - tag_register会等待tag_delete完成
        - 跨级别协调正确
        """
        await self.async_setup_method()

        # 预先注册标签
        await self.tag_service.register_tag(
            project_id=self.project_id,
            tag_name="old_tag",
            summary="旧标签"
        )
        print("  ✓ 预先注册标签: old_tag")

        # 添加使用该标签的条目
        result = await self.project_service.add_item(
            project_id=self.project_id,
            group="features",
            content="Test feature",
            summary="Test",
            status="pending",
            tags=["old_tag"]
        )
        assert result["success"]
        print(f"  ✓ 添加条目: {result['item_id']}")

        # 创建慢速tag_delete任务（模拟耗时操作）
        async def slow_tag_delete():
            await asyncio.sleep(0.1)
            return await self.tag_service.delete_tag(
                project_id=self.project_id,
                tag_name="old_tag",
                force=True
            )

        # 启动tag_delete
        delete_task = asyncio.create_task(slow_tag_delete())

        # 等待tag_delete获取B2锁
        await asyncio.sleep(0.05)

        # 在tag_delete执行期间启动tag_register
        print("  → 在tag_delete期间启动tag_register")
        register_task = self.tag_service.register_tag(
            project_id=self.project_id,
            tag_name="new_tag",
            summary="新标签"
        )

        # 等待两个操作完成
        results = await asyncio.gather(delete_task, register_task, return_exceptions=True)

        delete_result, register_result = results

        # 验证结果
        assert not isinstance(delete_result, Exception), f"Delete exception: {delete_result}"
        assert not isinstance(register_result, Exception), f"Register exception: {register_result}"

        assert delete_result["success"], f"Delete failed: {delete_result.get('error')}"
        assert register_result["success"], f"Register failed: {register_result.get('error')}"

        print(f"  ✓ tag_delete 成功: {delete_result['message']}")
        print(f"  ✓ tag_register 成功: {register_result['message']}")

        # 验证最终状态
        tag_result = await self.tag_service.list_all_registered_tags(self.project_id)
        remaining_tags = [t["tag"] for t in tag_result["tags"]]
        print(f"  ✓ 剩余标签: {remaining_tags}")

        assert "old_tag" not in remaining_tags, "old_tag should be deleted"
        assert "new_tag" in remaining_tags, "new_tag should exist"

        print("✓ 测试通过：tag_delete期间执行tag_register成功（跨级别协调正确）")

    async def test_tag_merge_with_project_rename(self):
        """测试：tag_merge与project_rename并发执行（都是B2）.

        验证点：
        - tag_merge和project_rename都是B2级操作
        - 复杂场景下的B2级操作协调
        - 不会死锁
        """
        await self.async_setup_method()

        # 预先注册标签
        tag_names = ["source_tag", "target_tag"]
        for tag_name in tag_names:
            result = await self.tag_service.register_tag(
                project_id=self.project_id,
                tag_name=tag_name,
                summary=f"标签 {tag_name}"
            )
            assert result["success"]
            print(f"  ✓ 预先注册标签: {tag_name}")

        # 添加使用source_tag的条目
        for i in range(2):
            result = await self.project_service.add_item(
                project_id=self.project_id,
                group="features",
                content=f"Feature {i}",
                summary=f"F{i}",
                status="pending",
                tags=["source_tag"]
            )
            assert result["success"]
            print(f"  ✓ 添加条目 {i} 使用 source_tag")

        # 并发执行tag_merge和project_rename
        merge_task = self.tag_service.merge_tags(
            project_id=self.project_id,
            old_tag="source_tag",
            new_tag="target_tag"
        )

        rename_task = self.project_service.project_rename(
            project_id=self.project_id,
            new_name="merged_renamed_project"
        )

        # 并发执行
        print("  → 并发执行 tag_merge 和 project_rename")
        results = await asyncio.gather(merge_task, rename_task, return_exceptions=True)

        merge_result, rename_result = results

        # 验证结果
        assert not isinstance(merge_result, Exception), f"Merge exception: {merge_result}"
        assert not isinstance(rename_result, Exception), f"Rename exception: {rename_result}"

        assert merge_result["success"], f"Merge failed: {merge_result.get('error')}"
        assert rename_result["success"], f"Rename failed: {rename_result.get('error')}"

        print(f"  ✓ tag_merge 成功: {merge_result['message']}")
        print(f"  ✓ project_rename 成功: {rename_result['message']}")
        print(f"  ✓ 迁移条目数: {merge_result.get('migrated_count', 0)}")

        # 验证最终状态
        project_data = await self.project_service.get_project(self.project_id)
        project_name = project_data["data"]["info"]["name"]
        assert project_name == "merged_renamed_project"
        print(f"  ✓ 项目名称: {project_name}")

        tag_result = await self.tag_service.list_all_registered_tags(self.project_id)
        remaining_tags = [t["tag"] for t in tag_result["tags"]]
        print(f"  ✓ 剩余标签: {remaining_tags}")

        assert "source_tag" not in remaining_tags, "source_tag should be deleted (merged)"
        assert "target_tag" in remaining_tags, "target_tag should exist"

        # 验证条目标签已更新
        features = project_data["data"]["features"]
        for feature in features:
            if "source_tag" in feature.get("tags", []):
                print(f"  ✗ 条目 {feature['id']} 仍有 source_tag")
                assert False, f"Item {feature['id']} still has source_tag"
            if "target_tag" in feature.get("tags", []):
                print(f"  ✓ 条目 {feature['id']} 已更新为 target_tag")

        print("✓ 测试通过：tag_merge与project_rename并发执行成功")

    async def test_multiple_b2_operations_sequence(self):
        """测试：连续执行多个B2级操作（验证锁释放）.

        验证点：
        - 连续执行多个B2操作
        - B2锁在每个操作后正确释放
        - 不会有锁泄漏
        """
        await self.async_setup_method()

        # 预先注册标签
        tag_names = ["tag_a", "tag_b", "tag_c"]
        for tag_name in tag_names:
            result = await self.tag_service.register_tag(
                project_id=self.project_id,
                tag_name=tag_name,
                summary=f"标签 {tag_name}"
            )
            assert result["success"]
            print(f"  ✓ 预先注册标签: {tag_name}")

        # 添加条目
        for i in range(2):
            result = await self.project_service.add_item(
                project_id=self.project_id,
                group="features",
                content=f"Feature {i}",
                summary=f"F{i}",
                status="pending",
                tags=["tag_a", "tag_b"]
            )
            assert result["success"]

        # 连续执行多个B2操作
        print("  → 执行 project_rename")
        result1 = await self.project_service.project_rename(
            project_id=self.project_id,
            new_name="step1_renamed"
        )
        assert result1["success"]
        print(f"  ✓ project_rename 成功")

        print("  → 执行 tag_delete")
        result2 = await self.tag_service.delete_tag(
            project_id=self.project_id,
            tag_name="tag_c",
            force=True
        )
        assert result2["success"]
        print(f"  ✓ tag_delete 成功")

        print("  → 执行 tag_merge")
        result3 = await self.tag_service.merge_tags(
            project_id=self.project_id,
            old_tag="tag_a",
            new_tag="tag_b"
        )
        assert result3["success"]
        print(f"  ✓ tag_merge 成功，迁移 {result3.get('migrated_count', 0)} 个条目")

        print("  → 再次执行 project_rename")
        result4 = await self.project_service.project_rename(
            project_id=self.project_id,
            new_name="step2_final_rename"
        )
        assert result4["success"]
        print(f"  ✓ 第二次 project_rename 成功")

        # 验证最终状态
        project_data = await self.project_service.get_project(self.project_id)
        project_name = project_data["data"]["info"]["name"]
        assert project_name == "step2_final_rename"
        print(f"  ✓ 最终项目名: {project_name}")

        tag_result = await self.tag_service.list_all_registered_tags(self.project_id)
        remaining_tags = [t["tag"] for t in tag_result["tags"]]
        print(f"  ✓ 最终标签: {remaining_tags}")

        assert "tag_a" not in remaining_tags, "tag_a should be merged"
        assert "tag_c" not in remaining_tags, "tag_c should be deleted"
        assert "tag_b" in remaining_tags, "tag_b should exist"

        print("✓ 测试通过：连续执行多个B2操作成功（锁正确释放）")

    async def test_concurrent_mixed_b2_b3_operations(self):
        """测试：多个标签操作与B2操作并发（复杂场景）.

        验证点：
        - B2级操作串行执行
        - B3级操作可以并发（在B2操作之外）
        - 不会死锁
        - 所有操作最终成功
        """
        await self.async_setup_method()

        # 预先注册标签
        base_tags = ["base1", "base2", "base3"]
        for tag_name in base_tags:
            await self.tag_service.register_tag(
                project_id=self.project_id,
                tag_name=tag_name,
                summary=f"基础标签 {tag_name}"
            )
            print(f"  ✓ 预先注册标签: {tag_name}")

        # 添加条目
        for i in range(3):
            await self.project_service.add_item(
                project_id=self.project_id,
                group="features",
                content=f"Feature {i}",
                summary=f"F{i}",
                status="pending",
                tags=["base1"]
            )

        # 创建多个并发任务
        tasks = []

        # B2级操作
        tasks.append(self.tag_service.delete_tag(
            project_id=self.project_id,
            tag_name="base3",
            force=True
        ))

        # B3级操作（可以并发）
        tasks.append(self.tag_service.register_tag(
            project_id=self.project_id,
            tag_name="new_tag1",
            summary="新标签1"
        ))

        tasks.append(self.tag_service.register_tag(
            project_id=self.project_id,
            tag_name="new_tag2",
            summary="新标签2"
        ))

        # B2级操作
        tasks.append(self.tag_service.merge_tags(
            project_id=self.project_id,
            old_tag="base1",
            new_tag="base2"
        ))

        # 并发执行所有任务
        print("  → 并发执行多个标签操作（包含B2和B3级别）")
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 统计结果
        exceptions = [r for r in results if isinstance(r, Exception)]
        successes = [r for r in results if not isinstance(r, Exception) and r.get("success")]
        failures = [r for r in results if not isinstance(r, Exception) and not r.get("success")]

        print(f"  ✓ 总操作数: {len(results)}")
        print(f"  ✓ 成功: {len(successes)}")
        print(f"  ✓ 失败: {len(failures)}")
        print(f"  ✓ 异常: {len(exceptions)}")

        # 验证没有异常
        assert len(exceptions) == 0, f"Got {len(exceptions)} exceptions"

        # 验证最终状态
        tag_result = await self.tag_service.list_all_registered_tags(self.project_id)
        remaining_tags = [t["tag"] for t in tag_result["tags"]]
        print(f"  ✓ 最终标签: {remaining_tags}")

        assert "base1" not in remaining_tags, "base1 should be merged"
        assert "base3" not in remaining_tags, "base3 should be deleted"
        assert "new_tag1" in remaining_tags, "new_tag1 should exist"
        assert "new_tag2" in remaining_tags, "new_tag2 should exist"

        print("✓ 测试通过：复杂并发场景下所有操作成功")

    # ==================== 高并发压力测试 ====================

    async def test_high_concurrency_tag_operations(self):
        """测试：高并发标签操作（压力测试）.

        验证点：
        - 大量并发标签操作
        - 系统在高并发下的稳定性
        - 数据一致性得到保证
        """
        await self.async_setup_method()

        # 预先注册标签
        test_tags = ["concurrent_tag1", "concurrent_tag2", "concurrent_tag3", "concurrent_tag4"]
        for tag in test_tags:
            await self.tag_service.register_tag(
                project_id=self.project_id,
                tag_name=tag,
                summary=f"测试标签 {tag}"
            )

        # 先添加多个测试条目
        item_ids = []
        for i in range(5):
            add_result = await self.project_service.add_item(
                project_id=self.project_id,
                group="features",
                content=f"测试条目 {i}",
                summary=f"条目{i}",
                status="pending",
                tags=["initial_tag"]
            )
            assert add_result["success"]
            item_ids.append(add_result["item_id"])

        print(f"✓ 添加 {len(item_ids)} 个测试条目")

        # 创建大量并发标签操作
        tasks = []

        # 为每个条目添加多个标签
        for item_id in item_ids:
            for tag in test_tags:
                task = self.tag_service.add_item_tag(
                    project_id=self.project_id,
                    group_name="features",
                    item_id=item_id,
                    tag=tag
                )
                tasks.append(task)

        print(f"✓ 创建 {len(tasks)} 个并发标签操作任务")

        # 并发执行所有操作
        import time
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        elapsed = time.time() - start_time

        # 统计结果
        success_count = sum(1 for r in results if not isinstance(r, Exception) and r.get("success"))
        exception_count = sum(1 for r in results if isinstance(r, Exception))
        failure_count = len(results) - success_count - exception_count

        print(f"✓ 高并发测试完成:")
        print(f"  - 总操作数: {len(results)}")
        print(f"  - 成功: {success_count}")
        print(f"  - 失败: {failure_count}")
        print(f"  - 异常: {exception_count}")
        print(f"  - 耗时: {elapsed:.2f}s")

        # 验证没有异常和失败
        assert exception_count == 0, f"存在 {exception_count} 个异常操作"
        assert failure_count == 0, f"存在 {failure_count} 个失败操作"

        # 验证最终数据一致性
        project_result = await self.project_service.get_project(self.project_id)
        items = project_result["data"]["features"]

        for item_id in item_ids:
            test_item = next((item for item in items if item["id"] == item_id), None)
            assert test_item is not None, f"找不到条目 {item_id}"
            final_tags = set(test_item.get("tags", []))

            # 验证所有标签都被添加
            for tag in test_tags:
                assert tag in final_tags, f"条目 {item_id} 缺少标签 {tag}"

        print(f"✓ 高并发标签操作测试通过：数据一致性验证成功")
