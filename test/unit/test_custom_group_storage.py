#!/usr/bin/env python3
"""自定义组存储持久化测试.

验证自定义组条目的存储和加载机制与内置组一致。
覆盖：存储层 save/load、服务层 CRUD、磁盘文件验证。

关联 fix: fix_20260428_1 (CONTENT_SEPARATE_GROUPS硬编码导致自定义组条目未持久化到磁盘)
"""

import sys
import os
import tempfile
import shutil
import json
import asyncio
from pathlib import Path

import pytest
import pytest_asyncio

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from business.storage import Storage
from business.project_service import ProjectService
from business.groups_service import GroupsService
from business.item_validator import ItemValidator


@pytest.mark.asyncio
class TestCustomGroupStoragePersistence:
    """自定义组存储层持久化测试."""

    @pytest_asyncio.fixture(autouse=True)
    async def setup_teardown(self):
        self.temp_dir = None
        yield
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    async def _setup(self):
        """初始化测试环境."""
        self.temp_dir = tempfile.mkdtemp()
        self.storage = Storage(storage_dir=self.temp_dir)
        self.groups_service = GroupsService(self.storage)
        self.item_validator = ItemValidator(self.storage)
        self.project_service = ProjectService(self.storage, item_validator=self.item_validator)

        result = await self.project_service.register_project("custom_storage_test", "/tmp/test")
        self.project_id = result["data"]["project_id"]

        # 创建自定义组
        await self.groups_service.create_custom_group(
            project_id=self.project_id,
            group_name="my_tasks",
            content_max_bytes=8000,
            summary_max_bytes=90,
            enable_status=True,
            description="测试自定义组",
        )

    async def test_custom_group_directory_created_on_save(self):
        """添加条目后，自定义组目录应在磁盘上创建."""
        await self._setup()

        await self.project_service.add_item(
            project_id=self.project_id,
            group="my_tasks",
            content="测试内容",
            summary="测试条目",
            status="pending",
            tags=["test"],
        )

        project_dir = self.storage._get_project_dir(self.project_id)
        group_dir = project_dir / "my_tasks"
        assert group_dir.exists(), "自定义组目录应被创建"
        assert group_dir.is_dir(), "my_tasks 应该是目录"

    async def test_custom_group_index_json_created(self):
        """自定义组的 _index.json 应正确创建并包含条目元数据."""
        await self._setup()

        result = await self.project_service.add_item(
            project_id=self.project_id,
            group="my_tasks",
            content="索引测试内容",
            summary="索引测试",
            status="pending",
            tags=["test"],
        )
        item_id = result["data"]["item_id"]

        index_path = self.storage._get_group_index_path(self.project_id, "my_tasks")
        assert index_path.exists(), "_index.json 应被创建"

        with open(index_path, "r", encoding="utf-8") as f:
            index_data = json.load(f)

        assert "items" in index_data
        assert len(index_data["items"]) == 1
        assert index_data["items"][0]["id"] == item_id
        assert index_data["items"][0]["summary"] == "索引测试"
        # content 不应在 _index.json 中
        assert "content" not in index_data["items"][0]

    async def test_custom_group_content_md_file_created(self):
        """自定义组条目的 content 应存储到独立 .md 文件."""
        await self._setup()

        content = "这是自定义组条目的详细内容" * 10
        result = await self.project_service.add_item(
            project_id=self.project_id,
            group="my_tasks",
            content=content,
            summary="content测试",
            status="pending",
            tags=["test"],
        )
        item_id = result["data"]["item_id"]

        content_path = self.storage._get_item_content_path(self.project_id, "my_tasks", item_id)
        assert content_path.exists(), ".md 内容文件应被创建"

        saved = content_path.read_text(encoding="utf-8")
        assert saved == content, "content 内容应匹配"

    async def test_custom_group_data_survives_restart(self):
        """重启服务（新建 Storage 实例）后，自定义组数据应可正常加载."""
        await self._setup()

        await self.project_service.add_item(
            project_id=self.project_id,
            group="my_tasks",
            content="持久化内容",
            summary="持久化测试",
            status="pending",
            tags=["test"],
        )

        # 新建 Storage 实例模拟重启
        storage2 = Storage(storage_dir=self.temp_dir)
        project_service2 = ProjectService(storage2)
        result = await project_service2.get_project(self.project_id, include_items=True)

        assert result["success"], "重启后应能查询项目"
        items = result["data"].get("my_tasks", [])
        assert len(items) == 1, f"自定义组应有1个条目，实际 {len(items)}"
        assert items[0]["summary"] == "持久化测试"

    async def test_custom_group_item_detail_with_content(self):
        """通过服务层获取自定义组条目详情应包含 content."""
        await self._setup()

        result = await self.project_service.add_item(
            project_id=self.project_id,
            group="my_tasks",
            content="详情内容测试",
            summary="详情测试",
            status="pending",
            tags=["test"],
        )
        item_id = result["data"]["item_id"]

        # 清除缓存，强制从磁盘加载
        self.storage._cache.l2_cache.clear()
        self.storage._cache.l1_cache.clear()

        # 通过 storage 获取 content
        loaded_content = await self.storage.get_item_content(self.project_id, "my_tasks", item_id)
        assert loaded_content == "详情内容测试", "从磁盘加载的 content 应匹配"

    async def test_custom_group_update_saves_new_content(self):
        """更新自定义组条目的 content 应更新 .md 文件."""
        await self._setup()

        result = await self.project_service.add_item(
            project_id=self.project_id,
            group="my_tasks",
            content="原始内容",
            summary="更新测试",
            status="pending",
            tags=["test"],
        )
        item_id = result["data"]["item_id"]

        await self.project_service.update_item(
            project_id=self.project_id,
            group="my_tasks",
            item_id=item_id,
            content="更新后内容",
        )

        content_path = self.storage._get_item_content_path(self.project_id, "my_tasks", item_id)
        assert content_path.exists()
        saved = content_path.read_text(encoding="utf-8")
        assert saved == "更新后内容", "更新后 content 应匹配"

    async def test_custom_group_delete_removes_content_file(self):
        """删除自定义组条目应同时删除 .md 文件."""
        await self._setup()

        result = await self.project_service.add_item(
            project_id=self.project_id,
            group="my_tasks",
            content="待删除内容",
            summary="删除测试",
            status="pending",
            tags=["test"],
        )
        item_id = result["data"]["item_id"]

        content_path = self.storage._get_item_content_path(self.project_id, "my_tasks", item_id)
        assert content_path.exists(), "删除前 content 文件应存在"

        await self.project_service.delete_item(self.project_id, "my_tasks", item_id)

        assert not content_path.exists(), "删除后 content 文件应不存在"

    async def test_multiple_custom_groups_independent(self):
        """多个自定义组应独立存储，互不干扰."""
        await self._setup()

        # 创建第二个自定义组
        await self.groups_service.create_custom_group(
            project_id=self.project_id,
            group_name="my_notes",
            description="第二个自定义组",
        )

        # 分别添加条目
        r1 = await self.project_service.add_item(
            project_id=self.project_id,
            group="my_tasks",
            content="tasks内容",
            summary="tasks条目",
            status="pending",
            tags=["test"],
        )
        r2 = await self.project_service.add_item(
            project_id=self.project_id,
            group="my_notes",
            content="notes内容",
            summary="notes条目",
            tags=["test"],
        )

        # 验证两个组各自有独立的目录和文件
        project_dir = self.storage._get_project_dir(self.project_id)
        assert (project_dir / "my_tasks" / "_index.json").exists()
        assert (project_dir / "my_notes" / "_index.json").exists()

        id1 = r1["data"]["item_id"]
        id2 = r2["data"]["item_id"]
        assert (project_dir / "my_tasks" / f"{id1}.md").exists()
        assert (project_dir / "my_notes" / f"{id2}.md").exists()

        # 新实例加载验证
        storage2 = Storage(storage_dir=self.temp_dir)
        ps2 = ProjectService(storage2)
        result = await ps2.get_project(self.project_id, include_items=True)

        assert len(result["data"]["my_tasks"]) == 1
        assert len(result["data"]["my_notes"]) == 1

    async def test_builtin_groups_still_work(self):
        """修复后内置组的存储机制不应受影响."""
        await self._setup()

        result = await self.project_service.add_item(
            project_id=self.project_id,
            group="features",
            content="内置组测试内容",
            summary="内置组测试",
            status="pending",
            tags=["test"],
        )
        item_id = result["data"]["item_id"]

        # 验证 features 组的 .md 文件存在
        content_path = self.storage._get_item_content_path(self.project_id, "features", item_id)
        assert content_path.exists()
        saved = content_path.read_text(encoding="utf-8")
        assert saved == "内置组测试内容"

        # 验证重启后加载正常
        storage2 = Storage(storage_dir=self.temp_dir)
        ps2 = ProjectService(storage2)
        result = await ps2.get_project(self.project_id, include_items=True)
        assert len(result["data"]["features"]) == 1
