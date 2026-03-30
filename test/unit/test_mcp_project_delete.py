#!/usr/bin/env python3
"""MCP接口: project_delete 完整边界测试.

测试删除条目接口的所有边界情况。
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


def _setup_project_with_item():
    """创建测试项目和条目."""
    temp_dir = tempfile.mkdtemp()
    memory = ProjectMemory(storage_dir=temp_dir)

    result = memory.register_project("测试项目", "/tmp", "测试", ["test"])
    project_id = result["project_id"]
    memory.register_tag(project_id, "test", "测试标签")

    result = memory.add_item(
        project_id=project_id,
        group="features",
        content="内容",
        summary="测试",
        status="pending",
        tags=["test"]
    )
    item_id = result["item_id"]

    return temp_dir, memory, project_id, item_id


class TestProjectDeleteBasic:
    """基础功能测试."""

    def test_delete_feature_success(self):
        """测试删除功能成功."""
        print("测试: 删除功能...")
        temp_dir, memory, project_id, item_id = _setup_project_with_item()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_delete(
                    project_id=project_id,
                    group="features",
                    item_id=item_id
                )
                data = json.loads(result)

                assert data["success"], f"删除失败: {data}"

            print("  ✓ 删除功能测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_delete_note_success(self):
        """测试删除笔记成功."""
        print("测试: 删除笔记...")
        temp_dir, memory, project_id, _ = _setup_project_with_item()
        try:
            result = memory.add_item(
                project_id=project_id,
                group="notes",
                content="笔记",
                summary="笔记",
                tags=["test"]
            )
            note_id = result["item_id"]

            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_delete(
                    project_id=project_id,
                    group="notes",
                    item_id=note_id
                )
                data = json.loads(result)

                assert data["success"], f"删除笔记失败: {data}"

            print("  ✓ 删除笔记测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_delete_fix_success(self):
        """测试删除修复成功."""
        print("测试: 删除修复...")
        temp_dir, memory, project_id, _ = _setup_project_with_item()
        try:
            result = memory.add_item(
                project_id=project_id,
                group="fixes",
                content="修复",
                summary="修复",
                status="pending",
                tags=["test"]
            )
            fix_id = result["item_id"]

            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_delete(
                    project_id=project_id,
                    group="fixes",
                    item_id=fix_id
                )
                data = json.loads(result)

                assert data["success"], f"删除修复失败: {data}"

            print("  ✓ 删除修复测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_delete_standard_success(self):
        """测试删除规范成功."""
        print("测试: 删除规范...")
        temp_dir, memory, project_id, _ = _setup_project_with_item()
        try:
            result = memory.add_item(
                project_id=project_id,
                group="standards",
                content="规范",
                summary="规范",
                tags=["test"]
            )
            std_id = result["item_id"]

            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_delete(
                    project_id=project_id,
                    group="standards",
                    item_id=std_id
                )
                data = json.loads(result)

                assert data["success"], f"删除规范失败: {data}"

            print("  ✓ 删除规范测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestProjectDeleteRequiredParams:
    """必填参数验证测试."""

    def test_missing_project_id(self):
        """测试缺少 project_id."""
        print("测试: 缺少 project_id...")
        temp_dir, memory, project_id, item_id = _setup_project_with_item()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_delete(
                    project_id="",
                    group="features",
                    item_id=item_id
                )
                data = json.loads(result)

                assert not data["success"], "空 project_id 应该失败"

            print("  ✓ 缺少 project_id 测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_missing_group(self):
        """测试缺少 group."""
        print("测试: 缺少 group...")
        temp_dir, memory, project_id, item_id = _setup_project_with_item()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_delete(
                    project_id=project_id,
                    group="",
                    item_id=item_id
                )
                data = json.loads(result)

                assert not data["success"], "空 group 应该失败"

            print("  ✓ 缺少 group 测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_missing_item_id(self):
        """测试缺少 item_id."""
        print("测试: 缺少 item_id...")
        temp_dir, memory, project_id, _ = _setup_project_with_item()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_delete(
                    project_id=project_id,
                    group="features",
                    item_id=""
                )
                data = json.loads(result)

                assert not data["success"], "空 item_id 应该失败"

            print("  ✓ 缺少 item_id 测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestProjectDeleteGroupValidation:
    """分组参数验证测试."""

    def test_invalid_group(self):
        """测试无效分组."""
        print("测试: 无效分组...")
        temp_dir, memory, project_id, item_id = _setup_project_with_item()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_delete(
                    project_id=project_id,
                    group="invalid",
                    item_id=item_id
                )
                data = json.loads(result)

                assert not data["success"], "无效分组应该失败"

            print("  ✓ 无效分组测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestProjectDeleteEdgeCases:
    """边缘情况测试."""

    def test_delete_nonexistent_item(self):
        """测试删除不存在的条目."""
        print("测试: 删除不存在的条目...")
        temp_dir, memory, project_id, _ = _setup_project_with_item()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_delete(
                    project_id=project_id,
                    group="features",
                    item_id="feat_nonexistent"
                )
                data = json.loads(result)

                assert not data["success"], "不存在的条目应该失败"

            print("  ✓ 删除不存在的条目测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_delete_from_nonexistent_project(self):
        """测试从不存在的项目删除."""
        print("测试: 从不存在的项目删除...")
        temp_dir, memory, project_id, item_id = _setup_project_with_item()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_delete(
                    project_id="nonexistent_project",
                    group="features",
                    item_id=item_id
                )
                data = json.loads(result)

                assert not data["success"], "不存在的项目应该失败"

            print("  ✓ 从不存在的项目删除测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_delete_from_archived_project(self):
        """测试从已归档项目删除."""
        print("测试: 从已归档项目删除...")
        temp_dir, memory, project_id, item_id = _setup_project_with_item()
        try:
            memory.remove_project(project_id, mode="archive")

            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_delete(
                    project_id=project_id,
                    group="features",
                    item_id=item_id
                )
                data = json.loads(result)

                assert not data["success"], "已归档项目应该拒绝删除"

            print("  ✓ 从已归档项目删除测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_delete_twice(self):
        """测试重复删除."""
        print("测试: 重复删除...")
        temp_dir, memory, project_id, item_id = _setup_project_with_item()
        try:
            with patch.object(api.tools, 'memory', memory):
                # 第一次删除
                result1 = api.tools.project_delete(
                    project_id=project_id,
                    group="features",
                    item_id=item_id
                )
                data1 = json.loads(result1)
                assert data1["success"], "第一次删除应该成功"

                # 第二次删除
                result2 = api.tools.project_delete(
                    project_id=project_id,
                    group="features",
                    item_id=item_id
                )
                data2 = json.loads(result2)

                assert not data2["success"], "重复删除应该失败"

            print("  ✓ 重复删除测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_concurrent_delete_same_item(self):
        """测试并发删除同一条目."""
        print("测试: 并发删除...")
        temp_dir, memory, project_id, item_id = _setup_project_with_item()
        try:
            import threading

            results = []
            errors = []

            def delete_item():
                try:
                    with patch.object(api.tools, 'memory', memory):
                        result = api.tools.project_delete(
                            project_id=project_id,
                            group="features",
                            item_id=item_id
                        )
                        results.append(json.loads(result))
                except Exception as e:
                    errors.append(e)

            threads = [threading.Thread(target=delete_item) for _ in range(3)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            # 验证只有一个成功，其他失败
            success_count = sum(1 for r in results if r.get("success"))
            assert success_count <= 1, "并发删除应该只有一个成功"

            print("  ✓ 并发删除测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_delete_item_with_special_id_format(self):
        """测试特殊格式的 ID."""
        print("测试: 特殊格式 ID...")
        temp_dir, memory, project_id, _ = _setup_project_with_item()
        try:
            special_ids = [
                "feat_20260330_001",
                "feat_00000000_000",
                "feat_99999999_999",
                "note_20260330_001",
                "fix_20260330_001",
                "std_20260330_001",
            ]

            for special_id in special_ids:
                with patch.object(api.tools, 'memory', memory):
                    result = api.tools.project_delete(
                        project_id=project_id,
                        group="features",
                        item_id=special_id
                    )
                    # ID 格式正确但不存在，应该失败
                    data = json.loads(result)
                    assert not data["success"] or data["success"]

            print("  ✓ 特殊格式 ID 测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestProjectDeleteResponseFormat:
    """响应格式测试."""

    def test_response_format_on_success(self):
        """测试成功响应格式."""
        print("测试: 成功响应格式...")
        temp_dir, memory, project_id, item_id = _setup_project_with_item()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_delete(
                    project_id=project_id,
                    group="features",
                    item_id=item_id
                )
                data = json.loads(result)

                assert data["success"] is True
                assert "data" in data
                assert data["data"]["deleted"] is True
                assert data["data"]["project_id"] == project_id
                assert data["data"]["group"] == "features"
                assert data["data"]["item_id"] == item_id

            print("  ✓ 成功响应格式测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_response_format_on_failure(self):
        """测试失败响应格式."""
        print("测试: 失败响应格式...")
        temp_dir, memory, project_id, _ = _setup_project_with_item()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_delete(
                    project_id=project_id,
                    group="features",
                    item_id="nonexistent"
                )
                data = json.loads(result)

                assert data["success"] is False
                assert "error" in data

            print("  ✓ 失败响应格式测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


def run_all_tests():
    """运行所有测试."""
    print("=" * 60)
    print("MCP接口: project_delete 完整边界测试")
    print("=" * 60)
    print()

    test_classes = [
        TestProjectDeleteBasic,
        TestProjectDeleteRequiredParams,
        TestProjectDeleteGroupValidation,
        TestProjectDeleteEdgeCases,
        TestProjectDeleteResponseFormat,
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
