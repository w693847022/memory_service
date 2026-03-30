#!/usr/bin/env python3
"""MCP接口: project_tags_info 完整边界测试.

测试查询标签信息接口的所有边界情况。
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


def _setup_project_with_tags():
    """创建带标签的测试项目."""
    temp_dir = tempfile.mkdtemp()
    memory = ProjectMemory(storage_dir=temp_dir)

    result = memory.register_project("测试项目", "/tmp", "测试", ["test"])
    project_id = result["project_id"]

    # 注册多个标签
    memory.register_tag(project_id, "api", "API接口标签")
    memory.register_tag(project_id, "backend", "后端标签")
    memory.register_tag(project_id, "frontend", "前端标签")
    memory.register_tag(project_id, "database", "数据库标签")
    memory.register_tag(project_id, "ui", "UI标签")

    # 添加使用标签的条目
    memory.add_item(project_id, "features", "内容1", "API功能", "pending", tags=["api", "backend"])
    memory.add_item(project_id, "features", "内容2", "UI优化", "pending", tags=["frontend", "ui"])
    memory.add_item(project_id, "features", "内容3", "数据库设计", "in_progress", tags=["database"])
    memory.add_item(project_id, "notes", "笔记1", "API笔记", tags=["api"])
    memory.add_item(project_id, "fixes", "修复1", "UI修复", "pending", "high", tags=["ui"])

    return temp_dir, memory, project_id


class TestProjectTagsInfoBasic:
    """基础功能测试."""

    def test_list_all_registered_tags(self):
        """测试列出所有已注册标签."""
        print("测试: 列出所有已注册标签...")
        temp_dir, memory, project_id = _setup_project_with_tags()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_tags_info(project_id=project_id)
                data = json.loads(result)

                assert data["success"], f"列出标签失败: {data}"
                assert "tags" in data["data"]
                # 应该包含注册的标签 + 默认标签
                assert data["data"]["total_tags"] >= 5

            print("  ✓ 列出所有已注册标签测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_list_group_tags(self):
        """测试列出分组标签."""
        print("测试: 列出分组标签...")
        temp_dir, memory, project_id = _setup_project_with_tags()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_tags_info(
                    project_id=project_id,
                    group_name="features"
                )
                data = json.loads(result)

                assert data["success"], f"列出分组标签失败: {data}"
                assert "tags" in data["data"]
                assert data["data"]["group_name"] == "features"

            print("  ✓ 列出分组标签测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_query_specific_tag(self):
        """测试查询特定标签."""
        print("测试: 查询特定标签...")
        temp_dir, memory, project_id = _setup_project_with_tags()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_tags_info(
                    project_id=project_id,
                    group_name="features",
                    tag_name="api"
                )
                data = json.loads(result)

                assert data["success"], f"查询特定标签失败: {data}"
                assert "items" in data["data"]
                assert data["data"]["tag_name"] == "api"

            print("  ✓ 查询特定标签测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestProjectTagsInfoRequiredParams:
    """必填参数验证测试."""

    def test_missing_project_id(self):
        """测试缺少 project_id."""
        print("测试: 缺少 project_id...")
        temp_dir, memory, _ = _setup_project_with_tags()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_tags_info(project_id="")
                data = json.loads(result)

                assert not data["success"], "空 project_id 应该失败"

            print("  ✓ 缺少 project_id 测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_nonexistent_project(self):
        """测试不存在的项目."""
        print("测试: 不存在的项目...")
        temp_dir, memory, _ = _setup_project_with_tags()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_tags_info(project_id="nonexistent")
                data = json.loads(result)

                assert not data["success"], "不存在的项目应该失败"

            print("  ✓ 不存在的项目测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestProjectTagsInfoGroupValidation:
    """分组参数验证测试."""

    def test_invalid_group_name(self):
        """测试无效分组名."""
        print("测试: 无效分组名...")
        temp_dir, memory, project_id = _setup_project_with_tags()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_tags_info(
                    project_id=project_id,
                    group_name="invalid"
                )
                data = json.loads(result)

                assert not data["success"], "无效分组应该失败"

            print("  ✓ 无效分组名测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_all_valid_groups(self):
        """测试所有有效分组."""
        print("测试: 所有有效分组...")
        temp_dir, memory, project_id = _setup_project_with_tags()
        try:
            valid_groups = ["features", "notes", "fixes", "standards"]

            for group in valid_groups:
                with patch.object(api.tools, 'memory', memory):
                    result = api.tools.project_tags_info(
                        project_id=project_id,
                        group_name=group
                    )
                    data = json.loads(result)

                    assert data["success"], f"有效分组 {group} 应该成功"

            print("  ✓ 所有有效分组测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestProjectTagsInfoViewMode:
    """视图模式测试."""

    def test_view_mode_summary(self):
        """测试 summary 模式."""
        print("测试: summary 模式...")
        temp_dir, memory, project_id = _setup_project_with_tags()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_tags_info(
                    project_id=project_id,
                    view_mode="summary"
                )
                data = json.loads(result)

                assert data["success"], f"summary 模式失败: {data}"
                if len(data["data"]["tags"]) > 0:
                    tag = data["data"]["tags"][0]
                    # summary 模式只返回 tag, summary
                    expected_keys = {"tag", "summary"}
                    actual_keys = set(tag.keys())
                    assert actual_keys == expected_keys

            print("  ✓ summary 模式测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_view_mode_detail(self):
        """测试 detail 模式."""
        print("测试: detail 模式...")
        temp_dir, memory, project_id = _setup_project_with_tags()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_tags_info(
                    project_id=project_id,
                    view_mode="detail"
                )
                data = json.loads(result)

                assert data["success"], f"detail 模式失败: {data}"
                if len(data["data"]["tags"]) > 0:
                    tag = data["data"]["tags"][0]
                    assert "tag" in tag
                    assert "summary" in tag
                    assert "usage_count" in tag
                    assert "created_at" in tag

            print("  ✓ detail 模式测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_view_mode_invalid(self):
        """测试无效 view_mode."""
        print("测试: 无效 view_mode...")
        temp_dir, memory, project_id = _setup_project_with_tags()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_tags_info(
                    project_id=project_id,
                    view_mode="invalid"
                )
                data = json.loads(result)

                assert not data["success"], "无效 view_mode 应该失败"

            print("  ✓ 无效 view_mode 测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestProjectTagsInfoPagination:
    """分页测试."""

    def test_pagination_with_size(self):
        """测试指定 size."""
        print("测试: 指定 size...")
        temp_dir, memory, project_id = _setup_project_with_tags()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_tags_info(
                    project_id=project_id,
                    size=2
                )
                data = json.loads(result)

                assert data["success"], f"分页失败: {data}"
                assert len(data["data"]["tags"]) == 2

            print("  ✓ 指定 size 测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_pagination_with_page(self):
        """测试指定 page."""
        print("测试: 指定 page...")
        temp_dir, memory, project_id = _setup_project_with_tags()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_tags_info(
                    project_id=project_id,
                    page=1,
                    size=2
                )
                data = json.loads(result)

                assert data["success"], f"分页失败: {data}"
                assert data["data"]["page"] == 1
                assert data["data"]["has_next"] is not None

            print("  ✓ 指定 page 测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_pagination_edge_cases(self):
        """测试分页边界."""
        print("测试: 分页边界...")
        temp_dir, memory, project_id = _setup_project_with_tags()
        try:
            with patch.object(api.tools, 'memory', memory):
                # page=0 - 会被转为 page=1
                result = api.tools.project_tags_info(
                    project_id=project_id,
                    page=0
                )
                data = json.loads(result)
                # page=0 被视为 page=1
                if data["success"]:
                    assert data["data"]["page"] == 1

                # 超大 page - 返回空列表
                result = api.tools.project_tags_info(
                    project_id=project_id,
                    page=999,
                    size=5
                )
                data = json.loads(result)
                if data["success"]:
                    # 超出范围应该返回空
                    assert len(data["data"]["tags"]) == 0

            print("  ✓ 分页边界测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestProjectTagsInfoFilters:
    """过滤条件测试."""

    def test_summary_pattern_filter(self):
        """测试摘要正则过滤."""
        print("测试: 摘要正则过滤...")
        temp_dir, memory, project_id = _setup_project_with_tags()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_tags_info(
                    project_id=project_id,
                    summary_pattern="API"
                )
                data = json.loads(result)

                assert data["success"], f"摘要过滤失败: {data}"
                # 应该只匹配包含 API 的标签

            print("  ✓ 摘要正则过滤测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_tag_name_pattern_filter(self):
        """测试标签名正则过滤."""
        print("测试: 标签名正则过滤...")
        temp_dir, memory, project_id = _setup_project_with_tags()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_tags_info(
                    project_id=project_id,
                    tag_name_pattern="^(api|ui)$"
                )
                data = json.loads(result)

                assert data["success"], f"标签名过滤失败: {data}"
                assert data["data"]["filtered_total"] == 2

            print("  ✓ 标签名正则过滤测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_combined_filters(self):
        """测试组合过滤."""
        print("测试: 组合过滤...")
        temp_dir, memory, project_id = _setup_project_with_tags()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_tags_info(
                    project_id=project_id,
                    summary_pattern="接口",
                    tag_name_pattern="^a"
                )
                data = json.loads(result)

                assert data["success"], f"组合过滤失败: {data}"
                # 应该同时满足两个条件

            print("  ✓ 组合过滤测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_invalid_regex_pattern(self):
        """测试无效正则表达式."""
        print("测试: 无效正则表达式...")
        temp_dir, memory, project_id = _setup_project_with_tags()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_tags_info(
                    project_id=project_id,
                    summary_pattern="[invalid"
                )
                data = json.loads(result)

                assert not data["success"], "无效正则应该失败"

            print("  ✓ 无效正则表达式测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestProjectTagsInfoUnregistered:
    """未注册标签测试."""

    def test_list_unregistered_tags(self):
        """测试列出未注册标签."""
        print("测试: 列出未注册标签...")
        temp_dir = tempfile.mkdtemp()
        try:
            memory = ProjectMemory(storage_dir=temp_dir)
            result = memory.register_project("测试项目", "/tmp", "测试")
            project_id = result["project_id"]

            # 添加条目但未注册标签
            memory.add_item(project_id, "features", "内容", "测试", "pending", tags=["unregistered"])

            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_tags_info(
                    project_id=project_id,
                    group_name="features",
                    unregistered_only=True
                )
                data = json.loads(result)

                assert data["success"], f"列出未注册标签失败: {data}"
                # 应该包含未注册的标签

            print("  ✓ 列出未注册标签测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_unregistered_with_pagination(self):
        """测试未注册标签不支持分页."""
        print("测试: 未注册标签分页...")
        temp_dir = tempfile.mkdtemp()
        try:
            memory = ProjectMemory(storage_dir=temp_dir)
            result = memory.register_project("测试项目", "/tmp", "测试")
            project_id = result["project_id"]

            memory.add_item(project_id, "features", "内容", "测试", "pending", tags=["unreg1", "unreg2"])

            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_tags_info(
                    project_id=project_id,
                    group_name="features",
                    unregistered_only=True,
                    page=1,
                    size=1
                )
                data = json.loads(result)

                # 未注册标签不支持分页，应该返回所有结果
                assert data["success"], f"未注册标签查询失败: {data}"

            print("  ✓ 未注册标签分页测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestProjectTagsInfoTagQuery:
    """标签查询测试."""

    def test_query_tag_items(self):
        """测试查询标签下的条目."""
        print("测试: 查询标签下的条目...")
        temp_dir, memory, project_id = _setup_project_with_tags()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_tags_info(
                    project_id=project_id,
                    group_name="features",
                    tag_name="api"
                )
                data = json.loads(result)

                assert data["success"], f"查询标签条目失败: {data}"
                assert "items" in data["data"]
                assert len(data["data"]["items"]) == 1

            print("  ✓ 查询标签下的条目测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_query_tag_with_view_mode(self):
        """测试标签查询支持 view_mode."""
        print("测试: 标签查询 view_mode...")
        temp_dir, memory, project_id = _setup_project_with_tags()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_tags_info(
                    project_id=project_id,
                    group_name="features",
                    tag_name="api",
                    view_mode="summary"
                )
                data = json.loads(result)

                assert data["success"], f"标签查询 view_mode 失败: {data}"
                if len(data["data"]["items"]) > 0:
                    item = data["data"]["items"][0]
                    # summary 模式只返回 id, summary, tags
                    expected_keys = {"id", "summary", "tags"}
                    actual_keys = set(item.keys())
                    assert actual_keys == expected_keys

            print("  ✓ 标签查询 view_mode 测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_query_nonexistent_tag(self):
        """测试查询不存在的标签."""
        print("测试: 查询不存在的标签...")
        temp_dir, memory, project_id = _setup_project_with_tags()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_tags_info(
                    project_id=project_id,
                    group_name="features",
                    tag_name="nonexistent"
                )
                data = json.loads(result)

                assert data["success"], f"查询不存在的标签应返回空: {data}"
                assert data["data"]["total"] == 0

            print("  ✓ 查询不存在的标签测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestProjectTagsInfoEdgeCases:
    """边缘情况测试."""

    def test_empty_project(self):
        """测试空项目."""
        print("测试: 空项目...")
        temp_dir = tempfile.mkdtemp()
        try:
            memory = ProjectMemory(storage_dir=temp_dir)
            result = memory.register_project("空项目", "/tmp")
            project_id = result["project_id"]

            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_tags_info(project_id=project_id)
                data = json.loads(result)

                assert data["success"], "空项目应该成功"
                assert data["data"]["total_tags"] >= 0  # 可能有默认标签

            print("  ✓ 空项目测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_empty_group(self):
        """测试空分组."""
        print("测试: 空分组...")
        temp_dir = tempfile.mkdtemp()
        try:
            memory = ProjectMemory(storage_dir=temp_dir)
            result = memory.register_project("测试项目", "/tmp")
            project_id = result["project_id"]

            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_tags_info(
                    project_id=project_id,
                    group_name="features"
                )
                data = json.loads(result)

                assert data["success"], "空分组应该成功"
                assert data["data"]["total_tags"] == 0

            print("  ✓ 空分组测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_archived_project(self):
        """测试已归档项目."""
        print("测试: 已归档项目...")
        temp_dir, memory, project_id = _setup_project_with_tags()
        try:
            memory.remove_project(project_id, mode="archive")

            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_tags_info(project_id=project_id)
                data = json.loads(result)

                assert not data["success"], "已归档项目应该失败"

            print("  ✓ 已归档项目测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_filters_in_response(self):
        """测试响应中包含过滤条件."""
        print("测试: 响应包含过滤条件...")
        temp_dir, memory, project_id = _setup_project_with_tags()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_tags_info(
                    project_id=project_id,
                    summary_pattern="API",
                    tag_name_pattern="api"
                )
                data = json.loads(result)

                assert data["success"], f"获取标签失败: {data}"
                assert "filters" in data["data"]
                assert data["data"]["filters"]["summary_pattern"] == "API"
                assert data["data"]["filters"]["tag_name_pattern"] == "api"

            print("  ✓ 响应包含过滤条件测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


def run_all_tests():
    """运行所有测试."""
    print("=" * 60)
    print("MCP接口: project_tags_info 完整边界测试")
    print("=" * 60)
    print()

    test_classes = [
        TestProjectTagsInfoBasic,
        TestProjectTagsInfoRequiredParams,
        TestProjectTagsInfoGroupValidation,
        TestProjectTagsInfoViewMode,
        TestProjectTagsInfoPagination,
        TestProjectTagsInfoFilters,
        TestProjectTagsInfoUnregistered,
        TestProjectTagsInfoTagQuery,
        TestProjectTagsInfoEdgeCases,
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
