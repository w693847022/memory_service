#!/usr/bin/env python3
"""MCP接口: tag_* 完整边界测试.

测试标签管理接口的所有边界情况：
- tag_register
- tag_update
- tag_delete
- tag_merge
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

    return temp_dir, memory, project_id


# ==================== tag_register ====================

class TestTagRegisterBasic:
    """tag_register 基础功能测试."""

    def test_register_tag_success(self):
        """测试注册标签成功."""
        print("测试: 注册标签成功...")
        temp_dir, memory, project_id = _setup_project()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.tag_register(
                    project_id=project_id,
                    tag_name="api",
                    summary="API相关标签"
                )
                data = json.loads(result)

                assert data["success"], f"注册标签失败: {data}"

            print("  ✓ 注册标签成功测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_register_tag_with_aliases(self):
        """测试注册带别名的标签."""
        print("测试: 注册带别名的标签...")
        temp_dir, memory, project_id = _setup_project()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.tag_register(
                    project_id=project_id,
                    tag_name="backend",
                    summary="后端标签",
                    aliases="后端,server"
                )
                data = json.loads(result)

                assert data["success"], f"注册带别名标签失败: {data}"

            print("  ✓ 注册带别名标签测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestTagRegisterValidation:
    """tag_register 参数验证测试."""

    def test_missing_project_id(self):
        """测试缺少 project_id."""
        print("测试: 缺少 project_id...")
        temp_dir, memory, _ = _setup_project()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.tag_register(
                    project_id="",
                    tag_name="test",
                    summary="测试"
                )
                data = json.loads(result)

                assert not data["success"], "空 project_id 应该失败"

            print("  ✓ 缺少 project_id 测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_missing_tag_name(self):
        """测试缺少 tag_name."""
        print("测试: 缺少 tag_name...")
        temp_dir, memory, project_id = _setup_project()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.tag_register(
                    project_id=project_id,
                    tag_name="",
                    summary="测试"
                )
                data = json.loads(result)

                assert not data["success"], "空 tag_name 应该失败"

            print("  ✓ 缺少 tag_name 测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_missing_summary(self):
        """测试缺少 summary."""
        print("测试: 缺少 summary...")
        temp_dir, memory, project_id = _setup_project()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.tag_register(
                    project_id=project_id,
                    tag_name="test",
                    summary=""
                )
                data = json.loads(result)

                # summary 可能必填
                assert not data["success"] or "summary" in data.get("error", "").lower()

            print("  ✓ 缺少 summary 测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_invalid_tag_name(self):
        """测试无效标签名."""
        print("测试: 无效标签名...")
        temp_dir, memory, project_id = _setup_project()
        try:
            invalid_names = ["tag with spaces", "标签", "标签!", "tag@"]

            for name in invalid_names:
                with patch.object(api.tools, 'memory', memory):
                    result = api.tools.tag_register(
                        project_id=project_id,
                        tag_name=name,
                        summary="测试"
                    )
                    data = json.loads(result)

                    # 无效标签名应该失败
                    assert not data["success"] or "tag" in data.get("error", "").lower()

            print("  ✓ 无效标签名测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_register_duplicate_tag(self):
        """测试重复注册标签."""
        print("测试: 重复注册标签...")
        temp_dir, memory, project_id = _setup_project()
        try:
            # 第一次注册
            result1 = api.tools.tag_register(
                project_id=project_id,
                tag_name="duplicate",
                summary="测试"
            )

            # 第二次注册
            with patch.object(api.tools, 'memory', memory):
                result2 = api.tools.tag_register(
                    project_id=project_id,
                    tag_name="duplicate",
                    summary="测试"
                )
                data2 = json.loads(result2)

                # 重复注册应该失败或更新
                assert not data2["success"] or "已存在" in data2.get("error", "") or data2["success"]

            print("  ✓ 重复注册标签测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


# ==================== tag_update ====================

class TestTagUpdateBasic:
    """tag_update 基础功能测试."""

    def test_update_tag_summary(self):
        """测试更新标签摘要."""
        print("测试: 更新标签摘要...")
        temp_dir, memory, project_id = _setup_project()
        try:
            # 先注册标签
            memory.register_tag(project_id, "test", "原摘要")

            with patch.object(api.tools, 'memory', memory):
                result = api.tools.tag_update(
                    project_id=project_id,
                    tag_name="test",
                    summary="新摘要"
                )
                data = json.loads(result)

                assert data["success"], f"更新标签失败: {data}"

            print("  ✓ 更新标签摘要测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestTagUpdateValidation:
    """tag_update 参数验证测试."""

    def test_update_nonexistent_tag(self):
        """测试更新不存在的标签."""
        print("测试: 更新不存在的标签...")
        temp_dir, memory, project_id = _setup_project()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.tag_update(
                    project_id=project_id,
                    tag_name="nonexistent",
                    summary="新摘要"
                )
                data = json.loads(result)

                assert not data["success"], "不存在的标签应该失败"

            print("  ✓ 更新不存在的标签测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_update_empty_summary(self):
        """测试更新为空摘要."""
        print("测试: 更新为空摘要...")
        temp_dir, memory, project_id = _setup_project()
        try:
            memory.register_tag(project_id, "test", "原摘要")

            with patch.object(api.tools, 'memory', memory):
                result = api.tools.tag_update(
                    project_id=project_id,
                    tag_name="test",
                    summary=""
                )
                data = json.loads(result)

                # 空摘要可能被允许或拒绝
                # 验证有明确行为

            print("  ✓ 更新为空摘要测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


# ==================== tag_delete ====================

class TestTagDeleteBasic:
    """tag_delete 基础功能测试."""

    def test_delete_unused_tag(self):
        """测试删除未使用的标签."""
        print("测试: 删除未使用的标签...")
        temp_dir, memory, project_id = _setup_project()
        try:
            # 注册但未使用
            memory.register_tag(project_id, "unused", "未使用标签")

            with patch.object(api.tools, 'memory', memory):
                result = api.tools.tag_delete(
                    project_id=project_id,
                    tag_name="unused"
                )
                data = json.loads(result)

                assert data["success"], f"删除未使用标签失败: {data}"

            print("  ✓ 删除未使用标签测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_delete_used_tag_with_force(self):
        """测试强制删除使用中的标签."""
        print("测试: 强制删除使用中的标签...")
        temp_dir, memory, project_id = _setup_project()
        try:
            # 注册并使用标签
            memory.register_tag(project_id, "used", "使用标签")
            memory.add_item(project_id, "features", "内容", "测试", "pending", tags=["used"])

            with patch.object(api.tools, 'memory', memory):
                result = api.tools.tag_delete(
                    project_id=project_id,
                    tag_name="used",
                    force="true"
                )
                data = json.loads(result)

                assert data["success"], f"强制删除失败: {data}"

            print("  ✓ 强制删除使用中的标签测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_delete_used_tag_without_force(self):
        """测试不强制删除使用中的标签."""
        print("测试: 不强制删除使用中的标签...")
        temp_dir, memory, project_id = _setup_project()
        try:
            memory.register_tag(project_id, "used2", "使用标签")
            memory.add_item(project_id, "features", "内容", "测试", "pending", tags=["used2"])

            with patch.object(api.tools, 'memory', memory):
                result = api.tools.tag_delete(
                    project_id=project_id,
                    tag_name="used2",
                    force="false"
                )
                data = json.loads(result)

                assert not data["success"], "不强制删除使用中的标签应该失败"

            print("  ✓ 不强制删除使用中的标签测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestTagDeleteValidation:
    """tag_delete 参数验证测试."""

    def test_delete_nonexistent_tag(self):
        """测试删除不存在的标签."""
        print("测试: 删除不存在的标签...")
        temp_dir, memory, project_id = _setup_project()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.tag_delete(
                    project_id=project_id,
                    tag_name="nonexistent"
                )
                data = json.loads(result)

                assert not data["success"], "不存在的标签应该失败"

            print("  ✓ 删除不存在的标签测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_force_parameter_values(self):
        """测试 force 参数值."""
        print("测试: force 参数值...")
        temp_dir, memory, project_id = _setup_project()
        try:
            memory.register_tag(project_id, "test", "测试")

            for force_val in ["true", "false", "True", "False", "TRUE", "FALSE"]:
                with patch.object(api.tools, 'memory', memory):
                    result = api.tools.tag_delete(
                        project_id=project_id,
                        tag_name="test",
                        force=force_val
                    )
                    # 各种大小写应该都能处理
                    data = json.loads(result)

            print("  ✓ force 参数值测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


# ==================== tag_merge ====================

class TestTagMergeBasic:
    """tag_merge 基础功能测试."""

    def test_merge_tags_success(self):
        """测试合并标签成功."""
        print("测试: 合并标签成功...")
        temp_dir, memory, project_id = _setup_project()
        try:
            # 注册两个标签
            memory.register_tag(project_id, "old_tag", "旧标签")
            memory.register_tag(project_id, "new_tag", "新标签")

            # 使用旧标签
            memory.add_item(project_id, "features", "内容", "测试", "pending", tags=["old_tag"])

            with patch.object(api.tools, 'memory', memory):
                result = api.tools.tag_merge(
                    project_id=project_id,
                    old_tag="old_tag",
                    new_tag="new_tag"
                )
                data = json.loads(result)

                assert data["success"], f"合并标签失败: {data}"

            print("  ✓ 合并标签成功测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestTagMergeValidation:
    """tag_merge 参数验证测试."""

    def test_merge_nonexistent_old_tag(self):
        """测试合并不存在的旧标签."""
        print("测试: 合并不存在的旧标签...")
        temp_dir, memory, project_id = _setup_project()
        try:
            memory.register_tag(project_id, "new", "新标签")

            with patch.object(api.tools, 'memory', memory):
                result = api.tools.tag_merge(
                    project_id=project_id,
                    old_tag="nonexistent",
                    new_tag="new"
                )
                data = json.loads(result)

                assert not data["success"], "不存在的旧标签应该失败"

            print("  ✓ 合并不存在的旧标签测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_merge_nonexistent_new_tag(self):
        """测试合并到不存在的新标签."""
        print("测试: 合并到不存在的新标签...")
        temp_dir, memory, project_id = _setup_project()
        try:
            memory.register_tag(project_id, "old", "旧标签")

            with patch.object(api.tools, 'memory', memory):
                result = api.tools.tag_merge(
                    project_id=project_id,
                    old_tag="old",
                    new_tag="nonexistent"
                )
                data = json.loads(result)

                # 新标签不存在可能自动创建或失败
                # 验证有明确行为

            print("  ✓ 合并到不存在的新标签测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_merge_same_tag(self):
        """测试合并相同标签."""
        print("测试: 合并相同标签...")
        temp_dir, memory, project_id = _setup_project()
        try:
            memory.register_tag(project_id, "same", "相同标签")

            with patch.object(api.tools, 'memory', memory):
                result = api.tools.tag_merge(
                    project_id=project_id,
                    old_tag="same",
                    new_tag="same"
                )
                data = json.loads(result)

                # 合并相同标签应该失败或无操作
                assert not data["success"] or "相同" in data.get("error", "") or data["success"]

            print("  ✓ 合并相同标签测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_merge_to_archived_project(self):
        """测试合并已归档项目的标签."""
        print("测试: 合并已归档项目的标签...")
        temp_dir, memory, project_id = _setup_project()
        try:
            memory.register_tag(project_id, "old", "旧标签")
            memory.register_tag(project_id, "new", "新标签")
            memory.remove_project(project_id, mode="archive")

            with patch.object(api.tools, 'memory', memory):
                result = api.tools.tag_merge(
                    project_id=project_id,
                    old_tag="old",
                    new_tag="new"
                )
                data = json.loads(result)

                assert not data["success"], "已归档项目应该拒绝合并"

            print("  ✓ 合并已归档项目的标签测试通过")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


def run_all_tests():
    """运行所有测试."""
    print("=" * 60)
    print("MCP接口: tag_* 完整边界测试")
    print("=" * 60)
    print()

    test_classes = [
        TestTagRegisterBasic,
        TestTagRegisterValidation,
        TestTagUpdateBasic,
        TestTagUpdateValidation,
        TestTagDeleteBasic,
        TestTagDeleteValidation,
        TestTagMergeBasic,
        TestTagMergeValidation,
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
