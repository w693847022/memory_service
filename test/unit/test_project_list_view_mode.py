#!/usr/bin/env python3
"""project_list view_mode 参数单元测试."""

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


def _create_projects(memory, count: int, prefix: str = "project"):
    """创建多个测试项目."""
    project_ids = []
    for i in range(count):
        name = f"{prefix}_{i+1:03d}"
        result = memory.register_project(name, "", f"{name} 摘要", ["test", f"tag{i % 3}"])
        project_ids.append(result["project_id"])
    return project_ids


def test_view_mode_default():
    """测试 view_mode 默认值为 summary，返回 4 个字段."""
    print("测试: view_mode 默认值...")

    test_dir = tempfile.mkdtemp()
    try:
        memory = ProjectMemory(storage_dir=test_dir)
        _create_projects(memory, 5)

        with patch.object(api.tools, 'memory', memory):
            result = api.tools.project_list()
            data = json.loads(result)

            assert data["success"], f"请求失败: {data.get('error')}"
            assert data["data"]["filtered_total"] == 5

            projects = data["data"]["projects"]
            assert len(projects) > 0, "应该返回至少一条数据"
            project = projects[0]

            expected_keys = {"id", "name", "summary", "tags"}
            actual_keys = set(project.keys())
            assert actual_keys == expected_keys, f"summary 模式应只返回 {expected_keys}，实际返回 {actual_keys}"
            assert "created_at" not in project, "summary 模式不应包含 created_at 字段"

        print("  ✓ view_mode 默认值测试通过")
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


def test_view_mode_summary():
    """测试 view_mode=summary 显式传参."""
    print("测试: view_mode=summary 返回字段...")

    test_dir = tempfile.mkdtemp()
    try:
        memory = ProjectMemory(storage_dir=test_dir)
        _create_projects(memory, 3)

        with patch.object(api.tools, 'memory', memory):
            result = api.tools.project_list(view_mode="summary")
            data = json.loads(result)

            assert data["success"], f"请求失败: {data.get('error')}"

            project = data["data"]["projects"][0]
            expected_keys = {"id", "name", "summary", "tags"}
            actual_keys = set(project.keys())
            assert actual_keys == expected_keys, f"summary 模式应只返回 {expected_keys}，实际返回 {actual_keys}"

        print("  ✓ view_mode=summary 返回字段测试通过")
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


def test_view_mode_detail():
    """测试 view_mode=detail 返回全部字段."""
    print("测试: view_mode=detail 返回字段...")

    test_dir = tempfile.mkdtemp()
    try:
        memory = ProjectMemory(storage_dir=test_dir)
        _create_projects(memory, 2)

        with patch.object(api.tools, 'memory', memory):
            result = api.tools.project_list(view_mode="detail")
            data = json.loads(result)

            assert data["success"], f"请求失败: {data.get('error')}"

            project = data["data"]["projects"][0]
            assert "id" in project, "detail 模式应包含 id 字段"
            assert "name" in project, "detail 模式应包含 name 字段"
            assert "summary" in project, "detail 模式应包含 summary 字段"
            assert "tags" in project, "detail 模式应包含 tags 字段"
            assert "created_at" in project, "detail 模式应包含 created_at 字段"

        print("  ✓ view_mode=detail 返回字段测试通过")
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


def test_view_mode_invalid():
    """测试无效的 view_mode 值."""
    print("测试: 无效的 view_mode 值...")

    test_dir = tempfile.mkdtemp()
    try:
        memory = ProjectMemory(storage_dir=test_dir)

        with patch.object(api.tools, 'memory', memory):
            result = api.tools.project_list(view_mode="invalid")
            data = json.loads(result)

            assert not data["success"], "无效的 view_mode 应该返回失败"
            assert "无效的 view_mode" in data.get("error", ""), f"错误信息应包含'无效的 view_mode'，实际: {data.get('error')}"

        print("  ✓ 无效的 view_mode 值测试通过")
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


def test_name_pattern_filter():
    """测试 name_pattern 正则过滤."""
    print("测试: name_pattern 正则过滤...")

    test_dir = tempfile.mkdtemp()
    try:
        memory = ProjectMemory(storage_dir=test_dir)
        _create_projects(memory, 3, prefix="test_api")
        _create_projects(memory, 2, prefix="prod_web")

        with patch.object(api.tools, 'memory', memory):
            # 精确前缀匹配
            result = api.tools.project_list(name_pattern="^test_api", view_mode="detail")
            data = json.loads(result)

            assert data["success"], f"请求失败: {data.get('error')}"
            assert data["data"]["filtered_total"] == 3, f"应匹配 3 个 test_api 项目，实际 {data['data']['filtered_total']}"
            assert data["data"]["total"] == 5, f"总数应为 5，实际 {data['data']['total']}"

            # 包含匹配
            result2 = api.tools.project_list(name_pattern="web")
            data2 = json.loads(result2)

            assert data2["success"], f"请求失败: {data2.get('error')}"
            assert data2["data"]["filtered_total"] == 2, f"应匹配 2 个 web 项目，实际 {data2['data']['filtered_total']}"

        print("  ✓ name_pattern 正则过滤测试通过")
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


def test_name_pattern_no_match():
    """测试 name_pattern 无匹配."""
    print("测试: name_pattern 无匹配...")

    test_dir = tempfile.mkdtemp()
    try:
        memory = ProjectMemory(storage_dir=test_dir)
        _create_projects(memory, 3, prefix="alpha")

        with patch.object(api.tools, 'memory', memory):
            result = api.tools.project_list(name_pattern="^zzz")
            data = json.loads(result)

            assert data["success"], f"请求失败: {data.get('error')}"
            assert data["data"]["filtered_total"] == 0
            assert data["data"]["projects"] == []

        print("  ✓ name_pattern 无匹配测试通过")
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


def test_name_pattern_invalid_regex():
    """测试无效正则表达式."""
    print("测试: 无效正则表达式...")

    test_dir = tempfile.mkdtemp()
    try:
        memory = ProjectMemory(storage_dir=test_dir)

        with patch.object(api.tools, 'memory', memory):
            result = api.tools.project_list(name_pattern="[invalid")
            data = json.loads(result)

            assert not data["success"], "无效正则应该返回失败"
            assert "无效的正则表达式" in data.get("error", ""), f"错误信息应包含'无效的正则表达式'，实际: {data.get('error')}"

        print("  ✓ 无效正则表达式测试通过")
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


def test_pagination():
    """测试分页参数."""
    print("测试: 分页参数...")

    test_dir = tempfile.mkdtemp()
    try:
        memory = ProjectMemory(storage_dir=test_dir)
        _create_projects(memory, 15, prefix="page_test")

        with patch.object(api.tools, 'memory', memory):
            # 第 1 页，每页 5 条
            result = api.tools.project_list(page=1, size=5, view_mode="detail")
            data = json.loads(result)

            assert data["success"], f"请求失败: {data.get('error')}"
            assert len(data["data"]["projects"]) == 5, f"第1页应返回5条，实际 {len(data['data']['projects'])} 条"
            assert data["data"]["page"] == 1
            assert data["data"]["size"] == 5
            assert data["data"]["total_pages"] == 3
            assert data["data"]["has_next"] is True
            assert data["data"]["has_prev"] is False

            # 第 2 页
            result2 = api.tools.project_list(page=2, size=5, view_mode="detail")
            data2 = json.loads(result2)

            assert data2["success"], f"请求失败: {data2.get('error')}"
            assert len(data2["data"]["projects"]) == 5
            assert data2["data"]["has_next"] is True
            assert data2["data"]["has_prev"] is True

            # 第 3 页（最后一页）
            result3 = api.tools.project_list(page=3, size=5, view_mode="detail")
            data3 = json.loads(result3)

            assert data3["success"], f"请求失败: {data3.get('error')}"
            assert len(data3["data"]["projects"]) == 5
            assert data3["data"]["has_next"] is False

        print("  ✓ 分页参数测试通过")
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


def test_size_default_with_view_mode():
    """测试 size 根据 view_mode 自动设置默认值."""
    print("测试: size 根据 view_mode 自动设置...")

    test_dir = tempfile.mkdtemp()
    try:
        memory = ProjectMemory(storage_dir=test_dir)
        _create_projects(memory, 25, prefix="size_test")

        with patch.object(api.tools, 'memory', memory):
            # summary 模式默认 size=20
            result1 = api.tools.project_list(view_mode="summary")
            data1 = json.loads(result1)
            assert data1["success"], f"请求失败: {data1.get('error')}"
            assert len(data1["data"]["projects"]) == 20, f"summary 模式默认应返回20条，实际返回 {len(data1['data']['projects'])} 条"
            assert data1["data"]["filtered_total"] == 25

            # detail 模式默认 size=0（全部）
            result2 = api.tools.project_list(view_mode="detail")
            data2 = json.loads(result2)
            assert data2["success"], f"请求失败: {data2.get('error')}"
            assert len(data2["data"]["projects"]) == 25, f"detail 模式默认应返回全部25条，实际返回 {len(data2['data']['projects'])} 条"

        print("  ✓ size 根据 view_mode 自动设置测试通过")
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


def test_size_override():
    """测试显式传入 size 覆盖 view_mode 默认值."""
    print("测试: size 覆盖 view_mode 默认值...")

    test_dir = tempfile.mkdtemp()
    try:
        memory = ProjectMemory(storage_dir=test_dir)
        _create_projects(memory, 15, prefix="override_test")

        with patch.object(api.tools, 'memory', memory):
            # summary 模式，显式指定 size=10
            result = api.tools.project_list(view_mode="summary", size=10)
            data = json.loads(result)
            assert data["success"], f"请求失败: {data.get('error')}"
            assert len(data["data"]["projects"]) == 10, f"显式指定 size=10 应返回10条，实际返回 {len(data['data']['projects'])} 条"

        print("  ✓ size 覆盖默认值测试通过")
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


def test_combined_params():
    """测试组合参数: view_mode + name_pattern + 分页."""
    print("测试: 组合参数...")

    test_dir = tempfile.mkdtemp()
    try:
        memory = ProjectMemory(storage_dir=test_dir)
        _create_projects(memory, 10, prefix="api_server")
        _create_projects(memory, 5, prefix="web_client")

        with patch.object(api.tools, 'memory', memory):
            # 精简模式 + 名称过滤 + 分页
            result = api.tools.project_list(
                view_mode="summary",
                name_pattern="^api",
                page=1,
                size=5
            )
            data = json.loads(result)

            assert data["success"], f"请求失败: {data.get('error')}"
            assert data["data"]["total"] == 15, f"总数应为 15，实际 {data['data']['total']}"
            assert data["data"]["filtered_total"] == 10, f"过滤后应为 10，实际 {data['data']['filtered_total']}"
            assert len(data["data"]["projects"]) == 5, f"第1页应返回5条，实际 {len(data['data']['projects'])} 条"
            assert data["data"]["filters"]["name_pattern"] == "^api"

            # 验证 summary 模式字段
            project = data["data"]["projects"][0]
            assert "id" in project
            assert "name" in project
            assert "summary" in project
            assert "tags" in project
            assert "created_at" not in project

        print("  ✓ 组合参数测试通过")
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


if __name__ == "__main__":
    test_view_mode_default()
    test_view_mode_summary()
    test_view_mode_detail()
    test_view_mode_invalid()
    test_name_pattern_filter()
    test_name_pattern_no_match()
    test_name_pattern_invalid_regex()
    test_pagination()
    test_size_default_with_view_mode()
    test_size_override()
    test_combined_params()
    print("\n✅ 所有测试通过!")
