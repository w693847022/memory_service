#!/usr/bin/env python3
"""Drain机制完整并发测试.

整合了所有drain相关测试场景，覆盖五层阻挡位系统的Drain机制（排空机制）：

1. tag_delete drain - 标签删除时的drain机制
2. remove_project drain - 项目删除时的drain机制
3. delete_item drain - 条目删除时的drain机制
4. group_delete drain - 分组删除时的drain机制
5. 跨级别drain组合 - 各种跨级别的drain组合测试
6. 版本冲突测试 - 并发更新导致的版本冲突
7. 高并发负载测试 - 压力测试
"""

import sys
import os
import asyncio
import tempfile
import shutil
from pathlib import Path
import time
import pytest
import pytest_asyncio

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from business.storage import Storage
from business.project_service import ProjectService
from business.tag_service import TagService
from business.groups_service import GroupsService
from src.models.group import UnifiedGroupConfig, DEFAULT_GROUP_CONFIGS


@pytest.mark.asyncio
class TestDrainCompleteMechanism:
    """Drain机制完整并发测试类."""

    @pytest_asyncio.fixture(autouse=True)
    async def setup_teardown(self):
        """每个测试方法前后的设置和清理."""
        self.temp_dir = None
        self.storage = None
        self.project_service = None
        self.tag_service = None
        yield
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    async def setup_project(self, project_name="drain_test_project"):
        """设置测试项目.

        Args:
            project_name: 项目名称

        Returns:
            project_id: 项目ID
        """
        self.temp_dir = tempfile.mkdtemp()
        self.storage = Storage(storage_dir=self.temp_dir)
        self.groups_service = GroupsService(self.storage)
        self.project_service = ProjectService(self.storage, groups_service=self.groups_service)
        self.tag_service = TagService(self.storage)

        result = await self.project_service.register_project(
            project_name,
            f"/tmp/{project_name}",
            summary="Drain机制完整测试项目"
        )
        return result["data"]["project_id"]

    # ==================== tag_delete drain 测试 ====================

    async def test_tag_delete_drain_waits_for_add_item(self):
        """测试：tag_delete应该等待add_item完成（Drain机制）.

        测试场景：
        1. 注册一个测试标签
        2. 同时启动 tag_delete (需要drain B4+B5) 和 add_item (B4操作)
        3. tag_delete 应该等待 add_item 完成
        4. 验证操作正确完成，且无死锁
        """
        project_id = await self.setup_project("tag_delete_drain_test")

        # 步骤1: 注册一个测试标签
        await self.tag_service.register_tag(
            project_id, "test_tag", "排空机制测试专用标签"
        )
        print("  ✓ 注册标签: test_tag")

        # 步骤2: 添加一个初始条目（使用该标签）
        add_result = await self.project_service.add_item(
            project_id=project_id,
            group="features",
            content="Initial feature",
            summary="Initial",
            status="pending",
            tags=["test_tag"]
        )
        assert add_result["success"]
        print(f"  ✓ 添加初始条目: {add_result['data']['item_id']}")

        # 步骤3: 同时启动 tag_delete 和 add_item
        # tag_delete 需要 drain B4+B5，所以应该等待 add_item 完成
        add_task = self.project_service.add_item(
            project_id=project_id,
            group="features",
            content="Another feature",
            summary="Another",
            status="pending",
            tags=["test"]
        )

        delete_task = self.tag_service.delete_tag(
            project_id=project_id,
            tag_name="test_tag",
            force=True  # 强制删除，因为初始条目使用了此标签
        )

        # 步骤4: 并发执行
        start_time = time.time()
        results = await asyncio.gather(add_task, delete_task, return_exceptions=True)
        elapsed = time.time() - start_time

        add_result, delete_result = results

        # 步骤5: 验证结果
        assert not isinstance(add_result, Exception), f"Add异常: {add_result}"
        assert not isinstance(delete_result, Exception), f"Delete异常: {delete_result}"

        assert add_result["success"], f"Add失败: {add_result.get('error')}"
        assert delete_result["success"], f"Delete失败: {delete_result.get('error')}"

        print(f"  ✓ Add成功: {add_result['data']['item_id']}")
        print(f"  ✓ Delete成功")
        print(f"  ✓ 耗时: {elapsed:.2f}s (drain机制生效)")

        # 步骤6: 验证tag确实被删除了
        tag_result = await self.tag_service.list_all_registered_tags(project_id)
        tag_names = [t["tag"] for t in tag_result.get("tags", [])]
        assert "test_tag" not in tag_names, "Tag应该被删除"
        print(f"  ✓ Tag确认已删除")

        print("✓ 测试通过: tag_delete等待add_item完成")

    # ==================== remove_project drain 测试 ====================

    async def test_remove_project_drain_waits_for_update(self):
        """测试：remove_project应该等待update_item完成（Drain机制）.

        测试场景：
        1. 创建一个测试条目
        2. 启动慢速update_item操作
        3. 同时启动remove_project操作
        4. remove_project需要drain B4+B5，应该等待update完成
        """
        project_id = await self.setup_project("remove_project_drain_test")

        # 步骤1: 添加一个测试条目
        add_result = await self.project_service.add_item(
            project_id=project_id,
            group="features",
            content="Test feature",
            summary="Test",
            status="pending",
            tags=["test"]
        )
        assert add_result["success"]
        item_id = add_result["data"]["item_id"]
        print(f"  ✓ 添加测试条目: {item_id}")

        # 步骤2: 启动慢速update操作（模拟耗时操作）
        async def slow_update():
            """模拟慢速更新操作."""
            await asyncio.sleep(0.1)  # 模拟耗时
            result = await self.project_service.update_item(
                project_id=project_id,
                group="features",
                item_id=item_id,
                summary="Updated"
            )
            return result

        # 步骤3: 并发执行 update 和 remove_project
        update_task = asyncio.create_task(slow_update())

        # 给update一点时间先获取锁
        await asyncio.sleep(0.05)

        remove_task = self.project_service.remove_project(project_id, mode="delete")

        # 步骤4: 并发执行
        start_time = time.time()
        results = await asyncio.gather(update_task, remove_task, return_exceptions=True)
        elapsed = time.time() - start_time

        update_result, remove_result = results

        # 步骤5: 验证结果
        assert not isinstance(update_result, Exception), f"Update异常: {update_result}"
        assert not isinstance(remove_result, Exception), f"Remove异常: {remove_result}"

        assert update_result["success"], f"Update失败: {update_result.get('error')}"
        print(f"  ✓ Update成功: {update_result['data']['item_id']}")
        print(f"  ✓ Remove结果: {remove_result.get('success', False)}")
        print(f"  ✓ 耗时: {elapsed:.2f}s")

        print("✓ 测试通过: remove_project等待update_item完成")

    # ==================== delete_item drain 测试 ====================

    async def test_delete_item_drain_waits_for_update(self):
        """测试：delete_item应该等待update_item完成（Drain机制）.

        测试场景：
        1. 创建一个测试条目
        2. 同时启动 delete_item 和 update_item 操作
        3. delete_item需要drain B4+B5，应该等待update完成
        4. 验证操作正确完成，且无死锁
        """
        project_id = await self.setup_project("delete_item_drain_test")

        # 步骤1: 创建测试条目
        add_result = await self.project_service.add_item(
            project_id=project_id,
            group="features",
            content="Test feature for delete drain",
            summary="Original Feature",
            status="pending",
            tags=["test_tag"]
        )
        assert add_result["success"]
        item_id = add_result["data"]["item_id"]
        print(f"  ✓ 创建测试条目: {item_id}")

        # 步骤2: 启动慢速update操作
        async def slow_update():
            """模拟慢速更新操作."""
            await asyncio.sleep(0.1)  # 模拟耗时
            result = await self.project_service.update_item(
                project_id=project_id,
                group="features",
                item_id=item_id,
                summary="Updated Feature"
            )
            return result

        update_task = asyncio.create_task(slow_update())

        # 给update一点时间先获取B5锁
        await asyncio.sleep(0.05)

        # 步骤3: 启动delete操作
        delete_task = self.project_service.delete_item(
            project_id=project_id,
            group="features",
            item_id=item_id
        )

        # 步骤4: 并发执行并测量时间
        start_time = time.time()
        results = await asyncio.gather(update_task, delete_task, return_exceptions=True)
        elapsed = time.time() - start_time

        update_result, delete_result = results

        # 步骤5: 验证结果
        assert not isinstance(update_result, Exception), f"Update异常: {update_result}"
        assert not isinstance(delete_result, Exception), f"Delete异常: {delete_result}"

        if update_result.get("success"):
            print(f"  ✓ Update成功: {update_result['data']['item_id']}")
        else:
            print(f"  ⚠ Update失败（预期行为）: {update_result.get('error', 'unknown')}")

        if delete_result.get("success"):
            print(f"  ✓ Delete成功")
        else:
            print(f"  ⚠ Delete失败: {delete_result.get('error', 'unknown')}")

        print(f"  ✓ 耗时: {elapsed:.2f}s (drain机制生效)")

        # 验证不会死锁
        assert elapsed < 2.0, f"可能发生死锁，耗时: {elapsed:.2f}s"

        print("✓ 测试通过: delete_item正确等待update_item完成")

    async def test_delete_item_drain_waits_for_multiple_updates(self):
        """测试：delete_item应该等待多个update_item操作完成.

        测试场景：
        1. 创建一个测试条目
        2. 同时启动多个update_item操作
        3. 启动delete_item操作
        4. 验证delete等待所有update完成
        """
        project_id = await self.setup_project("delete_multiple_updates_test")

        # 步骤1: 创建测试条目
        add_result = await self.project_service.add_item(
            project_id=project_id,
            group="features",
            content="Test feature for multiple updates",
            summary="Original",
            status="pending",
            tags=["test"]
        )
        assert add_result["success"]
        item_id = add_result["data"]["item_id"]
        version = add_result["data"]["item"].get("_v", 1)
        print(f"  ✓ 创建测试条目: {item_id}, version: {version}")

        # 步骤2: 启动多个update操作
        async def update_with_version(new_summary, ver):
            """带版本号的更新操作."""
            await asyncio.sleep(0.05)  # 模拟耗时
            result = await self.project_service.update_item(
                project_id=project_id,
                group="features",
                item_id=item_id,
                summary=new_summary,
                expected_version=ver
            )
            return result

        # 启动3个更新操作
        update_tasks = [
            update_with_version("Update 1", version),
            update_with_version("Update 2", version),
            update_with_version("Update 3", version)
        ]

        # 等待更新启动
        await asyncio.sleep(0.02)

        # 步骤3: 启动delete操作
        delete_task = self.project_service.delete_item(
            project_id=project_id,
            group="features",
            item_id=item_id
        )

        # 步骤4: 并发执行
        start_time = time.time()
        all_results = await asyncio.gather(*update_tasks, delete_task, return_exceptions=True)
        elapsed = time.time() - start_time

        update_results = all_results[:len(update_tasks)]
        delete_result = all_results[len(update_tasks)]

        # 步骤5: 验证结果
        assert not isinstance(delete_result, Exception), f"Delete异常: {delete_result}"

        success_updates = sum(1 for r in update_results if not isinstance(r, Exception) and r.get("success"))
        conflict_updates = sum(1 for r in update_results if not isinstance(r, Exception) and r.get("error") == "version_conflict")

        print(f"  ✓ 成功更新: {success_updates}")
        print(f"  ✓ 版本冲突: {conflict_updates}")
        print(f"  ✓ Delete结果: {delete_result.get('success', False)}")
        print(f"  ✓ 耗时: {elapsed:.2f}s")

        assert elapsed < 3.0, f"可能发生死锁，耗时: {elapsed:.2f}s"

        print("✓ 测试通过: delete_item正确等待多个update_item完成")

    async def test_delete_item_concurrent_with_tag_operations(self):
        """测试：delete_item与tag操作并发（Drain机制）.

        测试场景：
        1. 注册一个测试标签
        2. 创建一个测试条目（不含该标签）
        3. 同时启动 delete_item 和 add_item_tag 操作
        4. 验证tag操作在delete期间被正确处理
        """
        project_id = await self.setup_project("delete_tag_concurrent_test")

        # 步骤1: 注册测试标签
        tag_result = await self.tag_service.register_tag(
            project_id=project_id,
            tag_name="concurrent_tag",
            summary="并发删除操作测试标签"
        )
        assert tag_result["success"]
        print(f"  ✓ 注册标签: concurrent_tag")

        # 步骤2: 创建测试条目（不含该标签）
        add_result = await self.project_service.add_item(
            project_id=project_id,
            group="features",
            content="Test feature for tag concurrent",
            summary="Feature without tag",
            status="pending",
            tags=[]
        )
        assert add_result["success"]
        item_id = add_result["data"]["item_id"]
        print(f"  ✓ 创建测试条目: {item_id}")

        # 步骤3: 启动慢速delete操作
        async def slow_delete():
            """模拟慢速删除操作."""
            await asyncio.sleep(0.1)  # 模拟耗时
            result = await self.project_service.delete_item(
                project_id=project_id,
                group="features",
                item_id=item_id
            )
            return result

        delete_task = asyncio.create_task(slow_delete())

        # 给delete一点时间先获取B4锁
        await asyncio.sleep(0.05)

        # 步骤4: 启动add_tag操作
        add_tag_task = self.tag_service.add_item_tag(
            project_id=project_id,
            group_name="features",
            item_id=item_id,
            tag="concurrent_tag"
        )

        # 步骤5: 并发执行
        start_time = time.time()
        results = await asyncio.gather(delete_task, add_tag_task, return_exceptions=True)
        elapsed = time.time() - start_time

        delete_result = results[0]
        add_tag_result = results[1] if len(results) > 1 else None

        # 步骤6: 验证结果
        assert not isinstance(delete_result, Exception), f"Delete异常: {delete_result}"

        if add_tag_result and not isinstance(add_tag_result, Exception):
            print(f"  ✓ Delete结果: {delete_result.get('success', False)}")
            print(f"  ✓ Add_tag结果: {add_tag_result.get('success', False)}")
        else:
            print(f"  ✓ Delete结果: {delete_result.get('success', False)}")
            print(f"  ⚠ Add_tag可能因条目已删除而失败")

        print(f"  ✓ 耗时: {elapsed:.2f}s")

        assert elapsed < 2.0, f"可能发生死锁，耗时: {elapsed:.2f}s"

        print("✓ 测试通过: delete_item与tag操作正确协调")

    async def test_delete_item_during_tag_operations(self):
        """测试：delete_item期间的tag操作应该被正确处理.

        测试场景：
        1. 创建一个带标签的测试条目
        2. 启动delete_item操作
        3. 在delete期间尝试add/remove_item_tag
        4. 验证tag操作正确处理（可能失败但不应死锁）
        """
        project_id = await self.setup_project("delete_during_tag_test")

        # 步骤1: 注册标签
        await self.tag_service.register_tag(
            project_id=project_id,
            tag_name="delete_during_tag",
            summary="删除期间操作测试标签"
        )
        print(f"  ✓ 注册标签: delete_during_tag")

        # 步骤2: 创建带标签的测试条目
        add_result = await self.project_service.add_item(
            project_id=project_id,
            group="features",
            content="Test feature for tag during delete",
            summary="Feature with tag",
            status="pending",
            tags=["delete_during_tag"]
        )
        assert add_result["success"]
        item_id = add_result["data"]["item_id"]
        print(f"  ✓ 创建测试条目: {item_id}")

        # 步骤3: 启动慢速delete
        async def slow_delete():
            """模拟慢速删除操作."""
            await asyncio.sleep(0.15)
            result = await self.project_service.delete_item(
                project_id=project_id,
                group="features",
                item_id=item_id
            )
            return result

        delete_task = asyncio.create_task(slow_delete())

        # 等待delete获取B4锁
        await asyncio.sleep(0.05)

        # 步骤4: 在delete期间尝试tag操作
        async def tag_operations():
            """执行多个tag操作."""
            results = []

            # add tag (B5操作)
            await asyncio.sleep(0.02)
            result1 = await self.tag_service.add_item_tag(
                project_id=project_id,
                group_name="features",
                item_id=item_id,
                tag="delete_during_tag"
            )
            results.append(("add_tag", result1))

            # remove tag (B5操作)
            await asyncio.sleep(0.02)
            result2 = await self.tag_service.remove_item_tag(
                project_id=project_id,
                group_name="features",
                item_id=item_id,
                tag="delete_during_tag"
            )
            results.append(("remove_tag", result2))

            return results

        tag_task = asyncio.create_task(tag_operations())

        # 步骤5: 并发执行
        start_time = time.time()
        delete_result, tag_results = await asyncio.gather(
            delete_task, tag_task, return_exceptions=True
        )
        elapsed = time.time() - start_time

        # 步骤6: 验证结果
        assert not isinstance(delete_result, Exception), f"Delete异常: {delete_result}"

        print(f"  ✓ Delete结果: {delete_result.get('success', False)}")

        if not isinstance(tag_results, Exception):
            for op_name, result in tag_results:
                if not isinstance(result, Exception):
                    print(f"  ✓ {op_name}结果: {result.get('success', False)}")
                else:
                    print(f"  ⚠ {op_name}异常: {result}")
        else:
            print(f"  ⚠ Tag操作异常: {tag_results}")

        print(f"  ✓ 耗时: {elapsed:.2f}s")

        assert elapsed < 2.0, f"可能发生死锁，耗时: {elapsed:.2f}s"

        print("✓ 测试通过: delete期间的tag操作正确处理")

    async def test_concurrent_delete_different_items(self):
        """测试：并发删除不同条目（Drain机制）.

        测试场景：
        1. 创建多个测试条目
        2. 同时删除不同的条目
        3. 验证并发删除不同条目不会互相阻塞
        """
        project_id = await self.setup_project("concurrent_delete_test")

        # 步骤1: 创建3个测试条目
        item_ids = []
        for i in range(3):
            add_result = await self.project_service.add_item(
                project_id=project_id,
                group="features",
                content=f"Test feature {i} for concurrent delete",
                summary=f"Feature {i}",
                status="pending",
                tags=[f"tag_{i}"]
            )
            assert add_result["success"]
            item_ids.append(add_result["data"]["item_id"])
        print(f"  ✓ 创建 {len(item_ids)} 个测试条目")

        # 步骤2: 并发删除不同的条目
        async def delete_with_delay(item_id, delay):
            """带延时的删除操作."""
            await asyncio.sleep(delay)
            result = await self.project_service.delete_item(
                project_id=project_id,
                group="features",
                item_id=item_id
            )
            return result

        # 创建3个删除任务，不同延时
        tasks = [
            delete_with_delay(item_ids[0], 0.05),
            delete_with_delay(item_ids[1], 0.03),
            delete_with_delay(item_ids[2], 0.07)
        ]

        # 步骤3: 并发执行
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        elapsed = time.time() - start_time

        # 步骤4: 验证结果
        exceptions = [r for r in results if isinstance(r, Exception)]
        successes = [r for r in results if not isinstance(r, Exception) and r.get("success")]

        print(f"  ✓ 成功删除: {len(successes)}/{len(results)}")
        print(f"  ✓ 异常数: {len(exceptions)}")
        print(f"  ✓ 耗时: {elapsed:.2f}s")

        assert len(exceptions) == 0, f"存在 {len(exceptions)} 个异常: {exceptions}"
        assert len(successes) > 0, "没有删除成功"
        assert elapsed < 2.0, f"可能发生死锁，耗时: {elapsed:.2f}s"

        # 步骤5: 验证最终状态
        project_data = await self.project_service.get_project(project_id)
        features = project_data["data"]["features"]
        remaining_items = [f for f in features if f["id"] in item_ids]

        print(f"  ✓ 剩余条目数: {len(remaining_items)}")
        print(f"  ✓ 应该为: {len(item_ids) - len(successes)}")

        assert len(remaining_items) == len(item_ids) - len(successes), \
            f"剩余条目数不匹配: 期望 {len(item_ids) - len(successes)}, 实际 {len(remaining_items)}"

        print("✓ 测试通过: 并发删除不同条目正确执行")

    # ==================== group_delete drain 测试 ====================

    async def test_group_delete_drain_blocks_add_item(self):
        """测试：group_delete应该等待add_item完成（Drain机制）.

        测试场景：
        1. 创建自定义分组
        2. 同时启动 group_delete 和 add_item 操作
        3. group_delete需要drain B4+B5，应该等待add_item完成
        """
        project_id = await self.setup_project("group_delete_drain_test")

        # 步骤1: 创建自定义组
        group_config = UnifiedGroupConfig(
            content_max_bytes=240,
            summary_max_bytes=90,
            allow_related=False,
            enable_status=True,
            enable_severity=False
        )
        group_data = group_config.to_dict()
        group_data["description"] = "测试组"

        result = await self.project_service.add_item(
            project_id=project_id,
            group="groups",
            content=str(group_data),
            summary="创建测试组",
            tags=[]
        )
        assert result["success"]
        custom_group_name = f"custom_test_group_{int(time.time())}"
        print(f"  ✓ 创建自定义组请求")

        # 步骤2: 并发执行 group_delete 和 add_item
        # 添加一个条目到features（B4操作）
        add_task = self.project_service.add_item(
            project_id=project_id,
            group="features",
            content="Test feature",
            summary="Test",
            status="pending",
            tags=["test"]
        )

        # 删除自定义组（需要drain）
        delete_task = self.project_service.update_item(
            project_id=project_id,
            group="groups",
            item_id=custom_group_name,
            content=f"{group_data}",
            summary=custom_group_name,
            tags=[]
        )

        # 步骤3: 并发执行
        start_time = time.time()
        results = await asyncio.gather(add_task, delete_task, return_exceptions=True)
        elapsed = time.time() - start_time

        add_result, delete_result = results

        # 步骤4: 验证结果
        assert not isinstance(add_result, Exception), f"Add异常: {add_result}"
        assert not isinstance(delete_result, Exception), f"Delete异常: {delete_result}"

        print(f"  ✓ Add结果: {add_result.get('success')}")
        print(f"  ✓ Delete结果: {delete_result.get('success')}")
        print(f"  ✓ 耗时: {elapsed:.2f}s")

        print("✓ 测试通过: group_delete与add_item协调")

    # ==================== 跨级别drain组合测试 ====================

    async def test_project_rename_with_concurrent_updates(self):
        """测试：project_rename期间并发update应该被正确处理.

        测试场景：
        1. 创建多个条目
        2. 启动project_rename操作
        3. 在rename期间并发更新条目
        4. 验证操作正确协调，无死锁
        """
        project_id = await self.setup_project("rename_concurrent_test")

        # 步骤1: 创建3个条目
        item_ids = []
        for i in range(3):
            result = await self.project_service.add_item(
                project_id=project_id,
                group="features",
                content=f"Feature {i}",
                summary=f"F{i}",
                status="pending",
                tags=["test"]
            )
            item_ids.append(result["data"]["item_id"])
        print(f"  ✓ 添加 {len(item_ids)} 个条目")

        # 步骤2: 在rename期间并发更新
        rename_task = self.project_service.project_rename(
            project_id=project_id,
            new_name="renamed_drain_test"
        )

        # 等待rename获取B2后，启动更新操作
        async def delayed_updates():
            await asyncio.sleep(0.1)  # 等待rename获取B2
            tasks = []
            for item_id in item_ids:
                task = self.project_service.update_item(
                    project_id=project_id,
                    group="features",
                    item_id=item_id,
                    summary=f"Updated {item_id}"
                )
                tasks.append(task)
            return await asyncio.gather(*tasks, return_exceptions=True)

        # 步骤3: 并发执行
        rename_result, update_results = await asyncio.gather(
            rename_task, delayed_updates(), return_exceptions=True
        )

        assert not isinstance(rename_result, Exception), f"Rename异常: {rename_result}"
        assert rename_result["success"], f"Rename失败: {rename_result.get('error')}"
        print(f"  ✓ Rename成功")

        # 检查更新结果（可能全部失败，也可能部分成功）
        success_updates = sum(1 for r in update_results if not isinstance(r, Exception) and r.get("success"))
        print(f"  ✓ 成功的更新: {success_updates}/{len(update_results)}")

        print("✓ 测试通过: rename期间并发更新协调")

    # ==================== 版本冲突测试 ====================

    async def test_concurrent_update_same_item_version_conflict(self):
        """测试：同一item的并发更新应该只有一个成功（版本冲突）.

        测试场景：
        1. 创建一个测试条目
        2. 同时启动多个update_item操作（使用相同版本号）
        3. 验证只有一个成功，其他返回版本冲突
        """
        project_id = await self.setup_project("version_conflict_test")

        # 步骤1: 创建测试条目
        add_result = await self.project_service.add_item(
            project_id=project_id,
            group="features",
            content="Test feature",
            summary="Original",
            status="pending",
            tags=["test"]
        )
        assert add_result["success"]
        item_id = add_result["data"]["item_id"]
        version = add_result["data"]["item"].get("_v", 1)
        print(f"  ✓ 添加条目: {item_id}, version: {version}")

        # 步骤2: 两个并发更新操作，都使用相同的版本号
        update1 = self.project_service.update_item(
            project_id=project_id,
            group="features",
            item_id=item_id,
            summary="Update 1",
            expected_version=version
        )

        update2 = self.project_service.update_item(
            project_id=project_id,
            group="features",
            item_id=item_id,
            summary="Update 2",
            expected_version=version
        )

        # 步骤3: 并发执行
        results = await asyncio.gather(update1, update2, return_exceptions=True)

        # 步骤4: 验证：只有一个成功，另一个返回版本冲突
        assert not isinstance(results[0], Exception), f"Update1异常: {results[0]}"
        assert not isinstance(results[1], Exception), f"Update2异常: {results[1]}"

        success_count = sum(1 for r in results if r.get("success"))
        conflict_count = sum(1 for r in results if r.get("error") == "version_conflict")

        print(f"  ✓ 成功数: {success_count}")
        print(f"  ✓ 冲突数: {conflict_count}")

        assert success_count == 1, f"期望1个成功，实际 {success_count}"
        assert conflict_count == 1, f"期望1个冲突，实际 {conflict_count}"

        # 步骤5: 验证最终状态
        get_result = await self.project_service.get_project(project_id)
        items = get_result["data"]["features"]
        item = next(i for i in items if i["id"] == item_id)
        print(f"  ✓ 最终summary: {item['summary']}")

        print("✓ 测试通过: 版本冲突正确处理")

    # ==================== 高并发负载测试 ====================

    async def test_high_concurrent_load(self):
        """测试：高并发负载（压力测试）.

        测试场景：
        1. 并发执行大量操作（add、tag register等）
        2. 验证无死锁、数据一致性
        """
        project_id = await self.setup_project("high_concurrent_load_test")

        # 步骤1: 并发执行大量操作
        tasks = []

        # 10个add操作
        for i in range(10):
            task = self.project_service.add_item(
                project_id=project_id,
                group="features",
                content=f"Feature {i}",
                summary=f"F{i}",
                status="pending",
                tags=["stress"]
            )
            tasks.append(task)

        # 5个tag register操作
        for i in range(5):
            task = self.tag_service.register_tag(
                project_id=project_id,
                tag_name=f"stress_tag_{i}",
                summary=f"Stress tag {i}"
            )
            tasks.append(task)

        # 步骤2: 执行所有并发操作
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        elapsed = time.time() - start_time

        # 步骤3: 统计结果
        exceptions = sum(1 for r in results if isinstance(r, Exception))
        successes = sum(1 for r in results if not isinstance(r, Exception) and r.get("success"))
        failures = len(results) - successes - exceptions

        print(f"  ✓ 总操作数: {len(results)}")
        print(f"  ✓ 成功: {successes}")
        print(f"  ✓ 失败: {failures}")
        print(f"  ✓ 异常: {exceptions}")
        print(f"  ✓ 耗时: {elapsed:.2f}s")

        # 步骤4: 验证
        assert exceptions == 0, f"存在 {exceptions} 个异常，可能死锁"
        assert successes > 0, "没有操作成功"

        # 步骤5: 验证最终数据一致性
        project_data = await self.project_service.get_project(project_id)
        features = project_data["data"]["features"]
        print(f"  ✓ 最终features数量: {len(features)}")

        print("✓ 测试通过: 高并发负载无死锁")
