#!/usr/bin/env python3
"""project_tags_info 分页、过滤、view_mode 单元测试."""

import sys
import tempfile
import shutil
import json
from pathlib import Path
from unittest.mock import patch

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from features.project import ProjectMemory

# 预先导入 api.tools 以避免模块缓存问题
import api.tools


def _setup_project(memory, project_name="test_tags_project"):
    """创建测试项目并注册标签."""
    result = memory.register_project(project_name, "/tmp", "测试标签项目")
    project_id = result["project_id"]

    # 注册多个标签
    memory.register_tag(project_id, "api", "API接口相关标签")
    memory.register_tag(project_id, "enhancement", "功能增强标签")
    memory.register_tag(project_id, "bugfix", "Bug修复标签")
    memory.register_tag(project_id, "database", "数据库相关标签")
    memory.register_tag(project_id, "ui", "用户界面标签")

    # 添加一些条目使用这些标签
    memory.add_item(project_id=project_id, group="features",
                    summary="API优化", content="c1", status="pending", tags=["api", "enhancement"])
    memory.add_item(project_id=project_id, group="features",
                    summary="UI重构", content="c2", status="pending", tags=["ui"])
    memory.add_item(project_id=project_id, group="fixes",
                    summary="Bug修复", content="c3", status="pending", tags=["bugfix", "api"])

    return project_id


def test_tags_info_all_registered_pagination():
    """测试所有注册标签分页."""
    print("测试: 所有注册标签分页...")

    test_dir = tempfile.mkdtemp()
    try:
        memory = ProjectMemory(storage_dir=test_dir)
        project_id = _setup_project(memory)

        with patch.object(api.tools, 'memory', memory):
            # 第一页，每页2条
            result = api.tools.project_tags_info(
                project_id=project_id, page=1, size=2, view_mode="detail"
            )
            data = json.loads(result)
            assert data["success"], f"请求失败: {data.get('error')}"
            assert data["data"]["filtered_total"] == 12, \
                f"过滤总数应为12(8默认+4新增去重)，实际 {data['data']['filtered_total']}"
            assert len(data["data"]["tags"]) == 2, \
                f"当前页应为2条，实际 {len(data['data']['tags'])}"
            assert data["data"]["page"] == 1
            assert data["data"]["has_next"] is True
            assert data["data"]["has_prev"] is False

            # 第二页
            result2 = api.tools.project_tags_info(
                project_id=project_id, page=2, size=2, view_mode="detail"
            )
            data2 = json.loads(result2)
            assert data2["success"]
            assert len(data2["data"]["tags"]) == 2, \
                f"第二页应为2条，实际 {len(data2['data']['tags'])}"
            assert data2["data"]["has_prev"] is True

        print("  ✓ 所有注册标签分页测试通过")
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


def test_tags_info_group_tags_pagination():
    """测试分组标签列表分页."""
    print("测试: 分组标签列表分页...")

    test_dir = tempfile.mkdtemp()
    try:
        memory = ProjectMemory(storage_dir=test_dir)
        project_id = _setup_project(memory)

        with patch.object(api.tools, 'memory', memory):
            # features 分组有 api, enhancement, ui 三个在用标签（通过 add_item 添加的）
            result = api.tools.project_tags_info(
                project_id=project_id, group_name="features",
                page=1, size=2, view_mode="detail"
            )
            data = json.loads(result)
            assert data["success"], f"请求失败: {data.get('error')}"
            assert data["data"]["filtered_total"] == 3, \
                f"过滤总数应为3(api,enhancement,ui)，实际 {data['data']['filtered_total']}"
            assert len(data["data"]["tags"]) == 2
            assert data["data"]["group_name"] == "features"

        print("  ✓ 分组标签列表分页测试通过")
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


def test_tags_info_view_mode_summary():
    """测试 summary 模式只返回 tag 和 summary 字段."""
    print("测试: summary 模式字段过滤...")

    test_dir = tempfile.mkdtemp()
    try:
        memory = ProjectMemory(storage_dir=test_dir)
        project_id = _setup_project(memory)

        with patch.object(api.tools, 'memory', memory):
            result = api.tools.project_tags_info(
                project_id=project_id, view_mode="summary"
            )
            data = json.loads(result)
            assert data["success"], f"请求失败: {data.get('error')}"

            for tag_item in data["data"]["tags"]:
                keys = set(tag_item.keys())
                assert keys == {"tag", "summary"}, \
                    f"summary 模式应只包含 tag 和 summary，实际 {keys}"

        print("  ✓ summary 模式字段过滤测试通过")
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


def test_tags_info_view_mode_detail():
    """测试 detail 模式返回所有字段."""
    print("测试: detail 模式返回全部字段...")

    test_dir = tempfile.mkdtemp()
    try:
        memory = ProjectMemory(storage_dir=test_dir)
        project_id = _setup_project(memory)

        with patch.object(api.tools, 'memory', memory):
            result = api.tools.project_tags_info(
                project_id=project_id, view_mode="detail"
            )
            data = json.loads(result)
            assert data["success"], f"请求失败: {data.get('error')}"

            for tag_item in data["data"]["tags"]:
                assert "tag" in tag_item
                assert "summary" in tag_item
                assert "usage_count" in tag_item
                assert "created_at" in tag_item

        print("  ✓ detail 模式返回全部字段测试通过")
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


def test_tags_info_summary_pattern_filter():
    """测试 summary 正则过滤."""
    print("测试: summary 正则过滤...")

    test_dir = tempfile.mkdtemp()
    try:
        memory = ProjectMemory(storage_dir=test_dir)
        project_id = _setup_project(memory)

        with patch.object(api.tools, 'memory', memory):
            result = api.tools.project_tags_info(
                project_id=project_id,
                summary_pattern="API", view_mode="detail"
            )
            data = json.loads(result)
            assert data["success"], f"请求失败: {data.get('error')}"
            assert data["data"]["filtered_total"] == 1, \
                f"应匹配1条API相关标签，实际 {data['data']['filtered_total']}"
            assert data["data"]["tags"][0]["tag"] == "api"

            # 无匹配
            result2 = api.tools.project_tags_info(
                project_id=project_id,
                summary_pattern="不存在的摘要", view_mode="detail"
            )
            data2 = json.loads(result2)
            assert data2["success"]
            assert data2["data"]["filtered_total"] == 0

        print("  ✓ summary 正则过滤测试通过")
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


def test_tags_info_tag_name_pattern_filter():
    """测试标签名正则过滤."""
    print("测试: 标签名正则过滤...")

    test_dir = tempfile.mkdtemp()
    try:
        memory = ProjectMemory(storage_dir=test_dir)
        project_id = _setup_project(memory)

        with patch.object(api.tools, 'memory', memory):
            result = api.tools.project_tags_info(
                project_id=project_id,
                tag_name_pattern="^(api|ui)$", view_mode="detail"
            )
            data = json.loads(result)
            assert data["success"], f"请求失败: {data.get('error')}"
            assert data["data"]["filtered_total"] == 2, \
                f"应匹配2条标签(api+ui)，实际 {data['data']['filtered_total']}"

            tag_names = [t["tag"] for t in data["data"]["tags"]]
            assert "api" in tag_names
            assert "ui" in tag_names

        print("  ✓ 标签名正则过滤测试通过")
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


def test_tags_info_combined_filters():
    """测试组合过滤(summary_pattern + tag_name_pattern)."""
    print("测试: 组合过滤...")

    test_dir = tempfile.mkdtemp()
    try:
        memory = ProjectMemory(storage_dir=test_dir)
        project_id = _setup_project(memory)

        with patch.object(api.tools, 'memory', memory):
            # 标签名含 a 或 e，且摘要含"标签"
            result = api.tools.project_tags_info(
                project_id=project_id,
                tag_name_pattern="^(api|enhancement)$",
                summary_pattern="标签",
                view_mode="detail"
            )
            data = json.loads(result)
            assert data["success"]
            assert data["data"]["filtered_total"] == 2

            # 标签名和摘要矛盾条件（无匹配）
            result2 = api.tools.project_tags_info(
                project_id=project_id,
                tag_name_pattern="^ui$",
                summary_pattern="API",
                view_mode="detail"
            )
            data2 = json.loads(result2)
            assert data2["success"]
            assert data2["data"]["filtered_total"] == 0

        print("  ✓ 组合过滤测试通过")
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


def test_tags_info_invalid_regex():
    """测试无效正则报错."""
    print("测试: 无效正则报错...")

    test_dir = tempfile.mkdtemp()
    try:
        memory = ProjectMemory(storage_dir=test_dir)
        project_id = _setup_project(memory)

        with patch.object(api.tools, 'memory', memory):
            result = api.tools.project_tags_info(
                project_id=project_id,
                summary_pattern="[invalid"
            )
            data = json.loads(result)
            assert not data["success"]
            assert "正则表达式" in data["error"]

            result2 = api.tools.project_tags_info(
                project_id=project_id,
                tag_name_pattern="[invalid"
            )
            data2 = json.loads(result2)
            assert not data2["success"]
            assert "正则表达式" in data2["error"]

        print("  ✓ 无效正则报错测试通过")
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


def test_tags_info_invalid_view_mode():
    """测试无效 view_mode 报错."""
    print("测试: 无效 view_mode 报错...")

    test_dir = tempfile.mkdtemp()
    try:
        memory = ProjectMemory(storage_dir=test_dir)
        project_id = _setup_project(memory)

        with patch.object(api.tools, 'memory', memory):
            result = api.tools.project_tags_info(
                project_id=project_id,
                view_mode="invalid"
            )
            data = json.loads(result)
            assert not data["success"]
            assert "view_mode" in data["error"]

        print("  ✓ 无效 view_mode 报错测试通过")
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


def test_tags_info_tag_name_query_unchanged():
    """测试按标签名查询不受分页/过滤影响."""
    print("测试: 按标签名查询保持不变...")

    test_dir = tempfile.mkdtemp()
    try:
        memory = ProjectMemory(storage_dir=test_dir)
        project_id = _setup_project(memory)

        with patch.object(api.tools, 'memory', memory):
            # tag_name 模式应忽略分页/过滤参数
            result = api.tools.project_tags_info(
                project_id=project_id, group_name="features",
                tag_name="api", page=1, size=1,
                summary_pattern="不存在的", view_mode="detail"
            )
            data = json.loads(result)
            assert data["success"], f"请求失败: {data.get('error')}"
            assert data["data"]["total"] == 1
            assert data["data"]["tag_name"] == "api"
            # 不应有分页信息
            assert "page" not in data["data"]

        print("  ✓ 按标签名查询保持不变测试通过")
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


def test_tags_info_unregistered_unchanged():
    """测试未注册标签查询不受分页/过滤影响."""
    print("测试: 未注册标签查询保持不变...")

    test_dir = tempfile.mkdtemp()
    try:
        memory = ProjectMemory(storage_dir=test_dir)
        project_id = _setup_project(memory)

        with patch.object(api.tools, 'memory', memory):
            # 未注册标签查询应忽略分页/过滤参数，直接返回底层结果
            result = api.tools.project_tags_info(
                project_id=project_id, group_name="features",
                unregistered_only=True, page=1, size=1,
                summary_pattern="不存在的"
            )
            data = json.loads(result)
            assert data["success"], f"请求失败: {data.get('error')}"
            # 不应有分页信息
            assert "page" not in data["data"]
            assert "filtered_total" not in data["data"]

        print("  ✓ 未注册标签查询保持不变测试通过")
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


def test_tags_info_default_size():
    """测试默认 size 行为（summary=20，detail=全部）."""
    print("测试: 默认 size 行为...")

    test_dir = tempfile.mkdtemp()
    try:
        memory = ProjectMemory(storage_dir=test_dir)
        project_id = _setup_project(memory)

        with patch.object(api.tools, 'memory', memory):
            # summary 模式默认 size=20，12个标签全部返回（< 20所以只有1页）
            result = api.tools.project_tags_info(
                project_id=project_id, view_mode="summary"
            )
            data = json.loads(result)
            assert data["success"]
            assert len(data["data"]["tags"]) == 12, \
                f"应返回12个标签(8默认+4新增去重)，实际 {len(data['data']['tags'])}"
            assert data["data"]["has_next"] is False
            assert data["data"]["page"] == 1

            # detail 模式默认 size=0（全部），不应有分页信息
            result2 = api.tools.project_tags_info(
                project_id=project_id, view_mode="detail"
            )
            data2 = json.loads(result2)
            assert data2["success"]
            assert len(data2["data"]["tags"]) == 12, \
                f"detail模式应返回全部12个标签，实际 {len(data2['data']['tags'])}"
            assert "page" not in data2["data"]

        print("  ✓ 默认 size 行为测试通过")
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


def test_tags_info_filters_in_response():
    """测试过滤条件出现在响应中."""
    print("测试: 过滤条件出现在响应中...")

    test_dir = tempfile.mkdtemp()
    try:
        memory = ProjectMemory(storage_dir=test_dir)
        project_id = _setup_project(memory)

        with patch.object(api.tools, 'memory', memory):
            result = api.tools.project_tags_info(
                project_id=project_id,
                summary_pattern="API",
                tag_name_pattern="api"
            )
            data = json.loads(result)
            assert data["success"]
            assert "filters" in data["data"]
            assert data["data"]["filters"]["summary_pattern"] == "API"
            assert data["data"]["filters"]["tag_name_pattern"] == "api"

            # 无过滤条件时不出现 filters
            result2 = api.tools.project_tags_info(project_id=project_id)
            data2 = json.loads(result2)
            assert data2["success"]
            assert "filters" not in data2["data"]

        print("  ✓ 过滤条件出现在响应中测试通过")
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


def run_all_tests():
    """运行所有单元测试."""
    print("=" * 60)
    print("project_tags_info 分页/过滤/view_mode 单元测试")
    print("=" * 60)
    print()

    tests = [
        test_tags_info_all_registered_pagination,
        test_tags_info_group_tags_pagination,
        test_tags_info_view_mode_summary,
        test_tags_info_view_mode_detail,
        test_tags_info_summary_pattern_filter,
        test_tags_info_tag_name_pattern_filter,
        test_tags_info_combined_filters,
        test_tags_info_invalid_regex,
        test_tags_info_invalid_view_mode,
        test_tags_info_tag_name_query_unchanged,
        test_tags_info_unregistered_unchanged,
        test_tags_info_default_size,
        test_tags_info_filters_in_response,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
            print()
        except AssertionError as e:
            failed += 1
            print(f"  ✗ 测试失败: {e}")
            print()
        except Exception as e:
            failed += 1
            print(f"  ✗ 测试错误: {e}")
            import traceback
            traceback.print_exc()
            print()

    print("=" * 60)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
