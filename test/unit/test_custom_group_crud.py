"""自定义组条目 CRUD 全面单元测试.

通过 mock storage 和 item_validator，直接测试 ProjectService 对自定义组的
add_item、update_item、delete_item 以及查询能力。
覆盖边界条件：空自定义组添加第一条目、删除全部条目后重新添加。
"""

import sys
import pytest
import pytest_asyncio
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, AsyncMock

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from business.project_service import ProjectService
from src.models.storage import ProjectData
from src.models.project import ProjectMetadata
from src.models.item import Item
from src.models.group import UnifiedGroupConfig


def _make_project_data(groups: dict | None = None) -> ProjectData:
    """创建测试用 ProjectData."""
    now = datetime.now().isoformat()
    metadata = ProjectMetadata(
        id="550e8400-e29b-41d4-a716-446655440000",
        name="test_project",
        created_at=now,
        updated_at=now,
        tags=[]
    )
    return ProjectData(
        id="550e8400-e29b-41d4-a716-446655440000",
        name="test_project",
        version=1,
        versions={"project": 1, "tag_registry": 1},
        metadata=metadata,
        tag_registry={},
        groups=groups or {}
    )


def _mock_storage_with_project(project_data: ProjectData):
    """创建 mock storage，get_project_data 返回指定数据."""
    storage = Mock()
    storage.get_project_data = AsyncMock(return_value=project_data)
    storage.save_project_data = AsyncMock(return_value=True)
    storage.save_item_content = AsyncMock(return_value=True)
    storage.delete_item_content = Mock(return_value=True)
    storage.generate_item_id = Mock(side_effect=lambda prefix, pid, pdata: f"{prefix}_{datetime.now().strftime('%Y%m%d')}_{len(pdata.get_items(prefix)) + 1}")
    storage.generate_timestamps.return_value = {
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    storage.get_group_configs = AsyncMock(return_value={"groups": {}, "group_settings": {}})
    return storage


def _mock_item_validator_with_custom_group(group_name: str, max_items: int = 0):
    """创建 mock item_validator，包含指定自定义组配置."""
    validator = Mock()
    config = UnifiedGroupConfig(
        enable_status=True,
        status_values=["pending", "in_progress", "completed"],
        enable_severity=False,
        max_tags=2,
        max_items=max_items,
        content_max_bytes=4000,
        summary_max_bytes=90,
        required_fields=["content", "summary", "status"]
    )
    all_configs = {
        "features": UnifiedGroupConfig(
            enable_status=True, status_values=["pending", "in_progress", "completed"],
            enable_severity=False, max_tags=2, content_max_bytes=4000, summary_max_bytes=90
        ),
        group_name: config,
    }
    validator.get_all_configs = AsyncMock(return_value=all_configs)
    return validator


@pytest.mark.asyncio
class TestCustomGroupItemCRUD:
    """测试自定义组条目的完整 CRUD 流程."""

    @pytest_asyncio.fixture
    async def setup(self):
        """每个测试的独立 setup."""
        self.group_name = "my_custom_group"
        self.project_data = _make_project_data()
        self.storage = _mock_storage_with_project(self.project_data)
        self.validator = _mock_item_validator_with_custom_group(self.group_name)
        self.service = ProjectService(self.storage, item_validator=self.validator)
        yield

    async def test_create_item_in_empty_custom_group(self, setup):
        """向空自定义组添加第一条目，验证返回成功且 ID 正确."""
        result = await self.service.add_item(
            project_id="proj-1",
            group=self.group_name,
            content="第一条内容",
            summary="第一条摘要",
            status="pending",
            tags=["test"]
        )
        assert result["success"] is True, f"创建失败: {result.get('error')}"
        assert result["data"]["group"] == self.group_name
        item_id = result["data"]["item_id"]
        assert item_id.startswith(f"{self.group_name}_")
        assert item_id.endswith("_1")

    async def test_create_multiple_items_ids_unique(self, setup):
        """连续创建多条目，ID 唯一递增."""
        ids = []
        for i in range(3):
            result = await self.service.add_item(
                project_id="proj-1",
                group=self.group_name,
                content=f"内容{i}",
                summary=f"摘要{i}",
                status="pending",
                tags=["test"]
            )
            assert result["success"] is True
            ids.append(result["data"]["item_id"])

        assert len(ids) == len(set(ids))
        for i, item_id in enumerate(ids):
            assert item_id.endswith(f"_{i + 1}")

    async def test_read_items_list(self, setup):
        """读取自定义组条目列表，验证所有条目可读."""
        # 先添加 2 条
        for i in range(2):
            await self.service.add_item(
                project_id="proj-1",
                group=self.group_name,
                content=f"内容{i}",
                summary=f"摘要{i}",
                status="pending",
                tags=["test"]
            )

        # 重新加载项目数据（模拟读取）
        items = self.project_data.get_items(self.group_name)
        assert len(items) == 2
        assert items[0].summary == "摘要0"
        assert items[1].summary == "摘要1"

    async def test_update_item_content_and_status(self, setup):
        """更新自定义组条目，验证内容更新成功."""
        # 创建条目
        create_result = await self.service.add_item(
            project_id="proj-1",
            group=self.group_name,
            content="原始内容",
            summary="原始摘要",
            status="pending",
            tags=["test"]
        )
        assert create_result["success"] is True
        item_id = create_result["data"]["item_id"]

        # 更新
        update_result = await self.service.update_item(
            project_id="proj-1",
            group=self.group_name,
            item_id=item_id,
            content="更新后内容",
            summary="更新后摘要",
            status="completed"
        )
        assert update_result["success"] is True, f"更新失败: {update_result.get('error')}"
        assert update_result["data"]["item"]["summary"] == "更新后摘要"
        assert update_result["data"]["item"]["status"] == "completed"
        assert update_result["data"]["version"] == 2

    async def test_delete_item_success(self, setup):
        """删除自定义组条目，验证删除成功."""
        # 创建条目
        create_result = await self.service.add_item(
            project_id="proj-1",
            group=self.group_name,
            content="待删除内容",
            summary="待删除摘要",
            status="pending",
            tags=["test"]
        )
        assert create_result["success"] is True
        item_id = create_result["data"]["item_id"]
        assert len(self.project_data.get_items(self.group_name)) == 1

        # 删除
        delete_result = await self.service.delete_item(
            project_id="proj-1",
            group=self.group_name,
            item_id=item_id
        )
        assert delete_result["success"] is True, f"删除失败: {delete_result.get('error')}"
        assert len(self.project_data.get_items(self.group_name)) == 0

    async def test_delete_all_items_then_recreate(self, setup):
        """边界条件：删除全部条目后重新添加."""
        # 添加 2 条
        for i in range(2):
            await self.service.add_item(
                project_id="proj-1",
                group=self.group_name,
                content=f"内容{i}",
                summary=f"摘要{i}",
                status="pending",
                tags=["test"]
            )
        assert len(self.project_data.get_items(self.group_name)) == 2

        # 全部删除
        items = list(self.project_data.get_items(self.group_name))
        for item in items:
            await self.service.delete_item("proj-1", self.group_name, item.id)
        assert len(self.project_data.get_items(self.group_name)) == 0

        # 重新添加
        result = await self.service.add_item(
            project_id="proj-1",
            group=self.group_name,
            content="新内容",
            summary="新摘要",
            status="pending",
            tags=["test"]
        )
        assert result["success"] is True
        # 重新添加后序号应继续递增（因为 mock 的 generate_item_id 基于当前组长度 +1）
        # 删除后长度为 0，所以新 ID 为 _1
        assert result["data"]["item_id"].endswith("_1")

    async def test_create_item_exceeds_max_items(self, setup):
        """边界条件：超过 max_items 限制应被拒绝."""
        # 使用 max_items=1 的 validator
        validator = _mock_item_validator_with_custom_group(self.group_name, max_items=1)
        service = ProjectService(self.storage, item_validator=validator)

        # 第一条成功
        result1 = await service.add_item(
            project_id="proj-1",
            group=self.group_name,
            content="内容1",
            summary="摘要1",
            status="pending",
            tags=["test"]
        )
        assert result1["success"] is True

        # 第二条应被拒绝
        result2 = await service.add_item(
            project_id="proj-1",
            group=self.group_name,
            content="内容2",
            summary="摘要2",
            status="pending",
            tags=["test"]
        )
        assert result2["success"] is False
        assert "最大条目数量限制" in result2["error"]

    async def test_update_nonexistent_item(self, setup):
        """更新不存在的条目应返回错误."""
        result = await self.service.update_item(
            project_id="proj-1",
            group=self.group_name,
            item_id="nonexistent_20260427_1",
            summary="新摘要"
        )
        assert result["success"] is False
        assert "找不到" in result["error"]

    async def test_delete_nonexistent_item(self, setup):
        """删除不存在的条目应返回错误."""
        result = await self.service.delete_item(
            project_id="proj-1",
            group=self.group_name,
            item_id="nonexistent_20260427_1"
        )
        assert result["success"] is False
        assert "找不到" in result["error"]
