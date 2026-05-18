"""自定义组条目 ID 唯一性单元测试.

验证修复后的 _generate_item_id 对自定义组能正确生成唯一递增 ID，
且内置组行为不受影响。
"""

import sys
import pytest
import pytest_asyncio
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from business.core.storage_base import ProjectStorage
from src.models.storage import ProjectData
from src.models.project import ProjectMetadata
from src.models.item import Item


def _make_project_data_with_custom_group(group_name: str, items: list | None = None) -> ProjectData:
    """创建包含自定义组的 ProjectData."""
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
        groups[group_name] = [Item.model_validate(i) for i in items]
    return ProjectData(
        id="550e8400-e29b-41d4-a716-446655440000",
        name="test_project",
        version=1,
        versions={"project": 1, "tag_registry": 1, group_name: 1},
        metadata=metadata,
        tag_registry={},
        groups=groups
    )


class TestCustomGroupItemIdGeneration:
    """测试自定义组条目 ID 生成唯一性."""

    def test_generate_item_id_for_custom_group_increments(self):
        """连续向自定义组添加条目，ID 应唯一递增."""
        storage = ProjectStorage(storage_dir="/tmp/test_storage")
        group_name = "my_custom_group"

        # 空组第一条
        project_data = _make_project_data_with_custom_group(group_name)
        id1 = storage._generate_item_id(group_name, "proj-1", project_data)
        assert id1.startswith(f"{group_name}_{datetime.now().strftime('%Y%m%d')}_1")

        # 添加第一条到组中
        project_data.add_item(group_name, Item(
            id=id1, summary="s1", content="c1",
            tags=["test"], created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(), version=1
        ))

        # 第二条应递增
        id2 = storage._generate_item_id(group_name, "proj-1", project_data)
        assert id2.endswith("_2")
        assert id2 != id1

        project_data.add_item(group_name, Item(
            id=id2, summary="s2", content="c2",
            tags=["test"], created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(), version=1
        ))

        # 第三条应递增
        id3 = storage._generate_item_id(group_name, "proj-1", project_data)
        assert id3.endswith("_3")
        assert id3 != id2

    def test_generate_item_id_different_dates(self):
        """不同日期的条目 ID 格式正确且日期部分匹配."""
        storage = ProjectStorage(storage_dir="/tmp/test_storage")
        group_name = "frontend_graph"

        project_data = _make_project_data_with_custom_group(group_name)
        item_id = storage._generate_item_id(group_name, "proj-1", project_data)

        parts = item_id.split("_")
        assert len(parts) >= 3
        # prefix 为 group_name，若含下划线则 split 后多段；最后两段为日期和序号
        date_part = parts[-2]
        seq_part = parts[-1]
        assert len(date_part) == 8
        assert date_part.isdigit()
        seq = int(seq_part)
        assert seq >= 1
        # 前缀部分重组后应等于 group_name
        prefix = "_".join(parts[:-2])
        assert prefix == group_name

    def test_builtin_groups_not_affected(self):
        """内置组 ID 生成不受影响，仍使用短前缀."""
        storage = ProjectStorage(storage_dir="/tmp/test_storage")

        groups_and_prefixes = {
            "features": "feat",
            "fixes": "fix",
            "notes": "note",
            "standards": "std",
        }

        for group_name, expected_prefix in groups_and_prefixes.items():
            project_data = _make_project_data_with_custom_group(group_name)
            item_id = storage._generate_item_id(expected_prefix, "proj-1", project_data)
            assert item_id.startswith(f"{expected_prefix}_{datetime.now().strftime('%Y%m%d')}_")

    def test_generate_item_id_with_underscore_group_name(self):
        """带下划线的自定义组名作为完整前缀."""
        storage = ProjectStorage(storage_dir="/tmp/test_storage")
        group_name = "my_group_name"

        project_data = _make_project_data_with_custom_group(group_name)
        item_id = storage._generate_item_id(group_name, "proj-1", project_data)

        assert item_id.startswith(f"{group_name}_")
        parts = item_id.split("_")
        # 前缀应保留原始 group_name（含下划线），不应被替换
        assert parts[0] == "my"
        assert parts[1] == "group"
        assert parts[2] == "name"

    def test_generate_item_id_respects_existing_max_counter(self):
        """生成 ID 时应基于现有条目最大序号递增."""
        storage = ProjectStorage(storage_dir="/tmp/test_storage")
        group_name = "tasks"
        today = datetime.now().strftime("%Y%m%d")

        # 预置一个已有条目，序号为 5
        existing_items = [
            {
                "id": f"{group_name}_{today}_5",
                "summary": "existing",
                "content": "content",
                "tags": ["test"],
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "version": 1
            }
        ]
        project_data = _make_project_data_with_custom_group(group_name, existing_items)

        new_id = storage._generate_item_id(group_name, "proj-1", project_data)
        assert new_id == f"{group_name}_{today}_6"

    def test_generate_item_id_for_uppercase_group_name(self):
        """大写自定义组名(如 Requirement)用 lower 前缀生成 ID 应正确递增."""
        storage = ProjectStorage(storage_dir="/tmp/test_storage")
        group_name = "Requirement"          # 大写开头的组名
        today = datetime.now().strftime("%Y%m%d")

        # 预置一个已有条目，使用 lower 前缀
        existing_items = [
            {
                "id": f"requirement_{today}_1",
                "summary": "existing item",
                "content": "",
                "tags": ["test"],
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "version": 1
            }
        ]
        project_data = _make_project_data_with_custom_group(group_name, existing_items)

        # 使用小写前缀调用 _generate_item_id，模拟 project_service.py 的行为
        new_id = storage._generate_item_id("requirement", "proj-1", project_data)
        assert new_id == f"requirement_{today}_2"
        assert not new_id.endswith("_1")  # 不应重复使用 _1

    def test_generate_item_id_for_empty_custom_group(self):
        """空自定义组添加第一条目时 ID 序号为 1."""
        storage = ProjectStorage(storage_dir="/tmp/test_storage")
        group_name = "empty_group"

        project_data = _make_project_data_with_custom_group(group_name)
        assert len(project_data.get_items(group_name)) == 0

        item_id = storage._generate_item_id(group_name, "proj-1", project_data)
        assert item_id.endswith("_1")
