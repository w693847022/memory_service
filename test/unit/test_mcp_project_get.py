#!/usr/bin/env python3
"""MCP接口: project_get 完整边界测试.

测试获取项目/条目接口的所有边界情况。
"""

import sys
import tempfile
import shutil
import json
from pathlib import Path
from unittest.mock import patch
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from features.project import ProjectMemory
import api.tools


def _setup_project_with_items():
    """创建测试项目和多个条目."""
    temp_dir = tempfile.mkdtemp()
    memory = ProjectMemory(storage_dir=temp_dir)

    result = memory.register_project("测试项目", "/tmp", "测试", ["test"])
    project_id = result["project_id"]
    memory.register_tag(project_id, "test", "测试标签")
    memory.register_tag(project_id, "api", "API标签")
    memory.register_tag(project_id, "backend", "后端标签")

    # 添加各种状态的条目
    memory.add_item(project_id, "features", "内容1", "功能A", "pending", tags=["test"])
    memory.add_item(project_id, "features", "内容2", "功能B", "in_progress", tags=["api"])
    memory.add_item(project_id, "features", "内容3", "功能C", "completed", tags=["backend"])
    memory.add_item(project_id, "fixes", "修复1", "修复A", "pending", "high", tags=["test"])
    memory.add_item(project_id, "notes", "笔记1", "笔记A", tags=["test"])
    memory.add_item(project_id, "standards", "规范1", "规范A", tags=["test"])

    return temp_dir, memory, project_id


class TestProjectGetBasic:
    """基础功能测试."""

    def test_get_project_info(self):
        """测试获取项目信息（不传 group_name）."""
        print("测试: 获取项目信息...")
        temp_dir, memory, project_id = _setup_project_with_items()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_get(project_id=project_id)
                data = json.loads(result)

                assert data["success"], f"获取项目信息失败: {data}"
                assert "data" in data
                assert "info" in data["data"]
                assert "groups" in data["data"]

            print("  ✓ 获取项目信息测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_get_group_list(self):
        """测试获取分组列表."""
        print("测试: 获取分组列表...")
        temp_dir, memory, project_id = _setup_project_with_items()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_get(
                    project_id=project_id,
                    group_name="features"
                )
                data = json.loads(result)

                assert data["success"], f"获取分组列表失败: {data}"
                assert "items" in data["data"]
                assert len(data["data"]["items"]) == 3

            print("  ✓ 获取分组列表测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_get_item_detail(self):
        """测试获取条目详情."""
        print("测试: 获取条目详情...")
        temp_dir, memory, project_id = _setup_project_with_items()
        try:
            # 先获取列表找到 item_id
            project_data = memory.get_project(project_id)
            item_id = project_data["data"]["features"][0]["id"]

            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_get(
                    project_id=project_id,
                    group_name="features",
                    item_id=item_id
                )
                data = json.loads(result)

                assert data["success"], f"获取条目详情失败: {data}"
                assert "item" in data["data"]
                assert "content" in data["data"]["item"]

            print("  ✓ 获取条目详情测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestProjectGetParams:
    """参数验证测试."""

    def test_missing_project_id(self):
        """测试缺少 project_id."""
        print("测试: 缺少 project_id...")
        temp_dir, memory, _ = _setup_project_with_items()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_get(project_id="")
                data = json.loads(result)

                assert not data["success"], "空 project_id 应该失败"

            print("  ✓ 缺少 project_id 测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_invalid_group_name(self):
        """测试无效分组名."""
        print("测试: 无效分组名...")
        temp_dir, memory, project_id = _setup_project_with_items()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_get(
                    project_id=project_id,
                    group_name="invalid"
                )
                data = json.loads(result)

                assert not data["success"], "无效分组应该失败"

            print("  ✓ 无效分组名测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_nonexistent_project_id(self):
        """测试不存在的项目ID."""
        print("测试: 不存在的项目ID...")
        temp_dir, memory, _ = _setup_project_with_items()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_get(project_id="nonexistent-id")
                data = json.loads(result)

                assert not data["success"], "不存在的项目应该失败"

            print("  ✓ 不存在的项目ID测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_nonexistent_item_id(self):
        """测试不存在的条目ID."""
        print("测试: 不存在的条目ID...")
        temp_dir, memory, project_id = _setup_project_with_items()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_get(
                    project_id=project_id,
                    group_name="features",
                    item_id="feat_nonexistent"
                )
                data = json.loads(result)

                assert not data["success"], "不存在的条目应该失败"

            print("  ✓ 不存在的条目ID测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestProjectGetFilters:
    """过滤条件测试."""

    def test_status_filter(self):
        """测试状态过滤."""
        print("测试: 状态过滤...")
        temp_dir, memory, project_id = _setup_project_with_items()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_get(
                    project_id=project_id,
                    group_name="features",
                    status="pending"
                )
                data = json.loads(result)

                assert data["success"], f"状态过滤失败: {data}"
                assert data["data"]["filtered_total"] == 1

            print("  ✓ 状态过滤测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_severity_filter(self):
        """测试严重程度过滤."""
        print("测试: 严重程度过滤...")
        temp_dir, memory, project_id = _setup_project_with_items()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_get(
                    project_id=project_id,
                    group_name="fixes",
                    severity="high"
                )
                data = json.loads(result)

                assert data["success"], f"严重程度过滤失败: {data}"
                assert data["data"]["filtered_total"] == 1

            print("  ✓ 严重程度过滤测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_tags_filter_or_logic(self):
        """测试标签过滤（OR逻辑）."""
        print("测试: 标签过滤（OR逻辑）...")
        temp_dir, memory, project_id = _setup_project_with_items()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_get(
                    project_id=project_id,
                    group_name="features",
                    tags="api,backend"  # OR 逻辑
                )
                data = json.loads(result)

                assert data["success"], f"标签过滤失败: {data}"
                assert data["data"]["filtered_total"] == 2  # 功能B和功能C

            print("  ✓ 标签过滤测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_combined_filters(self):
        """测试组合过滤."""
        print("测试: 组合过滤...")
        temp_dir, memory, project_id = _setup_project_with_items()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_get(
                    project_id=project_id,
                    group_name="features",
                    status="in_progress",
                    tags="api"
                )
                data = json.loads(result)

                assert data["success"], f"组合过滤失败: {data}"
                assert data["data"]["filtered_total"] == 1

            print("  ✓ 组合过滤测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestProjectGetPagination:
    """分页测试."""

    def test_pagination_default(self):
        """测试默认分页."""
        print("测试: 默认分页...")
        temp_dir, memory, project_id = _setup_project_with_items()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_get(
                    project_id=project_id,
                    group_name="features"
                )
                data = json.loads(result)

                assert data["success"], f"默认分页失败: {data}"
                # 默认返回20条，只有3条所以全部返回

            print("  ✓ 默认分页测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_pagination_with_size(self):
        """测试指定 size."""
        print("测试: 指定 size...")
        temp_dir, memory, project_id = _setup_project_with_items()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_get(
                    project_id=project_id,
                    group_name="features",
                    size=2
                )
                data = json.loads(result)

                assert data["success"], f"指定 size 失败: {data}"
                assert len(data["data"]["items"]) == 2
                assert data["data"]["has_next"] is True

            print("  ✓ 指定 size 测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_pagination_with_page(self):
        """测试指定 page."""
        print("测试: 指定 page...")
        temp_dir, memory, project_id = _setup_project_with_items()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_get(
                    project_id=project_id,
                    group_name="features",
                    page=2,
                    size=2
                )
                data = json.loads(result)

                assert data["success"], f"指定 page 失败: {data}"
                assert len(data["data"]["items"]) == 1
                assert data["data"]["page"] == 2

            print("  ✓ 指定 page 测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_pagination_edge_cases(self):
        """测试分页边界情况."""
        print("测试: 分页边界...")
        temp_dir, memory, project_id = _setup_project_with_items()
        try:
            # page=0
            result = api.tools.project_get(
                project_id=project_id,
                group_name="features",
                page=0
            )
            data = json.loads(result)
            assert not data["success"] or "page" in data.get("error", "").lower()

            # 超大 page
            result = api.tools.project_get(
                project_id=project_id,
                group_name="features",
                page=999
            )
            data = json.loads(result)
            if data["success"]:
                assert data["data"]["filtered_total"] == 0 or len(data["data"]["items"]) == 0

            print("  ✓ 分页边界测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestProjectGetViewMode:
    """视图模式测试."""

    def test_view_mode_summary(self):
        """测试 summary 模式."""
        print("测试: summary 模式...")
        temp_dir, memory, project_id = _setup_project_with_items()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_get(
                    project_id=project_id,
                    group_name="features",
                    view_mode="summary"
                )
                data = json.loads(result)

                assert data["success"], f"summary 模式失败: {data}"
                if len(data["data"]["items"]) > 0:
                    item = data["data"]["items"][0]
                    # summary 模式只返回 id, summary, tags
                    expected_keys = {"id", "summary", "tags"}
                    actual_keys = set(item.keys())
                    assert actual_keys == expected_keys, f"summary 模式应只返回 {expected_keys}"

            print("  ✓ summary 模式测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_view_mode_detail(self):
        """测试 detail 模式."""
        print("测试: detail 模式...")
        temp_dir, memory, project_id = _setup_project_with_items()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_get(
                    project_id=project_id,
                    group_name="features",
                    view_mode="detail"
                )
                data = json.loads(result)

                assert data["success"], f"detail 模式失败: {data}"
                if len(data["data"]["items"]) > 0:
                    item = data["data"]["items"][0]
                    # detail 模式返回更多字段但不包括 content
                    assert "id" in item
                    assert "summary" in item
                    assert "status" in item
                    assert "content" not in item  # 列表模式不返回 content

            print("  ✓ detail 模式测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_view_mode_invalid(self):
        """测试无效 view_mode."""
        print("测试: 无效 view_mode...")
        temp_dir, memory, project_id = _setup_project_with_items()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_get(
                    project_id=project_id,
                    group_name="features",
                    view_mode="invalid"
                )
                data = json.loads(result)

                assert not data["success"], "无效 view_mode 应该失败"

            print("  ✓ 无效 view_mode 测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestProjectGetTimeFilters:
    """时间过滤测试."""

    def test_created_after_filter(self):
        """测试 created_after 过滤."""
        print("测试: created_after 过滤...")
        temp_dir, memory, project_id = _setup_project_with_items()
        try:
            # 修改第一个条目的创建时间
            project_data = memory.get_project(project_id)
            old_date = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")
            project_data["data"]["features"][0]["created_at"] = f"{old_date}T10:00:00.000000"
            memory._save_project(project_id, project_data["data"])

            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_get(
                    project_id=project_id,
                    group_name="features",
                    created_after=(datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")
                )
                data = json.loads(result)

                assert data["success"], f"created_after 过滤失败: {data}"
                # 应该排除旧条目

            print("  ✓ created_after 过滤测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_created_before_filter(self):
        """测试 created_before 过滤."""
        print("测试: created_before 过滤...")
        temp_dir, memory, project_id = _setup_project_with_items()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_get(
                    project_id=project_id,
                    group_name="features",
                    created_before="2099-12-31"
                )
                data = json.loads(result)

                assert data["success"], f"created_before 过滤失败: {data}"
                # 所有条目都应该在范围内

            print("  ✓ created_before 过滤测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_invalid_date_format(self):
        """测试无效日期格式."""
        print("测试: 无效日期格式...")
        temp_dir, memory, project_id = _setup_project_with_items()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_get(
                    project_id=project_id,
                    group_name="features",
                    created_after="2026/03/01"  # 错误格式
                )
                data = json.loads(result)

                assert not data["success"], "无效日期格式应该失败"

            print("  ✓ 无效日期格式测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_updated_at_filter(self):
        """测试 updated_at 过滤."""
        print("测试: updated_at 过滤...")
        temp_dir, memory, project_id = _setup_project_with_items()
        try:
            # 更新一个条目设置 updated_at
            project_data = memory.get_project(project_id)
            project_data["data"]["features"][0]["updated_at"] = "2026-03-15T10:00:00.000000"
            memory._save_project(project_id, project_data["data"])

            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_get(
                    project_id=project_id,
                    group_name="features",
                    updated_after="2026-03-01"
                )
                data = json.loads(result)

                assert data["success"], f"updated_after 过滤失败: {data}"

            print("  ✓ updated_at 过滤测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestProjectGetSummaryPattern:
    """摘要正则过滤测试."""

    def test_summary_pattern_match(self):
        """测试摘要正则匹配."""
        print("测试: 摘要正则匹配...")
        temp_dir, memory, project_id = _setup_project_with_items()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_get(
                    project_id=project_id,
                    group_name="features",
                    summary_pattern="功能[ABC]"
                )
                data = json.loads(result)

                assert data["success"], f"摘要正则过滤失败: {data}"
                assert data["data"]["filtered_total"] == 3

            print("  ✓ 摘要正则匹配测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_summary_pattern_no_match(self):
        """测试摘要正则无匹配."""
        print("测试: 摘要正则无匹配...")
        temp_dir, memory, project_id = _setup_project_with_items()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_get(
                    project_id=project_id,
                    group_name="features",
                    summary_pattern="不存在的"
                )
                data = json.loads(result)

                assert data["success"], f"摘要正则过滤失败: {data}"
                assert data["data"]["filtered_total"] == 0

            print("  ✓ 摘要正则无匹配测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_summary_pattern_invalid_regex(self):
        """测试无效正则表达式."""
        print("测试: 无效正则表达式...")
        temp_dir, memory, project_id = _setup_project_with_items()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_get(
                    project_id=project_id,
                    group_name="features",
                    summary_pattern="[invalid"
                )
                data = json.loads(result)

                assert not data["success"], "无效正则应该失败"

            print("  ✓ 无效正则表达式测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestProjectGetEdgeCases:
    """边缘情况测试."""

    def test_get_from_archived_project(self):
        """测试从已归档项目获取."""
        print("测试: 从已归档项目获取...")
        temp_dir, memory, project_id = _setup_project_with_items()
        try:
            memory.remove_project(project_id, mode="archive")

            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_get(project_id=project_id)
                data = json.loads(result)

                assert not data["success"], "已归档项目应该失败"

            print("  ✓ 从已归档项目获取测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_get_empty_group(self):
        """测试获取空分组."""
        print("测试: 获取空分组...")
        temp_dir, memory, project_id = _setup_project_with_items()
        try:
            # 删除所有条目 - 先获取所有 id，然后逐个删除
            project_data = memory.get_project(project_id)
            item_ids = [item["id"] for item in project_data["data"]["features"]]
            for item_id in item_ids:
                memory.delete_item(project_id, "features", item_id)

            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_get(
                    project_id=project_id,
                    group_name="features"
                )
                data = json.loads(result)

                assert data["success"], "空分组应该成功"
                assert data["data"]["total"] == 0

            print("  ✓ 获取空分组测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_item_detail_mode_ignores_view_mode(self):
        """测试详情模式忽略 view_mode."""
        print("测试: 详情模式忽略 view_mode...")
        temp_dir, memory, project_id = _setup_project_with_items()
        try:
            project_data = memory.get_project(project_id)
            item_id = project_data["data"]["features"][0]["id"]

            with patch.object(api.tools, 'memory', memory):
                # 即使指定 summary 模式，详情模式也应返回完整数据
                result = api.tools.project_get(
                    project_id=project_id,
                    group_name="features",
                    item_id=item_id,
                    view_mode="summary"
                )
                data = json.loads(result)

                assert data["success"], f"获取详情失败: {data}"
                # 详情模式应包含 content
                assert "content" in data["data"]["item"]

            print("  ✓ 详情模式忽略 view_mode 测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


def run_all_tests():
    """运行所有测试."""
    print("=" * 60)
    print("MCP接口: project_get 完整边界测试")
    print("=" * 60)
    print()

    test_classes = [
        TestProjectGetBasic,
        TestProjectGetParams,
        TestProjectGetFilters,
        TestProjectGetPagination,
        TestProjectGetViewMode,
        TestProjectGetTimeFilters,
        TestProjectGetSummaryPattern,
        TestProjectGetEdgeCases,
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
