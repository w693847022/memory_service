#!/usr/bin/env python3
"""项目归档功能单元测试.

主要验证点：
1. 归档后的项目状态
2. 项目目录是否存在（应该不存在）
3. 压缩文件是否存在
4. 压缩文件里文件数量是否完整
"""

import sys
import pytest
import tarfile
import tempfile
import json
from pathlib import Path
from datetime import datetime

# Add src to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.business.storage import Storage


# ==================== 测试辅助函数 ====================

def count_files_in_directory(directory: Path) -> int:
    """递归计算目录中的文件数量."""
    if not directory.exists():
        return 0
    count = 0
    for item in directory.rglob('*'):
        if item.is_file():
            count += 1
    return count


def count_files_in_tarball(tarball_path: Path) -> int:
    """计算 tar.gz 压缩包中的文件数量."""
    if not tarball_path.exists():
        return 0
    count = 0
    with tarfile.open(str(tarball_path), 'r:gz') as tar:
        count = len(tar.getnames())
    return count


def create_test_project(storage: Storage, project_id: str, project_name: str) -> Path:
    """创建一个测试项目并返回项目目录路径."""
    # 项目目录按项目名称存储
    project_dir = storage.storage_dir / project_name
    project_dir.mkdir(parents=True, exist_ok=True)

    # 创建时间戳
    now = datetime.now().isoformat()

    # 创建项目元数据文件 (_project.json) - 使用正确格式
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
            "summary": "测试项目",
            "tags": ["test"],
            "status": "active",
            "created_at": now,
            "updated_at": now,
            "path": None
        }
    }

    project_json = project_dir / "_project.json"
    with open(project_json, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    # 创建标签索引文件 (_tags.json)
    tags_index = {
        "test": {
            "summary": "测试标签",
            "created_at": now,
            "usage_count": 0,
            "aliases": []
        }
    }

    tags_json = project_dir / "_tags.json"
    with open(tags_json, 'w', encoding='utf-8') as f:
        json.dump(tags_index, f, ensure_ascii=False, indent=2)

    # 创建组配置文件 (_group_configs.json)
    groups_config = {
        "features": {
            "enable_status": True,
            "status_values": ["pending", "in_progress", "completed"],
            "enable_severity": False
        },
        "fixes": {
            "enable_status": True,
            "status_values": ["pending", "in_progress", "completed"],
            "enable_severity": True,
            "severity_values": ["critical", "high", "medium", "low"]
        },
        "notes": {
            "enable_status": False,
            "enable_severity": False
        },
        "standards": {
            "enable_status": False,
            "enable_severity": False
        }
    }

    groups_json = project_dir / "_group_configs.json"
    with open(groups_json, 'w', encoding='utf-8') as f:
        json.dump(groups_config, f, ensure_ascii=False, indent=2)

    # 创建 features 分组索引
    features_dir = project_dir / "features"
    features_dir.mkdir(exist_ok=True)

    features_index = {
        "version": 1,
        "items": []
    }

    features_index_file = features_dir / "_index.json"
    with open(features_index_file, 'w', encoding='utf-8') as f:
        json.dump(features_index, f, ensure_ascii=False, indent=2)

    return project_dir


# ==================== 归档功能测试 ====================

@pytest.mark.asyncio
async def test_archive_project_removes_directory():
    """测试：归档后原项目目录应该被删除."""
    print("\n测试：归档后原项目目录应该被删除...")

    with tempfile.TemporaryDirectory() as tmp:
        storage = Storage(storage_dir=Path(tmp))

        # 创建测试项目
        project_name = "test_remove_dir"
        project_id = storage._generate_id(project_name)
        project_dir = create_test_project(storage, project_id, project_name)

        # 验证项目目录创建成功
        assert project_dir.exists(), "项目目录应该存在"
        print(f"  项目目录创建成功: {project_dir}")

        # 执行归档
        result = await storage.archive_project(project_id)
        assert result["success"], f"归档失败: {result.get('error')}"
        print(f"  归档成功")

        # 验证原项目目录被删除
        assert not project_dir.exists(), "归档后原项目目录应该被删除"
        print(f"  ✓ 原项目目录已删除")


@pytest.mark.asyncio
async def test_archive_creates_tarball():
    """测试：归档后应该创建 tar.gz 压缩文件."""
    print("\n测试：归档后应该创建 tar.gz 压缩文件...")

    with tempfile.TemporaryDirectory() as tmp:
        storage = Storage(storage_dir=Path(tmp))

        # 创建测试项目
        project_name = "test_tarball_creation"
        project_id = storage._generate_id(project_name)
        create_test_project(storage, project_id, project_name)

        # 执行归档
        result = await storage.archive_project(project_id)
        assert result["success"], f"归档失败: {result.get('error')}"

        # 验证压缩文件存在
        archive_path = result.get("archive_path")
        assert archive_path, "归档结果应该包含 archive_path"
        archive_file = Path(archive_path)
        assert archive_file.exists(), f"压缩文件应该存在: {archive_file}"
        assert archive_file.suffixes == ['.tar', '.gz'], "压缩文件应该是 .tar.gz 格式"
        print(f"  ✓ 压缩文件创建成功: {archive_file.name}")


@pytest.mark.asyncio
async def test_archive_creates_metadata():
    """测试：归档后应该创建元数据文件."""
    print("\n测试：归档后应该创建元数据文件...")

    with tempfile.TemporaryDirectory() as tmp:
        storage = Storage(storage_dir=Path(tmp))

        # 创建测试项目
        project_name = "test_metadata_creation"
        project_id = storage._generate_id(project_name)
        create_test_project(storage, project_id, project_name)

        # 执行归档
        result = await storage.archive_project(project_id)
        assert result["success"], f"归档失败: {result.get('error')}"

        # 验证元数据文件存在
        meta_path = result.get("meta_path")
        assert meta_path, "归档结果应该包含 meta_path"
        meta_file = Path(meta_path)
        assert meta_file.exists(), f"元数据文件应该存在: {meta_file}"
        assert meta_file.suffix == '.json', "元数据文件应该是 .json 格式"
        print(f"  ✓ 元数据文件创建成功: {meta_file.name}")

        # 验证元数据内容
        with open(meta_file, 'r', encoding='utf-8') as f:
            meta_data = json.load(f)

        assert meta_data["id"] == project_id, "元数据应该包含正确的项目ID"
        assert meta_data["name"] == project_name, "元数据应该包含正确的项目名称"
        assert "archived_at" in meta_data, "元数据应该包含归档时间"
        assert "archive_file" in meta_data, "元数据应该包含归档文件名"
        assert "created_at" in meta_data, "元数据应该包含创建时间"
        assert "updated_at" in meta_data, "元数据应该包含更新时间"
        assert meta_data["created_at"], "元数据 created_at 不应为空"
        assert meta_data["updated_at"], "元数据 updated_at 不应为空"
        print(f"  ✓ 元数据内容正确")


@pytest.mark.asyncio
async def test_archive_file_count_completeness():
    """测试：压缩文件中的文件数量应该完整."""
    print("\n测试：压缩文件中的文件数量应该完整...")

    with tempfile.TemporaryDirectory() as tmp:
        storage = Storage(storage_dir=Path(tmp))

        # 创建测试项目
        project_name = "test_file_completeness"
        project_id = storage._generate_id(project_name)
        project_dir = create_test_project(storage, project_id, project_name)

        # 统计原始项目目录中的文件数量
        original_file_count = count_files_in_directory(project_dir)
        print(f"  原始项目文件数量: {original_file_count}")

        # 执行归档
        result = await storage.archive_project(project_id)
        assert result["success"], f"归档失败: {result.get('error')}"

        # 验证压缩文件中的文件数量
        archive_file = Path(result.get("archive_path"))
        archive_file_count = count_files_in_tarball(archive_file)
        print(f"  压缩文件中的文件数量: {archive_file_count}")

        # 压缩包中应该包含相同的文件数量（至少要包含原有文件）
        assert archive_file_count >= original_file_count, (
            f"压缩文件中的文件数量({archive_file_count})应该不少于原始数量({original_file_count})"
        )
        print(f"  ✓ 压缩文件内容完整")


@pytest.mark.asyncio
async def test_archive_file_contents():
    """测试：压缩文件中应该包含所有关键文件."""
    print("\n测试：压缩文件中应该包含所有关键文件...")

    with tempfile.TemporaryDirectory() as tmp:
        storage = Storage(storage_dir=Path(tmp))

        # 创建测试项目
        project_name = "test_file_contents"
        project_id = storage._generate_id(project_name)
        project_dir = create_test_project(storage, project_id, project_name)

        # 执行归档
        result = await storage.archive_project(project_id)
        assert result["success"], f"归档失败: {result.get('error')}"

        # 检查压缩文件内容
        archive_file = Path(result.get("archive_path"))
        with tarfile.open(str(archive_file), 'r:gz') as tar:
            archived_files = set(tar.getnames())

        # 验证关键文件存在（归档后使用项目名称作为目录名）
        key_files = [
            f"{project_name}/_project.json",
            f"{project_name}/_group_configs.json",
            f"{project_name}/_tags.json",
            f"{project_name}/features/_index.json"
        ]

        for key_file in key_files:
            assert key_file in archived_files, f"压缩文件中应该包含 {key_file}，实际包含: {archived_files}"
            print(f"  ✓ 包含关键文件: {key_file}")


@pytest.mark.asyncio
async def test_archive_stores_in_correct_location():
    """测试：归档文件应该存储在 .archived 目录下."""
    print("\n测试：归档文件应该存储在 .archived 目录下...")

    with tempfile.TemporaryDirectory() as tmp:
        storage = Storage(storage_dir=Path(tmp))

        # 创建测试项目
        project_name = "test_archive_location"
        project_id = storage._generate_id(project_name)
        create_test_project(storage, project_id, project_name)

        # 执行归档
        result = await storage.archive_project(project_id)
        assert result["success"], f"归档失败: {result.get('error')}"

        # 验证归档文件位置
        archive_file = Path(result.get("archive_path"))
        archive_dir = storage._get_archive_dir()

        assert archive_file.parent == archive_dir, (
            f"归档文件应该在 .archived 目录下: {archive_file.parent} vs {archive_dir}"
        )
        assert archive_dir.name == ".archived", "归档目录名称应该是 .archived"
        print(f"  ✓ 归档文件位置正确: {archive_dir}")


@pytest.mark.asyncio
async def test_archive_with_nonexistent_project():
    """测试：归档不存在的项目应该返回错误."""
    print("\n测试：归档不存在的项目应该返回错误...")

    with tempfile.TemporaryDirectory() as tmp:
        storage = Storage(storage_dir=Path(tmp))

        # 使用不存在的项目ID
        fake_project_id = "00000000-0000-0000-0000-000000000000"
        result = await storage.archive_project(fake_project_id)

        assert result["success"] is False, "归档不存在的项目应该失败"
        assert "error" in result, "应该包含错误信息"
        print(f"  ✓ 正确返回错误: {result['error']}")


@pytest.mark.asyncio
async def test_archive_project_status():
    """测试：归档后检查项目是否被标记为已归档."""
    print("\n测试：归档后检查项目是否被标记为已归档...")

    with tempfile.TemporaryDirectory() as tmp:
        storage = Storage(storage_dir=Path(tmp))

        # 创建测试项目
        project_name = "test_archive_status"
        project_id = storage._generate_id(project_name)
        create_test_project(storage, project_id, project_name)

        # 归档前项目未被标记为已归档
        is_archived_before = await storage.is_archived(project_id)
        assert is_archived_before is False, "归档前项目不应该被标记为已归档"
        print(f"  归档前 is_archived: {is_archived_before}")

        # 执行归档
        result = await storage.archive_project(project_id)
        assert result["success"], f"归档失败: {result.get('error')}"

        # 归档后项目被标记为已归档
        is_archived_after = await storage.is_archived(project_id)
        assert is_archived_after is True, "归档后项目应该被标记为已归档"
        print(f"  归档后 is_archived: {is_archived_after}")
        print(f"  ✓ 项目归档状态正确")


@pytest.mark.asyncio
async def test_multiple_archives_independently():
    """测试：多个项目归档互不影响."""
    print("\n测试：多个项目归档互不影响...")

    with tempfile.TemporaryDirectory() as tmp:
        storage = Storage(storage_dir=Path(tmp))

        # 创建两个测试项目
        project1_id = storage._generate_id("project1")
        project1_dir = create_test_project(storage, project1_id, "project1")

        project2_id = storage._generate_id("project2")
        project2_dir = create_test_project(storage, project2_id, "project2")

        # 归档第一个项目
        result1 = await storage.archive_project(project1_id)
        assert result1["success"], "项目1归档失败"

        # 验证项目1被归档，项目2不受影响
        assert not project1_dir.exists(), "项目1目录应该被删除"
        assert project2_dir.exists(), "项目2目录不应该受影响"
        print(f"  ✓ 项目1已归档，项目2不受影响")

        # 归档第二个项目
        result2 = await storage.archive_project(project2_id)
        assert result2["success"], "项目2归档失败"

        # 验证两个项目都被归档
        assert not project2_dir.exists(), "项目2目录应该被删除"

        # 验证两个归档文件都存在
        archive1 = Path(result1.get("archive_path"))
        archive2 = Path(result2.get("archive_path"))
        assert archive1.exists(), "项目1归档文件应该存在"
        assert archive2.exists(), "项目2归档文件应该存在"
        print(f"  ✓ 两个项目都成功归档")


# ==================== 运行所有测试 ====================

def run_all_tests():
    """运行所有测试."""
    import asyncio

    print("=" * 70)
    print("项目归档功能单元测试")
    print("验证点：项目状态、目录删除、压缩文件、文件完整性")
    print("=" * 70)

    tests = [
        ("归档后原项目目录被删除", test_archive_project_removes_directory),
        ("归档创建 tar.gz 压缩文件", test_archive_creates_tarball),
        ("归档创建元数据文件", test_archive_creates_metadata),
        ("压缩文件数量完整", test_archive_file_count_completeness),
        ("压缩文件内容完整", test_archive_file_contents),
        ("归档文件位置正确", test_archive_stores_in_correct_location),
        ("不存在项目归档失败", test_archive_with_nonexistent_project),
        ("归档状态正确", test_archive_project_status),
        ("多项目归档独立", test_multiple_archives_independently),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        print(f"\n{'=' * 70}")
        print(f"测试: {test_name}")
        print('=' * 70)
        try:
            asyncio.run(test_func())
            passed += 1
            print(f"✓ {test_name} - 通过")
        except AssertionError as e:
            failed += 1
            print(f"✗ {test_name} - 失败: {e}")
        except Exception as e:
            failed += 1
            print(f"✗ {test_name} - 错误: {e}")

    print("\n" + "=" * 70)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("=" * 70)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
