#!/usr/bin/env python3
"""标签数量限制集成测试.

测试 max_tags 配置的完整流程：
1. 创建 item 时标签数量超限被拒绝
2. 更新 item 时标签数量超限被拒绝
3. 不同组的 max_tags 配置生效
4. 向后兼容（现有 item 不受影响）
"""

import sys
import os
import tempfile
import shutil
import asyncio
from pathlib import Path
import pytest
import pytest_asyncio

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from business.storage import Storage
from business.project_service import ProjectService
from business.groups_service import GroupsService


@pytest.mark.asyncio
class TestMaxTagsValidation:
    """标签数量限制集成测试类."""

    @pytest_asyncio.fixture(autouse=True)
    async def setup_teardown(self):
        """每个测试方法前后的设置和清理."""
        self.temp_dir = None
        self.storage = None
        self.project_service = None
        self.groups_service = None
        self.project_id = None
        yield
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    async def async_setup_method(self):
        """每个测试方法前执行：设置测试环境."""
        self.temp_dir = tempfile.mkdtemp()
        self.storage = Storage(storage_dir=self.temp_dir)
        self.groups_service = GroupsService(self.storage)
        self.project_service = ProjectService(self.storage, self.groups_service)

        # 注册测试项目
        result = await self.project_service.register_project("测试项目", "/tmp/test")
        self.project_id = result["data"]["project_id"]

    async def test_add_item_with_tags_exceeding_limit(self):
        """测试添加 item 时标签数量超限被拒绝."""
        print("测试: 添加 item 时标签数量超限...")
        await self.async_setup_method()

        # 尝试添加3个标签（超过默认限制2）
        result = await self.project_service.add_item(
            project_id=self.project_id,
            group="features",
            content="测试内容",
            summary="测试摘要",
            status="pending",
            tags=["tag1", "tag2", "tag3"]  # 超过限制
        )

        assert not result["success"], "应该添加失败"
        assert "标签数量超限" in result["error"], f"错误消息应该包含超限提示: {result['error']}"
        assert "当前 3 个" in result["error"], f"错误消息应该包含当前数量: {result['error']}"
        assert "最大允许 2 个" in result["error"], f"错误消息应该包含最大限制: {result['error']}"

        print(f"  ✓ 添加 item 时标签数量超限被拒绝: {result['error']}")

    async def test_add_item_with_tags_within_limit(self):
        """测试添加 item 时标签数量在限制内成功."""
        print("测试: 添加 item 时标签数量在限制内...")
        await self.async_setup_method()

        # 添加2个标签（等于限制）
        result = await self.project_service.add_item(
            project_id=self.project_id,
            group="features",
            content="测试内容",
            summary="测试摘要",
            status="pending",
            tags=["tag1", "tag2"]
        )

        assert result["success"], f"应该添加成功: {result.get('error')}"
        assert "item_id" in result["data"], "返回数据应该包含 item_id"

        print(f"  ✓ 添加 item 时标签数量在限制内成功: {result['data']['item_id']}")

    async def test_add_item_with_empty_tags(self):
        """测试添加 item 时标签数量为0失败（需要至少1个标签）."""
        print("测试: 添加 item 时标签数量为0...")
        await self.async_setup_method()

        # 尝试添加空标签列表
        result = await self.project_service.add_item(
            project_id=self.project_id,
            group="features",
            content="测试内容",
            summary="测试摘要",
            status="pending",
            tags=[]
        )

        assert not result["success"], "空标签列表应该添加失败"
        assert "tags 参数不能为空" in result["error"], f"错误消息应该提示标签不能为空: {result['error']}"

        print(f"  ✓ 添加 item 时空标签列表被拒绝: {result['error']}")

    async def test_update_item_with_tags_exceeding_limit(self):
        """测试更新 item 时标签数量超限被拒绝."""
        print("测试: 更新 item 时标签数量超限...")
        await self.async_setup_method()

        # 先添加一个正常的 item
        add_result = await self.project_service.add_item(
            project_id=self.project_id,
            group="features",
            content="测试内容",
            summary="测试摘要",
            status="pending",
            tags=["tag1"]
        )
        item_id = add_result["data"]["item_id"]

        # 尝试更新为3个标签（超过限制）
        result = await self.project_service.update_item(
            project_id=self.project_id,
            group="features",
            item_id=item_id,
            tags=["tag1", "tag2", "tag3"]  # 超过限制
        )

        assert not result["success"], "应该更新失败"
        assert "标签数量超限" in result["error"], f"错误消息应该包含超限提示: {result['error']}"

        print(f"  ✓ 更新 item 时标签数量超限被拒绝: {result['error']}")

    async def test_update_item_with_tags_within_limit(self):
        """测试更新 item 时标签数量在限制内成功."""
        print("测试: 更新 item 时标签数量在限制内...")
        await self.async_setup_method()

        # 先添加一个正常的 item
        add_result = await self.project_service.add_item(
            project_id=self.project_id,
            group="features",
            content="测试内容",
            summary="测试摘要",
            status="pending",
            tags=["tag1"]
        )
        item_id = add_result["data"]["item_id"]

        # 更新为2个标签（等于限制）
        result = await self.project_service.update_item(
            project_id=self.project_id,
            group="features",
            item_id=item_id,
            tags=["tag1", "tag2"]
        )

        assert result["success"], f"应该更新成功: {result.get('error')}"

        # 验证更新后的标签
        project_data = await self.storage.get_project_data(self.project_id)
        item = project_data.get_item("features", item_id)
        assert item.tags == ["tag1", "tag2"], f"标签应该被更新为 ['tag1', 'tag2']，实际是 {item.tags}"

        print(f"  ✓ 更新 item 时标签数量在限制内成功")

    async def test_different_groups_with_custom_max_tags(self):
        """测试不同组的自定义 max_tags 配置."""
        print("测试: 不同组的自定义 max_tags 配置...")
        await self.async_setup_method()

        # 修改 features 组的 max_tags 为 1
        await self.groups_service.update_group_config(
            self.project_id, "features", {"max_tags": 1}
        )

        # 修改 notes 组的 max_tags 为 5
        await self.groups_service.update_group_config(
            self.project_id, "notes", {"max_tags": 5}
        )

        # features 组：尝试添加2个标签（超过限制1）
        result = await self.project_service.add_item(
            project_id=self.project_id,
            group="features",
            content="测试内容",
            summary="测试摘要",
            tags=["tag1", "tag2"]
        )
        assert not result["success"], "features 组应该拒绝2个标签"
        assert "最大允许 1 个" in result["error"], f"错误消息应该提示最大允许1个: {result['error']}"

        # features 组：添加1个标签（等于限制）
        result = await self.project_service.add_item(
            project_id=self.project_id,
            group="features",
            content="测试内容",
            summary="测试摘要",
            tags=["tag1"]
        )
        assert result["success"], "features 组应该接受1个标签"

        # notes 组：添加5个标签（等于限制）
        result = await self.project_service.add_item(
            project_id=self.project_id,
            group="notes",
            content="测试内容",
            summary="测试摘要",
            tags=["tag1", "tag2", "tag3", "tag4", "tag5"]
        )
        assert result["success"], "notes 组应该接受5个标签"

        # notes 组：尝试添加6个标签（超过限制5）
        result = await self.project_service.add_item(
            project_id=self.project_id,
            group="notes",
            content="测试内容",
            summary="测试摘要",
            tags=["tag1", "tag2", "tag3", "tag4", "tag5", "tag6"]
        )
        assert not result["success"], "notes 组应该拒绝6个标签"
        assert "最大允许 5 个" in result["error"], f"错误消息应该提示最大允许5个: {result['error']}"

        print(f"  ✓ 不同组的自定义 max_tags 配置生效")

    async def test_backward_compatibility_existing_items(self):
        """测试向后兼容：现有 item 不受影响."""
        print("测试: 向后兼容 - 现有 item 不受影响...")
        await self.temp_setup_with_old_item()

        # 验证旧 item 存在且有3个标签（超过当前限制）
        project_data = await self.storage.get_project_data(self.project_id)
        old_item = project_data.get_item("features", self.old_item_id)
        assert old_item is not None, "旧 item 应该存在"
        assert len(old_item.tags) == 3, f"旧 item 应该有3个标签，实际有 {len(old_item.tags)} 个"

        # 验证可以读取旧 item（直接从存储读取）
        project_data = await self.storage.get_project_data(self.project_id)
        old_item_check = project_data.get_item("features", self.old_item_id)
        assert old_item_check is not None, "应该能读取旧 item"

        # 验证可以更新旧 item 的其他字段（不影响标签）
        result = await self.project_service.update_item(
            project_id=self.project_id,
            group="features",
            item_id=self.old_item_id,
            content="更新后的内容"
        )
        assert result["success"], "应该能更新旧 item 的其他字段"

        # 验证标签没有被改变
        project_data = await self.storage.get_project_data(self.project_id)
        updated_item = project_data.get_item("features", self.old_item_id)
        assert len(updated_item.tags) == 3, "标签应该保持不变"

        print(f"  ✓ 向后兼容：现有 item 不受影响")

    async def temp_setup_with_old_item(self):
        """临时设置：创建一个有3个标签的旧 item（模拟向后兼容场景）."""
        self.temp_dir = tempfile.mkdtemp()
        self.storage = Storage(storage_dir=self.temp_dir)
        self.groups_service = GroupsService(self.storage)
        self.project_service = ProjectService(self.storage, self.groups_service)

        # 注册项目
        result = await self.project_service.register_project("测试项目", "/tmp/test")
        self.project_id = result["data"]["project_id"]

        # 直接操作存储创建一个"旧" item（有3个标签，绕过验证）
        from src.models.item import Item
        import datetime

        # 生成一个有效的 ID 格式
        from datetime import datetime as dt
        timestamp = dt.now().strftime("%Y%m%d")
        old_item_id = f"feat_{timestamp}_1"

        old_item = Item(
            id=old_item_id,
            summary="旧功能",
            content="这是旧的内容",
            tags=["old_tag1", "old_tag2", "old_tag3"],  # 3个标签
            created_at=datetime.datetime.now().isoformat(),
            updated_at=datetime.datetime.now().isoformat(),
            version=1
        )

        project_data = await self.storage.get_project_data(self.project_id)
        project_data.add_item("features", old_item)
        await self.storage.save_project_data(self.project_id, project_data)

        self.old_item_id = old_item_id

    async def test_max_tags_zero_disallows_all_tags(self):
        """测试 max_tags=0 时不允许任何标签."""
        print("测试: max_tags=0 时不允许任何标签...")
        await self.async_setup_method()

        # 修改组的 max_tags 为 0
        await self.groups_service.update_group_config(
            self.project_id, "features", {"max_tags": 0}
        )

        # 尝试添加带标签的 item
        result = await self.project_service.add_item(
            project_id=self.project_id,
            group="features",
            content="测试内容",
            summary="测试摘要",
            status="pending",
            tags=["tag1"]
        )

        assert not result["success"], "max_tags=0 时应该拒绝任何标签"
        assert "标签数量超限" in result["error"], f"错误消息应该包含超限提示: {result['error']}"

        print(f"  ✓ max_tags=0 时不允许任何标签")

    async def test_custom_group_with_max_tags(self):
        """测试自定义组的 max_tags 配置."""
        print("测试: 自定义组的 max_tags 配置...")
        await self.async_setup_method()

        # 创建自定义组并设置 max_tags=3
        result = await self.groups_service.create_custom_group(
            project_id=self.project_id,
            group_name="custom_tasks",
            content_max_bytes=2000,
            summary_max_bytes=100,
            allow_related=False,
            allowed_related_to=[],
            enable_status=True,
            enable_severity=False,
            max_tags=3
        )

        assert result["success"], f"创建自定义组应该成功: {result.get('error')}"

        # 验证自定义组的 max_tags 配置
        config = await self.groups_service.get_group_config(self.project_id, "custom_tasks")
        assert config.max_tags == 3, f"自定义组的 max_tags 应该是3，实际是 {config.max_tags}"

        # 添加3个标签（等于限制）
        result = await self.project_service.add_item(
            project_id=self.project_id,
            group="custom_tasks",
            content="测试内容",
            summary="测试摘要",
            status="pending",
            tags=["tag1", "tag2", "tag3"]
        )
        assert result["success"], "自定义组应该接受3个标签"

        # 尝试添加4个标签（超过限制）
        result = await self.project_service.add_item(
            project_id=self.project_id,
            group="custom_tasks",
            content="测试内容",
            summary="测试摘要",
            status="pending",
            tags=["tag1", "tag2", "tag3", "tag4"]
        )
        assert not result["success"], "自定义组应该拒绝4个标签"
        assert "最大允许 3 个" in result["error"], f"错误消息应该提示最大允许3个: {result['error']}"

        print(f"  ✓ 自定义组的 max_tags 配置生效")
