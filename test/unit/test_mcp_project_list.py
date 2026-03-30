#!/usr/bin/env python3
"""MCP接口: project_list 完整边界测试.

测试列出项目接口的所有边界情况。
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


def _create_projects(memory, count=5):
    """创建多个测试项目."""
    project_ids = []
    for i in range(count):
        result = memory.register_project(
            name=f"项目{i}",
            path=f"/path/project{i}",
            summary=f"项目{i}摘要",
            tags=["test"]
        )
        project_ids.append(result["project_id"])
    return project_ids


class TestProjectListBasic:
    """基础功能测试."""

    def test_list_empty(self):
        """测试空项目列表."""
        print("测试: 空项目列表...")
        temp_dir = tempfile.mkdtemp()
        try:
            memory = ProjectMemory(storage_dir=temp_dir)

            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_list()
                data = json.loads(result)

                assert data["success"], f"获取列表失败: {data}"
                assert data["data"]["total"] == 0
                assert data["data"]["projects"] == []

            print("  ✓ 空项目列表测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_list_with_projects(self):
        """测试有项目的列表."""
        print("测试: 有项目的列表...")
        temp_dir = tempfile.mkdtemp()
        try:
            memory = ProjectMemory(storage_dir=temp_dir)
            _create_projects(memory, 3)

            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_list()
                data = json.loads(result)

                assert data["success"], f"获取列表失败: {data}"
                assert data["data"]["total"] == 3

            print("  ✓ 有项目的列表测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestProjectListViewMode:
    """视图模式测试."""

    def test_view_mode_summary(self):
        """测试 summary 模式."""
        print("测试: summary 模式...")
        temp_dir = tempfile.mkdtemp()
        try:
            memory = ProjectMemory(storage_dir=temp_dir)
            _create_projects(memory, 5)

            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_list(view_mode="summary")
                data = json.loads(result)

                assert data["success"], f"summary 模式失败: {data}"
                if len(data["data"]["projects"]) > 0:
                    project = data["data"]["projects"][0]
                    # summary 模式只返回 id, name, summary, tags, status
                    expected_keys = {"id", "name", "summary", "tags", "status"}
                    actual_keys = set(project.keys())
                    assert actual_keys == expected_keys

            print("  ✓ summary 模式测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_view_mode_detail(self):
        """测试 detail 模式."""
        print("测试: detail 模式...")
        temp_dir = tempfile.mkdtemp()
        try:
            memory = ProjectMemory(storage_dir=temp_dir)
            _create_projects(memory, 5)

            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_list(view_mode="detail")
                data = json.loads(result)

                assert data["success"], f"detail 模式失败: {data}"
                if len(data["data"]["projects"]) > 0:
                    project = data["data"]["projects"][0]
                    assert "created_at" in project

            print("  ✓ detail 模式测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_view_mode_invalid(self):
        """测试无效 view_mode."""
        print("测试: 无效 view_mode...")
        temp_dir = tempfile.mkdtemp()
        try:
            memory = ProjectMemory(storage_dir=temp_dir)

            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_list(view_mode="invalid")
                data = json.loads(result)

                assert not data["success"], "无效 view_mode 应该失败"

            print("  ✓ 无效 view_mode 测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestProjectListNamePattern:
    """名称过滤测试."""

    def test_name_pattern_match(self):
        """测试名称匹配."""
        print("测试: 名称匹配...")
        temp_dir = tempfile.mkdtemp()
        try:
            memory = ProjectMemory(storage_dir=temp_dir)
            _create_projects(memory, 10)

            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_list(name_pattern="项目[0-4]")
                data = json.loads(result)

                assert data["success"], f"名称过滤失败: {data}"
                assert data["data"]["filtered_total"] == 5

            print("  ✓ 名称匹配测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_name_pattern_no_match(self):
        """测试名称无匹配."""
        print("测试: 名称无匹配...")
        temp_dir = tempfile.mkdtemp()
        try:
            memory = ProjectMemory(storage_dir=temp_dir)
            _create_projects(memory, 5)

            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_list(name_pattern="不存在")
                data = json.loads(result)

                assert data["success"], f"名称过滤失败: {data}"
                assert data["data"]["filtered_total"] == 0

            print("  ✓ 名称无匹配测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_name_pattern_invalid_regex(self):
        """测试无效正则."""
        print("测试: 无效正则...")
        temp_dir = tempfile.mkdtemp()
        try:
            memory = ProjectMemory(storage_dir=temp_dir)

            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_list(name_pattern="[invalid")
                data = json.loads(result)

                assert not data["success"], "无效正则应该失败"

            print("  ✓ 无效正则测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestProjectListPagination:
    """分页测试."""

    def test_pagination_default(self):
        """测试默认分页."""
        print("测试: 默认分页...")
        temp_dir = tempfile.mkdtemp()
        try:
            memory = ProjectMemory(storage_dir=temp_dir)
            _create_projects(memory, 25)

            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_list(view_mode="summary")
                data = json.loads(result)

                assert data["success"], f"默认分页失败: {data}"
                # summary 模式默认 20
                assert len(data["data"]["projects"]) == 20
                assert data["data"]["has_next"] is True

            print("  ✓ 默认分页测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_pagination_with_page_size(self):
        """测试指定分页参数."""
        print("测试: 指定分页参数...")
        temp_dir = tempfile.mkdtemp()
        try:
            memory = ProjectMemory(storage_dir=temp_dir)
            _create_projects(memory, 15)

            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_list(page=1, size=5, view_mode="detail")
                data = json.loads(result)

                assert data["success"], f"分页失败: {data}"
                assert len(data["data"]["projects"]) == 5
                assert data["data"]["page"] == 1
                assert data["data"]["size"] == 5
                assert data["data"]["total_pages"] == 3
                assert data["data"]["has_next"] is True

            print("  ✓ 指定分页参数测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_pagination_last_page(self):
        """测试最后一页."""
        print("测试: 最后一页...")
        temp_dir = tempfile.mkdtemp()
        try:
            memory = ProjectMemory(storage_dir=temp_dir)
            _create_projects(memory, 12)

            with patch.object(api.tools, 'memory', memory):
                # 12 个项目，每页 5 个，第 3 页是最后一页
                result = api.tools.project_list(page=3, size=5, view_mode="detail")
                data = json.loads(result)

                assert data["success"], f"最后一页失败: {data}"
                assert len(data["data"]["projects"]) == 2
                assert data["data"]["has_next"] is False

            print("  ✓ 最后一页测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_pagination_edge_cases(self):
        """测试分页边界情况."""
        print("测试: 分页边界...")
        temp_dir = tempfile.mkdtemp()
        try:
            memory = ProjectMemory(storage_dir=temp_dir)
            _create_projects(memory, 10)

            with patch.object(api.tools, 'memory', memory):
                # page=0 - 当前实现会被转换为 page=1
                result = api.tools.project_list(page=0)
                data = json.loads(result)
                # page=0 会被视为 page=1，返回成功
                assert data["success"], "page=0 应该被处理为 page=1 并返回成功"
                assert data["data"]["page"] == 1

                # 超大 page - 返回空列表
                result = api.tools.project_list(page=999, size=5)
                data = json.loads(result)
                if data["success"]:
                    assert data["data"]["filtered_total"] == 10
                    assert len(data["data"]["projects"]) == 0

                # size=0 (detail 模式应该返回全部)
                result = api.tools.project_list(size=0, view_mode="detail")
                data = json.loads(result)
                if data["success"]:
                    assert len(data["data"]["projects"]) == 10

            print("  ✓ 分页边界测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestProjectListIncludeArchived:
    """归档项目测试."""

    def test_exclude_archived_default(self):
        """测试默认不包含归档项目."""
        print("测试: 默认不包含归档...")
        temp_dir = tempfile.mkdtemp()
        try:
            memory = ProjectMemory(storage_dir=temp_dir)
            project_ids = _create_projects(memory, 3)

            # 归档一个项目
            memory.remove_project(project_ids[1], mode="archive")

            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_list(include_archived=False)
                data = json.loads(result)

                assert data["success"], f"获取列表失败: {data}"
                assert data["data"]["total"] == 2  # 不包含归档

            print("  ✓ 默认不包含归档测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_include_archived_true(self):
        """测试包含归档项目."""
        print("测试: 包含归档...")
        temp_dir = tempfile.mkdtemp()
        try:
            memory = ProjectMemory(storage_dir=temp_dir)
            project_ids = _create_projects(memory, 3)

            # 归档一个项目
            memory.remove_project(project_ids[1], mode="archive")

            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_list(include_archived=True)
                data = json.loads(result)

                assert data["success"], f"获取列表失败: {data}"
                assert data["data"]["total"] == 3  # 包含归档

                # 验证归档项目标记
                projects = data["data"]["projects"]
                archived = [p for p in projects if p.get("status") == "archived"]
                assert len(archived) == 1

            print("  ✓ 包含归档测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestProjectListEdgeCases:
    """边缘情况测试."""

    def test_list_with_filters_combination(self):
        """测试组合过滤."""
        print("测试: 组合过滤...")
        temp_dir = tempfile.mkdtemp()
        try:
            memory = ProjectMemory(storage_dir=temp_dir)
            _create_projects(memory, 20)

            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_list(
                    name_pattern="项目[0-9]",
                    page=1,
                    size=5,
                    view_mode="summary"
                )
                data = json.loads(result)

                assert data["success"], f"组合过滤失败: {data}"
                assert len(data["data"]["projects"]) == 5
                assert data["data"]["filters"]["name_pattern"] == "项目[0-9]"

            print("  ✓ 组合过滤测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


def run_all_tests():
    """运行所有测试."""
    print("=" * 60)
    print("MCP接口: project_list 完整边界测试")
    print("=" * 60)
    print()

    test_classes = [
        TestProjectListBasic,
        TestProjectListViewMode,
        TestProjectListNamePattern,
        TestProjectListPagination,
        TestProjectListIncludeArchived,
        TestProjectListEdgeCases,
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
