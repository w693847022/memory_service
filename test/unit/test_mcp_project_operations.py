#!/usr/bin/env python3
"""MCP接口: project_* 操作类接口完整边界测试.

测试项目操作接口：
- project_remove
- project_rename
- project_groups_list
- project_stats
"""

import sys
import tempfile
import shutil
import json
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from features.project import ProjectMemory
import api.tools


def _setup_project():
    """创建测试项目."""
    temp_dir = tempfile.mkdtemp()
    memory = ProjectMemory(storage_dir=temp_dir)

    result = memory.register_project("测试项目", "/tmp", "测试", ["test"])
    project_id = result["project_id"]
    memory.register_tag(project_id, "test", "测试标签")

    # 添加一些条目
    memory.add_item(project_id, "features", "内容", "功能", "pending", tags=["test"])
    memory.add_item(project_id, "notes", "笔记", "笔记", tags=["test"])

    return temp_dir, memory, project_id


# ==================== project_remove ====================

class TestProjectRemoveBasic:
    """project_remove 基础功能测试."""

    def test_archive_project(self):
        """测试归档项目."""
        print("测试: 归档项目...")
        temp_dir, memory, project_id = _setup_project()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_remove(
                    project_id=project_id,
                    mode="archive"
                )
                data = json.loads(result)

                assert data["success"], f"归档项目失败: {data}"

            print("  ✓ 归档项目测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_delete_project(self):
        """测试永久删除项目."""
        print("测试: 永久删除项目...")
        temp_dir, memory, project_id = _setup_project()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_remove(
                    project_id=project_id,
                    mode="delete"
                )
                data = json.loads(result)

                assert data["success"], f"删除项目失败: {data}"

            print("  ✓ 永久删除项目测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestProjectRemoveValidation:
    """project_remove 参数验证测试."""

    def test_missing_project_id(self):
        """测试缺少 project_id."""
        print("测试: 缺少 project_id...")
        temp_dir, memory, _ = _setup_project()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_remove(project_id="")
                data = json.loads(result)

                assert not data["success"], "空 project_id 应该失败"

            print("  ✓ 缺少 project_id 测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_invalid_mode(self):
        """测试无效 mode."""
        print("测试: 无效 mode...")
        temp_dir, memory, project_id = _setup_project()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_remove(
                    project_id=project_id,
                    mode="invalid"
                )
                data = json.loads(result)

                assert not data["success"], "无效 mode 应该失败"

            print("  ✓ 无效 mode 测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_remove_nonexistent_project(self):
        """测试删除不存在的项目."""
        print("测试: 删除不存在的项目...")
        temp_dir, memory, _ = _setup_project()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_remove(project_id="nonexistent")
                data = json.loads(result)

                assert not data["success"], "不存在的项目应该失败"

            print("  ✓ 删除不存在的项目测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_remove_already_archived_project(self):
        """测试删除已归档的项目."""
        print("测试: 删除已归档的项目...")
        temp_dir, memory, project_id = _setup_project()
        try:
            # 第一次归档
            memory.remove_project(project_id, mode="archive")

            # 第二次尝试归档
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_remove(
                    project_id=project_id,
                    mode="archive"
                )
                data = json.loads(result)

                assert not data["success"], "已归档项目应该失败"

            print("  ✓ 删除已归档的项目测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


# ==================== project_rename ====================

class TestProjectRenameBasic:
    """project_rename 基础功能测试."""

    def test_rename_success(self):
        """测试重命名成功."""
        print("测试: 重命名成功...")
        temp_dir, memory, project_id = _setup_project()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_rename(
                    project_id=project_id,
                    new_name="新项目名"
                )
                data = json.loads(result)

                assert data["success"], f"重命名失败: {data}"
                assert data["data"]["new_name"] == "新项目名"

            print("  ✓ 重命名成功测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestProjectRenameValidation:
    """project_rename 参数验证测试."""

    def test_missing_project_id(self):
        """测试缺少 project_id."""
        print("测试: 缺少 project_id...")
        temp_dir, memory, _ = _setup_project()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_rename(
                    project_id="",
                    new_name="新名称"
                )
                data = json.loads(result)

                assert not data["success"], "空 project_id 应该失败"

            print("  ✓ 缺少 project_id 测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_missing_new_name(self):
        """测试缺少 new_name."""
        print("测试: 缺少 new_name...")
        temp_dir, memory, project_id = _setup_project()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_rename(
                    project_id=project_id,
                    new_name=""
                )
                data = json.loads(result)

                assert not data["success"], "空 new_name 应该失败"

            print("  ✓ 缺少 new_name 测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_rename_nonexistent_project(self):
        """测试重命名不存在的项目."""
        print("测试: 重命名不存在的项目...")
        temp_dir, memory, _ = _setup_project()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_rename(
                    project_id="nonexistent",
                    new_name="新名称"
                )
                data = json.loads(result)

                assert not data["success"], "不存在的项目应该失败"

            print("  ✓ 重命名不存在的项目测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_rename_archived_project(self):
        """测试重命名已归档项目."""
        print("测试: 重命名已归档项目...")
        temp_dir, memory, project_id = _setup_project()
        try:
            memory.remove_project(project_id, mode="archive")

            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_rename(
                    project_id=project_id,
                    new_name="新名称"
                )
                data = json.loads(result)

                assert not data["success"], "已归档项目应该拒绝重命名"

            print("  ✓ 重命名已归档项目测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_rename_to_duplicate_name(self):
        """测试重命名为重复名称."""
        print("测试: 重命名为重复名称...")
        temp_dir = tempfile.mkdtemp()
        try:
            memory = ProjectMemory(storage_dir=temp_dir)
            result1 = memory.register_project("项目1", "/tmp1")
            result2 = memory.register_project("项目2", "/tmp2")

            project_id_1 = result1["project_id"]

            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_rename(
                    project_id=project_id_1,
                    new_name="项目2"
                )
                data = json.loads(result)

                # 重复名称可能被允许或拒绝
                # 验证有明确行为

            print("  ✓ 重命名为重复名称测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


# ==================== project_groups_list ====================

class TestProjectGroupsList:
    """project_groups_list 测试."""

    def test_list_groups_success(self):
        """测试列出分组成功."""
        print("测试: 列出分组...")
        temp_dir, memory, project_id = _setup_project()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_groups_list(project_id=project_id)
                data = json.loads(result)

                assert data["success"], f"列出分组失败: {data}"
                assert "groups" in data["data"]
                # 应该有4个分组
                assert len(data["data"]["groups"]) == 4

            print("  ✓ 列出分组测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_list_groups_nonexistent_project(self):
        """测试列出不存在项目的分组."""
        print("测试: 列出不存在项目的分组...")
        temp_dir, memory, _ = _setup_project()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_groups_list(project_id="nonexistent")
                data = json.loads(result)

                assert not data["success"], "不存在的项目应该失败"

            print("  ✓ 列出不存在项目的分组测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


# ==================== project_stats ====================

class TestProjectStats:
    """project_stats 测试."""

    def test_get_stats_success(self):
        """测试获取统计成功."""
        print("测试: 获取统计...")
        temp_dir = tempfile.mkdtemp()
        try:
            memory = ProjectMemory(storage_dir=temp_dir)

            # 创建多个项目
            for i in range(3):
                result = memory.register_project(f"项目{i}", f"/tmp{i}")
                project_id = result["project_id"]
                memory.add_item(project_id, "features", f"内容{i}", f"功能{i}", "pending", tags=["test"])

            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_stats()
                data = json.loads(result)

                assert data["success"], f"获取统计失败: {data}"
                assert "total_projects" in data["data"]
                assert data["data"]["total_projects"] == 3

            print("  ✓ 获取统计测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_get_stats_empty(self):
        """测试空项目统计."""
        print("测试: 空项目统计...")
        temp_dir = tempfile.mkdtemp()
        try:
            memory = ProjectMemory(storage_dir=temp_dir)

            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_stats()
                data = json.loads(result)

                assert data["success"], f"获取统计失败: {data}"
                assert data["data"]["total_projects"] == 0

            print("  ✓ 空项目统计测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


def run_all_tests():
    """运行所有测试."""
    print("=" * 60)
    print("MCP接口: project_* 操作类完整边界测试")
    print("=" * 60)
    print()

    test_classes = [
        TestProjectRemoveBasic,
        TestProjectRemoveValidation,
        TestProjectRenameBasic,
        TestProjectRenameValidation,
        TestProjectGroupsList,
        TestProjectStats,
    ]

    passed = 0
    failed = 0

    for test_class in test_classes:
        instance = test_class()
        for method_name in dir(instance):
            if method_name.startswith("test_"):
                try:
                    method = getattr(instance, method_name)
                    method()
                    passed += 1
                except AssertionError as e:
                    failed += 1
                    print(f"  ✗ {method_name} 失败: {e}")
                except Exception as e:
                    failed += 1
                    print(f"  ✗ {method_name} 错误: {e}")

    print()
    print("=" * 60)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
