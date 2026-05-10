#!/usr/bin/env python3
"""项目信息修改功能单元测试.

主要验证点：
1. 修改 summary/tags/path 成功
2. 部分更新（只修改部分字段）
3. 归档项目不能修改
4. 不存在的项目返回错误
5. 未指定字段时返回错误
"""

import sys
import pytest
import json
from pathlib import Path
from datetime import datetime

# Add src to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.business.storage import Storage
from src.business.project_service import ProjectService


def create_test_project(storage: Storage, project_id: str, project_name: str) -> Path:
    """创建一个测试项目并返回项目目录路径."""
    project_dir = storage.storage_dir / project_name
    project_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now().isoformat()

    metadata = {
        "id": project_id,
        "name": project_name,
        "_version": 1,
        "_versions": {
            "project": 1,
            "tag_registry": 1,
            "features": 1,
            "fixes": 1,
            "notes": 1,
            "standards": 1
        },
        "info": {
            "id": project_id,
            "name": project_name,
            "summary": "原始描述",
            "tags": ["original-tag"],
            "status": "active",
            "created_at": now,
            "updated_at": now,
            "path": "/original/path"
        }
    }

    project_json = project_dir / "_project.json"
    with open(project_json, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    # 创建标签索引文件
    tags_index = {
        "original-tag": {
            "summary": "原始标签",
            "created_at": now,
            "usage_count": 0,
            "aliases": []
        }
    }
    tags_json = project_dir / "_tags.json"
    with open(tags_json, 'w', encoding='utf-8') as f:
        json.dump(tags_index, f, ensure_ascii=False, indent=2)

    # 创建组配置文件
    groups_config = {
        "features": {"enable_status": True, "status_values": ["pending", "in_progress", "completed"], "enable_severity": False},
        "fixes": {"enable_status": True, "status_values": ["pending", "in_progress", "completed"], "enable_severity": True, "severity_values": ["critical", "high", "medium", "low"]},
        "notes": {"enable_status": False, "enable_severity": False},
        "standards": {"enable_status": False, "enable_severity": False}
    }
    groups_json = project_dir / "_group_configs.json"
    with open(groups_json, 'w', encoding='utf-8') as f:
        json.dump(groups_config, f, ensure_ascii=False, indent=2)

    # 创建分组目录和索引
    for group_name in ["features", "fixes", "notes", "standards"]:
        group_dir = project_dir / group_name
        group_dir.mkdir(exist_ok=True)
        index_file = group_dir / "_index.json"
        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump({"version": 1, "items": []}, f, ensure_ascii=False, indent=2)

    return project_dir


# ==================== 测试用例 ====================

@pytest.mark.asyncio
async def test_update_summary_success():
    """测试：成功修改项目摘要."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        storage = Storage(storage_dir=Path(tmp))
        service = ProjectService(storage)

        project_name = "test_update_summary"
        project_id = storage._generate_id(project_name)
        create_test_project(storage, project_id, project_name)

        result = await service.project_update_info(project_id, summary="新描述")
        assert result["success"], f"修改失败: {result.get('error')}"
        assert "summary" in result["data"]["updated_fields"]
        assert result["data"]["info"]["summary"] == "新描述"


@pytest.mark.asyncio
async def test_update_tags_success():
    """测试：成功修改项目标签."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        storage = Storage(storage_dir=Path(tmp))
        service = ProjectService(storage)

        project_name = "test_update_tags"
        project_id = storage._generate_id(project_name)
        create_test_project(storage, project_id, project_name)

        result = await service.project_update_info(project_id, tags=["tag1", "tag2"])
        assert result["success"], f"修改失败: {result.get('error')}"
        assert "tags" in result["data"]["updated_fields"]
        assert result["data"]["info"]["tags"] == ["tag1", "tag2"]


@pytest.mark.asyncio
async def test_update_path_success():
    """测试：成功修改项目路径."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        storage = Storage(storage_dir=Path(tmp))
        service = ProjectService(storage)

        project_name = "test_update_path"
        project_id = storage._generate_id(project_name)
        create_test_project(storage, project_id, project_name)

        result = await service.project_update_info(project_id, path="/new/path")
        assert result["success"], f"修改失败: {result.get('error')}"
        assert "path" in result["data"]["updated_fields"]
        assert result["data"]["info"]["path"] == "/new/path"


@pytest.mark.asyncio
async def test_update_multiple_fields():
    """测试：同时修改多个字段."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        storage = Storage(storage_dir=Path(tmp))
        service = ProjectService(storage)

        project_name = "test_update_multi"
        project_id = storage._generate_id(project_name)
        create_test_project(storage, project_id, project_name)

        result = await service.project_update_info(
            project_id,
            summary="新描述",
            tags=["new-tag"],
            path="/new/path"
        )
        assert result["success"], f"修改失败: {result.get('error')}"
        assert set(result["data"]["updated_fields"]) == {"summary", "tags", "path"}
        assert result["data"]["info"]["summary"] == "新描述"
        assert result["data"]["info"]["tags"] == ["new-tag"]
        assert result["data"]["info"]["path"] == "/new/path"


@pytest.mark.asyncio
async def test_update_no_fields_returns_error():
    """测试：未指定修改字段时返回错误."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        storage = Storage(storage_dir=Path(tmp))
        service = ProjectService(storage)

        project_name = "test_no_fields"
        project_id = storage._generate_id(project_name)
        create_test_project(storage, project_id, project_name)

        result = await service.project_update_info(project_id)
        assert result["success"] is False
        assert "未指定" in result["error"]


@pytest.mark.asyncio
async def test_update_archived_project_returns_error():
    """测试：归档项目不能修改信息."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        storage = Storage(storage_dir=Path(tmp))
        service = ProjectService(storage)

        project_name = "test_archived"
        project_id = storage._generate_id(project_name)
        create_test_project(storage, project_id, project_name)

        # 先归档
        archive_result = await storage.archive_project(project_id)
        assert archive_result["success"]

        # 尝试修改
        result = await service.project_update_info(project_id, summary="新描述")
        assert result["success"] is False
        assert "归档" in result["error"]


@pytest.mark.asyncio
async def test_update_nonexistent_project_returns_error():
    """测试：修改不存在的项目返回错误."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        storage = Storage(storage_dir=Path(tmp))
        service = ProjectService(storage)

        fake_id = "00000000-0000-0000-0000-000000000000"
        result = await service.project_update_info(fake_id, summary="新描述")
        assert result["success"] is False


@pytest.mark.asyncio
async def test_update_preserves_unmodified_fields():
    """测试：部分更新不影响的字段保持原值."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        storage = Storage(storage_dir=Path(tmp))
        service = ProjectService(storage)

        project_name = "test_partial"
        project_id = storage._generate_id(project_name)
        create_test_project(storage, project_id, project_name)

        # 只修改 summary，tags 和 path 应保持不变
        result = await service.project_update_info(project_id, summary="新描述")
        assert result["success"]
        assert result["data"]["info"]["tags"] == ["original-tag"]
        assert result["data"]["info"]["path"] == "/original/path"


@pytest.mark.asyncio
async def test_update_version_incremented():
    """测试：修改后版本号递增."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        storage = Storage(storage_dir=Path(tmp))
        service = ProjectService(storage)

        project_name = "test_version"
        project_id = storage._generate_id(project_name)
        create_test_project(storage, project_id, project_name)

        # 获取原始版本
        project_data = await storage.get_project_data(project_id)
        original_version = project_data.versions.get("project", 1)

        # 修改
        result = await service.project_update_info(project_id, summary="新描述")
        assert result["success"]

        # 验证版本号递增
        updated_data = await storage.get_project_data(project_id)
        assert updated_data.versions.get("project") == original_version + 1


# ==================== 运行所有测试 ====================

def run_all_tests():
    """运行所有测试."""
    import asyncio

    print("=" * 70)
    print("项目信息修改功能单元测试")
    print("=" * 70)

    tests = [
        ("修改摘要成功", test_update_summary_success),
        ("修改标签成功", test_update_tags_success),
        ("修改路径成功", test_update_path_success),
        ("同时修改多个字段", test_update_multiple_fields),
        ("未指定字段返回错误", test_update_no_fields_returns_error),
        ("归档项目不能修改", test_update_archived_project_returns_error),
        ("不存在项目返回错误", test_update_nonexistent_project_returns_error),
        ("部分更新保持原值", test_update_preserves_unmodified_fields),
        ("修改后版本号递增", test_update_version_incremented),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        print(f"\n测试: {test_name}")
        try:
            asyncio.run(test_func())
            passed += 1
            print(f"  ✓ 通过")
        except AssertionError as e:
            failed += 1
            print(f"  ✗ 失败: {e}")
        except Exception as e:
            failed += 1
            print(f"  ✗ 错误: {e}")

    print(f"\n{'=' * 70}")
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("=" * 70)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
