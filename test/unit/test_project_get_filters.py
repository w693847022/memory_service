#!/usr/bin/env python3
"""project_get summary_pattern 和时间范围过滤单元测试."""

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


def _setup_project(memory, project_name="test_project"):
    """创建测试项目（注册默认标签）."""
    result = memory.register_project(project_name, "/tmp", "测试项目", ["test"])
    project_id = result["project_id"]
    return project_id


def test_summary_pattern_filter():
    """测试 summary 正则过滤基本功能."""
    print("测试: summary 正则过滤基本功能...")

    test_dir = tempfile.mkdtemp()
    try:
        memory = ProjectMemory(storage_dir=test_dir)
        project_id = _setup_project(memory)

        memory.add_item(project_id=project_id, group="features",
                        summary="API 接口优化", content="c1", status="pending", tags=["test"])
        memory.add_item(project_id=project_id, group="features",
                        summary="数据库重构", content="c2", status="pending", tags=["test"])
        memory.add_item(project_id=project_id, group="features",
                        summary="API 响应格式统一", content="c3", status="completed", tags=["test"])

        with patch.object(api.tools, 'memory', memory):
            # 过滤包含 API 的
            result = api.tools.project_get(
                project_id=project_id, group_name="features",
                summary_pattern="API", view_mode="detail"
            )
            data = json.loads(result)
            assert data["success"], f"请求失败: {data.get('error')}"
            assert data["data"]["filtered_total"] == 2, \
                f"应匹配2条API相关记录，实际 {data['data']['filtered_total']}"

            # 过滤无匹配
            result2 = api.tools.project_get(
                project_id=project_id, group_name="features",
                summary_pattern="不存在的关键词", view_mode="detail"
            )
            data2 = json.loads(result2)
            assert data2["success"], f"请求失败: {data2.get('error')}"
            assert data2["data"]["filtered_total"] == 0, \
                f"无匹配应返回0条，实际 {data2['data']['filtered_total']}"

        print("  ✓ summary 正则过滤基本功能测试通过")
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


def test_summary_pattern_regex():
    """测试 summary 正则特殊模式和无效正则."""
    print("测试: summary 正则特殊模式...")

    test_dir = tempfile.mkdtemp()
    try:
        memory = ProjectMemory(storage_dir=test_dir)
        project_id = _setup_project(memory)

        memory.add_item(project_id=project_id, group="features",
                        summary="测试功能 A", content="c1", status="pending")
        memory.add_item(project_id=project_id, group="features",
                        summary="开发功能 B", content="c2", status="pending")
        memory.add_item(project_id=project_id, group="features",
                        summary="优化功能 C", content="c3", status="pending")

        with patch.object(api.tools, 'memory', memory):
            # 正则 ^测试 只匹配第一条
            result = api.tools.project_get(
                project_id=project_id, group_name="features",
                summary_pattern="^测试", view_mode="detail"
            )
            data = json.loads(result)
            assert data["success"], f"请求失败: {data.get('error')}"
            assert data["data"]["filtered_total"] == 1, \
                f"^测试 应只匹配1条，实际 {data['data']['filtered_total']}"

            # 无效正则返回错误
            result2 = api.tools.project_get(
                project_id=project_id, group_name="features",
                summary_pattern="[invalid"
            )
            data2 = json.loads(result2)
            assert not data2["success"], "无效正则应返回失败"
            assert "无效的summary_pattern正则表达式" in data2.get("error", ""), \
                f"错误信息应包含'无效的summary_pattern正则表达式'，实际: {data2.get('error')}"

        print("  ✓ summary 正则特殊模式测试通过")
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


def test_created_time_range_filter():
    """测试创建时间范围过滤."""
    print("测试: 创建时间范围过滤...")

    test_dir = tempfile.mkdtemp()
    try:
        memory = ProjectMemory(storage_dir=test_dir)
        project_id = _setup_project(memory)

        # 添加条目
        memory.add_item(project_id=project_id, group="features",
                        summary="功能A", content="c1", status="pending")
        memory.add_item(project_id=project_id, group="features",
                        summary="功能B", content="c2", status="pending")

        # 获取数据，修改时间戳，然后保存
        project_data = memory.get_project(project_id)["data"]
        project_data["features"][0]["created_at"] = "2026-03-10T10:00:00.000000"
        project_data["features"][1]["created_at"] = "2026-03-20T15:30:00.000000"
        memory._save_project(project_id, project_data)

        with patch.object(api.tools, 'memory', memory):
            # created_after: 包含边界
            result = api.tools.project_get(
                project_id=project_id, group_name="features",
                created_after="2026-03-10", view_mode="detail"
            )
            data = json.loads(result)
            assert data["success"], f"请求失败: {data.get('error')}"
            assert data["data"]["filtered_total"] == 2, \
                f"created_after=03-10 应匹配2条(包含边界)，实际 {data['data']['filtered_total']}"

            # created_before: 包含边界
            result2 = api.tools.project_get(
                project_id=project_id, group_name="features",
                created_before="2026-03-10", view_mode="detail"
            )
            data2 = json.loads(result2)
            assert data2["success"], f"请求失败: {data2.get('error')}"
            assert data2["data"]["filtered_total"] == 1, \
                f"created_before=03-10 应匹配1条(包含边界)，实际 {data2['data']['filtered_total']}"

            # 范围过滤
            result3 = api.tools.project_get(
                project_id=project_id, group_name="features",
                created_after="2026-03-11", created_before="2026-03-20",
                view_mode="detail"
            )
            data3 = json.loads(result3)
            assert data3["success"], f"请求失败: {data3.get('error')}"
            assert data3["data"]["filtered_total"] == 1, \
                f"范围过滤应匹配1条，实际 {data3['data']['filtered_total']}"

        print("  ✓ 创建时间范围过滤测试通过")
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


def test_updated_time_range_filter():
    """测试修改时间范围过滤."""
    print("测试: 修改时间范围过滤...")

    test_dir = tempfile.mkdtemp()
    try:
        memory = ProjectMemory(storage_dir=test_dir)
        project_id = _setup_project(memory)

        memory.add_item(project_id=project_id, group="features",
                        summary="功能A", content="c1", status="pending")
        memory.add_item(project_id=project_id, group="features",
                        summary="功能B", content="c2", status="pending")
        memory.add_item(project_id=project_id, group="features",
                        summary="功能C", content="c3", status="pending")

        # 获取数据，设置 updated_at，然后保存
        project_data = memory.get_project(project_id)["data"]
        project_data["features"][0]["updated_at"] = "2026-03-15T12:00:00.000000"
        project_data["features"][1]["updated_at"] = "2026-03-20T12:00:00.000000"
        project_data["features"][2]["updated_at"] = None
        memory._save_project(project_id, project_data)

        with patch.object(api.tools, 'memory', memory):
            # updated_after: 无 updated_at 的条目应被排除
            result = api.tools.project_get(
                project_id=project_id, group_name="features",
                updated_after="2026-03-14", view_mode="detail"
            )
            data = json.loads(result)
            assert data["success"], f"请求失败: {data.get('error')}"
            assert data["data"]["filtered_total"] == 2, \
                f"updated_after 应匹配2条(排除无updated_at的)，实际 {data['data']['filtered_total']}"

            # updated_before
            result2 = api.tools.project_get(
                project_id=project_id, group_name="features",
                updated_before="2026-03-15", view_mode="detail"
            )
            data2 = json.loads(result2)
            assert data2["success"], f"请求失败: {data2.get('error')}"
            assert data2["data"]["filtered_total"] == 1, \
                f"updated_before=03-15 应匹配1条，实际 {data2['data']['filtered_total']}"

        print("  ✓ 修改时间范围过滤测试通过")
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


def test_invalid_date_format():
    """测试无效日期格式."""
    print("测试: 无效日期格式...")

    test_dir = tempfile.mkdtemp()
    try:
        memory = ProjectMemory(storage_dir=test_dir)
        project_id = _setup_project(memory)

        with patch.object(api.tools, 'memory', memory):
            result = api.tools.project_get(
                project_id=project_id, group_name="features",
                created_after="2026/03/01"
            )
            data = json.loads(result)
            assert not data["success"], "无效日期格式应返回失败"
            assert "无效的日期格式" in data.get("error", ""), \
                f"错误信息应包含'无效的日期格式'，实际: {data.get('error')}"

            result2 = api.tools.project_get(
                project_id=project_id, group_name="features",
                updated_before="not-a-date"
            )
            data2 = json.loads(result2)
            assert not data2["success"], "无效日期格式应返回失败"

        print("  ✓ 无效日期格式测试通过")
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


def test_combined_filters():
    """测试组合过滤（summary_pattern + 时间范围 + tags）."""
    print("测试: 组合过滤...")

    test_dir = tempfile.mkdtemp()
    try:
        memory = ProjectMemory(storage_dir=test_dir)
        project_id = _setup_project(memory)

        memory.add_item(project_id=project_id, group="features",
                        summary="API 接口优化", content="c1", status="pending", tags=["test"])
        memory.add_item(project_id=project_id, group="features",
                        summary="API 响应格式", content="c2", status="completed", tags=["test", "implementation"])
        memory.add_item(project_id=project_id, group="features",
                        summary="数据库重构", content="c3", status="pending", tags=["test"])

        # 获取数据，设置时间，然后保存
        project_data = memory.get_project(project_id)["data"]
        project_data["features"][0]["created_at"] = "2026-03-10T10:00:00.000000"
        project_data["features"][1]["created_at"] = "2026-03-15T10:00:00.000000"
        project_data["features"][2]["created_at"] = "2026-03-20T10:00:00.000000"
        memory._save_project(project_id, project_data)

        with patch.object(api.tools, 'memory', memory):
            # summary_pattern + tags + 时间范围
            result = api.tools.project_get(
                project_id=project_id, group_name="features",
                summary_pattern="API", tags="test",
                created_after="2026-03-12", created_before="2026-03-16",
                view_mode="detail"
            )
            data = json.loads(result)
            assert data["success"], f"请求失败: {data.get('error')}"
            assert data["data"]["filtered_total"] == 1, \
                f"组合过滤应匹配1条(API+test+03-12~16)，实际 {data['data']['filtered_total']}"

        print("  ✓ 组合过滤测试通过")
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


def test_filters_response_field():
    """测试 filters 响应字段包含新过滤条件."""
    print("测试: filters 响应字段...")

    test_dir = tempfile.mkdtemp()
    try:
        memory = ProjectMemory(storage_dir=test_dir)
        project_id = _setup_project(memory)

        memory.add_item(project_id=project_id, group="features",
                        summary="测试功能", content="c1", status="pending")

        with patch.object(api.tools, 'memory', memory):
            result = api.tools.project_get(
                project_id=project_id, group_name="features",
                summary_pattern="测试", created_after="2026-03-01",
                view_mode="detail"
            )
            data = json.loads(result)
            assert data["success"], f"请求失败: {data.get('error')}"
            assert "filters" in data["data"], "应包含 filters 字段"
            filters = data["data"]["filters"]
            assert filters["summary_pattern"] == "测试", \
                f"filters.summary_pattern 应为 '测试'，实际 {filters['summary_pattern']}"
            assert filters["created_after"] == "2026-03-01", \
                f"filters.created_after 应为 '2026-03-01'，实际 {filters['created_after']}"
            assert filters["created_before"] == "", \
                "未传的参数应为空字符串"
            assert filters["updated_after"] == "", \
                "未传的参数应为空字符串"
            assert filters["updated_before"] == "", \
                "未传的参数应为空字符串"

        print("  ✓ filters 响应字段测试通过")
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


def test_no_filter_backward_compatible():
    """测试不传新参数时行为不变（向后兼容）."""
    print("测试: 向后兼容...")

    test_dir = tempfile.mkdtemp()
    try:
        memory = ProjectMemory(storage_dir=test_dir)
        project_id = _setup_project(memory)

        for i in range(3):
            memory.add_item(project_id=project_id, group="features",
                            summary=f"功能 {i+1}", content=f"c{i+1}", status="pending")

        with patch.object(api.tools, 'memory', memory):
            # 不传新参数，应返回全部
            result = api.tools.project_get(
                project_id=project_id, group_name="features",
                view_mode="detail"
            )
            data = json.loads(result)
            assert data["success"], f"请求失败: {data.get('error')}"
            assert data["data"]["filtered_total"] == 3, \
                f"不传新参数应返回全部3条，实际 {data['data']['filtered_total']}"
            # 不应有 filters 字段（没有过滤条件）
            assert "filters" not in data["data"], "无过滤条件时不应有 filters 字段"

        print("  ✓ 向后兼容测试通过")
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


if __name__ == "__main__":
    test_summary_pattern_filter()
    test_summary_pattern_regex()
    test_created_time_range_filter()
    test_updated_time_range_filter()
    test_invalid_date_format()
    test_combined_filters()
    test_filters_response_field()
    test_no_filter_backward_compatible()
    print("\n全部测试通过!")
