"""自定义组管理功能测试.

测试自定义组的创建、更新、删除、组设置等功能。
"""

import json
import os
import shutil
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch

# 设置 PYTHONPATH
import sys
src_dir = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_dir))

from features.project import ProjectMemory
import api.tools


def _setup_project():
    """创建临时项目和内存实例."""
    temp_dir = tempfile.mkdtemp()
    memory = ProjectMemory(storage_dir=temp_dir)
    result = memory.register_project(
        name="test_project",
        path="/tmp/test",
        summary="测试项目",
        tags=["test"]
    )
    assert result["success"], f"创建项目失败: {result}"
    project_id = result["project_id"]
    return temp_dir, memory, project_id


class TestCustomGroupCRUD:
    """自定义组 CRUD 测试."""

    def test_create_custom_group_success(self):
        """测试成功创建自定义组."""
        print("测试: 创建自定义组...")
        temp_dir, memory, project_id = _setup_project()
        try:
            result = memory.create_custom_group(
                project_id=project_id,
                group_name="apis",
                content_max_bytes=500,
                summary_max_bytes=100,
                allow_related=True,
                allowed_related_to=["notes", "features"],
                enable_status=True,
                enable_severity=False
            )
            assert result.get("success"), f"创建自定义组失败: {result}"

            # 验证组配置已保存
            configs = memory._load_group_configs(project_id)
            assert "apis" in configs.get("groups", {})
            apis_config = configs["groups"]["apis"]
            assert apis_config.content_max_bytes == 500
            assert apis_config.summary_max_bytes == 100
            assert apis_config.allow_related == True
            assert apis_config.allowed_related_to == ["notes", "features"]
            assert apis_config.enable_status == True
            assert apis_config.enable_severity == False

            print("  ✓ 创建自定义组成功")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_create_custom_group_reserved_name_conflict(self):
        """测试创建自定义组时保留字段冲突."""
        print("测试: 保留字段冲突...")
        temp_dir, memory, project_id = _setup_project()
        try:
            # 测试与保留字段冲突
            for reserved in ["id", "info", "tag_registry"]:
                result = memory.create_custom_group(
                    project_id=project_id,
                    group_name=reserved
                )
                assert not result.get("success"), f"保留字段 {reserved} 应该被拒绝"
                assert "与系统配置字段冲突" in result.get("error", "")

            print("  ✓ 保留字段冲突检测成功")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_create_custom_group_duplicate_name(self):
        """测试创建重复名称的自定义组."""
        print("测试: 重复名称检测...")
        temp_dir, memory, project_id = _setup_project()
        try:
            # 创建第一个自定义组
            result1 = memory.create_custom_group(
                project_id=project_id,
                group_name="apis"
            )
            assert result1.get("success")

            # 尝试创建同名组
            result2 = memory.create_custom_group(
                project_id=project_id,
                group_name="apis"
            )
            assert not result2.get("success")
            assert "已存在" in result2.get("error", "")

            print("  ✓ 重复名称检测成功")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_update_custom_group_success(self):
        """测试更新自定义组配置."""
        print("测试: 更新自定义组...")
        temp_dir, memory, project_id = _setup_project()
        try:
            # 创建自定义组
            memory.create_custom_group(
                project_id=project_id,
                group_name="apis",
                content_max_bytes=500,
                allow_related=False
            )

            # 更新配置
            result = memory.update_custom_group(
                project_id=project_id,
                group_name="apis",
                content_max_bytes=1000,
                allow_related=True,
                allowed_related_to=["notes"]
            )
            assert result.get("success"), f"更新失败: {result}"

            # 验证更新
            configs = memory._load_group_configs(project_id)
            apis_config = configs["groups"]["apis"]
            assert apis_config.content_max_bytes == 1000
            assert apis_config.allow_related == True
            assert apis_config.allowed_related_to == ["notes"]

            print("  ✓ 更新自定义组成功")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_update_nonexistent_group(self):
        """测试更新不存在的自定义组."""
        print("测试: 更新不存在的组...")
        temp_dir, memory, project_id = _setup_project()
        try:
            result = memory.update_custom_group(
                project_id=project_id,
                group_name="nonexistent"
            )
            assert not result.get("success")
            assert "不存在" in result.get("error", "")

            print("  ✓ 更新不存在组检测成功")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_delete_custom_group_success(self):
        """测试删除自定义组."""
        print("测试: 删除自定义组...")
        temp_dir, memory, project_id = _setup_project()
        try:
            # 创建自定义组
            memory.create_custom_group(
                project_id=project_id,
                group_name="apis"
            )

            # 删除
            result = memory.delete_custom_group(
                project_id=project_id,
                group_name="apis"
            )
            assert result.get("success"), f"删除失败: {result}"

            # 验证已删除
            configs = memory._load_group_configs(project_id)
            assert "apis" not in configs.get("groups", {})

            print("  ✓ 删除自定义组成功")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestGroupSettings:
    """组设置测试."""

    def test_get_group_settings(self):
        """测试获取组设置."""
        print("测试: 获取组设置...")
        temp_dir, memory, project_id = _setup_project()
        try:
            result = memory.get_group_settings(project_id)
            assert result.get("success")
            settings = result.get("settings", {})
            assert "default_related_rules" in settings
            assert settings["default_related_rules"]["features"] == ["notes"]
            assert settings["default_related_rules"]["fixes"] == ["features", "notes"]

            print("  ✓ 获取组设置成功")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_update_group_settings(self):
        """测试更新组设置."""
        print("测试: 更新组设置...")
        temp_dir, memory, project_id = _setup_project()
        try:
            new_rules = {
                "features": ["notes", "fixes"],
                "fixes": ["notes"],
                "standards": ["notes"],
                "notes": []
            }
            result = memory.update_group_settings(
                project_id=project_id,
                default_related_rules=new_rules
            )
            assert result.get("success"), f"更新失败: {result}"

            # 验证更新
            configs = memory._load_group_configs(project_id)
            assert configs["group_settings"]["default_related_rules"]["features"] == ["notes", "fixes"]

            print("  ✓ 更新组设置成功")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestListGroups:
    """列出组测试."""

    def test_list_groups_includes_custom(self):
        """测试列出组包含自定义组."""
        print("测试: 列出组包含自定义组...")
        temp_dir, memory, project_id = _setup_project()
        try:
            # 创建自定义组
            memory.create_custom_group(
                project_id=project_id,
                group_name="apis",
                content_max_bytes=500,
                summary_max_bytes=100,
                allow_related=True,
                allowed_related_to=["notes"],
                enable_status=True,
                enable_severity=False
            )

            # 列出组
            result = memory.list_groups(project_id)
            assert result.get("success")

            groups = result.get("groups", [])
            group_names = [g["name"] for g in groups]

            # 验证内置组
            assert "features" in group_names
            assert "notes" in group_names
            assert "fixes" in group_names
            assert "standards" in group_names

            # 验证自定义组
            assert "apis" in group_names

            # 找到自定义组信息
            apis_group = next(g for g in groups if g["name"] == "apis")
            assert apis_group["is_builtin"] == False
            assert apis_group["config"]["content_max_bytes"] == 500
            assert apis_group["config"]["allow_related"] == True

            print("  ✓ 列出组包含自定义组成功")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestReservedFields:
    """保留字段检测测试."""

    def test_is_reserved_field(self):
        """测试保留字段检测."""
        print("测试: 保留字段检测...")
        from business.core.groups import is_reserved_field

        assert is_reserved_field("id") == True
        assert is_reserved_field("info") == True
        assert is_reserved_field("tag_registry") == True

        # 内置组名不是保留字段
        assert is_reserved_field("features") == False
        assert is_reserved_field("notes") == False
        assert is_reserved_field("fixes") == False
        assert is_reserved_field("standards") == False

        # 自定义组名
        assert is_reserved_field("apis") == False
        assert is_reserved_field("custom_group") == False

        print("  ✓ 保留字段检测成功")


class TestValidateRelatedRules:
    """关联规则验证测试."""

    def test_validate_related_features_to_notes(self):
        """测试 features 关联 notes 应该成功."""
        print("测试: features 关联 notes...")
        temp_dir, memory, project_id = _setup_project()
        try:
            # 先创建一个 note
            note_result = memory.add_item(
                project_id=project_id,
                group="notes",
                summary="测试笔记",
                content="笔记内容",
                tags=["test"]
            )
            assert note_result.get("success"), f"创建笔记失败: {note_result}"
            note_id = note_result.get("item_id")

            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_add(
                    project_id=project_id,
                    group="features",
                    summary="测试功能",
                    content="功能描述",
                    status="pending",
                    related=f'{{"notes": ["{note_id}"]}}',
                    tags="test"
                )
                data = json.loads(result)
                assert data.get("success"), f"features 关联 notes 应该成功: {data}"

            print("  ✓ features 关联 notes 成功")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_validate_related_features_to_features_rejected(self):
        """测试 features 不能关联 features."""
        print("测试: features 不能关联 features...")
        temp_dir, memory, project_id = _setup_project()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_add(
                    project_id=project_id,
                    group="features",
                    summary="测试功能",
                    content="功能描述",
                    status="pending",
                    related='{"features": ["feat_001"]}',
                    tags="test"
                )
                data = json.loads(result)
                assert not data.get("success"), "features 不能关联 features 应该失败"
                assert "只能关联" in data.get("error", "") or "features" in data.get("error", "").lower()

            print("  ✓ features 不能关联 features 被正确拒绝")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_validate_related_notes_not_allowed(self):
        """测试 notes 不支持关联."""
        print("测试: notes 不支持关联...")
        temp_dir, memory, project_id = _setup_project()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_add(
                    project_id=project_id,
                    group="notes",
                    summary="测试笔记",
                    content="笔记内容",
                    related='{"features": ["feat_001"]}',
                    tags="test"
                )
                data = json.loads(result)
                assert not data.get("success"), "notes 不支持关联应该失败"

            print("  ✓ notes 不支持关联被正确拒绝")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_validate_related_standards_to_notes(self):
        """测试 standards 只能关联 notes."""
        print("测试: standards 关联 notes...")
        temp_dir, memory, project_id = _setup_project()
        try:
            # 先创建一个 note
            note_result = memory.add_item(
                project_id=project_id,
                group="notes",
                summary="测试笔记",
                content="笔记内容",
                tags=["test"]
            )
            assert note_result.get("success"), f"创建笔记失败: {note_result}"
            note_id = note_result.get("item_id")

            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_add(
                    project_id=project_id,
                    group="standards",
                    summary="测试规范",
                    content="规范内容",
                    related=f'{{"notes": ["{note_id}"]}}',
                    tags="test"
                )
                data = json.loads(result)
                assert data.get("success"), f"standards 关联 notes 应该成功: {data}"

            print("  ✓ standards 关联 notes 成功")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_validate_related_standards_to_features_rejected(self):
        """测试 standards 不能关联 features."""
        print("测试: standards 不能关联 features...")
        temp_dir, memory, project_id = _setup_project()
        try:
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_add(
                    project_id=project_id,
                    group="standards",
                    summary="测试规范",
                    content="规范内容",
                    related='{"features": ["feat_001"]}',
                    tags="test"
                )
                data = json.loads(result)
                assert not data.get("success"), "standards 不能关联 features 应该失败"

            print("  ✓ standards 不能关联 features 被正确拒绝")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestCustomGroupValidation:
    """自定义组验证测试."""

    def test_validate_content_length_custom_group(self):
        """测试自定义组 content 长度验证."""
        print("测试: 自定义组 content 长度验证...")
        temp_dir, memory, project_id = _setup_project()
        try:
            # 创建自定义组，限制 content_max_bytes=100
            memory.create_custom_group(
                project_id=project_id,
                group_name="apis",
                content_max_bytes=100,
                summary_max_bytes=50,
                allow_related=False
            )

            configs = memory._load_group_configs(project_id)

            with patch.object(api.tools, 'memory', memory):
                # 测试超过限制
                result = api.tools.project_add(
                    project_id=project_id,
                    group="apis",
                    summary="测试摘要",
                    content="a" * 150,  # 超过 100 字节
                    status="pending",  # 自定义组开启了 status
                    tags="test"
                )
                data = json.loads(result)
                assert not data.get("success"), "超过限制应该失败"
                assert "内容过长" in data.get("error", "")

                # 测试在限制内
                result2 = api.tools.project_add(
                    project_id=project_id,
                    group="apis",
                    summary="测试摘要",
                    content="a" * 50,  # 在 100 字节内
                    status="pending",  # 自定义组开启了 status
                    tags="test"
                )
                data2 = json.loads(result2)
                assert data2.get("success"), f"在限制内应该成功: {data2}"

            print("  ✓ 自定义组 content 长度验证成功")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_validate_summary_length_custom_group(self):
        """测试自定义组 summary 长度验证."""
        print("测试: 自定义组 summary 长度验证...")
        temp_dir, memory, project_id = _setup_project()
        try:
            # 创建自定义组，限制 summary_max_bytes=30
            memory.create_custom_group(
                project_id=project_id,
                group_name="apis",
                content_max_bytes=200,
                summary_max_bytes=30,
                allow_related=False
            )

            with patch.object(api.tools, 'memory', memory):
                # 测试超过限制
                result = api.tools.project_add(
                    project_id=project_id,
                    group="apis",
                    summary="a" * 50,  # 超过 30 字节
                    content="内容",
                    status="pending",  # 自定义组开启了 status
                    tags="test"
                )
                data = json.loads(result)
                assert not data.get("success"), "超过限制应该失败"
                assert "摘要过长" in data.get("error", "")

            print("  ✓ 自定义组 summary 长度验证成功")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestProjectGroupsListAPI:
    """project_groups_list 接口测试."""

    def test_groups_list_returns_all_groups(self):
        """测试 project_groups_list 返回所有组."""
        print("测试: groups_list 返回所有组...")
        temp_dir, memory, project_id = _setup_project()
        try:
            # 创建自定义组
            memory.create_custom_group(
                project_id=project_id,
                group_name="apis"
            )

            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_groups_list(project_id)
                data = json.loads(result)

                assert data.get("success"), f"获取组列表失败: {data}"
                groups = data.get("data", {}).get("groups", [])
                group_names = [g["name"] for g in groups]

                # 验证内置组和自定义组都在列表中
                assert "features" in group_names
                assert "notes" in group_names
                assert "fixes" in group_names
                assert "standards" in group_names
                assert "apis" in group_names

            print("  ✓ groups_list 返回所有组成功")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestCustomGroupSeverityValidation:
    """自定义组 severity 验证测试."""

    def test_custom_group_enable_severity_valid_value(self):
        """测试自定义组开启 severity 时，有效值应该成功."""
        print("测试: 自定义组开启 severity 有效值...")
        temp_dir, memory, project_id = _setup_project()
        try:
            # 创建开启 severity 的自定义组
            memory.create_custom_group(
                project_id=project_id,
                group_name="apis",
                enable_severity=True
            )

            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_add(
                    project_id=project_id,
                    group="apis",
                    summary="测试摘要",
                    content="测试内容",
                    status="pending",
                    severity="high",
                    tags="test"
                )
                data = json.loads(result)
                assert data.get("success"), f"有效 severity 值应该成功: {data}"

            print("  ✓ 自定义组 severity 有效值成功")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_custom_group_enable_severity_invalid_value(self):
        """测试自定义组开启 severity 时，无效值应该被拒绝."""
        print("测试: 自定义组开启 severity 无效值...")
        temp_dir, memory, project_id = _setup_project()
        try:
            # 创建开启 severity 的自定义组
            memory.create_custom_group(
                project_id=project_id,
                group_name="apis",
                enable_severity=True
            )

            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_add(
                    project_id=project_id,
                    group="apis",
                    summary="测试摘要",
                    content="测试内容",
                    status="pending",
                    severity="invalid_severity",
                    tags="test"
                )
                data = json.loads(result)
                assert not data.get("success"), "无效 severity 值应该失败"
                assert "severity" in data.get("error", "").lower()

            print("  ✓ 自定义组 severity 无效值被拒绝")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_custom_group_disable_severity_ignored(self):
        """测试自定义组关闭 severity 时，传入 severity 应该被忽略."""
        print("测试: 自定义组关闭 severity 时传入 severity...")
        temp_dir, memory, project_id = _setup_project()
        try:
            # 创建关闭 severity 的自定义组（默认）
            memory.create_custom_group(
                project_id=project_id,
                group_name="apis",
                enable_severity=False
            )

            with patch.object(api.tools, 'memory', memory):
                # 关闭 severity 时传入 severity 仍应成功（被忽略）
                result = api.tools.project_add(
                    project_id=project_id,
                    group="apis",
                    summary="测试摘要",
                    content="测试内容",
                    status="pending",
                    severity="high",
                    tags="test"
                )
                data = json.loads(result)
                assert data.get("success"), f"关闭 severity 时传入 severity 应被忽略: {data}"

            print("  ✓ 自定义组关闭 severity 时传入 severity 被忽略")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestCustomGroupRelatedValidation:
    """自定义组关联规则验证测试."""

    def test_custom_group_allow_related_false_rejected(self):
        """测试自定义组关闭关联时，尝试关联应该被拒绝."""
        print("测试: 自定义组关闭关联时尝试关联...")
        temp_dir, memory, project_id = _setup_project()
        try:
            # 创建关闭关联的自定义组
            memory.create_custom_group(
                project_id=project_id,
                group_name="apis",
                allow_related=False
            )

            # 先创建一个 note
            note_result = memory.add_item(
                project_id=project_id,
                group="notes",
                summary="测试笔记",
                content="笔记内容",
                tags=["test"]
            )
            assert note_result.get("success"), f"创建笔记失败: {note_result}"
            note_id = note_result.get("item_id")

            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_add(
                    project_id=project_id,
                    group="apis",
                    summary="测试摘要",
                    content="测试内容",
                    status="pending",
                    related=f'{{"notes": ["{note_id}"]}}',
                    tags="test"
                )
                data = json.loads(result)
                assert not data.get("success"), "关闭关联时尝试关联应该失败"
                assert "不支持关联" in data.get("error", "")

            print("  ✓ 自定义组关闭关联时尝试关联被拒绝")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_custom_group_allow_related_specific_targets(self):
        """测试自定义组允许关联但限制目标组."""
        print("测试: 自定义组允许关联但限制目标组...")
        temp_dir, memory, project_id = _setup_project()
        try:
            # 创建允许关联但只允许关联 notes 的自定义组
            memory.create_custom_group(
                project_id=project_id,
                group_name="apis",
                allow_related=True,
                allowed_related_to=["notes"]
            )

            # 先创建一个 note 和一个 feature
            note_result = memory.add_item(
                project_id=project_id,
                group="notes",
                summary="测试笔记",
                content="笔记内容",
                tags=["test"]
            )
            assert note_result.get("success")
            note_id = note_result.get("item_id")

            feat_result = memory.add_item(
                project_id=project_id,
                group="features",
                summary="测试功能",
                content="功能描述",
                status="pending",
                tags=["test"]
            )
            assert feat_result.get("success")
            feat_id = feat_result.get("item_id")

            with patch.object(api.tools, 'memory', memory):
                # 关联 notes 应该成功
                result1 = api.tools.project_add(
                    project_id=project_id,
                    group="apis",
                    summary="测试摘要",
                    content="测试内容",
                    status="pending",
                    related=f'{{"notes": ["{note_id}"]}}',
                    tags="test"
                )
                data1 = json.loads(result1)
                assert data1.get("success"), f"关联 notes 应该成功: {data1}"

                # 关联 features 应该失败
                result2 = api.tools.project_add(
                    project_id=project_id,
                    group="apis",
                    summary="测试摘要2",
                    content="测试内容2",
                    status="pending",
                    related=f'{{"features": ["{feat_id}"]}}',
                    tags="test"
                )
                data2 = json.loads(result2)
                assert not data2.get("success"), "只允许关联 notes 时关联 features 应该失败"
                assert "只能关联" in data2.get("error", "")

            print("  ✓ 自定义组允许关联但限制目标组验证成功")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestCustomGroupPartialUpdate:
    """自定义组部分更新测试."""

    def test_update_custom_group_partial_fields(self):
        """测试只更新部分字段时，其他字段保持不变."""
        print("测试: 部分更新自定义组...")
        temp_dir, memory, project_id = _setup_project()
        try:
            # 创建自定义组
            memory.create_custom_group(
                project_id=project_id,
                group_name="apis",
                content_max_bytes=500,
                summary_max_bytes=100,
                allow_related=True,
                allowed_related_to=["notes", "features"],
                enable_status=True,
                enable_severity=False
            )

            # 只更新 content_max_bytes
            result = memory.update_custom_group(
                project_id=project_id,
                group_name="apis",
                content_max_bytes=1000
            )
            assert result.get("success"), f"更新失败: {result}"

            # 验证其他字段保持不变
            configs = memory._load_group_configs(project_id)
            apis_config = configs["groups"]["apis"]
            assert apis_config.content_max_bytes == 1000, "content_max_bytes 应该更新"
            assert apis_config.summary_max_bytes == 100, "summary_max_bytes 应该保持不变"
            assert apis_config.allow_related == True, "allow_related 应该保持不变"
            assert apis_config.allowed_related_to == ["notes", "features"], "allowed_related_to 应该保持不变"
            assert apis_config.enable_status == True, "enable_status 应该保持不变"
            assert apis_config.enable_severity == False, "enable_severity 应该保持不变"

            print("  ✓ 部分更新自定义组成功")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestDeleteNonexistentGroup:
    """删除不存在的组测试."""

    def test_delete_nonexistent_group(self):
        """测试删除不存在的自定义组."""
        print("测试: 删除不存在的组...")
        temp_dir, memory, project_id = _setup_project()
        try:
            result = memory.delete_custom_group(
                project_id=project_id,
                group_name="nonexistent"
            )
            assert not result.get("success")
            assert "不存在" in result.get("error", "")

            print("  ✓ 删除不存在组检测成功")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestCustomGroupIDPrefix:
    """自定义组 ID 前缀测试."""

    def test_custom_group_id_prefix_uses_full_name(self):
        """测试自定义组使用完整组名作为 ID 前缀."""
        print("测试: 自定义组 ID 前缀使用完整组名...")
        temp_dir, memory, project_id = _setup_project()
        try:
            # 创建自定义组
            memory.create_custom_group(
                project_id=project_id,
                group_name="apis"
            )

            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_add(
                    project_id=project_id,
                    group="apis",
                    summary="测试摘要",
                    content="测试内容",
                    status="pending",
                    tags="test"
                )
                data = json.loads(result)
                assert data.get("success"), f"添加项目失败: {data}"

                item_id = data.get("data", {}).get("item_id", "")
                # 自定义组 "apis" 的前缀应该是 "apis" 而不是 "api" 或其他
                assert item_id.startswith("apis_"), f"自定义组 ID 前缀应该使用完整组名，actual: {item_id}"

            print("  ✓ 自定义组 ID 前缀使用完整组名成功")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_builtin_group_id_prefix(self):
        """测试内置组使用预定义前缀."""
        print("测试: 内置组 ID 前缀...")
        temp_dir, memory, project_id = _setup_project()
        try:
            with patch.object(api.tools, 'memory', memory):
                # features -> feat_
                result = api.tools.project_add(
                    project_id=project_id,
                    group="features",
                    summary="测试功能",
                    content="功能描述",
                    status="pending",
                    tags="test"
                )
                data = json.loads(result)
                assert data.get("success")
                feat_id = data.get("data", {}).get("item_id", "")
                assert feat_id.startswith("feat_"), f"features 前缀应该是 feat_，actual: {feat_id}"

                # fixes -> fix_
                result2 = api.tools.project_add(
                    project_id=project_id,
                    group="fixes",
                    summary="测试修复",
                    content="修复描述",
                    status="pending",
                    severity="high",
                    tags="test"
                )
                data2 = json.loads(result2)
                assert data2.get("success")
                fix_id = data2.get("data", {}).get("item_id", "")
                assert fix_id.startswith("fix_"), f"fixes 前缀应该是 fix_，actual: {fix_id}"

                # notes -> note_
                result3 = api.tools.project_add(
                    project_id=project_id,
                    group="notes",
                    summary="测试笔记",
                    content="笔记内容",
                    tags="test"
                )
                data3 = json.loads(result3)
                assert data3.get("success")
                note_id = data3.get("data", {}).get("item_id", "")
                assert note_id.startswith("note_"), f"notes 前缀应该是 note_，actual: {note_id}"

                # standards -> std_
                result4 = api.tools.project_add(
                    project_id=project_id,
                    group="standards",
                    summary="测试规范",
                    content="规范内容",
                    tags="test"
                )
                data4 = json.loads(result4)
                assert data4.get("success")
                std_id = data4.get("data", {}).get("item_id", "")
                assert std_id.startswith("std_"), f"standards 前缀应该是 std_，actual: {std_id}"

            print("  ✓ 内置组 ID 前缀验证成功")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestCustomGroupStatusValidation:
    """自定义组 status 验证测试."""

    def test_custom_group_enable_status_valid_value(self):
        """测试自定义组开启 status 时，有效值应该成功."""
        print("测试: 自定义组开启 status 有效值...")
        temp_dir, memory, project_id = _setup_project()
        try:
            # 创建开启 status 的自定义组（默认开启）
            memory.create_custom_group(
                project_id=project_id,
                group_name="apis",
                enable_status=True
            )

            with patch.object(api.tools, 'memory', memory):
                for status in ["pending", "in_progress", "completed"]:
                    result = api.tools.project_add(
                        project_id=project_id,
                        group="apis",
                        summary="测试摘要",
                        content="测试内容",
                        status=status,
                        tags="test"
                    )
                    data = json.loads(result)
                    assert data.get("success"), f"status={status} 应该成功: {data}"

            print("  ✓ 自定义组 status 有效值成功")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_custom_group_enable_status_invalid_value(self):
        """测试自定义组开启 status 时，无效值应该被拒绝."""
        print("测试: 自定义组开启 status 无效值...")
        temp_dir, memory, project_id = _setup_project()
        try:
            memory.create_custom_group(
                project_id=project_id,
                group_name="apis",
                enable_status=True
            )

            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_add(
                    project_id=project_id,
                    group="apis",
                    summary="测试摘要",
                    content="测试内容",
                    status="invalid_status",
                    tags="test"
                )
                data = json.loads(result)
                assert not data.get("success"), "无效 status 值应该失败"
                assert "status" in data.get("error", "").lower()

            print("  ✓ 自定义组 status 无效值被拒绝")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestBuiltinGroupConfig:
    """内置组配置测试."""

    def test_builtin_group_default_config(self):
        """测试内置组默认配置生效."""
        print("测试: 内置组默认配置...")
        temp_dir, memory, project_id = _setup_project()
        try:
            # 加载组配置
            configs = memory._load_group_configs(project_id)
            groups = configs.get("groups", {})

            # 验证内置组默认配置
            assert "features" in groups
            assert "fixes" in groups
            assert "notes" in groups
            assert "standards" in groups

            features_config = groups["features"]
            assert features_config.content_max_bytes == 240
            assert features_config.summary_max_bytes == 90
            assert features_config.enable_status == True
            assert features_config.status_values == ["pending", "in_progress", "completed"]
            assert features_config.is_builtin == True

            fixes_config = groups["fixes"]
            assert fixes_config.enable_severity == True
            assert fixes_config.severity_values == ["critical", "high", "medium", "low"]

            notes_config = groups["notes"]
            assert notes_config.enable_status == False
            assert notes_config.enable_severity == False

            print("  ✓ 内置组默认配置正确")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_update_builtin_group_config(self):
        """测试更新内置组配置."""
        print("测试: 更新内置组配置...")
        temp_dir, memory, project_id = _setup_project()
        try:
            # 更新内置组配置
            result = memory.update_group(
                project_id=project_id,
                group_name="features",
                content_max_bytes=500,
                summary_max_bytes=150,
                allow_related=True,
                allowed_related_to=["notes", "fixes"]
            )
            assert result.get("success"), f"更新内置组失败: {result}"

            # 验证更新
            configs = memory._load_group_configs(project_id)
            features_config = configs["groups"]["features"]
            assert features_config.content_max_bytes == 500
            assert features_config.summary_max_bytes == 150
            assert features_config.allowed_related_to == ["notes", "fixes"]
            assert features_config.is_builtin == True  # 仍然是内置组

            print("  ✓ 更新内置组配置成功")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_list_groups_includes_builtin_config(self):
        """测试 list_groups 返回内置组完整配置."""
        print("测试: list_groups 返回内置组配置...")
        temp_dir, memory, project_id = _setup_project()
        try:
            result = memory.list_groups(project_id)
            assert result.get("success")

            groups = result.get("groups", [])
            features_group = next((g for g in groups if g["name"] == "features"), None)
            assert features_group is not None
            assert features_group["is_builtin"] == True
            assert features_group["config"]["content_max_bytes"] == 240
            assert features_group["config"]["enable_status"] == True

            fixes_group = next((g for g in groups if g["name"] == "fixes"), None)
            assert fixes_group is not None
            assert fixes_group["config"]["enable_severity"] == True

            print("  ✓ list_groups 返回内置组完整配置")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_builtin_group_item_validation(self):
        """测试内置组项目验证生效."""
        print("测试: 内置组项目验证...")
        temp_dir, memory, project_id = _setup_project()
        try:
            # features 组需要 status
            with patch.object(api.tools, 'memory', memory):
                result = api.tools.project_add(
                    project_id=project_id,
                    group="features",
                    summary="测试功能",
                    content="功能内容",
                    tags="test"
                )
                data = json.loads(result)
                assert not data.get("success"), "features 组缺少 status 应该失败"
                assert "status" in data.get("error", "")

                # 提供 status 后应该成功
                result = api.tools.project_add(
                    project_id=project_id,
                    group="features",
                    summary="测试功能",
                    content="功能内容",
                    status="pending",
                    tags="test"
                )
                data = json.loads(result)
                assert data.get("success"), f"提供 status 后应该成功: {data}"

            print("  ✓ 内置组项目验证正确")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_builtin_group_cannot_be_deleted(self):
        """测试内置组不能被删除."""
        print("测试: 内置组不能删除...")
        temp_dir, memory, project_id = _setup_project()
        try:
            # 尝试删除内置组
            result = memory.delete_custom_group(
                project_id=project_id,
                group_name="features"
            )
            assert not result.get("success"), "内置组不应该被删除"
            assert "不能删除" in result.get("error", "")

            print("  ✓ 内置组不能删除")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_update_nonexistent_group_fails(self):
        """测试更新不存在的组失败."""
        print("测试: 更新不存在的组失败...")
        temp_dir, memory, project_id = _setup_project()
        try:
            # 更新一个不存在的组
            result = memory.update_group(
                project_id=project_id,
                group_name="nonexistent",
                content_max_bytes=300
            )
            assert not result.get("success"), "更新不存在的组应该失败"
            assert "不存在" in result.get("error", "")

            print("  ✓ 更新不存在的组正确失败")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
