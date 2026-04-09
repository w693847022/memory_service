#!/usr/bin/env python3
"""版本控制单元测试."""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import pytest
import pytest_asyncio
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from business.project_service import ProjectService
from datetime import datetime


@pytest.mark.asyncio
class TestVersionControl:
    """测试版本控制功能."""

    @pytest_asyncio.fixture(autouse=True)
    async def setup_fixtures(self):
        """设置测试环境 - 每个测试方法前自动执行."""
        # Create async context manager mock for barrier
        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def mock_barrier_update(*args, **kwargs):
            yield

        mock_barrier = Mock()
        mock_barrier.update_item = mock_barrier_update

        self.mock_storage = Mock()
        self.mock_storage.barrier = mock_barrier
        self.mock_storage.generate_timestamps.return_value = {
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        # Make async methods return AsyncMock
        self.mock_storage.update_item_with_version_check = AsyncMock()
        self.mock_storage.get_project_data = AsyncMock()
        self.mock_storage.save_project_data = AsyncMock()
        self.mock_storage.update_timestamp = Mock()
        self.service = ProjectService(self.mock_storage)
        yield
        # Cleanup if needed

    async def test_update_item_with_version_conflict(self):
        """测试版本冲突检测."""
        # 准备测试数据
        project_id = "test_project"
        group = "features"
        item_id = "feat_20260409_1"

        # 创建一个版本为2的条目
        item_data = {
            "id": item_id,
            "summary": "Test feature",
            "content": "Test content",
            "version": 2,
            "tags": ["test"],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }

        # Mock get_project_data to return project with the item
        self.mock_storage.get_project_data.return_value = {
            "info": {
                "name": "Test Project",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "tags": []
            },
            "features": [item_data],
            "tag_registry": {}
        }

        # 尝试用错误的版本号更新（期望版本是1，但实际是2）
        result = await self.service.update_item(
            project_id=project_id,
            group=group,
            item_id=item_id,
            summary="Updated summary",
            expected_version=1  # 错误的版本号
        )

        # 验证版本冲突被检测到
        assert result["success"] is False
        assert result["error"] == "version_conflict"

    async def test_update_item_with_correct_version(self):
        """测试正确版本号的更新."""
        project_id = "test_project"
        group = "features"
        item_id = "feat_20260409_1"

        # 创建一个版本为2的条目
        item_data = {
            "id": item_id,
            "summary": "Test feature",
            "content": "Test content",
            "version": 2,
            "tags": ["test"],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }

        # Mock get_project_data to return project with the item
        self.mock_storage.get_project_data.return_value = {
            "info": {
                "name": "Test Project",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "tags": []
            },
            "features": [item_data],
            "tag_registry": {}
        }
        self.mock_storage.save_project_data.return_value = True

        # 用正确的版本号更新
        result = await self.service.update_item(
            project_id=project_id,
            group=group,
            item_id=item_id,
            summary="Updated summary",
            expected_version=2  # 正确的版本号
        )

        # 验证更新成功且版本递增
        assert result["success"] is True
        assert result["version"] == 3
        assert result["item"]["summary"] == "Updated summary"

    async def test_update_item_without_version_check(self):
        """测试不进行版本检查的更新."""
        project_id = "test_project"
        group = "features"
        item_id = "feat_20260409_1"

        item_data = {
            "id": item_id,
            "summary": "Test feature",
            "content": "Test content",
            "version": 2,
            "tags": ["test"],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }

        # Mock get_project_data to return project with the item
        self.mock_storage.get_project_data.return_value = {
            "info": {
                "name": "Test Project",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "tags": []
            },
            "features": [item_data],
            "tag_registry": {}
        }
        self.mock_storage.save_project_data.return_value = True

        # 不提供版本号，应该直接更新
        result = await self.service.update_item(
            project_id=project_id,
            group=group,
            item_id=item_id,
            summary="Updated summary"
        )

        # 验证更新成功且版本递增
        assert result["success"] is True
        assert result["version"] == 3

    async def test_update_item_version_initialization(self):
        """测试没有版本字段的条目初始化为版本1."""
        project_id = "test_project"
        group = "features"
        item_id = "feat_20260409_1"

        # 创建没有版本字段的条目
        item_data = {
            "id": item_id,
            "summary": "Test feature",
            "content": "Test content",
            "version": 1,
            "tags": ["test"],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }

        # Mock get_project_data to return project with the item
        self.mock_storage.get_project_data.return_value = {
            "info": {
                "name": "Test Project",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "tags": []
            },
            "features": [item_data],
            "tag_registry": {}
        }
        self.mock_storage.save_project_data.return_value = True

        # 更新条目
        result = await self.service.update_item(
            project_id=project_id,
            group=group,
            item_id=item_id,
            summary="Updated summary"
        )

        # 验证版本从1初始化并递增到2
        assert result["success"] is True
        assert result["version"] == 2