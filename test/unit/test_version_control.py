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

from src.models.storage import ProjectData
from src.models.project import ProjectMetadata
from src.models.item import Item
from src.models.tag import TagInfo


def _make_project_data(items=None, group="features"):
    """创建测试用 ProjectData 模型。"""
    now = datetime.now().isoformat()
    metadata = ProjectMetadata(
        id="550e8400-e29b-41d4-a716-446655440000",
        name="test_project",
        created_at=now,
        updated_at=now,
        tags=[]
    )
    groups = {}
    if items:
        for item_dict in items:
            if "version" not in item_dict and "_v" in item_dict:
                item_dict["version"] = item_dict["_v"]
            item = Item.model_validate(item_dict)
            if group not in groups:
                groups[group] = []
            groups[group].append(item)

    return ProjectData(
        id="550e8400-e29b-41d4-a716-446655440000",
        name="test_project",
        version=1,
        versions={"project": 1, "tag_registry": 1, "features": 1},
        metadata=metadata,
        tag_registry={},
        groups=groups
    )


@pytest.mark.asyncio
class TestVersionControl:
    """测试版本控制功能."""

    @pytest_asyncio.fixture(autouse=True)
    async def setup_fixtures(self):
        """设置测试环境 - 每个测试方法前自动执行."""
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
        self.mock_storage.get_project_data = AsyncMock()
        self.mock_storage.save_project_data = AsyncMock()
        self.service = ProjectService(self.mock_storage)
        yield

    async def test_update_item_with_version_conflict(self):
        """测试版本冲突检测."""
        project_id = "test_project"
        group = "features"
        item_id = "feat_20260409_1"
        now = datetime.now().isoformat()

        item_data = {
            "id": item_id,
            "summary": "Test feature",
            "content": "Test content",
            "version": 2,
            "tags": ["test"],
            "created_at": now,
            "updated_at": now
        }

        self.mock_storage.get_project_data.return_value = _make_project_data([item_data], group)

        result = await self.service.update_item(
            project_id=project_id,
            group=group,
            item_id=item_id,
            summary="Updated summary",
            expected_version=1  # 错误的版本号
        )

        assert result["success"] is False
        assert result["error"] == "version_conflict"

    async def test_update_item_with_correct_version(self):
        """测试正确版本号的更新."""
        project_id = "test_project"
        group = "features"
        item_id = "feat_20260409_1"
        now = datetime.now().isoformat()

        item_data = {
            "id": item_id,
            "summary": "Test feature",
            "content": "Test content",
            "version": 2,
            "tags": ["test"],
            "created_at": now,
            "updated_at": now
        }

        self.mock_storage.get_project_data.return_value = _make_project_data([item_data], group)
        self.mock_storage.save_project_data.return_value = True

        result = await self.service.update_item(
            project_id=project_id,
            group=group,
            item_id=item_id,
            summary="Updated summary",
            expected_version=2  # 正确的版本号
        )

        assert result["success"] is True
        assert result["data"]["version"] == 3
        assert result["data"]["item"]["summary"] == "Updated summary"

    async def test_update_item_without_version_check(self):
        """测试不进行版本检查的更新."""
        project_id = "test_project"
        group = "features"
        item_id = "feat_20260409_1"
        now = datetime.now().isoformat()

        item_data = {
            "id": item_id,
            "summary": "Test feature",
            "content": "Test content",
            "version": 2,
            "tags": ["test"],
            "created_at": now,
            "updated_at": now
        }

        self.mock_storage.get_project_data.return_value = _make_project_data([item_data], group)
        self.mock_storage.save_project_data.return_value = True

        result = await self.service.update_item(
            project_id=project_id,
            group=group,
            item_id=item_id,
            summary="Updated summary"
        )

        assert result["success"] is True
        assert result["data"]["version"] == 3

    async def test_update_item_version_initialization(self):
        """测试没有版本字段的条目初始化为版本1."""
        project_id = "test_project"
        group = "features"
        item_id = "feat_20260409_1"
        now = datetime.now().isoformat()

        item_data = {
            "id": item_id,
            "summary": "Test feature",
            "content": "Test content",
            "version": 1,
            "tags": ["test"],
            "created_at": now,
            "updated_at": now
        }

        self.mock_storage.get_project_data.return_value = _make_project_data([item_data], group)
        self.mock_storage.save_project_data.return_value = True

        result = await self.service.update_item(
            project_id=project_id,
            group=group,
            item_id=item_id,
            summary="Updated summary"
        )

        assert result["success"] is True
        assert result["data"]["version"] == 2
